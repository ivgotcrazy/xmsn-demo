<script setup lang="ts">
/**
 * 02A 需求对话 Agent（原型）：顶部标题栏 + 新建/我的会话，底部输入栏 + "提交匹配"（单端点），
 * 右侧"需求档案"悬浮摘要面板（可折叠），对话萃取 + 选项回填 + 三态档案 + 确认提交。
 */
import { computed, nextTick, onMounted, ref, watch } from "vue"
import { useRouter } from "vue-router"
import { NButton, NInput, NModal, NPopconfirm, NTag, useMessage } from "naive-ui"

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

// NModal 默认 teleport 到 body，脱离 .theme-b2b 作用域导致主题 CSS 变量不级联；
// 挂到客户侧 theme 根内，使确认弹框正确应用 MASTER 语义 token。
const modalTo = ".main-layout.theme-b2b"

const messages = ref<{ role: "assistant" | "user"; content: string; error?: boolean; created_at?: string }[]>([])
const options = ref<string[]>([])
const optionsType = ref<"none" | "single" | "multi" | "actions">("none")
const input = ref("")
// 前端「当前需求」：基于会话历史萃取的需求点集合（schema 实例 + strictness，D5/D7）
const demandPoints = ref<DemandPoint[]>([])
// D7 两步化：确认框（strictness 可微调）→ 正式提交
const confirmOpen = ref(false)
const editablePoints = ref<DemandPoint[]>([])
const version = ref<number | null>(null)
const conversationId = ref("")
const sending = ref(false)
const loading = ref(true)
const asideCollapsed = ref(false)
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

// 聊天体验：①消息列表自动跟随最新（滚动到底）；②发送后恢复输入焦点（sending 期间 disabled 会夺焦）
const msgListRef = ref<HTMLElement | null>(null)
const inputRef = ref<{ focus: () => void } | null>(null)

function scrollToBottom(): void {
  void nextTick(() => {
    const el = msgListRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}
// flush:"post"：DOM 渲染后执行——消息列表 div 仅在 loading=false 时才存在（v-else），
// 需同时 watch loading 翻转，否则加载时 msgListRef 为 null 导致首次滚动被跳过
watch(() => [messages.value.length, loading.value], scrollToBottom, { flush: "post" })

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

/** 提交门槛（D12）：是否已有品类外的需求点（固定维度或扩展需求），用于禁用/隐藏提交入口。 */
function hasOtherDemandPoints(): boolean {
  return demandPoints.value.some((p) => p.key !== "product_type")
}

/** 可提交：已明确产品类型且已有品类外需求点（D12）。 */
const canSubmit = computed<boolean>(() => hasProductType() && hasOtherDemandPoints())

/** 提交门槛未达时的提示文案（替代裸置灰按钮，向用户说明下一步）。 */
const submitHintText = computed<string>(() => {
  if (!hasProductType()) return "请先明确要寻找的产品类型（如智能音箱、机顶盒）"
  return "补充需求点（如操作系统、认证、起订量等）后即可提交匹配"
})

// 提交确认框（D7 两步化）：品类锚点 / 其余需求点 分组展示
const anchorPoint = computed<DemandPoint | null>(() => editablePoints.value.find((p) => p.key === "product_type") ?? null)
const otherPoints = computed<DemandPoint[]>(() => editablePoints.value.filter((p) => p.key !== "product_type"))

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
    optionsType.value = last?.options_type ?? "none"
    demandPoints.value = res.demand_points ?? []
    version.value = res.version ?? null
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
    const res = await conversationStart({ user_id: "u-customer-001" })
    conversationId.value = res.conversation_id
    messages.value = [{ role: "assistant", content: res.first_message.content, created_at: new Date().toISOString() }]
    options.value = res.first_message.options ?? []
    optionsType.value = res.first_message.options_type ?? "none"
    demandPoints.value = res.demand_points ?? []
    version.value = null
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

async function send(text?: string, clickedOption?: string | string[] | null): Promise<void> {
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
      clicked_option: clickedOption ?? null,
    })
    messages.value.push({ role: "assistant", content: res.assistant_message.content, created_at: new Date().toISOString() })
    options.value = res.assistant_message.options ?? []
    optionsType.value = res.assistant_message.options_type ?? "none"
    // 前端「当前需求」：全量替换为萃取出的需求点集合
    demandPoints.value = res.demand_points ?? []
    // 强命令在聊天内直接提交（SC-22/25）：展示警示并跳转匹配结果页
    if (res.submitted && res.redirect_to) {
      if (res.warnings?.length) {
        res.warnings.forEach((w) => message.warning(w))
      } else {
        message.success("已提交匹配")
      }
      void router.push(res.redirect_to)
      return
    }
    // 一会话一产品：萃取到产品类型后，会话卡标题联动更新（新会话「新会话」→ 产品名）
    if (res.title) {
      const cur = sessions.value.find((s) => s.conversation_id === conversationId.value)
      if (cur) cur.title = res.title
    }
  } catch {
    messages.value.push({ role: "assistant", content: "发送失败，请重试", error: true })
  } finally {
    sending.value = false
    // 输入焦点恢复：sending 置 disabled 会夺焦，请求结束重新聚焦以便连续输入
    void nextTick(() => inputRef.value?.focus())
  }
}

