<script setup lang="ts">
/**
 * 01D 厂商能力档案（只读）：档案内容严格对应「能力 Schema」（CAPABILITY_SCHEMA_FIELDS 遍历渲染）。
 * 顶部 = 综合评估（纯文字：完备度 X/N + 缺失项标红带建议 + 低置信度字段提示）；主体 = schema 驱动的能力字段列表
 * （硬能力缺失标红「未提取」+ 建议；软标签中性展示）；每个能力值带**独立置信度列** + source_map 溯源（文档·第N页，可预览）。
 * 文档列表展示在 01C 录入页（此处不重复）。
 */
import { computed, ref } from "vue"
import { NButton, NModal, NSpin, NTag } from "naive-ui"

import { documentsDocIdFile, type CapabilityOut } from "@xmsn/api"
import { CAPABILITY_SCHEMA_FIELDS } from "@xmsn/types"

const props = defineProps<{ capability: CapabilityOut | null }>()

const hardFields = computed(() => CAPABILITY_SCHEMA_FIELDS.filter((f) => f.hard))
const softFields = computed(() => CAPABILITY_SCHEMA_FIELDS.filter((f) => !f.hard))

function hasValue(v: unknown): boolean {
  if (v === null || v === undefined || v === "") return false
  if (Array.isArray(v)) return v.length > 0
  return true
}
function display(v: unknown): string {
  if (Array.isArray(v)) return v.join("、")
  return String(v ?? "")
}

// 各字段当前值（来自 structured_tags，key 与 schema 一一对应）
function fieldValue(key: string): unknown {
  return props.capability?.structured_tags?.[key]
}

// 缺失的硬能力（计入完备度，档案页标红 + 建议）
const missingHard = computed(() =>
  hardFields.value.filter((f) => !hasValue(fieldValue(f.key))),
)
const filledHardCount = computed(() => hardFields.value.length - missingHard.value.length)

/** 完备度：由实际数据计算（X/N 硬能力已提取），保证与缺失标红严格一致 */
const completeness = computed(() =>
  hardFields.value.length === 0 ? 0 : filledHardCount.value / hardFields.value.length,
)

// 每个字段的溯源+置信度（source_map: key → { doc_id, doc_name, page, chunk_text, confidence }）
interface SourceRef {
  doc_id?: string
  doc_name?: string
  page?: number
  chunk_text?: string
  /** 字段级解析置信度 0-1，<0.6 视为低置信度 */
  confidence?: number
}
function sourceOf(key: string): SourceRef | undefined {
  const s = props.capability?.source_map?.[key]
  return s && typeof s === "object" ? (s as SourceRef) : undefined
}
/** 字段级解析置信度（0-1）；未提取/无溯源字段返回 undefined */
function fieldConfidence(key: string): number | undefined {
  return sourceOf(key)?.confidence
}
/** 低置信度字段（已提取但 confidence < 0.6）：综合评估区提示补文档 */
const lowConfidenceFields = computed(() =>
  CAPABILITY_SCHEMA_FIELDS.filter((f) => {
    const c = fieldConfidence(f.key)
    return hasValue(fieldValue(f.key)) && c !== undefined && c < 0.6
  }),
)

// 原始文档 → 全屏预览（溯源点击：打开真实源文件，非文本提取）
const previewOpen = ref(false)
const previewLoading = ref(false)
const previewUrl = ref<string | null>(null)
const previewTitle = ref("")

function revokePreview(): void {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = null
  }
}

async function openDoc(docName?: string, docId?: string, page?: number): Promise<void> {
  previewTitle.value = `${docName ?? "原始文档"}${page ? ` · 引用第 ${page} 页` : ""}`
  previewOpen.value = true
  previewLoading.value = true
  revokePreview()
  try {
    const blob = await documentsDocIdFile(docId ?? "")
    previewUrl.value = URL.createObjectURL(blob)
  } catch {
    previewUrl.value = null
  } finally {
    previewLoading.value = false
  }
}
</script>

