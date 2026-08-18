<script setup lang="ts">
/**
 * 首页（00C 落地页 / 公开）
 * 设计规范：design-system/xmsn/MASTER.md（B2B Service · Trust & Authority + Conversion）
 * - 藏青 #0F172A + 蓝 CTA #0369A1 + Plus Jakarta Sans，高可访问性（对比度/焦点态/减少动效/44px 触控）。
 * - 核心卖点：基于「对话」实现供需智能匹配 → Hero 内置聊天预览动效 + 醒目「立即开始对话匹配」入口。
 * - 卖点数据取自真实演示数据（智能音箱品类 / 10 家已审核厂商 / 匹配分 / 原文溯源）。
 */
import { onMounted, onUnmounted, ref } from "vue"
import { useRouter } from "vue-router"

import { useAuthStore } from "@/stores/auth"

const router = useRouter()
const auth = useAuthStore()

/** 聊天入口：已登录直达对话页，未登录先登录（登录后回跳）。 */
function chatEntry(): void {
  router.push(auth.isAuthenticated() ? "/customer/chat" : "/login?redirect=/customer/chat")
}
function vendorEntry(): void {
  router.push(auth.isAuthenticated() ? "/vendor/dashboard" : "/login?redirect=/vendor/dashboard")
}

// ---------- Hero 聊天预览动效（步骤状态机，尊重 prefers-reduced-motion） ----------
const CHAT_STEPS = 6
const step = ref(0)
let timer: number | undefined

function prefersReduced(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches
}

function play() {
  if (prefersReduced()) {
    step.value = CHAT_STEPS - 1 // 静态展示最终态
    return
  }
  step.value = 0
  timer = window.setInterval(() => {
    step.value = (step.value + 1) % CHAT_STEPS
  }, 1600)
}

onMounted(play)
onUnmounted(() => {
  if (timer !== undefined) window.clearInterval(timer)
})

// ---------- 真实演示数据（智能音箱品类，取自实际匹配运行） ----------
const demoVendors = [
  { name: "深圳市声域智能科技有限公司", score: 100, os: "Android + RTOS", cert: "CE · FCC · SRRC", moq: 1000, lead: 30, loc: "广东深圳" },
  { name: "广州市云雀智能科技有限公司", score: 100, os: "Android", cert: "—", moq: 1000, lead: 25, loc: "广东广州" },
  { name: "中山市天籁智能电器有限公司", score: 88, os: "Android", cert: "CE · FCC · SRRC", moq: 1500, lead: 28, loc: "广东中山" },
  { name: "青岛市浪声智能设备有限公司", score: 75, os: "RTOS", cert: "CE · FCC", moq: 500, lead: 25, loc: "山东青岛" },
]

const stats = [
  { value: "10", label: "已入驻智能音箱厂商" },
  { value: "10", label: "真实 PDF 能力文档" },
  { value: "100", label: "Top 匹配分" },
  { value: "<1s", label: "单次匹配计算" },
]
</script>

