"""admin-service 服务（T2.5）：审核流转 + 厂商列表 + 审计日志。

实现以《产品需求设计》1.6 / 4.3 为准：审核通过/驳回写 vendors.audit_status + admin_logs
（append-only 审计）；厂商列表支持按审核状态筛选、分页、含是否有能力档案标记。
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AdminLog, Vendor, VendorCapability
from app.schemas.admin import AuditResponse, VendorAuditItem, VendorListResponse
from app.schemas.common import err_400, err_404


async def audit_vendor(db: AsyncSession, vendor_id: str, action: str, comment: str | None, admin_user_id: str) -> AuditResponse:
    """一键审核（pass/reject）：更新厂商审核状态 + 写审计日志。"""
    vid = uuid.UUID(vendor_id)
    res = await db.execute(select(Vendor).where(Vendor.vendor_id == vid))
    vendor = res.scalar_one_or_none()
    if not vendor:
        raise err_404("厂商不存在")
    if action == "reject" and not comment:
        raise err_400("驳回需填写审核意见")
    vendor.audit_status = "passed" if action == "pass" else "rejected"
    db.add(
        AdminLog(
            admin_user_id=uuid.UUID(admin_user_id) if admin_user_id else None,
            action=f"audit_{action}",
            target_type="vendor",
            target_id=vendor_id,
            detail={"comment": comment or ""},
        )
    )
    await db.commit()
    return AuditResponse(vendor_id=vendor_id, audit_status=vendor.audit_status, audited_at=datetime.utcnow())


async def list_vendors(db: AsyncSession, audit_status: str | None, page: int, page_size: int) -> VendorListResponse:
    """厂商列表（按审核状态筛选、分页）；标记是否已有能力档案。"""
    filters = []
    if audit_status:
        filters.append(Vendor.audit_status == audit_status)

    total = (
        await db.execute(select(func.count()).select_from(Vendor).where(*filters))
    ).scalar_one()

    q = select(Vendor).where(*filters).order_by(Vendor.created_at.desc())
    rows = list((await db.execute(q.offset((page - 1) * page_size).limit(page_size))).scalars().all())

    cap_ids: set[uuid.UUID] = set()
    if rows:
        ids = [r.vendor_id for r in rows]
        cres = await db.execute(select(VendorCapability.vendor_id).where(VendorCapability.vendor_id.in_(ids)))
        cap_ids = set(cres.scalars().all())

    items = [
        VendorAuditItem(
            vendor_id=str(v.vendor_id),
            company_name=v.company_name,
            location=v.location,
            main_industry=v.main_industry,
            audit_status=v.audit_status,
            has_capability=v.vendor_id in cap_ids,
            created_at=v.created_at,
        )
        for v in rows
    ]
    return VendorListResponse(list=items, total=total, page=page, page_size=page_size)
