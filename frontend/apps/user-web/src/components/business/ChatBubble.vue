<script setup lang="ts">
/**
 * 对话气泡（COMP-017）：左 Agent / 右用户 / 加载 / 错误态。
 */
defineProps<{
  role: "assistant" | "user"
  content: string
  loading?: boolean
  error?: boolean
}>()
</script>

<template>
  <div class="chat-bubble" :class="`chat-bubble--${role}`">
    <div class="chat-bubble__avatar">{{ role === "assistant" ? "需" : "我" }}</div>
    <div class="chat-bubble__body" :class="{ 'chat-bubble__body--error': error }">
      <template v-if="error">发送失败，请重试</template>
      <template v-else-if="loading"><span class="chat-bubble__typing">…</span></template>
      <template v-else>{{ content }}</template>
    </div>
  </div>
</template>

<style scoped>
.chat-bubble {
  display: flex;
  gap: var(--space-12);
  margin: var(--space-16) 0;
  max-width: 720px;
}
.chat-bubble--user {
  flex-direction: row-reverse;
  margin-left: auto;
}
.chat-bubble__avatar {
  flex: none;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: var(--font-weight-600);
  color: var(--color-on-primary);
  background: var(--color-primary);
}
.chat-bubble--user .chat-bubble__avatar {
  background: var(--color-text-secondary);
}
.chat-bubble__body {
  padding: var(--space-12) var(--space-16);
  border-radius: var(--radius-12);
  background: var(--color-chat-agent-bg);
  line-height: var(--line-height-loose);
  word-break: break-word;
  white-space: pre-wrap;
}
.chat-bubble--user .chat-bubble__body {
  background: var(--color-chat-user-bg);
  color: var(--color-text);
}
.chat-bubble__body--error {
  background: var(--color-error-bg);
  color: var(--color-error-text);
}
.chat-bubble__typing {
  animation: blink 1s infinite;
}
@keyframes blink {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 1; }
}
</style>
