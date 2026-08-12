"""后台任务：消费 TaskQueue（能力解析/匹配解释/画像构建）。M2 起填充。

任务经 core/queue.TaskQueue 调度（进程内实现，ADR-09）；任务幂等，
解析失败记录日志（可重新上传触发重试）。
"""
from __future__ import annotations

import logging

from sqlalchemy import select

from app.db.models import BuyerRequest, MatchResult, VendorCapability
from app.db.session import SessionLocal
from app.domains.file_service.parser import extract_pages
from app.domains.file_service.storage import storage
from app.domains.match_service import explain, retriever as match_retriever
from app.domains.vendor_service import extractor, validator
from app.vector import indexer as vector

logger = logging.getLogger("xmsn.worker")


async def handle_task(task: str, payload: dict) -> None:
    if task == "parse_capability":
        await _parse_capability(payload["capability_id"])
    elif task == "match_explain":
        await _explain_match(payload["match_id"])
    else:
        logger.warning("unknown task: %s", task)


async def _explain_match(match_id: str) -> None:
    """M5：对单个匹配结果异步生成解释（T5.2）——LLM 判定三组 + ai_comment + source 溯源（T5.3）。

    失败/非法时不覆盖打分判定（降级保留三组）。
    """
    import uuid

    async with SessionLocal() as db:
        mr = await db.get(MatchResult, uuid.UUID(match_id))
        if not mr:
            return
        req = await db.get(BuyerRequest, mr.request_id)
        if not req:
            return
        cap = (await db.execute(
            select(VendorCapability).where(VendorCapability.vendor_id == mr.vendor_id)
        )).scalar_one_or_none()
        if not cap:
            return
        demand = req.structured_demand or {}
        tags = cap.structured_tags or {}
        # 溯源：检索该厂商 doc_chunks 中与需求相关的原文块（T5.3）
        query = match_retriever.demand_embedding_text(demand)
        chunks = await match_retriever.retrieve_chunks(str(cap.vendor_id), query, top_k=5)
        # 兼容历史 doc_chunks（doc_id 存文件名）：按 doc_refs 映射为 storage file_id（可 preview）
        name2id = {r.get("name"): r.get("file_id") for r in (cap.doc_refs or [])}
        for ch in chunks:
            ch["doc_id"] = name2id.get(ch.get("doc_name"), ch.get("doc_id"))
        # LLM 解释
        result = await explain.generate(demand, tags, chunks)
        if not result["params"]:
            logger.info("explain empty for %s (保留打分判定)", match_id)
            return
        matched = [p for p in result["params"] if p["verdict"] == "matched"]
        partial = []
        unmatched = []
        for p in result["params"]:
            if p["verdict"] == "matched":
                matched.append(p)
            elif p["verdict"] in ("partial", "missing"):
                # missing（厂商未声明）语义并入 partial（需协商）；契约 MatchParam 仅 3 值
                partial.append({**p, "verdict": "partial"})
            elif p["verdict"] == "unmatched":
                unmatched.append(p)
        mr.matched_params = matched
        mr.partial_params = partial
        mr.unmatched_params = unmatched
        mr.ai_comment = result["ai_comment"]
        await db.commit()
        logger.info("explain done: %s (matched=%d partial=%d unmatched=%d)",
                    match_id, len(matched), len(partial), len(unmatched))


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

