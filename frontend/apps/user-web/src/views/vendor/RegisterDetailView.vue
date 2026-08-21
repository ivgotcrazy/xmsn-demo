<script setup lang="ts">
/**
 * 01A 厂商注册详情 · 企业基本信息（B2B Service 重设计，对齐 MASTER.md）：
 * 分屏式（AuthBrandPanel 品牌区 + 表单区 theme-b2b），与登录/厂商注册同款 Trust & Authority。
 * 保存后回写 auth.user.vendor_id（否则控制台一直"未完善资料"），进入能力录入。
 */
import { ref } from "vue"
import { useRouter } from "vue-router"
import { NButton, NConfigProvider, NForm, NFormItem, NInput, NUpload, useMessage, type UploadFileInfo } from "naive-ui"

import { vendorRegister } from "@xmsn/api"
import { themeB2bOverrides } from "@xmsn/tokens"

import AuthBrandPanel from "@/components/business/AuthBrandPanel.vue"
import { uploadFile } from "@/api/upload"
import { useAuthStore } from "@/stores/auth"

const router = useRouter()
const message = useMessage()
const auth = useAuthStore()

const form = ref({
  company_name: "",
  location: "",
  main_industry: "",
  credit_code: "",
})
const licenseFile = ref<UploadFileInfo | null>(null)
const licenseId = ref("")
const loading = ref(false)

async function handleLicenseChange(data: { file: UploadFileInfo; fileList: UploadFileInfo[] }): Promise<void> {
  const file = data.fileList[0] ?? data.file
  licenseFile.value = file ?? null
  if (file?.file) {
    try {
      const res = await uploadFile(file.file)
      licenseId.value = res.file_id
      message.success("营业执照上传成功")
    } catch {
      message.error("上传失败")
    }
  }
}

async function submit(): Promise<void> {
  if (!form.value.company_name) {
    message.warning("请填写企业名称")
    return
  }
  loading.value = true
  try {
    const res = await vendorRegister({
      company_name: form.value.company_name,
      location: form.value.location || undefined,
      main_industry: form.value.main_industry || undefined,
      credit_code: form.value.credit_code || undefined,
      license_file_id: licenseId.value || undefined,
    })
    // 关键：把厂商档案 id 回写到当前用户并持久化，否则控制台一直"未完善资料"
    auth.updateUser({ vendor_id: res.vendor_id })
    message.success(`企业信息已保存（审核状态：${res.audit_status}）`)
    await router.push("/vendor/capability")
  } catch (e) {
    message.error((e as Error).message || "保存失败")
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
            <router-link class="auth-reg__back" to="/vendor/register">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M19 12H5M12 19l-7-7 7-7" /></svg>
              返回上一步
            </router-link>
            <h2 class="auth-reg__title">企业基本信息</h2>
            <p class="auth-reg__sub">完善企业信息，通过审核后进入代工匹配池</p>

            <NForm class="auth-reg__form" label-placement="top">
              <NFormItem label="企业名称" required>
                <NInput v-model:value="form.company_name" size="large" placeholder="如：东莞某某电子有限公司" :input-props="{ autocomplete: 'organization' }" />
              </NFormItem>
              <div class="regdetail__row">
                <NFormItem label="所在地">
                  <NInput v-model:value="form.location" size="large" placeholder="如：广东东莞" />
                </NFormItem>
                <NFormItem label="主营行业">
                  <NInput v-model:value="form.main_industry" size="large" placeholder="如：消费电子" />
                </NFormItem>
              </div>
              <NFormItem label="统一社会信用代码">
                <NInput v-model:value="form.credit_code" size="large" placeholder="18 位信用代码（全局唯一）" />
              </NFormItem>
              <NFormItem label="营业执照（jpg/png/pdf ≤10MB）">
                <NUpload
                  accept=".jpg,.jpeg,.png,.pdf"
                  :max="1"
                  :default-upload="false"
                  :file-list="licenseFile ? [licenseFile] : []"
                  @change="handleLicenseChange"
                >
                  <NButton size="large">选择文件</NButton>
                </NUpload>
              </NFormItem>
            </NForm>

            <NButton class="auth-reg__submit" type="primary" block size="large" :loading="loading" @click="submit()">
              保存并录入能力
            </NButton>

            <div class="auth-reg__footer">
              已有账号？<router-link class="auth-reg__link" to="/login">去登录</router-link>
            </div>
          </div>

          <p class="auth-reg__copyright">© 2026 需脉枢纽</p>
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
.auth-reg__back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 16px;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-accent);
  cursor: pointer;
  transition: color 200ms ease;
}
.auth-reg__back svg { width: 16px; height: 16px; }
.auth-reg__back:hover { text-decoration: underline; }
.auth-reg__back:focus-visible { outline: 3px solid rgba(3, 105, 161, 0.45); outline-offset: 2px; }
.auth-reg__title { font-size: 28px; font-weight: 800; color: var(--color-primary); }
.auth-reg__sub { margin-top: 8px; font-size: 15px; color: var(--color-muted-foreground); }
.auth-reg__form { margin-top: 24px; }
.auth-reg__submit { margin-top: 4px; }
.auth-reg__footer { margin-top: 20px; text-align: center; font-size: 14px; color: var(--color-muted-foreground); }
.auth-reg__link { color: var(--color-accent); font-weight: 700; cursor: pointer; }
.auth-reg__link:hover { text-decoration: underline; }
.auth-reg__link:focus-visible { outline: 3px solid rgba(3, 105, 161, 0.45); outline-offset: 2px; }
.auth-reg__copyright { margin-top: 24px; text-align: center; font-size: 12px; color: var(--color-muted-foreground); }

.regdetail__row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }

@media (max-width: 900px) {
  .auth-reg__inner { grid-template-columns: 1fr; }
  .auth-reg__panel { padding: 32px 24px; }
}
@media (max-width: 640px) {
  .regdetail__row { grid-template-columns: 1fr; }
}
@media (max-width: 375px) {
  .auth-reg { padding: 16px; }
}
@media (prefers-reduced-motion: reduce) {
  .auth-reg *, .auth-reg *::before, .auth-reg *::after { transition-duration: 0.01ms !important; }
}
</style>
