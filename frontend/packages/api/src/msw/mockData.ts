/**
 * MSW mock 数据（手写，契约派生 handlers 的数据来源；架构 5.5）。
 * - T1.6 基础版：覆盖全部接口，支撑示例页自测
 * - T1.9 丰富版：对齐演示故事线（预置厂商/买家/需求/匹配）与 faker 随机
 * - 仅 dev 生效（VITE_USE_MOCK），生产构建不含 MSW
 *
 * key 约定："<METHOD> <path>"，与 msw/handlers.ts 生成物一一对应。
 */

export type MockResolver = (request: Request) => unknown | Promise<unknown>

const DEMO_USER_VENDOR = {
  user_id: "u-vendor-001",
  phone: "13800000001",
  email: "vendor@xmsn.demo",
  role: "vendor",
  status: "active",
  created_at: "2026-08-01T08:00:00Z",
}

const DEMO_USER_BUYER = {
  user_id: "u-buyer-001",
  phone: "13900000001",
  email: "buyer@xmsn.demo",
  role: "buyer",
  status: "active",
  created_at: "2026-08-01T08:00:00Z",
}

const DEMO_USER_ADMIN = {
  user_id: "u-admin-001",
  phone: "13800000000",
  email: "admin@xmsn.demo",
  role: "admin",
  status: "active",
  created_at: "2026-08-01T08:00:00Z",
}

const DEMO_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.mock"

/** 按手机号返回不同演示账号（13800000000=管理员 / 13800000001=厂商 / 其他=买家）。 */
function resolveDemoUser(phone: string | undefined): (typeof DEMO_USER_ADMIN)[] {
  if (phone === "13800000000") return [DEMO_USER_ADMIN]
  if (phone === "13800000001") return [DEMO_USER_VENDOR]
  return [DEMO_USER_BUYER]
}

