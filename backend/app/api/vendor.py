"""厂商接口（契约 6.3.2 / 产品 1.x；路由 01A-01D）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.db.session import get_session
from app.domains.vendor_service import service as vendor_service
from app.schemas.common import ApiResponse, err_404
from app.schemas.vendor import CapabilityOut, VendorOut, VendorRegisterRequest

router = APIRouter(prefix="/vendor", tags=["vendor"])


@router.post("/register", response_model=ApiResponse[VendorOut], summary="企业基本信息（厂商注册详情）")
async def register_vendor(
    payload: VendorRegisterRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_session),
) -> ApiResponse[VendorOut]:
    return ApiResponse(data=await vendor_service.register_vendor(db, user.user_id, payload))


@router.get("/{vendor_id}", response_model=ApiResponse[VendorOut], summary="厂商档案")
async def get_vendor(
    vendor_id: str, user: CurrentUser, db: AsyncSession = Depends(get_session)
) -> ApiResponse[VendorOut]:
    vendor = await vendor_service.get_vendor(db, vendor_id)
    if not vendor:
        raise err_404("厂商不存在")
    return ApiResponse(data=vendor)


@router.post("/capability/upload", response_model=ApiResponse[CapabilityOut], summary="能力录入（仅上传文档，AI 解析）")
async def upload_capability(
    vendor_id: str = Form(...),
    documents: list[UploadFile] = File(default=[]),
    db: AsyncSession = Depends(get_session),
) -> ApiResponse[CapabilityOut]:
    items = [(await d.read(), d.filename or "unnamed") for d in documents]
    return ApiResponse(data=await vendor_service.upload_capability(db, vendor_id, items))


@router.get("/capability/{vendor_id}", response_model=ApiResponse[CapabilityOut], summary="厂商能力档案（只读）")
async def get_capability(
    vendor_id: str, user: CurrentUser, db: AsyncSession = Depends(get_session)
) -> ApiResponse[CapabilityOut]:
    cap = await vendor_service.get_capability(db, vendor_id)
    if not cap:
        raise err_404("能力档案不存在")
    return ApiResponse(data=cap)


@router.delete(
    "/capability/{vendor_id}/documents/{document_id}",
    response_model=ApiResponse[CapabilityOut],
    summary="删除能力文档（触发重新解析，版本+1）",
)
async def delete_capability_document(
    vendor_id: str, document_id: str, db: AsyncSession = Depends(get_session)
) -> ApiResponse[CapabilityOut]:
    return ApiResponse(data=await vendor_service.delete_document(db, vendor_id, document_id))
