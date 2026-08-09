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


class ConversationMessageItem(BaseModel):
    """会话内单条消息（02A 会话切换恢复现场用）。"""

    role: Literal["assistant", "user"]
    content: str
    error: bool = False
    options: list[str] = Field(default_factory=list, description="仅末条助手消息可带候选选项")


class ConversationMessagesResponse(BaseModel):
    """会话完整现场：消息气泡 + 当前需求槽位 + 档案版本（02A 点击会话切换恢复）。"""

    conversation_id: str
    status: Literal["active", "confirmed", "closed"]
    messages: list[ConversationMessageItem]
    current_slots: dict = Field(default_factory=dict)
    slot_confidence: dict = Field(default_factory=dict)
    excluded: list[str] = Field(default_factory=list)
    unset_fields: list[str] = Field(default_factory=list)
    version: int | None = None
    confirm_prompted: bool = False


class RequestSnapshot(BaseModel):
    request_id: str
    version: int
    structured_demand: dict = Field(default_factory=dict)
    created_at: datetime
    match_count: int = 0


class RequestSnapshotListResponse(BaseModel):
    requests: list[RequestSnapshot]
    total: int
