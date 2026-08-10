<script setup lang="ts">
/**
 * 买家端厂商能力页（02B 独立页 / COMP-029）：单页三块紧凑——厂商基本信息 / 厂商能力档案 / 厂商能力文档。
 * 从匹配结果页「查看厂商能力」进入；返回回匹配结果页。
 */
import { onMounted, ref } from "vue"
import { useRoute, useRouter } from "vue-router"
import { NButton, NModal, NSpin, NTag, useMessage } from "naive-ui"

import {
  documentsDocIdPreview,
  vendorCapabilityVendorId,
  vendorVendorId,
  type CapabilityOut,
  type DocumentPreviewResponse,
  type VendorOut,
} from "@xmsn/api"

const route = useRoute()
const router = useRouter()
const message = useMessage()

const vendor = ref<VendorOut | null>(null)
const cap = ref<CapabilityOut | null>(null)
const loading = ref(true)

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

// 能力文档 → 大尺寸预览
const previewOpen = ref(false)
const previewLoading = ref(false)
const preview = ref<DocumentPreviewResponse | null>(null)
const previewDocName = ref("")

async function openDoc(docName?: string): Promise<void> {
  previewDocName.value = docName ?? "原始文档"
  previewOpen.value = true
  previewLoading.value = true
  preview.value = null
  try {
    preview.value = await documentsDocIdPreview("doc-001", 1)
  } catch {
    preview.value = null
  } finally {
    previewLoading.value = false
  }
}

onMounted(async () => {
  try {
    const vendorId = (route.params.vendorId as string) || "v-001"
    const [v, c] = await Promise.all([vendorVendorId(vendorId), vendorCapabilityVendorId(vendorId)])
    vendor.value = v
    cap.value = c
  } catch {
    message.error("加载厂商能力失败")
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="vendor-page">
    <header class="vendor-page__head">
      <NButton text size="small" @click="router.back()">← 返回</NButton>
      <h2>厂商能力</h2>
    </header>

    <div v-if="loading" class="vendor-page__loading">加载中…</div>
    <div v-else-if="vendor" class="vendor-page__body">
      <!-- ① 厂商基本信息 -->
      <section class="vendor-block">
        <h3>厂商基本信息</h3>
        <div class="vendor-block__row">
          <span class="vendor-block__name">{{ vendor.company_name }}</span>
          <NTag
            :type="vendor.audit_status === 'passed' ? 'success' : 'warning'"
            :bordered="false"
          >
            {{ vendor.audit_status === "passed" ? "已通过" : "审核中" }}
          </NTag>
        </div>
        <div class="vendor-block__meta">
          {{ vendor.location ?? "—" }}<template v-if="vendor.main_industry"> · {{ vendor.main_industry }}</template>
        </div>
      </section>

      <!-- ② 厂商能力档案 -->
      <section v-if="cap" class="vendor-block">
        <h3>厂商能力档案</h3>
        <div class="vendor-block__tags">
          <div v-for="(v, k) in cap.structured_tags" :key="k" class="vendor-block__tag">
            <span class="vendor-block__k">{{ TAG_LABEL[k as string] ?? k }}</span>
            <span class="vendor-block__v">{{ display(v) }}</span>
          </div>
        </div>
        <p v-if="cap.summary_text" class="vendor-block__summary">{{ cap.summary_text }}</p>
      </section>

      <!-- ③ 厂商能力文档 -->
      <section v-if="cap" class="vendor-block">
        <h3>厂商能力文档</h3>
        <div v-if="cap.raw_text" class="vendor-block__raw">
          <p>{{ cap.raw_text }}</p>
        </div>
        <div v-if="cap.doc_urls?.length" class="vendor-block__docs">
          <NButton v-for="d in cap.doc_urls" :key="d" text class="doc" @click="openDoc(d)">
            📄 {{ d }}
          </NButton>
        </div>
      </section>
    </div>

    <!-- 大尺寸文档预览 -->
    <NModal
      v-model:show="previewOpen"
      preset="card"
      :title="previewDocName"
      style="width: 94vw; max-width: 1400px; height: 92vh"
    >
      <NSpin :show="previewLoading">
        <template v-if="preview">
          <div class="preview__meta">{{ preview.doc_name }} · 第 {{ preview.page }} 页</div>
          <p class="preview__content">{{ preview.content }}</p>
          <mark class="preview__highlight">{{ preview.highlight }}</mark>
        </template>
      </NSpin>
    </NModal>
  </div>
</template>

<style scoped>
.vendor-page {
  max-width: 960px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-16);
}
.vendor-page__head {
  display: flex;
  align-items: center;
  gap: var(--space-12);
}
.vendor-page__head h2 {
  margin: 0;
  font-size: var(--font-size-20);
}
.vendor-page__loading {
  padding: var(--space-32);
  color: var(--color-text-secondary);
}
.vendor-page__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-16);
}
.vendor-block {
  background: var(--color-bg-panel);
  border: var(--border-width-1) solid var(--color-border-subtle);
  border-radius: var(--radius-12);
  padding: var(--space-16);
}
.vendor-block h3 {
  margin: 0 0 var(--space-12);
  font-size: var(--font-size-15);
  font-weight: var(--font-weight-600);
}
.vendor-block__row {
  display: flex;
  align-items: center;
  gap: var(--space-12);
}
.vendor-block__name {
  font-size: var(--font-size-18);
  font-weight: var(--font-weight-600);
}
.vendor-block__meta {
  margin-top: var(--space-4);
  font-size: var(--font-size-13);
  color: var(--color-text-secondary);
}
.vendor-block__tags {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-8);
}
.vendor-block__tag {
  display: flex;
  justify-content: space-between;
  gap: var(--space-16);
  padding: var(--space-8) var(--space-12);
  background: var(--color-bg);
  border-radius: var(--radius-8);
  font-size: var(--font-size-13);
}
.vendor-block__k {
  color: var(--color-text-secondary);
  white-space: nowrap;
}
.vendor-block__v {
  font-weight: var(--font-weight-500);
  text-align: right;
  word-break: break-all;
}
.vendor-block__summary {
  margin: var(--space-12) 0 0;
  line-height: var(--line-height-loose);
  font-size: var(--font-size-14);
}
.vendor-block__raw p {
  margin: 0;
  font-size: var(--font-size-13);
  line-height: var(--line-height-loose);
  word-break: break-all;
}
.vendor-block__docs {
  margin-top: var(--space-12);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  align-items: flex-start;
}
.vendor-block__docs .doc {
  color: var(--color-primary);
}
.preview__meta {
  font-size: var(--font-size-13);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-8);
}
.preview__content {
  line-height: var(--line-height-loose);
}
.preview__highlight {
  background: var(--color-warning-bg);
  padding: 0 4px;
  border-radius: var(--radius-4);
}
</style>
