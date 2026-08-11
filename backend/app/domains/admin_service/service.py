"""admin-service 服务（T2.5）：审核流转 + 厂商列表 + 审计日志。

实现以《产品需求设计》1.6 / 4.3 为准：审核通过/驳回写 vendors.audit_status + admin_logs
（append-only 审计）；厂商列表支持按审核状态筛选、分页、含是否有能力档案标记。
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AdminLog, Vendor, VendorCapability
from app.schemas.admin import (
    AdminLogItem,
    AdminLogListResponse,
    AdminRequestItem,
    AdminRequestListResponse,
    AdminStatsResponse,
    AuditResponse,
    BuyerItem,
    BuyerListResponse,
    KnowledgeDeleteResponse,
    KnowledgeItemOut,
    KnowledgeListResponse,
    VendorAuditItem,
    VendorListResponse,
)
from app.schemas.common import err_400, err_404

logger = logging.getLogger("xmsn.admin")


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


# ---------- M6：数据概览 / 需求查看 / 买家列表 / 审计日志 ----------

_ACTION_LABEL = {
    "login": "管理员登录",
    "audit_pass": "厂商审核通过",
    "audit_reject": "厂商审核驳回",
    "knowledge_add": "知识新增",
    "knowledge_delete": "知识删除",
    "export": "数据导出",
    "config_change": "配置变更",
}


async def stats(db: AsyncSession) -> AdminStatsResponse:
    """数据概览（03B 四个统计卡片）。"""
    from app.db.models import BuyerRequest, MatchRun, User

    total_users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    total_vendors = (await db.execute(select(func.count()).select_from(Vendor))).scalar_one()
    total_requests = (
        await db.execute(select(func.count()).select_from(BuyerRequest).where(BuyerRequest.deleted_at.is_(None)))
    ).scalar_one()
    total_matches = (await db.execute(select(func.count()).select_from(MatchRun))).scalar_one()
    return AdminStatsResponse(total_users=total_users, total_vendors=total_vendors,
                              total_requests=total_requests, total_matches=total_matches)


async def list_requests(db: AsyncSession, page: int, page_size: int) -> AdminRequestListResponse:
    """需求与匹配查看（03C）：行=需求档案，内嵌匹配实体（含物化统计）。"""
    from app.db.models import BuyerRequest, MatchRun, User

    total = (
        await db.execute(select(func.count()).select_from(BuyerRequest).where(BuyerRequest.deleted_at.is_(None)))
    ).scalar_one()
    reqs = list((await db.execute(
        select(BuyerRequest).where(BuyerRequest.deleted_at.is_(None))
        .order_by(BuyerRequest.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all())

    # 买家手机号 + 匹配实体（一次性联查）
    uids = {r.user_id for r in reqs}
    phones: dict = {}
    if uids:
        ures = await db.execute(select(User.user_id, User.phone).where(User.user_id.in_(uids)))
        phones = {str(u): p for u, p in ures.all()}
    rids = [r.request_id for r in reqs]
    runs: dict = {}
    if rids:
        rres = await db.execute(select(MatchRun).where(MatchRun.request_id.in_(rids)))
        runs = {str(r.request_id): r for r in rres.scalars().all()}

    from app.schemas.match import MatchRun as MatchRunSchema

    items = [
        AdminRequestItem(
            request_id=str(r.request_id),
            conversation_id=str(r.conversation_id),
            version=r.version,
            structured_demand=r.structured_demand or {},
            buyer_phone=phones.get(str(r.user_id), ""),
            run=(MatchRunSchema(
                run_id=str(run.run_id), request_id=str(run.request_id), status=run.status,
                total_vendors=run.total_vendors, best_score=run.best_score,
                computation_time_ms=run.computation_time_ms, created_at=run.created_at,
            ) if (run := runs.get(str(r.request_id))) else None),
            created_at=r.created_at,
        )
        for r in reqs
    ]
    return AdminRequestListResponse(list=items, total=total, page=page, page_size=page_size)


async def list_buyers(db: AsyncSession, keyword: str | None, status: str | None,
                      page: int, page_size: int) -> BuyerListResponse:
    """买家列表（role='buyer' + 会话/需求统计，一次性聚合避免逐行联查）。"""
    from app.db.models import BuyerRequest, Conversation, User

    filters = [User.role == "buyer"]
    if keyword:
        kw = f"%{keyword}%"
        filters.append(User.phone.ilike(kw) | (User.email.ilike(kw) if User.email else False))
    if status == "disabled":
        filters.append(User.status == "disabled")

    total = (await db.execute(select(func.count()).select_from(User).where(*filters))).scalar_one()
    users = list((await db.execute(
        select(User).where(*filters).order_by(User.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).scalars().all())

    uids = {u.user_id for u in users}
    conv_counts: dict = {}
    req_counts: dict = {}
    if uids:
        cc = await db.execute(select(Conversation.user_id, func.count()).where(
            Conversation.user_id.in_(uids), Conversation.deleted_at.is_(None)).group_by(Conversation.user_id))
        conv_counts = {str(u): n for u, n in cc.all()}
        rc = await db.execute(select(BuyerRequest.user_id, func.count()).where(
            BuyerRequest.user_id.in_(uids), BuyerRequest.deleted_at.is_(None)).group_by(BuyerRequest.user_id))
        req_counts = {str(u): n for u, n in rc.all()}

    items = [
        BuyerItem(
            user_id=str(u.user_id), phone=u.phone or "", email=getattr(u, "email", None),
            status="disabled" if u.status == "disabled" else "active",
            conversation_count=conv_counts.get(str(u.user_id), 0),
            request_count=req_counts.get(str(u.user_id), 0),
            last_active_at=u.updated_at,
            created_at=u.created_at,
        )
        for u in users
    ]
    return BuyerListResponse(list=items, total=total, page=page, page_size=page_size)


async def list_logs(db: AsyncSession, action: str | None, page: int, page_size: int) -> AdminLogListResponse:
    """审计日志（append-only；联管理员手机号 + action 中文标签）。"""
    from app.db.models import User

    filters = []
    if action:
        filters.append(AdminLog.action == action)
    total = (await db.execute(select(func.count()).select_from(AdminLog).where(*filters))).scalar_one()
    logs = list((await db.execute(
        select(AdminLog).where(*filters).order_by(AdminLog.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).scalars().all())

    admin_names: dict = {}
    auids = {l.admin_user_id for l in logs if l.admin_user_id}
    if auids:
        ares = await db.execute(select(User.user_id, User.phone).where(User.user_id.in_(auids)))
        admin_names = {str(u): p or "" for u, p in ares.all()}

    items = [
        AdminLogItem(
            log_id=str(l.log_id), action=l.action or "",
            action_label=_ACTION_LABEL.get(l.action or "", l.action or ""),
            target_type=l.target_type, target_id=l.target_id,
            admin_name=admin_names.get(str(l.admin_user_id), "") if l.admin_user_id else "",
            detail=l.detail or {}, created_at=l.created_at,
        )
        for l in logs
    ]
    return AdminLogListResponse(list=items, total=total, page=page, page_size=page_size)


# ---------- M6：领域知识管理（T6.1，增/删/列 + 向量化 knowledge_base） ----------

async def list_knowledge(db: AsyncSession, page: int, page_size: int) -> KnowledgeListResponse:
    """知识列表（分页）。"""
    from app.db.models import KnowledgeItem

    total = (await db.execute(select(func.count()).select_from(KnowledgeItem))).scalar_one()
    rows = list((await db.execute(
        select(KnowledgeItem).order_by(KnowledgeItem.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).scalars().all())
    items = [
        KnowledgeItemOut(
            knowledge_id=str(k.knowledge_id), content=k.content,
            category=k.category, industry=k.industry, source=k.source, created_at=k.created_at,
        )
        for k in rows
    ]
    return KnowledgeListResponse(list=items, total=total, page=page, page_size=page_size)


async def create_knowledge(db: AsyncSession, content: str, category: str | None,
                           industry: str | None, admin_user_id: str) -> KnowledgeItemOut:
    """新增知识：落库 knowledge_items + 向量化写入 knowledge_base（增量添加，3.4）。"""
    from app.db.models import KnowledgeItem
    from app.llm.embedding import embed
    from app.vector.client import KNOWLEDGE_COLLECTION, get_client

    item = KnowledgeItem(content=content, category=category or "terminology",
                         industry=industry, source="admin")
    db.add(item)
    await db.commit()
    await db.refresh(item)

    try:
        [vec] = await embed([item.content])
        get_client().upsert(KNOWLEDGE_COLLECTION, data=[{
            "id": f"k_{item.knowledge_id}", "knowledge_id": str(item.knowledge_id),
            "category": item.category, "industry": item.industry, "embedding": vec,
        }])
        item.embedding_id = f"k_{item.knowledge_id}"
        await db.commit()
    except Exception as exc:  # noqa: BLE001 - 向量化失败不阻断落库（可重试）
        logger.warning("knowledge vectorize failed: %s", exc)

    db.add(AdminLog(admin_user_id=uuid.UUID(admin_user_id), action="knowledge_add",
                    target_type="knowledge", target_id=str(item.knowledge_id),
                    detail={"category": item.category, "industry": item.industry}))
    await db.commit()
    return KnowledgeItemOut(
        knowledge_id=str(item.knowledge_id), content=item.content,
        category=item.category, industry=item.industry, source=item.source, created_at=item.created_at,
    )


async def delete_knowledge(db: AsyncSession, knowledge_id: str, admin_user_id: str) -> KnowledgeDeleteResponse:
    """删除知识：删向量（knowledge_base）+ 物理删行。"""
    from app.db.models import KnowledgeItem
    from app.vector.client import KNOWLEDGE_COLLECTION, get_client

    kid = uuid.UUID(knowledge_id)
    item = await db.get(KnowledgeItem, kid)
    if not item:
        raise err_404("知识不存在")
    try:
        get_client().delete(KNOWLEDGE_COLLECTION, filter=f'knowledge_id == "{knowledge_id}"')
    except Exception:  # noqa: BLE001
        pass
    await db.delete(item)
    db.add(AdminLog(admin_user_id=uuid.UUID(admin_user_id), action="knowledge_delete",
                    target_type="knowledge", target_id=knowledge_id, detail={}))
    await db.commit()
    return KnowledgeDeleteResponse(knowledge_id=knowledge_id)
