"""厂商域契约（产品 1.1/1.6；路由 01A/01B/01C/01D）。"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class VendorRegisterRequest(BaseModel):
    """企业基本信息（01A 厂商注册详情 / 产品 1.1）。"""

    company_name: str = Field(min_length=1, max_length=255)
    location: str | None = None
    main_industry: str | None = None
    credit_code: str | None = Field(default=None, description="统一社会信用代码（全局唯一）")
    license_file_id: str | None = Field(default=None, description="营业执照文件 ID（先调 /files/upload）")


class VendorOut(BaseModel):
    vendor_id: str
    company_name: str
    location: str | None = None
    main_industry: str | None = None
    credit_code: str | None = None
    audit_status: str = "pending"
    created_at: datetime


class CapabilityUploadForm(BaseModel):
    """能力录入：仅上传文档（AI 解析为能力档案）。厂商对文档质量负责。"""

    vendor_id: str
    document_ids: list[str] = Field(default_factory=list, description="文档 file_id 列表（先调 /files/upload）")


class CapabilityOut(BaseModel):
    """厂商能力档案（只读，01D）：AI 从文档解析，硬/软能力分层，全部可溯源到文档。"""

    capability_id: str
    vendor_id: str
    structured_tags: dict = Field(default_factory=dict)
    summary_text: str | None = None
    audit_status: Literal["pending", "passed", "rejected"] = "pending"
    # 档案版本：每次重新解析（增/删文档）version+1，配合 updated_at 让厂商确认档案是否已随最新文档更新
    version: int = Field(default=1, description="档案版本号：每次重新解析（增/删文档）递增")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="档案生成时间")
    doc_count: int = Field(default=0, description="本次档案基于的文档数")
    # 能力完备度（硬能力覆盖比例）：引导厂商补文档
    completeness: float | None = Field(default=None, description="能力完备度：硬能力已提取字段/硬能力总数 0-1")
    # 字段级溯源+置信度：{ field_key: {doc_id, doc_name, page, chunk_text, confidence} }
    source_map: dict = Field(
        default_factory=dict,
        description="能力字段 → 文档来源（含字段级解析置信度 confidence 0-1，<0.6 低置信度）",
    )
    raw_text: str | None = Field(default=None, description="文档原文片段")
    doc_urls: list[str] = Field(default_factory=list, description="文档名列表")
    # 文档引用 [{file_id, name}]：供「查看厂商能力」页对 PDF 预览定位（/documents/{file_id}/preview）
    doc_refs: list[dict] = Field(
        default_factory=list, description="文档引用 [{file_id, name}]，用于 PDF 预览定位"
    )
