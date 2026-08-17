<script setup lang="ts">
/**
 * 00A 注册页（选择角色，原型明确化 §1）：纯角色选择页（COMP-003）。
 * 「我是厂商」→ 01A 厂商注册；「我是采购方」→ 客户注册。
 */
import { useRouter } from "vue-router"
import { NButton } from "naive-ui"

const router = useRouter()
</script>

<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1 class="auth-card__title">注册账号</h1>
      <p class="auth-card__subtitle">选择您的身份开始使用</p>
      <div class="auth-card__roles">
        <NButton type="primary" block size="large" @click="router.push('/vendor/register')">
          我是厂商
        </NButton>
        <NButton block size="large" @click="router.push('/customer/register')">
          我是采购方
        </NButton>
      </div>
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
.auth-card__roles {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-16);
}
.auth-card__footer {
  margin-top: var(--space-16);
  text-align: center;
  font-size: var(--font-size-13);
  color: var(--color-text-secondary);
}
</style>
