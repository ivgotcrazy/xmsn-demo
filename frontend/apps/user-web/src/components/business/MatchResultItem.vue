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
  rank?: number
}>()
const emit = defineEmits<{ open: [] }>()

const SOURCE_LABEL: Record<string, string> = { llm: "LLM", rule: "规则", hybrid: "混合" }

/** 匹配分梯度：>=90 强匹配 / >=70 较匹配 / 其余 一般。 */
function scoreTier(score: number): { label: string; cls: string } {
  if (score >= 90) return { label: "强匹配", cls: "match-item__tier--strong" }
  if (score >= 70) return { label: "较匹配", cls: "match-item__tier--mid" }
  return { label: "一般", cls: "match-item__tier--low" }
}
</script>

<template>
  <div class="match-item" :class="{ 'match-item--active': active }" @click="emit('open')">
    <div class="match-item__main">
      <div class="match-item__head">
        <span v-if="rank" class="match-item__rank" :class="{ 'is-top': rank <= 3 }">{{ rank }}</span>
        <span class="match-item__name">{{ item.company_name }}</span>
        <NTag size="small" :bordered="false">{{ SOURCE_LABEL[item.match_source ?? "llm"] ?? item.match_source }}</NTag>
        <NTag v-if="(item.missing_count ?? 0) > 0" size="small" type="warning" :bordered="false">
          未声明 {{ item.missing_count }}
        </NTag>
      </div>
      <div v-if="item.summary" class="match-item__summary">{{ item.summary }}</div>
      <div class="match-item__meta">
        <span class="match-item__tier" :class="scoreTier(item.match_score).cls">{{ scoreTier(item.match_score).label }}</span>
        {{ item.location ?? "—" }} · 匹配 {{ item.matched_count ?? 0 }}/{{
          (item.matched_count ?? 0) +
          (item.partial_count ?? 0) +
          (item.missing_count ?? 0) +
          (item.unmatched_count ?? 0)
        }} 项
      </div>
    </div>
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
  gap: var(--space-12);
  padding: var(--space-12);
  background: var(--color-bg-panel);
  border: var(--border-width-1) solid var(--color-border-subtle);
  border-radius: var(--radius-12);
  cursor: pointer;
  transition: border-color var(--duration-fast) var(--ease-standard);
}
.match-item:hover {
  border-color: var(--color-accent);
}
.match-item--active {
  border-color: var(--color-accent);
  box-shadow: var(--shadow-1);
}
.match-item__main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.match-item__head {
  display: flex;
  align-items: center;
  gap: var(--space-8);
  min-width: 0;
}
.match-item__name {
  font-size: var(--font-size-14);
  font-weight: var(--font-weight-600);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}
.match-item__summary {
  font-size: var(--font-size-12);
  color: var(--color-text-secondary);
  line-height: var(--line-height-normal);
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.match-item__meta {
  font-size: var(--font-size-12);
  color: var(--color-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.match-item__rank {
  flex: none;
  min-width: 20px;
  height: 20px;
  padding: 0 5px;
  border-radius: var(--radius-full);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-12);
  font-weight: var(--font-weight-700);
  color: var(--color-text-secondary);
  background: var(--color-bg);
}
.match-item__rank.is-top {
  color: #fff;
  background: var(--color-accent);
}
.match-item__tier {
  font-weight: var(--font-weight-600);
}
.match-item__tier--strong { color: var(--color-success-text); }
.match-item__tier--mid { color: var(--color-warning-text); }
.match-item__tier--low { color: var(--color-text-secondary); }
.match-item__score {
  flex: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-4);
}
.match-item__arrow {
  font-size: var(--font-size-12);
  color: var(--color-accent);
}
</style>
