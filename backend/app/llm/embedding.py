"""Embedding 统一封装（智谱 embedding-2，1024 维；OpenAI 兼容 SDK）。

DeepSeek 无 Embedding 端点，故主力用智谱 embedding-2（可换 bge-m3，仅换实现）。
T2.4 双轨向量化使用；维度见 settings.embedding_dim。
"""
from __future__ import annotations

from openai import AsyncOpenAI

from app.core.config import settings

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.embedding_api_key,
            base_url=settings.embedding_base_url,
            timeout=60.0,
        )
    return _client


async def embed(texts: list[str]) -> list[list[float]]:
    """批量文本 → 向量（保持输入顺序）。"""
    if not settings.embedding_api_key:
        raise RuntimeError("embedding_api_key 未配置")
    if not texts:
        return []
    resp = await _get_client().embeddings.create(model=settings.embedding_model, input=texts)
    return [d.embedding for d in resp.data]
