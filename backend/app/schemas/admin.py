"""管理员域契约（架构 6.3.4；产品 3.1；路由 03A/03B/03C/03D）。"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import PageData


class AuditRequest(BaseModel):
    action: Literal["pass", "reject"]
    comment: str | None = Field(default=None, description="审核意见（驳回时必填）")


class AuditResponse(BaseModel):
    vendor_id: str
    audit_status: Literal["passed", "rejected"]
    audited_at: datetime


class VendorAuditItem(BaseModel):
    vendor_id: str
    company_name: str
    location: str | None = None
    main_industry: str | None = None
    audit_status: Literal["pending", "passed", "rejected"]
    has_capability: bool = False
    created_at: datetime


class VendorListResponse(PageData[VendorAuditItem]):
    pass


class AdminStatsResponse(BaseModel):
    """数据概览（产品 3.1 AC1 四个统计卡片）。"""

    total_users: int
    total_requests: int
    total_vendors: int
    total_matches: int


class AdminRequestItem(BaseModel):
    request_id: str
    conversation_id: str
    version: int
    structured_demand: dict = Field(default_factory=dict)
    created_at: datetime
    match_count: int = 0


class AdminRequestListResponse(PageData[AdminRequestItem]):
    pass
