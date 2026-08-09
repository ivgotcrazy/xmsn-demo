import { fileURLToPath, URL } from "node:url"

import vue from "@vitejs/plugin-vue"
import { defineConfig } from "vite"

// VITE_USE_MOCK 默认 true（dev 走 MSW mock，架构 5.5）；生产构建不含 MSW
const useMock = process.env.VITE_USE_MOCK ?? "true"

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      // 真实联调（M7）：mock 关闭时走后端；mock 开启时被 MSW 拦截
      "/api": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
  define: {
    "import.meta.env.VITE_USE_MOCK": JSON.stringify(useMock),
  },
})
