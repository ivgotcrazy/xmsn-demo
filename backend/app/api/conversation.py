"""对话接口（契约 6.3.1 + 6.3.5；路由 02A）。message 逻辑已实现（JSON 聚合返回；SSE 流式封装留 M7 前端对接）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.db.session import get_session
from app.domains.conversation import service as conv_service
from app.schemas.common import ApiResponse
from app.schemas.conversation import (
    ConfirmRequest,
    ConfirmResponse,
    ConversationListResponse,
    ConversationMessagesResponse,
    ConversationStartRequest,
    ConversationStartResponse,
    DeleteResponse,
    MessageRequest,
    MessageResponse,
    RequestSnapshotListResponse,
)

router = APIRouter(prefix="/conversation", tags=["conversation"])
# 会话列表使用复数路径（架构 6.3.5：GET /api/v1/conversations）
list_router = APIRouter(prefix="/conversations", tags=["conversation"])

Db = AsyncSession


@router.post("/start", response_model=ApiResponse[ConversationStartResponse], summary="开始新的需求对话")
async def start(
    payload: ConversationStartRequest, user: CurrentUser, db: AsyncSession = Depends(get_session)
) -> ApiResponse[ConversationStartResponse]:
    return ApiResponse(data=await conv_service.start(db, user.user_id))


@router.post("/message", response_model=ApiResponse[MessageResponse], summary="发送消息")
async def message(
    payload: MessageRequest, user: CurrentUser, db: AsyncSession = Depends(get_session)
) -> ApiResponse[MessageResponse]:
    return ApiResponse(data=await conv_service.message(
        db, payload.conversation_id, payload.message, payload.clicked_option))


@router.post("/confirm", response_model=ApiResponse[ConfirmResponse], summary="确认需求档案并提交匹配（单端点）")
async def confirm(
    payload: ConfirmRequest, user: CurrentUser, db: AsyncSession = Depends(get_session)
) -> ApiResponse[ConfirmResponse]:
    return ApiResponse(data=await conv_service.confirm(db, payload.conversation_id, user.user_id, payload.demand_points))


# ---- 历史（6.3.5）----
@list_router.get("", response_model=ApiResponse[ConversationListResponse], summary="客户会话列表")
async def list_conversations(user: CurrentUser, db: AsyncSession = Depends(get_session)) -> ApiResponse[ConversationListResponse]:
    return ApiResponse(data=await conv_service.list_conversations(db, user.user_id))


@router.get("/{conversation_id}/messages", response_model=ApiResponse[ConversationMessagesResponse], summary="会话消息历史（02A 切换会话恢复现场）")
async def list_messages(
    conversation_id: str, user: CurrentUser, db: AsyncSession = Depends(get_session)
) -> ApiResponse[ConversationMessagesResponse]:
    return ApiResponse(data=await conv_service.list_messages(db, conversation_id))


@router.get("/{conversation_id}/requests", response_model=ApiResponse[RequestSnapshotListResponse], summary="需求快照版本列表")
async def list_requests(
    conversation_id: str, user: CurrentUser, db: AsyncSession = Depends(get_session)
) -> ApiResponse[RequestSnapshotListResponse]:
    return ApiResponse(data=await conv_service.list_requests(db, conversation_id))


@router.delete(
    "/{conversation_id}",
    response_model=ApiResponse[DeleteResponse],
    summary="逻辑删除会话（deleted_at 标记，数据保留）",
)
async def delete_conversation(
    conversation_id: str, user: CurrentUser, db: AsyncSession = Depends(get_session)
) -> ApiResponse[DeleteResponse]:
    return ApiResponse(data=await conv_service.delete_conversation(db, conversation_id))


@router.delete(
    "/{conversation_id}/requests/{request_id}",
    response_model=ApiResponse[DeleteResponse],
    summary="逻辑删除需求档案/匹配（deleted_at 标记，数据保留）",
)
async def delete_request(
    conversation_id: str, request_id: str, user: CurrentUser, db: AsyncSession = Depends(get_session)
) -> ApiResponse[DeleteResponse]:
    return ApiResponse(data=await conv_service.delete_request(db, conversation_id, request_id))
