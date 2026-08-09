"""文档接口（契约 6.3.5 查看原文预览；COMP-040）。"""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser
from app.schemas.common import ApiResponse, err_501
from app.schemas.documents import DocumentPreviewResponse

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/{doc_id}/preview", response_model=ApiResponse[DocumentPreviewResponse], summary="文档预览定位高亮")
async def preview(
    doc_id: str,
    user: CurrentUser,
    page: int = Query(default=1, ge=1),
) -> ApiResponse[DocumentPreviewResponse]:
    raise err_501("契约层占位：M5 实现")
