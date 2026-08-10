<script setup lang="ts">
/**
 * 事件日志（最终菜单 05）：admin_logs 审计（管理员操作/登录/导出/配置，append-only）。
 * 动作筛选 + 卡片表格（动作/对象/管理员/时间）+ 详情抽屉（完整 detail）。
 */
import { computed, h, onMounted, ref } from "vue"
import {
  NButton,
  NDataTable,
  NDrawer,
  NSelect,
  NTag,
  NSpin,
  useMessage,
  type DataTableColumns,
} from "naive-ui"

import { adminLogs, type AdminLogItem } from "@xmsn/api"

const message = useMessage()
const loading = ref(true)
const rows = ref<AdminLogItem[]>([])
const action = ref<string | null>(null)

const drawerOpen = ref(false)
const current = ref<AdminLogItem | null>(null)

const ACTION_OPTIONS = [
  { label: "厂商审核", value: "vendor_audit" },
  { label: "管理员登录", value: "login" },
  { label: "导出数据", value: "export" },
  { label: "配置变更", value: "config_change" },
]
const ACTION_META: Record<string, { type: "info" | "success" | "warning" | "default" }> = {
  vendor_audit: { type: "warning" },
  login: { type: "info" },
  export: { type: "success" },
  config_change: { type: "default" },
}

/** 时间格式化：MM-DD HH:mm。 */
function formatTime(iso?: string): string {
  if (!iso) return "—"
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const pad = (n: number): string => String(n).padStart(2, "0")
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** 目标对象摘要：target_type + target_id。 */
function targetText(row: AdminLogItem): string {
  if (!row.target_type) return "—"
  return `${row.target_type} · ${row.target_id ?? ""}`
}

/** detail 摘要（单行）。 */
function detailSummary(row: AdminLogItem): string {
  try {
    return Object.entries(row.detail ?? {})
      .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join("/") : String(v)}`)
      .join(" · ")
  } catch {
    return "—"
  }
}

const filtered = computed(() => {
  if (!action.value) return rows.value
  return rows.value.filter((r) => r.action === action.value)
})

const columns: DataTableColumns<AdminLogItem> = [
  {
    title: "动作",
    key: "action",
    width: 130,
    render: (row) =>
      h(
        NTag,
        { size: "small", type: ACTION_META[row.action]?.type ?? "default", bordered: false },
        { default: () => row.action_label || row.action },
      ),
  },
  {
    title: "对象",
    key: "target_type",
    width: 170,
    render: (row) => targetText(row),
  },
  { title: "详情摘要", key: "detail", render: (row) => detailSummary(row) },
  {
    title: "操作者",
    key: "admin_name",
    width: 100,
    render: (row) => row.admin_name || "—",
  },
  {
    title: "时间",
    key: "created_at",
    width: 130,
    render: (row) => formatTime(row.created_at),
  },
  {
    title: "操作",
    key: "actions",
    width: 90,
    render: (row) =>
      h(
        NButton,
        {
          size: "small",
          onClick: () => {
            current.value = row
            drawerOpen.value = true
          },
        },
        { default: () => "查看" },
      ),
  },
]

async function load(): Promise<void> {
  loading.value = true
  try {
    const res = await adminLogs(action.value, 1, 100)
    rows.value = res.list ?? []
  } catch {
    message.error("加载事件日志失败")
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="logs-page">
    <div class="logs-page__filters">
      <NSelect
        v-model:value="action"
        :options="ACTION_OPTIONS"
        placeholder="动作类型"
        clearable
        style="width: 160px"
      />
      <NButton @click="load()">查询</NButton>
    </div>

    <div class="logs-page__table-card">
      <NDataTable
        :columns="columns"
        :data="filtered"
        :loading="loading"
        :bordered="false"
        striped
        :row-key="(r) => r.log_id"
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
      width="520px"
      :content-style="{ padding: '16px 24px 24px' }"
      :title="`事件详情 ${current?.action_label ?? ''}`"
    >
      <NSpin :show="loading">
        <template v-if="current">
          <h4 class="logs-page__sub">基本信息</h4>
          <div class="logs-page__kv">
            <div><span>动作</span><b>{{ current.action_label || current.action }}</b></div>
            <div><span>对象类型</span><b>{{ current.target_type ?? "—" }}</b></div>
            <div><span>对象ID</span><b>{{ current.target_id ?? "—" }}</b></div>
            <div><span>操作者</span><b>{{ current.admin_name || "—" }}</b></div>
            <div><span>时间</span><b>{{ formatTime(current.created_at) }}</b></div>
          </div>

          <h4 class="logs-page__sub">详情</h4>
          <pre class="logs-page__json">{{ JSON.stringify(current.detail ?? {}, null, 2) }}</pre>
        </template>
      </NSpin>
    </NDrawer>
  </div>
</template>

<style scoped>
.logs-page__filters {
  display: flex;
  gap: var(--space-12);
  margin-bottom: var(--space-16);
}
.logs-page__table-card {
  padding: var(--space-16);
  background: var(--color-bg-panel);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-12);
  box-shadow: var(--shadow-1);
}
.logs-page__sub {
  margin: var(--space-16) 0 var(--space-8);
  font-size: 14px;
  font-weight: var(--font-weight-600);
}
.logs-page__kv {
  display: flex;
  flex-direction: column;
  gap: 0;
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-8);
  overflow: hidden;
}
.logs-page__kv div {
  display: flex;
  justify-content: space-between;
  gap: var(--space-16);
  padding: var(--space-12) var(--space-16);
}
.logs-page__kv div + div {
  border-top: 1px solid var(--color-border-subtle);
}
.logs-page__kv span {
  color: var(--color-text-secondary);
}
.logs-page__json {
  margin: 0;
  padding: var(--space-12);
  background: var(--color-bg);
  border-radius: var(--radius-8);
  font-size: 13px;
  overflow: auto;
}
</style>
