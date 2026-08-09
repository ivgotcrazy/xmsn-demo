<script setup lang="ts">
/**
 * 需求档案卡片（COMP-019）：按 Schema 品类分三态展示（已指定 / 未指定·可忽略 / 已排除）。
 */
import { computed } from "vue"
import { NTag } from "naive-ui"

import { REQUEST_SCHEMA_FIELDS } from "@xmsn/types"

const props = defineProps<{
  slots: Record<string, unknown>
  excluded?: string[]
  confidence?: Record<string, number>
  unsetFields?: string[]
}>()

const filled = computed(() =>
  REQUEST_SCHEMA_FIELDS.filter((f) => {
    const v = props.slots?.[f.key]
    const empty = v === undefined || v === null || v === "" || (Array.isArray(v) && v.length === 0)
    return !empty && !props.excluded?.includes(f.key)
  }),
)
const excluded = computed(() => REQUEST_SCHEMA_FIELDS.filter((f) => props.excluded?.includes(f.key)))
const ignored = computed(() =>
  REQUEST_SCHEMA_FIELDS.filter(
    (f) => !filled.value.includes(f) && !excluded.value.includes(f),
  ),
)

function displayValue(v: unknown): string {
  return Array.isArray(v) ? v.join("、") : String(v ?? "")
}
function confidenceOf(key: string): number | undefined {
  return props.confidence?.[key]
}
</script>

<template>
  <div class="demand-profile">
    <section v-if="filled.length">
      <h4>已指定</h4>
      <ul>
        <li v-for="f in filled" :key="f.key">
          <NTag size="small" type="success">{{ f.label }}</NTag>
          <span class="value">{{ displayValue(slots[f.key]) }}</span>
          <span v-if="confidenceOf(f.key) !== undefined" class="conf">
            {{ Math.round((confidenceOf(f.key) ?? 0) * 100) }}%
          </span>
        </li>
      </ul>
    </section>
    <section v-if="ignored.length">
      <h4>未指定 · 可忽略</h4>
      <ul>
        <li v-for="f in ignored" :key="f.key">
          <NTag size="small">{{ f.label }}</NTag>
          <span class="value muted">未填写</span>
        </li>
      </ul>
    </section>
    <section v-if="excluded.length">
      <h4>已排除</h4>
      <ul>
        <li v-for="f in excluded" :key="f.key">
          <NTag size="small" type="error">{{ f.label }}</NTag>
          <span class="value">{{ displayValue(slots[f.key]) }}</span>
        </li>
      </ul>
    </section>
    <div v-if="unsetFields?.length" class="hint">
      可忽略字段：{{ unsetFields.join("、") }}
    </div>
  </div>
</template>

<style scoped>
.demand-profile {
  display: flex;
  flex-direction: column;
  gap: var(--space-16);
}
.demand-profile h4 {
  margin: 0 0 var(--space-8);
  font-size: var(--font-size-14);
  font-weight: var(--font-weight-600);
  color: var(--color-text-secondary);
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
  align-items: center;
  gap: var(--space-8);
}
.value {
  flex: 1;
  color: var(--color-text);
}
.value.muted {
  color: var(--color-disabled);
}
.conf {
  font-size: var(--font-size-12);
  color: var(--color-primary);
}
.hint {
  font-size: var(--font-size-12);
  color: var(--color-disabled);
}
</style>
