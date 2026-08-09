"""文档域契约（架构 6.3.5 查看原文预览定位高亮，COMP-040）。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentPreviewResponse(BaseModel):
    doc_id: str
    doc_name: str
    page: int
    content: str
    highlight: str | None = Field(default=None, description="需要高亮的原文片段")
