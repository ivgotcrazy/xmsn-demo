/**
 * @xmsn/types 包：领域共享类型与业务常量。
 * - 契约类型（openapi 派生）经 @xmsn/api re-export，保证前后端单一真相源
 * - 领域常量（需求 Schema 品类 / 匹配三态 / 权重）与后端架构 6.6 对齐
 */
export * from "@xmsn/api"

// ============ 需求 Schema 品类（本体 D1，供需Schema §3.4/3.5） ============
export type ParamKey =
  | "product_type" | "certifications" | "moq" | "lead_time_days" | "monthly_capacity"
  | "process_types" | "application_scenario" | "customization_needs" | "budget_range"
  | "service_years" | "industry_cases" | "os" | "interfaces" | "wireless"
  | "mic_array" | "speaker_power" | "voice_assistant" | "decode_capability"
  | "soc_platform" | "tv_standard" | "output_interfaces" | "memory_storage"
  | "comm_protocol" | "power_supply" | "ip_rating" | "sensors" | "extended"

export interface ParamFieldMeta {
  key: ParamKey
  label: string
  /** multi 表示多值（数组），single 单值，number 数值，text 自由文本（本体 value_type） */
  kind: "multi" | "single" | "number" | "text"
  options?: string[]
}

/** 需求 Schema 字段元信息（PoC 展示 fallback；权威=后端本体 ontology.json，D5 schema 感知） */
export const REQUEST_SCHEMA_FIELDS: ParamFieldMeta[] = [
  { key: "product_type", label: "产品类型", kind: "single" },
  { key: "certifications", label: "认证", kind: "multi" },
  { key: "moq", label: "起订量", kind: "number" },
  { key: "lead_time_days", label: "交期(天)", kind: "number" },
  { key: "monthly_capacity", label: "月产能", kind: "number" },
  { key: "process_types", label: "制程能力", kind: "multi" },
  { key: "application_scenario", label: "应用场景", kind: "text" },
  { key: "customization_needs", label: "定制需求", kind: "text" },
  { key: "budget_range", label: "预算范围", kind: "text" },
  { key: "service_years", label: "服务年限", kind: "number" },
  { key: "industry_cases", label: "行业经验/案例", kind: "text" },
  { key: "os", label: "操作系统", kind: "multi" },
  { key: "interfaces", label: "接口", kind: "multi" },
  { key: "wireless", label: "无线", kind: "multi" },
]

export const PARAM_LABELS: Record<string, string> = Object.fromEntries(
  REQUEST_SCHEMA_FIELDS.map((f) => [f.key, f.label]),
)

// ============ 厂商能力 Schema（供给侧，本体同 key D1） ============
/** 能力字段 key（与需求侧同 key，D1；硬能力=RULE 判定主锚） */
export type CapabilityKey =
  | "process_types"
  | "certifications"
  | "os"
  | "interfaces"
  | "moq"
  | "lead_time_days"
  | "monthly_capacity"
  | "product_types"
  | "application_scenarios"
  | "customization"

export interface CapabilityFieldMeta {
  key: CapabilityKey
  label: string
  kind: "multi" | "number" | "single"
  /** 硬能力（RULE 判定，匹配主锚；缺失计入完备度）；false=软标签（语义/召回） */
  hard: boolean
  /** 缺失时的建议引导文案（能力档案页展示） */
  suggest?: string
}

/**
 * 厂商能力 Schema（薄而准确）：硬能力 = RULE 判定主锚（缺失计入完备度）；
 * 软标签 = 语义召回（产品类型为历史产品标签，不设硬门槛，创新产品不误杀）。
 * 档案页按此遍历渲染，保证页面内容与 schema 一一对应。
 */
export const CAPABILITY_SCHEMA_FIELDS: CapabilityFieldMeta[] = [
  { key: "process_types", label: "工艺", kind: "multi", hard: true, suggest: "建议补充「工艺/产线能力」文档" },
  { key: "certifications", label: "认证", kind: "multi", hard: true, suggest: "建议补充「认证证书」文档" },
  { key: "os", label: "操作系统", kind: "multi", hard: true, suggest: "建议补充「支持系统/平台」文档" },
  { key: "interfaces", label: "接口", kind: "multi", hard: true, suggest: "建议补充「接口规格」文档" },
  { key: "moq", label: "起订量", kind: "number", hard: true, suggest: "建议补充「报价/产能参数」文档" },
  { key: "lead_time_days", label: "交期(天)", kind: "number", hard: true, suggest: "建议补充「交期/生产周期」文档" },
  { key: "monthly_capacity", label: "月产能", kind: "number", hard: true, suggest: "建议补充「产线产能介绍」文档" },
  { key: "product_types", label: "产品类型", kind: "multi", hard: false },
  { key: "application_scenarios", label: "应用场景", kind: "multi", hard: false },
  { key: "customization", label: "定制化", kind: "single", hard: false },
]

export const CAPABILITY_LABELS: Record<string, string> = Object.fromEntries(
  CAPABILITY_SCHEMA_FIELDS.map((f) => [f.key, f.label]),
)

// ============ 匹配四档（D10：missing 独立成组） ============
export type Verdict = "matched" | "partial" | "missing" | "unmatched"

export const VERDICT_META: Record<Verdict, { label: string; tagType: "success" | "warning" | "default" | "error" }> = {
  matched: { label: "已匹配", tagType: "success" },
  partial: { label: "部分匹配", tagType: "warning" },
  missing: { label: "未声明", tagType: "default" },
  unmatched: { label: "未匹配", tagType: "error" },
}

// ============ 审核 / 角色 / 会话 ============
export type AuditStatus = "pending" | "passed" | "rejected"
export type UserRole = "vendor" | "customer" | "admin"
export type ConversationStatus = "active" | "confirmed" | "closed"

export const AUDIT_META: Record<AuditStatus, { label: string; tagType: "warning" | "success" | "error" }> = {
  pending: { label: "审核中", tagType: "warning" },
  passed: { label: "已通过", tagType: "success" },
  rejected: { label: "已驳回", tagType: "error" },
}
