<script setup lang="ts">
/**
 * 客户注册（B2B Service 重设计，对齐 MASTER.md）：
 * 00A 选「我是采购方」→ 注册表单（分屏式 theme-b2b）→ 直接进入 02A 自动登录。
 * 逻辑不变：注册成功 → /customer/chat。
 */
import { ref } from "vue"
import { useRouter } from "vue-router"
import { NButton, NConfigProvider, NForm, NFormItem, NInput, useMessage } from "naive-ui"

import { authRegister } from "@xmsn/api"
import { themeB2bOverrides } from "@xmsn/tokens"

import AuthBrandPanel from "@/components/business/AuthBrandPanel.vue"
import { useAuthStore } from "@/stores/auth"

const router = useRouter()
const message = useMessage()
const auth = useAuthStore()

const form = ref({ phone: "", email: "", verifyCode: "", password: "" })
const loading = ref(false)
const countdown = ref(0)

async function sendCode(): Promise<void> {
  if (!form.value.phone) {
    message.warning("请先填写手机号")
    return
  }
  message.success("验证码已发送（mock）")
  countdown.value = 60
  const timer = window.setInterval(() => {
    countdown.value -= 1
    if (countdown.value <= 0) window.clearInterval(timer)
  }, 1000)
}

async function submit(): Promise<void> {
  if (!form.value.phone || !form.value.password) {
    message.warning("请填写完整信息")
    return
  }
  loading.value = true
  try {
    const res = await authRegister({
      phone: form.value.phone,
      email: form.value.email || undefined,
      password: form.value.password,
      verify_code: form.value.verifyCode || "1234",
      role: "customer",
    })
    auth.setAuth(res.access_token, res.user)
    await router.push("/customer/chat")
  } catch (e) {
    message.error((e as Error).message || "注册失败")
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-reg theme-b2b">
    <NConfigProvider :theme-overrides="themeB2bOverrides">
      <div class="auth-reg__inner">
        <AuthBrandPanel />

        <main class="auth-reg__panel">
          <div class="auth-reg__card">
            <h2 class="auth-reg__title">采购方注册</h2>
            <p class="auth-reg__sub">注册后直接进入需求对话</p>

            <NForm class="auth-reg__form" label-placement="top">
              <NFormItem label="手机号">
                <NInput
                  v-model:value="form.phone"
                  size="large"
                  placeholder="请输入手机号"
                  :input-props="{ autocomplete: 'tel' }"
                />
              </NFormItem>
              <NFormItem label="邮箱（选填）">
                <NInput
                  v-model:value="form.email"
                  size="large"
                  placeholder="请输入邮箱"
                  :input-props="{ autocomplete: 'email' }"
                />
              </NFormItem>
              <NFormItem label="验证码">
                <div class="auth-reg__code">
                  <NInput v-model:value="form.verifyCode" size="large" placeholder="验证码" />
                  <NButton size="large" :disabled="countdown > 0" @click="sendCode()">
                    {{ countdown > 0 ? `${countdown}s` : "获取验证码" }}
                  </NButton>
                </div>
              </NFormItem>
              <NFormItem label="密码">
                <NInput
                  v-model:value="form.password"
                  type="password"
                  size="large"
                  show-password-on="click"
                  placeholder="6 位以上密码"
                  :input-props="{ autocomplete: 'new-password' }"
                  @keyup.enter="submit()"
                />
              </NFormItem>
            </NForm>

            <NButton class="auth-reg__submit" type="primary" block size="large" :loading="loading" @click="submit()">
              注 册
            </NButton>

            <div class="auth-reg__footer">
              已有账号？<router-link class="auth-reg__link" to="/login">去登录</router-link>
            </div>
          </div>

          <p class="auth-reg__copyright">© 2026 需脉枢纽 · 种子轮 PoC 演示</p>
        </main>
      </div>
    </NConfigProvider>
  </div>
</template>

<style scoped>
@import url("https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap");

.auth-reg {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: var(--color-background);
  font-family: var(--font-family-base);
  -webkit-font-smoothing: antialiased;
}
.auth-reg * { box-sizing: border-box; }
.auth-reg a { text-decoration: none; }
.auth-reg :where(h1, h2, p) { margin: 0; padding: 0; }

.auth-reg__inner {
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
.auth-reg__panel {
  padding: 48px 40px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.auth-reg__title { font-size: 28px; font-weight: 800; color: var(--color-primary); }
.auth-reg__sub { margin-top: 8px; font-size: 15px; color: var(--color-muted-foreground); }
.auth-reg__form { margin-top: 24px; }
.auth-reg__code { display: flex; gap: var(--space-8); width: 100%; }
.auth-reg__submit { margin-top: 4px; }
.auth-reg__footer { margin-top: 20px; text-align: center; font-size: 14px; color: var(--color-muted-foreground); }
.auth-reg__link { color: var(--color-accent); font-weight: 700; cursor: pointer; }
.auth-reg__link:hover { text-decoration: underline; }
.auth-reg__link:focus-visible { outline: 3px solid rgba(3, 105, 161, 0.45); outline-offset: 2px; }
.auth-reg__copyright { margin-top: 24px; text-align: center; font-size: 12px; color: var(--color-muted-foreground); }

@media (max-width: 900px) {
  .auth-reg__inner { grid-template-columns: 1fr; }
  .auth-reg__panel { padding: 32px 24px; }
}
@media (max-width: 375px) {
  .auth-reg { padding: 16px; }
}
@media (prefers-reduced-motion: reduce) {
  .auth-reg *, .auth-reg *::before, .auth-reg *::after { transition-duration: 0.01ms !important; }
}
</style>