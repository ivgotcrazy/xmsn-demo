<script setup lang="ts">
/**
 * 管理端布局（COMP-005 侧边导航，240px）：侧边菜单 + 顶部栏 + 内容区。
 */
import { computed, h } from "vue"
import { useRoute, useRouter } from "vue-router"
import { NButton, NMenu } from "naive-ui"
import {
  BusinessOutline,
  DocumentTextOutline,
  GitCompareOutline,
  PeopleOutline,
  PieChartOutline,
} from "@vicons/ionicons5"

import { useAuthStore } from "@/stores/auth"

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const title = computed(() => (route.meta.title as string | undefined) ?? "")

const renderIcon = (icon: unknown) => () => h(icon as never)

const menus = [
  { key: "/admin/dashboard", label: "数据概览", icon: renderIcon(PieChartOutline) },
  { key: "/admin/customers", label: "客户管理", icon: renderIcon(PeopleOutline) },
  { key: "/admin/vendors", label: "厂商管理", icon: renderIcon(BusinessOutline) },
  { key: "/admin/requests", label: "需求匹配", icon: renderIcon(GitCompareOutline) },
  { key: "/admin/logs", label: "事件日志", icon: renderIcon(DocumentTextOutline) },
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
      <div class="admin-layout__brand">
        <span class="admin-layout__brand-mark">需</span>
        <span class="admin-layout__brand-name">需脉枢纽</span>
      </div>
      <div class="admin-layout__menu">
        <NMenu
          :options="menus"
          :value="route.path"
          inverted
          :root-indent="16"
          @update:value="onMenuSelect"
        />
      </div>
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
  display: flex;
  flex-direction: column;
  background: var(--color-sidebar-bg);
  border-right: 1px solid var(--color-sidebar-border);
  padding: var(--space-16) 0;
}
.admin-layout__brand {
  display: flex;
  align-items: center;
  gap: var(--space-8);
  padding: 0 var(--space-16) var(--space-24);
}
.admin-layout__brand-mark {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-8);
  background: var(--color-primary);
  color: var(--color-on-primary);
  font-size: 16px;
  font-weight: var(--font-weight-700);
}
.admin-layout__brand-name {
  font-size: 16px;
  font-weight: var(--font-weight-700);
  color: var(--color-sidebar-brand);
}
.admin-layout__menu {
  flex: 1;
  overflow-y: auto;
}
.admin-layout__menu :deep(.n-menu) {
  background: transparent;
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
  border-bottom: 1px solid var(--color-border-subtle);
  box-shadow: var(--shadow-1);
  position: sticky;
  top: 0;
  z-index: 10;
}
.admin-layout__title {
  font-size: 16px;
  font-weight: var(--font-weight-600);
}
.admin-layout__user {
  display: flex;
  align-items: center;
  gap: var(--space-12);
  flex-shrink: 0;
  white-space: nowrap;
  font-size: 13px;
}
.admin-layout__content {
  flex: 1;
  padding: var(--space-24);
  overflow: auto;
}
</style>
