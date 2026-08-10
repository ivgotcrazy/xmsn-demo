"""文件上传接口（通用：营业执照/能力文档，multipart；文件上传不做前端 mock，留真实联调）。"""
from __future__ import annotations

from fastapi import APIRouter, File, UploadFile

from app.core.config import settings
from app.domains.file_service.storage import storage
from app.schemas.common import ApiResponse, err_400
from app.schemas.file import UploadResult

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload", response_model=ApiResponse[UploadResult], summary="通用文件上传（≤20MB）")
async def upload(file: UploadFile = File(...)) -> ApiResponse[UploadResult]:
    data = await file.read()
    if len(data) > settings.max_upload_size_mb * 1024 * 1024:
        raise err_400(f"文件超过 {settings.max_upload_size_mb}MB 限制")
    name = file.filename or "unnamed"
    file_id, url = await storage.save(data, name)
    return ApiResponse(
        data=UploadResult(file_id=file_id, url=url, name=name, size=len(data), content_type=file.content_type)
    )
