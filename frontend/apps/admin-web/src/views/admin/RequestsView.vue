<script setup lang="ts">
/**
 * 需求匹配（最终菜单 04）：行=需求档案（=一次匹配，1:1 匹配实体）。客户/产品/匹配结果
 * （基于 run.status）/版本/时间 + 详情抽屉（匹配实体物化统计 + 厂商列表 + 三组判定）。
 */
import { computed, h, onMounted, ref } from "vue"
import {
  NButton,
  NDataTable,
  NDrawer,
  NInput,
  NSelect,
  NSpin,
  NTag,
  useMessage,
  type DataTableColumns,
} from "naive-ui"

import {
  adminRequests,
  matchCompute,
  matchDetailMatchId,
  pollUntil,
  type AdminRequestItem,
  type MatchDetailResponse,
  type MatchItem,
} from "@xmsn/api"

const message = useMessage()
const loading = ref(true)
const rows = ref<AdminRequestItem[]>([])
const keyword = ref("")
const status = ref<string | null>(null)

const drawerOpen = ref(false)
const current = ref<AdminRequestItem | null>(null)
const runMetaText = ref("")
const runEmpty = ref(false)

// 抽屉内：厂商列表 + 选中厂商详情
const matchItems = ref<MatchItem[]>([])
const detail = ref<MatchDetailResponse | null>(null)
const detailLoading = ref(false)
const selectedVendorId = ref("")

