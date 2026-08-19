<script setup lang="ts">
/**
 * 02B 匹配结果页（独立页·三栏）：左需求档案(280px) / 中厂商列表(380px) / 右匹配详情(弹性)。
 * 从 02A 匹配记录卡片进入；点返回回会话页；查看厂商能力 → /customer/vendor/:vendorId。
 */
import { computed, onMounted, ref } from "vue"
import { useRoute, useRouter } from "vue-router"
import { NButton, NSpin, useMessage } from "naive-ui"

import {
  matchCompute,
  matchDetailMatchId,
  pollUntil,
  type DemandPoint,
  type MatchDetailResponse,
  type MatchItem,
  type MatchRun,
} from "@xmsn/api"

import DemandProfileCard from "@/components/business/DemandProfileCard.vue"
import MatchDetailPanel from "@/components/business/MatchDetailPanel.vue"
import MatchResultItem from "@/components/business/MatchResultItem.vue"

const route = useRoute()
const router = useRouter()
const message = useMessage()

const items = ref<MatchItem[]>([])
const total = ref(0)
const run = ref<MatchRun | null>(null)
const demandPoints = ref<DemandPoint[]>([])
const selectedId = ref("")
const selectedItem = ref<MatchItem | null>(null)
const detail = ref<MatchDetailResponse | null>(null)
const detailLoading = ref(false)
const computing = ref(true)

const productType = computed(() => {
  const p = demandPoints.value.find((d) => d.key === "product_type")
  return p ? String(Array.isArray(p.value) ? p.value.join("/") : p.value) : ""
})

/** 匹配实体元信息行（物化字段，无需实时统计）：共 N 家 · 最佳 X% · 耗时 Y。 */
const runMeta = computed(() => {
  if (!run.value) return ""
  const parts = [`共 ${run.value.total_vendors ?? 0} 家`]
  if (run.value.best_score != null) parts.push(`最佳 ${run.value.best_score}%`)
  if (run.value.computation_time_ms) parts.push(`耗时 ${(run.value.computation_time_ms / 1000).toFixed(2)}s`)
  return parts.join(" · ")
})

async function load(): Promise<void> {
  computing.value = true
  try {
    const requestId = (route.params.requestId as string) || "req-001"
    const res = await matchCompute({ request_id: requestId })
    run.value = res.run ?? null
    items.value = res.match_results ?? []
    total.value = run.value?.total_vendors ?? items.value.length
    demandPoints.value = res.demand_points ?? []
    if (items.value.length) {
      await select(items.value[0].match_id)
    }
  } catch {
    message.error("匹配计算失败")
  } finally {
    computing.value = false
  }
}

async function select(matchId: string): Promise<void> {
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

/** 查看厂商能力 → 跳转客户端厂商能力页（返回回匹配结果页）。 */
function viewVendor(): void {
  const vendorId = selectedItem.value?.vendor_id ?? detail.value?.vendor_id
  if (!vendorId) {
    message.error("厂商信息缺失")
    return
  }
  void router.push(`/customer/vendor/${vendorId}`)
}

/** 返回 → 会话页。 */
function goBack(): void {
  void router.push("/customer/chat")
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="matches-page">
    <header class="matches-page__head">
      <NButton text size="small" @click="goBack()">← 返回</NButton>
      <h2>匹配结果<template v-if="productType"> · {{ productType }}</template></h2>
      <span v-if="runMeta" class="matches-page__meta">{{ runMeta }}</span>
    </header>

    <div v-if="computing" class="matches-page__loading"><NSpin>匹配计算中…</NSpin></div>
    <div v-else class="matches-page__layout">
      <!-- 左：需求档案（固定 280px） -->
      <aside class="matches-page__demand">
        <h3>需求档案</h3>
        <DemandProfileCard :points="demandPoints" />
      </aside>

      <!-- 中：工厂列表（固定 380px） -->
      <div class="matches-page__list">
        <div class="matches-page__list-head">
          <h3>厂商列表</h3>
          <span class="matches-page__list-count">共 {{ total }} 家</span>
        </div>
        <div class="matches-page__items">
          <div v-for="(it, i) in items" :key="it.match_id" class="matches-page__item">
            <MatchResultItem
              :item="it"
              :active="it.match_id === selectedId"
              :rank="i + 1"
              @open="select(it.match_id)"
            />
          </div>
          <div v-if="!items.length && run?.status === 'empty'" class="matches-page__empty">
            本次匹配已执行，但未找到合适的工厂
          </div>
          <div v-if="!items.length && run?.status !== 'empty'" class="matches-page__empty">
            暂无匹配结果
          </div>
        </div>
      </div>

      <!-- 右：匹配详情（弹性，min-width 480px） -->
      <div class="matches-page__detail">
        <MatchDetailPanel
          :detail="detail"
          :item="selectedItem"
          :loading="detailLoading"
          @view-vendor="viewVendor"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.matches-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 56px - var(--space-12) - var(--space-12));
  gap: var(--space-12);
}
.matches-page__head {
  display: flex;
  align-items: center;
  gap: var(--space-12);
  flex: none;
}
.matches-page__head h2 {
  margin: 0;
  font-size: var(--font-size-18);
}
.matches-page__meta {
  margin-left: var(--space-8);
  font-size: 13px;
  color: var(--color-text-secondary);
}
.matches-page__loading,
.matches-page__empty {
  padding: var(--space-32);
  text-align: center;
  color: var(--color-text-secondary);
}
.matches-page__layout {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: var(--space-12);
}
/* 左：需求档案（固定 280px） */
.matches-page__demand {
  width: 280px;
  flex: none;
  min-height: 0;
  overflow-y: auto;
  background: var(--color-bg-panel);
  border: var(--border-width-1) solid var(--color-border-subtle);
  border-radius: var(--radius-12);
  padding: var(--space-12);
}
.matches-page__demand h3 {
  margin: 0 0 var(--space-12);
  font-size: var(--font-size-15);
  font-weight: var(--font-weight-600);
}
/* 中：工厂列表（固定 380px，card） */
.matches-page__list {
  width: 380px;
  flex: none;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-12);
  background: var(--color-bg-panel);
  border: var(--border-width-1) solid var(--color-border-subtle);
  border-radius: var(--radius-12);
  padding: var(--space-12);
}
.matches-page__list-head {
  flex: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.matches-page__list-head h3 {
  margin: 0;
  font-size: var(--font-size-15);
  font-weight: var(--font-weight-600);
}
.matches-page__list-count {
  font-size: var(--font-size-13);
  color: var(--color-text-secondary);
}
.matches-page__items {
  display: flex;
  flex-direction: column;
  gap: var(--space-12);
}
/* 右：匹配详情（弹性，min-width 480px，card） */
.matches-page__detail {
  flex: 1;
  min-width: 480px;
  min-height: 0;
  overflow-y: auto;
  background: var(--color-bg-panel);
  border: var(--border-width-1) solid var(--color-border-subtle);
  border-radius: var(--radius-12);
  padding: var(--space-12);
}
</style>
