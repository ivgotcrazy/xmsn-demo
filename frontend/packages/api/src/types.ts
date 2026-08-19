/* 生成物（只读勿手改）—— 由 scripts/generate.ts 从 openapi.json 契约快照生成 */

export type AdminLogItem = {
  log_id: string;
  action: string;
  action_label?: string;
  target_type?: (string | null);
  target_id?: (string | null);
  admin_name?: string;
  detail?: Record<string, unknown>;
  created_at: string;
};
export type AdminLogListResponse = {
  list: AdminLogItem[];
  total: number;
  page: number;
  page_size: number;
};
export type AdminRequestItem = {
  request_id: string;
  conversation_id: string;
  version: number;
  structured_demand?: Record<string, unknown>;
  customer_phone?: string;
  run?: (MatchRun | null);
  created_at: string;
};
export type AdminRequestListResponse = {
  list: AdminRequestItem[];
  total: number;
  page: number;
  page_size: number;
};
export type AdminStatsResponse = {
  total_users: number;
  total_requests: number;
  total_vendors: number;
  total_matches: number;
};
export type ApiResponse_AdminLogListResponse_ = {
  code?: number;
  message?: string;
  data?: (AdminLogListResponse | null);
};
export type ApiResponse_AdminRequestListResponse_ = {
  code?: number;
  message?: string;
  data?: (AdminRequestListResponse | null);
};
export type ApiResponse_AdminStatsResponse_ = {
  code?: number;
  message?: string;
  data?: (AdminStatsResponse | null);
};
export type ApiResponse_AuditResponse_ = {
  code?: number;
  message?: string;
  data?: (AuditResponse | null);
};
export type ApiResponse_AuthToken_ = {
  code?: number;
  message?: string;
  data?: (AuthToken | null);
};
export type ApiResponse_CapabilityOut_ = {
  code?: number;
  message?: string;
  data?: (CapabilityOut | null);
};
export type ApiResponse_ConfirmResponse_ = {
  code?: number;
  message?: string;
  data?: (ConfirmResponse | null);
};
export type ApiResponse_ConversationListResponse_ = {
  code?: number;
  message?: string;
  data?: (ConversationListResponse | null);
};
export type ApiResponse_ConversationMessagesResponse_ = {
  code?: number;
  message?: string;
  data?: (ConversationMessagesResponse | null);
};
export type ApiResponse_ConversationStartResponse_ = {
  code?: number;
  message?: string;
  data?: (ConversationStartResponse | null);
};
export type ApiResponse_CustomerListResponse_ = {
  code?: number;
  message?: string;
  data?: (CustomerListResponse | null);
};
export type ApiResponse_DeleteResponse_ = {
  code?: number;
  message?: string;
  data?: (DeleteResponse | null);
};
export type ApiResponse_DocumentPreviewResponse_ = {
  code?: number;
  message?: string;
  data?: (DocumentPreviewResponse | null);
};
export type ApiResponse_KnowledgeDeleteResponse_ = {
  code?: number;
  message?: string;
  data?: (KnowledgeDeleteResponse | null);
};
export type ApiResponse_KnowledgeItemOut_ = {
  code?: number;
  message?: string;
  data?: (KnowledgeItemOut | null);
};
export type ApiResponse_KnowledgeListResponse_ = {
  code?: number;
  message?: string;
  data?: (KnowledgeListResponse | null);
};
export type ApiResponse_MatchComputeResponse_ = {
  code?: number;
  message?: string;
  data?: (MatchComputeResponse | null);
};
export type ApiResponse_MatchDetailResponse_ = {
  code?: number;
  message?: string;
  data?: (MatchDetailResponse | null);
};
export type ApiResponse_MessageResponse_ = {
  code?: number;
  message?: string;
  data?: (MessageResponse | null);
};
export type ApiResponse_RequestSnapshotListResponse_ = {
  code?: number;
  message?: string;
  data?: (RequestSnapshotListResponse | null);
};
export type ApiResponse_UploadResult_ = {
  code?: number;
  message?: string;
  data?: (UploadResult | null);
};
export type ApiResponse_UserOut_ = {
  code?: number;
  message?: string;
  data?: (UserOut | null);
};
export type ApiResponse_VendorListResponse_ = {
  code?: number;
  message?: string;
  data?: (VendorListResponse | null);
};
export type ApiResponse_VendorOut_ = {
  code?: number;
  message?: string;
  data?: (VendorOut | null);
};
export type ApiResponse_dict_ = {
  code?: number;
  message?: string;
  data?: (Record<string, unknown> | null);
};
export type AssistantMessage = {
  role?: string;
  content: string;
  options?: string[];
  options_type?: "none" | "single" | "multi" | "actions";
};
export type AuditRequest = {
  action: "pass" | "reject";
  comment?: (string | null);
};
export type AuditResponse = {
  vendor_id: string;
  audit_status: "passed" | "rejected";
  audited_at: string;
};
export type AuthToken = {
  access_token: string;
  token_type?: string;
  expires_in: number;
  user: UserOut;
};
export type Body_upload_api_v1_files_upload_post = {
  file: string;
};
export type Body_upload_capability_api_v1_vendor_capability_upload_post = {
  vendor_id: string;
  documents?: string[];
};
export type CapabilityOut = {
  capability_id: string;
  vendor_id: string;
  structured_tags?: Record<string, unknown>;
  summary_text?: (string | null);
  audit_status?: "pending" | "passed" | "rejected";
  version?: number;
  updated_at?: string;
  doc_count?: number;
  completeness?: (number | null);
  source_map?: Record<string, unknown>;
  raw_text?: (string | null);
  doc_urls?: string[];
  doc_refs?: Record<string, unknown>[];
};
export type ConfirmRequest = {
  conversation_id: string;
  demand_points?: DemandPoint[];
};
export type ConfirmResponse = {
  request_id: string;
  version: number;
  redirect_to?: string;
  warnings?: string[];
};
export type ConversationListItem = {
  conversation_id: string;
  title?: string;
  status: "active" | "confirmed" | "closed";
  updated_at: string;
  last_request_id?: (string | null);
  request_count?: number;
};
export type ConversationListResponse = {
  conversations: ConversationListItem[];
  total: number;
};
export type ConversationMessageItem = {
  role: "assistant" | "user";
  content: string;
  error?: boolean;
  options?: string[];
  options_type?: "none" | "single" | "multi" | "actions";
  created_at?: (string | null);
};
export type ConversationMessagesResponse = {
  conversation_id: string;
  title?: string;
  status: "active" | "confirmed" | "closed";
  messages: ConversationMessageItem[];
  demand_points?: DemandPoint[];
  version?: (number | null);
  confirm_prompted?: boolean;
};
export type ConversationStartRequest = {
  user_id: string;
};
export type ConversationStartResponse = {
  conversation_id: string;
  first_message: AssistantMessage;
  demand_points?: DemandPoint[];
  title?: string;
};
export type CustomerItem = {
  user_id: string;
  phone: string;
  email?: (string | null);
  status?: "active" | "disabled";
  conversation_count?: number;
  request_count?: number;
  last_active_at?: (string | null);
  created_at: string;
};
export type CustomerListResponse = {
  list: CustomerItem[];
  total: number;
  page: number;
  page_size: number;
};
export type DeleteResponse = {
  id: string;
  deleted?: boolean;
  deleted_at: string;
};
export type DemandPoint = {
  key: string;
  label: string;
  value: (string | string[]);
  strictness?: "strict" | "best-effort";
  confidence?: number;
};
export type DocumentPreviewResponse = {
  doc_id: string;
  doc_name: string;
  page: number;
  content: string;
  highlight?: (string | null);
};
export type HTTPValidationError = {
  detail?: ValidationError[];
};
export type KnowledgeCreateRequest = {
  content: string;
  category?: (string | null);
  industry?: (string | null);
};
export type KnowledgeDeleteResponse = {
  knowledge_id: string;
  deleted?: boolean;
};
export type KnowledgeItemOut = {
  knowledge_id: string;
  content: string;
  category?: (string | null);
  industry?: (string | null);
  source?: (string | null);
  created_at: string;
};
export type KnowledgeListResponse = {
  list: KnowledgeItemOut[];
  total: number;
  page: number;
  page_size: number;
};
export type LoginRequest = {
  phone?: (string | null);
  email?: (string | null);
  password: string;
};
export type MatchComputeRequest = {
  request_id: string;
};
export type MatchComputeResponse = {
  run: MatchRun;
  match_results?: MatchItem[];
  demand_points?: DemandPoint[];
};
export type MatchDetailResponse = {
  match_id: string;
  request_id: string;
  vendor_id: string;
  company_name: string;
  matched_params?: MatchParam[];
  partial_params?: MatchParam[];
  missing_params?: MatchParam[];
  unmatched_params?: MatchParam[];
  match_reason?: (string | null);
  risk_warning?: (string | null);
  ai_comment?: (string | null);
  explanation_status?: "pending" | "ready";
};
export type MatchItem = {
  match_id: string;
  vendor_id: string;
  company_name: string;
  location?: (string | null);
  summary?: (string | null);
  match_score: number;
  semantic_score?: (number | null);
  match_source?: "llm" | "rule" | "hybrid";
  matched_count?: number;
  partial_count?: number;
  missing_count?: number;
  unmatched_count?: number;
};
export type MatchParam = {
  key: string;
  label: string;
  value: string;
  verdict: "matched" | "partial" | "missing" | "unmatched";
  strictness?: string;
  source_doc_id?: (string | null);
  source_doc_name?: (string | null);
  source_page?: (number | null);
  source_text?: (string | null);
};
export type MatchRun = {
  run_id: string;
  request_id: string;
  status?: "running" | "done" | "empty";
  total_vendors?: number;
  best_score?: (number | null);
  computation_time_ms?: number;
  created_at: string;
};
export type MessageRequest = {
  conversation_id: string;
  message: string;
  clicked_option?: (string | string[] | null);
};
export type MessageResponse = {
  assistant_message: AssistantMessage;
  demand_points?: DemandPoint[];
  title?: string;
  submitted?: boolean;
  redirect_to?: string;
  warnings?: string[];
};
export type RegisterRequest = {
  phone?: (string | null);
  email?: (string | null);
  password: string;
  role?: "vendor" | "customer";
  verify_code?: (string | null);
};
export type RequestSnapshot = {
  request_id: string;
  version: number;
  structured_demand?: Record<string, unknown>;
  created_at: string;
  match_count?: number;
};
export type RequestSnapshotListResponse = {
  requests: RequestSnapshot[];
  total: number;
};
export type SendCodeRequest = {
  phone?: (string | null);
  email?: (string | null);
  scene?: "register" | "login" | "reset";
};
export type UploadResult = {
  file_id: string;
  url: string;
  name: string;
  size: number;
  content_type?: (string | null);
};
export type UserOut = {
  user_id: string;
  phone?: (string | null);
  email?: (string | null);
  role: string;
  status?: string;
  created_at: string;
  vendor_id?: (string | null);
};
export type ValidationError = {
  loc: (string | number)[];
  msg: string;
  type: string;
};
export type VendorAuditItem = {
  vendor_id: string;
  company_name: string;
  location?: (string | null);
  main_industry?: (string | null);
  audit_status: "pending" | "passed" | "rejected";
  has_capability?: boolean;
  created_at: string;
};
export type VendorListResponse = {
  list: VendorAuditItem[];
  total: number;
  page: number;
  page_size: number;
};
export type VendorOut = {
  vendor_id: string;
  company_name: string;
  location?: (string | null);
  main_industry?: (string | null);
  credit_code?: (string | null);
  audit_status?: string;
  created_at: string;
};
export type VendorRegisterRequest = {
  company_name: string;
  location?: (string | null);
  main_industry?: (string | null);
  credit_code?: (string | null);
  license_file_id?: (string | null);
};
