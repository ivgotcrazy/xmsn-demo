<script setup lang="ts">
/**
 * 历史匹配（原型明确化 §3：「查看历史匹配」，需求匹配快照版本列表）。
 */
import { onMounted, ref } from "vue"
import { useRouter } from "vue-router"
import { useMessage } from "naive-ui"

import { conversationConversationIdRequests, type RequestSnapshot } from "@xmsn/api"

const router = useRouter()
const message = useMessage()
const list = ref<RequestSnapshot[]>([])
const loading = ref(true)

function demandText(d: Record<string, unknown>): string {
  return Object.entries(d ?? {})
    .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join("/") : String(v)}`)
    .join(" · ")
}

onMounted(async () => {
  try {
    const res = await conversationConversationIdRequests("conv-001")
    list.value = res.requests ?? []
  } catch (e) {
    message.error((e as Error).message || "加载失败")
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="history-page">
    <div class="history-page__head">
      <h2>历史匹配</h2>
    </div>
    <div class="history-page__list">
      <div
        v-for="r in list"
        :key="r.request_id"
        class="history-page__item"
        @click="router.push(`/buyer/matches/${r.request_id}`)"
      >
        <div class="history-page__info">
          <span class="history-page__version">v{{ r.version }}</span>
          <span class="history-page__text">
            {{ demandText(r.structured_demand as Record<string, unknown>) }}
          </span>
        </div>
        <div class="history-page__meta">
          {{ r.match_count ?? 0 }} 条匹配 · {{ r.created_at }}
        </div>
      </div>
      <div v-if="!list.length" class="history-page__empty">暂无历史匹配</div>
    </div>
  </div>
</template>

<style scoped>
.history-page {
  max-width: 800px;
  margin: 0 auto;
}
.history-page__head {
  margin-bottom: var(--space-16);
}
.history-page__head h2 {
  margin: 0;
  font-size: var(--font-size-20);
}
.history-page__list {
  display: flex;
  flex-direction: column;
  gap: var(--space-12);
}
.history-page__item {
  padding: var(--space-16);
  background: var(--color-bg-panel);
  border: var(--border-width-1) solid var(--color-border-subtle);
  border-radius: var(--radius-12);
  cursor: pointer;
}
.history-page__item:hover {
  border-color: var(--color-primary);
}
.history-page__info {
  display: flex;
  align-items: center;
  gap: var(--space-12);
}
.history-page__version {
  flex: none;
  font-weight: var(--font-weight-700);
  color: var(--color-primary);
}
.history-page__text {
  font-size: var(--font-size-13);
}
.history-page__meta {
  margin-top: var(--space-8);
  font-size: var(--font-size-12);
  color: var(--color-text-secondary);
}
.history-page__empty {
  padding: var(--space-32);
  text-align: center;
  color: var(--color-text-secondary);
}
</style>
