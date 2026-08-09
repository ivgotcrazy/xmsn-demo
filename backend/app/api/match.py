"""匹配引擎接口（契约 6.3.3；路由 02B + 匹配详情页）。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.schemas.common import ApiResponse, err_501
from app.schemas.match import MatchComputeRequest, MatchComputeResponse, MatchDetailResponse

router = APIRouter(prefix="/match", tags=["match"])


@router.post("/compute", response_model=ApiResponse[MatchComputeResponse], summary="触发匹配计算")
async def compute(payload: MatchComputeRequest, user: CurrentUser) -> ApiResponse[MatchComputeResponse]:
    raise err_501("契约层占位：M4 实现")


@router.get("/detail/{match_id}", response_model=ApiResponse[MatchDetailResponse], summary="匹配详情（含解释，异步轮询）")
async def detail(match_id: str, user: CurrentUser) -> ApiResponse[MatchDetailResponse]:
    raise err_501("契约层占位：M4 实现")
