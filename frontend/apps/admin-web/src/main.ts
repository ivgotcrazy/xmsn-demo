/**
 * admin-web 入口：MSW mock 注入（VITE_USE_MOCK）→ Pinia → Router → 挂载。
 */
import { createPinia } from "pinia"
import { createApp } from "vue"

import "@xmsn/tokens/tokens.css"

import App from "./App.vue"
import { router } from "./router"

async function bootstrap(): Promise<void> {
  if (import.meta.env.VITE_USE_MOCK !== "false") {
    const { worker } = await import("@xmsn/api")
    await worker.start({ onUnhandledRequest: "bypass" })
  }

  const app = createApp(App)
  app.use(createPinia())
  app.use(router)
  app.mount("#app")
}

void bootstrap()
