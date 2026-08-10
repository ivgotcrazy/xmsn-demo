<script setup lang="ts">
/**
 * 03B 数据概览（原型 4.1）：三统计卡片（图标+数值+较昨日变化，点击跳转）+
 * 下方三个近 30 日历史趋势折线图（用户/厂商/匹配，各占整行）+ 待处理事项，Demo 数据为静态展示。
 */
import { computed, onMounted, ref } from "vue"
import { useRouter } from "vue-router"
import { NSpin } from "naive-ui"

import { adminStats, type AdminStatsResponse } from "@xmsn/api"

const router = useRouter()
const stats = ref<AdminStatsResponse | null>(null)
const loading = ref(true)

// 卡片：图标(SVG 路径) + 主题色 + 变化趋势（Demo 静态）。需求档案与匹配一一对应，故不单独展示需求总数。
const cards = computed(() => {
  const s = stats.value
  return [
    {
      label: "用户总数",
      value: s?.total_users ?? 0,
      delta: "+12%",
      up: true,
      color: "#2563eb",
      bg: "#eff6ff",
      icon: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm0 2c-4 0-8 2-8 5v1h16v-1c0-3-4-5-8-5z',
      link: "",
    },
    {
      label: "厂商总数",
      value: s?.total_vendors ?? 0,
      delta: "+4%",
      up: true,
      color: "#d97706",
      bg: "#fffbeb",
      icon: 'M3 21h18M5 21V11l5 3V11l5 3V11l6 3v7',
      link: "/admin/vendors",
    },
    {
      label: "匹配次数",
      value: s?.total_matches ?? 0,
      delta: "+21%",
      up: true,
      color: "#dc2626",
      bg: "#fef2f2",
      icon: 'M5 12a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm14-6a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm0 12a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM7 9l10-3M7 15l10 3',
      link: "/admin/requests",
    },
  ]
})

// 历史趋势（近 30 日，Demo 静态折线）：确定性生成（正弦+增长+噪声），刷新不随机变化。
function genTrend(seed: number, base: number, growth: number): number[] {
  const pts: number[] = []
  for (let i = 0; i < 30; i++) {
    const wave = Math.sin(i / 3 + seed) * 3
    const noise = Math.sin(i * 2.7 + seed * 1.3) * 1.5
    const v = Math.max(1, Math.round(base + growth * i + wave + noise))
    pts.push(v)
  }
  return pts
}
function buildSeries(data: number[]): { line: string; area: string } {
  const max = Math.max(...data)
  const min = Math.min(...data)
  const W = 600
  const H = 120
  const PAD = 8
  const range = max - min || 1
  const pts = data.map((v, i) => {
    const x = PAD + (i / (data.length - 1)) * (W - PAD * 2)
    const y = H - PAD - ((v - min) / range) * (H - PAD * 2)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })
  return { line: pts.join(" "), area: `${PAD},${H} ${pts.join(" ")} ${W - PAD},${H}` }
}

// 近 30 日三个趋势（用户/厂商/匹配），各占整行
const TREND_RANGE = "07-12 ~ 08-10"
const TREND_AXIS = ["07-12", "07-26", "08-10"]
const trends = [
  { label: "用户总数", color: "#2563eb", bg: "#eff6ff", series: buildSeries(genTrend(1, 3, 0.3)) },
  { label: "厂商总数", color: "#d97706", bg: "#fffbeb", series: buildSeries(genTrend(2, 1, 0.15)) },
  { label: "匹配次数", color: "#dc2626", bg: "#fef2f2", series: buildSeries(genTrend(3, 5, 1.7)) },
]

function go(link: string): void {
  if (link) void router.push(link)
}

onMounted(async () => {
  try {
    stats.value = await adminStats()
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <NSpin :show="loading">
    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div
        v-for="c in cards"
        :key="c.label"
        class="stat-card"
        :class="{ 'is-clickable': !!c.link }"
        @click="go(c.link)"
      >
        <div class="stat-card__top">
          <span class="stat-card__icon" :style="{ background: c.bg, color: c.color }">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path :d="c.icon" />
            </svg>
          </span>
          <div class="stat-card__main">
            <div class="stat-card__label">{{ c.label }}</div>
            <div class="stat-card__value">{{ c.value }}</div>
          </div>
          <span class="stat-card__delta" :class="{ 'is-up': c.up }">{{ c.delta }}</span>
        </div>
      </div>
    </div>

    <!-- 历史趋势图：用户/厂商/匹配，各占整行，近 30 日 -->
    <div class="trend-rows">
      <section v-for="t in trends" :key="t.label" class="trend-row">
        <div class="trend-row__head">
          <h3 class="dash-card__title">{{ t.label }} · 近 30 日</h3>
          <span class="trend-row__range">{{ TREND_RANGE }}</span>
        </div>
        <svg class="trend-row__svg" viewBox="0 0 600 120" preserveAspectRatio="none">
          <polygon :points="t.series.area" :fill="t.color" opacity="0.1" />
          <polyline
            :points="t.series.line"
            fill="none"
            :stroke="t.color"
            stroke-width="2.5"
            vector-effect="non-scaling-stroke"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
        <div class="trend-row__axis">
          <span v-for="a in TREND_AXIS" :key="a">{{ a }}</span>
        </div>
      </section>
    </div>
  </NSpin>
</template>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-16);
}
.stat-card {
  position: relative;
  overflow: hidden;
  padding: var(--space-16) var(--space-16) var(--space-16) var(--space-16);
  background: var(--color-bg-panel);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-12);
  box-shadow: var(--shadow-1);
}
.stat-card.is-clickable {
  cursor: pointer;
  transition: transform var(--duration-fast) var(--ease-standard), box-shadow var(--duration-fast) var(--ease-standard);
}
.stat-card.is-clickable:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-2);
}
.stat-card__top {
  display: flex;
  align-items: center;
  gap: var(--space-12);
}
.stat-card__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  flex: none;
  border-radius: var(--radius-12);
}
.stat-card__main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.stat-card__value {
  font-size: 26px;
  font-weight: var(--font-weight-700);
  color: var(--color-text);
  line-height: 1.1;
}
.stat-card__label {
  font-size: 13px;
  color: var(--color-text-secondary);
}
.stat-card__delta {
  font-size: 13px;
  font-weight: var(--font-weight-600);
}
.stat-card__delta.is-up {
  color: var(--color-success);
}
.stat-card__delta.is-down {
  color: var(--color-error);
}

/* 图表区：历史趋势（各占整行） */
.dash-card__title {
  margin: 0;
  font-size: 15px;
  font-weight: var(--font-weight-600);
}
.trend-rows {
  display: flex;
  flex-direction: column;
  gap: var(--space-16);
  margin-top: var(--space-16);
}
.trend-row {
  padding: var(--space-16);
  background: var(--color-bg-panel);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-12);
  box-shadow: var(--shadow-1);
}
.trend-row__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-12);
}
.trend-row__range {
  font-size: 12px;
  color: var(--color-text-secondary);
}
.trend-row__svg {
  display: block;
  width: 100%;
  height: 140px;
  margin-top: var(--space-8);
}
.trend-row__axis {
  display: flex;
  justify-content: space-between;
  margin-top: var(--space-4);
  font-size: 12px;
  color: var(--color-text-secondary);
}
</style>
