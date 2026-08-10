<script setup lang="ts">
/**
 * 02A 需求对话 Agent（原型）：顶部标题栏 + 新建/我的会话，底部输入栏含"完成需求描述"，
 * 右侧"当前需求"悬浮摘要面板（可折叠），对话萃取 + 选项回填 + 三态档案 + 确认提交。
 */
import { h, onMounted, ref } from "vue"
import { useRouter } from "vue-router"
import { NButton, NInput, NPopconfirm, NTag, useMessage } from "naive-ui"

import {
  conversationConfirm,
  conversationConversationId,
  conversationConversationIdMessages,
  conversationConversationIdRequests,
  conversationConversationIdRequestsRequestId,
  conversationMessage,
  conversationStart,
  conversations,
  filesUpload,
  type ConversationListItem,
  type DemandPoint,
  type RequestSnapshot,
} from "@xmsn/api"

import ChatBubble from "@/components/business/ChatBubble.vue"
import DemandProfileCard from "@/components/business/DemandProfileCard.vue"
import OptionButtonGroup from "@/components/business/OptionButtonGroup.vue"

const message = useMessage()
const router = useRouter()

const messages = ref<{ role: "assistant" | "user"; content: string; error?: boolean; created_at?: string }[]>([])
const options = ref<string[]>([])
const input = ref("")
// 前端「当前需求」：基于会话历史萃取的需求点集合（不感知 schema）
const demandPoints = ref<DemandPoint[]>([])
const version = ref<number | null>(null)
const conversationId = ref("")
const sending = ref(false)
const loading = ref(true)
const asideCollapsed = ref(false)
// 原型明确化 §2：核心参数齐备后是否已提示"确认完成"
const confirmPrompted = ref(false)
// 02A 会话管理：左侧常驻会话列表 + 当前会话高亮
const sessions = ref<ConversationListItem[]>([])
const activeId = ref("")
// 02A 匹配记录：右侧按会话展示匹配记录，点击进入匹配结果页
const records = ref<RequestSnapshot[]>([])
// 匹配记录卡片独立收起（收起方向与当前需求相反）
const recordsCollapsed = ref(false)
// 聊天输入框：附件（demo：mock 上传，展示附件条）
const attachments = ref<{ name: string; fileId: string }[]>([])
const uploading = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

function chooseAttachment(): void {
  fileInput.value?.click()
}

async function onFileSelected(e: Event): Promise<void> {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  target.value = ""
  if (!file) return
  uploading.value = true
  try {
    const res = await filesUpload()
    attachments.value.push({ name: res.name ?? file.name, fileId: res.file_id })
  } catch {
    message.error("上传附件失败")
  } finally {
    uploading.value = false
  }
}

function removeAttachment(name: string): void {
  attachments.value = attachments.value.filter((a) => a.name !== name)
}

/** 产品类型前置校验：需求点中是否已明确产品类型（匹配锚点）。 */
function hasProductType(): boolean {
  return demandPoints.value.some((p) => p.key === "product_type" && p.value !== "")
}

/** 时间分组条：组首（首条 / 跨天 / 距上条超 5 分钟）显示，格式 当天 HH:mm / 昨天 HH:mm / MM-DD HH:mm。 */
const GROUP_GAP_MS = 5 * 60 * 1000
function showTimeDivider(index: number): boolean {
  const cur = messages.value[index]
  if (!cur?.created_at) return false
  if (index === 0) return true
  const prev = messages.value[index - 1]
  if (!prev?.created_at) return true
  const a = new Date(cur.created_at)
  const b = new Date(prev.created_at)
  if (a.toDateString() !== b.toDateString()) return true
  return a.getTime() - b.getTime() > GROUP_GAP_MS
}
function formatDividerTime(iso?: string): string {
  if (!iso) return ""
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ""
  const hm = `${pad2(d.getHours())}:${pad2(d.getMinutes())}`
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const that = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  const diffDays = Math.round((today.getTime() - that.getTime()) / 86400000)
  if (diffDays <= 0) return hm
  if (diffDays === 1) return `昨天 ${hm}`
  return `${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ${hm}`
}
function pad2(n: number): string {
  return String(n).padStart(2, "0")
}
/** 会话卡更新时间：MM-DD HH:mm（本 demo 会话均为历史日期，不做相对时间）。 */
function formatSessionTime(iso?: string): string {
  if (!iso) return ""
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return `${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ${pad2(d.getHours())}:${pad2(d.getMinutes())}`
}

