<script setup lang="ts">
/**
 * 02A 需求对话 Agent（原型）：顶部标题栏 + 新建/我的会话，底部输入栏含"完成需求描述"，
 * 右侧"当前需求"悬浮摘要面板（可折叠），对话萃取 + 选项回填 + 三态档案 + 确认提交。
 */
import { onMounted, ref } from "vue"
import { useRouter } from "vue-router"
import { NButton, NInput, useMessage } from "naive-ui"

import {
  conversationConfirm,
  conversationFinish,
  conversationMessage,
  conversationStart,
} from "@xmsn/api"

import ChatBubble from "@/components/business/ChatBubble.vue"
import DemandProfileCard from "@/components/business/DemandProfileCard.vue"
import OptionButtonGroup from "@/components/business/OptionButtonGroup.vue"

const router = useRouter()
const message = useMessage()

const messages = ref<{ role: "assistant" | "user"; content: string; error?: boolean }[]>([])
const options = ref<string[]>([])
const input = ref("")
const slots = ref<Record<string, unknown>>({})
const confidence = ref<Record<string, number>>({})
const excluded = ref<string[]>([])
const unsetFields = ref<string[]>([])
const version = ref<number | null>(null)
const conversationId = ref("")
const sending = ref(false)
const loading = ref(true)
const asideCollapsed = ref(false)
// 原型明确化 §2：核心参数齐备后是否已提示"确认完成"
const confirmPrompted = ref(false)

async function init(): Promise<void> {
  loading.value = true
  try {
    const res = await conversationStart({ user_id: "u-buyer-001" })
    conversationId.value = res.conversation_id
    messages.value.push({ role: "assistant", content: res.first_message.content })
    options.value = res.first_message.options ?? []
  } catch {
    messages.value.push({ role: "assistant", content: "初始化失败，请刷新重试", error: true })
  } finally {
    loading.value = false
  }
}

async function newSession(): Promise<void> {
  messages.value = []
  options.value = []
  input.value = ""
  slots.value = {}
  confidence.value = {}
  excluded.value = []
  unsetFields.value = []
  version.value = null
  conversationId.value = ""
  await init()
}

async function send(text?: string): Promise<void> {
  const content = (text ?? input.value).trim()
  if (!content || sending.value) return
  messages.value.push({ role: "user", content })
  input.value = ""
  sending.value = true
  try {
    const res = await conversationMessage({
      conversation_id: conversationId.value,
      message: content,
    })
    messages.value.push({ role: "assistant", content: res.assistant_message.content })
    options.value = res.assistant_message.options ?? []
    slots.value = { ...slots.value, ...res.updated_slots }
    confidence.value = {
      ...confidence.value,
      ...(res.slot_confidence as Record<string, number> | undefined),
    }
    // 原型明确化 §2：核心参数（产品类型等）齐备后 Agent 主动提示确认完成
    if (slots.value.product_type && !confirmPrompted.value) {
      confirmPrompted.value = true
      messages.value.push({
        role: "assistant",
        content: "核心需求已明确，确认完成？还是继续补充？",
      })
      options.value = ["确认完成", "继续补充"]
    }
  } catch {
    messages.value.push({ role: "assistant", content: "发送失败，请重试", error: true })
  } finally {
    sending.value = false
  }
}

function pick(opt: string): void {
  // 原型明确化 §2："确认完成"触发完成；"继续补充"继续对话
  if (opt === "确认完成") {
    void finish()
    return
  }
  if (opt === "继续补充") {
    options.value = []
    return
  }
  input.value = opt
}

async function finish(): Promise<void> {
  if (!conversationId.value || version.value !== null) return
  // 原型明确化 §2：产品类型未指定时不可完成
  if (!slots.value.product_type) {
    message.warning("请先明确要寻找的产品类型")
    return
  }
  try {
    const res = await conversationFinish({ conversation_id: conversationId.value, message: "" })
    version.value = res.version
    slots.value = { ...slots.value, ...res.profile }
    unsetFields.value = res.unset_fields ?? []
    message.success(`需求档案已生成（版本 v${res.version}）`)
  } catch {
    message.error("生成需求档案失败")
  }
}

