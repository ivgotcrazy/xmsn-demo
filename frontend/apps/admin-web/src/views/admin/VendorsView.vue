<script setup lang="ts">
/**
 * 03D 厂商产品查看（原型 4.3 / 1.6）：面包屑 + 搜索 + 表格 + "查看"三标签详情抽屉 + 一键审核。
 */
import { computed, h, onMounted, ref } from "vue"
import {
  NButton,
  NDataTable,
  NDrawer,
  NInput,
  NModal,
  NPopconfirm,
  NSpin,
  NTabPane,
  NTabs,
  NTag,
  useMessage,
  type DataTableColumns,
} from "naive-ui"

import {
  adminVendors,
  adminVendorsVendorIdAudit,
  documentsDocIdPreview,
  vendorCapabilityVendorId,
  vendorVendorId,
  type CapabilityOut,
  type DocumentPreviewResponse,
  type VendorAuditItem,
  type VendorOut,
} from "@xmsn/api"

import { AUDIT_META } from "@xmsn/types"

const message = useMessage()
const loading = ref(true)
const rows = ref<VendorAuditItem[]>([])
const keyword = ref("")

const drawerOpen = ref(false)
const currentVendor = ref<VendorAuditItem | null>(null)
const vendorDetail = ref<VendorOut | null>(null)
const capDetail = ref<CapabilityOut | null>(null)
const detailLoading = ref(false)

// 原始资料文档预览（COMP-034）
const previewOpen = ref(false)
const preview = ref<DocumentPreviewResponse | null>(null)
async function openDocPreview(name: string): Promise<void> {
  previewOpen.value = true
  preview.value = null
  try {
    preview.value = await documentsDocIdPreview("doc-001", 3)
  } catch {
    preview.value = null
  }
  void name
}

const filtered = computed(() => {
  if (!keyword.value) return rows.value
  const k = keyword.value.trim().toLowerCase()
  return rows.value.filter((r) => r.company_name.toLowerCase().includes(k))
})

const TAG_LABEL: Record<string, string> = {
  product_types: "产品类型",
  process_types: "工艺",
  certifications: "认证",
  os_support: "操作系统",
  interfaces: "接口",
  min_order_qty: "起订量",
  lead_time_days: "交期(天)",
  application_scenarios: "应用场景",
}
function display(v: unknown): string {
  return Array.isArray(v) ? v.join("、") : String(v ?? "")
}

async function load(): Promise<void> {
  loading.value = true
  try {
    const res = await adminVendors(undefined, 1, 100)
    rows.value = res.list ?? []
  } finally {
    loading.value = false
  }
}

async function openDetail(row: VendorAuditItem): Promise<void> {
  currentVendor.value = row
  drawerOpen.value = true
  detailLoading.value = true
  vendorDetail.value = null
  capDetail.value = null
  try {
    const [v, c] = await Promise.all([
      vendorVendorId(row.vendor_id),
      vendorCapabilityVendorId(row.vendor_id),
    ])
    vendorDetail.value = v
    capDetail.value = c
  } catch (e) {
    message.error((e as Error).message || "加载详情失败")
  } finally {
    detailLoading.value = false
  }
}

async function audit(row: VendorAuditItem, action: "pass" | "reject"): Promise<void> {
  try {
    const res = await adminVendorsVendorIdAudit(row.vendor_id, {
      action,
      comment: action === "reject" ? "资料不完整" : undefined,
    })
    message.success(`已${action === "pass" ? "通过" : "驳回"}：${res.audit_status}`)
    await load()
  } catch (e) {
    message.error((e as Error).message || "审核失败")
  }
}

