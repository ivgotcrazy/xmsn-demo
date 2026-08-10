<script setup lang="ts">
/**
 * 厂商端布局（原型 01B：经典后台布局，左侧 240px 深色侧边导航 COMP-005）。
 * 菜单项：控制台 / 录入能力 / 我的档案；顶部用户信息。
 */
import { useRoute, useRouter } from "vue-router"
import { NButton } from "naive-ui"

import { useAuthStore } from "@/stores/auth"

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const menus = [
  { key: "/vendor/dashboard", label: "控制台" },
  { key: "/vendor/capability", label: "能力录入" },
  { key: "/vendor/profile", label: "能力档案" },
]

function go(key: string): void {
  void router.push(key)
}

function logout(): void {
  auth.logout()
  void router.push("/login")
}
</script>

<template>
  <div class="vendor-layout">
    <aside class="vendor-layout__side">
      <div class="vendor-layout__logo" @click="router.push('/vendor/dashboard')">需脉枢纽</div>
      <nav class="vendor-layout__nav">
        <div
          v-for="m in menus"
          :key="m.key"
          class="vendor-layout__item"
          :class="{ 'is-active': route.path === m.key }"
          @click="go(m.key)"
        >
          {{ m.label }}
        </div>
      </nav>
    </aside>
    <div class="vendor-layout__main">
      <header class="vendor-layout__top">
        <span class="vendor-layout__crumb">厂商端 / {{ route.meta.title as string }}</span>
        <div class="vendor-layout__user">
          <span class="vendor-layout__who">{{ auth.user?.phone ?? "厂商" }}</span>
          <NButton text size="small" @click="logout()">退出登录</NButton>
        </div>
      </header>
      <main class="vendor-layout__content">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<style scoped>
.vendor-layout {
  display: flex;
  min-height: 100vh;
}
.vendor-layout__side {
  width: var(--width-sidebar);
  flex: none;
  display: flex;
  flex-direction: column;
  background: var(--gray-900);
  color: var(--gray-100);
  padding: var(--space-16) 0;
}
.vendor-layout__logo {
  padding: 0 var(--space-24) var(--space-32);
  font-size: var(--font-size-18);
  font-weight: var(--font-weight-700);
  color: #fff;
  cursor: pointer;
}
.vendor-layout__nav {
  display: flex;
  flex-direction: column;
}
.vendor-layout__item {
  height: 48px;
  display: flex;
  align-items: center;
  padding: 0 var(--space-24);
  font-size: var(--font-size-14);
  color: var(--gray-300);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-standard);
}
.vendor-layout__item:hover {
  background: var(--gray-800);
  color: #fff;
}
.vendor-layout__item.is-active {
  background: var(--gray-800);
  color: #fff;
  border-left: 3px solid var(--color-primary);
}
.vendor-layout__main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.vendor-layout__top {
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
  padding: 0 var(--space-24);
  background: var(--color-bg-panel);
  border-bottom: var(--border-width-1) solid var(--color-border-subtle);
}
.vendor-layout__crumb {
  font-size: var(--font-size-13);
  color: var(--color-text-secondary);
}
.vendor-layout__user {
  display: flex;
  align-items: center;
  gap: var(--space-12);
  flex-shrink: 0;
  white-space: nowrap;
}
.vendor-layout__who {
  font-size: var(--font-size-13);
  white-space: nowrap;
}
.vendor-layout__content {
  flex: 1;
  padding: var(--space-24);
  overflow: auto;
  max-width: var(--breakpoint-lg);
  width: 100%;
  margin: 0 auto;
  box-sizing: border-box;
}
</style>
