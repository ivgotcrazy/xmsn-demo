<script setup lang="ts">
/**
 * 02B 匹配结果弹窗（并入 02A）：点击匹配记录卡片触发，按 request_id 拉取匹配结果。
 * 复用 MatchResultItem / MatchDetailPanel / 文档预览（原 02B 页内容迁入）。
 */
import { ref, watch } from "vue"
import { NModal, NSpin, useMessage } from "naive-ui"

import {
  documentsDocIdPreview,
  matchCompute,
  matchDetailMatchId,
  pollUntil,
  type DocumentPreviewResponse,
  type MatchDetailResponse,
  type MatchItem,
} from "@xmsn/api"

import MatchDetailPanel from "@/components/business/MatchDetailPanel.vue"
import MatchResultItem from "@/components/business/MatchResultItem.vue"

const props = defineProps<{ show: boolean; requestId: string }>()
const emit = defineEmits<{ (e: "update:show", v: boolean): void }>()
const message = useMessage()

const items = ref<MatchItem[]>([])
const total = ref(0)
const selectedId = ref("")
const detail = ref<MatchDetailResponse | null>(null)
const selectedItem = ref<MatchItem | null>(null)
const detailLoading = ref(false)
const computing = ref(false)

const previewOpen = ref(false)
const previewLoading = ref(false)
const preview = ref<DocumentPreviewResponse | null>(null)

async function load(): Promise<void> {
  computing.value = true
  items.value = []
  total.value = 0
  detail.value = null
  try {
    const res = await matchCompute({ request_id: props.requestId })
    items.value = res.match_results
    total.value = res.total_matches
    if (items.value.length) {
      await openDetail(items.value[0].match_id)
    }
  } catch {
    message.error("匹配计算失败")
  } finally {
    computing.value = false
  }
}

async function openDetail(matchId: string): Promise<void> {
  selectedId.value = matchId
  selectedItem.value = items.value.find((it) => it.match_id === matchId) ?? null
  detailLoading.value = true
  detail.value = null
  try {
    detail.value = await pollUntil(
      () => matchDetailMatchId(matchId),
      (d) => d.explanation_status === "ready",
      { intervalMs: 1000, timeoutMs: 30_000 },
    )
  } catch {
    message.error("加载匹配解释失败")
  } finally {
    detailLoading.value = false
  }
}

async function openPreview(): Promise<void> {
  previewOpen.value = true
  previewLoading.value = true
  try {
    preview.value = await documentsDocIdPreview("doc-001", 3)
  } catch {
    preview.value = null
  } finally {
    previewLoading.value = false
  }
}

function onClose(v: boolean): void {
  emit("update:show", v)
}

watch(
  () => props.show,
  (v) => {
    if (v) void load()
  },
)
</script>

<template>
  <NModal
    :show="show"
    preset="card"
    title="匹配结果"
    style="width: 720px"
    @update:show="onClose"
  >
    <div class="match-modal">
      <div v-if="computing" class="match-modal__loading"><NSpin>匹配计算中…</NSpin></div>
      <template v-else>
        <div class="match-modal__sub">为您找到 {{ total }} 家匹配的工厂</div>
        <div class="match-modal__list">
          <div v-for="it in items" :key="it.match_id" class="match-modal__item">
            <MatchResultItem
              :item="it"
              :active="it.match_id === selectedId"
              @open="openDetail(it.match_id)"
            />
            <MatchDetailPanel
              v-if="it.match_id === selectedId"
              :detail="detail"
              :item="selectedItem"
              :loading="detailLoading"
              @preview="openPreview"
            />
          </div>
          <div v-if="!items.length" class="match-modal__empty">暂无精确匹配的工厂</div>
        </div>
      </template>
    </div>

    <NModal v-model:show="previewOpen" preset="card" title="原文预览（定位高亮）" style="width: 640px">
      <NSpin :show="previewLoading">
        <template v-if="preview">
          <div class="preview__meta">{{ preview.doc_name }} · 第 {{ preview.page }} 页</div>
          <p class="preview__content">{{ preview.content }}</p>
          <mark class="preview__highlight">{{ preview.highlight }}</mark>
        </template>
      </NSpin>
    </NModal>
  </NModal>
</template>

<style scoped>
.match-modal__loading,
.match-modal__empty {
  padding: var(--space-32);
  text-align: center;
  color: var(--color-text-secondary);
}
.match-modal__sub {
  margin-bottom: var(--space-12);
  color: var(--color-text-secondary);
  font-size: var(--font-size-13);
}
.match-modal__list {
  display: flex;
  flex-direction: column;
  gap: var(--space-12);
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