function pick(value: string | string[]): void {
  // "提交匹配" → 两步化确认框（D7）；多选提交数组；单选/动作提交单值
  if (typeof value === "string" && value === "提交匹配") {
    void openConfirm()
    return
  }
  if (Array.isArray(value)) {
    void send(value.join("、"), value) // 多选：确定性直写（clicked_option=list）
    return
  }
  void send(value, value) // 单选/动作：点击即提交
}

function displayVal(v: string | string[]): string {
  return Array.isArray(v) ? v.join("、") : v
}

/** 值 → 标签数组（数组原样；顿号分隔字符串拆开；确认框逐项 chip 展示用）。 */
function splitValue(v: string | string[]): string[] {
  return Array.isArray(v) ? v.map(String) : String(v).split("、").map((s) => s.trim()).filter(Boolean)
}

/** D7 两步化第一步：打开确认框（只读展示需求点 + strictness，可微调） */
function openConfirm(): void {
  if (!conversationId.value) return
  // D12：品类锚定 + 至少 1 个需求点（品类外）
  if (!hasProductType()) {
    message.warning("请先明确要寻找的产品类型")
    return
  }
  const others = demandPoints.value.filter((p) => p.key !== "product_type")
  if (others.length === 0) {
    message.warning("请补充需求点（如操作系统、认证、起订量等）后才能提交匹配")
    return
  }
  editablePoints.value = demandPoints.value.map((p) => ({
    ...p,
    value: Array.isArray(p.value) ? [...p.value] : p.value,
  }))
  confirmOpen.value = true
}

/** 确认框内 strictness 切换（D7 可微调） */
function toggleStrictness(p: DemandPoint): void {
  p.strictness = p.strictness === "strict" ? "best-effort" : "strict"
}

/** 确认框 strictness 概览：共 N 项 · M 必须 · K 尽力。 */
const strictCounts = computed(() => {
  const pts = editablePoints.value
  const strict = pts.filter((p) => p.strictness === "strict").length
  return { total: pts.length, strict, best: pts.length - strict }
})

/** 批量设置其余需求点（非品类锚点）的 strictness。 */
function setAllStrictness(strict: boolean): void {
  otherPoints.value.forEach((p) => {
    p.strictness = strict ? "strict" : "best-effort"
  })
}

