"""数据模型（对齐系统架构设计 6.1 + 用户画像设计 3 + 代理详细设计 3.5 事实数据）。

包含：users / vendors / vendor_capabilities / conversations / buyer_requests /
user_profiles / profile_schemas / match_results / knowledge_items / admin_logs /
llm_call_logs / conversation_events
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('vendor','buyer','admin')", name="ck_users_role"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    # 手机号/邮箱至少其一（支持纯邮箱注册）
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Vendor(Base):
    __tablename__ = "vendors"
    __table_args__ = (
        CheckConstraint("audit_status IN ('pending','passed','rejected')", name="ck_vendors_audit"),
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    company_name: Mapped[str] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    main_industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    credit_code: Mapped[str | None] = mapped_column(String(18), unique=True, nullable=True)
    license_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    audit_status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VendorCapability(Base):
    __tablename__ = "vendor_capabilities"
    __table_args__ = (
        Index("idx_vendor_tags_gin", "structured_tags", postgresql_using="gin"),
    )
    capability_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    vendor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("vendors.vendor_id"))
    structured_tags: Mapped[dict] = mapped_column(JSONB, default=dict)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 档案版本（每次重新解析增/删文档 +1）、基于文档数、完备度、字段级溯源+置信度
    version: Mapped[int] = mapped_column(Integer, default=1)
    doc_count: Mapped[int] = mapped_column(Integer, default=0)
    completeness: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_map: Mapped[dict] = mapped_column(JSONB, default=dict)
    # 文档引用 [{file_id, name}]：增删文档触发重新解析（version+1）
    doc_refs: Mapped[list] = mapped_column(JSONB, default=list)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    doc_urls: Mapped[list] = mapped_column(ARRAY(Text), default=list)
    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    rep_embedding_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint("status IN ('active','confirmed','closed')", name="ck_conversations_status"),
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    status: Mapped[str] = mapped_column(String(20), default="active")
    # 会话标题（一会话一产品）：聚焦的产品类型名，未确定时为「新会话」
    title: Mapped[str] = mapped_column(String(100), default="新会话")
    conversation_history: Mapped[list] = mapped_column(JSONB, default=list)
    current_slots: Mapped[dict] = mapped_column(JSONB, default=dict)
    # 逻辑删除标记（数据有挖掘价值，仅从可见列表移除）
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class BuyerRequest(Base):
    __tablename__ = "buyer_requests"
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.conversation_id")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    structured_demand: Mapped[dict] = mapped_column(JSONB, default=dict)
    embedding_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="confirmed")
    # 逻辑删除标记（需求档案/匹配有挖掘价值，仅从可见列表移除）
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProfileSchema(Base):
    """画像 Schema 定义（用户画像设计 3.1）：加维度=加行，零 DDL。"""

    __tablename__ = "profile_schemas"
    __table_args__ = (
        CheckConstraint("scope IN ('base','industry')", name="ck_profile_schemas_scope"),
        Index("uq_profile_schemas_version_scope_industry", "schema_version", "scope", "industry", unique=True),
    )
    schema_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    schema_version: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(100))
    scope: Mapped[str] = mapped_column(String(20), default="base")
    industry: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dimensions: Mapped[list] = mapped_column(JSONB, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserProfile(Base):
    """用户画像（用户画像设计 3.2）：Schema 驱动 + 版本化。"""

    __tablename__ = "user_profiles"
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), unique=True)
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    profile_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    confidence: Mapped[dict] = mapped_column(JSONB, default=dict)
    total_requests: Mapped[int] = mapped_column(Integer, default=0)
    last_request_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MatchRun(Base):
    """匹配实体 = 一次匹配行为（1:1 锚定需求档案）。物化统计，查询免实时计算。

    同需求点集重新匹配 = 生成新需求档案 + 新匹配实体；故 request_id 当前 1:1 唯一。
    """

    __tablename__ = "match_runs"
    __table_args__ = (
        CheckConstraint("status IN ('running','done','empty')", name="ck_match_runs_status"),
        Index("uq_match_runs_request", "request_id", unique=True),
    )
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("buyer_requests.request_id")
    )
    status: Mapped[str] = mapped_column(String(20), default="done")
    total_vendors: Mapped[int] = mapped_column(Integer, default=0)
    best_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    computation_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MatchResult(Base):
    __tablename__ = "match_results"
    __table_args__ = (
        CheckConstraint("match_source IN ('llm','rule','hybrid')", name="ck_match_results_source"),
        Index("idx_match_request", "request_id"),
        Index("idx_match_vendor", "vendor_id"),
    )
    match_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("match_runs.run_id"), nullable=False
    )
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("buyer_requests.request_id"))
    vendor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("vendors.vendor_id"))
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    semantic_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    param_hit_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    critical_fail: Mapped[bool] = mapped_column(Boolean, default=False)
    match_source: Mapped[str] = mapped_column(String(10), default="llm")
    matched_params: Mapped[list] = mapped_column(JSONB, default=list)
    partial_params: Mapped[list] = mapped_column(JSONB, default=list)
    unmatched_params: Mapped[list] = mapped_column(JSONB, default=list)
    ai_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class KnowledgeItem(Base):
    __tablename__ = "knowledge_items"
    knowledge_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    content: Mapped[str] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    embedding_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AdminLog(Base):
    __tablename__ = "admin_logs"
    log_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True
    )
    action: Mapped[str | None] = mapped_column(String(50), nullable=True)
    target_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LlmCallLog(Base):
    """LLM 调用事实数据（append-only，代理详细设计 3.5）。"""

    __tablename__ = "llm_call_logs"
    llm_call_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    turn: Mapped[int | None] = mapped_column(Integer, nullable=True)
    task: Mapped[str | None] = mapped_column(String(50), nullable=True)
    input_full: Mapped[dict] = mapped_column(JSONB, default=dict)
    output_raw: Mapped[dict] = mapped_column(JSONB, default=dict)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    params: Mapped[dict] = mapped_column(JSONB, default=dict)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    retry_of: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ConversationEvent(Base):
    """会话事件流（append-only，可重放）。"""

    __tablename__ = "conversation_events"
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    seq: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
