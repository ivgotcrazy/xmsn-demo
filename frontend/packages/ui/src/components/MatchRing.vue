<script setup lang="ts">
/**
 * 匹配度环形进度（COMP-023）：自研 SVG 环形，无依赖（Naive 无环形进度组件）。
 * 颜色语义（走 CSS 变量 + class，保证 SVG stroke 生效）：
 *   >=80 success，>=60 warning，否则 error。
 */
import { computed } from "vue"

const props = defineProps<{
  score: number
  size?: number
  strokeWidth?: number
}>()

const R = computed(() => (props.size ?? 64) / 2 - (props.strokeWidth ?? 6) - 2)
const C = computed(() => 2 * Math.PI * R.value)
const offset = computed(() => C.value * (1 - Math.min(100, Math.max(0, props.score)) / 100))
const levelClass = computed(() =>
  props.score >= 80 ? "ring--success" : props.score >= 60 ? "ring--warning" : "ring--error",
)
</script>

<template>
  <div class="match-ring" :style="{ width: (size ?? 64) + 'px', height: (size ?? 64) + 'px' }">
    <svg :width="size ?? 64" :height="size ?? 64" viewBox="0 0 64 64">
      <circle class="match-ring__track" cx="32" cy="32" :r="R" fill="none" :stroke-width="strokeWidth ?? 6" />
      <circle
        class="match-ring__arc"
        :class="levelClass"
        cx="32"
        cy="32"
        :r="R"
        fill="none"
        :stroke-width="strokeWidth ?? 6"
        stroke-linecap="round"
        :stroke-dasharray="C"
        :stroke-dashoffset="offset"
        transform="rotate(-90 32 32)"
      />
    </svg>
    <div class="match-ring__value" :class="levelClass">
      <span>{{ Math.round(score) }}</span>
    </div>
  </div>
</template>

<style scoped>
.match-ring {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.match-ring__track {
  stroke: var(--color-border-subtle);
}
.ring--success {
  stroke: var(--color-success);
  color: var(--color-success);
}
.ring--warning {
  stroke: var(--color-warning);
  color: var(--color-warning);
}
.ring--error {
  stroke: var(--color-error);
  color: var(--color-error);
}
.match-ring__value {
  position: absolute;
  font-size: var(--font-size-18);
  font-weight: var(--font-weight-700);
}
</style>
