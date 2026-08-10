"""厂商接口（契约 6.3.2 / 产品 1.x；路由 01A-01D）。"""
from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile

from app.api.deps import CurrentUser
from app.schemas.common import ApiResponse, err_501
from app.schemas.vendor import CapabilityOut, VendorOut, VendorRegisterRequest

router = APIRouter(prefix="/vendor", tags=["vendor"])


@router.post("/register", response_model=ApiResponse[VendorOut], summary="企业基本信息（厂商注册详情）")
async def register_vendor(payload: VendorRegisterRequest, user: CurrentUser) -> ApiResponse[VendorOut]:
    raise err_501("契约层占位：M2 实现")


@router.get("/{vendor_id}", response_model=ApiResponse[VendorOut], summary="厂商档案")
async def get_vendor(vendor_id: str, user: CurrentUser) -> ApiResponse[VendorOut]:
    raise err_501("契约层占位：M2 实现")


@router.post("/capability/upload", response_model=ApiResponse[CapabilityOut], summary="能力录入（仅上传文档，AI 解析）")
async def upload_capability(
    vendor_id: str = Form(...),
    documents: list[UploadFile] = File(default=[]),
) -> ApiResponse[CapabilityOut]:
    raise err_501("契约层占位：M2 实现")


@router.get("/capability/{vendor_id}", response_model=ApiResponse[CapabilityOut], summary="厂商能力档案（只读）")
async def get_capability(vendor_id: str, user: CurrentUser) -> ApiResponse[CapabilityOut]:
    raise err_501("契约层占位：M2 实现")


@router.delete(
    "/capability/{vendor_id}/documents/{document_id}",
    response_model=ApiResponse[CapabilityOut],
    summary="删除能力文档（触发重新解析，版本+1）",
)
async def delete_capability_document(vendor_id: str, document_id: str) -> ApiResponse[CapabilityOut]:
    raise err_501("契约层占位：M2 实现")
