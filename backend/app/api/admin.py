"""管理员接口（契约 6.3.4 + 产品 3.1；路由 03A-03D，需 admin 角色）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminUser
from app.db.session import get_session
from app.domains.admin_service import service as admin_service
from app.schemas.admin import (
    AdminLogListResponse,
    AdminRequestListResponse,
    AdminStatsResponse,
    AuditRequest,
    AuditResponse,
    BuyerListResponse,
    VendorListResponse,
)
from app.schemas.common import ApiResponse, err_501

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/vendors/{vendor_id}/audit", response_model=ApiResponse[AuditResponse], summary="厂商能力档案审核")
async def audit_vendor(
    vendor_id: str,
    payload: AuditRequest,
    admin: AdminUser,
    db: AsyncSession = Depends(get_session),
) -> ApiResponse[AuditResponse]:
    return ApiResponse(data=await admin_service.audit_vendor(db, vendor_id, payload.action, payload.comment, admin.user_id))


@router.get("/vendors", response_model=ApiResponse[VendorListResponse], summary="厂商列表（按审核状态筛选，分页）")
async def list_vendors(
    admin: AdminUser,
    audit_status: str | None = Query(default=None, description="pending/passed/rejected"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
) -> ApiResponse[VendorListResponse]:
    return ApiResponse(data=await admin_service.list_vendors(db, audit_status, page, page_size))


@router.get("/stats", response_model=ApiResponse[AdminStatsResponse], summary="数据概览（四个统计卡片）")
async def stats(admin: AdminUser) -> ApiResponse[AdminStatsResponse]:
    raise err_501("契约层占位：M2 实现")


@router.get("/requests", response_model=ApiResponse[AdminRequestListResponse], summary="需求与匹配查看（分页）")
async def list_requests(
    admin: AdminUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ApiResponse[AdminRequestListResponse]:
    raise err_501("契约层占位：M3 实现")


@router.get("/buyers", response_model=ApiResponse[BuyerListResponse], summary="买家列表（搜索/状态筛选，分页）")
async def list_buyers(
    admin: AdminUser,
    keyword: str | None = Query(default=None, description="手机号/邮箱关键词"),
    status: str | None = Query(default=None, description="active/disabled"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ApiResponse[BuyerListResponse]:
    raise err_501("契约层占位：M3 实现")


@router.get("/logs", response_model=ApiResponse[AdminLogListResponse], summary="事件日志（审计，按动作筛选，分页）")
async def list_logs(
    admin: AdminUser,
    action: str | None = Query(default=None, description="动作类型"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ApiResponse[AdminLogListResponse]:
    raise err_501("契约层占位：M3 实现")
