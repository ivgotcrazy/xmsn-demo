<script setup lang="ts">
/**
 * 认证页共享品牌区（B2B Service / MASTER.md Trust & Authority）：
 * 藏青背景 + 品牌 mark + 信任点（对话萃取 / 已审核厂商池 / 匹配可溯源）+ 徽章。
 * 用于登录 / 角色选择 / 厂商注册 / 采购方注册 等公共认证页（页面根需有 .theme-b2b）。
 */
</script>

<template>
  <aside class="auth-brand" aria-label="品牌介绍">
    <div class="auth-brand__head">
      <span class="auth-brand__mark" aria-hidden="true">需</span>
      <div>
        <h1 class="auth-brand__name">需脉枢纽</h1>
        <p class="auth-brand__tagline">B2B 代工制造 · AI 供需智能匹配</p>
      </div>
    </div>

    <ul class="auth-brand__points">
      <li class="auth-brand__point">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>
        <span><b>对话式需求萃取</b>描述需求即生成结构化档案</span>
      </li>
      <li class="auth-brand__point">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /><path d="M9 12l2 2 4-4" /></svg>
        <span><b>已审核厂商池</b>能力文档 AI 解析 + 人工审核</span>
      </li>
      <li class="auth-brand__point">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6M9 15l2 2 4-4" /></svg>
        <span><b>匹配可溯源</b>每项判定都可打开原文 PDF</span>
      </li>
    </ul>

    <span class="auth-brand__badge">已审核厂商 · 真实能力文档</span>
  </aside>
</template>

<style scoped>
.auth-brand {
  background: var(--color-primary);
  color: #fff;
  padding: 48px 40px;
  display: flex;
  flex-direction: column;
  gap: 32px;
}
.auth-brand__head { display: flex; align-items: center; gap: 14px; }
.auth-brand__mark {
  flex: none;
  width: 46px; height: 46px;
  border-radius: 12px;
  background: var(--color-accent);
  color: #fff;
  font-weight: 800; font-size: 22px;
  display: inline-flex; align-items: center; justify-content: center;
}
.auth-brand__name { margin: 0; font-size: 24px; font-weight: 800; color: #fff; }
.auth-brand__tagline { margin: 4px 0 0; font-size: 13px; color: #94a3b8; }
.auth-brand__points { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 20px; }
.auth-brand__point { display: flex; align-items: flex-start; gap: 12px; font-size: 14px; line-height: 1.6; color: #cbd5e1; }
.auth-brand__point svg { flex: none; width: 20px; height: 20px; color: var(--color-accent); margin-top: 2px; }
.auth-brand__point b { display: block; color: #fff; font-weight: 700; }
.auth-brand__badge {
  margin-top: auto;
  align-self: flex-start;
  padding: 8px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.14);
  color: #e2e8f0;
  font-size: 13px; font-weight: 600;
}
@media (max-width: 900px) {
  .auth-brand { padding: 28px 24px; gap: 20px; }
  .auth-brand__points { display: none; }
}
</style>
