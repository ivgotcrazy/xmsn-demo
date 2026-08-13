"""精选测试数据（curated）——方案A：10 家高质量厂商 + 10 条行业知识，贴近真实场景测试/优化。

- 数据源：scripts/data/curated_vendors.json + curated_knowledge.json（可评审、可版本化）
- 幂等：按 credit_code / 知识 content 检查，已存在跳过；可重复执行。
- 厂商：VendorCapability.source_type="curated"；能力文档真实写入存储（溯源 preview 可用）+ 双轨向量
- 知识：KnowledgeItem.source="curated:用途"；knowledge_base 向量 upsert
- 运行：python scripts/seed_curated.py（cwd=backend）
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from sqlalchemy import select

from app.db.models import KnowledgeItem, Vendor, VendorCapability
from app.db.session import SessionLocal
from app.domains.file_service.storage import storage
from app.llm.embedding import embed
from app.vector import indexer as vector
from app.vector.client import KNOWLEDGE_COLLECTION, get_client

DATA = Path(__file__).resolve().parent / "data"


def _load(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


async def _seed_vendors(db) -> None:
    data = _load("curated_vendors.json")
    created = 0
    for item in data["vendors"]:
        vd = item["vendor"]
        cap = item["capability"]
        exists = (await db.execute(select(Vendor).where(Vendor.credit_code == vd["credit_code"]))).scalar_one_or_none()
        if exists:
            continue
        vendor = Vendor(**vd)
        db.add(vendor)
        await db.flush()
        # 能力文档真实写入存储（溯源 preview 可用，不再 404）
        file_id, _url = await storage.save(cap["doc"].encode("utf-8"), f"{vd['company_name']}能力介绍.md")
        vcap = VendorCapability(
            vendor_id=vendor.vendor_id,
            structured_tags=cap["structured_tags"],
            summary_text=cap["summary_text"],
            completeness=1.0,
            source_type="curated",
            version=1,
            doc_count=1,
            doc_refs=[{"name": f"{vd['company_name']}能力介绍.md", "file_id": file_id}],
        )
        db.add(vcap)
        await db.flush()
        # 双轨向量（代表向量 + 原文块溯源）
        await vector.index_representative(str(vendor.vendor_id), cap["structured_tags"], cap["summary_text"])
        await vector.index_doc_chunks(str(vendor.vendor_id), file_id,
                                      f"{vd['company_name']}能力介绍.md", [cap["doc"]])
        created += 1
    await db.commit()
    print(f"  curated vendors created: {created}")


async def _seed_knowledge(db) -> None:
    data = _load("curated_knowledge.json")
    created = 0
    for k in data["knowledge"]:
        exists = (await db.execute(select(KnowledgeItem).where(KnowledgeItem.content == k["content"]))).scalar_one_or_none()
        if exists:
            continue
        item = KnowledgeItem(content=k["content"], category=k["category"], industry=k["industry"],
                             source=f"curated:{k['usage']}")
        db.add(item)
        await db.flush()
        created += 1
    await db.commit()
    # 全量知识向量 upsert（与 seed_data 一致，幂等）
    rows = (await db.execute(select(KnowledgeItem))).scalars().all()
    texts = [r.content for r in rows]
    vecs = await embed(texts)
    client = get_client()
    client.upsert(KNOWLEDGE_COLLECTION, data=[
        {"id": f"k_{r.knowledge_id}", "knowledge_id": str(r.knowledge_id),
         "category": r.category, "industry": r.industry, "embedding": v}
        for r, v in zip(rows, vecs)
    ])
    print(f"  curated knowledge created: {created}（库内共 {len(rows)} 条，向量已 upsert）")


async def seed() -> None:
    async with SessionLocal() as db:
        print("=== 精选测试数据 ===")
        await _seed_vendors(db)
        await _seed_knowledge(db)
        print("=== 完成 ===")


if __name__ == "__main__":
    asyncio.run(seed())