<template>
  <div class="home theme-b2b">
    <!-- 导航 -->
    <header class="nav">
      <div class="nav__inner">
        <a class="nav__brand" href="#top" aria-label="需脉枢纽 首页">
          <span class="nav__logo">需</span>
          <span class="nav__name">需脉枢纽</span>
        </a>
        <nav class="nav__links" aria-label="主导航">
          <a href="#how">如何工作</a>
          <a href="#product">产品特色</a>
          <a href="#demo">智能音箱演示</a>
        </nav>
        <div class="nav__actions">
          <template v-if="auth.isAuthenticated()">
            <button class="btn btn--ghost" type="button" @click="router.push('/customer/chat')">进入工作台</button>
          </template>
          <template v-else>
            <button class="btn btn--ghost" type="button" @click="router.push('/login')">登录</button>
          </template>
          <button class="btn btn--primary" type="button" @click="chatEntry">
            开始匹配
            <svg class="btn__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
          </button>
        </div>
      </div>
    </header>

    <!-- Hero -->
    <section id="top" class="hero">
      <div class="hero__inner">
        <div class="hero__copy">
          <span class="eyebrow">B2B 代工制造 · AI 供需智能匹配</span>
          <h1 class="hero__title">描述需求，<span class="hero__accent">对话即匹配</span></h1>
          <p class="hero__lead">
            需脉枢纽用 AI 对话萃取你的代工需求，智能匹配已审核代工厂，
            并给出可解释的匹配理由、风险提示与「原文溯源」——不靠猜，每一项都有出处。
          </p>
          <div class="hero__cta">
            <button class="btn btn--primary btn--lg" type="button" @click="chatEntry">
              立即开始对话匹配
              <svg class="btn__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
            </button>
            <button class="btn btn--secondary btn--lg" type="button" @click="vendorEntry">厂商入驻</button>
          </div>
          <ul class="hero__stats">
            <li v-for="s in stats" :key="s.label" class="hero__stat">
              <strong>{{ s.value }}</strong><span>{{ s.label }}</span>
            </li>
          </ul>
        </div>

        <!-- 聊天预览动效 -->
        <div class="chat-preview" aria-hidden="true">
          <div class="chat-preview__head">
            <span class="chat-preview__dot" />
            <span>需脉 AI 选型助手</span>
            <span class="chat-preview__live">演示</span>
          </div>
          <div class="chat-preview__body">
            <div class="msg msg--agent" :class="{ 'is-in': step >= 0 }">
              <span class="msg__who">需</span>
              <p>您好！我是需脉AI选型助手。请告诉我您需要找什么类型的代工厂？</p>
            </div>
            <div class="chips" :class="{ 'is-in': step >= 1 }">
              <span class="chip">机顶盒</span>
              <span class="chip chip--active">智能音箱</span>
              <span class="chip">IoT 设备</span>
            </div>
            <div class="msg msg--user" :class="{ 'is-in': step >= 2 }">
              <p>我需要智能音箱，Android 系统，起订量 1000 台，交期 30 天</p>
            </div>
            <div class="msg msg--agent" :class="{ 'is-in': step >= 3 }">
              <span class="msg__who">需</span>
              <p class="typing"><span /><span /><span /></p>
            </div>
            <div class="msg msg--agent" :class="{ 'is-in': step >= 4 }">
              <span class="msg__who">需</span>
              <p>已记录：产品类型 智能音箱 · 操作系统 Android · 起订量 1000 · 交期 30 天</p>
            </div>
            <div class="result" :class="{ 'is-in': step >= 5 }">
              <div class="result__row"><span>深圳市声域智能科技有限公司</span><b>100</b></div>
              <div class="result__row"><span>广州市云雀智能科技有限公司</span><b>100</b></div>
              <div class="result__row"><span>中山市天籁智能电器有限公司</span><b>88</b></div>
              <div class="result__cite"><svg class="result__doc-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6" /></svg>第 1 页 · 原文溯源</div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 数据证明（Proof） -->
    <section id="proof" class="proof">
      <div class="proof__inner">
        <h2 class="section-title">不是演示片，是真实运行的结果</h2>
        <p class="section-sub">厂商能力由 AI 从真实 PDF 解析、经人工审核，匹配全程可解释、可溯源。</p>
        <ul class="proof__grid">
          <li class="proof__item">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" /></svg>
            <h3>AI 解析 + 人工审核</h3>
            <p>厂商上传能力文档，AI 提取结构化能力档案，审核通过后才进入匹配池。</p>
          </li>
          <li class="proof__item">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 20V10M18 20V4M6 20v-4" /></svg>
            <h3>双通道匹配</h3>
            <p>规则参数判定 + 语义召回双通道打分，兼顾硬指标与自然语言意图。</p>
          </li>
          <li class="proof__item">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6M9 15l2 2 4-4" /></svg>
            <h3>出处可溯源</h3>
            <p>每条匹配判定都能打开厂商原始文档「PDF 第 N 页」核对，不凭感觉。</p>
          </li>
        </ul>
      </div>
    </section>

    <!-- 如何工作（Solution Overview） -->
    <section id="how" class="how">
      <div class="how__inner">
        <h2 class="section-title">三步，从需求到决策</h2>
        <ol class="how__steps">
          <li class="how__step">
            <span class="how__num">1</span>
            <h3>对话描述需求</h3>
            <p>AI Agent 引导补全品类、参数与严格度，自动生成结构化需求档案，支持随时修正。</p>
          </li>
          <li class="how__step">
            <span class="how__num">2</span>
            <h3>智能双通道匹配</h3>
            <p>规则判定 + 语义召回，对已审核厂商打分排序，秒级返回候选。</p>
          </li>
          <li class="how__step">
            <span class="how__num">3</span>
            <h3>可解释决策</h3>
            <p>匹配理由、风险提示与原文溯源一应俱全，对比多家厂商后做出采购决策。</p>
          </li>
        </ol>
      </div>
    </section>

    <!-- 分角色价值 -->
    <section id="product" class="product">
      <div class="product__inner">
        <h2 class="section-title">为供需双方与管理者而设计</h2>
        <div class="product__grid">
          <article class="product__card">
            <h3>面向客户（采购方）</h3>
            <ul>
              <li>对话式需求描述，AI 主动引导补全</li>
              <li>秒级匹配 + 匹配分梯度对比</li>
              <li>匹配理由 / 风险提示 / 原文溯源</li>
              <li>会话历史与需求档案版本可回看</li>
            </ul>
          </article>
          <article class="product__card">
            <h3>面向厂商</h3>
            <ul>
              <li>上传能力文档即生成结构化能力档案</li>
              <li>字段级溯源，随时更新重新解析</li>
              <li>能力完备度自检，引导补齐资料</li>
              <li>审核通过后进入真实需求匹配池</li>
            </ul>
          </article>
          <article class="product__card">
            <h3>面向管理者</h3>
            <ul>
              <li>需求 / 客户 / 厂商 / 日志数据概览</li>
              <li>匹配结果追溯与复核</li>
              <li>厂商审核与审计日志</li>
              <li>全部操作留痕，可追踪</li>
            </ul>
          </article>
        </div>
      </div>
    </section>

    <!-- 智能音箱真实演示 -->
    <section id="demo" class="demo">
      <div class="demo__inner">
        <h2 class="section-title">精选演示 · 智能音箱品类</h2>
        <p class="section-sub">以「智能音箱 / Android / 起订量 1000 台 / 交期 30 天」为例的真实匹配结果。</p>
        <ul class="demo__grid">
          <li v-for="v in demoVendors" :key="v.name" class="demo__card">
            <div class="demo__head">
              <span class="demo__name">{{ v.name }}</span>
              <span class="demo__score">匹配 {{ v.score }}</span>
            </div>
            <dl class="demo__meta">
              <div><dt>系统</dt><dd>{{ v.os }}</dd></div>
              <div><dt>认证</dt><dd>{{ v.cert }}</dd></div>
              <div><dt>MOQ</dt><dd>{{ v.moq }} 台</dd></div>
              <div><dt>交期</dt><dd>{{ v.lead }} 天</dd></div>
            </dl>
          </li>
        </ul>
        <div class="demo__cta">
          <button class="btn btn--primary btn--lg" type="button" @click="chatEntry">
            亲自跑一次匹配
            <svg class="btn__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
          </button>
        </div>
      </div>
    </section>

    <!-- 最终 CTA -->
    <section id="cta" class="cta">
      <div class="cta__inner">
        <h2 class="cta__title">现在就描述您的代工需求</h2>
        <p class="cta__sub">登录后即可保存会话与历史匹配结果。</p>
        <button class="btn btn--inverse btn--lg" type="button" @click="chatEntry">
          立即开始对话匹配
          <svg class="btn__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
        </button>
      </div>
    </section>

    <!-- 页脚 -->
    <footer class="footer">
      <div class="footer__inner">
        <div class="footer__brand">
          <span class="nav__logo">需</span>
          <span>需脉枢纽 · B2B 代工制造供需智能匹配平台</span>
        </div>
        <div class="footer__links">
          <a href="#how">如何工作</a>
          <a href="#product">产品特色</a>
          <a href="#demo">智能音箱演示</a>
          <a href="#top">返回顶部</a>
        </div>
        <p class="footer__copy">© 2026 需脉枢纽 · 种子轮 PoC 演示</p>
      </div>
    </footer>
  </div>
