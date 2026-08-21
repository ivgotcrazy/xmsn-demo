"""认证接口（T2.1 实现）：注册 / 登录 / 验证码 / 当前用户 / 游客会话。"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.security import create_guest_token, decode_token
from app.db.models import User
from app.db.session import get_session
from app.domains.user_auth import service as auth_service
from app.schemas.auth import AuthToken, GuestToken, LoginRequest, RegisterRequest, SendCodeRequest, UserOut
from app.schemas.common import ApiResponse, err_404

router = APIRouter(prefix="/auth", tags=["auth"])

Db = Annotated[AsyncSession, Depends(get_session)]


@router.post("/register", response_model=ApiResponse[AuthToken], summary="用户注册（厂商/客户）")
async def register(payload: RegisterRequest, db: Db) -> ApiResponse[AuthToken]:
    return ApiResponse(data=await auth_service.register(db, payload))


@router.post("/login", response_model=ApiResponse[AuthToken], summary="用户登录")
async def login(payload: LoginRequest, db: Db) -> ApiResponse[AuthToken]:
    return ApiResponse(data=await auth_service.login(db, payload))


@router.post("/send-code", response_model=ApiResponse[dict], summary="发送验证码")
async def send_code(payload: SendCodeRequest) -> ApiResponse[dict]:
    return ApiResponse(data=await auth_service.send_code(payload))


@router.post("/guest", response_model=ApiResponse[GuestToken], summary="游客会话（匿名体验，不落账号）")
async def guest() -> ApiResponse[GuestToken]:
    token = create_guest_token()
    exp = int(decode_token(token)["exp"])
    now = int(datetime.now(timezone.utc).timestamp())
    return ApiResponse(data=GuestToken(access_token=token, expires_in=max(exp - now, 0)))


@router.get("/me", response_model=ApiResponse[UserOut], summary="当前用户信息")
async def me(user: CurrentUser, db: Db) -> ApiResponse[UserOut]:
    res = await db.execute(select(User).where(User.user_id == uuid.UUID(user.user_id)))
    u = res.scalar_one_or_none()
    if not u:
        raise err_404("用户不存在")
    return ApiResponse(data=await auth_service.user_out(db, u))
