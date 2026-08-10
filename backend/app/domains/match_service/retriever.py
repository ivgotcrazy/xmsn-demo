"""通道A 语义检索（T4.1）——《匹配详细设计》第 3 章。

职责：需求向量在 `vendor_representative` 集合 ANN 检索 Top-K 厂商候选，产出 semantic_score。
- 需求向量化文本：demand_embedding_text（3.2）
- 参数：top_k=50、min_semantic=0.35（低于阈值不进候选，节省通道B LLM 调用）
- 边界：只负责"相关召回"；不读原文块（doc_chunks 仅供溯源）
"""
from __future__ import annotations

import asyncio
import logging

from app.llm.embedding import embed
from app.vector.client import CHUNK_COLLECTION, REP_COLLECTION, get_client

logger = logging.getLogger("xmsn.match")

TOP_K = 50
MIN_SEMANTIC = 0.35


def _norm_slot(sv):
    """兼容三态 dict({value,state}) / 纯值 / excluded 标记({excluded:True,value}) → (value, state)。"""
    if isinstance(sv, dict):
        if "state" in sv:
            return sv.get("value"), sv.get("state")
        if sv.get("excluded"):
            return sv.get("value"), "excluded"
        return sv, "set"
    return sv, "set"


def demand_embedding_text(demand: dict) -> str:
    """需求快照（三态 structured_demand）→ 向量化文本（3.2）。排除/通配/空值不拼入。"""
    parts: list[str] = []
    for k, sv in (demand or {}).items():
        v, st = _norm_slot(sv)
        if st in ("excluded", "wildcard"):
            continue
        if v is None or v == "" or v == []:
            continue
        parts.append(f"{k}:{'、'.join(str(x) for x in v) if isinstance(v, list) else v}")
    extra = demand.get("extra_constraints")
    if isinstance(extra, list):
        for c in extra:
            parts.append(f"约束:{c}")
    return " ".join(parts).strip()


def _search_sync(qvec: list[float], top_k: int, min_score: float) -> list[dict]:
    """同步 Milvus ANN（vendor_representative）。返回 [{vendor_id, semantic_score}]。"""
    client = get_client()
    res = client.search(
        REP_COLLECTION,
        data=[qvec],
        limit=top_k * 2,
        output_fields=["vendor_id"],
        search_params={"metric_type": "COSINE", "params": {}},
    )
    out: list[dict] = []
    for hit in (res[0] if res else []):
        score = float(hit.get("distance", 0.0))
        if score < min_score:
            continue
        vid = hit.get("entity", {}).get("vendor_id")
        if not vid:
            continue
        out.append({"vendor_id": vid, "semantic_score": score})
    return out[:top_k]


async def retrieve(demand: dict, top_k: int = TOP_K, min_score: float = MIN_SEMANTIC) -> list[dict]:
    """需求 → Top-K 厂商候选（vendor_id + semantic_score）。embedding 失败由 service 兜底降级。"""
    text = demand_embedding_text(demand)
    if not text:
        return []
    [qvec] = await embed([text])
    return await asyncio.to_thread(_search_sync, qvec, top_k, min_score)


def _search_chunks_sync(vendor_id: str, qvec: list[float], top_k: int) -> list[dict]:
    """同步检索该厂商 doc_chunks 原文块（溯源用，T5.3）。"""
    client = get_client()
    res = client.search(
        CHUNK_COLLECTION,
        data=[qvec],
        limit=top_k * 3,
        filter=f'vendor_id == "{vendor_id}"',
        output_fields=["doc_id", "doc_name", "page", "chunk_text"],
        search_params={"metric_type": "COSINE", "params": {}},
    )
    out: list[dict] = []
    for hit in (res[0] if res else []):
        ent = hit.get("entity", {})
        if not ent.get("chunk_text"):
            continue
        out.append({
            "doc_id": ent.get("doc_id"),
            "doc_name": ent.get("doc_name"),
            "page": ent.get("page"),
            "chunk_text": ent.get("chunk_text"),
            "score": float(hit.get("distance", 0.0)),
        })
    return out[:top_k]


async def retrieve_chunks(vendor_id: str, query: str, top_k: int = 5) -> list[dict]:
    """厂商 doc_chunks 原文块检索（解释溯源：source → 查看原文）。"""
    query = (query or "").strip()
    if not query:
        return []
    try:
        [qvec] = await embed([query])
        return await asyncio.to_thread(_search_chunks_sync, vendor_id, qvec, top_k)
    except Exception as exc:  # noqa: BLE001 - 溯源失败不阻断解释
        logger.warning("chunk retrieve failed: %s", exc)
        return []


async def tag_search(demand: dict) -> list[dict]:
    """通道A 标签检索兜底（6.1 hybrid）：embedding 不可用时，structured_tags 直接命中。

    简化：从 PG 全量 passed 厂商能力，按 product_type/os 等已指定值做精确包含匹配，
    返回 vendor_id + semantic_score=0.5（无向量，语义维度缺失不虚报高分）。
    """
    from sqlalchemy import select

    from app.db.models import VendorCapability
    from app.db.session import SessionLocal

    d_val = {}
    for k, sv in (demand or {}).items():
        v, st = _norm_slot(sv)
        if st != "set":
            continue
        if v not in (None, "", []):
            d_val[k] = v

    out: list[dict] = []
    async with SessionLocal() as db:
        res = await db.execute(
            select(VendorCapability).where(VendorCapability.structured_tags.isnot(None))
        )
        for cap in res.scalars().all():
            tags = cap.structured_tags or {}
            if _tags_hit(d_val, tags):
                out.append({"vendor_id": str(cap.vendor_id), "semantic_score": 0.5})
    return out


def _tags_hit(demand_vals: dict, tags: dict) -> bool:
    """已指定需求值 与 厂商标签 是否有交集（product_type/os/interfaces/certifications）。"""
    mapping = {
        "product_type": "product_types",
        "os": "os_support",
        "interfaces": "interfaces",
        "certifications": "certifications",
    }
    for d_field, tag_field in mapping.items():
        d = demand_vals.get(d_field)
        if d is None:
            continue
        s = tags.get(tag_field)
        if s is None:
            continue
        s_set = set(s) if isinstance(s, list) else {s}
        d_list = d if isinstance(d, list) else [d]
        if any(x in s_set for x in d_list):
            return True
    return False
