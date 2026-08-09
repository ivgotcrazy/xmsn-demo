"""对话域契约（架构 6.3.1 + 6.3.5；路由 02A）。"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ---- 对话 Agent ----
class ConversationStartRequest(BaseModel):
    user_id: str


class AssistantMessage(BaseModel):
    role: str = "assistant"
    content: str
    options: list[str] = Field(default_factory=list, description="可选回答（槽位候选）")


class ConversationStartResponse(BaseModel):
    conversation_id: str
    first_message: AssistantMessage
    current_slots: dict = Field(default_factory=dict)


class MessageRequest(BaseModel):
    conversation_id: str
    message: str


class MessageResponse(BaseModel):
    """SSE 流式对话的最终聚合形状；流式逐 token 由 index.ts 用 fetch+ReadableStream 封装（5.4）。"""

    assistant_message: AssistantMessage
    updated_slots: dict = Field(default_factory=dict)
    slot_confidence: dict = Field(default_factory=dict)


class FinishResponse(BaseModel):
    """完成需求描述 → 生成需求档案（版本 vN）。"""

    profile: dict = Field(default_factory=dict)
    version: int
    unset_fields: list[str] = Field(default_factory=list)


class ConfirmRequest(BaseModel):
    conversation_id: str
    final_demand: dict = Field(default_factory=dict)


class ConfirmResponse(BaseModel):
    request_id: str
    version: int
    redirect_to: str


# ---- 历史（产品 2.8）----
class ConversationListItem(BaseModel):
    conversation_id: str
    status: Literal["active", "confirmed", "closed"]
    updated_at: datetime
    last_request_id: str | None = None
    request_count: int = 0


class ConversationListResponse(BaseModel):
    conversations: list[ConversationListItem]
    total: int


class RequestSnapshot(BaseModel):
    request_id: str
    version: int
    structured_demand: dict = Field(default_factory=dict)
    created_at: datetime
    match_count: int = 0


class RequestSnapshotListResponse(BaseModel):
    requests: list[RequestSnapshot]
    total: int
