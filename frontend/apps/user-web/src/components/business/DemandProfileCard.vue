<script setup lang="ts">
/**
 * 需求档案卡片（COMP-019）：基于会话历史萃取的需求点列表（固定/扩展统一展示，不感知 schema）。
 */
import { NTag } from "naive-ui"

import type { DemandPoint } from "@xmsn/api"

defineProps<{
  points: DemandPoint[]
}>()

function displayValue(v: string | string[]): string {
  return Array.isArray(v) ? v.join("、") : v
}
</script>

<template>
  <div class="demand-profile">
    <div v-if="!points.length" class="demand-profile__empty">
      正在对话中萃取您的需求…
    </div>
    <ul v-else>
      <li v-for="p in points" :key="p.key">
        <div class="demand-profile__row">
          <NTag size="small">{{ p.label }}</NTag>
          <span v-if="p.confidence !== undefined" class="demand-profile__conf">
            {{ Math.round((p.confidence ?? 0) * 100) }}%
          </span>
        </div>
        <div class="demand-profile__value">{{ displayValue(p.value) }}</div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.demand-profile {
  display: flex;
  flex-direction: column;
  gap: var(--space-8);
}
.demand-profile__empty {
  font-size: var(--font-size-13);
  color: var(--color-text-secondary);
  padding: var(--space-8) 0;
}
.demand-profile ul {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: var(--space-8);
}
.demand-profile li {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.demand-profile__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-8);
}
.demand-profile__value {
  color: var(--color-text);
  line-height: var(--line-height-normal);
  padding-left: var(--space-2);
}
.demand-profile__conf {
  font-size: var(--font-size-12);
  color: var(--color-primary);
}
</style>
