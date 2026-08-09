<script setup lang="ts">
/**
 * 买家端布局（会话一体化）：顶部品牌 + 用户/退出；无菜单（买家端仅 02A 一页）。
 */
import { useRouter } from "vue-router"
import { NButton } from "naive-ui"

import { useAuthStore } from "@/stores/auth"

const router = useRouter()
const auth = useAuthStore()

function logout(): void {
  auth.logout()
  void router.push("/login")
}
</script>

<template>
  <div class="main-layout">
    <header class="main-layout__nav">
      <div class="main-layout__brand" @click="router.push('/buyer/chat')">需脉枢纽</div>
      <div class="main-layout__spacer" />
      <div class="main-layout__user">
        <span class="main-layout__who">
          买家<span v-if="auth.user"> · {{ auth.user.phone }}</span>
        </span>
        <NButton text size="small" @click="logout()">退出登录</NButton>
      </div>
    </header>
    <main class="main-layout__content">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.main-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}
.main-layout__nav {
  box-sizing: border-box;
  display: flex;
  align-items: center;
  gap: var(--space-24);
  height: 56px;
  padding: 0 var(--space-24);
  background: var(--color-bg-panel);
  border-bottom: var(--border-width-1) solid var(--color-border-subtle);
}
.main-layout__brand {
  font-size: var(--font-size-18);
  font-weight: var(--font-weight-700);
  color: var(--color-primary);
  cursor: pointer;
  white-space: nowrap;
}
.main-layout__spacer {
  flex: 1 1 0;
  min-width: 0;
}
.main-layout__user {
  display: flex;
  align-items: center;
  gap: var(--space-12);
  flex-shrink: 0;
  white-space: nowrap;
}
.main-layout__who {
  color: var(--color-text-secondary);
  font-size: var(--font-size-13);
  white-space: nowrap;
}
.main-layout__content {
  flex: 1;
  width: 100%;
  padding: var(--space-12);
  box-sizing: border-box;
}
</style>
