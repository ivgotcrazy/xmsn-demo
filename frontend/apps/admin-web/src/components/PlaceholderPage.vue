<script setup lang="ts">
/**
 * 页面占位（T1.7 骨架）：真实交互在 T1.8 各页面实现中替换。
 */
defineProps<{
  title: string
  desc?: string
}>()
</script>

<template>
  <div class="placeholder">
    <div class="placeholder__badge">M1 骨架</div>
    <h2>{{ title }}</h2>
    <p>{{ desc ?? "页面骨架已就绪，交互在 T1.8 实现。" }}</p>
  </div>
</template>

<style scoped>
.placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  gap: var(--space-8);
  color: var(--color-text-secondary);
}
.placeholder__badge {
  padding: 2px 10px;
  border-radius: var(--radius-full);
  background: var(--color-primary-bg);
  color: var(--color-primary);
  font-size: var(--font-size-12);
}
h2 {
  margin: 0;
  color: var(--color-text);
  font-size: var(--font-size-20);
}
p {
  margin: 0;
}
</style>
