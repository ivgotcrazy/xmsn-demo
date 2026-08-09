"""文件域契约（通用上传：营业执照/能力资料文档，PoC 本地盘 FileStorage）。"""
from __future__ import annotations

from pydantic import BaseModel


class UploadResult(BaseModel):
    file_id: str
    url: str
    name: str
    size: int
    content_type: str | None = None