async function confirm(): Promise<void> {
  confirmOpen.value = false
  if (!conversationId.value) return
  try {
    const res = await conversationConfirm({
      conversation_id: conversationId.value,
      demand_points: editablePoints.value,
    })
    message.success("已提交匹配")
    // 02A 匹配记录：不跳页，刷新匹配记录并首次自动弹出结果
    await loadRecords()
    // 提交后进入该次匹配的结果页（返回回会话页）
    void router.push(`/customer/matches/${res.request_id}`)
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
  void router.push(`/customer/matches/${requestId}`)
}

/** 匹配记录卡片标题：优先显示匹配产品类型（三态快照 {value,state} 取值）。 */
function recordTitle(r: RequestSnapshot): string {
  const sd = (r.structured_demand as Record<string, any> | undefined) ?? {}
  const pt = sd.product_type
  const val = typeof pt === "object" && pt !== null ? pt.value : pt
  return val ? String(val) : "需求匹配"
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
            <div v-else ref="msgListRef" class="chat-page__messages">
              <template v-for="(m, i) in messages">
                <div v-if="showTimeDivider(i)" class="chat-page__time-divider">{{ formatDividerTime(m.created_at) }}</div>
                <ChatBubble :role="m.role" :content="m.content" :error="m.error" />
                <OptionButtonGroup
                  v-if="m.role === 'assistant' && !m.error && i === messages.length - 1"
                  :options="options"
                  :options-type="optionsType"
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
                    <svg class="chat-page__attach-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" /></svg>{{ a.name }}
                  </NTag>
                </div>
                <NInput
                  ref="inputRef"
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
          <!-- 需求档案 card -->
          <div class="chat-page__aside-card chat-page__demand" :class="{ 'is-collapsed': asideCollapsed }">
            <div class="chat-page__aside-head">
              <h3>需求档案</h3>
              <NButton text size="small" @click="asideCollapsed = !asideCollapsed">
                {{ asideCollapsed ? "展开" : "收起" }}
              </NButton>
            </div>
            <div v-show="!asideCollapsed" class="chat-page__aside-body">
              <DemandProfileCard :points="demandPoints" />
            </div>
            <div v-if="!asideCollapsed" class="chat-page__demand-footer">
              <NButton
                v-if="canSubmit"
                type="primary"
                block
                size="large"
                class="chat-page__submit"
                @click="openConfirm()"
              >
                <template #icon>
                  <svg class="chat-page__submit-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
                </template>
                提交匹配
              </NButton>
              <div v-else class="chat-page__demand-hint">
                <svg class="chat-page__hint-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10" /><path d="M12 8v4M12 16h.01" /></svg>
                <span>{{ submitHintText }}</span>
              </div>
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

    <!-- D7 两步化：提交确认框（需求档案清晰分层展示 + strictness 可微调） -->
    <NModal v-model:show="confirmOpen" preset="card" title="确认提交匹配" class="chat-confirm__modal" :to="modalTo" style="width: 640px">
      <p class="chat-confirm__hint">
        请核对下方需求档案，右侧可切换严格度：<em>必须</em>＝硬性要求、<em>尽力</em>＝倾向项。确认后开始匹配。
      </p>

      <div class="chat-confirm__summary">
        <span>共 <b>{{ strictCounts.total }}</b> 项</span>
        <span class="chat-confirm__summary-strict">必须 {{ strictCounts.strict }}</span>
        <span class="chat-confirm__summary-best">尽力 {{ strictCounts.best }}</span>
      </div>

      <div v-if="!editablePoints.length" class="chat-confirm__empty">
        暂无可确认的需求点，请先在对话中补充。
      </div>

      <div v-else class="chat-confirm__list">
        <!-- 品类锚点：单独高亮 -->
        <div v-if="anchorPoint" class="chat-confirm__section">
          <div class="chat-confirm__section-title">品类锚点</div>
          <div class="chat-confirm__row chat-confirm__row--anchor">
            <div class="chat-confirm__label">{{ anchorPoint.label }}</div>
            <div class="chat-confirm__value">
              <NTag size="small" round type="primary">{{ displayVal(anchorPoint.value) }}</NTag>
            </div>
            <div class="chat-confirm__strict">
              <NButton
                size="tiny"
                round
                :type="anchorPoint.strictness === 'strict' ? 'warning' : 'default'"
                @click="toggleStrictness(anchorPoint)"
              >
                {{ anchorPoint.strictness === "strict" ? "必须" : "尽力" }}
              </NButton>
            </div>
          </div>
        </div>

        <!-- 其余需求点 -->
        <div v-if="otherPoints.length" class="chat-confirm__section">
          <div class="chat-confirm__section-title">
            需求点
            <span class="chat-confirm__count">{{ otherPoints.length }}</span>
            <span class="chat-confirm__batch">
              <button type="button" class="chat-confirm__batch-btn" @click="setAllStrictness(true)">全部必须</button>
              <button type="button" class="chat-confirm__batch-btn" @click="setAllStrictness(false)">全部尽力</button>
            </span>
          </div>
          <div v-for="(p, i) in otherPoints" :key="i" class="chat-confirm__row">
            <div class="chat-confirm__label">{{ p.label }}</div>
            <div class="chat-confirm__value">
              <NTag
                v-for="(v, vi) in splitValue(p.value)"
                :key="vi"
                size="small"
                class="chat-confirm__tag"
              >
                {{ v }}
              </NTag>
            </div>
            <div class="chat-confirm__strict">
              <NButton
                size="tiny"
                round
                :type="p.strictness === 'strict' ? 'warning' : 'default'"
                @click="toggleStrictness(p)"
              >
                {{ p.strictness === "strict" ? "必须" : "尽力" }}
              </NButton>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <div class="chat-confirm__actions">
          <NButton @click="confirmOpen = false">取消</NButton>
          <NButton type="primary" @click="confirm()">确认提交</NButton>
        </div>
      </template>
    </NModal>
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
  border-color: var(--color-accent);
}
.chat-page__rail-item.is-active {
  border-color: var(--color-accent);
  background: var(--color-accent-50);
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
.chat-page__submit-icon {
  width: 16px;
  height: 16px;
}
/* 提交门槛未达：原因提示（替代裸置灰按钮） */
.chat-page__demand-hint {
  display: flex;
  align-items: flex-start;
  gap: var(--space-8);
  padding: var(--space-12);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-8);
  background: var(--color-background);
  font-size: var(--font-size-13);
  line-height: var(--line-height-normal);
  color: var(--color-muted-foreground);
}
.chat-page__hint-icon {
  flex: none;
  width: 16px;
  height: 16px;
  margin-top: 1px;
  color: var(--color-accent);
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
  border-color: var(--color-accent);
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

/* 提交确认框（D7 两步化）：需求档案分层展示，避免信息挤成一坨 */
.chat-confirm__hint {
  margin: 0 0 var(--space-16);
  font-size: var(--font-size-13);
  line-height: var(--line-height-normal);
  color: var(--color-text-secondary);
}
.chat-confirm__hint em {
  font-style: normal;
  font-weight: var(--font-weight-600);
  color: var(--color-accent);
}
.chat-confirm__empty {
  padding: var(--space-24) var(--space-16);
  text-align: center;
  font-size: var(--font-size-13);
  color: var(--color-text-secondary);
  border: var(--border-width-1) dashed var(--color-border-strong);
  border-radius: var(--radius-8);
}
.chat-confirm__list {
  display: flex;
  flex-direction: column;
  gap: var(--space-16);
  max-height: 46vh;
  overflow-y: auto;
}
.chat-confirm__section-title {
  display: flex;
  align-items: center;
  gap: var(--space-8);
  margin-bottom: var(--space-8);
  font-size: var(--font-size-13);
  font-weight: var(--font-weight-600);
  color: var(--color-text-secondary);
}
.chat-confirm__count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 6px;
  border-radius: var(--radius-full);
  background: var(--color-chat-agent-bg);
  font-size: var(--font-size-12);
  font-weight: var(--font-weight-500);
  color: var(--color-text-secondary);
}
.chat-confirm__summary {
  display: flex;
  align-items: center;
  gap: var(--space-12);
  margin: 0 0 var(--space-16);
  font-size: var(--font-size-13);
  color: var(--color-text-secondary);
}
.chat-confirm__summary b { font-weight: var(--font-weight-700); color: var(--color-text); }
.chat-confirm__summary-strict { color: var(--color-warning-text); font-weight: var(--font-weight-700); }
.chat-confirm__summary-best { color: var(--color-text-secondary); }
.chat-confirm__batch {
  margin-left: auto;
  display: inline-flex;
  gap: var(--space-4);
}
.chat-confirm__batch-btn {
  padding: 2px 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  background: var(--color-card);
  color: var(--color-muted-foreground);
  font-size: 12px;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-standard);
}
.chat-confirm__batch-btn:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}
.chat-confirm__batch-btn:focus-visible {
  outline: 3px solid rgba(3, 105, 161, 0.45);
  outline-offset: 2px;
}
.chat-confirm__row {
  display: flex;
  align-items: center;
  gap: var(--space-12);
  padding: var(--space-12);
  border: var(--border-width-1) solid var(--color-border-subtle);
  border-radius: var(--radius-8);
  background: var(--color-bg-panel);
}
.chat-confirm__row + .chat-confirm__row {
  margin-top: var(--space-8);
}
/* 品类锚点行：左侧主题色竖条高亮 */
.chat-confirm__row--anchor {
  border-color: var(--color-border-strong);
  border-left: 3px solid var(--color-accent);
  background: var(--color-accent-50);
}
.chat-confirm__label {
  flex: none;
  width: 96px;
  font-size: var(--font-size-13);
  font-weight: var(--font-weight-600);
  color: var(--color-text-secondary);
}
.chat-confirm__value {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-6);
  font-size: var(--font-size-13);
  color: var(--color-text);
}
.chat-confirm__strict {
  flex: none;
}
.chat-confirm__actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-8);
}
.chat-page__attach-icon {
  width: 13px;
  height: 13px;
  margin-right: 2px;
  vertical-align: -2px;
}
</style>

<style>
/* naive NModal 根元素由 naive 内部渲染、无 scoped data-v，需全局样式；
   弹框经 :to 挂在 .theme-b2b 内，主题 CSS 变量可级联。 */
.chat-confirm__modal {
  border-radius: var(--radius-16) !important;
  box-shadow: var(--shadow-xl) !important;
}
.chat-confirm__modal .n-card-content {
  padding: var(--space-xl) !important;
}
</style>
