<script setup lang="ts">
/**
 * 管理端布局（COMP-005 侧边导航，240px）：侧边菜单 + 顶部栏 + 内容区。
 */
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import { NButton, NMenu } from "naive-ui"

import { useAuthStore } from "@/stores/auth"

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const title = computed(() => (route.meta.title as string | undefined) ?? "")

const menus = [
  { key: "/admin/dashboard", label: "数据概览" },
  { key: "/admin/requests", label: "需求与匹配" },
  { key: "/admin/vendors", label: "厂商产品" },
]

function onMenuSelect(key: string | number): void {
  void router.push(String(key))
}

function logout(): void {
  auth.logout()
  void router.push("/admin/login")
}
</script>

<template>
  <div class="admin-layout">
    <aside class="admin-layout__side">
      <div class="admin-layout__brand">需脉枢纽</div>
      <NMenu
        :options="menus"
        :value="route.path"
        :root-indent="16"
        @update:value="onMenuSelect"
      />
    </aside>
    <div class="admin-layout__body">
      <header class="admin-layout__top">
        <span class="admin-layout__title">{{ title }}</span>
        <div class="admin-layout__user">
          <span>管理员</span>
          <NButton text size="small" @click="logout()">退出登录</NButton>
        </div>
      </header>
      <main class="admin-layout__content">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<style scoped>
.admin-layout {
  display: flex;
  min-height: 100vh;
}
.admin-layout__side {
  width: var(--width-sidebar);
  flex: none;
  background: var(--color-bg-panel);
  border-right: var(--border-width-1) solid var(--color-border-subtle);
  padding: var(--space-16) var(--space-8);
}
.admin-layout__brand {
  padding: 0 var(--space-16) var(--space-24);
  font-size: var(--font-size-18);
  font-weight: var(--font-weight-700);
  color: var(--color-primary);
}
.admin-layout__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.admin-layout__top {
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
  padding: 0 var(--space-24);
  background: var(--color-bg-panel);
  border-bottom: var(--border-width-1) solid var(--color-border-subtle);
}
.admin-layout__title {
  font-size: var(--font-size-16);
  font-weight: var(--font-weight-600);
}
.admin-layout__user {
  display: flex;
  align-items: center;
  gap: var(--space-12);
  flex-shrink: 0;
  white-space: nowrap;
  font-size: var(--font-size-13);
}
.admin-layout__content {
  flex: 1;
  padding: var(--space-24);
  overflow: auto;
}
</style>
