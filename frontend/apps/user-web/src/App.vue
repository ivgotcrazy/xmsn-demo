<script setup lang="ts">
/**
 * user-web 根组件：Naive UI 主题映射 + 中文 locale + 全局 Provider。
 * 页面布局由路由嵌套承载（VendorLayout / MainLayout / 公共卡片页）。
 */
import { NConfigProvider, NDialogProvider, NMessageProvider, dateZhCN, zhCN } from "naive-ui"

import { themeOverrides } from "@xmsn/tokens"
</script>

<template>
  <NConfigProvider :theme-overrides="themeOverrides" :locale="zhCN" :date-locale="dateZhCN">
    <NDialogProvider>
      <NMessageProvider>
        <RouterView />
      </NMessageProvider>
    </NDialogProvider>
  </NConfigProvider>
</template>
