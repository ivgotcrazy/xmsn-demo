<script setup lang="ts">
/**
 * 客户端布局（会话一体化）：顶部品牌 + 用户/退出；无菜单（客户端仅 02A 一页）。
 * B2B Service（MASTER.md）：根加 theme-b2b + 内嵌 NConfigProvider(themeB2bOverrides)，
 * 一次激活全部客户页（chat / matches / vendor）的藏青 + 蓝 CTA + Plus Jakarta Sans。
 */
import { useRouter } from "vue-router"
import { NButton, NConfigProvider } from "naive-ui"

import { themeB2bOverrides } from "@xmsn/tokens"

import { useAuthStore } from "@/stores/auth"

const router = useRouter()
const auth = useAuthStore()

function logout(): void {
  auth.logout()
  void router.push("/login")
}
</script>

<template>
  <div class="main-layout theme-b2b">
    <NConfigProvider :theme-overrides="themeB2bOverrides">
      <header class="main-layout__nav">
        <div class="main-layout__brand" @click="router.push('/customer/chat')">
          <span class="main-layout__mark" aria-hidden="true">需</span>
          <span>需脉枢纽</span>
        </div>
        <div class="main-layout__spacer" />
        <div class="main-layout__user">
          <span class="main-layout__who">
            客户<span v-if="auth.user"> · {{ auth.user.phone }}</span>
          </span>
          <NButton text size="small" class="main-layout__logout" @click="logout()">退出登录</NButton>
        </div>
      </header>
      <main class="main-layout__content">
        <RouterView />
      </main>
    </NConfigProvider>
  </div>
</template>

<style scoped>
@import url("https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap");

.main-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  color: var(--color-text);
  background: var(--color-background);
  font-family: var(--font-family-base);
  -webkit-font-smoothing: antialiased;
}
.main-layout__nav {
  box-sizing: border-box;
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  gap: var(--space-lg);
  height: 56px;
  padding: 0 var(--space-lg);
  background: var(--color-card);
  border-bottom: 1px solid var(--color-border);
}
.main-layout__brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 700;
  color: var(--color-primary);
  cursor: pointer;
  white-space: nowrap;
}
.main-layout__mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 8px;
  background: var(--color-primary);
  color: #fff;
  font-weight: 800;
  font-size: 15px;
}
.main-layout__spacer {
  flex: 1 1 0;
  min-width: 0;
}
.main-layout__user {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
  white-space: nowrap;
}
.main-layout__who {
  color: var(--color-muted-foreground);
  font-size: 13px;
  white-space: nowrap;
}
.main-layout__logout {
  color: var(--color-muted-foreground);
}
.main-layout__logout:hover {
  color: var(--color-accent);
}
.main-layout__content {
  flex: 1;
  width: 100%;
  padding: var(--space-12);
  box-sizing: border-box;
}
</style>
