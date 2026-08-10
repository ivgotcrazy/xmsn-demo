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


class DemandPoint(BaseModel):
    """会话中萃取的单一需求点（前端「当前需求」展示单元，不感知 schema；固定/扩展由后端映射）。"""

    key: str
    label: str
    value: str | list[str]
    confidence: float = 1.0


class ConversationStartResponse(BaseModel):
    conversation_id: str
    first_message: AssistantMessage
    demand_points: list[DemandPoint] = Field(default_factory=list)
    title: str = "新会话"


class MessageRequest(BaseModel):
    conversation_id: str
    message: str


class MessageResponse(BaseModel):
    """SSE 流式对话的最终聚合形状；流式逐 token 由 index.ts 用 fetch+ReadableStream 封装（5.4）。
    demand_points 为当前完整需求点集合（全量返回，前端整体替换）。
    title 为会话当前标题（=聚焦的产品类型名，未确定时为「新会话」）。"""

    assistant_message: AssistantMessage
    demand_points: list[DemandPoint] = Field(default_factory=list)
    title: str = "新会话"


class ConfirmRequest(BaseModel):
    conversation_id: str
    demand_points: list[DemandPoint] = Field(default_factory=list)


class ConfirmResponse(BaseModel):
    request_id: str
    version: int
    redirect_to: str = ""


# ---- 历史（产品 2.8）----
class ConversationListItem(BaseModel):
    conversation_id: str
    title: str = "新会话"
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
    created_at: datetime | None = None


class ConversationMessagesResponse(BaseModel):
    """会话完整现场：消息气泡 + 完整需求点集合 + 档案版本（02A 点击会话切换恢复）。
    title 为会话当前标题（=聚焦的产品类型名，未确定时为「新会话」）。"""

    conversation_id: str
    title: str = "新会话"
    status: Literal["active", "confirmed", "closed"]
    messages: list[ConversationMessageItem]
    demand_points: list[DemandPoint] = Field(default_factory=list)
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


class DeleteResponse(BaseModel):
    """逻辑删除结果：数据保留（deleted_at 标记），仅从可见列表移除（所有数据有挖掘价值）。"""

    id: str
    deleted: bool = True
    deleted_at: datetime
