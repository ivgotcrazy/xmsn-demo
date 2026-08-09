"""匹配引擎契约（架构 6.3.3；路由 02B + 匹配详情页）。"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.conversation import DemandPoint


class MatchComputeRequest(BaseModel):
    request_id: str


class MatchItem(BaseModel):
    match_id: str
    vendor_id: str
    company_name: str
    location: str | None = None
    summary: str | None = None
    match_score: float
    semantic_score: float | None = None
    param_hit_rate: float | None = None
    critical_fail: bool = False
    match_source: Literal["llm", "rule", "hybrid"] = "llm"
    matched_count: int = 0
    unmatched_count: int = 0


class MatchComputeResponse(BaseModel):
    match_results: list[MatchItem]
    total_matches: int
    computation_time_ms: int
    demand_points: list[DemandPoint] = Field(
        default_factory=list,
        description="本次匹配对应的需求档案（需求点集合；一个档案对应多个匹配结果）",
    )


class MatchParam(BaseModel):
    """单条参数判定（仅对买家已指定参数判定；出处引用指向厂商原始文档）。

    partial 语义为“需协商·厂商未声明”：买家已指定但厂商能力档案未声明/部分覆盖。
    """

    key: str
    label: str
    value: str
    verdict: Literal["matched", "partial", "unmatched"]
    source_doc_id: str | None = None
    source_doc_name: str | None = None
    source_page: int | None = None
    source_text: str | None = None


class MatchDetailResponse(BaseModel):
    """匹配详情（含解释；异步生成，未生成时 explanation_status=pending 返回骨架标记，前端轮询）。"""

    match_id: str
    request_id: str
    vendor_id: str
    company_name: str
    matched_params: list[MatchParam] = Field(default_factory=list)
    partial_params: list[MatchParam] = Field(default_factory=list)
    unmatched_params: list[MatchParam] = Field(default_factory=list)
    ai_comment: str | None = None
    explanation_status: Literal["pending", "ready"] = "pending"