async function confirm(): Promise<void> {
  if (!conversationId.value || version.value === null) return
  try {
    const res = await conversationConfirm({
      conversation_id: conversationId.value,
      final_demand: slots.value,
    })
    await router.push(res.redirect_to)
  } catch {
    message.error("提交匹配失败")
  }
}

onMounted(() => {
  void init()
})
</script>

<template>
  <div class="chat-page">
    <header class="chat-page__header">
      <h2>需脉AI选型助手</h2>
      <div class="chat-page__header-actions">
        <NButton size="small" @click="newSession()">新建会话</NButton>
        <NButton size="small" @click="router.push('/buyer/sessions')">我的会话</NButton>
      </div>
    </header>
    <div class="chat-page__body">
      <div class="chat-page__main">
        <div class="chat-page__panel">
          <div v-if="loading" class="chat-page__empty">对话初始化中…</div>
          <div v-else class="chat-page__messages">
            <template v-for="(m, i) in messages">
              <ChatBubble :role="m.role" :content="m.content" :error="m.error" />
              <OptionButtonGroup
                v-if="m.role === 'assistant' && !m.error && i === messages.length - 1"
                :options="options"
                @select="pick"
              />
            </template>
          </div>
          <div class="chat-page__composer">
            <NInput
              v-model:value="input"
              placeholder="描述您的代工需求，如：需要 5000 台机顶盒，Linux 系统，支持网口和 USB…"
              :disabled="sending"
              @keyup.enter="send()"
            />
            <NButton type="primary" :loading="sending" :disabled="!input.trim()" @click="send()">
              发送
            </NButton>
            <NButton
              :disabled="version !== null || !conversationId || !slots.product_type"
              :title="!slots.product_type ? '请先明确要寻找的产品类型' : undefined"
              @click="finish()"
            >
              {{ version !== null ? `已生成 v${version}` : "完成需求描述" }}
            </NButton>
          </div>
        </div>
      </div>
      <aside class="chat-page__aside" :class="{ 'is-collapsed': asideCollapsed }">
        <div class="chat-page__aside-head">
          <h3>当前需求</h3>
          <NButton text size="small" @click="asideCollapsed = !asideCollapsed">
            {{ asideCollapsed ? "展开" : "收起" }}
          </NButton>
        </div>
        <div v-show="!asideCollapsed" class="chat-page__aside-body">
          <DemandProfileCard
            :slots="slots"
            :excluded="excluded"
            :confidence="confidence"
            :unset-fields="unsetFields"
          />
          <NButton
            v-if="version !== null"
            type="primary"
            block
            @click="confirm()"
          >
            确认并提交匹配 →
          </NButton>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 56px - 48px);
  gap: var(--space-12);
}
.chat-page__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex: none;
  padding: 0 var(--space-4);
}
.chat-page__header h2 {
  margin: 0;
  font-size: var(--font-size-18);
}
.chat-page__header-actions {
  display: flex;
  gap: var(--space-8);
}
.chat-page__body {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: var(--space-24);
}
.chat-page__main {
  flex: 1;
  min-width: 0;
  display: flex;
}
.chat-page__panel {
  display: flex;
  flex-direction: column;
  width: 100%;
  background: var(--color-bg-panel);
  border: var(--border-width-1) solid var(--color-border-subtle);
  border-radius: var(--radius-12);
  overflow: hidden;
}
.chat-page__messages {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-24);
}
.chat-page__empty {
  padding: var(--space-24);
  color: var(--color-text-secondary);
}
.chat-page__composer {
  display: flex;
  gap: var(--space-12);
  padding: var(--space-16);
  border-top: var(--border-width-1) solid var(--color-border-subtle);
}
.chat-page__composer .n-input {
  flex: 1;
}
.chat-page__aside {
  width: 320px;
  flex: none;
  background: var(--color-bg-panel);
  border: var(--border-width-1) solid var(--color-border-subtle);
  border-radius: var(--radius-12);
  padding: var(--space-16);
  display: flex;
  flex-direction: column;
  gap: var(--space-16);
  overflow-y: auto;
}
.chat-page__aside.is-collapsed {
  width: auto;
  min-width: 120px;
}
.chat-page__aside-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.chat-page__aside-head h3 {
  margin: 0;
  font-size: var(--font-size-16);
}
.chat-page__aside-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-16);
}
</style>
