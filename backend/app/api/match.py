"""匹配引擎接口（契约 6.3.3；路由 02B + 匹配详情页）。M4 实现：compute（双通道）+ detail（三组判定）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.db.session import get_session
from app.domains.match_service import service as match_service
from app.schemas.common import ApiResponse
from app.schemas.match import MatchComputeRequest, MatchComputeResponse, MatchDetailResponse

router = APIRouter(prefix="/match", tags=["match"])


@router.post("/compute", response_model=ApiResponse[MatchComputeResponse], summary="触发匹配计算")
async def compute(
    payload: MatchComputeRequest, user: CurrentUser, db: AsyncSession = Depends(get_session)
) -> ApiResponse[MatchComputeResponse]:
    return ApiResponse(data=await match_service.compute(db, payload.request_id))


@router.get("/detail/{match_id}", response_model=ApiResponse[MatchDetailResponse], summary="匹配详情（含解释，异步轮询）")
async def detail(
    match_id: str, user: CurrentUser, db: AsyncSession = Depends(get_session)
) -> ApiResponse[MatchDetailResponse]:
    return ApiResponse(data=await match_service.detail(db, match_id))