function renderDemand(row: AdminRequestItem): string {
  const d = row.structured_demand as Record<string, unknown>
  return Object.entries(d ?? {})
    .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join("/") : String(v)}`)
    .join(" · ")
}

/** 时间格式化：MM-DD HH:mm。 */
function formatTime(iso?: string): string {
  if (!iso) return "—"
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const pad = (n: number): string => String(n).padStart(2, "0")
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** 手机号脱敏：139****0001。 */
function maskPhone(phone?: string): string {
  if (!phone || phone.length < 7) return phone ?? "—"
  return `${phone.slice(0, 3)}****${phone.slice(-4)}`
}

/** 匹配实体元信息文本（物化字段）。 */
function buildRunMeta(r: AdminRequestItem["run"]): string {
  if (!r) return ""
  const parts = [`匹配 ${r.total_vendors ?? 0} 家`]
  if (r.best_score != null) parts.push(`最佳 ${r.best_score}%`)
  if (r.computation_time_ms) parts.push(`耗时 ${(r.computation_time_ms / 1000).toFixed(2)}s`)
  return parts.join(" · ")
}

const filtered = computed(() => {
  let list = rows.value
  if (keyword.value.trim()) {
    const k = keyword.value.trim().toLowerCase()
    list = list.filter((r) => {
      const d = r.structured_demand as Record<string, unknown>
      return (
        r.request_id.toLowerCase().includes(k) ||
        r.customer_phone?.toLowerCase().includes(k) ||
        JSON.stringify(d ?? {}).toLowerCase().includes(k)
      )
    })
  }
  if (status.value) {
    if (status.value === "matched") list = list.filter((r) => r.run?.status === "done")
    if (status.value === "empty") list = list.filter((r) => r.run?.status === "empty")
  }
  return list
})

/** 匹配状态渲染：基于 run.status（done=有厂商 / empty=无合适厂商 / 无 run=—）。 */
function renderMatchStatus(row: AdminRequestItem) {
  const run = row.run
  if (!run) return h(NTag, { size: "small", type: "default", bordered: false }, { default: () => "—" })
  if (run.status === "empty") {
    return h(NTag, { size: "small", type: "warning", bordered: false }, { default: () => "无合适厂商" })
  }
  return h(
    NTag,
    { size: "small", type: "success", bordered: false },
    { default: () => `找到 ${run.total_vendors ?? 0} 家` },
  )
}

const columns: DataTableColumns<AdminRequestItem> = [
  {
    title: "客户",
    key: "customer_phone",
    width: 130,
    render: (row) => maskPhone(row.customer_phone),
  },
  {
    title: "产品类型",
    key: "product_type",
    width: 120,
    render: (row) =>
      h(
        NTag,
        { size: "small", type: "info", bordered: false },
        { default: () => String((row.structured_demand as Record<string, unknown>)?.product_type ?? "—") },
      ),
  },
  { title: "需求画像", key: "structured_demand", render: (row) => renderDemand(row) },
  { title: "匹配结果", key: "run", width: 130, render: (row) => renderMatchStatus(row) },
  { title: "版本", key: "version", width: 70, align: "center", render: (row) => `v${row.version}` },
  { title: "提交时间", key: "created_at", width: 130, render: (row) => formatTime(row.created_at) },
  {
    title: "操作",
    key: "actions",
    width: 90,
    render: (row) =>
      h(NButton, { size: "small", onClick: () => void openDetail(row) }, { default: () => "查看" }),
  },
]

async function openDetail(row: AdminRequestItem): Promise<void> {
  current.value = row
  drawerOpen.value = true
  runMetaText.value = buildRunMeta(row.run)
  runEmpty.value = row.run?.status === "empty"
  matchItems.value = []
  detail.value = null
  selectedVendorId.value = ""
  try {
    const res = await matchCompute({ request_id: row.request_id })
    matchItems.value = res.match_results ?? []
  } catch {
    matchItems.value = []
  }
}

/** 抽屉内点选厂商 → 拉取匹配详情（三组判定）。 */
async function selectVendor(m: MatchItem): Promise<void> {
  selectedVendorId.value = m.match_id
  detailLoading.value = true
  detail.value = null
  try {
    detail.value = await pollUntil(
      () => matchDetailMatchId(m.match_id),
      (d) => d.explanation_status === "ready",
      { intervalMs: 1000, timeoutMs: 30_000 },
    )
  } catch {
    message.error("加载匹配详情失败")
  } finally {
    detailLoading.value = false
  }
}

function exportCsv(): void {
  const header = "需求ID,版本,客户,产品类型,需求画像,匹配厂商数,最佳匹配,提交时间"
  const lines = filtered.value.map((r) =>
    [
      r.request_id,
      r.version,
      r.customer_phone ?? "",
      (r.structured_demand as Record<string, unknown>)?.product_type ?? "",
      renderDemand(r),
      r.run?.total_vendors ?? 0,
      r.run?.best_score ?? "",
      r.created_at,
    ].join(","),
  )
  const csv = [header, ...lines].join("\n")
  const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = "requests.csv"
  a.click()
  URL.revokeObjectURL(url)
  message.success(`已导出 ${filtered.value.length} 条`)
}

onMounted(async () => {
  try {
    const res = await adminRequests(1, 100)
    rows.value = res.list ?? []
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="requests-page">
    <div class="requests-page__filters">
      <NInput v-model:value="keyword" placeholder="搜索需求ID/产品/客户" clearable style="width: 240px" @keyup.enter="() => {}" />
      <NSelect
        v-model:value="status"
        :options="[
          { label: '已匹配', value: 'matched' },
          { label: '无合适厂商', value: 'empty' },
        ]"
        placeholder="匹配结果"
        clearable
        style="width: 140px"
      />
      <NButton @click="exportCsv()">导出 CSV</NButton>
    </div>
    <div class="requests-page__table-card">
      <NDataTable
        :columns="columns"
        :data="filtered"
        :loading="loading"
        :bordered="false"
        striped
        :row-key="(r) => r.request_id"
        :pagination="{
          pageSize: 10,
          showSizePicker: true,
          pageSizes: [10, 20],
        }"
      />
    </div>

    <NDrawer
      v-model:show="drawerOpen"
      placement="right"
      width="680px"
      :content-style="{ padding: '16px 24px 24px' }"
      :title="`需求详情 ${current?.request_id ?? ''}`"
    >
      <template v-if="current">
        <h4 class="requests-page__sub">基本信息</h4>
        <div class="requests-page__kv">
          <div><span>客户</span><b>{{ maskPhone(current.customer_phone) }}</b></div>
          <div><span>会话ID</span><b>{{ current.conversation_id }}</b></div>
          <div><span>版本</span><b>v{{ current.version }}</b></div>
          <div><span>提交时间</span><b>{{ formatTime(current.created_at) }}</b></div>
        </div>

        <h4 class="requests-page__sub">结构化需求</h4>
        <pre class="requests-page__json">{{ JSON.stringify(current.structured_demand, null, 2) }}</pre>

        <!-- 匹配实体：物化统计条（匹配行为存在；empty 表示无合适厂商） -->
        <div class="requests-page__run" :class="{ 'is-empty': runEmpty }">
          <span class="requests-page__run-label">匹配实体</span>
          <span v-if="runEmpty" class="requests-page__run-text">本次匹配未找到合适厂商</span>
          <span v-else class="requests-page__run-text">{{ runMetaText }}</span>
        </div>

        <h4 class="requests-page__sub">厂商列表（{{ matchItems.length }} 家）</h4>
        <div v-if="matchItems.length" class="requests-page__matches">
          <div
            v-for="m in matchItems"
            :key="m.match_id"
            class="requests-page__match"
            :class="{ 'is-selected': m.match_id === selectedVendorId }"
            @click="selectVendor(m)"
          >
            <span class="requests-page__match-mark">{{ m.company_name.slice(0, 1) }}</span>
            <span class="name">{{ m.company_name }}</span>
            <NTag v-if="(m.missing_count ?? 0) > 0" size="tiny" type="warning" :bordered="false">未声明 {{ m.missing_count }}</NTag>
            <span class="score">{{ m.match_score.toFixed(1) }} 分</span>
          </div>
        </div>
        <p v-else-if="runEmpty" class="requests-page__hist-hint">
          本次匹配已执行但未找到合适厂商（匹配实体已保留）。
        </p>
        <p v-else>该需求暂无匹配记录</p>

        <!-- 选中厂商 → 匹配详情（三组判定 + AI 评语） -->
        <template v-if="detail">
          <h4 class="requests-page__sub">{{ detail.company_name }} · 匹配详情</h4>
          <div v-if="detail.ai_comment" class="requests-page__summary">{{ detail.ai_comment }}</div>
          <div v-if="detail.matched_params?.length" class="requests-page__group requests-page__group--match">
            <h5>✅ 匹配项</h5>
            <div v-for="p in detail.matched_params" :key="p.key" class="requests-page__param">
              <span>{{ p.label }}</span><b>{{ p.value }}</b>
            </div>
          </div>
          <div v-if="detail.partial_params?.length" class="requests-page__group requests-page__group--partial">
            <h5>⚠️ 未声明项</h5>
            <div v-for="p in detail.partial_params" :key="p.key" class="requests-page__param">
              <span>{{ p.label }}</span><b>{{ p.value }}</b>
            </div>
          </div>
          <div v-if="detail.unmatched_params?.length" class="requests-page__group requests-page__group--unmatched">
            <h5>❌ 不匹配项</h5>
            <div v-for="p in detail.unmatched_params" :key="p.key" class="requests-page__param">
              <span>{{ p.label }}</span><b>{{ p.value }}</b>
            </div>
          </div>
        </template>
        <p v-if="detailLoading" class="requests-page__hist-hint">匹配详情生成中…</p>
      </template>
    </NDrawer>
  </div>
</template>

<style scoped>
.requests-page__filters {
  display: flex;
  gap: var(--space-12);
  margin-bottom: var(--space-16);
}
.requests-page__table-card {
  padding: var(--space-16);
  background: var(--color-bg-panel);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-12);
  box-shadow: var(--shadow-1);
}
.requests-page__sub {
  margin: var(--space-16) 0 var(--space-8);
  font-size: 14px;
  font-weight: var(--font-weight-600);
}
.requests-page__kv {
  display: flex;
  flex-direction: column;
  gap: 0;
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-8);
  overflow: hidden;
}
.requests-page__kv div {
  display: flex;
  justify-content: space-between;
  gap: var(--space-16);
  padding: var(--space-12) var(--space-16);
}
.requests-page__kv div + div {
  border-top: 1px solid var(--color-border-subtle);
}
.requests-page__kv span {
  color: var(--color-text-secondary);
}
.requests-page__json {
  margin: 0;
  padding: var(--space-12);
  background: var(--color-bg);
  border-radius: var(--radius-8);
  font-size: 13px;
  overflow: auto;
}
.requests-page__run {
  display: flex;
  align-items: center;
  gap: var(--space-12);
  margin-top: var(--space-16);
  padding: var(--space-12) var(--space-16);
  background: var(--color-primary-bg);
  border-left: 3px solid var(--color-primary);
  border-radius: var(--radius-8);
}
.requests-page__run.is-empty {
  background: var(--color-warning-bg);
  border-left-color: var(--color-warning);
}
.requests-page__run-label {
  font-size: 12px;
  color: var(--color-text-secondary);
  white-space: nowrap;
}
.requests-page__run-text {
  font-size: 14px;
  font-weight: var(--font-weight-600);
}
.requests-page__matches {
  display: flex;
  flex-direction: column;
  gap: var(--space-8);
}
.requests-page__match {
  display: flex;
  align-items: center;
  gap: var(--space-8);
  padding: var(--space-8) var(--space-12);
  background: var(--color-bg);
  border-radius: var(--radius-8);
  font-size: 13px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: border-color var(--duration-fast) var(--ease-standard);
}
.requests-page__match:hover {
  border-color: var(--color-primary);
}
.requests-page__match.is-selected {
  border-color: var(--color-primary);
  background: var(--color-primary-bg);
}
.requests-page__match-mark {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: var(--radius-6);
  background: var(--color-primary-bg);
  color: var(--color-primary);
  font-size: 12px;
  font-weight: var(--font-weight-600);
}
.requests-page__match .name {
  flex: 1;
}
.requests-page__match .score {
  font-weight: var(--font-weight-600);
  color: var(--color-primary);
}
.requests-page__summary {
  margin: 0 0 var(--space-12);
  padding: var(--space-12);
  background: var(--color-primary-bg);
  border-left: 3px solid var(--color-primary);
  border-radius: var(--radius-8);
  line-height: var(--line-height-loose);
  font-size: 13px;
}
.requests-page__group {
  padding: var(--space-12);
  border-radius: var(--radius-8);
  margin-bottom: var(--space-12);
}
.requests-page__group h5 {
  margin: 0 0 var(--space-8);
  font-size: 13px;
}
.requests-page__group--match {
  background: var(--color-match-success-bg);
}
.requests-page__group--partial {
  background: var(--color-match-warning-bg);
}
.requests-page__group--unmatched {
  background: var(--color-match-error-bg);
}
.requests-page__param {
  display: flex;
  justify-content: space-between;
  gap: var(--space-16);
  padding: var(--space-4) 0;
  font-size: 13px;
}
.requests-page__param span {
  color: var(--color-text-secondary);
}
.requests-page__hist-hint {
  margin-top: var(--space-12);
  font-size: 12px;
  color: var(--color-disabled);
}
</style>
