"""管理员域契约（架构 6.3.4；产品 3.1；路由 03A/03B/03C/03D）。"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import PageData
from app.schemas.match import MatchRun


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
    """需求匹配列表项（行=需求档案=一次匹配；run 内嵌匹配实体，含物化统计）。"""

    request_id: str
    conversation_id: str
    version: int
    structured_demand: dict = Field(default_factory=dict)
    buyer_phone: str = ""
    run: MatchRun | None = None
    created_at: datetime


class AdminRequestListResponse(PageData[AdminRequestItem]):
    pass


class BuyerItem(BaseModel):
    """买家列表项（users 表 role='buyer' + 关联统计，一次性返回避免逐行联查）。"""

    user_id: str
    phone: str
    email: str | None = None
    status: Literal["active", "disabled"] = "active"
    conversation_count: int = 0
    request_count: int = 0
    last_active_at: datetime | None = None
    created_at: datetime


class BuyerListResponse(PageData[BuyerItem]):
    pass


class AdminLogItem(BaseModel):
    """事件日志项（admin_logs 审计：管理员操作/登录/导出等，append-only）。"""

    log_id: str
    action: str
    action_label: str = ""
    target_type: str | None = None
    target_id: str | None = None
    admin_name: str = ""
    detail: dict = Field(default_factory=dict)
    created_at: datetime


class AdminLogListResponse(PageData[AdminLogItem]):
    pass


# ---- 领域知识管理（T6.1，M6 后台：增/删/列 + 向量化） ----

class KnowledgeCreateRequest(BaseModel):
    content: str = Field(..., min_length=4, max_length=2000, description="知识文本")
    category: str | None = Field(default="terminology", description="terminology/trap/dependency/faq")
    industry: str | None = Field(default=None, description="适用行业（如机顶盒；空=通用）")


class KnowledgeItemOut(BaseModel):
    knowledge_id: str
    content: str
    category: str | None = None
    industry: str | None = None
    source: str | None = None
    created_at: datetime


class KnowledgeListResponse(PageData[KnowledgeItemOut]):
    pass


class KnowledgeDeleteResponse(BaseModel):
    knowledge_id: str
    deleted: bool = True
