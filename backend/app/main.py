"""需脉枢纽 · 后端 FastAPI 应用入口（模块化单体骨架）。

装配 core（配置/日志/安全）+ 统一响应/异常处理 + /healthz；
各域 router 由后续里程碑（M2-M6）挂载，此处预留占位。
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import setup_logging
from app.schemas.common import ApiResponse, BizError

logger = logging.getLogger("xmsn")


def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="需脉枢纽 · B2B 代工制造供需智能语义匹配平台",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # ---- 统一异常处理（契约 5.3）----
    @app.exception_handler(BizError)
    async def biz_error_handler(_: Request, exc: BizError) -> JSONResponse:
        return JSONResponse(status_code=exc.http_status,
                            content=ApiResponse(code=exc.code, message=exc.message).model_dump())

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=400,
                            content=ApiResponse(code=400, message=f"参数错误: {exc.errors()}").model_dump())

    @app.exception_handler(HTTPException)
    async def http_handler(_: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code,
                            content=ApiResponse(code=exc.status_code, message=str(exc.detail)).model_dump())

    @app.exception_handler(Exception)
    async def unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error: %s", exc)
        return JSONResponse(status_code=500,
                            content=ApiResponse(code=500, message="系统错误").model_dump())

    # ---- 健康检查 ----
    @app.get("/healthz", tags=["系统"], response_model=ApiResponse[dict])
    async def healthz() -> ApiResponse[dict]:
        return ApiResponse(data={"status": "ok", "app": settings.app_name})

    # ---- 业务路由（契约先行：M1 全部 501 stub，M2-M6 逐域实现）----
    from app.api.router import api_router

    app.include_router(api_router)

    return app


app = create_app()
