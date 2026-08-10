/* 生成物（只读勿手改）—— 由 scripts/generate.ts 从 openapi.json 契约快照生成 */
/* MSW handlers：契约派生，数据来自 src/msw/mockData.ts（T1.9 丰富） */
import { http, HttpResponse } from "msw"
import { resolveMock } from "./mockData"

export const handlers = [
  http.get("*/healthz", async ({ request }) => {
    const data = await resolveMock("GET /healthz", request)
    return HttpResponse.json({ code: 0, message: "ok", data })
  }),
  http.post("*/api/v1/auth/register", async ({ request }) => {
    const data = await resolveMock("POST /api/v1/auth/register", request)
    return HttpResponse.json({ code: 0, message: "ok", data })
  }),
  http.post("*/api/v1/auth/login", async ({ request }) => {
    const data = await resolveMock("POST /api/v1/auth/login", request)
    return HttpResponse.json({ code: 0, message: "ok", data })
  }),
  http.post("*/api/v1/auth/send-code", async ({ request }) => {
    const data = await resolveMock("POST /api/v1/auth/send-code", request)
    return HttpResponse.json({ code: 0, message: "ok", data })
  }),
  http.get("*/api/v1/auth/me", async ({ request }) => {
    const data = await resolveMock("GET /api/v1/auth/me", request)
    return HttpResponse.json({ code: 0, message: "ok", data })
  }),
  http.post("*/api/v1/vendor/register", async ({ request }) => {
    const data = await resolveMock("POST /api/v1/vendor/register", request)
    return HttpResponse.json({ code: 0, message: "ok", data })
  }),
  http.get("*/api/v1/vendor/:vendor_id", async ({ request }) => {
    const data = await resolveMock("GET /api/v1/vendor/{vendor_id}", request)
    return HttpResponse.json({ code: 0, message: "ok", data })
  }),
  http.post("*/api/v1/vendor/capability/upload", async ({ request }) => {
    const data = await resolveMock("POST /api/v1/vendor/capability/upload", request)
    return HttpResponse.json({ code: 0, message: "ok", data })
  }),
  http.get("*/api/v1/vendor/capability/:vendor_id", async ({ request }) => {
    const data = await resolveMock("GET /api/v1/vendor/capability/{vendor_id}", request)
    return HttpResponse.json({ code: 0, message: "ok", data })
  }),
  http.post("*/api/v1/files/upload", async ({ request }) => {
    const data = await resolveMock("POST /api/v1/files/upload", request)
    return HttpResponse.json({ code: 0, message: "ok", data })
  }),
  http.post("*/api/v1/conversation/start", async ({ request }) => {
    const data = await resolveMock("POST /api/v1/conversation/start", request)
    return HttpResponse.json({ code: 0, message: "ok", data })
  }),
  http.post("*/api/v1/conversation/message", async ({ request }) => {
    const data = await resolveMock("POST /api/v1/conversation/message", request)
    return HttpResponse.json({ code: 0, message: "ok", data })
  }),
  http.post("*/api/v1/conversation/finish", async ({ request }) => {
    const data = await resolveMock("POST /api/v1/conversation/finish", request)
    return HttpResponse.json({ code: 0, message: "ok", data })
  }),
  http.post("*/api/v1/conversation/confirm", async ({ request }) => {
    const data = await resolveMock("POST /api/v1/conversation/confirm", request)
    return HttpResponse.json({ code: 0, message: "ok", data })
  }),
  http.get("*/api/v1/conversation/:conversation_id/messages", async ({ request }) => {
    const data = await resolveMock("GET /api/v1/conversation/{conversation_id}/messages", request)
    return HttpResponse.json({ code: 0, message: "ok", data })
  }),
  http.get("*/api/v1/conversation/:conversation_id/requests", async ({ request }) => {
    const data = await resolveMock("GET /api/v1/conversation/{conversation_id}/requests", request)
    return HttpResponse.json({ code: 0, message: "ok", data })
  }),
  http.delete("*/api/v1/conversation/:conversation_id", async ({ request }) => {
    const data = await resolveMock("DELETE /api/v1/conversation/{conversation_id}", request)
    return HttpResponse.json({ code: 0, message: "ok", data })
  }),
  http.delete("*/api/v1/conversation/:conversation_id/requests/:request_id", async ({ request }) => {
    const data = await resolveMock("DELETE /api/v1/conversation/{conversation_id}/requests/{request_id}", request)
    return HttpResponse.json({ code: 0, message: "ok", data })
  }),
  http.get("*/api/v1/conversations", async ({ request }) => {
    const data = await resolveMock("GET /api/v1/conversations", request)
    return HttpResponse.json({ code: 0, message: "ok", data })
  }),
  http.post("*/api/v1/match/compute", async ({ request }) => {
    const data = await resolveMock("POST /api/v1/match/compute", request)
    return HttpResponse.json({ code: 0, message: "ok", data })
  }),
  http.get("*/api/v1/match/detail/:match_id", async ({ request }) => {
    const data = await resolveMock("GET /api/v1/match/detail/{match_id}", request)
    return HttpResponse.json({ code: 0, message: "ok", data })
  }),
  http.post("*/api/v1/admin/vendors/:vendor_id/audit", async ({ request }) => {
    const data = await resolveMock("POST /api/v1/admin/vendors/{vendor_id}/audit", request)
    return HttpResponse.json({ code: 0, message: "ok", data })
  }),
  http.get("*/api/v1/admin/vendors", async ({ request }) => {
    const data = await resolveMock("GET /api/v1/admin/vendors", request)
    return HttpResponse.json({ code: 0, message: "ok", data })
  }),
  http.get("*/api/v1/admin/stats", async ({ request }) => {
    const data = await resolveMock("GET /api/v1/admin/stats", request)
    return HttpResponse.json({ code: 0, message: "ok", data })
  }),
  http.get("*/api/v1/admin/requests", async ({ request }) => {
    const data = await resolveMock("GET /api/v1/admin/requests", request)
    return HttpResponse.json({ code: 0, message: "ok", data })
  }),
  http.get("*/api/v1/admin/buyers", async ({ request }) => {
    const data = await resolveMock("GET /api/v1/admin/buyers", request)
    return HttpResponse.json({ code: 0, message: "ok", data })
  }),
  http.get("*/api/v1/admin/logs", async ({ request }) => {
    const data = await resolveMock("GET /api/v1/admin/logs", request)
    return HttpResponse.json({ code: 0, message: "ok", data })
  }),
  http.get("*/api/v1/documents/:doc_id/preview", async ({ request }) => {
    const data = await resolveMock("GET /api/v1/documents/{doc_id}/preview", request)
    return HttpResponse.json({ code: 0, message: "ok", data })
  }),
  http.get("*/healthz", () => HttpResponse.json({ code: 0, message: "ok", data: { status: "ok" } }))
]
