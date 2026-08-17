"""Embedding 统一封装（智谱 embedding-2，1024 维；OpenAI 兼容 SDK）。

DeepSeek 无 Embedding 端点，故主力用智谱 embedding-2（可换 bge-m3，仅换实现）。
T2.4 双轨向量化使用；维度见 settings.embedding_dim。

2026-08-17：按官方限制分批——单条 ≤512 token、单请求数组总长 ≤8K token。
embed() 对入参按累计 token 分批发送（保序），避免长文档一次请求超 8K 被截断。
"""
from __future__ import annotations

import re
from functools import lru_cache

from openai import AsyncOpenAI

from app.core.config import settings

_client: AsyncOpenAI | None = None

# 智谱 embedding-2 单请求数组总长 ≤8K token，留余量取 6000
_EMBED_BATCH_MAX_TOKENS = 6000


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.embedding_api_key,
            base_url=settings.embedding_base_url,
            timeout=60.0,
        )
    return _client


@lru_cache(maxsize=1)
def _encoding() -> object | None:
    try:
        import tiktoken

        return tiktoken.get_encoding("cl100k_base")
    except Exception:  # noqa: BLE001 - tiktoken 不可用/下载失败时回退启发式
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


async def _embed_batch(texts: list[str]) -> list[list[float]]:
    resp = await _get_client().embeddings.create(model=settings.embedding_model, input=texts)
    # 智谱可能按输入顺序返回；按 index 排序保序（兼容顺序错乱）
    ordered = sorted(resp.data, key=lambda d: d.index)
    return [d.embedding for d in ordered]


async def embed(texts: list[str]) -> list[list[float]]:
    """批量文本 → 向量（保持输入顺序；按 token 分批，单批 ≤8K 上限）。"""
    if not settings.embedding_api_key:
        raise RuntimeError("embedding_api_key 未配置")
    if not texts:
        return []

    batches: list[list[str]] = []
    cur: list[str] = []
    cur_tokens = 0
    for t in texts:
        n = _count_tokens(t)
        if cur and cur_tokens + n > _EMBED_BATCH_MAX_TOKENS:
            batches.append(cur)
            cur = []
            cur_tokens = 0
        cur.append(t)
        cur_tokens += n
    if cur:
        batches.append(cur)

    out: list[list[float]] = []
    for batch in batches:
        out.extend(await _embed_batch(batch))
    return out
