<script setup lang="ts">
/**
 * 01A 厂商注册详情（产品 1.1）：企业基本信息 + 营业执照上传。
 */
import { ref } from "vue"
import { useRouter } from "vue-router"
import { NButton, NForm, NFormItem, NInput, NUpload, useMessage, type UploadFileInfo } from "naive-ui"

import { vendorRegister } from "@xmsn/api"

import { uploadFile } from "@/api/upload"

const router = useRouter()
const message = useMessage()

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
    message.success(`企业信息已保存（审核状态：${res.audit_status}）`)
    await router.push("/vendor/dashboard")
  } catch (e) {
    message.error((e as Error).message || "保存失败")
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="register-detail">
    <div class="register-detail__back">
      <NButton text size="small" @click="router.push('/vendor/register')">← 返回上一步</NButton>
    </div>
    <h2>企业基本信息</h2>
    <NForm label-placement="top" class="register-detail__form">
      <NFormItem label="企业名称" required>
        <NInput v-model:value="form.company_name" placeholder="如：东莞某某电子有限公司" />
      </NFormItem>
      <div class="register-detail__row">
        <NFormItem label="所在地">
          <NInput v-model:value="form.location" placeholder="如：广东东莞" />
        </NFormItem>
        <NFormItem label="主营行业">
          <NInput v-model:value="form.main_industry" placeholder="如：消费电子" />
        </NFormItem>
      </div>
      <NFormItem label="统一社会信用代码">
        <NInput v-model:value="form.credit_code" placeholder="18 位信用代码（全局唯一）" />
      </NFormItem>
      <NFormItem label="营业执照（jpg/png/pdf ≤10MB）">
        <NUpload
          accept=".jpg,.jpeg,.png,.pdf"
          :max="1"
          :default-upload="false"
          :file-list="licenseFile ? [licenseFile] : []"
          @change="handleLicenseChange"
        >
          <NButton>选择文件</NButton>
        </NUpload>
      </NFormItem>
      <NButton type="primary" block :loading="loading" @click="submit()">保存并录入能力</NButton>
    </NForm>
  </div>
</template>

<style scoped>
.register-detail {
  max-width: 640px;
  margin: 0 auto;
  padding: var(--space-24);
  background: var(--color-bg-panel);
  border: var(--border-width-1) solid var(--color-border-subtle);
  border-radius: var(--radius-12);
}
.register-detail h2 {
  margin: 0 0 var(--space-24);
  font-size: var(--font-size-18);
}
.register-detail__back {
  display: flex;
  margin-bottom: var(--space-16);
}
.register-detail__back .n-button {
  color: var(--color-text-secondary);
}
.register-detail__back .n-button:hover {
  color: var(--color-accent);
}
.register-detail__row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-16);
}
</style>
