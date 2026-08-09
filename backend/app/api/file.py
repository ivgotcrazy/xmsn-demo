"""文件上传接口（通用：营业执照/能力文档，multipart；文件上传不做前端 mock，留真实联调）。"""
from __future__ import annotations

from fastapi import APIRouter, File, UploadFile

from app.schemas.common import ApiResponse, err_501
from app.schemas.file import UploadResult

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload", response_model=ApiResponse[UploadResult], summary="通用文件上传（≤10MB）")
async def upload(file: UploadFile = File(...)) -> ApiResponse[UploadResult]:
    raise err_501("契约层占位：M2 实现")
