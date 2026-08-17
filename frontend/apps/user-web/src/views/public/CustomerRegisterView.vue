<script setup lang="ts">
/**
 * 客户注册（原型明确化 §1）：00A 选「我是采购方」→ 注册表单 → 直接进入 02A 自动登录。
 */
import { ref } from "vue"
import { useRouter } from "vue-router"
import { NButton, NForm, NFormItem, NInput, useMessage } from "naive-ui"

import { authRegister } from "@xmsn/api"

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
  <div class="auth-page">
    <div class="auth-card">
      <h1 class="auth-card__title">采购方注册</h1>
      <p class="auth-card__subtitle">注册后直接进入需求对话</p>
      <NForm label-placement="top">
        <NFormItem label="手机号">
          <NInput v-model:value="form.phone" placeholder="请输入手机号" />
        </NFormItem>
        <NFormItem label="邮箱（选填）">
          <NInput v-model:value="form.email" placeholder="请输入邮箱" />
        </NFormItem>
        <NFormItem label="验证码">
          <div class="auth-card__code">
            <NInput v-model:value="form.verifyCode" placeholder="验证码" />
            <NButton :disabled="countdown > 0" @click="sendCode()">
              {{ countdown > 0 ? `${countdown}s` : "获取验证码" }}
            </NButton>
          </div>
        </NFormItem>
        <NFormItem label="密码">
          <NInput
            v-model:value="form.password"
            type="password"
            show-password-on="click"
            placeholder="6 位以上密码"
            @keyup.enter="submit()"
          />
        </NFormItem>
      </NForm>
      <NButton type="primary" block :loading="loading" @click="submit()">注 册</NButton>
      <div class="auth-card__footer">
        已有账号？
        <router-link to="/login">去登录</router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
.auth-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: var(--color-bg);
}
.auth-card {
  width: 380px;
  padding: var(--space-32);
  background: var(--color-bg-panel);
  border-radius: var(--radius-16);
  box-shadow: var(--shadow-2);
}
.auth-card__title {
  margin: 0;
  text-align: center;
  font-size: var(--font-size-20);
  color: var(--color-primary);
}
.auth-card__subtitle {
  margin: var(--space-8) 0 var(--space-24);
  text-align: center;
  font-size: var(--font-size-12);
  color: var(--color-text-secondary);
}
.auth-card__code {
  display: flex;
  gap: var(--space-8);
  width: 100%;
}
.auth-card__footer {
  margin-top: var(--space-16);
  text-align: center;
  font-size: var(--font-size-13);
  color: var(--color-text-secondary);
}
</style>
