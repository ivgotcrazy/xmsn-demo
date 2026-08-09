<script setup lang="ts">
/**
 * 02B 匹配结果（原型 02B）：标题栏 + "查看历史匹配" → "为您找到 N 家" → 列表就地展开详情。
 * 经 @xmsn/api 客户端调用（M1 契约 mock 拦截；M4 真实后端）。
 */
import { onMounted, ref } from "vue"
import { useRoute, useRouter } from "vue-router"
import { NButton, NModal, NSpin, useMessage } from "naive-ui"

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

const route = useRoute()
const router = useRouter()
const message = useMessage()

const items = ref<MatchItem[]>([])
const total = ref(0)
const selectedId = ref("")
const detail = ref<MatchDetailResponse | null>(null)
const selectedItem = ref<MatchItem | null>(null)
const detailLoading = ref(false)
const computing = ref(true)

const previewOpen = ref(false)
const previewLoading = ref(false)
const preview = ref<DocumentPreviewResponse | null>(null)

async function load(): Promise<void> {
  computing.value = true
  try {
    const requestId = (route.params.requestId as string) || "req-001"
    const res = await matchCompute({ request_id: requestId })
    items.value = res.match_results
    total.value = res.total_matches
    if (items.value.length) {
      selectedId.value = items.value[0].match_id
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

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="matches-page">
    <div class="matches-page__head">
      <h2>匹配结果</h2>
      <span class="matches-page__history" @click="router.push('/buyer/history')">查看历史匹配</span>
    </div>
    <div class="matches-page__sub">为您找到 {{ total }} 家匹配的工厂</div>

    <div v-if="computing" class="matches-page__loading"><NSpin>匹配计算中…</NSpin></div>
    <template v-else>
      <div class="matches-page__list">
        <div v-for="it in items" :key="it.match_id" class="matches-page__item">
          <MatchResultItem :item="it" :active="it.match_id === selectedId" @open="openDetail(it.match_id)" />
          <MatchDetailPanel
            v-if="it.match_id === selectedId"
            :detail="detail"
            :item="selectedItem"
            :loading="detailLoading"
            @preview="openPreview"
          />
        </div>
        <div v-if="!items.length" class="matches-page__empty">暂无精确匹配的工厂</div>
      </div>
      <div class="matches-page__actions">
        <NButton dashed @click="router.push('/buyer/chat')">修改需求</NButton>
      </div>
    </template>

    <NModal v-model:show="previewOpen" preset="card" title="原文预览（定位高亮）" style="width: 640px">
      <NSpin :show="previewLoading">
        <template v-if="preview">
          <div class="preview__meta">
            {{ preview.doc_name }} · 第 {{ preview.page }} 页
          </div>
          <p class="preview__content">{{ preview.content }}</p>
          <mark class="preview__highlight">{{ preview.highlight }}</mark>
        </template>
      </NSpin>
    </NModal>
  </div>
</template>

<style scoped>
.matches-page {
  max-width: 800px;
  margin: 0 auto;
}
.matches-page__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: var(--space-8);
}
.matches-page__head h2 {
  margin: 0;
  font-size: var(--font-size-20);
}
.matches-page__history {
  font-size: var(--font-size-13);
  color: var(--color-primary);
  cursor: pointer;
}
.matches-page__sub {
  margin-bottom: var(--space-16);
  color: var(--color-text-secondary);
  font-size: var(--font-size-13);
}
.matches-page__list {
  display: flex;
  flex-direction: column;
  gap: var(--space-12);
}
.matches-page__loading,
.matches-page__empty {
  padding: var(--space-32);
  text-align: center;
  color: var(--color-text-secondary);
}
.matches-page__actions {
  margin-top: var(--space-24);
  display: flex;
  justify-content: center;
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
