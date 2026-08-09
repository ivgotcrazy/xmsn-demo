<script setup lang="ts">
/**
 * 03C 需求与匹配查看（原型 4.2）：面包屑 + 搜索筛选栏 + 表格 + "查看"抽屉 + 导出 CSV。
 */
import { computed, h, onMounted, ref } from "vue"
import {
  NButton,
  NDataTable,
  NDrawer,
  NInput,
  NSelect,
  NTag,
  useMessage,
  type DataTableColumns,
} from "naive-ui"

import { adminRequests, matchCompute, type AdminRequestItem, type MatchItem } from "@xmsn/api"

const message = useMessage()
const loading = ref(true)
const rows = ref<AdminRequestItem[]>([])
const keyword = ref("")
const status = ref<string | null>(null)

const drawerOpen = ref(false)
const current = ref<AdminRequestItem | null>(null)

function renderDemand(row: AdminRequestItem): string {
  const d = row.structured_demand as Record<string, unknown>
  return Object.entries(d ?? {})
    .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join("/") : String(v)}`)
    .join(" · ")
}

const filtered = computed(() => {
  let list = rows.value
  if (keyword.value) {
    const k = keyword.value.trim().toLowerCase()
    list = list.filter((r) => {
      const d = r.structured_demand as Record<string, unknown>
      return (
        r.request_id.toLowerCase().includes(k) ||
        JSON.stringify(d ?? {}).toLowerCase().includes(k)
      )
    })
  }
  if (status.value) {
    const matched = status.value === "matched"
    list = list.filter((r) => ((r.match_count ?? 0) > 0) === matched)
  }
  return list
})

const matchItems = ref<MatchItem[]>([])

async function openDetail(row: AdminRequestItem): Promise<void> {
  current.value = row
  drawerOpen.value = true
  matchItems.value = []
  try {
    const res = await matchCompute({ request_id: row.request_id })
    matchItems.value = res.match_results ?? []
  } catch {
    matchItems.value = []
  }
}

function exportCsv(): void {
  const header = "需求ID,版本,需求画像,匹配次数,提交时间"
  const lines = filtered.value.map((r) =>
    [r.request_id, r.version, renderDemand(r), r.match_count ?? 0, r.created_at].join(","),
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

const columns: DataTableColumns<AdminRequestItem> = [
  { title: "需求ID", key: "request_id", width: 190 },
  {
    title: "产品类型",
    key: "product_type",
    width: 120,
    render: (row) => String((row.structured_demand as Record<string, unknown>)?.product_type ?? "—"),
  },
  { title: "需求画像", key: "structured_demand", render: (row) => renderDemand(row) },
  {
    title: "匹配状态",
    key: "match_count",
    width: 110,
    render: (row) =>
      h(
        NTag,
        { size: "small", type: (row.match_count ?? 0) > 0 ? "success" : "default", bordered: false },
        { default: () => ((row.match_count ?? 0) > 0 ? "已匹配" : "未匹配") },
      ),
  },
  { title: "提交时间", key: "created_at", width: 190 },
  {
    title: "操作",
    key: "actions",
    width: 90,
    render: (row) =>
      h(NButton, { size: "small", onClick: () => void openDetail(row) }, { default: () => "查看" }),
  },
]

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
    <div class="requests-page__crumb">管理员后台 / 需求与匹配</div>
    <div class="requests-page__filters">
      <NInput v-model:value="keyword" placeholder="搜索关键词" clearable style="width: 240px" />
      <NSelect
        v-model:value="status"
        :options="[
          { label: '已匹配', value: 'matched' },
          { label: '未匹配', value: 'unmatched' },
        ]"
        placeholder="匹配状态"
        clearable
        style="width: 140px"
      />
      <NButton @click="exportCsv()">导出 CSV</NButton>
    </div>
    <NDataTable
      :columns="columns"
      :data="filtered"
      :loading="loading"
      :bordered="false"
      :row-key="(r) => r.request_id"
    />

    <NDrawer
      v-model:show="drawerOpen"
      placement="right"
      width="640px"
      :title="`需求详情 ${current?.request_id ?? ''}`"
    >
      <template v-if="current">
        <h4>结构化需求</h4>
        <pre class="requests-page__json">{{ JSON.stringify(current.structured_demand, null, 2) }}</pre>
        <h4>匹配结果（{{ matchItems.length }} 家）</h4>
        <div v-if="matchItems.length" class="requests-page__matches">
          <div v-for="m in matchItems" :key="m.match_id" class="requests-page__match">
            <span class="name">{{ m.company_name }}</span>
            <NTag v-if="m.critical_fail" size="tiny" type="error" :bordered="false">关键参数不符</NTag>
            <span class="score">{{ m.match_score.toFixed(1) }} 分</span>
          </div>
        </div>
        <p v-else>该需求暂无匹配记录</p>
        <p class="requests-page__hist-hint">完整对话历史将在接入真实会话数据后展示。</p>
      </template>
    </NDrawer>
  </div>
</template>

<style scoped>
.requests-page__crumb {
  margin-bottom: var(--space-16);
  font-size: var(--font-size-13);
  color: var(--color-text-secondary);
}
.requests-page__filters {
  display: flex;
  gap: var(--space-12);
  margin-bottom: var(--space-16);
}
.requests-page__json {
  margin: 0 0 var(--space-16);
  padding: var(--space-12);
  background: var(--color-bg);
  border-radius: var(--radius-8);
  font-size: var(--font-size-13);
  overflow: auto;
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
  font-size: var(--font-size-13);
}
.requests-page__match .name {
  flex: 1;
}
.requests-page__match .score {
  font-weight: var(--font-weight-600);
  color: var(--color-primary);
}
.requests-page__hist-hint {
  margin-top: var(--space-12);
  font-size: var(--font-size-12);
  color: var(--color-disabled);
}
</style>
