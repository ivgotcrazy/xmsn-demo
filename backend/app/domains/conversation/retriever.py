"""领域知识检索（T3.4，RAG）——《代理详细设计》第 5 章。

- build_rag_query：已确认槽位摘要 + 最近用户消息 → 检索 query
- retrieve：knowledge_base（Milvus）按 industry 过滤 + 余弦相似度 Top-K，
  再回 PG knowledge_items 取 content（文本以 PG 为主，Milvus 仅向量）
- build_knowledge_section：System Prompt 第 4 区块（`[来源:{category}] {content}`）
- 边界：知识只增强对话专业性，不参与匹配打分（架构 6.2 / LLD 5.2）；
  低于 min_score 不注入（防噪声）；检索异常静默降级（不阻塞对话）
"""
from __future__ import annotations

import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import KnowledgeItem
from app.llm.embedding import embed
from app.vector.client import KNOWLEDGE_COLLECTION, get_client

logger = logging.getLogger("xmsn.retriever")

RAG_TOP_K = 3
# 校准值：智谱 embedding-2 中文语义相似度普遍偏低（相关≈0.5+，无关≈0.2），
# 设计文档 0.6 实测会把相关命中全部过滤；0.4 能精准分离相关/无关（见 T3.4 验证）。
RAG_MIN_SCORE = 0.4


class KnowledgeHit:
    """单条知识命中（含 PG 文本内容）。"""

    __slots__ = ("knowledge_id", "category", "industry", "content", "score")

    def __init__(self, knowledge_id: str, category: str | None, industry: str | None,
                 content: str, score: float) -> None:
        self.knowledge_id = knowledge_id
        self.category = category or "general"
        self.industry = industry
        self.content = content
        self.score = score


def build_rag_query(state: dict) -> str:
    """query = 已确认槽位摘要 + 最近用户消息（LLD 5.1）。"""
    parts = []
    for k, sv in state.items():
        if k.startswith("_") or not isinstance(sv, dict) or sv.get("state") != "set":
            continue
        v = sv.get("value")
        if v is None:
            continue
        parts.append(f"{k}:{'、'.join(v) if isinstance(v, list) else v}")
    return " ".join(parts).strip()


def build_knowledge_section(hits: list[KnowledgeHit]) -> str:
    """System Prompt 第 4 区块（与 Schema/指令隔离，防注入）。"""
    if not hits:
        return ""
    blocks = [f"[来源:{h.category}] {h.content}" for h in hits]
    return "# 行业背景知识\n" + "\n".join(blocks)


def _search_sync(query_vec: list[float], industry: str | None, top_k: int, min_score: float) -> list[dict]:
    """同步 Milvus 检索（industry 过滤 + 余弦）。返回命中实体 dict 列表。"""
    client = get_client()
    filt = f'industry == "{industry}"' if industry else ""
    res = client.search(
        KNOWLEDGE_COLLECTION,
        data=[query_vec],
        limit=top_k * 4,
        filter=filt,
        output_fields=["knowledge_id", "category", "industry"],
        search_params={"metric_type": "COSINE", "params": {}},
    )
    out: list[dict] = []
    for hit in (res[0] if res else []):
        score = float(hit.get("distance", 0.0))
        if score < min_score:
            continue
        ent = hit.get("entity", {})
        out.append({
            "knowledge_id": ent.get("knowledge_id"),
            "category": ent.get("category"),
            "industry": ent.get("industry"),
            "score": score,
        })
    return out[:top_k]


async def retrieve(db: AsyncSession, query: str, industry: str | None,
                   top_k: int = RAG_TOP_K, min_score: float = RAG_MIN_SCORE) -> list[KnowledgeHit]:
    """检索 Top-K 知识，回 PG 取 content。空 query 或检索失败 → []。"""
    query = (query or "").strip()
    if not query or not db:
        return []
    try:
        [qvec] = await embed([query])
    except Exception as exc:  # noqa: BLE001
        logger.warning("rag embed failed: %s", exc)
        return []
    try:
        hits = await asyncio.to_thread(_search_sync, qvec, industry, top_k, min_score)
    except Exception as exc:  # noqa: BLE001
        logger.warning("rag search failed (降级不注入): %s", exc)
        return []

    result: list[KnowledgeHit] = []
    for h in hits:
        kid = h.get("knowledge_id")
        if not kid:
            continue
        try:
            kid_uuid = uuid.UUID(str(kid))
        except ValueError:
            continue
        row = await db.get(KnowledgeItem, kid_uuid)
        if row and row.content:
            result.append(KnowledgeHit(
                knowledge_id=str(row.knowledge_id),
                category=row.category,
                industry=row.industry,
                content=row.content,
                score=h["score"],
            ))
    return result