<template>
  <div v-if="capability" class="capability">
    <!-- 顶部：一句话能力摘要（概要条） -->
    <section v-if="capability.summary_text" class="capability__summary">
      <span class="capability__summary-label">一句话能力摘要</span>
      <p class="capability__summary-text">{{ capability.summary_text }}</p>
    </section>

    <!-- 综合评估（纯文字）：完备度 + 缺失项 + 低置信度字段 -->
    <section class="capability__assess">
      <h3>综合评估</h3>

      <div class="capability__assess-text">
        <p class="capability__assess-line">
          能力完备度：已提取 <b>{{ filledHardCount }}</b> 项硬能力（共 {{ hardFields.length }} 项）
          <template v-if="missingHard.length">，{{ missingHard.length }} 项缺失。</template>
          <template v-else>，各字段均已提取 🎉</template>
        </p>

        <!-- 缺失项（硬能力，标红 + 建议） -->
        <div v-if="missingHard.length" class="capability__missing">
          <span class="capability__missing-label">缺失项</span>
          <div class="capability__missing-tags">
            <NTag
              v-for="f in missingHard"
              :key="f.key"
              size="small"
              type="error"
              :bordered="false"
            >{{ f.label }}</NTag>
          </div>
          <p v-if="missingHard.length === 1" class="capability__missing-tip">
            {{ missingHard[0].label }}：{{ missingHard[0].suggest ?? "建议补充对应文档" }}
          </p>
          <ul v-else class="capability__missing-tips">
            <li v-for="f in missingHard" :key="f.key">
              {{ f.label }}：{{ f.suggest ?? "建议补充对应文档" }}
            </li>
          </ul>
        </div>

        <!-- 低置信度字段（黄色提示补文档） -->
        <div v-if="lowConfidenceFields.length" class="capability__low">
          <p class="capability__low-tip">
            以下字段解析把握不足（置信度 &lt; 60%），建议补充更清晰的文档后重新解析：
          </p>
          <ul class="capability__low-list">
            <li v-for="f in lowConfidenceFields" :key="f.key">
              {{ f.label }}（{{ Math.round((fieldConfidence(f.key) ?? 0) * 100) }}%）
            </li>
          </ul>
        </div>
        <p v-else class="capability__assess-tip is-ok">各字段解析把握良好 ✅</p>
      </div>
    </section>

    <!-- 主体：schema 驱动的能力字段列表（硬能力 → 软标签） -->
    <section class="capability__fields">
      <h3>能力档案</h3>

      <div class="capability__field-group">
        <div class="capability__group-title">硬能力（匹配主锚）</div>
        <div
          v-for="f in hardFields"
          :key="f.key"
          class="capability__field"
          :class="{ 'is-missing': !hasValue(fieldValue(f.key)) }"
        >
          <span class="capability__field-status">
            <template v-if="hasValue(fieldValue(f.key))">✓</template>
            <template v-else>✗</template>
          </span>
          <span class="capability__field-label">{{ f.label }}</span>
          <span class="capability__field-value">
            <template v-if="hasValue(fieldValue(f.key))">{{ display(fieldValue(f.key)) }}</template>
            <template v-else>未提取</template>
          </span>
          <!-- 字段级解析置信度（独立列） -->
          <span
            class="capability__field-conf"
            :class="{ 'is-low': (fieldConfidence(f.key) ?? 1) < 0.6 }"
          >
            <template v-if="hasValue(fieldValue(f.key)) && fieldConfidence(f.key) !== undefined">
              {{ Math.round((fieldConfidence(f.key) ?? 0) * 100) }}%
            </template>
            <template v-else>—</template>
          </span>
          <span v-if="sourceOf(f.key)" class="capability__field-source">
            <NButton
              text
              size="small"
              type="primary"
              @click="openDoc(sourceOf(f.key)!.doc_name, sourceOf(f.key)!.doc_id, sourceOf(f.key)!.page)"
            >
              {{ sourceOf(f.key)!.doc_name }} · 第 {{ sourceOf(f.key)!.page }} 页
            </NButton>
          </span>
          <span v-if="!hasValue(fieldValue(f.key))" class="capability__field-suggest">
            {{ f.suggest }}
          </span>
        </div>
      </div>

      <div class="capability__field-group">
        <div class="capability__group-title">软标签（语义召回）</div>
        <div
          v-for="f in softFields"
          :key="f.key"
          class="capability__field"
        >
          <span class="capability__field-status is-soft">
            <template v-if="hasValue(fieldValue(f.key))">✓</template>
            <template v-else>–</template>
          </span>
          <span class="capability__field-label">{{ f.label }}</span>
          <span class="capability__field-value">
            <template v-if="hasValue(fieldValue(f.key))">{{ display(fieldValue(f.key)) }}</template>
            <template v-else>未填写</template>
          </span>
          <!-- 字段级解析置信度（独立列） -->
          <span
            class="capability__field-conf"
            :class="{ 'is-low': (fieldConfidence(f.key) ?? 1) < 0.6 }"
          >
            <template v-if="hasValue(fieldValue(f.key)) && fieldConfidence(f.key) !== undefined">
              {{ Math.round((fieldConfidence(f.key) ?? 0) * 100) }}%
            </template>
            <template v-else>—</template>
          </span>
          <span v-if="sourceOf(f.key)" class="capability__field-source">
            <NButton
              text
              size="small"
              type="primary"
              @click="openDoc(sourceOf(f.key)!.doc_name, sourceOf(f.key)!.doc_id, sourceOf(f.key)!.page)"
            >
              {{ sourceOf(f.key)!.doc_name }} · 第 {{ sourceOf(f.key)!.page }} 页
            </NButton>
          </span>
        </div>
      </div>
    </section>

    <!-- 全屏源文件预览（iframe 内嵌真实 PDF，非文本提取） -->
    <NModal
      v-model:show="previewOpen"
      preset="card"
      :title="previewTitle"
      style="width: 94vw; max-width: 1400px; height: 92vh"
      @after-leave="revokePreview"
    >
      <NSpin :show="previewLoading">
        <iframe
          v-if="previewUrl"
          :src="previewUrl"
          class="capability__preview-frame"
          title="源文件预览"
        ></iframe>
      </NSpin>
    </NModal>
  </div>
