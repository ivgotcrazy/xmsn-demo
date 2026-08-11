import { fileURLToPath, URL } from "node:url"

import vue from "@vitejs/plugin-vue"
import { defineConfig } from "vite"

const useMock = process.env.VITE_USE_MOCK ?? "true"
// M8 T8.2：生产容器部署于 /admin/ 子路径（vite base）；本地 dev 保持根路径
const base = process.env.VITE_BASE ?? "/"

export default defineConfig({
  base,
  plugins: [vue()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5174,
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
  define: {
    "import.meta.env.VITE_USE_MOCK": JSON.stringify(useMock),
  },
})
