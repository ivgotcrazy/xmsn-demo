"""匹配引擎契约（架构 6.3.3；路由 02B + 匹配详情页）。"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


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


class MatchDetailResponse(BaseModel):
    """匹配详情（含解释；异步生成，未生成时 explanation_status=pending 返回骨架标记，前端轮询）。"""

    match_id: str
    request_id: str
    vendor_id: str
    company_name: str
    matched_params: list[dict] = Field(default_factory=list)
    partial_params: list[dict] = Field(default_factory=list)
    unmatched_params: list[dict] = Field(default_factory=list)
    ai_comment: str | None = None
    explanation_status: Literal["pending", "ready"] = "pending"
