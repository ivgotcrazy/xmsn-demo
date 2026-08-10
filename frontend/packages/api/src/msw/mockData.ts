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

/** 演示需求点集合：机顶盒（固定字段 + 扩展需求点：外壳颜色/双系统/海外认证）。 */
const DEMAND_POINTS_STB = [
  { key: "product_type", label: "产品类型", value: "机顶盒", confidence: 1.0 },
  { key: "os_support", label: "操作系统", value: ["Linux"], confidence: 1.0 },
  { key: "interfaces", label: "接口", value: ["网口", "USB"], confidence: 1.0 },
  { key: "min_order_qty", label: "起订量", value: "5000 台", confidence: 1.0 },
  { key: "certifications", label: "认证", value: ["ISO9001"], confidence: 0.9 },
  { key: "appearance", label: "外壳颜色", value: "黑色", confidence: 0.95 },
  { key: "dual_system", label: "双系统", value: "支持", confidence: 0.9 },
  { key: "overseas_cert", label: "海外认证", value: ["CE", "FCC"], confidence: 0.85 },
]

/** 演示需求点集合：智能音箱（进行中会话）。 */
const DEMAND_POINTS_SPEAKER = [
  { key: "product_type", label: "产品类型", value: "智能音箱", confidence: 1.0 },
  { key: "os_support", label: "操作系统", value: ["Linux"], confidence: 1.0 },
  { key: "appearance", label: "外壳颜色", value: "白色", confidence: 0.9 },
]

/** 一会话一产品：产品类型萃取映射（会话标题=产品类型名；含首次萃取回复与需求点集合）。 */
const PRODUCT_PROFILES: Record<
  string,
  { title: string; reply: string; options: string[]; points: typeof DEMAND_POINTS_STB }
> = {
  机顶盒: {
    title: "机顶盒",
    reply: "好的，机顶盒代工，需要Linux系统。请问您需要哪些接口？",
    options: ["网口", "USB", "HDMI", "GPIO"],
    points: DEMAND_POINTS_STB,
  },
  智能音箱: {
    title: "智能音箱",
    reply: "好的，智能音箱代工，需要什么操作系统？",
    options: ["Linux", "Android", "RTOS"],
    points: DEMAND_POINTS_SPEAKER,
  },
}
const PRODUCT_KEYWORDS: Record<string, string[]> = {
  机顶盒: ["机顶盒", "机顶", "STB", "电视盒", "盒子"],
  智能音箱: ["智能音箱", "音箱", "音响", "speaker"],
}
/** 会话锁定产品：conv-001 已确认机顶盒；conv-002 进行中智能音箱；新建会话无锁定。 */
const SESSION_LOCKED: Record<string, string> = {
  "conv-001": "机顶盒",
  "conv-002": "智能音箱",
}
/** 从用户消息中检测提到的产品类型（返回标题；未命中返回 undefined）。 */
function detectProduct(message: string): string | undefined {
  for (const [title, kws] of Object.entries(PRODUCT_KEYWORDS)) {
    if (kws.some((k) => message.includes(k))) return title
  }
  return undefined
}

// 逻辑删除状态（仅 dev mock；真实后端用 deleted_at 标记过滤，数据保留有挖掘价值）
const deletedConversations = new Set<string>()
const deletedRequests = new Set<string>()

const deletedAt = (): string => new Date().toISOString()

// capability 演示状态（仅 dev mock）：文档集合 + 档案版本，增/删文档触发重新解析（version+1）
const capDemoDocs: string[] = ["产能介绍.pdf", "认证资质.pdf"]
let capDemoVersion = 3
const capNow = (): string => new Date().toISOString()

