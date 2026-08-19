<script setup lang="ts">
/**
 * 00B 登录（B2B Service 重设计，对齐 design-system/xmsn/MASTER.md）
 * - 视觉：.theme-b2b（藏青 #0F172A + 蓝 CTA #0369A1 + Plus Jakarta Sans）+ themeB2bOverrides（Naive 交互色）。
 * - 布局：Trust & Authority 分屏式——左品牌/信任区 + 右表单。
 * - 逻辑保持不变：成功后按 redirect 回跳 / 角色 fallback。
 */
import { ref } from "vue"
import { useRoute, useRouter } from "vue-router"
import { NButton, NConfigProvider, NForm, NFormItem, NInput, useMessage } from "naive-ui"

import { authLogin } from "@xmsn/api"
import { themeB2bOverrides } from "@xmsn/tokens"

import { useAuthStore } from "@/stores/auth"

const router = useRouter()
const route = useRoute()
const message = useMessage()
const auth = useAuthStore()

// 表单初始为空：不在页面暴露任何演示账号凭证
const form = ref({ phone: "", password: "" })
const loading = ref(false)

async function submit(): Promise<void> {
  if (!form.value.phone || !form.value.password) {
    message.warning("请输入手机号和密码")
    return
  }
  loading.value = true
  try {
    const res = await authLogin({ phone: form.value.phone, password: form.value.password })
    auth.setAuth(res.access_token, res.user)
    const redirect = route.query.redirect as string | undefined
    const fallback = res.user.role === "vendor" ? "/vendor/dashboard" : "/customer/chat"
    await router.push(redirect ?? fallback)
  } catch (e) {
    message.error((e as Error).message || "登录失败")
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login theme-b2b">
    <NConfigProvider :theme-overrides="themeB2bOverrides">
      <div class="login__inner">
        <!-- 品牌区：信任与权威 -->
        <aside class="login__brand" aria-label="品牌介绍">
          <RouterLink class="login__back" to="/">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M19 12H5M12 19l-7-7 7-7" /></svg>
            <span>返回首页</span>
          </RouterLink>
          <RouterLink class="login__brand-head" to="/" aria-label="需脉枢纽 首页">
            <span class="login__brand-mark" aria-hidden="true">需</span>
            <div>
              <h1 class="login__brand-name">需脉枢纽</h1>
              <p class="login__brand-tagline">B2B 代工制造 · AI 供需智能匹配</p>
            </div>
          </RouterLink>

          <ul class="login__points">
            <li class="login__point">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>
              <span><b>对话式需求萃取</b>描述需求即生成结构化档案</span>
            </li>
            <li class="login__point">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /><path d="M9 12l2 2 4-4" /></svg>
              <span><b>已审核厂商池</b>能力文档 AI 解析 + 人工审核</span>
            </li>
            <li class="login__point">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6M9 15l2 2 4-4" /></svg>
              <span><b>匹配可溯源</b>每项判定都可打开原文 PDF</span>
            </li>
          </ul>

          <span class="login__badge">已审核厂商 · 真实能力文档</span>
        </aside>

        <!-- 表单区 -->
        <main class="login__panel">
          <div class="login__card">
            <h2 class="login__title">登录工作台</h2>
            <p class="login__sub">进入后即可用对话描述需求、匹配已审核代工厂</p>

            <NForm class="login__form" label-placement="top">
              <NFormItem label="手机号">
                <NInput
                  v-model:value="form.phone"
                  size="large"
                  placeholder="请输入手机号"
                  :input-props="{ autocomplete: 'tel' }"
                />
              </NFormItem>
              <NFormItem label="密码">
                <NInput
                  v-model:value="form.password"
                  type="password"
                  size="large"
                  show-password-on="click"
                  placeholder="请输入密码"
                  :input-props="{ autocomplete: 'current-password' }"
                  @keyup.enter="submit()"
                />
              </NFormItem>
            </NForm>

            <NButton class="login__submit" type="primary" block size="large" :loading="loading" @click="submit()">
              登 录
            </NButton>

            <div class="login__footer">
              还没有账号？<router-link class="login__link" to="/register">立即注册</router-link>
            </div>
          </div>

          <p class="login__copyright">© 2026 需脉枢纽</p>
        </main>
      </div>
    </NConfigProvider>
  </div>
</template>

<style scoped>
@import url("https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap");

.login {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: var(--color-background);
  font-family: var(--font-family-base);
  -webkit-font-smoothing: antialiased;
}
.login * { box-sizing: border-box; }
.login a { text-decoration: none; }
/* 重置用 :where() 让特异性归零，避免覆盖后续单类 margin-top 纵向节奏 */
.login :where(h1, h2, p, ul) { margin: 0; padding: 0; }
.login ul { list-style: none; }

.login__inner {
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
.login__brand {
  background: var(--color-primary);
  color: #fff;
  padding: 48px 40px;
  display: flex;
  flex-direction: column;
  gap: 32px;
}
.login__back {
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
.login__back svg { width: 16px; height: 16px; }
.login__back:hover { color: #fff; background: rgba(255, 255, 255, 0.08); }
.login__back:focus-visible { outline: 3px solid rgba(3, 105, 161, 0.6); outline-offset: 2px; }
.login__brand-head {
  display: flex;
  align-items: center;
  gap: 14px;
  border-radius: 8px;
  cursor: pointer;
  transition: opacity 200ms ease;
}
.login__brand-head:hover { opacity: 0.88; }
.login__brand-head:focus-visible { outline: 3px solid rgba(3, 105, 161, 0.6); outline-offset: 2px; }
.login__brand-mark {
  flex: none;
  width: 46px; height: 46px;
  border-radius: 12px;
  background: var(--color-accent);
  color: #fff;
  font-weight: 800; font-size: 22px;
  display: inline-flex; align-items: center; justify-content: center;
}
.login__brand-name { font-size: 24px; font-weight: 800; color: #fff; }
.login__brand-tagline { margin-top: 4px; font-size: 13px; color: #94a3b8; }
.login__points { display: flex; flex-direction: column; gap: 20px; }
.login__point { display: flex; align-items: flex-start; gap: 12px; font-size: 14px; line-height: 1.6; color: #cbd5e1; }
.login__point svg { flex: none; width: 20px; height: 20px; color: var(--color-accent); margin-top: 2px; }
.login__point b { display: block; color: #fff; font-weight: 700; }
.login__badge {
  margin-top: auto;
  align-self: flex-start;
  padding: 8px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.14);
  color: #e2e8f0;
  font-size: 13px; font-weight: 600;
}

/* ---- 表单区 ---- */
.login__panel {
  padding: 48px 40px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.login__title { font-size: 28px; font-weight: 800; color: var(--color-primary); }
.login__sub { margin-top: 8px; font-size: 15px; color: var(--color-muted-foreground); }
.login__form { margin-top: 24px; }
.login__submit { margin-top: 4px; }
.login__footer { margin-top: 20px; text-align: center; font-size: 14px; color: var(--color-muted-foreground); }
.login__link { color: var(--color-accent); font-weight: 700; cursor: pointer; }
.login__link:hover { text-decoration: underline; }
.login__link:focus-visible { outline: 3px solid rgba(3, 105, 161, 0.45); outline-offset: 2px; }
.login__copyright { margin-top: 24px; text-align: center; font-size: 12px; color: var(--color-muted-foreground); }

/* ---- 响应式 ---- */
@media (max-width: 900px) {
  .login__inner { grid-template-columns: 1fr; }
  .login__brand { padding: 28px 24px; gap: 20px; }
  .login__points { display: none; }
  .login__panel { padding: 32px 24px; }
}
@media (max-width: 375px) {
  .login { padding: 16px; }
}

/* ---- 减少动效 ---- */
@media (prefers-reduced-motion: reduce) {
  .login *, .login *::before, .login *::after { transition-duration: 0.01ms !important; }
}
</style>