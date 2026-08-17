"""文档接口（契约 6.3.5 查看原文预览；COMP-040；M5 完善高亮定位；源文件直读）。"""
from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.api.deps import CurrentUser
from app.domains.file_service.parser import extract_pages
from app.domains.file_service.storage import storage
from app.schemas.common import ApiResponse, err_404, err_501
from app.schemas.documents import DocumentPreviewResponse

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/{doc_id}/preview", response_model=ApiResponse[DocumentPreviewResponse], summary="文档预览定位高亮")
async def preview(
    doc_id: str,
    user: CurrentUser,
    page: int = Query(default=1, ge=1),
) -> ApiResponse[DocumentPreviewResponse]:
    if not await storage.exists(doc_id):
        raise err_404("文档不存在")
    data = await storage.read(doc_id)
    doc_name = await storage.name(doc_id)
    pages = extract_pages(data, doc_name)
    if not pages:
        raise err_501("该文档无法解析")
    page_text = pages[min(page - 1, len(pages) - 1)]
    return ApiResponse(
        data=DocumentPreviewResponse(
            doc_id=doc_id,
            doc_name=doc_name,
            page=page,
            content=page_text,
            highlight=None,
        )
    )


@router.get("/{doc_id}/file", summary="源文件直读（原样返回，浏览器内嵌预览/下载，非文本提取）")
async def download_doc(doc_id: str, user: CurrentUser) -> Response:
    if not await storage.exists(doc_id):
        raise err_404("文档不存在")
    data = await storage.read(doc_id)
    doc_name = await storage.name(doc_id)
    media_type = (
        "application/pdf"
        if doc_name.lower().endswith(".pdf")
        else "application/octet-stream"
    )
    # Content-Disposition: inline 让浏览器内嵌展示（PDF 原生查看器）；filename 用 RFC 5987 UTF-8 编码
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{quote(doc_name)}"},
    )
