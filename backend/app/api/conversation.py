"""对话接口（契约 6.3.1 + 6.3.5；路由 02A）。message 为 SSE 流式，前端 index.ts 封装。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.schemas.common import ApiResponse, err_501
from app.schemas.conversation import (
    ConfirmRequest,
    ConfirmResponse,
    ConversationListResponse,
    ConversationStartRequest,
    ConversationStartResponse,
    FinishResponse,
    MessageRequest,
    MessageResponse,
    RequestSnapshotListResponse,
)

router = APIRouter(prefix="/conversation", tags=["conversation"])
# 会话列表使用复数路径（架构 6.3.5：GET /api/v1/conversations）
list_router = APIRouter(prefix="/conversations", tags=["conversation"])


@router.post("/start", response_model=ApiResponse[ConversationStartResponse], summary="开始新的需求对话")
async def start(payload: ConversationStartRequest, user: CurrentUser) -> ApiResponse[ConversationStartResponse]:
    raise err_501("契约层占位：M3 实现")


@router.post("/message", response_model=ApiResponse[MessageResponse], summary="发送消息（SSE 流式）")
async def message(payload: MessageRequest, user: CurrentUser) -> ApiResponse[MessageResponse]:
    raise err_501("契约层占位：M3 实现")


@router.post("/finish", response_model=ApiResponse[FinishResponse], summary="完成需求描述 → 生成需求档案")
async def finish(payload: MessageRequest, user: CurrentUser) -> ApiResponse[FinishResponse]:
    raise err_501("契约层占位：M3 实现")


@router.post("/confirm", response_model=ApiResponse[ConfirmResponse], summary="确认需求档案并提交匹配")
async def confirm(payload: ConfirmRequest, user: CurrentUser) -> ApiResponse[ConfirmResponse]:
    raise err_501("契约层占位：M3 实现")


# ---- 历史（6.3.5）----
@list_router.get("", response_model=ApiResponse[ConversationListResponse], summary="买家会话列表")
async def list_conversations(user: CurrentUser) -> ApiResponse[ConversationListResponse]:
    raise err_501("契约层占位：M3 实现")


@router.get("/{conversation_id}/requests", response_model=ApiResponse[RequestSnapshotListResponse], summary="需求快照版本列表")
async def list_requests(conversation_id: str, user: CurrentUser) -> ApiResponse[RequestSnapshotListResponse]:
    raise err_501("契约层占位：M3 实现")