</template>

<style scoped>
.capability__summary {
  display: flex;
  align-items: center;
  gap: var(--space-16);
  padding: var(--space-16);
  background: var(--color-primary-bg);
  border-left: 3px solid var(--color-primary);
  border-radius: var(--radius-8);
  margin-bottom: var(--space-16);
}
.capability__summary-label {
  flex: none;
  font-size: var(--font-size-13);
  font-weight: var(--font-weight-600);
  color: var(--color-primary-text);
  white-space: nowrap;
}
.capability__summary-text {
  margin: 0;
  font-size: var(--font-size-14);
  line-height: var(--line-height-loose);
  color: var(--color-text);
}

/* 综合评估 */
.capability__assess {
  background: var(--color-bg-panel);
  border: var(--border-width-1) solid var(--color-border-subtle);
  border-radius: var(--radius-12);
  padding: var(--space-16);
  margin-bottom: var(--space-16);
}
.capability__assess h3,
.capability__fields h3 {
  margin: 0 0 var(--space-12);
  font-size: var(--font-size-15);
  font-weight: var(--font-weight-600);
}
.capability__assess-text {
  display: flex;
  flex-direction: column;
  gap: var(--space-8);
}
.capability__assess-line {
  margin: 0;
  font-size: var(--font-size-13);
  color: var(--color-text);
  line-height: var(--line-height-normal);
}
.capability__assess-line b {
  color: var(--color-primary);
}
.capability__assess-tip {
  margin: 0;
  font-size: var(--font-size-12);
  color: var(--color-text-secondary);
  line-height: var(--line-height-normal);
}
.capability__assess-tip.is-ok {
  color: var(--color-success-text);
}
.capability__low {
  margin-top: var(--space-8);
  padding-top: var(--space-12);
  border-top: var(--border-width-1) dashed var(--color-border-strong);
}
.capability__low-tip {
  margin: 0;
  font-size: var(--font-size-13);
  color: var(--color-warning-text);
  line-height: var(--line-height-normal);
}
.capability__low-list {
  margin: var(--space-8) 0 0;
  padding-left: var(--space-16);
  font-size: var(--font-size-13);
  color: var(--color-warning-text);
  line-height: var(--line-height-normal);
}
.capability__missing {
  margin-top: var(--space-16);
  padding-top: var(--space-12);
  border-top: var(--border-width-1) dashed var(--color-border-strong);
}
.capability__missing-label {
  font-size: var(--font-size-13);
  font-weight: var(--font-weight-600);
  color: var(--color-error);
}
.capability__missing-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-8);
  margin-top: var(--space-8);
}
.capability__missing-tip,
.capability__missing-tips {
  margin: var(--space-8) 0 0;
  font-size: var(--font-size-12);
  color: var(--color-error-text);
  line-height: var(--line-height-normal);
}
.capability__missing-tips {
  padding-left: var(--space-16);
}

