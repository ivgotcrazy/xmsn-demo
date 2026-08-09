<script setup lang="ts">
/**
 * 厂商能力档案（只读，三栏）：左"原始输入" / 中"AI 提取的结构化标签" / 右"一句话能力摘要"。
 * 共享组件：厂商端 01D / 买家端 02B 厂商能力页复用；原始文档可点击全屏预览。
 */
import { ref } from "vue"
import { NButton, NModal, NSpin } from "naive-ui"

import { documentsDocIdPreview, type CapabilityOut, type DocumentPreviewResponse } from "@xmsn/api"

const props = defineProps<{ capability: CapabilityOut | null }>()

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

// 原始文档 → 全屏预览
const previewOpen = ref(false)
const previewLoading = ref(false)
const preview = ref<DocumentPreviewResponse | null>(null)
const previewDocName = ref("")

async function openDoc(docName?: string, docId?: string): Promise<void> {
  previewDocName.value = docName ?? "原始文档"
  previewOpen.value = true
  previewLoading.value = true
  preview.value = null
  try {
    preview.value = await documentsDocIdPreview(docId ?? "doc-001", 1)
  } catch {
    preview.value = null
  } finally {
    previewLoading.value = false
  }
}
</script>

<template>
  <div v-if="capability" class="capability">
    <div class="capability__cols">
      <!-- 左栏：原始输入 -->
      <section class="capability__col">
        <h3>原始输入</h3>
        <div class="capability__source">
          <div class="capability__source-title">表单摘要</div>
          <div class="capability__source-text">见中栏结构化标签（来源：表单）</div>
          <div v-if="capability.raw_text" class="capability__source-title">文本片段</div>
          <p v-if="capability.raw_text" class="capability__source-text">{{ capability.raw_text }}</p>
          <div v-if="capability.doc_urls?.length" class="capability__source-title">文档</div>
          <ul v-if="capability.doc_urls?.length" class="capability__source-list">
            <li v-for="d in capability.doc_urls" :key="d">
              <NButton text size="small" class="doc" @click="openDoc(d)">📄 {{ d }}</NButton>
            </li>
          </ul>
        </div>
      </section>

      <!-- 中栏：AI 提取的结构化标签（只读） -->
      <section class="capability__col">
        <h3>AI 提取的结构化标签</h3>
        <div class="capability__tags">
          <div
            v-for="(v, k) in capability.structured_tags"
            :key="k"
            class="capability__tag"
            title="来源：表单 / 文本 / 文档"
          >
            <span class="capability__k">{{ TAG_LABEL[k as string] ?? k }}</span>
            <span class="capability__v">{{ display(v) }}</span>
          </div>
        </div>
      </section>

      <!-- 右栏：一句话能力摘要 -->
      <section class="capability__col">
        <h3>一句话能力摘要</h3>
        <p class="capability__summary">{{ capability.summary_text }}</p>
      </section>
    </div>

    <!-- 全屏文档预览 -->
    <NModal
      v-model:show="previewOpen"
      preset="card"
      :title="previewDocName"
      style="width: 94vw; max-width: 1400px; height: 92vh"
    >
      <NSpin :show="previewLoading">
        <template v-if="preview">
          <div class="capability__preview-meta">{{ preview.doc_name }} · 第 {{ preview.page }} 页</div>
          <p class="capability__preview-content">{{ preview.content }}</p>
          <mark class="capability__preview-highlight">{{ preview.highlight }}</mark>
        </template>
      </NSpin>
    </NModal>
  </div>
</template>

<style scoped>
.capability__cols {
  display: grid;
  grid-template-columns: 2fr 3fr 2fr;
  gap: var(--space-16);
  align-items: start;
}
.capability__col {
  background: var(--color-bg-panel);
  border: var(--border-width-1) solid var(--color-border-subtle);
  border-radius: var(--radius-12);
  padding: var(--space-16);
}
.capability__col h3 {
  margin: 0 0 var(--space-12);
  font-size: var(--font-size-15);
  font-weight: var(--font-weight-600);
}
.capability__source-title {
  margin-top: var(--space-12);
  font-size: var(--font-size-13);
  color: var(--color-text-secondary);
}
.capability__source-text {
  margin: var(--space-4) 0 0;
  font-size: var(--font-size-13);
  line-height: var(--line-height-normal);
  word-break: break-all;
}
.capability__source-list {
  margin: var(--space-4) 0 0;
  padding-left: var(--space-16);
  font-size: var(--font-size-13);
}
.capability__source-list .doc {
  color: var(--color-primary);
}
.capability__tags {
  display: flex;
  flex-direction: column;
  gap: var(--space-8);
}
.capability__tag {
  display: flex;
  justify-content: space-between;
  gap: var(--space-16);
  padding: var(--space-8) var(--space-12);
  background: var(--color-bg);
  border-radius: var(--radius-8);
}
.capability__k {
  color: var(--color-text-secondary);
}
.capability__v {
  font-weight: var(--font-weight-500);
  text-align: right;
  word-break: break-all;
}
.capability__summary {
  margin: 0;
  line-height: var(--line-height-loose);
  color: var(--color-text);
}
.capability__preview {
  max-width: 960px;
  margin: 0 auto;
  padding: var(--space-24);
}
.capability__preview-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-16);
}
.capability__preview-head h3 {
  margin: 0;
  font-size: var(--font-size-20);
}
.capability__preview-meta {
  font-size: var(--font-size-13);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-8);
}
.capability__preview-content {
  line-height: var(--line-height-loose);
}
.capability__preview-highlight {
  background: var(--color-warning-bg);
  padding: 0 4px;
  border-radius: var(--radius-4);
}
</style>
