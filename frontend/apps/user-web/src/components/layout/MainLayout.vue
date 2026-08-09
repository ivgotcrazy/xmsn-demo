<script setup lang="ts">
/**
 * 买家端布局（原型 02A/02B）：顶部品牌 + 导航（需求对话/匹配结果）+ 用户/退出。
 * 页面内再实现各自标题栏（02A 需脉AI选型助手 / 02B 匹配结果）。
 */
import { useRoute, useRouter } from "vue-router"
import { NButton, NMenu } from "naive-ui"

import { useAuthStore } from "@/stores/auth"

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const menus = [
  { key: "/buyer/chat", label: "需求对话" },
  { key: "/buyer/matches", label: "匹配结果" },
]

function onMenuSelect(key: string): void {
  void router.push(key)
}

function logout(): void {
  auth.logout()
  void router.push("/login")
}
</script>

<template>
  <div class="main-layout">
    <header class="main-layout__nav">
      <div class="main-layout__brand" @click="router.push('/buyer/chat')">需脉枢纽</div>
      <NMenu
        mode="horizontal"
        :options="menus"
        :value="route.path"
        class="main-layout__menu"
        @update:value="onMenuSelect"
      />
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
.main-layout__menu {
  flex: 0 1 auto;
  min-width: 0;
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
