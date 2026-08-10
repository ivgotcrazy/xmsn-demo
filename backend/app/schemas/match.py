"""匹配引擎契约（架构 6.3.3；路由 02B + 匹配详情页）。"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.conversation import DemandPoint


class MatchComputeRequest(BaseModel):
    request_id: str


class MatchRun(BaseModel):
    """匹配实体 = 一次匹配行为（1:1 锚定一个需求档案）。物化统计字段，查询免实时计算。

    status: running=计算中 / done=有厂商命中 / empty=本次匹配发生但无厂商命中。
    """

    run_id: str
    request_id: str
    status: Literal["running", "done", "empty"] = "done"
    total_vendors: int = 0
    best_score: float | None = None
    computation_time_ms: int = 0
    created_at: datetime


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
    """一次匹配的整体结果：run（匹配实体，含物化统计）+ 厂商匹配结果列表（可为空）。"""

    run: MatchRun
    match_results: list[MatchItem] = Field(default_factory=list)
    demand_points: list[DemandPoint] = Field(
        default_factory=list,
        description="本次匹配对应的需求档案（需求点集合；一个档案对应一个匹配实体）",
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
