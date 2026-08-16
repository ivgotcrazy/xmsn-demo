<script setup lang="ts">
/**
 * 需求档案卡片（COMP-019，D5）：当前需求 = 需求点实例（label 由品类 Schema 提供）
 * + strictness 两档徽标（D7：必须/尽力）。
 */
import { NTag } from "naive-ui"

import type { DemandPoint } from "@xmsn/api"

defineProps<{
  points: DemandPoint[]
}>()

const STRICTNESS_META: Record<string, { label: string; type: "warning" | "default" }> = {
  strict: { label: "必须", type: "warning" },
  "best-effort": { label: "尽力", type: "default" },
}

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
          <span class="demand-profile__strict">
            <NTag v-if="p.strictness" size="tiny" :type="STRICTNESS_META[p.strictness]?.type ?? 'default'" :bordered="false">
              {{ STRICTNESS_META[p.strictness]?.label ?? p.strictness }}
            </NTag>
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
.demand-profile__strict {
  display: inline-flex;
}
.demand-profile__value {
  color: var(--color-text);
  line-height: var(--line-height-normal);
  padding-left: var(--space-4);
}
.demand-profile__conf {
  font-size: var(--font-size-12);
  color: var(--color-primary);
}
</style>
