/**
 * @xmsn/types 包：领域共享类型与业务常量。
 * - 契约类型（openapi 派生）经 @xmsn/api re-export，保证前后端单一真相源
 * - 领域常量（需求 Schema 品类 / 匹配三态 / 权重）与后端架构 6.6 对齐
 */
export * from "@xmsn/api"

// ============ 需求 Schema 品类（架构 6.6） ============
export type ParamKey =
  | "product_type"
  | "os_support"
  | "certifications"
  | "application_scenes"
  | "interfaces"
  | "min_order_qty"
  | "process"
  | "lead_time_days"
  | "customization"

export interface ParamFieldMeta {
  key: ParamKey
  label: string
  /** multi 表示多值（数组），single 单值，number 数值 */
  kind: "multi" | "single" | "number"
  options?: string[]
  /** 参数匹配权重（架构 6.6 权重表） */
  weight: number
  /** 关键参数：LLM verdict critical_fail 时封顶 50% */
  critical?: boolean
  /** 是否允许用户显式排除 */
  excludable?: boolean
}

/** 需求 Schema 字段元信息（与后端 params.yaml / 权重表一致） */
export const REQUEST_SCHEMA_FIELDS: ParamFieldMeta[] = [
  { key: "product_type", label: "产品类型", kind: "single", weight: 2.0, critical: true },
  { key: "os_support", label: "操作系统", kind: "multi", weight: 1.5, critical: true },
  { key: "certifications", label: "认证", kind: "multi", weight: 1.5 },
  { key: "application_scenes", label: "应用场景", kind: "multi", weight: 1.0 },
  { key: "interfaces", label: "接口", kind: "multi", weight: 1.0 },
  { key: "min_order_qty", label: "起订量", kind: "number", weight: 1.0 },
  { key: "process", label: "工艺", kind: "multi", weight: 0.5 },
  { key: "lead_time_days", label: "交期(天)", kind: "number", weight: 0.5 },
  { key: "customization", label: "定制化", kind: "single", weight: 0.5, excludable: true },
]

export const PARAM_LABELS: Record<string, string> = Object.fromEntries(
  REQUEST_SCHEMA_FIELDS.map((f) => [f.key, f.label]),
)

// ============ 匹配三态（架构 6.3 匹配） ============
export type Verdict = "matched" | "partial" | "unmatched"

export const VERDICT_META: Record<Verdict, { label: string; tagType: "success" | "warning" | "error" }> = {
  matched: { label: "已匹配", tagType: "success" },
  partial: { label: "部分匹配", tagType: "warning" },
  unmatched: { label: "未匹配", tagType: "error" },
}

// ============ 审核 / 角色 / 会话 ============
export type AuditStatus = "pending" | "passed" | "rejected"
export type UserRole = "vendor" | "buyer" | "admin"
export type ConversationStatus = "active" | "confirmed" | "closed"

export const AUDIT_META: Record<AuditStatus, { label: string; tagType: "warning" | "success" | "error" }> = {
  pending: { label: "审核中", tagType: "warning" },
  passed: { label: "已通过", tagType: "success" },
  rejected: { label: "已驳回", tagType: "error" },
}
