/**
 * API 手写薄封装（架构 5.4）：JWT 注入 + 统一响应 {code,message,data} 解包 + 分页/轮询辅助 + SSE。
 * 生成客户端（src/client.ts）统一经此 request 发送请求。
 */

const TOKEN_KEY = "xmsn_token"

/** 统一响应信封（架构 5.3）：{ code, message, data }，code != 0 为业务/系统错误。 */
interface Envelope<T> {
  code?: number
  message?: string
  data?: T
}

export function getToken(): string | null {
  return typeof localStorage !== "undefined" ? localStorage.getItem(TOKEN_KEY) : null
}

export function setToken(token: string | null): void {
  if (typeof localStorage === "undefined") return
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

export interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE"
  body?: unknown
  query?: Record<string, unknown>
  headers?: Record<string, string>
  formData?: FormData
  signal?: AbortSignal
}

export class ApiError extends Error {
  code: number
  constructor(code: number, message: string) {
    super(message)
    this.code = code
  }
}

/** 统一请求：附加 Bearer Token，解包 {code,message,data}，非零 code 抛 ApiError。 */
export async function request<T>(url: string, opts: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, query, headers = {}, formData, signal } = opts

  let finalUrl = url
  if (query) {
    const qs = Object.entries(query)
      .filter(([, v]) => v !== undefined && v !== null && v !== "")
      .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
      .join("&")
    if (qs) finalUrl += (finalUrl.includes("?") ? "&" : "?") + qs
  }

  const h: Record<string, string> = { ...headers }
  const token = getToken()
  if (token) h.Authorization = `Bearer ${token}`

  let bodyPayload: BodyInit | undefined
  if (formData) {
    bodyPayload = formData
  } else if (body !== undefined) {
    h["Content-Type"] = "application/json"
    bodyPayload = JSON.stringify(body)
  }

  const res = await fetch(finalUrl, { method, headers: h, body: bodyPayload, signal })
  let json: Envelope<T> | T
  try {
    json = (await res.json()) as Envelope<T> | T
  } catch {
    throw new ApiError(res.status, `HTTP ${res.status}`)
  }
  const envelope = json as Envelope<T>
  if (typeof envelope.code === "number" && envelope.code !== 0) {
    throw new ApiError(envelope.code, envelope.message || "请求失败")
  }
  return (envelope.data !== undefined ? envelope.data : json) as T
}

/** 二进制请求（非 JSON 信封）：JWT 注入 + 返回 Blob（供 iframe 内嵌预览 / 下载）。 */
export async function requestBlob(url: string, opts: RequestOptions = {}): Promise<Blob> {
  const h: Record<string, string> = {}
  const token = getToken()
  if (token) h.Authorization = `Bearer ${token}`
  const res = await fetch(url, {
    method: opts.method || "GET",
    headers: h,
    signal: opts.signal,
  })
  if (!res.ok) throw new ApiError(res.status, `HTTP ${res.status}`)
  return await res.blob()
}

/** 厂商原始文档直读（源文件，非文本提取）：GET /api/v1/documents/{docId}/file → Blob。 */
export async function documentsDocIdFile(docId: string): Promise<Blob> {
  return requestBlob(`/api/v1/documents/${encodeURIComponent(docId)}/file`)
}

/** SSE 流式对话（架构 5.4：OpenAPI 无法描述流式响应，fetch + ReadableStream 封装）。 */
export async function* sseStream<T = string>(url: string, opts: RequestOptions = {}): AsyncGenerator<T> {
  const h: Record<string, string> = {}
  const token = getToken()
  if (token) h.Authorization = `Bearer ${token}`
  if (opts.body !== undefined) h["Content-Type"] = "application/json"

  const res = await fetch(url, {
    method: opts.method || "POST",
    headers: h,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    signal: opts.signal,
  })
  if (!res.ok || !res.body) throw new ApiError(res.status, `SSE HTTP ${res.status}`)

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buf = ""
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    const lines = buf.split("\n")
    buf = lines.pop() ?? ""
    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed.startsWith("data:")) continue
      const payload = trimmed.slice(5).trim()
      if (!payload) continue
      if (payload === "[DONE]") return
      try {
        yield JSON.parse(payload) as T
      } catch {
        yield payload as unknown as T
      }
    }
  }
}

/** 异步结果轮询辅助（架构 5.4：匹配解释骨架轮询）。 */
export async function pollUntil<T>(
  fn: () => Promise<T>,
  isDone: (v: T) => boolean,
  opts: { intervalMs?: number; timeoutMs?: number; onPending?: () => void } = {},
): Promise<T> {
  const intervalMs = opts.intervalMs ?? 1500
  const timeoutMs = opts.timeoutMs ?? 60_000
  const start = Date.now()
  for (;;) {
    const v = await fn()
    if (isDone(v)) return v
    opts.onPending?.()
    if (Date.now() - start > timeoutMs) return v
    await new Promise((r) => setTimeout(r, intervalMs))
  }
}