const columns: DataTableColumns<VendorAuditItem> = [
  { title: "厂商ID", key: "vendor_id", width: 190 },
  { title: "企业名称", key: "company_name" },
  { title: "所在地", key: "location" },
  { title: "主营行业", key: "main_industry" },
  {
    title: "审核状态",
    key: "audit_status",
    width: 100,
    render: (row) => {
      const meta = AUDIT_META[row.audit_status]
      return h(NTag, { size: "small", type: meta.tagType, bordered: false }, { default: () => meta.label })
    },
  },
  { title: "提交时间", key: "created_at", width: 180 },
  {
    title: "操作",
    key: "actions",
    width: 210,
    render: (row) =>
      h("div", { style: "display:flex;gap:8px" }, [
        h(NButton, { size: "small", onClick: () => void openDetail(row) }, { default: () => "查看" }),
        row.audit_status === "pending"
          ? h(
              NButton,
              { size: "small", type: "primary", onClick: () => void audit(row, "pass") },
              { default: () => "通过" },
            )
          : null,
        row.audit_status === "pending"
          ? h(
              NPopconfirm,
              { onPositiveClick: () => void audit(row, "reject") },
              {
                trigger: () =>
                  h(NButton, { size: "small", type: "error", secondary: true }, { default: () => "驳回" }),
                default: () => "确定驳回该厂商？",
              },
            )
          : null,
      ]),
  },
]

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="vendors-page">
    <div class="vendors-page__crumb">管理员后台 / 厂商产品</div>
    <div class="vendors-page__bar">
      <NInput v-model:value="keyword" placeholder="搜索企业名称" clearable style="width: 240px" />
    </div>
    <NDataTable
      :columns="columns"
      :data="filtered"
      :loading="loading"
      :bordered="false"
      :row-key="(r) => r.vendor_id"
    />

    <NDrawer
      v-model:show="drawerOpen"
      placement="right"
      width="640px"
      :title="`厂商详情 ${currentVendor?.company_name ?? ''}`"
    >
      <NSpin :show="detailLoading">
        <NTabs v-if="vendorDetail || capDetail" type="line">
          <NTabPane name="basic" tab="基本信息">
            <div v-if="vendorDetail" class="vendors-page__kv">
              <div><span>企业名称</span><b>{{ vendorDetail.company_name }}</b></div>
              <div><span>所在地</span><b>{{ vendorDetail.location ?? "—" }}</b></div>
              <div><span>主营行业</span><b>{{ vendorDetail.main_industry ?? "—" }}</b></div>
              <div><span>信用代码</span><b>{{ vendorDetail.credit_code ?? "—" }}</b></div>
              <div><span>审核状态</span><b>{{ AUDIT_META[(vendorDetail.audit_status ?? 'pending') as keyof typeof AUDIT_META].label }}</b></div>
            </div>
          </NTabPane>
          <NTabPane name="cap" tab="AI 能力档案">
            <div v-if="capDetail" class="vendors-page__tags">
              <div v-for="(v, k) in capDetail.structured_tags" :key="k" class="vendors-page__tag">
                <span class="k">{{ TAG_LABEL[k] ?? k }}</span>
                <span class="v">{{ display(v) }}</span>
              </div>
              <div v-if="capDetail.summary_text" class="vendors-page__summary">
                {{ capDetail.summary_text }}
              </div>
            </div>
          </NTabPane>
          <NTabPane name="raw" tab="原始资料">
            <div v-if="capDetail">
              <h4>文本片段</h4>
              <p class="vendors-page__raw">{{ capDetail.raw_text ?? "—" }}</p>
              <h4>文档（点击预览）</h4>
              <ul v-if="capDetail.doc_urls?.length" class="vendors-page__docs">
                <li
                  v-for="d in capDetail.doc_urls"
                  :key="d"
                  class="vendors-page__doc"
                  @click="openDocPreview(d)"
                >
                  📄 {{ d }}
                </li>
              </ul>
            </div>
          </NTabPane>
        </NTabs>
      </NSpin>
    </NDrawer>

    <NModal v-model:show="previewOpen" preset="card" title="文档预览（定位高亮）" style="width: 640px">
      <template v-if="preview">
        <div class="vendors-page__preview-meta">
          {{ preview.doc_name }} · 第 {{ preview.page }} 页
        </div>
        <p class="vendors-page__preview-content">{{ preview.content }}</p>
        <mark class="vendors-page__preview-hl">{{ preview.highlight }}</mark>
      </template>
    </NModal>
  </div>
</template>

<style scoped>
.vendors-page__crumb {
  margin-bottom: var(--space-16);
  font-size: var(--font-size-13);
  color: var(--color-text-secondary);
}
.vendors-page__bar {
  margin-bottom: var(--space-16);
}
.vendors-page__kv {
  display: flex;
  flex-direction: column;
  gap: var(--space-12);
}
.vendors-page__kv div {
  display: flex;
  justify-content: space-between;
  gap: var(--space-16);
}
.vendors-page__kv span {
  color: var(--color-text-secondary);
}
.vendors-page__tags {
  display: flex;
  flex-direction: column;
  gap: var(--space-8);
}
.vendors-page__tag {
  display: flex;
  justify-content: space-between;
  gap: var(--space-16);
  padding: var(--space-8) var(--space-12);
  background: var(--color-bg);
  border-radius: var(--radius-8);
}
.vendors-page__tag .k {
  color: var(--color-text-secondary);
}
.vendors-page__summary {
  margin-top: var(--space-12);
  padding: var(--space-12);
  background: var(--color-primary-bg);
  border-left: 3px solid var(--color-primary);
  border-radius: var(--radius-8);
  line-height: var(--line-height-loose);
}
.vendors-page__raw {
  line-height: var(--line-height-loose);
}
.vendors-page__docs {
  padding-left: var(--space-16);
}
.vendors-page__doc {
  cursor: pointer;
  color: var(--color-primary);
  margin-bottom: var(--space-4);
}
.vendors-page__doc:hover {
  text-decoration: underline;
}
.vendors-page__preview-meta {
  font-size: var(--font-size-13);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-8);
}
.vendors-page__preview-content {
  line-height: var(--line-height-loose);
}
.vendors-page__preview-hl {
  background: var(--color-warning-bg);
  padding: 0 4px;
  border-radius: var(--radius-4);
}
</style>
