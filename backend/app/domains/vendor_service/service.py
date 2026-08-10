"""vendor-service 服务（T2.3）：仅文档录入 → AI 异步解析 → 只读能力档案。

实现以《厂商解析详细设计》为准：upload 保存文档并建档案骨架（version+1）后入队异步解析；
delete 移除文档触发重新解析；get 返回最新档案（audit_status 取厂商审核状态，见 T2.5）。
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.queue import queue
from app.db.models import Vendor, VendorCapability
from app.domains.file_service.storage import storage
from app.schemas.common import err_400, err_404
from app.schemas.vendor import CapabilityOut, VendorOut, VendorRegisterRequest


async def register_vendor(db: AsyncSession, user_id: str, payload: VendorRegisterRequest) -> VendorOut:
    """厂商注册详情（01A / 产品 1.1）：创建 vendors 记录（审核中）。"""
    if payload.credit_code:
        res = await db.execute(select(Vendor).where(Vendor.credit_code == payload.credit_code))
        if res.scalar_one_or_none():
            raise err_400("统一社会信用代码已存在")
    vendor = Vendor(
        user_id=user_id,
        company_name=payload.company_name,
        location=payload.location,
        main_industry=payload.main_industry,
        credit_code=payload.credit_code,
        audit_status="pending",
    )
    db.add(vendor)
    await db.commit()
    await db.refresh(vendor)
    return VendorOut(
        vendor_id=str(vendor.vendor_id),
        company_name=vendor.company_name,
        location=vendor.location,
        main_industry=vendor.main_industry,
        credit_code=vendor.credit_code,
        audit_status=vendor.audit_status,
        created_at=vendor.created_at,
    )


async def _to_out(cap: VendorCapability, audit_status: str) -> CapabilityOut:
    return CapabilityOut(
        capability_id=str(cap.capability_id),
        vendor_id=str(cap.vendor_id),
        structured_tags=cap.structured_tags or {},
        summary_text=cap.summary_text,
        audit_status=audit_status,
        version=cap.version or 1,
        updated_at=cap.updated_at,
        doc_count=cap.doc_count or 0,
        completeness=cap.completeness,
        source_map=cap.source_map or {},
        raw_text=cap.raw_text,
        doc_urls=cap.doc_urls or [],
    )


async def _audit_of(db: AsyncSession, vendor_id) -> str:
    res = await db.execute(select(Vendor.audit_status).where(Vendor.vendor_id == vendor_id))
    return res.scalar_one_or_none() or "pending"


async def _get_cap(db: AsyncSession, vendor_id) -> VendorCapability | None:
    res = await db.execute(select(VendorCapability).where(VendorCapability.vendor_id == vendor_id))
    return res.scalar_one_or_none()


async def get_capability(db: AsyncSession, vendor_id) -> CapabilityOut | None:
    cap = await _get_cap(db, vendor_id)
    if not cap:
        return None
    return await _to_out(cap, await _audit_of(db, vendor_id))


async def upload_capability(db: AsyncSession, vendor_id, documents: list[tuple[bytes, str]]) -> CapabilityOut:
    """保存文档 → 档案骨架（version+1, doc_count, doc_refs）→ 入队异步解析。"""
    doc_refs: list[dict] = []
    for data, name in documents:
        file_id, _url = await storage.save(data, name)
        doc_refs.append({"file_id": file_id, "name": name})

    cap = await _get_cap(db, vendor_id)
    if cap is None:
        cap = VendorCapability(vendor_id=vendor_id, structured_tags={}, doc_urls=[], doc_refs=[])
        db.add(cap)
    cap.version = (cap.version or 0) + 1
    cap.doc_count = len(doc_refs)
    cap.doc_urls = [r["name"] for r in doc_refs]
    cap.doc_refs = doc_refs
    await db.commit()
    await db.refresh(cap)

    await queue.enqueue("parse_capability", {"capability_id": str(cap.capability_id)})
    return await _to_out(cap, await _audit_of(db, vendor_id))


async def delete_document(db: AsyncSession, vendor_id, document_id) -> CapabilityOut:
    """删除能力文档（存储+引用移除）→ 触发重新解析（version+1）。"""
    cap = await _get_cap(db, vendor_id)
    if not cap:
        raise err_404("能力档案不存在")
    refs = list(cap.doc_refs or [])
    target = next((r for r in refs if r.get("file_id") == document_id), None)
    if not target:
        raise err_404("文档不存在")
    await storage.delete(document_id)
    refs = [r for r in refs if r.get("file_id") != document_id]
    cap.doc_refs = refs
    cap.doc_urls = [r["name"] for r in refs]
    cap.doc_count = len(refs)
    cap.version = (cap.version or 0) + 1
    await db.commit()
    await db.refresh(cap)

    await queue.enqueue("parse_capability", {"capability_id": str(cap.capability_id)})
    return await _to_out(cap, await _audit_of(db, vendor_id))
