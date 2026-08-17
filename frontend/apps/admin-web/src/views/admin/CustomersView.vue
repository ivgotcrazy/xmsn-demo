<script setup lang="ts">
/**
 * 客户管理（最终菜单 02）：所有注册客户。搜索/状态筛选 + 卡片表格（手机号脱敏、状态、
 * 会话数/需求数/最近活跃/注册时间）+ 详情抽屉（基本信息 + 需求行为 + 需求记录）。
 */
import { computed, h, onMounted, ref } from "vue"
import {
  NButton,
  NDataTable,
  NDrawer,
  NInput,
  NSelect,
  NTag,
  NSpin,
  useMessage,
  type DataTableColumns,
} from "naive-ui"

import { adminCustomers, type CustomerItem } from "@xmsn/api"

const message = useMessage()
const loading = ref(true)
const rows = ref<CustomerItem[]>([])
const keyword = ref("")
const status = ref<string | null>(null)

const drawerOpen = ref(false)
const current = ref<CustomerItem | null>(null)

/** 手机号脱敏：139****0001。 */
function maskPhone(phone?: string): string {
  if (!phone || phone.length < 7) return phone ?? "—"
  return `${phone.slice(0, 3)}****${phone.slice(-4)}`
}

/** 时间格式化：MM-DD HH:mm。 */
function formatTime(iso?: string | null): string {
  if (!iso) return "—"
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const pad = (n: number): string => String(n).padStart(2, "0")
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const filtered = computed(() => {
  let list = rows.value
  if (keyword.value.trim()) {
    const k = keyword.value.trim().toLowerCase()
    list = list.filter((r) => r.phone.toLowerCase().includes(k) || (r.email ?? "").toLowerCase().includes(k))
  }
  if (status.value) {
    list = list.filter((r) => r.status === status.value)
  }
  return list
})

const columns: DataTableColumns<CustomerItem> = [
  {
    title: "手机号",
    key: "phone",
    width: 150,
    render: (row) => maskPhone(row.phone),
  },
  {
    title: "状态",
    key: "status",
    width: 90,
    render: (row) =>
      h(
        NTag,
        { size: "small", type: row.status === "active" ? "success" : "default", bordered: false },
        { default: () => (row.status === "active" ? "正常" : "停用") },
      ),
  },
  {
    title: "会话数",
    key: "conversation_count",
    width: 90,
    align: "center",
    render: (row) => String(row.conversation_count ?? 0),
  },
  {
    title: "需求数",
    key: "request_count",
    width: 90,
    align: "center",
    render: (row) => String(row.request_count ?? 0),
  },
  {
    title: "最近活跃",
    key: "last_active_at",
    width: 130,
    render: (row) => formatTime(row.last_active_at),
  },
  {
    title: "注册时间",
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
    const res = await adminCustomers(keyword.value || null, status.value, 1, 100)
    rows.value = res.list ?? []
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="customers-page">
    <div class="customers-page__filters">
      <NInput v-model:value="keyword" placeholder="搜索手机号/邮箱" clearable style="width: 240px" @keyup.enter="load()" />
      <NSelect
        v-model:value="status"
        :options="[
          { label: '正常', value: 'active' },
          { label: '停用', value: 'disabled' },
        ]"
        placeholder="状态"
        clearable
        style="width: 140px"
      />
      <NButton @click="load()">查询</NButton>
    </div>

    <div class="customers-page__table-card">
      <NDataTable
        :columns="columns"
        :data="filtered"
        :loading="loading"
        :bordered="false"
        striped
        :row-key="(r) => r.user_id"
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
      :title="`客户详情 ${current ? maskPhone(current.phone) : ''}`"
    >
      <NSpin :show="loading">
        <div v-if="current" class="customers-page__drawer-body">
          <h4>基本信息</h4>
          <div class="customers-page__kv">
            <div><span>手机号</span><b>{{ current.phone }}</b></div>
            <div><span>邮箱</span><b>{{ current.email ?? "—" }}</b></div>
            <div><span>角色</span><b>客户</b></div>
            <div><span>状态</span><b>{{ current.status === "active" ? "正常" : "停用" }}</b></div>
            <div><span>注册时间</span><b>{{ formatTime(current.created_at) }}</b></div>
          </div>

          <h4>需求行为</h4>
          <div class="customers-page__kv">
            <div><span>会话数</span><b>{{ current.conversation_count ?? 0 }}</b></div>
            <div><span>需求档案数</span><b>{{ current.request_count ?? 0 }}</b></div>
            <div><span>最近活跃</span><b>{{ formatTime(current.last_active_at) }}</b></div>
          </div>

          <p class="customers-page__hint">需求记录明细将在接入真实需求数据后展示。</p>
        </div>
      </NSpin>
    </NDrawer>
  </div>
</template>

<style scoped>
.customers-page__filters {
  display: flex;
  gap: var(--space-12);
  margin-bottom: var(--space-16);
}
.customers-page__table-card {
  padding: var(--space-16);
  background: var(--color-bg-panel);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-12);
  box-shadow: var(--shadow-1);
}
.customers-page__kv {
  display: flex;
  flex-direction: column;
  gap: 0;
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-8);
  overflow: hidden;
  margin-bottom: var(--space-16);
}
.customers-page__kv div {
  display: flex;
  justify-content: space-between;
  gap: var(--space-16);
  padding: var(--space-12) var(--space-16);
}
.customers-page__kv div + div {
  border-top: 1px solid var(--color-border-subtle);
}
.customers-page__kv span {
  color: var(--color-text-secondary);
}
.customers-page__hint {
  font-size: 12px;
  color: var(--color-disabled);
}
.customers-page__drawer-body h4 {
  margin: 0 0 var(--space-12);
  font-size: 14px;
}
</style>
