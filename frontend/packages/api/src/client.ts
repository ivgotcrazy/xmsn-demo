/* 生成物（只读勿手改）—— 由 scripts/generate.ts 从 openapi.json 契约快照生成 */
/* API 客户端：统一经 http.request 封装（JWT 注入 + 统一响应 {code,message,data} 解包） */
import { request } from "./http"
import type { RegisterRequest, AuthToken, LoginRequest, SendCodeRequest, UserOut, VendorRegisterRequest, VendorOut, CapabilityOut, UploadResult, ConversationStartRequest, ConversationStartResponse, MessageRequest, MessageResponse, FinishResponse, ConfirmRequest, ConfirmResponse, ConversationMessagesResponse, RequestSnapshotListResponse, DeleteResponse, ConversationListResponse, MatchComputeRequest, MatchComputeResponse, MatchDetailResponse, AuditRequest, AuditResponse, VendorListResponse, AdminStatsResponse, AdminRequestListResponse, BuyerListResponse, AdminLogListResponse, DocumentPreviewResponse } from "./types"

export async function healthz(): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>("/healthz", { method: "GET" })
}

export async function authRegister(body: RegisterRequest): Promise<AuthToken> {
  return request<AuthToken>("/api/v1/auth/register", { method: "POST", body })
}

export async function authLogin(body: LoginRequest): Promise<AuthToken> {
  return request<AuthToken>("/api/v1/auth/login", { method: "POST", body })
}

export async function authSendCode(body: SendCodeRequest): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>("/api/v1/auth/send-code", { method: "POST", body })
}

export async function authMe(): Promise<UserOut> {
  return request<UserOut>("/api/v1/auth/me", { method: "GET" })
}

export async function vendorRegister(body: VendorRegisterRequest): Promise<VendorOut> {
  return request<VendorOut>("/api/v1/vendor/register", { method: "POST", body })
}

export async function vendorVendorId(vendorId: string): Promise<VendorOut> {
  return request<VendorOut>(`/api/v1/vendor/${vendorId}`, { method: "GET" })
}

export async function vendorCapabilityUpload(): Promise<CapabilityOut> {
  return request<CapabilityOut>("/api/v1/vendor/capability/upload", { method: "POST" })
}

export async function vendorCapabilityVendorId(vendorId: string): Promise<CapabilityOut> {
  return request<CapabilityOut>(`/api/v1/vendor/capability/${vendorId}`, { method: "GET" })
}

export async function filesUpload(): Promise<UploadResult> {
  return request<UploadResult>("/api/v1/files/upload", { method: "POST" })
}

export async function conversationStart(body: ConversationStartRequest): Promise<ConversationStartResponse> {
  return request<ConversationStartResponse>("/api/v1/conversation/start", { method: "POST", body })
}

export async function conversationMessage(body: MessageRequest): Promise<MessageResponse> {
  return request<MessageResponse>("/api/v1/conversation/message", { method: "POST", body })
}

export async function conversationFinish(body: MessageRequest): Promise<FinishResponse> {
  return request<FinishResponse>("/api/v1/conversation/finish", { method: "POST", body })
}

export async function conversationConfirm(body: ConfirmRequest): Promise<ConfirmResponse> {
  return request<ConfirmResponse>("/api/v1/conversation/confirm", { method: "POST", body })
}

export async function conversationConversationIdMessages(conversationId: string): Promise<ConversationMessagesResponse> {
  return request<ConversationMessagesResponse>(`/api/v1/conversation/${conversationId}/messages`, { method: "GET" })
}

export async function conversationConversationIdRequests(conversationId: string): Promise<RequestSnapshotListResponse> {
  return request<RequestSnapshotListResponse>(`/api/v1/conversation/${conversationId}/requests`, { method: "GET" })
}

export async function conversationConversationId(conversationId: string): Promise<DeleteResponse> {
  return request<DeleteResponse>(`/api/v1/conversation/${conversationId}`, { method: "DELETE" })
}

export async function conversationConversationIdRequestsRequestId(conversationId: string, requestId: string): Promise<DeleteResponse> {
  return request<DeleteResponse>(`/api/v1/conversation/${conversationId}/requests/${requestId}`, { method: "DELETE" })
}

export async function conversations(): Promise<ConversationListResponse> {
  return request<ConversationListResponse>("/api/v1/conversations", { method: "GET" })
}

export async function matchCompute(body: MatchComputeRequest): Promise<MatchComputeResponse> {
  return request<MatchComputeResponse>("/api/v1/match/compute", { method: "POST", body })
}

export async function matchDetailMatchId(matchId: string): Promise<MatchDetailResponse> {
  return request<MatchDetailResponse>(`/api/v1/match/detail/${matchId}`, { method: "GET" })
}

export async function adminVendorsVendorIdAudit(vendorId: string, body: AuditRequest): Promise<AuditResponse> {
  return request<AuditResponse>(`/api/v1/admin/vendors/${vendorId}/audit`, { method: "POST", body })
}

export async function adminVendors(auditStatus?: (string | null), page?: number, pageSize?: number): Promise<VendorListResponse> {
  return request<VendorListResponse>("/api/v1/admin/vendors", { method: "GET", query: { auditStatus, page, pageSize } })
}

export async function adminStats(): Promise<AdminStatsResponse> {
  return request<AdminStatsResponse>("/api/v1/admin/stats", { method: "GET" })
}

export async function adminRequests(page?: number, pageSize?: number): Promise<AdminRequestListResponse> {
  return request<AdminRequestListResponse>("/api/v1/admin/requests", { method: "GET", query: { page, pageSize } })
}

export async function adminBuyers(keyword?: (string | null), status?: (string | null), page?: number, pageSize?: number): Promise<BuyerListResponse> {
  return request<BuyerListResponse>("/api/v1/admin/buyers", { method: "GET", query: { keyword, status, page, pageSize } })
}

export async function adminLogs(action?: (string | null), page?: number, pageSize?: number): Promise<AdminLogListResponse> {
  return request<AdminLogListResponse>("/api/v1/admin/logs", { method: "GET", query: { action, page, pageSize } })
}

export async function documentsDocIdPreview(docId: string, page?: number): Promise<DocumentPreviewResponse> {
  return request<DocumentPreviewResponse>(`/api/v1/documents/${docId}/preview`, { method: "GET", query: { page } })
}
