<script setup lang="ts">
/**
 * 匹配结果列表项（原型 02B / COMP-022）：三列——左(工厂信息) / 中(一句话摘要) / 右(匹配度+箭头)。
 */
import { NTag } from "naive-ui"

import { MatchRing } from "@xmsn/ui"
import type { MatchItem } from "@xmsn/api"

defineProps<{
  item: MatchItem
  active?: boolean
}>()
const emit = defineEmits<{ open: [] }>()

const SOURCE_LABEL: Record<string, string> = { llm: "LLM", rule: "规则", hybrid: "混合" }
</script>

<template>
  <div class="match-item" :class="{ 'match-item--active': active }" @click="emit('open')">
    <div class="match-item__info">
      <div class="match-item__head">
        <span class="match-item__name">{{ item.company_name }}</span>
        <NTag size="small" :bordered="false">{{ SOURCE_LABEL[item.match_source ?? "llm"] ?? item.match_source }}</NTag>
        <NTag v-if="item.critical_fail" size="small" type="error" :bordered="false">关键参数不符</NTag>
      </div>
      <div class="match-item__meta">
        {{ item.location ?? "—" }} · 参数 {{ (item.matched_count ?? 0) + (item.unmatched_count ?? 0) }} 项
      </div>
    </div>
    <div v-if="item.summary" class="match-item__summary">{{ item.summary }}</div>
    <div class="match-item__score">
      <MatchRing :score="item.match_score" :size="48" :stroke-width="4" />
      <span class="match-item__arrow">{{ active ? "收起 ▴" : "详情 ▾" }}</span>
    </div>
  </div>
</template>

<style scoped>
.match-item {
  display: flex;
  align-items: center;
  gap: var(--space-16);
  padding: var(--space-16);
  background: var(--color-bg-panel);
  border: var(--border-width-1) solid var(--color-border-subtle);
  border-radius: var(--radius-12);
  cursor: pointer;
  transition: border-color var(--duration-fast) var(--ease-standard);
}
.match-item:hover {
  border-color: var(--color-primary);
}
.match-item--active {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-1);
}
.match-item__info {
  flex: 2;
  min-width: 0;
}
.match-item__head {
  display: flex;
  align-items: center;
  gap: var(--space-8);
}
.match-item__name {
  font-size: var(--font-size-16);
  font-weight: var(--font-weight-600);
}
.match-item__meta {
  margin-top: var(--space-4);
  font-size: var(--font-size-12);
  color: var(--color-text-secondary);
}
.match-item__summary {
  flex: 3;
  min-width: 0;
  font-size: var(--font-size-13);
  color: var(--color-text-secondary);
  line-height: var(--line-height-normal);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.match-item__score {
  flex: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-4);
}
.match-item__arrow {
  font-size: var(--font-size-12);
  color: var(--color-primary);
}
</style>
