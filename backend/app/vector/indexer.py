"""双轨向量索引（T2.4 / 架构 6.2）。

代表向量 = embed(summary)（D9：自然语言全字段 ≤400 字，1 档案 1 向量，路径A）；
原文块向量 = 文档按 800 字切块（overlap 100），携带 vendor_id/doc_id/page/chunk_text（引用溯源）。
重新解析/删除后调用方先删旧向量再写入（保持"仅最新"）。
"""
from __future__ import annotations

import asyncio

from app.llm.embedding import embed
from app.vector.client import CHUNK_COLLECTION, REP_COLLECTION, get_client


def chunk_text(text: str, max_chars: int = 800, overlap: int = 100) -> list[str]:
    """按字符切块（厂商解析 LLD 3：max_chars=800, overlap=100）。"""
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks


def _delete_sync(vendor_id: str) -> None:
    client = get_client()
    for col in (REP_COLLECTION, CHUNK_COLLECTION):
        try:
            client.delete(col, filter=f'vendor_id == "{vendor_id}"')
        except Exception:  # noqa: BLE001 - 集合可能为空
            pass


def _upsert_rep(vendor_id: str, text: str, vec: list[float]) -> None:
    get_client().upsert(
        REP_COLLECTION,
        data=[{"id": f"rep_{vendor_id}", "vendor_id": vendor_id, "text": text, "embedding": vec}],
    )


def _insert_chunks(vendor_id: str, rows: list[dict]) -> int:
    get_client().insert(CHUNK_COLLECTION, data=rows)
    return len(rows)


async def delete_vendor_vectors(vendor_id: str) -> None:
    """删除某厂商全部向量（重解析前清理，保持"仅最新"）。"""
    await asyncio.to_thread(_delete_sync, vendor_id)


async def index_representative(vendor_id: str, summary: str) -> None:
    """写入厂商代表向量（覆盖）——REP = embed(summary)（D9：自然语言全字段 ≤400 字）。"""
    text = summary
    [vec] = await embed([text])
    await asyncio.to_thread(_upsert_rep, vendor_id, text, vec)


async def index_doc_chunks(vendor_id: str, doc_id: str, doc_name: str, page_texts: list[str]) -> int:
    """写入单文档原文块向量（按页切块），返回写入块数。"""
    rows: list[dict] = []
    for page_no, page_text in enumerate(page_texts, start=1):
        for ci, seg in enumerate(chunk_text(page_text)):
            rows.append({
                "id": f"{doc_id}_{page_no}_{ci}",
                "vendor_id": vendor_id,
                "doc_id": doc_id,
                "doc_name": doc_name,
                "page": str(page_no),
                "chunk_text": seg,
                "embedding": None,  # 占位，下面批量嵌入
            })
    if not rows:
        return 0
    texts = [r["chunk_text"] for r in rows]
    vecs = await embed(texts)
    for r, v in zip(rows, vecs):
        r["embedding"] = v
    return await asyncio.to_thread(_insert_chunks, vendor_id, rows)
