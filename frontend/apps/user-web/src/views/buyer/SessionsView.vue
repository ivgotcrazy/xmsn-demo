<script setup lang="ts">
/**
 * 会话历史列表（原型明确化 §2：「我的会话」，对应 conversations 接口）。
 */
import { onMounted, ref } from "vue"
import { useRouter } from "vue-router"
import { NButton, NTag, useMessage } from "naive-ui"

import { conversations, type ConversationListItem } from "@xmsn/api"

const router = useRouter()
const message = useMessage()
const list = ref<ConversationListItem[]>([])
const loading = ref(true)

const STATUS: Record<string, { label: string; type: "success" | "default" | "warning" }> = {
  confirmed: { label: "已确认", type: "success" },
  active: { label: "进行中", type: "default" },
  closed: { label: "已关闭", type: "warning" },
}

onMounted(async () => {
  try {
    const res = await conversations()
    list.value = res.conversations ?? []
  } catch (e) {
    message.error((e as Error).message || "加载失败")
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="sessions-page">
    <div class="sessions-page__head">
      <h2>我的会话</h2>
      <NButton size="small" @click="router.push('/buyer/chat')">新建会话</NButton>
    </div>
    <div class="sessions-page__list">
      <div
        v-for="c in list"
        :key="c.conversation_id"
        class="sessions-page__item"
        @click="router.push('/buyer/chat')"
      >
        <div class="sessions-page__info">
          <span class="sessions-page__id">{{ c.conversation_id }}</span>
          <NTag size="small" :type="STATUS[c.status]?.type ?? 'default'" :bordered="false">
            {{ STATUS[c.status]?.label ?? c.status }}
          </NTag>
        </div>
        <div class="sessions-page__meta">
          请求 {{ c.request_count ?? 0 }} 次 · {{ c.updated_at }}
        </div>
      </div>
      <div v-if="!list.length" class="sessions-page__empty">暂无会话</div>
    </div>
  </div>
</template>

<style scoped>
.sessions-page {
  max-width: 800px;
  margin: 0 auto;
}
.sessions-page__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-16);
}
.sessions-page__head h2 {
  margin: 0;
  font-size: var(--font-size-20);
}
.sessions-page__list {
  display: flex;
  flex-direction: column;
  gap: var(--space-12);
}
.sessions-page__item {
  padding: var(--space-16);
  background: var(--color-bg-panel);
  border: var(--border-width-1) solid var(--color-border-subtle);
  border-radius: var(--radius-12);
  cursor: pointer;
}
.sessions-page__item:hover {
  border-color: var(--color-primary);
}
.sessions-page__info {
  display: flex;
  align-items: center;
  gap: var(--space-8);
}
.sessions-page__id {
  font-weight: var(--font-weight-600);
}
.sessions-page__meta {
  margin-top: var(--space-8);
  font-size: var(--font-size-12);
  color: var(--color-text-secondary);
}
.sessions-page__empty {
  padding: var(--space-32);
  text-align: center;
  color: var(--color-text-secondary);
}
</style>
