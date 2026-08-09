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
    """能力录入三步合一提交（1.6/01C）：结构化表单 + 自由文本 + 文档。"""

    vendor_id: str
    form_data: dict = Field(default_factory=dict, description="结构化能力表单（按需求 Schema 品类）")
    free_text: str | None = None
    document_ids: list[str] = Field(default_factory=list, description="文档 file_id 列表（先调 /files/upload）")


class CapabilityOut(BaseModel):
    """厂商能力档案（只读，原型 01D 三栏：原始输入 / AI结构化标签 / 一句话摘要）。"""

    capability_id: str
    vendor_id: str
    structured_tags: dict = Field(default_factory=dict)
    summary_text: str | None = None
    audit_status: Literal["pending", "passed", "rejected"] = "pending"
    # 原型 01D 左栏"原始输入"：表单摘要 + 自由文本片段 + 文档名列表
    raw_text: str | None = Field(default=None, description="自由文本片段（Step2）")
    doc_urls: list[str] = Field(default_factory=list, description="文档名列表（Step3）")