async function init(): Promise<void> {
  loading.value = true
  try {
    const res = await conversations()
    sessions.value = res.conversations ?? []
    if (sessions.value.length) {
      await openConversation(sessions.value[0].conversation_id)
    } else {
      await newSession()
    }
  } catch {
    messages.value.push({ role: "assistant", content: "初始化失败，请刷新重试", error: true })
    loading.value = false
  }
}

/** 02A 会话管理：点击左侧会话 → 恢复该会话现场（气泡/槽位/档案版本）。 */
async function openConversation(id: string): Promise<void> {
  activeId.value = id
  loading.value = true
  try {
    const res = await conversationConversationIdMessages(id)
    conversationId.value = res.conversation_id
    messages.value = (res.messages ?? []).map((m) => ({
      role: m.role,
      content: m.content,
      error: m.error ?? false,
      created_at: m.created_at ?? undefined,
    }))
    const last = [...(res.messages ?? [])].reverse().find((m) => m.role === "assistant")
    options.value = last?.options ?? []
    demandPoints.value = res.demand_points ?? []
    version.value = res.version ?? null
    confirmPrompted.value = res.confirm_prompted ?? false
    await loadRecords()
  } catch {
    messages.value = []
    records.value = []
    message.error("加载会话失败")
  } finally {
    loading.value = false
  }
}

async function newSession(): Promise<void> {
  loading.value = true
  try {
    const res = await conversationStart({ user_id: "u-buyer-001" })
    conversationId.value = res.conversation_id
    messages.value = [{ role: "assistant", content: res.first_message.content, created_at: new Date().toISOString() }]
    options.value = res.first_message.options ?? []
    demandPoints.value = res.demand_points ?? []
    version.value = null
    confirmPrompted.value = false
    records.value = []
    activeId.value = res.conversation_id
    sessions.value.unshift({
      conversation_id: res.conversation_id,
      title: res.title ?? "新会话",
      status: "active",
      updated_at: new Date().toISOString(),
      last_request_id: null,
      request_count: 0,
    })
  } catch {
    message.error("新建会话失败")
  } finally {
    loading.value = false
  }
}

/** Shift+Enter 发送（防误发）；普通 Enter 换行。 */
function onEnter(e: KeyboardEvent): void {
  if (e.shiftKey) {
    e.preventDefault()
    void send()
  }
}