/* schema 驱动字段列表 */
.capability__fields {
  background: var(--color-bg-panel);
  border: var(--border-width-1) solid var(--color-border-subtle);
  border-radius: var(--radius-12);
  padding: var(--space-16);
  margin-bottom: var(--space-16);
}
.capability__field-group + .capability__field-group {
  margin-top: var(--space-16);
  border-top: var(--border-width-1) solid var(--color-border-subtle);
  padding-top: var(--space-12);
}
.capability__group-title {
  font-size: var(--font-size-12);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-8);
}
.capability__field {
  display: flex;
  align-items: center;
  gap: var(--space-12);
  padding: var(--space-8) 0;
  border-bottom: var(--border-width-1) solid var(--color-border-subtle);
}
.capability__field:last-child {
  border-bottom: none;
}
.capability__field.is-missing {
  background: var(--color-error-bg);
  border-radius: var(--radius-8);
  padding-left: var(--space-12);
  padding-right: var(--space-12);
}
.capability__field-status {
  flex: none;
  width: 18px;
  height: 18px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-12);
  color: #fff;
  background: var(--color-success);
}
.capability__field-status.is-soft {
  background: var(--color-border-strong);
  color: var(--color-text-secondary);
}
.capability__field.is-missing .capability__field-status {
  background: var(--color-error);
}
.capability__field-label {
  flex: none;
  width: 80px;
  font-size: var(--font-size-13);
  color: var(--color-text-secondary);
}
.capability__field-value {
  flex: 1;
  font-size: var(--font-size-13);
  font-weight: var(--font-weight-500);
  word-break: break-all;
}
.capability__field.is-missing .capability__field-value {
  color: var(--color-error-text);
}
.capability__field-conf {
  flex: none;
  width: 56px;
  text-align: right;
  font-size: var(--font-size-12);
  font-weight: var(--font-weight-500);
  color: var(--color-text-secondary);
}
.capability__field-conf.is-low {
  color: var(--color-warning);
  font-weight: var(--font-weight-600);
}
.capability__field-source {
  flex: none;
  font-size: var(--font-size-12);
}
.capability__field-suggest {
  flex: none;
  font-size: var(--font-size-12);
  color: var(--color-error-text);
}

.capability__preview-frame {
  width: 100%;
  height: calc(92vh - 130px);
  border: none;
  border-radius: var(--radius-8);
}
</style>