export const mockData: Record<string, MockResolver | unknown> = {
  // ---- auth ----
  "POST /api/v1/auth/login": (request: Request) =>
    request
      .json()
      .then((body: { phone?: string }) => ({
        access_token: DEMO_TOKEN,
        token_type: "bearer",
        expires_in: 604800,
        user: resolveDemoUser(body.phone ?? "")[0],
      }))
      .catch(() => ({
        access_token: DEMO_TOKEN,
        token_type: "bearer",
        expires_in: 604800,
        user: DEMO_USER_BUYER,
      })),
  "POST /api/v1/auth/register": () => ({
    access_token: DEMO_TOKEN,
    token_type: "bearer",
    expires_in: 604800,
    user: DEMO_USER_BUYER,
  }),
  "POST /api/v1/auth/send-code": () => ({ sent: true }),
  "GET /api/v1/auth/me": () => DEMO_USER_BUYER,

  // ---- vendor ----
  "POST /api/v1/vendor/register": () => ({
    vendor_id: "v-001",
    company_name: "东莞某某电子有限公司",
    location: "广东东莞",
    main_industry: "消费电子",
    credit_code: "91441900MA4WU7XXXX",
    audit_status: "pending",
    created_at: "2026-08-02T03:00:00Z",
  }),
  "GET /api/v1/vendor/{vendor_id}": () => ({
    vendor_id: "v-001",
    company_name: "东莞某某电子有限公司",
    location: "广东东莞",
    main_industry: "消费电子",
    credit_code: "91441900MA4WU7XXXX",
    audit_status: "passed",
    created_at: "2026-08-02T03:00:00Z",
  }),
  "POST /api/v1/vendor/capability/upload": () => ({
    capability_id: "cap-001",
    vendor_id: "v-001",
    structured_tags: {
      product_types: ["机顶盒", "智能音箱", "IoT设备"],
      process_types: ["SMT贴片", "组装测试", "整机包装"],
      certifications: ["ISO9001", "ISO14001"],
      os_support: ["Linux", "Android"],
      interfaces: ["网口", "USB", "HDMI"],
      min_order_qty: 3000,
      lead_time_days: 20,
      application_scenarios: ["家庭娱乐", "智能家居"],
    },
    summary_text:
      "珠三角10年电子代工经验，专注机顶盒/智能音箱 ODM，具备 SMT+整机组装测试一体化能力，支持 Linux/Android 定制，月产能 50 万台。",
    raw_text:
      "本公司专注机顶盒/智能音箱 ODM 十余年，拥有 8 条 SMT 贴片线与组装测试一体化车间，支持 Linux/Android 双系统定制，月产能 50 万台。",
    doc_urls: ["产能介绍.pdf", "认证资质.pdf"],
    audit_status: "pending",
  }),
  "GET /api/v1/vendor/capability/{vendor_id}": () => ({
    capability_id: "cap-001",
    vendor_id: "v-001",
    structured_tags: {
      product_types: ["机顶盒", "智能音箱", "IoT设备"],
      process_types: ["SMT贴片", "组装测试", "整机包装"],
      certifications: ["ISO9001", "ISO14001"],
      os_support: ["Linux", "Android"],
      interfaces: ["网口", "USB", "HDMI"],
      min_order_qty: 3000,
      lead_time_days: 20,
      application_scenarios: ["家庭娱乐", "智能家居"],
    },
    summary_text:
      "珠三角10年电子代工经验，专注机顶盒/智能音箱 ODM，具备 SMT+整机组装测试一体化能力，支持 Linux/Android 定制，月产能 50 万台。",
    raw_text:
      "本公司专注机顶盒/智能音箱 ODM 十余年，拥有 8 条 SMT 贴片线与组装测试一体化车间，支持 Linux/Android 双系统定制，月产能 50 万台。",
    doc_urls: ["产能介绍.pdf", "认证资质.pdf"],
    audit_status: "passed",
  }),

  // ---- files ----
  "POST /api/v1/files/upload": () => ({
    file_id: "file-001",
    url: "/data/uploads/license.pdf",
    name: "营业执照.pdf",
    size: 204800,
    content_type: "application/pdf",
  }),

  // ---- conversation ----
  "POST /api/v1/conversation/start": () => ({
    conversation_id: "conv-001",
    first_message: {
      role: "assistant",
      content: "您好！我是需脉AI选型助手。请告诉我您需要找什么类型的代工厂？",
      options: ["机顶盒", "智能音箱", "IoT设备", "其他"],
    },
    current_slots: {},
  }),
  "POST /api/v1/conversation/message": () => ({
    assistant_message: {
      role: "assistant",
      content: "好的，机顶盒代工，需要Linux系统。请问您需要哪些接口？",
      options: ["网口", "USB", "HDMI", "GPIO"],
    },
    updated_slots: { product_type: "机顶盒", os_support: ["Linux"] },
    slot_confidence: { product_type: 1.0, os_support: 1.0 },
  }),
  "POST /api/v1/conversation/finish": () => ({
    profile: {
      product_type: "机顶盒",
      os_support: ["Linux"],
      interfaces: ["网口", "USB"],
      min_order_qty: 5000,
      certifications: ["ISO9001"],
    },
    version: 1,
    unset_fields: ["lead_time_days", "application_scenarios"],
  }),
  "POST /api/v1/conversation/confirm": () => ({
    request_id: "req-001",
    version: 2,
    redirect_to: "/buyer/matches/req-001",
  }),
  "GET /api/v1/conversations": () => ({
    conversations: [
      {
        conversation_id: "conv-001",
        status: "confirmed",
        updated_at: "2026-08-05T09:30:00Z",
        last_request_id: "req-001",
        request_count: 2,
      },
      {
        conversation_id: "conv-002",
        status: "active",
        updated_at: "2026-08-06T10:00:00Z",
        last_request_id: null,
        request_count: 0,
      },
    ],
    total: 2,
  }),
  "GET /api/v1/conversation/{conversation_id}/requests": () => ({
    requests: [
      {
        request_id: "req-001",
        version: 1,
        structured_demand: { product_type: "机顶盒", os_support: ["Linux"] },
        created_at: "2026-08-05T09:00:00Z",
        match_count: 5,
      },
      {
        request_id: "req-002",
        version: 2,
        structured_demand: {
          product_type: "机顶盒",
          os_support: ["Linux"],
          interfaces: ["网口", "USB"],
          min_order_qty: 5000,
        },
        created_at: "2026-08-05T09:30:00Z",
        match_count: 3,
      },
    ],
    total: 2,
  }),

  // ---- match ----
  "POST /api/v1/match/compute": () => ({
    match_results: [
      {
        match_id: "m-001",
        vendor_id: "v-001",
        company_name: "东莞某某电子有限公司",
        location: "广东东莞",
        summary: "珠三角10年机顶盒ODM经验，Linux 深度定制，支持网口/USB/HDMI 接口。",
        match_score: 92.5,
        semantic_score: 0.82,
        param_hit_rate: 0.96,
        critical_fail: false,
        match_source: "hybrid",
        matched_count: 7,
        unmatched_count: 1,
      },
      {
        match_id: "m-002",
        vendor_id: "v-002",
        company_name: "深圳智联科技",
        location: "广东深圳",
        summary: "机顶盒/OTT 产品制造，Android 平台为主，少量 Linux 定制能力。",
        match_score: 78.0,
        semantic_score: 0.71,
        param_hit_rate: 0.82,
        critical_fail: false,
        match_source: "llm",
        matched_count: 6,
        unmatched_count: 2,
      },
      {
        match_id: "m-003",
        vendor_id: "v-003",
        company_name: "惠州华创电子",
        location: "广东惠州",
        summary: "消费电子整机代工，偏智能音箱/穿戴，机顶盒经验较少。",
        match_score: 45.0,
        semantic_score: 0.58,
        param_hit_rate: 0.52,
        critical_fail: true,
        match_source: "llm",
        matched_count: 3,
        unmatched_count: 5,
      },
    ],
    total_matches: 3,
    computation_time_ms: 1250,
  }),
  "GET /api/v1/match/detail/{match_id}": () => ({
    match_id: "m-001",
    request_id: "req-001",
    vendor_id: "v-001",
    company_name: "东莞某某电子有限公司",
    matched_params: [
      { key: "product_type", label: "产品类型", value: "机顶盒", verdict: "matched" },
      { key: "os_support", label: "操作系统", value: "Linux", verdict: "matched" },
      { key: "interfaces", label: "接口", value: "网口,USB,HDMI", verdict: "matched" },
      { key: "min_order_qty", label: "起订量", value: "5000", verdict: "matched" },
    ],
    partial_params: [{ key: "certifications", label: "认证", value: "ISO9001", verdict: "partial" }],
    unmatched_params: [{ key: "application_scenarios", label: "应用场景", value: "家庭娱乐", verdict: "unmatched" }],
    ai_comment:
      "该厂商在机顶盒代工、Linux 系统定制与所需接口（网口/USB/HDMI）上高度匹配，起订量满足要求；认证 ISO9001 具备但未覆盖全部所需项，整体推荐度较高。",
    explanation_status: "ready",
  }),

  // ---- admin ----
  "POST /api/v1/admin/vendors/{vendor_id}/audit": () => ({
    vendor_id: "v-001",
    audit_status: "passed",
    audited_at: "2026-08-07T06:00:00Z",
  }),
  "GET /api/v1/admin/vendors": () => ({
    list: [
      {
        vendor_id: "v-001",
        company_name: "东莞某某电子有限公司",
        location: "广东东莞",
        main_industry: "消费电子",
        audit_status: "pending",
        has_capability: true,
        created_at: "2026-08-02T03:00:00Z",
      },
      {
        vendor_id: "v-002",
        company_name: "深圳智联科技",
        location: "广东深圳",
        main_industry: "消费电子",
        audit_status: "pending",
        has_capability: true,
        created_at: "2026-08-03T04:00:00Z",
      },
      {
        vendor_id: "v-003",
        company_name: "惠州华创电子",
        location: "广东惠州",
        main_industry: "消费电子",
        audit_status: "passed",
        has_capability: true,
        created_at: "2026-08-01T02:00:00Z",
      },
    ],
    total: 3,
    page: 1,
    page_size: 20,
  }),
  "GET /api/v1/admin/stats": () => ({
    total_users: 12,
    total_requests: 24,
    total_vendors: 6,
    total_matches: 58,
  }),
  "GET /api/v1/admin/requests": () => ({
    list: [
      {
        request_id: "req-001",
        conversation_id: "conv-001",
        version: 2,
        structured_demand: {
          product_type: "机顶盒",
          os_support: ["Linux"],
          min_order_qty: 5000,
        },
        created_at: "2026-08-05T09:30:00Z",
        match_count: 3,
      },
      {
        request_id: "req-002",
        conversation_id: "conv-003",
        version: 1,
        structured_demand: { product_type: "智能音箱", os_support: ["Android"] },
        created_at: "2026-08-06T07:00:00Z",
        match_count: 2,
      },
    ],
    total: 2,
    page: 1,
    page_size: 20,
  }),

  // ---- documents ----
  "GET /api/v1/documents/{doc_id}/preview": () => ({
    doc_id: "doc-001",
    doc_name: "产能介绍.pdf",
    page: 3,
    content:
      "本公司具备机顶盒整机 ODM 能力，支持 Linux/Android 双系统定制，提供网口、USB、HDMI 等标准接口，月产能 50 万台……",
    highlight: "支持 Linux/Android 双系统定制",
  }),
}

export async function resolveMock(key: string, request: Request): Promise<unknown> {
  const entry = mockData[key]
  if (entry === undefined) return null
  return typeof entry === "function" ? (entry as MockResolver)(request) : entry
}