async function send(text?: string): Promise<void> {
  const content = (text ?? input.value).trim()
  if (!content || sending.value) return
  messages.value.push({ role: "user", content, created_at: new Date().toISOString() })
  input.value = ""
  attachments.value = []
  sending.value = true
  try {
    const res = await conversationMessage({
      conversation_id: conversationId.value,
      message: content,
    })
    messages.value.push({ role: "assistant", content: res.assistant_message.content, created_at: new Date().toISOString() })
    options.value = res.assistant_message.options ?? []
    // 前端「当前需求」：全量替换为萃取出的需求点集合
    demandPoints.value = res.demand_points ?? []
    // 一会话一产品：萃取到产品类型后，会话卡标题联动更新（新会话「新会话」→ 产品名）
    if (res.title) {
      const cur = sessions.value.find((s) => s.conversation_id === conversationId.value)
      if (cur) cur.title = res.title
    }
    // 原型明确化 §2：核心参数（产品类型等）齐备后 Agent 主动提示确认完成
    if (hasProductType() && !confirmPrompted.value) {
      confirmPrompted.value = true
      messages.value.push({
        role: "assistant",
        content: "核心需求已明确，确认完成？还是继续补充？",
        created_at: new Date().toISOString(),
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
  // "确认完成"直接提交匹配（右侧按钮随时可提交）；"继续补充"继续对话
  if (opt === "确认完成") {
    void confirm()
    return
  }
  if (opt === "继续补充") {
    options.value = []
    return
  }
  input.value = opt
}

async function confirm(): Promise<void> {
  if (!conversationId.value) return
  // 产品类型未明确时提示（匹配锚点）
  if (!hasProductType()) {
    message.warning("请先明确要寻找的产品类型")
    return
  }
  try {
    const res = await conversationConfirm({
      conversation_id: conversationId.value,
      demand_points: demandPoints.value,
    })
    message.success("已提交匹配")
    // 02A 匹配记录：不跳页，刷新匹配记录并首次自动弹出结果
    await loadRecords()
    // 提交后进入该次匹配的结果页（返回回会话页）
    void router.push(`/buyer/matches/${res.request_id}`)
  } catch {
    message.error("提交匹配失败")
  }
}

/** 02A 匹配记录：拉取当前会话的匹配记录（需求匹配快照列表）。 */
async function loadRecords(): Promise<void> {
  if (!conversationId.value) {
    records.value = []
    return
  }
  try {
    const res = await conversationConversationIdRequests(conversationId.value)
    records.value = res.requests ?? []
  } catch {
    records.value = []
  }
}

/** 02A 匹配记录：点击卡片打开匹配结果弹窗。 */
function openRecord(requestId: string): void {
  void router.push(`/buyer/matches/${requestId}`)
}

/** 匹配记录卡片标题：优先显示匹配产品类型。 */
function recordTitle(r: RequestSnapshot): string {
  const pt = (r.structured_demand as Record<string, unknown> | undefined)?.product_type
  return pt ? String(pt) : "需求匹配"
}

/** 逻辑删除会话（deleted_at 标记，数据保留）：确认后从列表移除；若删除当前会话，切换到剩余首个。 */
async function deleteSession(s: ConversationListItem): Promise<void> {
  try {
    await conversationConversationId(s.conversation_id)
    sessions.value = sessions.value.filter((x) => x.conversation_id !== s.conversation_id)
    if (activeId.value === s.conversation_id) {
      if (sessions.value.length) {
        await openConversation(sessions.value[0].conversation_id)
      } else {
        await newSession()
      }
    }
    message.success("会话已删除（数据已保留）")
  } catch {
    message.error("删除会话失败")
  }
}

/** 逻辑删除匹配记录（需求档案，数据保留）。 */
async function deleteRecord(r: RequestSnapshot): Promise<void> {
  try {
    await conversationConversationIdRequestsRequestId(conversationId.value, r.request_id)
    records.value = records.value.filter((x) => x.request_id !== r.request_id)
    message.success("匹配记录已删除（数据已保留）")
  } catch {
    message.error("删除匹配记录失败")
  }
}

onMounted(() => {
  void init()
})
</script>

<template>
  <div class="chat-page">
    <!-- 左侧：常驻会话列表（02A 会话管理） -->
    <div class="chat-page__rail">
      <div class="chat-page__rail-head">
        <span>会话</span>
        <NButton text size="small" @click="newSession()">新建会话</NButton>
      </div>
      <div class="chat-page__rail-list">
        <div
          v-for="s in sessions"
          :key="s.conversation_id"
          class="chat-page__rail-item"
          :class="{ 'is-active': s.conversation_id === activeId }"
          @click="openConversation(s.conversation_id)"
        >
          <div class="chat-page__rail-top">
            <span class="chat-page__rail-id">{{ s.title || s.conversation_id }}</span>
            <NPopconfirm
              @positive-click="deleteSession(s)"
              positive-text="删除"
              negative-text="取消"
            >
              <template #trigger>
                <NButton text size="small" class="chat-page__rail-del" @click.stop>
                  删除
                </NButton>
              </template>
              删除该会话？
            </NPopconfirm>
          </div>
          <div class="chat-page__rail-meta">
            <span class="chat-page__rail-time">{{ formatSessionTime(s.updated_at) }}</span>
            <span class="chat-page__rail-count">匹配 {{ s.request_count ?? 0 }} 次</span>
          </div>
        </div>
        <div v-if="!sessions.length" class="chat-page__rail-empty">暂无会话</div>
      </div>
    </div>

    <div class="chat-page__body">
      <div class="chat-page__main-row">
        <div class="chat-page__main">
          <div class="chat-page__panel">
            <div v-if="loading" class="chat-page__empty">对话初始化中…</div>
            <div v-else class="chat-page__messages">
              <template v-for="(m, i) in messages">
                <div v-if="showTimeDivider(i)" class="chat-page__time-divider">{{ formatDividerTime(m.created_at) }}</div>
                <ChatBubble :role="m.role" :content="m.content" :error="m.error" />
                <OptionButtonGroup
                  v-if="m.role === 'assistant' && !m.error && i === messages.length - 1"
                  :options="options"
                  @select="pick"
                />
              </template>
            </div>
            <div class="chat-page__composer">
              <div class="chat-page__input">
                <div v-if="attachments.length" class="chat-page__attachments">
                  <NTag
                    v-for="a in attachments"
                    :key="a.fileId"
                    closable
                    size="small"
                    @close="removeAttachment(a.name)"
                  >
                    📎 {{ a.name }}
                  </NTag>
                </div>
                <NInput
                  v-model:value="input"
                  type="textarea"
                  :bordered="false"
                  :autosize="{ minRows: 1, maxRows: 10 }"
                  placeholder="描述您的代工需求，如：需要 5000 台机顶盒，Linux 系统，支持网口和 USB…（Shift+Enter 发送）"
                  :disabled="sending"
                  @keydown.enter="onEnter"
                />
                <div class="chat-page__input-actions">
                  <NButton size="small" :loading="uploading" :disabled="sending" @click="chooseAttachment()">
                    附件
                  </NButton>
                  <NButton
                    type="primary"
                    size="small"
                    :loading="sending"
                    :disabled="!input.trim()"
                    @click="send()"
                  >
                    发送
                  </NButton>
                </div>
              </div>
              <input ref="fileInput" type="file" style="display: none" @change="onFileSelected" />
            </div>
          </div>
        </div>
        <aside class="chat-page__aside">
          <!-- 当前需求 card -->
          <div class="chat-page__aside-card chat-page__demand" :class="{ 'is-collapsed': asideCollapsed }">
            <div class="chat-page__aside-head">
              <h3>当前需求</h3>
              <NButton text size="small" @click="asideCollapsed = !asideCollapsed">
                {{ asideCollapsed ? "展开" : "收起" }}
              </NButton>
            </div>
            <div v-show="!asideCollapsed" class="chat-page__aside-body">
              <DemandProfileCard :points="demandPoints" />
            </div>
            <div v-if="hasProductType() && !asideCollapsed" class="chat-page__demand-footer">
              <NButton type="primary" block @click="confirm()">提交匹配 →</NButton>
            </div>
          </div>

          <!-- 匹配记录 card（可独立收起，方向与当前需求相反） -->
          <div
            class="chat-page__aside-card chat-page__records-card"
            :class="{ 'is-collapsed': recordsCollapsed }"
          >
            <div class="chat-page__aside-head">
              <h3>匹配记录</h3>
              <NButton text size="small" @click="recordsCollapsed = !recordsCollapsed">
                {{ recordsCollapsed ? "展开" : "收起" }}
              </NButton>
            </div>
            <div v-show="!recordsCollapsed" class="chat-page__records-body">
              <div v-if="!records.length" class="chat-page__records-empty">
                暂无匹配结果，完成需求并提交匹配后生成
              </div>
              <div v-else class="chat-page__records-list">
                <div
                  v-for="r in records"
                  :key="r.request_id"
                  class="chat-page__record"
                  @click="openRecord(r.request_id)"
                >
                  <div class="chat-page__record-top">
                    <span class="chat-page__record-name">
                      {{ recordTitle(r) }}
                    </span>
                    <NPopconfirm
                      @positive-click="deleteRecord(r)"
                      positive-text="删除"
                      negative-text="取消"
                    >
                      <template #trigger>
                        <NButton text size="small" type="error" class="chat-page__record-del" @click.stop>
                          删除
                        </NButton>
                      </template>
                      删除该匹配记录？
                    </NPopconfirm>
                  </div>
                  <div class="chat-page__record-meta">
                    <span class="chat-page__record-time">{{ formatSessionTime(r.created_at) }}</span>
                    <span class="chat-page__record-count">找到 {{ r.match_count ?? 0 }} 家</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: row;
  height: calc(100vh - 56px - var(--space-12) - var(--space-12));
  gap: var(--space-12);
}
/* 左侧：常驻会话列表 */
.chat-page__rail {
  width: 300px;
  flex: none;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-panel);
  border: var(--border-width-1) solid var(--color-border-subtle);
  border-radius: var(--radius-12);
  overflow: hidden;
}
.chat-page__rail-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-12) var(--space-12) 0;
}
.chat-page__rail-head span {
  font-weight: var(--font-weight-600);
  font-size: var(--font-size-16);
}
.chat-page__rail-list {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-12);
  display: flex;
  flex-direction: column;
  gap: var(--space-12);
}
.chat-page__rail-item {
  padding: var(--space-12);
  border: var(--border-width-1) solid var(--color-border-subtle);
  border-radius: var(--radius-8);
  cursor: pointer;
}
.chat-page__rail-item:hover {
  border-color: var(--color-primary);
}
.chat-page__rail-item.is-active {
  border-color: var(--color-primary);
  background: var(--color-primary-bg);
}
.chat-page__rail-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-8);
}
.chat-page__rail-id {
  font-size: var(--font-size-13);
  font-weight: var(--font-weight-600);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.chat-page__rail-meta {
  margin-top: var(--space-8);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-8);
  font-size: var(--font-size-12);
  color: var(--color-text-secondary);
}
.chat-page__rail-del {
  color: var(--color-text-secondary);
}
.chat-page__rail-del:hover {
  color: var(--color-error);
}
.chat-page__rail-empty {
  padding: var(--space-24);
  text-align: center;
  color: var(--color-text-secondary);
  font-size: var(--font-size-13);
}
.chat-page__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.chat-page__main-row {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: var(--space-12);
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
  padding: var(--space-12);
}
.chat-page__time-divider {
  text-align: center;
  margin: var(--space-16) 0;
  font-size: var(--font-size-11);
  color: var(--color-text-secondary);
}
.chat-page__empty {
  padding: var(--space-24);
  color: var(--color-text-secondary);
}
.chat-page__composer {
  display: flex;
  gap: var(--space-12);
  padding: var(--space-12);
}
.chat-page__input {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-8);
  border: var(--border-width-1) solid var(--color-border-subtle);
  border-radius: var(--radius-12);
  padding: var(--space-8);
  background: var(--color-bg-panel);
}
.chat-page__input :deep(.n-input) {
  width: 100%;
}
.chat-page__input :deep(.n-input__textarea-el) {
  line-height: var(--line-height-normal);
}
.chat-page__input-actions {
  flex: none;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-8);
}
.chat-page__attachments {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-8);
  margin-bottom: var(--space-8);
}
.chat-page__aside {
  width: 320px;
  flex: none;
  display: flex;
  flex-direction: column;
  gap: var(--space-12);
  min-height: 0;
}
/* 独立 card：当前需求 与 匹配记录 各占一半 */
.chat-page__aside-card {
  flex: 1 1 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-12);
  background: var(--color-bg-panel);
  border: var(--border-width-1) solid var(--color-border-subtle);
  border-radius: var(--radius-12);
  padding: var(--space-12);
  overflow-y: auto;
}
.chat-page__demand {
  overflow: hidden;
}
.chat-page__demand.is-collapsed {
  flex: 0 0 auto;
}
.chat-page__aside-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex: none;
}
.chat-page__aside-head h3 {
  margin: 0;
  font-size: var(--font-size-16);
}
.chat-page__aside-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-12);
}
.chat-page__demand-footer {
  flex: none;
  padding-top: var(--space-12);
}
.chat-page__records-card.is-collapsed {
  flex: 0 0 auto;
}
.chat-page__records-empty {
  font-size: var(--font-size-13);
  color: var(--color-text-secondary);
  padding: var(--space-8) 0;
}
.chat-page__records-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-8);
}
.chat-page__record {
  padding: var(--space-12);
  border: var(--border-width-1) solid var(--color-border-subtle);
  border-radius: var(--radius-8);
  cursor: pointer;
}
.chat-page__record:hover {
  border-color: var(--color-primary);
}
.chat-page__record-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-8);
}
.chat-page__record-name {
  font-size: var(--font-size-13);
  font-weight: var(--font-weight-600);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.chat-page__record-del {
  color: var(--color-text-secondary);
}
.chat-page__record-del:hover {
  color: var(--color-error);
}
.chat-page__record-meta {
  margin-top: var(--space-8);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-8);
  font-size: var(--font-size-12);
  color: var(--color-text-secondary);
}
</style>
