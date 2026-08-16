"""Stage1 语义召回（T4.1）——《匹配详细设计》第 3 章 + AI核心 §5.3.2。

职责：在 **Stage0 passed 集内**做**两路 ANN**：路径A 代表向量（vendor_representative）+ 路径B 原文块（doc_chunks），
semantic_score = max(rep, chunk)，**只做召回不进最终分**（D9/D10）。
- 需求向量化文本：demand_embedding_text（D9 自然语言模板，与厂商 summary 同构保证向量对称）
- 参数：top_k=50、min_semantic≈0.35（待评估，§5.3.6②）
"""
from __future__ import annotations

import asyncio
import json
import logging

from app.domains import ontology
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
    """需求档案（正向点快照 D6/D7/D8）→ 自然语言需求描述（D9，与厂商 summary 同构保证向量对称）。"""
    demand = demand or {}
    dims = demand.get("dimensions")
    parts: list[str] = []
    if isinstance(dims, dict):
        pt_sv = dims.get("product_type") or {}
        pt = pt_sv.get("value") if isinstance(pt_sv, dict) else None
        for key, sv in dims.items():
            if not isinstance(sv, dict):
                continue
            v = sv.get("value")
            if v in (None, "", []):
                continue
            label = ontology.label_of(key, pt)
            val = "、".join(str(x) for x in v) if isinstance(v, list) else str(v)
            parts.append(f"{label}{val}")
    else:
        # 兼容旧快照（扁平 key: value）
        for k, sv in demand.items():
            v, st = _norm_slot(sv)
            if st in ("excluded", "wildcard") or v in (None, "", []):
                continue
            label = ontology.label_of(k)
            val = "、".join(str(x) for x in v) if isinstance(v, list) else str(v)
            parts.append(f"{label}{val}")
    for e in demand.get("extended", []) or []:
        if isinstance(e, dict) and e.get("value"):
            parts.append(str(e["value"]))
        elif isinstance(e, str) and e.strip():
            parts.append(e.strip())
    return "，".join(parts).strip()


def _filter_expr(passed_ids: list[str] | None) -> str | None:
    return f'vendor_id in {json.dumps(passed_ids)}' if passed_ids else None


def _search_sync(qvec: list[float], top_k: int, min_score: float, passed_ids: list[str] | None = None) -> list[dict]:
    """路径A：vendor_representative ANN（passed 集内）。返回 [{vendor_id, semantic_score, recall_source}]。"""
    client = get_client()
    res = client.search(
        REP_COLLECTION,
        data=[qvec],
        limit=top_k * 2,
        filter=_filter_expr(passed_ids),
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
        out.append({"vendor_id": vid, "semantic_score": score, "recall_source": "rep"})
    return out[:top_k]


def _search_chunks_all_sync(qvec: list[float], top_k: int, min_score: float, passed_ids: list[str] | None = None) -> list[dict]:
    """路径B：doc_chunks 原文块 ANN（passed 集内），按厂商聚合并取最高分。"""
    client = get_client()
    res = client.search(
        CHUNK_COLLECTION,
        data=[qvec],
        limit=top_k * 4,
        filter=_filter_expr(passed_ids),
        output_fields=["vendor_id"],
        search_params={"metric_type": "COSINE", "params": {}},
    )
    best: dict[str, float] = {}
    for hit in (res[0] if res else []):
        score = float(hit.get("distance", 0.0))
        if score < min_score:
            continue
        vid = hit.get("entity", {}).get("vendor_id")
        if not vid:
            continue
        if vid not in best or score > best[vid]:
            best[vid] = score
    return [{"vendor_id": k, "semantic_score": v, "recall_source": "chunk"} for k, v in best.items()]


async def retrieve(demand: dict, top_k: int = TOP_K, min_score: float = MIN_SEMANTIC,
                   passed_ids: list[str] | None = None) -> list[dict]:
    """Stage1：passed 内两路 ANN（REP ∪ 原文块），semantic_score = max（只做召回）。"""
    text = demand_embedding_text(demand)
    if not text:
        return []
    [qvec] = await embed([text])
    rep, chk = await asyncio.gather(
        asyncio.to_thread(_search_sync, qvec, top_k, min_score, passed_ids),
        asyncio.to_thread(_search_chunks_all_sync, qvec, top_k, min_score, passed_ids),
    )
    merged: dict[str, dict] = {}
    for c in rep + chk:
        vid = c["vendor_id"]
        if vid not in merged or c["semantic_score"] > merged[vid]["semantic_score"]:
            merged[vid] = c
    out = sorted(merged.values(), key=lambda x: -x["semantic_score"])[:top_k]
    return out


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
        "os": "os",
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
