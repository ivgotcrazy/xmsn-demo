<script setup lang="ts">
/**
 * 00A 注册（B2B Service 重设计，对齐 design-system/xmsn/MASTER.md）
 * - 视觉：.theme-b2b 藏青 #0F172A + 蓝 CTA #0369A1 + Plus Jakarta Sans，与登录页同款分屏（Trust & Authority）。
 * - 纯角色选择页：我是厂商 → /vendor/register；我是客户 → /customer/register。
 */
import { useRouter } from "vue-router"

const router = useRouter()
</script>

<template>
  <div class="register theme-b2b">
    <div class="register__inner">
      <!-- 品牌区：信任与权威 -->
      <aside class="register__brand" aria-label="品牌介绍">
          <RouterLink class="register__back" to="/">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M19 12H5M12 19l-7-7 7-7" /></svg>
            <span>返回首页</span>
          </RouterLink>
          <RouterLink class="register__brand-head" to="/" aria-label="需脉枢纽 首页">
            <span class="register__brand-mark" aria-hidden="true">需</span>
            <div>
              <h1 class="register__brand-name">需脉枢纽</h1>
              <p class="register__brand-tagline">B2B 代工制造 · AI 供需智能匹配</p>
            </div>
          </RouterLink>
        <ul class="register__points">
          <li class="register__point">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>
            <span><b>对话式需求萃取</b>描述需求即生成结构化档案</span>
          </li>
          <li class="register__point">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /><path d="M9 12l2 2 4-4" /></svg>
            <span><b>已审核厂商池</b>能力文档 AI 解析 + 人工审核</span>
          </li>
          <li class="register__point">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6M9 15l2 2 4-4" /></svg>
            <span><b>匹配可溯源</b>每项判定都可打开原文 PDF</span>
          </li>
        </ul>

        <span class="register__badge">已审核厂商 · 真实能力文档</span>
      </aside>

      <!-- 角色选择区 -->
      <main class="register__panel">
        <h2 class="register__title">注册账号</h2>
        <p class="register__sub">选择您的身份开始使用</p>

        <div class="register__roles">
          <button class="register__role" type="button" @click="router.push('/vendor/register')">
            <span class="register__role-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 20h20M4 20V8l6 4V8l6 4V4h4v16" /></svg>
            </span>
            <span class="register__role-body">
              <b>我是厂商</b>
              <span>上传能力文档，入驻代工匹配池</span>
            </span>
            <span class="register__role-arrow" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
            </span>
          </button>

          <button class="register__role" type="button" @click="router.push('/customer/register')">
            <span class="register__role-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10" /><circle cx="12" cy="12" r="6" /><circle cx="12" cy="12" r="2" /></svg>
            </span>
            <span class="register__role-body">
              <b>我是客户</b>
              <span>对话描述需求，匹配已审核代工厂</span>
            </span>
            <span class="register__role-arrow" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
            </span>
          </button>
        </div>

        <div class="register__footer">
          已有账号？<router-link class="register__link" to="/login">去登录</router-link>
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
@import url("https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap");

.register {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: var(--color-background);
  font-family: var(--font-family-base);
  -webkit-font-smoothing: antialiased;
}
.register * { box-sizing: border-box; }
.register a { text-decoration: none; }
/* 重置用 :where() 让特异性归零，避免覆盖后续单类 margin-top */
.register :where(h1, h2, p, ul) { margin: 0; padding: 0; }
.register ul { list-style: none; }
.register button { font-family: inherit; }

.register__inner {
  width: 100%;
  max-width: 1000px;
  display: grid;
  grid-template-columns: 0.95fr 1.05fr;
  border-radius: 20px;
  overflow: hidden;
  border: 1px solid var(--color-border);
  background: var(--color-card);
  box-shadow: var(--shadow-lg);
}

