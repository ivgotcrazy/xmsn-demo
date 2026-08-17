"""API 通用依赖：JWT 鉴权 / 管理员校验（契约 5.3；M2 接入真实用户查询）。"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.core.security import decode_token
from app.schemas.common import err_401, err_403

bearer_scheme = HTTPBearer(auto_error=False)


class UserContext(BaseModel):
    user_id: str
    role: str


async def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> UserContext:
    if creds is None:
        raise err_401()
    try:
        payload = decode_token(creds.credentials)
    except ValueError:
        raise err_401("无效或过期 Token")
    return UserContext(user_id=payload.get("sub", ""), role=payload.get("role", "customer"))


async def require_admin(user: Annotated[UserContext, Depends(get_current_user)]) -> UserContext:
    if user.role != "admin":
        raise err_403("需要管理员权限")
    return user


CurrentUser = Annotated[UserContext, Depends(get_current_user)]
AdminUser = Annotated[UserContext, Depends(require_admin)]
