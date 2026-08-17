"""双轨向量索引（T2.4 / 架构 6.2）。

代表向量 = embed(summary)（D9：自然语言全字段 ≤400 字，1 档案 1 向量，路径A）；
原文块向量 = 块级递归切分（按 token 度量、可跨页合并），携带 vendor_id/doc_id/page(页范围)/chunk_text。

切块规则（2026-08-17 重构，替代原"800 字符固定窗口按页切"）：
  - token 度量：兼容智谱 embedding-2 单条 512 token / 批量 8K token 上限；MAX_TOKENS=400 留余量，
    落库前断言 ≤512。
  - 块级原子：每页按段落拆块（块带页码），相邻块顺序合并成 chunk（可跨页）→ page 存范围 "2" 或 "2~3"。
  - 单个超长块（巨型表格/长段落）用 RecursiveCharacterTextSplitter 按行/句/字符兜底拆分，子块挂同一页码。
重新解析/删除后调用方先删旧向量再写入（保持"仅最新"）。
"""
from __future__ import annotations

import asyncio
import re
from functools import lru_cache

from app.llm.embedding import embed
from app.vector.client import CHUNK_COLLECTION, REP_COLLECTION, get_client

# ---- 切分参数（embedding-2：单条 ≤512 token；保守取 400 留余量）----
MAX_TOKENS = 400
OVERLAP_TOKENS = 50
# 单个超大块（巨型表格/长段落）兜底拆分的分隔符（行→句→词→字符，中文调优；末位空串保证必有切点）
_OVERSIZE_SEPARATORS = ["\n\n", "\n", "。", "；", "！", "？", "，", " ", ""]
# 嵌入单条硬上限（智谱 embedding-2 官方文档）
_EMBED_ITEM_MAX_TOKENS = 512


# ---- token 计数（tiktoken 近似；失败回退字符启发式）----
@lru_cache(maxsize=1)
def _encoding() -> object | None:
    try:
        import tiktoken

        return tiktoken.get_encoding("cl100k_base")
    except Exception:  # noqa: BLE001 - tiktoken 不可用/首次下载失败时回退启发式
        return None


def _count_tokens(text: str) -> int:
    """近似 token 数：中文≈1 字 1 token；英文/其他≈3 字符 1 token（偏保守）。"""
    enc = _encoding()
    if enc is not None:
        try:
            return len(enc.encode(text or ""))
        except Exception:  # noqa: BLE001 - encode 异常回退启发式
            pass
    cjk = len(re.findall(r"[\u4e00-\u9fff\u3040-\u30ff\u3000-\u303f\uff00-\uffef]", text or ""))
    other = max(0, len(text or "") - cjk)
    return cjk + (other + 2) // 3


def _split_blocks(page_text: str) -> list[str]:
    """每页 → 段落块（按空行切；段落保留内部行结构）。"""
    text = (page_text or "").strip()
    if not text:
        return []
    return [seg.strip() for seg in re.split(r"\n\s*\n", text) if seg.strip()]


def _split_oversized(text: str) -> list[str]:
    """单个超长块（巨型表格/长段落）：行→句→词→字符递归拆分，每块 ≤MAX_TOKENS。"""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        separators=_OVERSIZE_SEPARATORS,
        chunk_size=MAX_TOKENS,
        chunk_overlap=OVERLAP_TOKENS,
        length_function=_count_tokens,
        keep_separator=False,
        strip_whitespace=True,
    )
    return splitter.split_text(text)


def chunk_document(page_texts: list[str]) -> list[dict]:
    """整文档块级切分（可跨页合并），返回 [{text, page_start, page_end}]。

    - 原子块 = 段落（带页码）；相邻块顺序合并进 chunk，累计 token ≤ MAX_TOKENS。
    - 块可跨页：上页尾块 + 下页头块进同一 chunk → page_start/page_end 取 min/max。
    - 单块超限 → _split_oversized 按行/句拆，子块挂同一页码。
    - 重叠：flush 时把尾部若干块（合计 ≤ OVERLAP_TOKENS）结转给下一 chunk。
    """
    blocks: list[dict] = []  # {"text", "page"}
    for page_no, page_text in enumerate(page_texts, start=1):
        for seg in _split_blocks(page_text):
            if _count_tokens(seg) > MAX_TOKENS:
                for sub in _split_oversized(seg):
                    sub = sub.strip()
                    if sub:
                        blocks.append({"text": sub, "page": page_no})
            else:
                blocks.append({"text": seg, "page": page_no})

    chunks: list[dict] = []
    cur_blocks: list[dict] = []

    def _flush(with_carry: bool) -> None:
        nonlocal cur_blocks
        if not cur_blocks:
            return
        text = "\n".join(b["text"] for b in cur_blocks).strip()
        if text:
            pages = [b["page"] for b in cur_blocks]
            chunks.append({"text": text, "page_start": min(pages), "page_end": max(pages)})
        # 尾部块（合计 ≤ OVERLAP_TOKENS）结转作下一 chunk 开头
        carry: list[dict] = []
        acc = 0
        for b in reversed(cur_blocks):
            t = _count_tokens(b["text"])
            if acc + t <= OVERLAP_TOKENS:
                carry.insert(0, b)
                acc += t
            else:
                break
        cur_blocks = carry if with_carry else []

    for blk in blocks:
        if cur_blocks and _count_tokens("\n".join(b["text"] for b in cur_blocks)) + _count_tokens(blk["text"]) > MAX_TOKENS:
            _flush(with_carry=True)
        cur_blocks.append(blk)
    _flush(with_carry=False)
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
    """写入单文档原文块向量（块级跨页切分），返回写入块数。"""
    rows: list[dict] = []
    for ci, ch in enumerate(chunk_document(page_texts)):
        # 防御性断言：任何块不得超过 embedding 单条硬上限（512 token）
        if _count_tokens(ch["text"]) > _EMBED_ITEM_MAX_TOKENS:
            raise ValueError(f"chunk exceeds embedding-2 {_EMBED_ITEM_MAX_TOKENS} token limit: {len(ch['text'])} chars")
        page_label = (
            str(ch["page_start"])
            if ch["page_start"] == ch["page_end"]
            else f"{ch['page_start']}~{ch['page_end']}"
        )
        rows.append({
            "id": f"{doc_id}_{ch['page_start']}_{ci}",
            "vendor_id": vendor_id,
            "doc_id": doc_id,
            "doc_name": doc_name,
            "page": page_label,
            "chunk_text": ch["text"],
            "embedding": None,  # 占位，下面批量嵌入
        })
    if not rows:
        return 0
    texts = [r["chunk_text"] for r in rows]
    vecs = await embed(texts)
    for r, v in zip(rows, vecs):
        r["embedding"] = v
    return await asyncio.to_thread(_insert_chunks, vendor_id, rows)