</template>

<style scoped>
@import url("https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap");

/* 首页消费 .theme-b2b 语义 token（@xmsn/tokens/tokens-b2b.css ← MASTER.md B2B Service） */
.home {
  background: var(--color-background);
  color: var(--color-foreground);
  font-family: var(--font-family-base);
  -webkit-font-smoothing: antialiased;
  scroll-behavior: smooth;
}
.home * { box-sizing: border-box; }
.home a { color: inherit; text-decoration: none; }
.home :where(ul, ol) { margin: 0; padding: 0; list-style: none; }
.home :where(h1, h2, h3, p) { margin: 0; }

/* ---------- 通用按钮 ---------- */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 24px;
  border-radius: 8px;
  font: 600 15px/1.4 "Plus Jakarta Sans", system-ui, sans-serif;
  border: 2px solid transparent;
  cursor: pointer;
  transition: all 200ms ease;
  white-space: nowrap;
}
.btn:focus-visible { outline: 3px solid rgba(3, 105, 161, 0.45); outline-offset: 2px; }
.btn--primary { background: var(--color-accent); color: #fff; }
.btn--primary:hover { background: #075985; transform: translateY(-1px); }
.btn--secondary { background: transparent; color: var(--color-primary); border-color: var(--color-primary); }
.btn--secondary:hover { background: rgba(15, 23, 42, 0.06); }
.btn--ghost { background: transparent; color: var(--color-primary); }
.btn--ghost:hover { background: rgba(15, 23, 42, 0.06); }
.btn--inverse { background: #fff; color: var(--color-primary); }
.btn--inverse:hover { background: #f1f5f9; transform: translateY(-1px); }
.btn--lg { padding: 16px 32px; font-size: 16px; }
.btn__icon { width: 18px; height: 18px; }

/* ---------- 导航 ---------- */
.nav {
  position: sticky;
  top: 0;
  z-index: 20;
  background: rgba(248, 250, 252, 0.85);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--color-border);
}
.nav__inner {
  max-width: 1180px;
  margin: 0 auto;
  padding: 16px 24px;
  display: flex;
  align-items: center;
  gap: 24px;
}
.nav__brand { display: flex; align-items: center; gap: 8px; }
.nav__logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 9px;
  background: var(--color-primary);
  color: #fff;
  font-weight: 800;
  font-size: 17px;
}
.nav__name { font-weight: 800; font-size: 18px; color: var(--color-primary); }
.nav__links { display: flex; gap: 24px; margin-left: 8px; }
.nav__links a { color: var(--color-muted-foreground); font-weight: 600; font-size: 15px; transition: color 200ms ease; }
.nav__links a:hover { color: var(--color-primary); }
.nav__actions { margin-left: auto; display: flex; align-items: center; gap: 8px; }

/* ---------- Hero ---------- */
.hero { padding: 64px 24px 64px; }
.hero__inner {
  max-width: 1180px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1.05fr 0.95fr;
  gap: 64px;
  align-items: center;
}
.eyebrow {
  display: inline-block;
  padding: 6px 12px;
  border-radius: 999px;
  background: #e0f2fe;
  color: #075985;
  font-weight: 700;
  font-size: 13px;
}
.hero__title { margin-top: 24px; font-size: clamp(36px, 5vw, 56px); font-weight: 800; line-height: 1.12; color: var(--color-primary); }
.hero__accent { color: var(--color-accent); }
.hero__lead { margin-top: 24px; font-size: 17px; line-height: 1.7; color: var(--color-muted-foreground); max-width: 34em; }
.hero__cta { margin-top: 32px; display: flex; gap: 16px; flex-wrap: wrap; }
.hero__stats { margin-top: 48px; display: grid; grid-template-columns: repeat(4, auto); gap: 32px; }
.hero__stat { display: flex; flex-direction: column; gap: 4px; }
.hero__stat strong { font-size: 26px; font-weight: 800; color: var(--color-primary); }
.hero__stat span { font-size: 13px; color: var(--color-muted-foreground); }

/* ---------- 聊天预览 ---------- */
.chat-preview {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  box-shadow: var(--shadow-xl);
  overflow: hidden;
}
.chat-preview__head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: var(--color-primary);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
}
.chat-preview__dot { width: 10px; height: 10px; border-radius: 50%; background: #34d399; }
.chat-preview__live { margin-left: auto; font-size: 12px; background: rgba(255, 255, 255, 0.18); padding: 2px 8px; border-radius: 999px; }
.chat-preview__body { padding: 16px; display: flex; flex-direction: column; gap: 12px; min-height: 340px; }
.msg { display: flex; gap: 8px; align-items: flex-start; opacity: 0; transform: translateY(8px); transition: opacity 400ms ease, transform 400ms ease; }
.msg.is-in { opacity: 1; transform: none; }
.msg__who {
  flex: none;
  width: 26px; height: 26px;
  border-radius: 8px;
  background: var(--color-accent);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  display: inline-flex; align-items: center; justify-content: center;
}
.msg p { background: var(--color-muted); border-radius: 10px 10px 10px 2px; padding: 12px 16px; font-size: 14px; line-height: 1.55; }
.msg--user { flex-direction: row-reverse; }
.msg--user p { background: var(--color-accent); color: #fff; border-radius: 10px 10px 2px 10px; }
.chips { display: flex; gap: 8px; flex-wrap: wrap; opacity: 0; transform: translateY(8px); transition: opacity 400ms ease 150ms, transform 400ms ease 150ms; }
.chips.is-in { opacity: 1; transform: none; }
.chip { padding: 6px 12px; border-radius: 999px; border: 1px solid var(--color-border); background: #fff; font-size: 13px; font-weight: 600; }
.chip--active { border-color: var(--color-accent); color: var(--color-accent); background: #e0f2fe; }
.typing { display: inline-flex; gap: 4px; }
.typing span { width: 6px; height: 6px; border-radius: 50%; background: var(--color-muted-foreground); animation: blink 1.2s infinite; }
.typing span:nth-child(2) { animation-delay: 0.2s; }
.typing span:nth-child(3) { animation-delay: 0.4s; }
@keyframes blink { 0%, 100% { opacity: 0.3; } 50% { opacity: 1; } }
.result { opacity: 0; transform: translateY(8px); transition: opacity 400ms ease 200ms, transform 400ms ease 200ms; border: 1px solid var(--color-border); border-radius: 12px; overflow: hidden; }
.result.is-in { opacity: 1; transform: none; }
.result__row { display: flex; justify-content: space-between; gap: 8px; padding: 12px 16px; font-size: 13px; }
.result__row + .result__row { border-top: 1px solid var(--color-border); }
.result__row b { color: var(--color-accent); font-weight: 800; }
.result__cite { display: flex; align-items: center; gap: 6px; padding: 8px 12px; background: var(--color-muted); font-size: 12px; color: var(--color-muted-foreground); }
.result__doc-icon { width: 14px; height: 14px; flex: none; }

/* ---------- 区块通用 ---------- */
.section-title { font-size: clamp(26px, 3.4vw, 36px); font-weight: 800; color: var(--color-primary); text-align: center; }
.section-sub { margin-top: 16px; font-size: 16px; color: var(--color-muted-foreground); text-align: center; max-width: 44em; margin-inline: auto; }

/* ---------- Proof ---------- */
.proof { padding: 64px 24px; }
.proof__inner { max-width: 1180px; margin: 0 auto; }
.proof__grid { margin-top: 48px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }
.proof__item { background: var(--color-card); border: 1px solid var(--color-border); border-radius: 14px; padding: 32px; box-shadow: var(--shadow-sm); transition: box-shadow 200ms ease, transform 200ms ease; }
.proof__item:hover { box-shadow: var(--shadow-lg); transform: translateY(-2px); }
.proof__item svg { width: 34px; height: 34px; color: var(--color-accent); }
.proof__item h3 { margin-top: 16px; font-size: 18px; font-weight: 700; color: var(--color-primary); }
.proof__item p { margin-top: 8px; font-size: 15px; line-height: 1.6; color: var(--color-muted-foreground); }

/* ---------- How ---------- */
.how { padding: 64px 24px; background: var(--color-card); border-block: 1px solid var(--color-border); }
.how__inner { max-width: 1180px; margin: 0 auto; }
.how__steps { margin-top: 48px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }
.how__step { position: relative; padding: 32px 24px 32px 76px; border-radius: 14px; border: 1px solid var(--color-border); }
.how__num {
  position: absolute; left: 24px; top: 32px;
  width: 34px; height: 34px; border-radius: 10px;
  background: var(--color-primary); color: #fff;
  font-weight: 800; display: inline-flex; align-items: center; justify-content: center;
}
.how__step h3 { font-size: 18px; font-weight: 700; color: var(--color-primary); }
.how__step p { margin-top: 8px; font-size: 15px; line-height: 1.6; color: var(--color-muted-foreground); }

/* ---------- Product ---------- */
.product { padding: 64px 24px; }
.product__inner { max-width: 1180px; margin: 0 auto; }
.product__grid { margin-top: 48px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }
.product__card { background: var(--color-card); border: 1px solid var(--color-border); border-radius: 14px; padding: 32px; box-shadow: var(--shadow-sm); }
.product__card h3 { font-size: 18px; font-weight: 700; color: var(--color-primary); padding-bottom: 16px; border-bottom: 1px solid var(--color-border); }
.product__card ul { margin-top: 16px; display: flex; flex-direction: column; gap: 12px; }
.product__card li { position: relative; padding-left: 20px; font-size: 15px; line-height: 1.55; color: var(--color-muted-foreground); }
.product__card li::before { content: ""; position: absolute; left: 2px; top: 8px; width: 8px; height: 8px; border-radius: 50%; background: var(--color-accent); }

/* ---------- Demo ---------- */
.demo { padding: 64px 24px; background: var(--color-card); border-block: 1px solid var(--color-border); }
.demo__inner { max-width: 1180px; margin: 0 auto; }
.demo__grid { margin-top: 48px; display: grid; grid-template-columns: repeat(4, 1fr); gap: 24px; }
.demo__card { border: 1px solid var(--color-border); border-radius: 14px; padding: 24px; box-shadow: var(--shadow-sm); transition: box-shadow 200ms ease, transform 200ms ease; }
.demo__card:hover { box-shadow: var(--shadow-lg); transform: translateY(-2px); }
.demo__head { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
.demo__name { font-size: 15px; font-weight: 700; color: var(--color-primary); line-height: 1.4; }
.demo__score { flex: none; font-size: 13px; font-weight: 800; color: var(--color-accent); }
.demo__meta { margin-top: 16px; display: grid; grid-template-columns: 1fr 1fr; gap: 12px 16px; }
.demo__meta div { display: flex; justify-content: space-between; gap: 6px; font-size: 13px; }
.demo__meta dt { color: var(--color-muted-foreground); }
.demo__meta dd { margin: 0; font-weight: 600; color: var(--color-foreground); }
.demo__cta { margin-top: 48px; text-align: center; }

/* ---------- CTA ---------- */
.cta { padding: 64px 24px; background: var(--color-primary); color: #fff; }
.cta__inner { max-width: 760px; margin: 0 auto; text-align: center; }
.cta__title { font-size: clamp(28px, 4vw, 40px); font-weight: 800; }
.cta__sub { margin-top: 16px; font-size: 16px; color: #cbd5e1; }
.cta__inner .btn { margin-top: 32px; }

/* ---------- Footer ---------- */
.footer { padding: 48px 24px; background: var(--color-primary); border-top: 1px solid rgba(255, 255, 255, 0.1); color: #cbd5e1; }
.footer__inner { max-width: 1180px; margin: 0 auto; display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.footer__brand { display: flex; align-items: center; gap: 8px; font-weight: 600; }
.footer__links { display: flex; gap: 24px; flex-wrap: wrap; }
.footer__links a { color: #cbd5e1; font-size: 14px; transition: color 200ms ease; }
.footer__links a:hover { color: #fff; }
.footer__copy { width: 100%; margin-top: 24px; font-size: 13px; color: #64748b; text-align: center; }

/* ---------- 响应式 ---------- */
@media (max-width: 1024px) {
  .hero__inner { grid-template-columns: 1fr; }
  .proof__grid, .how__steps, .product__grid { grid-template-columns: 1fr; }
  .demo__grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 768px) {
  .nav__links { display: none; }
  .hero__stats { grid-template-columns: repeat(2, 1fr); }
  .demo__grid { grid-template-columns: 1fr; }
}
@media (max-width: 480px) {
  .nav__inner { padding: 12px 16px; gap: 12px; }
  .nav__logo { width: 30px; height: 30px; font-size: 15px; }
  .nav__name { font-size: 16px; }
  .nav__actions { gap: 6px; }
  .nav__actions .btn { padding: 9px 12px; font-size: 13px; }
  .nav__actions .btn__icon { width: 15px; height: 15px; }
}
@media (max-width: 375px) {
  .hero__cta .btn { width: 100%; }
}

/* 减少动效：直接展示静态最终态（聊天预览在脚本层已处理，这里兜底关闭动画） */
@media (prefers-reduced-motion: reduce) {
  .home { scroll-behavior: auto; }
  .home *, .home *::before, .home *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
}
</style>
