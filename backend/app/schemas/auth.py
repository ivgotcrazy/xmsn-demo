"""认证域契约（产品 1.1 / 2.1；路由 00A/00B/03A）。"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """自助注册：手机号/邮箱 + 密码 + 角色 + 验证码（厂商/客户）。"""

    phone: str | None = Field(default=None, description="手机号（与 email 至少其一）")
    email: str | None = Field(default=None, description="邮箱")
    password: str = Field(min_length=6, max_length=64)
    role: Literal["vendor", "customer"] = "customer"
    verify_code: str | None = Field(default=None, description="短信/邮箱验证码")


class LoginRequest(BaseModel):
    phone: str | None = None
    email: str | None = None
    password: str


class SendCodeRequest(BaseModel):
    phone: str | None = None
    email: str | None = None
    scene: Literal["register", "login", "reset"] = "register"


class UserOut(BaseModel):
    user_id: str
    phone: str | None = None
    email: str | None = None
    role: str
    status: str = "active"
    created_at: datetime


class AuthToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut
