"""认证接口（契约 5.5：M1 全部 501 stub，openapi 形状完整）。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.schemas.auth import AuthToken, LoginRequest, RegisterRequest, SendCodeRequest, UserOut
from app.schemas.common import ApiResponse, err_501

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=ApiResponse[AuthToken], summary="用户注册（厂商/买家）")
async def register(payload: RegisterRequest) -> ApiResponse[AuthToken]:
    raise err_501("契约层占位：M2 实现")


@router.post("/login", response_model=ApiResponse[AuthToken], summary="用户登录")
async def login(payload: LoginRequest) -> ApiResponse[AuthToken]:
    raise err_501("契约层占位：M2 实现")


@router.post("/send-code", response_model=ApiResponse[dict], summary="发送验证码")
async def send_code(payload: SendCodeRequest) -> ApiResponse[dict]:
    raise err_501("契约层占位：M2 实现")


@router.get("/me", response_model=ApiResponse[UserOut], summary="当前用户信息")
async def me(user: CurrentUser) -> ApiResponse[UserOut]:
    raise err_501("契约层占位：M2 实现")
