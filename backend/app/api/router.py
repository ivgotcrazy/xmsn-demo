"""API 路由聚合：契约先行阶段挂载全部子路由（handler 501 stub，M2-M6 逐域实现）。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api import admin, auth, conversation, documents, file, match, vendor

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(vendor.router)
api_router.include_router(file.router)
api_router.include_router(conversation.router)
api_router.include_router(conversation.list_router)
api_router.include_router(match.router)
api_router.include_router(admin.router)
api_router.include_router(documents.router)
