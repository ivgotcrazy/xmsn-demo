<script setup lang="ts">
/**
 * 03A 管理员登录：手机号/密码 → 校验 admin 角色 → 后台首页。
 */
import { ref } from "vue"
import { useRouter } from "vue-router"
import { NButton, NForm, NFormItem, NInput, useMessage } from "naive-ui"

import { authLogin } from "@xmsn/api"

import { useAuthStore } from "@/stores/auth"

const router = useRouter()
const message = useMessage()
const auth = useAuthStore()

const form = ref({ phone: "13800000000", password: "123456" })
const loading = ref(false)

async function submit(): Promise<void> {
  loading.value = true
  try {
    const res = await authLogin({ phone: form.value.phone, password: form.value.password })
    if (res.user.role !== "admin") {
      message.error("该账号无管理员权限")
      return
    }
    auth.setAuth(res.access_token, res.user)
    await router.push("/admin/dashboard")
  } catch (e) {
    message.error((e as Error).message || "登录失败")
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="admin-login">
    <div class="admin-login__card">
      <h1>需脉枢纽 · 管理后台</h1>
      <NForm label-placement="top">
        <NFormItem label="管理员账号">
          <NInput v-model:value="form.phone" placeholder="请输入管理员手机号" />
        </NFormItem>
        <NFormItem label="密码">
          <NInput v-model:value="form.password" type="password" show-password-on="click" @keyup.enter="submit()" />
        </NFormItem>
      </NForm>
      <NButton type="primary" block :loading="loading" @click="submit()">登 录</NButton>
    </div>
  </div>
</template>

<style scoped>
.admin-login {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: var(--color-bg);
}
.admin-login__card {
  width: 360px;
  padding: var(--space-32);
  background: var(--color-bg-panel);
  border-radius: var(--radius-16);
  box-shadow: var(--shadow-2);
}
.admin-login__card h1 {
  margin: 0 0 var(--space-24);
  text-align: center;
  font-size: var(--font-size-18);
  color: var(--color-primary);
}
</style>
