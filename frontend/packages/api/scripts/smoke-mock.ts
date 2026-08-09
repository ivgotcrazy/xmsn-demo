/**
 * mock 链路冒烟测试（T1.6 验收）：用 msw/node 加载契约派生 handlers，验证请求被拦截且返回统一响应。
 * 运行：cd frontend/packages/api && node_modules/.bin/tsx scripts/smoke-mock.ts
 */
import { setupServer } from "msw/node"

import { handlers } from "../src/msw/handlers"

const server = setupServer(...handlers)
server.listen({ onUnhandledRequest: "error" })

async function main(): Promise<void> {
  // 1) 登录
  const login = await fetch("http://localhost/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ phone: "13800000000", password: "123456" }),
  })
  const loginJson = await login.json()
  console.log("login:", login.status, "code=", loginJson.code, "data.user.role=", loginJson.data?.user?.role)

  // 2) 对话 start
  const start = await fetch("http://localhost/api/v1/conversation/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: "u-buyer-001" }),
  })
  const startJson = await start.json()
  console.log("start:", start.status, "first_message=", startJson.data?.first_message?.content?.slice(0, 12))

  // 3) 匹配 compute
  const match = await fetch("http://localhost/api/v1/match/compute", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ request_id: "req-001" }),
  })
  const matchJson = await match.json()
  console.log("match:", match.status, "total=", matchJson.data?.total_matches, "top=", matchJson.data?.match_results?.[0]?.match_score)

  // 4) admin stats
  const stats = await fetch("http://localhost/api/v1/admin/stats")
  const statsJson = await stats.json()
  console.log("stats:", stats.status, "total_vendors=", statsJson.data?.total_vendors)
}

main()
  .then(() => {
    server.close()
    console.log("SMOKE OK")
  })
  .catch((e) => {
    server.close()
    console.error("SMOKE FAIL:", e)
    process.exit(1)
  })
