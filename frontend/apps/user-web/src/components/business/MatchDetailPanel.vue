<script setup lang="ts">
/**
 * 匹配详情面板（原型 02B / COMP-024）：Drawer 内——match_score + 四组判定（D10：missing 独立）
 * + match_reason/risk_warning（D4，风险提示随匹配理由后展示）+ 行内文档引用 + 查看厂商能力。
 */
import { computed, ref } from "vue"
import { NButton, NModal, NSpin, NTag } from "naive-ui"

import {
  documentsDocIdFile,
  type MatchDetailResponse,
  type MatchItem,
} from "@xmsn/types"

const props = defineProps<{
  detail: MatchDetailResponse | null
  item: MatchItem | null
  loading?: boolean
}>()

const emit = defineEmits<{
  viewVendor: []
}>()

const GROUP = [
  { key: "matched_params", title: "匹配项", type: "success" },
  { key: "partial_params", title: "部分匹配", type: "warning" },
  { key: "missing_params", title: "未声明项", type: "default" },
  { key: "unmatched_params", title: "不匹配项", type: "error" },
] as const

const semanticPct = computed(() => Math.round((props.item?.semantic_score ?? 0) * 100))
const hitText = computed(() => {
  const matched = props.detail?.matched_params?.length ?? 0
  const total =
    matched +
    (props.detail?.partial_params?.length ?? 0) +
    (props.detail?.missing_params?.length ?? 0) +
    (props.detail?.unmatched_params?.length ?? 0)
  return `参数命中 ${matched}/${total}`
})

// 行内文档引用 → 全屏预览（打开真实源文件，非文本提取）
const previewOpen = ref(false)
const previewLoading = ref(false)
const previewUrl = ref<string | null>(null)
const previewTitle = ref("厂商原始文档")

/** 页码格式：chunk 的 page 可能是范围串 "2~3" → 显示 "2-3"；单页 "2" → "2"。 */
function fmtPage(p?: string | number | null): string {
  if (p === undefined || p === null || p === "") return ""
  const s = String(p)
  return s.includes("~") ? s.replace("~", "-") : s
}

function revokePreview(): void {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = null
  }
}

async function openPreview(sourceDocId?: string | null, sourcePage?: string | number | null): Promise<void> {
  previewTitle.value = sourcePage ? `厂商原始文档 · 引用第 ${fmtPage(sourcePage)} 页` : "厂商原始文档"
  previewOpen.value = true
  previewLoading.value = true
  revokePreview()
  try {
    const blob = await documentsDocIdFile(sourceDocId ?? "")
    previewUrl.value = URL.createObjectURL(blob)
  } catch {
    previewUrl.value = null
  } finally {
    previewLoading.value = false
  }
}
</script>

<template>
  <div class="match-detail">
    <NSpin :show="loading">
      <template v-if="detail">
        <div class="match-detail__head">
          <h3>{{ detail.company_name }}</h3>
          <span class="match-detail__vendor" @click="emit('viewVendor')">厂商详情</span>
        </div>
        <div class="match-detail__subrow">
          匹配分 {{ item?.match_score ?? 0 }} · 语义相似度 {{ semanticPct }}% · {{ hitText }}
        </div>

        <section v-if="detail.match_reason" class="match-detail__comment">
          <h4>匹配理由</h4>
          <p>{{ detail.match_reason }}</p>
        </section>

        <section v-if="detail.risk_warning" class="match-detail__comment match-detail__risk">
          <h4>风险提示</h4>
          <p class="match-detail__risk-body">{{ detail.risk_warning }}</p>
        </section>

        <section v-for="g in GROUP" :key="g.key" class="match-detail__group">
          <h4>
            <NTag size="small" :type="g.type" :bordered="false">{{ g.title }}</NTag>
          </h4>
          <ul v-if="detail[g.key]?.length">
            <li v-for="(p, i) in detail[g.key]" :key="i">
              <span class="k">{{ p.label }}</span>
              <span class="v">{{ p.value }}</span>
              <!-- 行内文档引用（判定可溯源到厂商原始文档；删除冗余 verdict 标签） -->
              <NButton
                v-if="p.source_page !== undefined && p.source_page !== null"
                text
                size="tiny"
                class="cite"
                @click="openPreview(p.source_doc_id, p.source_page)"
              >
                📄 第 {{ fmtPage(p.source_page) }} 页
              </NButton>
            </li>
          </ul>
          <div v-else class="match-detail__empty">无</div>
        </section>
      </template>
      <template v-else>
        <div class="match-detail__empty">理由生成中…</div>
      </template>
    </NSpin>

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
          class="preview__frame"
          title="源文件预览"
        ></iframe>
      </NSpin>
    </NModal>
  </div>
