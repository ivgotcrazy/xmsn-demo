"""user-auth 域服务（T2.1）：注册 / 登录 / 验证码 / 当前用户。

实现以《产品需求设计》1.1/2.1 与架构 5.3 为准；验证码在 PoC 无短信/邮件网关时
仅记日志（verify_code_required=false 不强制），演进接入网关时替换发送实现。
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import User
from app.schemas.auth import AuthToken, LoginRequest, RegisterRequest, SendCodeRequest, UserOut
from app.schemas.common import err_400, err_401

logger = logging.getLogger("xmsn.user_auth")

# 验证码存储（进程内；演进 Redis / 短信网关时替换实现，见 ADR-09 同哲学）
_verify_codes: dict[str, tuple[str, datetime]] = {}
_CODE_TTL = timedelta(minutes=5)


def user_out(u: User) -> UserOut:
    """User ORM → UserOut（契约形状）。"""
    return UserOut(
        user_id=str(u.user_id),
        phone=u.phone,
        email=u.email,
        role=u.role,
        status=u.status,
        created_at=u.created_at,
    )


def _token(u: User) -> AuthToken:
    return AuthToken(
        access_token=create_access_token(str(u.user_id), u.role),
        expires_in=settings.jwt_expire_minutes * 60,
        user=user_out(u),
    )


async def _find_user(db: AsyncSession, phone: str | None, email: str | None) -> User | None:
    if phone:
        res = await db.execute(select(User).where(User.phone == phone))
        return res.scalar_one_or_none()
    if email:
        res = await db.execute(select(User).where(User.email == email))
        return res.scalar_one_or_none()
    return None


def _check_code(account: str, code: str | None) -> None:
    rec = _verify_codes.get(account)
    if not rec or rec[1] + _CODE_TTL < datetime.utcnow():
        raise err_400("验证码已过期，请重新获取")
    if rec[0] != code:
        raise err_400("验证码错误")
    _verify_codes.pop(account, None)


async def register(db: AsyncSession, payload: RegisterRequest) -> AuthToken:
    """自助注册（厂商/买家）：手机号或邮箱至少其一；密码 bcrypt 哈希。"""
    if not payload.phone and not payload.email:
        raise err_400("手机号或邮箱至少填写其一")
    if await _find_user(db, payload.phone, payload.email):
        raise err_400("该手机号/邮箱已注册，请直接登录")
    if settings.verify_code_required:
        _check_code(payload.phone or payload.email or "", payload.verify_code)
    user = User(
        phone=payload.phone or None,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        status="active",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info("user registered: id=%s role=%s", user.user_id, user.role)
    return _token(user)


async def login(db: AsyncSession, payload: LoginRequest) -> AuthToken:
    """登录：按手机号/邮箱定位用户并校验密码。"""
    if not payload.phone and not payload.email:
        raise err_400("手机号或邮箱至少填写其一")
    user = await _find_user(db, payload.phone, payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise err_401("账号或密码错误")
    # M6 审计：管理员登录写 admin_logs（append-only）
    if user.role == "admin":
        from app.db.models import AdminLog

        db.add(AdminLog(admin_user_id=user.user_id, action="login",
                        target_type="admin", target_id=str(user.user_id), detail={"phone": user.phone}))
        await db.commit()
    return _token(user)


async def send_code(payload: SendCodeRequest) -> dict:
    """生成验证码并发送（PoC 仅日志；接入网关后替换发送实现）。"""
    account = payload.phone or payload.email
    if not account:
        raise err_400("手机号或邮箱至少填写其一")
    code = f"{secrets.randbelow(1_000_000):06d}"
    _verify_codes[account] = (code, datetime.utcnow())
    # 真实发送走短信/邮件网关（未配置时仅记录，便于本地联调）
    logger.info("verify code for %s: %s", account, code)
    return {"sent": True}