function buildCapabilityDoc(vendorId: string, docs: string[], version: number, audit: string) {
  return {
    capability_id: "cap-001",
    vendor_id: vendorId,
    structured_tags: {
      product_types: ["机顶盒", "智能音箱", "IoT设备"],
      process_types: ["SMT贴片", "组装测试", "整机包装"],
      certifications: ["ISO9001", "ISO14001"],
      os_support: ["Linux", "Android"],
      interfaces: ["网口", "USB", "HDMI"],
      moq: 3000,
      lead_time_days: 20,
      application_scenarios: ["家庭娱乐", "智能家居"],
    },
    summary_text:
      "珠三角10年电子代工经验，专注机顶盒/智能音箱 ODM，具备 SMT+整机组装测试一体化能力，支持 Linux/Android 定制，月产能 50 万台。",
    version,
    updated_at: capNow(),
    doc_count: docs.length,
    completeness: 0.857,
    source_map: {
      process_types: { doc_name: "产能介绍.pdf", page: 1, confidence: 0.92 },
      certifications: { doc_name: "认证资质.pdf", page: 1, confidence: 0.9 },
      os_support: { doc_name: "产能介绍.pdf", page: 2, confidence: 0.88 },
      interfaces: { doc_name: "产能介绍.pdf", page: 2, confidence: 0.85 },
      lead_time_days: { doc_name: "产能介绍.pdf", page: 3, confidence: 0.78 },
      moq: { doc_name: "产能介绍.pdf", page: 1, confidence: 0.5 },
      product_types: { doc_name: "产能介绍.pdf", page: 1, confidence: 0.8 },
      application_scenarios: { doc_name: "产能介绍.pdf", page: 2, confidence: 0.72 },
    },
    raw_text:
      "本公司专注机顶盒/智能音箱 ODM 十余年，拥有 8 条 SMT 贴片线与组装测试一体化车间，支持 Linux/Android 双系统定制，月产能 50 万台。",
    doc_urls: docs,
    audit_status: audit,
  }
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
  "GET /api/v1/vendor/{vendor_id}": (request: Request) => {
    const parts = new URL(request.url).pathname.split("/").filter(Boolean)
    const id = parts[parts.length - 1] ?? "v-001"
    const VENDORS: Record<string, object> = {
      "v-001": {
        vendor_id: "v-001",
        company_name: "东莞某某电子有限公司",
        location: "广东东莞",
        main_industry: "消费电子",
        credit_code: "91441900MA4WU7XXXX",
        audit_status: "passed",
        created_at: "2026-08-02T03:00:00Z",
      },
      "v-002": {
        vendor_id: "v-002",
        company_name: "深圳智联科技",
        location: "广东深圳",
        main_industry: "消费电子",
        credit_code: "91440300MA5KX9YYYY",
        audit_status: "pending",
        created_at: "2026-08-03T04:00:00Z",
      },
      "v-003": {
        vendor_id: "v-003",
        company_name: "惠州华创电子",
        location: "广东惠州",
        main_industry: "消费电子",
        credit_code: "91441300MA4T7ZZZZZ",
        audit_status: "passed",
        created_at: "2026-08-01T02:00:00Z",
      },
    }
    return VENDORS[id] ?? VENDORS["v-001"]
  },
  "POST /api/v1/vendor/capability/upload": (request: Request) =>
    request
      .formData()
      .then((fd) => {
        const files = fd.getAll("documents") as File[]
        const names = files.length ? files.map((f) => f.name) : ["产能介绍.pdf", "认证资质.pdf"]
        names.forEach((n) => {
          if (!capDemoDocs.includes(n)) capDemoDocs.push(n)
        })
        capDemoVersion += 1
        return buildCapabilityDoc((fd.get("vendor_id") as string) ?? "v-001", [...capDemoDocs], capDemoVersion, "pending")
      })
      .catch(() => ({
        capability_id: "cap-001",
        vendor_id: "v-001",
        structured_tags: {},
        summary_text: "",
        version: capDemoVersion,
        updated_at: capNow(),
        doc_count: 0,
        completeness: 0,
        source_map: {},
        doc_urls: [],
        audit_status: "pending",
      })),
  "GET /api/v1/vendor/capability/{vendor_id}": () =>
    buildCapabilityDoc("v-001", [...capDemoDocs], capDemoVersion, "passed"),
  "DELETE /api/v1/vendor/capability/{vendor_id}/documents/{document_id}": (request: Request) => {
    const parts = new URL(request.url).pathname.split("/").filter(Boolean)
    const docId = decodeURIComponent(parts[parts.length - 1] ?? "")
    const idx = capDemoDocs.indexOf(docId)
    if (idx >= 0) capDemoDocs.splice(idx, 1)
    capDemoVersion += 1
    return buildCapabilityDoc("v-001", [...capDemoDocs], capDemoVersion, "passed")
  },

  // ---- files ----
  "POST /api/v1/files/upload": () => ({
    file_id: "file-001",
    url: "/data/uploads/license.pdf",
    name: "营业执照.pdf",
    size: 204800,
    content_type: "application/pdf",
  }),

  // ---- conversation ----
  // 新建会话：返回新会话 conv-003 与开场语（前端插入列表顶部并高亮）
  "POST /api/v1/conversation/start": () => ({
    conversation_id: "conv-003",
    first_message: {
      role: "assistant",
      content: "您好！我是需脉AI选型助手。请告诉我您需要找什么类型的代工厂？",
      options: ["机顶盒", "智能音箱", "IoT设备", "其他"],
    },
    demand_points: [],
    title: "新会话",
  }),
  "POST /api/v1/conversation/message": (request: Request) =>
    request
      .json()
      .then((body: { conversation_id?: string; message?: string }) => {
        const conversationId = body.conversation_id ?? "conv-003"
        const text = body.message ?? ""
        const locked = SESSION_LOCKED[conversationId]
        const detected = detectProduct(text)
        // 守卫：会话已锁定产品 A，用户提到产品 B → 不切换，引导新建会话
        if (locked && detected && detected !== locked) {
          return {
            assistant_message: {
              role: "assistant",
              content: `检测到您提到「${detected}」，当前会话已聚焦「${locked}」。如需咨询 ${detected}，建议新建会话。`,
              options: [],
            },
            demand_points: PRODUCT_PROFILES[locked].points,
            title: locked,
          }
        }
        // 萃取：检测到产品（新会话首次锁定）
        if (detected) {
          const p = PRODUCT_PROFILES[detected]
          return {
            assistant_message: { role: "assistant", content: p.reply, options: p.options },
            demand_points: p.points,
            title: p.title,
          }
        }
        // 已锁定会话：补充其他需求（通用确认，不改变产品聚焦）
        if (locked) {
          return {
            assistant_message: {
              role: "assistant",
              content: "已记录，还有其他需求需要补充吗？",
              options: [],
            },
            demand_points: PRODUCT_PROFILES[locked].points,
            title: locked,
          }
        }
        // 新会话未检测到产品：通用追问
        return {
          assistant_message: {
            role: "assistant",
            content: "您好！我是需脉AI选型助手。请告诉我您需要找什么类型的代工厂？",
            options: ["机顶盒", "智能音箱", "IoT设备", "其他"],
          },
          demand_points: [],
          title: "新会话",
        }
      })
      .catch(() => ({
        assistant_message: {
          role: "assistant",
          content: "好的，机顶盒代工，需要Linux系统。请问您需要哪些接口？",
          options: ["网口", "USB", "HDMI", "GPIO"],
        },
        demand_points: DEMAND_POINTS_STB,
        title: "机顶盒",
      })),
  "POST /api/v1/conversation/finish": () => ({
    version: 1,
    demand_points: DEMAND_POINTS_STB,
  }),
  "POST /api/v1/conversation/confirm": () => ({
    request_id: "req-002",
    version: 2,
    redirect_to: "",
  }),
  "GET /api/v1/conversations": () => {
    const all = [
      {
        conversation_id: "conv-001",
        title: "机顶盒",
        status: "confirmed",
        updated_at: "2026-08-05T09:30:00Z",
        last_request_id: "req-001",
        request_count: 2,
      },
      {
        conversation_id: "conv-002",
        title: "智能音箱",
        status: "active",
        updated_at: "2026-08-06T10:00:00Z",
        last_request_id: null,
        request_count: 0,
      },
    ]
    const conversations = all.filter((c) => !deletedConversations.has(c.conversation_id))
    return { conversations, total: conversations.length }
  },
  "GET /api/v1/conversation/{conversation_id}/requests": (request: Request) => {
    const parts = new URL(request.url).pathname.split("/").filter(Boolean)
    const id = parts[parts.length - 2] ?? ""
    // 按会话维度：仅 conv-001（已确认）有匹配记录，其余会话（进行中）为空
    if (id === "conv-001") {
      const all = [
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
      ]
      const requests = all.filter((r) => !deletedRequests.has(r.request_id))
      return { requests, total: requests.length }
    }
    return { requests: [], total: 0 }
  },
  "DELETE /api/v1/conversation/{conversation_id}": (request: Request) => {
    const parts = new URL(request.url).pathname.split("/").filter(Boolean)
    const id = parts[parts.length - 1] ?? ""
    deletedConversations.add(id)
    return { id, deleted: true, deleted_at: deletedAt() }
  },
  "DELETE /api/v1/conversation/{conversation_id}/requests/{request_id}": (request: Request) => {
    const parts = new URL(request.url).pathname.split("/").filter(Boolean)
    const requestId = parts[parts.length - 1] ?? ""
    deletedRequests.add(requestId)
    return { id: requestId, deleted: true, deleted_at: deletedAt() }
  },
  "GET /api/v1/conversation/{conversation_id}/messages": (request: Request) => {
    const parts = new URL(request.url).pathname.split("/").filter(Boolean)
    const id = parts[parts.length - 2] ?? ""
    // conv-001：已确认完整现场（已生成 v1 档案）
    if (id === "conv-001") {
      return {
        conversation_id: "conv-001",
        title: "机顶盒",
        status: "confirmed",
        messages: [
          { role: "assistant", content: "您好！我是需脉AI选型助手。请告诉我您需要找什么类型的代工厂？", options: ["机顶盒", "智能音箱", "IoT设备", "其他"], created_at: "2026-08-05T09:00:00Z" },
          { role: "user", content: "机顶盒", created_at: "2026-08-05T09:01:00Z" },
          { role: "assistant", content: "好的，机顶盒代工，需要 Linux 系统。请问您需要哪些接口？", options: ["网口", "USB", "HDMI", "GPIO"], created_at: "2026-08-05T09:01:30Z" },
          { role: "user", content: "网口、USB", created_at: "2026-08-05T09:02:00Z" },
          { role: "assistant", content: "接口已记录：网口、USB。起订量大概多少？", created_at: "2026-08-05T09:02:30Z" },
          { role: "user", content: "5000 台", created_at: "2026-08-05T09:03:00Z" },
          { role: "assistant", content: "核心需求已明确，确认完成？还是继续补充？", options: ["确认完成", "继续补充"], created_at: "2026-08-05T09:03:30Z" },
          { role: "user", content: "确认完成", created_at: "2026-08-05T09:04:00Z" },
          { role: "assistant", content: "已生成需求档案 v1", created_at: "2026-08-05T09:04:30Z" },
        ],
        demand_points: DEMAND_POINTS_STB,
        version: 1,
        confirm_prompted: true,
      }
    }
    // conv-002：进行中（未完成档案）
    if (id === "conv-002") {
      return {
        conversation_id: "conv-002",
        title: "智能音箱",
        status: "active",
        messages: [
          { role: "assistant", content: "您好！我是需脉AI选型助手。请告诉我您需要找什么类型的代工厂？", options: ["机顶盒", "智能音箱", "IoT设备", "其他"], created_at: "2026-08-06T10:00:00Z" },
          { role: "user", content: "智能音箱", created_at: "2026-08-06T10:01:00Z" },
          { role: "assistant", content: "智能音箱代工，需要什么操作系统？", options: ["Linux", "Android", "RTOS"], created_at: "2026-08-06T10:01:30Z" },
          { role: "user", content: "Linux", created_at: "2026-08-06T10:02:00Z" },
          { role: "assistant", content: "好的，Linux 系统已记录。还需要补充其他要求吗？", created_at: "2026-08-06T10:02:30Z" },
        ],
        demand_points: DEMAND_POINTS_SPEAKER,
        version: null,
        confirm_prompted: true,
      }
    }
    // 其他（如新建会话 conv-003）：空现场
    return {
      conversation_id: id,
      title: "新会话",
      status: "active",
      messages: [],
      demand_points: [],
      version: null,
      confirm_prompted: false,
    }
  },

  // ---- match ----
  "POST /api/v1/match/compute": (request: Request) =>
    request
      .json()
      .then((body: { request_id?: string }) => {
        const requestId = body.request_id ?? ""
        // 空匹配示例：需求已提交匹配，但本次未找到任何合适厂商（匹配实体仍存在 status=empty）
        if (requestId === "req-003") {
          return {
            run: {
              run_id: "run-003",
              request_id: "req-003",
              status: "empty",
              total_vendors: 0,
              best_score: null,
              computation_time_ms: 820,
              created_at: "2026-08-09T11:00:00Z",
            },
            match_results: [],
            demand_points: DEMAND_POINTS_STB,
          }
        }
        // 正常匹配：一个需求档案对应一个匹配实体（run），run 下挂多个厂商匹配结果
        const runId = requestId === "req-002" ? "run-002" : "run-001"
        return {
          run: {
            run_id: runId,
            request_id: requestId,
            status: "done",
            total_vendors: 3,
            best_score: 92.5,
            computation_time_ms: 1250,
            created_at: "2026-08-05T09:30:00Z",
          },
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
          demand_points: requestId === "req-002" ? DEMAND_POINTS_STB : DEMAND_POINTS_STB,
        }
      })
      .catch(() => ({
        run: {
          run_id: "run-err",
          request_id: "",
          status: "empty",
          total_vendors: 0,
          best_score: null,
          computation_time_ms: 0,
          created_at: "2026-08-10T00:00:00Z",
        },
        match_results: [],
        demand_points: [],
      })),
  "GET /api/v1/match/detail/{match_id}": (request: Request) => {
    const parts = new URL(request.url).pathname.split("/").filter(Boolean)
    const id = parts[parts.length - 1] ?? "m-001"
    const base = { request_id: "req-001", explanation_status: "ready" as const }
    // m-002：深圳智联科技（Android 为主，Linux 定制有限）
    if (id === "m-002") {
      return {
        match_id: "m-002",
        vendor_id: "v-002",
        company_name: "深圳智联科技",
        matched_params: [
          { key: "product_type", label: "产品类型", value: "机顶盒", verdict: "matched", source_doc_id: "doc-001", source_doc_name: "产能介绍.pdf", source_page: 1, source_text: "专注机顶盒/OTT 制造" },
          { key: "os_support", label: "操作系统", value: "Linux", verdict: "partial", source_doc_id: "doc-001", source_doc_name: "产能介绍.pdf", source_page: 2, source_text: "Android 为主，少量 Linux 定制" },
        ],
        partial_params: [],
        unmatched_params: [
          { key: "interfaces", label: "接口", value: "网口、USB、HDMI", verdict: "unmatched", source_doc_id: "doc-001", source_doc_name: "产能介绍.pdf", source_page: 2, source_text: "主要提供 HDMI/USB，网口需确认" },
        ],
        ai_comment: "该厂商以 Android 平台为主，Linux 定制能力有限，接口覆盖部分满足，整体匹配度中等。",
        ...base,
      }
    }
    // m-003：惠州华创电子（偏智能音箱，机顶盒经验少，关键不符）
    if (id === "m-003") {
      return {
        match_id: "m-003",
        vendor_id: "v-003",
        company_name: "惠州华创电子",
        matched_params: [
          { key: "product_type", label: "产品类型", value: "智能音箱", verdict: "matched", source_doc_id: "doc-001", source_doc_name: "产能介绍.pdf", source_page: 1, source_text: "偏智能音箱/穿戴" },
        ],
        partial_params: [],
        unmatched_params: [
          { key: "os_support", label: "操作系统", value: "Linux", verdict: "unmatched", source_doc_id: "doc-001", source_doc_name: "产能介绍.pdf", source_page: 1, source_text: "机顶盒经验较少" },
        ],
        ai_comment: "该厂商偏智能音箱/穿戴，机顶盒代工经验较少，关键参数匹配不符，需谨慎评估。",
        ...base,
      }
    }
    // m-001：东莞某某电子有限公司（默认）
    return {
      match_id: "m-001",
      vendor_id: "v-001",
      company_name: "东莞某某电子有限公司",
      matched_params: [
        { key: "product_type", label: "产品类型", value: "机顶盒", verdict: "matched", source_doc_id: "doc-001", source_doc_name: "产能介绍.pdf", source_page: 1, source_text: "专注机顶盒/智能音箱 ODM 十余年" },
        { key: "os_support", label: "操作系统", value: "Linux", verdict: "matched", source_doc_id: "doc-001", source_doc_name: "产能介绍.pdf", source_page: 1, source_text: "支持 Linux/Android 双系统定制" },
        { key: "interfaces", label: "接口", value: "网口,USB,HDMI", verdict: "matched", source_doc_id: "doc-001", source_doc_name: "产能介绍.pdf", source_page: 2, source_text: "支持网口/USB/HDMI 等接口" },
        { key: "min_order_qty", label: "起订量", value: "5000", verdict: "matched", source_doc_id: "doc-001", source_doc_name: "产能介绍.pdf", source_page: 2, source_text: "月产能 50 万台，起订量灵活" },
      ],
      partial_params: [
        { key: "certifications", label: "认证", value: "ISO9001", verdict: "partial", source_doc_id: "doc-002", source_doc_name: "认证资质.pdf", source_page: 1, source_text: "已通过 ISO9001 认证" },
      ],
      unmatched_params: [
        { key: "application_scenarios", label: "应用场景", value: "家庭娱乐", verdict: "unmatched", source_doc_id: "doc-001", source_doc_name: "产能介绍.pdf", source_page: 3, source_text: "未提及家庭娱乐类应用场景" },
      ],
      ai_comment:
        "该厂商在机顶盒代工、Linux 系统定制与所需接口（网口/USB/HDMI）上高度匹配，起订量满足要求；认证 ISO9001 具备但未覆盖全部所需项，整体推荐度较高。",
      ...base,
    }
  },

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
  "GET /api/v1/admin/buyers": (request: Request) => {
    const url = new URL(request.url)
    const keyword = (url.searchParams.get("keyword") ?? "").trim().toLowerCase()
    const status = url.searchParams.get("status")
    const all = [
      { user_id: "u-buyer-001", phone: "13900000001", email: "buyer@xmsn.demo", status: "active", conversation_count: 2, request_count: 2, last_active_at: "2026-08-10T08:00:00Z", created_at: "2026-08-01T08:00:00Z" },
      { user_id: "u-buyer-002", phone: "13912340002", email: "lihua@qq.com", status: "active", conversation_count: 5, request_count: 4, last_active_at: "2026-08-09T14:20:00Z", created_at: "2026-08-02T09:00:00Z" },
      { user_id: "u-buyer-003", phone: "13912340003", email: "wangfang@163.com", status: "active", conversation_count: 3, request_count: 2, last_active_at: "2026-08-08T11:00:00Z", created_at: "2026-08-03T10:30:00Z" },
      { user_id: "u-buyer-004", phone: "13912340004", email: "zhangwei@aliyun.com", status: "active", conversation_count: 1, request_count: 1, last_active_at: "2026-08-07T16:45:00Z", created_at: "2026-08-04T13:00:00Z" },
      { user_id: "u-buyer-005", phone: "13912340005", email: "chenjing@outlook.com", status: "disabled", conversation_count: 4, request_count: 3, last_active_at: "2026-08-05T09:30:00Z", created_at: "2026-08-05T09:00:00Z" },
      { user_id: "u-buyer-006", phone: "13912340006", email: "liuyang@126.com", status: "active", conversation_count: 7, request_count: 6, last_active_at: "2026-08-10T09:10:00Z", created_at: "2026-08-06T15:20:00Z" },
      { user_id: "u-buyer-007", phone: "13912340007", email: "zhaolei@qq.com", status: "active", conversation_count: 2, request_count: 1, last_active_at: "2026-08-06T10:00:00Z", created_at: "2026-08-07T08:40:00Z" },
      { user_id: "u-buyer-008", phone: "13912340008", email: "sunli@163.com", status: "active", conversation_count: 0, request_count: 0, last_active_at: null, created_at: "2026-08-08T12:00:00Z" },
    ]
    let list = all
    if (status) list = list.filter((b) => b.status === status)
    if (keyword) {
      list = list.filter((b) => b.phone.toLowerCase().includes(keyword) || (b.email ?? "").toLowerCase().includes(keyword))
    }
    return { list, total: list.length, page: 1, page_size: 20 }
  },
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
        buyer_phone: "13900000001",
        created_at: "2026-08-05T09:30:00Z",
        run: {
          run_id: "run-001",
          request_id: "req-001",
          status: "done",
          total_vendors: 3,
          best_score: 92.5,
          computation_time_ms: 1250,
          created_at: "2026-08-05T09:30:00Z",
        },
      },
      {
        request_id: "req-002",
        conversation_id: "conv-003",
        version: 1,
        structured_demand: { product_type: "智能音箱", os_support: ["Android"] },
        buyer_phone: "13912340002",
        created_at: "2026-08-06T07:00:00Z",
        run: {
          run_id: "run-002",
          request_id: "req-002",
          status: "done",
          total_vendors: 2,
          best_score: 81.0,
          computation_time_ms: 980,
          created_at: "2026-08-06T07:00:00Z",
        },
      },
      {
        request_id: "req-003",
        conversation_id: "conv-002",
        version: 1,
        structured_demand: { product_type: "智能音箱", os_support: ["Linux"], appearance: "白色" },
        buyer_phone: "13912340005",
        created_at: "2026-08-09T11:00:00Z",
        run: {
          run_id: "run-003",
          request_id: "req-003",
          status: "empty",
          total_vendors: 0,
          best_score: null,
          computation_time_ms: 820,
          created_at: "2026-08-09T11:00:00Z",
        },
      },
    ],
    total: 3,
    page: 1,
    page_size: 20,
  }),
  "GET /api/v1/admin/logs": (request: Request) => {
    const url = new URL(request.url)
    const action = url.searchParams.get("action")
    const all = [
      { log_id: "log-001", action: "vendor_audit", action_label: "厂商审核", target_type: "vendor", target_id: "v-003", admin_name: "管理员", detail: { result: "通过", vendor: "惠州华创电子" }, created_at: "2026-08-07T06:00:00Z" },
      { log_id: "log-002", action: "vendor_audit", action_label: "厂商审核", target_type: "vendor", target_id: "v-001", admin_name: "管理员", detail: { result: "通过", vendor: "东莞某某电子有限公司" }, created_at: "2026-08-06T05:00:00Z" },
      { log_id: "log-003", action: "login", action_label: "管理员登录", target_type: "admin", target_id: "u-admin-001", admin_name: "管理员", detail: { phone: "13800000000" }, created_at: "2026-08-10T08:05:00Z" },
      { log_id: "log-004", action: "login", action_label: "管理员登录", target_type: "admin", target_id: "u-admin-001", admin_name: "管理员", detail: { phone: "13800000000" }, created_at: "2026-08-09T09:00:00Z" },
      { log_id: "log-005", action: "export", action_label: "导出数据", target_type: "request", target_id: "req-001", admin_name: "管理员", detail: { file: "requests.csv", rows: 3 }, created_at: "2026-08-10T10:20:00Z" },
      { log_id: "log-006", action: "config_change", action_label: "配置变更", target_type: "config", target_id: "match_threshold", admin_name: "管理员", detail: { key: "match_threshold", value: 0.3 }, created_at: "2026-08-08T14:00:00Z" },
      { log_id: "log-007", action: "vendor_audit", action_label: "厂商审核", target_type: "vendor", target_id: "v-002", admin_name: "管理员", detail: { result: "驳回", vendor: "深圳智联科技", comment: "资料不完整" }, created_at: "2026-08-05T11:30:00Z" },
      { log_id: "log-008", action: "export", action_label: "导出数据", target_type: "buyer", target_id: "u-buyer-001", admin_name: "管理员", detail: { file: "requests.csv", rows: 8 }, created_at: "2026-08-10T11:00:00Z" },
    ]
    const list = action ? all.filter((l) => l.action === action) : all
    return { list, total: list.length, page: 1, page_size: 20 }
  },

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