/* ---- 品牌区 ---- */
.register__brand {
  background: var(--color-primary);
  color: #fff;
  padding: 48px 40px;
  display: flex;
  flex-direction: column;
  gap: 32px;
}
.register__back {
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  margin: -6px -10px 0;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #cbd5e1;
  cursor: pointer;
  transition: color 200ms ease, background 200ms ease;
}
.register__back svg { width: 16px; height: 16px; }
.register__back:hover { color: #fff; background: rgba(255, 255, 255, 0.08); }
.register__back:focus-visible { outline: 3px solid rgba(3, 105, 161, 0.6); outline-offset: 2px; }
.register__brand-head {
  display: flex;
  align-items: center;
  gap: 14px;
  border-radius: 8px;
  cursor: pointer;
  transition: opacity 200ms ease;
}
.register__brand-head:hover { opacity: 0.88; }
.register__brand-head:focus-visible { outline: 3px solid rgba(3, 105, 161, 0.6); outline-offset: 2px; }
.register__brand-mark {
  flex: none;
  width: 46px; height: 46px;
  border-radius: 12px;
  background: var(--color-accent);
  color: #fff;
  font-weight: 800; font-size: 22px;
  display: inline-flex; align-items: center; justify-content: center;
}
.register__brand-name { font-size: 24px; font-weight: 800; color: #fff; }
.register__brand-tagline { margin-top: 4px; font-size: 13px; color: #94a3b8; }
.register__points { display: flex; flex-direction: column; gap: 20px; }
.register__point { display: flex; align-items: flex-start; gap: 12px; font-size: 14px; line-height: 1.6; color: #cbd5e1; }
.register__point svg { flex: none; width: 20px; height: 20px; color: var(--color-accent); margin-top: 2px; }
.register__point b { display: block; color: #fff; font-weight: 700; }
.register__badge {
  margin-top: auto;
  align-self: flex-start;
  padding: 8px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.14);
  color: #e2e8f0;
  font-size: 13px; font-weight: 600;
}

/* ---- 角色选择区 ---- */
.register__panel {
  padding: 48px 40px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.register__title { font-size: 28px; font-weight: 800; color: var(--color-primary); }
.register__sub { margin-top: 8px; font-size: 15px; color: var(--color-muted-foreground); }
.register__roles { margin-top: 24px; display: flex; flex-direction: column; gap: 16px; }
.register__role {
  display: flex;
  align-items: center;
  gap: 14px;
  width: 100%;
  padding: 18px 20px;
  border: 1px solid var(--color-border);
  border-radius: 14px;
  background: var(--color-card);
  text-align: left;
  cursor: pointer;
  transition: border-color 200ms ease, box-shadow 200ms ease, transform 200ms ease;
}
.register__role:hover { border-color: var(--color-accent); box-shadow: var(--shadow-md); transform: translateY(-1px); }
.register__role:active { transform: translateY(0); }
.register__role:focus-visible { outline: 3px solid rgba(3, 105, 161, 0.45); outline-offset: 2px; }
.register__role-icon {
  flex: none;
  width: 44px; height: 44px;
  border-radius: 12px;
  background: var(--color-muted);
  color: var(--color-accent);
  display: inline-flex; align-items: center; justify-content: center;
}
.register__role-icon svg { width: 22px; height: 22px; }
.register__role-body { display: flex; flex-direction: column; gap: 4px; }
.register__role-body b { font-size: 16px; font-weight: 700; color: var(--color-primary); }
.register__role-body > span { font-size: 13px; color: var(--color-muted-foreground); line-height: 1.5; }
.register__role-arrow { margin-left: auto; color: var(--color-muted-foreground); flex: none; }
.register__role-arrow svg { width: 18px; height: 18px; }
.register__footer { margin-top: 24px; text-align: center; font-size: 14px; color: var(--color-muted-foreground); }
.register__link { color: var(--color-accent); font-weight: 700; cursor: pointer; }
.register__link:hover { text-decoration: underline; }
.register__link:focus-visible { outline: 3px solid rgba(3, 105, 161, 0.45); outline-offset: 2px; }

/* ---- 响应式 ---- */
@media (max-width: 900px) {
  .register__inner { grid-template-columns: 1fr; }
  .register__brand { padding: 28px 24px; gap: 20px; }
  .register__points { display: none; }
  .register__panel { padding: 32px 24px; }
}
@media (max-width: 375px) {
  .register { padding: 16px; }
}

/* ---- 减少动效 ---- */
@media (prefers-reduced-motion: reduce) {
  .register *, .register *::before, .register *::after { transition-duration: 0.01ms !important; }
}
</style>