</template>

<style scoped>
.match-detail {
  display: flex;
  flex-direction: column;
  gap: var(--space-12);
}
.match-detail__alert {
  padding: var(--space-8) var(--space-12);
  border-radius: var(--radius-8);
  font-size: var(--font-size-13);
  margin-bottom: var(--space-16);
}
.match-detail__alert--warn {
  background: var(--color-error-bg);
  color: var(--color-error-text);
}
.match-detail__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: var(--space-8);
}
.match-detail__head h3 {
  margin: 0;
  font-size: var(--font-size-18);
}
.match-detail__vendor {
  color: var(--color-primary);
  font-size: var(--font-size-13);
  cursor: pointer;
  white-space: nowrap;
}
.match-detail__vendor:hover {
  text-decoration: underline;
}
.match-detail__subrow {
  padding: var(--space-8) var(--space-12);
  background: var(--color-bg);
  border-radius: var(--radius-8);
  font-size: var(--font-size-13);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-16);
}
.match-detail__group {
  margin-bottom: var(--space-16);
}
.match-detail__comment {
  margin-bottom: var(--space-24);
}
/* 风险提示标题：无背景（普通标题样式）；风险正文用警示底色块。
   选择器需高于 .match-detail__comment p（其编译带 [data-v] 优先级 0,2,1），
   否则风险正文会被蓝色注释样式覆盖。 */
.match-detail__risk .match-detail__risk-body {
  /* 与匹配理由（.match-detail__comment p）一致：统一 12px，无 --space-10 令牌 */
  padding: var(--space-12);
  border-radius: var(--radius-8);
  border-left: 3px solid var(--color-error);
  background: var(--color-error-bg);
  color: var(--color-error-text);
}
.match-detail__group h4,
.match-detail__comment h4 {
  margin: 0 0 var(--space-8);
  font-size: var(--font-size-14);
  font-weight: var(--font-weight-600);
}
.match-detail__group ul {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: var(--space-8);
}
.match-detail__group li {
  display: flex;
  align-items: center;
  gap: var(--space-8);
  font-size: var(--font-size-13);
}
.match-detail__group .k {
  width: 90px;
  flex: none;
  color: var(--color-text-secondary);
}
.match-detail__group .v {
  flex: 1;
  word-break: break-all;
}
.match-detail__empty {
  color: var(--color-disabled);
  font-size: var(--font-size-13);
}
.match-detail__comment p {
  margin: 0;
  line-height: var(--line-height-loose);
  color: var(--color-text);
  background: var(--color-primary-bg);
  border-left: 3px solid var(--color-primary);
  padding: var(--space-12);
  border-radius: var(--radius-8);
}
.cite {
  color: var(--color-primary);
  white-space: nowrap;
}
.preview {
  max-width: 960px;
  margin: 0 auto;
  padding: var(--space-24);
}
.preview__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-16);
}
.preview__head h3 {
  margin: 0;
  font-size: var(--font-size-20);
}
.preview__frame {
  width: 100%;
  height: calc(92vh - 130px);
  border: none;
  border-radius: var(--radius-8);
}
</style>
