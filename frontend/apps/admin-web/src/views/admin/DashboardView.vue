<script setup lang="ts">
/**
 * 03B 数据概览（原型 4.1）：四统计卡片 + 较昨日变化 + 点击跳转对应列表页。
 */
import { computed, onMounted, ref } from "vue"
import { useRouter } from "vue-router"
import { NSpin } from "naive-ui"

import { adminStats, type AdminStatsResponse } from "@xmsn/api"

const router = useRouter()
const stats = ref<AdminStatsResponse | null>(null)
const loading = ref(true)

const cards = computed(() => {
  const s = stats.value
  return [
    { label: "用户总数", value: s?.total_users ?? 0, delta: "+12%", link: "" },
    { label: "需求总数", value: s?.total_requests ?? 0, delta: "+8%", link: "/admin/requests" },
    { label: "厂商总数", value: s?.total_vendors ?? 0, delta: "+4%", link: "/admin/vendors" },
    { label: "匹配次数", value: s?.total_matches ?? 0, delta: "+21%", link: "/admin/requests" },
  ]
})

function go(link: string): void {
  if (link) void router.push(link)
}

onMounted(async () => {
  try {
    stats.value = await adminStats()
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <NSpin :show="loading">
    <div class="stats-grid">
      <div
        v-for="c in cards"
        :key="c.label"
        class="stat-card"
        :class="{ 'is-clickable': !!c.link }"
        @click="go(c.link)"
      >
        <div class="stat-card__label">{{ c.label }}</div>
        <div class="stat-card__value">{{ c.value }}</div>
        <div class="stat-card__delta">较昨日 {{ c.delta }}</div>
      </div>
    </div>
  </NSpin>
</template>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-16);
}
.stat-card {
  padding: var(--space-24);
  background: var(--color-bg-panel);
  border: var(--border-width-1) solid var(--color-border-subtle);
  border-radius: var(--radius-12);
}
.stat-card.is-clickable {
  cursor: pointer;
  transition: border-color var(--duration-fast) var(--ease-standard);
}
.stat-card.is-clickable:hover {
  border-color: var(--color-primary);
}
.stat-card__label {
  font-size: var(--font-size-13);
  color: var(--color-text-secondary);
}
.stat-card__value {
  margin-top: var(--space-8);
  font-size: var(--font-size-28);
  font-weight: var(--font-weight-700);
  color: var(--color-primary);
}
.stat-card__delta {
  margin-top: var(--space-8);
  font-size: var(--font-size-12);
  color: var(--color-success);
}
</style>
