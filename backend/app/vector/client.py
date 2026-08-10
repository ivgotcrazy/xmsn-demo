"""Milvus 客户端与集合管理（T2.4 / 架构 6.2；T3.4 knowledge_base）。

集合：
- vendor_representative：厂商级代表向量（1 档案=1 向量，通道A 语义匹配）
- doc_chunks：原文块向量（vendor_id/doc_id/doc_name/page/chunk_text，引用溯源）
- knowledge_base：领域知识文本向量（knowledge_id/category/industry，对话Agent RAG）
Embedding 维度见 settings.embedding_dim（智谱 embedding-2 = 1024）。

说明：pymilvus 2.5.4 的 AsyncMilvusClient API 不完整（缺 has_collection/prepare_index_params），
故用同步 MilvusClient，异步侧经 asyncio.to_thread 包装（调用量小，PoC 可接受）。
"""
from __future__ import annotations

import asyncio
import logging

from pymilvus import DataType, MilvusClient

from app.core.config import settings

logger = logging.getLogger("xmsn.vector")

REP_COLLECTION = "vendor_representative"
CHUNK_COLLECTION = "doc_chunks"
KNOWLEDGE_COLLECTION = "knowledge_base"

_client: MilvusClient | None = None


def get_client() -> MilvusClient:
    global _client
    if _client is None:
        _client = MilvusClient(uri=f"http://{settings.milvus_host}:{settings.milvus_port}")
    return _client


def _ensure_collections_sync() -> None:
    client = get_client()
    # collection -> 额外 VARCHAR 字段（id/embedding 由公共部分统一添加）
    specs = {
        REP_COLLECTION: [("vendor_id", "varchar"), ("text", "text")],
        CHUNK_COLLECTION: [("vendor_id", "varchar"), ("doc_id", "varchar"), ("doc_name", "varchar"), ("page", "varchar"), ("chunk_text", "chunk")],
        KNOWLEDGE_COLLECTION: [("knowledge_id", "varchar"), ("category", "varchar"), ("industry", "varchar")],
    }
    for name, fields in specs.items():
        if client.has_collection(name):
            continue
        schema = client.create_schema(auto_id=False)
        schema.add_field("id", DataType.VARCHAR, max_length=64, is_primary=True)
        for fname, _ftype in fields:
            schema.add_field(fname, DataType.VARCHAR, max_length=16384)
        schema.add_field("embedding", DataType.FLOAT_VECTOR, dim=settings.embedding_dim)
        index_params = client.prepare_index_params()
        index_params.add_index(field_name="embedding", index_type="AUTOINDEX", metric_type="COSINE")
        client.create_collection(name, schema=schema, index_params=index_params)
        logger.info("milvus collection ensured: %s", name)


async def ensure_collections() -> None:
    """幂等创建双轨集合（含向量索引，COSINE）。"""
    await asyncio.to_thread(_ensure_collections_sync)
