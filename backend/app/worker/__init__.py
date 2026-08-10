"""后台任务：消费 TaskQueue（能力解析/匹配解释/画像构建）。M2 起填充。

任务经 core/queue.TaskQueue 调度（进程内实现，ADR-09）；任务幂等，
解析失败记录日志（可重新上传触发重试）。
"""
from __future__ import annotations

import logging

from sqlalchemy import select

from app.db.models import VendorCapability
from app.db.session import SessionLocal
from app.domains.file_service.parser import extract_pages
from app.domains.file_service.storage import storage
from app.domains.vendor_service import extractor, validator
from app.vector import indexer as vector

logger = logging.getLogger("xmsn.worker")


async def handle_task(task: str, payload: dict) -> None:
    if task == "parse_capability":
        await _parse_capability(payload["capability_id"])
    else:
        logger.warning("unknown task: %s", task)


async def _parse_capability(capability_id: str) -> None:
    """读取文档 → 解析文本 → LLM 提取 → 校验落库 → 双轨向量化。"""
    async with SessionLocal() as db:
        res = await db.execute(select(VendorCapability).where(VendorCapability.capability_id == capability_id))
        cap = res.scalar_one_or_none()
        if not cap:
            return
        docs: list[tuple[dict, list[str]]] = []
        doc_texts: list[str] = []
        for ref in cap.doc_refs or []:
            try:
                data = await storage.read(ref["file_id"])
                pages = extract_pages(data, ref["name"])
            except Exception:  # noqa: BLE001 - 单文档失败不阻断
                logger.warning("doc parse failed: %s", ref.get("file_id"))
                continue
            docs.append((ref, pages))
            doc_texts.append(f"【{ref['name']}】\n" + "\n".join(pages))
        document_text = "\n\n".join(doc_texts)
        try:
            extracted = await extractor.extract(document_text)
            tags, completeness, source_map, summary = validator.validate(extracted)
            cap.structured_tags = tags
            cap.completeness = completeness
            cap.source_map = source_map
            cap.summary_text = summary
            cap.raw_text = document_text[:4000]
            await db.commit()
            logger.info("capability parsed: %s completeness=%s", capability_id, completeness)
        except Exception as exc:  # noqa: BLE001 - 解析失败记录，前端可重试/重传
            logger.error("capability parse failed: %s %s", capability_id, exc)
            return

        # 双轨向量化（解析成功后；重解析先删旧向量，保持"仅最新"）
        vendor_id = str(cap.vendor_id)
        try:
            await vector.delete_vendor_vectors(vendor_id)
            await vector.index_representative(vendor_id, tags, summary)
            for ref, pages in docs:
                await vector.index_doc_chunks(vendor_id, ref["file_id"], ref["name"], pages)
            logger.info("capability indexed: %s", capability_id)
        except Exception as exc:  # noqa: BLE001 - 索引失败不阻断（可重新上传）
            logger.error("vector index failed: %s %s", capability_id, exc)

