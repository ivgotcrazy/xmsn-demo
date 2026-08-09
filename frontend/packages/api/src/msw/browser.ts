/**
 * MSW 浏览器 worker（架构 5.5：仅 dev 生效，VITE_USE_MOCK=true 时注入；生产构建不含）。
 */
import { setupWorker } from "msw/browser"

import { handlers } from "./handlers"

export const worker = setupWorker(...handlers)
