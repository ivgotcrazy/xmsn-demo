"""初始数据库迁移：全部 12 张表（架构 6.1 + 画像 + 事实数据）

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("role IN ('vendor','buyer','admin')", name="ck_users_role"),
        sa.UniqueConstraint("phone"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "vendors",
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=True),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("main_industry", sa.String(100), nullable=True),
        sa.Column("credit_code", sa.String(18), nullable=True),
        sa.Column("license_url", sa.Text(), nullable=True),
        sa.Column("audit_status", sa.String(20), server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("audit_status IN ('pending','passed','rejected')", name="ck_vendors_audit"),
        sa.UniqueConstraint("credit_code"),
    )
    op.create_table(
        "vendor_capabilities",
        sa.Column("capability_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vendors.vendor_id"), nullable=False),
        sa.Column("structured_tags", postgresql.JSONB(), server_default="{}"),
        sa.Column("summary_text", sa.Text(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("doc_urls", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("source_type", sa.String(50), nullable=True),
        sa.Column("rep_embedding_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_vendor_tags_gin", "vendor_capabilities", ["structured_tags"], postgresql_using="gin")
    op.create_table(
        "conversations",
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("conversation_history", postgresql.JSONB(), server_default="[]"),
        sa.Column("current_slots", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('active','confirmed','closed')", name="ck_conversations_status"),
    )
    op.create_table(
        "buyer_requests",
        sa.Column("request_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("conversations.conversation_id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("structured_demand", postgresql.JSONB(), server_default="{}"),
        sa.Column("embedding_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), server_default="confirmed"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "profile_schemas",
        sa.Column("schema_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("scope", sa.String(20), server_default="base"),
        sa.Column("industry", sa.String(50), nullable=True),
        sa.Column("dimensions", postgresql.JSONB(), server_default="[]"),
        sa.Column("active", sa.Boolean(), server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("scope IN ('base','industry')", name="ck_profile_schemas_scope"),
        sa.UniqueConstraint("schema_version", "scope", "industry", name="uq_profile_schemas_version_scope_industry"),
    )
    op.create_table(
        "user_profiles",
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("schema_version", sa.Integer(), server_default="1"),
        sa.Column("profile_data", postgresql.JSONB(), server_default="{}"),
        sa.Column("confidence", postgresql.JSONB(), server_default="{}"),
        sa.Column("total_requests", sa.Integer(), server_default="0"),
        sa.Column("last_request_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id"),
    )
    op.create_table(
        "match_results",
        sa.Column("match_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("buyer_requests.request_id"), nullable=False),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vendors.vendor_id"), nullable=False),
        sa.Column("match_score", sa.Float(), nullable=True),
        sa.Column("semantic_score", sa.Float(), nullable=True),
        sa.Column("param_hit_rate", sa.Float(), nullable=True),
        sa.Column("critical_fail", sa.Boolean(), server_default=sa.false()),
        sa.Column("match_source", sa.String(10), server_default="llm"),
        sa.Column("matched_params", postgresql.JSONB(), server_default="[]"),
        sa.Column("partial_params", postgresql.JSONB(), server_default="[]"),
        sa.Column("unmatched_params", postgresql.JSONB(), server_default="[]"),
        sa.Column("ai_comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("match_source IN ('llm','rule','hybrid')", name="ck_match_results_source"),
    )
    op.create_index("idx_match_request", "match_results", ["request_id"])
    op.create_index("idx_match_vendor", "match_results", ["vendor_id"])
    op.create_table(
        "knowledge_items",
        sa.Column("knowledge_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("industry", sa.String(50), nullable=True),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("embedding_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "admin_logs",
        sa.Column("log_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("admin_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=True),
        sa.Column("action", sa.String(50), nullable=True),
        sa.Column("target_type", sa.String(50), nullable=True),
        sa.Column("target_id", sa.String(64), nullable=True),
        sa.Column("detail", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "llm_call_logs",
        sa.Column("llm_call_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("turn", sa.Integer(), nullable=True),
        sa.Column("task", sa.String(50), nullable=True),
        sa.Column("input_full", postgresql.JSONB(), server_default="{}"),
        sa.Column("output_raw", postgresql.JSONB(), server_default="{}"),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("params", postgresql.JSONB(), server_default="{}"),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("tokens", postgresql.JSONB(), server_default="{}"),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("retry_of", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "conversation_events",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(30), nullable=True),
        sa.Column("payload", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("conversation_events")
    op.drop_table("llm_call_logs")
    op.drop_table("admin_logs")
    op.drop_table("knowledge_items")
    op.drop_index("idx_match_vendor", table_name="match_results")
    op.drop_index("idx_match_request", table_name="match_results")
    op.drop_table("match_results")
    op.drop_table("user_profiles")
    op.drop_table("profile_schemas")
    op.drop_table("buyer_requests")
    op.drop_table("conversations")
    op.drop_index("idx_vendor_tags_gin", table_name="vendor_capabilities")
    op.drop_table("vendor_capabilities")
    op.drop_table("vendors")
    op.drop_table("users")
