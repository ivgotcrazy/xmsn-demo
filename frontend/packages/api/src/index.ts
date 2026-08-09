/**
 * @xmsn/api 包入口（手写）：统一导出 http 封装 / 生成类型 / 生成客户端 / mock 链路。
 */
export * from "./http"
export * from "./types"
export * from "./client"
export { mockData, resolveMock, type MockResolver } from "./msw/mockData"
export { worker } from "./msw/browser"
