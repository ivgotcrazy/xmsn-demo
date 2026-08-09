<script setup lang="ts">
/**
 * 匹配详情面板（原型 02B / COMP-024/026）：就地展开——子分数副行 + 三组判定 + AI 评语 + 查看原文。
 */
import { computed } from "vue"
import { NButton, NSpin, NTag } from "naive-ui"

import type { MatchDetailResponse, MatchItem } from "@xmsn/types"

const props = defineProps<{
  detail: MatchDetailResponse | null
  item: MatchItem | null
  loading?: boolean
}>()

const emit = defineEmits<{ preview: [] }>()

const GROUP = [
  { key: "matched_params", title: "匹配项", type: "success" },
  { key: "partial_params", title: "需协商/未声明", type: "warning" },
  { key: "unmatched_params", title: "不匹配项", type: "error" },
] as const

const semanticPct = computed(() => Math.round((props.item?.semantic_score ?? 0) * 100))
const hitText = computed(() => {
  const matched = props.detail?.matched_params?.length ?? 0
  const total =
    matched +
    (props.detail?.partial_params?.length ?? 0) +
    (props.detail?.unmatched_params?.length ?? 0)
  return `参数命中 ${matched}/${total}`
})
</script>

<template>
  <div class="match-detail">
    <NSpin :show="loading">
      <template v-if="detail">
        <div v-if="item?.critical_fail" class="match-detail__alert match-detail__alert--warn">
          ⚠️ 关键参数匹配需进一步协商确认
        </div>
        <div class="match-detail__head">
          <h3>{{ detail.company_name }}</h3>
          <span class="match-detail__status">
            解释状态：{{ detail.explanation_status === "ready" ? "已生成" : "生成中…" }}
          </span>
        </div>
        <div class="match-detail__subrow">
          语义相似度 {{ semanticPct }}% · {{ hitText }}
        </div>

        <section v-for="g in GROUP" :key="g.key" class="match-detail__group">
          <h4>
            <NTag size="small" :type="g.type" :bordered="false">{{ g.title }}</NTag>
          </h4>
          <ul v-if="detail[g.key]?.length">
            <li v-for="(p, i) in detail[g.key]" :key="i">
              <span class="k">{{ p.label }}</span>
              <span class="v">{{ p.value }}</span>
              <NTag size="tiny" :type="g.type" :bordered="false">{{ p.verdict ?? "—" }}</NTag>
            </li>
          </ul>
          <div v-else class="match-detail__empty">无</div>
        </section>

        <section v-if="detail.ai_comment" class="match-detail__comment">
          <h4>AI 评语</h4>
          <p>{{ detail.ai_comment }}</p>
        </section>

        <NButton block dashed size="small" @click="emit('preview')">
          查看原文（定位高亮）
        </NButton>
      </template>
      <template v-else>
        <div class="match-detail__empty">理由生成中…</div>
      </template>
    </NSpin>
  </div>
</template>

<style scoped>
.match-detail {
  padding: var(--space-16);
  background: var(--color-bg-panel);
  border: var(--border-width-1) solid var(--color-border-subtle);
  border-top: none;
  border-radius: 0 0 var(--radius-12) var(--radius-12);
  margin-top: calc(-1 * var(--border-width-1));
}
.match-detail__alert {
  padding: var(--space-8) var(--space-12);
  border-radius: var(--radius-8);
  font-size: var(--font-size-13);
  margin-bottom: var(--space-16);
}
.match-detail__alert--warn {
  background: var(--color-error-bg);
  color: var(--color-error-text);
}
.match-detail__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: var(--space-8);
}
.match-detail__head h3 {
  margin: 0;
  font-size: var(--font-size-18);
}
.match-detail__status {
  font-size: var(--font-size-12);
  color: var(--color-text-secondary);
}
.match-detail__subrow {
  padding: var(--space-8) var(--space-12);
  background: var(--color-bg);
  border-radius: var(--radius-8);
  font-size: var(--font-size-13);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-16);
}
.match-detail__group {
  margin-bottom: var(--space-16);
}
.match-detail__group h4,
.match-detail__comment h4 {
  margin: 0 0 var(--space-8);
  font-size: var(--font-size-14);
  font-weight: var(--font-weight-600);
}
.match-detail__group ul {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: var(--space-8);
}
.match-detail__group li {
  display: flex;
  align-items: center;
  gap: var(--space-8);
  font-size: var(--font-size-13);
}
.match-detail__group .k {
  width: 90px;
  flex: none;
  color: var(--color-text-secondary);
}
.match-detail__group .v {
  flex: 1;
  word-break: break-all;
}
.match-detail__empty {
  color: var(--color-disabled);
  font-size: var(--font-size-13);
}
.match-detail__comment p {
  margin: 0;
  line-height: var(--line-height-loose);
  color: var(--color-text);
  background: var(--color-primary-bg);
  border-left: 3px solid var(--color-primary);
  padding: var(--space-12);
  border-radius: var(--radius-8);
}
</style>
