<script setup lang="ts">
/**
 * admin-web 根组件：Naive UI 主题映射 + 中文 locale + 管理端布局切换。
 * 登录页（public）无侧边栏；其余页面经 AdminLayout 包裹。
 */
import { computed } from "vue"
import { useRoute } from "vue-router"
import { NConfigProvider, NDialogProvider, NMessageProvider, dateZhCN, zhCN } from "naive-ui"

import { themeOverrides } from "@xmsn/tokens"

import AdminLayout from "@/components/layout/AdminLayout.vue"

const route = useRoute()
const useAdminLayout = computed(() => !route.meta.public)
</script>

<template>
  <NConfigProvider :theme-overrides="themeOverrides" :locale="zhCN" :date-locale="dateZhCN">
    <NDialogProvider>
      <NMessageProvider>
        <AdminLayout v-if="useAdminLayout">
          <RouterView />
        </AdminLayout>
        <RouterView v-else />
      </NMessageProvider>
    </NDialogProvider>
  </NConfigProvider>
</template>
