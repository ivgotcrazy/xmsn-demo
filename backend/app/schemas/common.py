"""通用响应模型与业务异常（契约 5.3）。

统一响应：{ "code": 0, "message": "ok", "data": {...} }
错误码：400 参数 / 401 未认证 / 403 无权限 / 404 不存在 / 429 限流 / 500 系统 / 501 AI 不可用
"""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "ok"
    data: T | None = None


class BizError(Exception):
    """业务异常（对应 5.3 错误码）。"""

    def __init__(self, code: int, message: str, http_status: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status or (code if 400 <= code < 500 else 400)


# 便捷构造
def err_400(msg: str = "参数错误") -> BizError:
    return BizError(400, msg)


def err_401(msg: str = "未认证") -> BizError:
    return BizError(401, msg)


def err_403(msg: str = "无权限") -> BizError:
    return BizError(403, msg)


def err_404(msg: str = "资源不存在") -> BizError:
    return BizError(404, msg)


def err_429(msg: str = "触发限流") -> BizError:
    return BizError(429, msg, 429)


def err_500(msg: str = "系统错误") -> BizError:
    return BizError(500, msg, 500)


def err_501(msg: str = "AI 服务不可用") -> BizError:
    return BizError(501, msg, 501)


class PageData(BaseModel, Generic[T]):
    """分页数据结构（契约 5.3：page / page_size → list / total / page / page_size）。"""

    list: list[T]
    total: int
    page: int
    page_size: int
