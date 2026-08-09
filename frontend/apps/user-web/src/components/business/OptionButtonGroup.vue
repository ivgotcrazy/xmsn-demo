<script setup lang="ts">
/**
 * 选项按钮组（原型 02A / COMP-018）：动态候选回答，点击选中并回填输入框（可追加）。
 */
import { ref } from "vue"
import { NButton } from "naive-ui"

defineProps<{ options: string[] }>()
const emit = defineEmits<{ select: [value: string] }>()
const selected = ref("")
function onClick(o: string): void {
  selected.value = o
  emit("select", o)
}
</script>

<template>
  <div v-if="options.length" class="opt-group">
    <NButton
      v-for="o in options"
      :key="o"
      size="small"
      round
      :type="selected === o ? 'primary' : 'default'"
      @click="onClick(o)"
    >
      {{ o }}
    </NButton>
  </div>
</template>

<style scoped>
.opt-group {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-8);
  margin: 0 0 var(--space-8) 48px;
}
</style>
