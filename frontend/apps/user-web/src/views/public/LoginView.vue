<script setup lang="ts">
/**
 * 00B 登录（产品 1.1/2.1）：手机号 + 密码；成功后按角色跳转。
 */
import { ref } from "vue"
import { useRoute, useRouter } from "vue-router"
import { NButton, NForm, NFormItem, NInput, useMessage } from "naive-ui"

import { authLogin } from "@xmsn/api"

import { useAuthStore } from "@/stores/auth"

const router = useRouter()
const route = useRoute()
const message = useMessage()
const auth = useAuthStore()

const form = ref({ phone: "13900000001", password: "123456" })
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
  <div class="auth-page">
    <div class="auth-card">
      <h1 class="auth-card__title">需脉枢纽</h1>
      <p class="auth-card__subtitle">B2B 代工制造供需智能匹配平台</p>
      <NForm label-placement="top">
        <NFormItem label="手机号">
          <NInput v-model:value="form.phone" placeholder="请输入手机号" />
        </NFormItem>
        <NFormItem label="密码">
          <NInput v-model:value="form.password" type="password" show-password-on="click" placeholder="请输入密码" @keyup.enter="submit()" />
        </NFormItem>
      </NForm>
      <NButton type="primary" block :loading="loading" @click="submit()">登 录</NButton>
      <div class="auth-card__footer">
        还没有账号？
        <router-link to="/register">立即注册</router-link>
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
.auth-card__footer {
  margin-top: var(--space-16);
  text-align: center;
  font-size: var(--font-size-13);
  color: var(--color-text-secondary);
}
</style>
