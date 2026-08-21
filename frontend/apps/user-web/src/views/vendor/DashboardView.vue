<script setup lang="ts">
/**
 * 01B 厂商控制台（原型明确化 §4）：企业信息 + 审核状态 + 未完善资料 / 已通过 X 条能力+摘要。
 */
import { onMounted, ref } from "vue"
import { useRouter } from "vue-router"
import { NButton, NCard, NSpin, useMessage } from "naive-ui"

import { vendorCapabilityVendorId, vendorVendorId, type CapabilityOut, type VendorOut } from "@xmsn/api"

import VendorInfoCard from "@/components/vendor/VendorInfoCard.vue"
import { useAuthStore } from "@/stores/auth"

const router = useRouter()
const message = useMessage()
const auth = useAuthStore()
const vendor = ref<VendorOut | null>(null)
const cap = ref<CapabilityOut | null>(null)
const loading = ref(true)

onMounted(async () => {
  const vendorId = auth.user?.vendor_id
  if (!vendorId) {
    loading.value = false
    return
  }
  try {
    vendor.value = await vendorVendorId(vendorId)
    // 能力档案可能尚未创建（新厂商）→ 接口 404 视为"无能力"，不阻断控制台
    try {
      cap.value = await vendorCapabilityVendorId(vendorId)
    } catch {
      cap.value = null
    }
  } catch {
    message.error("加载厂商信息失败")
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <NSpin :show="loading">
    <div class="dashboard">
      <template v-if="vendor">
      <VendorInfoCard :vendor="vendor" />

      <!-- 原型明确化 §4：未完善资料 提示卡 -->
      <div v-if="!cap" class="dashboard__empty">
        <h3>未完善资料</h3>
        <p>您还未录入制造能力，能力档案生成后经审核进入匹配池。</p>
        <NButton type="primary" @click="router.push('/vendor/capability')">立即录入能力</NButton>
      </div>

      <!-- 能力概要在「能力档案」页查看，控制台不展示摘要 -->
      <div v-else-if="vendor.audit_status !== 'passed'" class="dashboard__tip">
        企业资料待审核，通过后能力进入匹配池。
      </div>

      <div class="dashboard__cards">
        <NCard title="制造能力" class="dashboard__card">
          <p>录入贵司的制造能力（产品类型 / 工艺 / 认证 / OS 等），经审核后进入匹配候选池。</p>
          <NButton type="primary" @click="router.push('/vendor/capability')">录入能力</NButton>
        </NCard>
        <NCard title="能力档案" class="dashboard__card">
          <p>查看已生成的能力档案（只读，不可编辑）。</p>
          <NButton @click="router.push('/vendor/profile')">查看档案</NButton>
        </NCard>
      </div>
      </template>
      <!-- 厂商账号已建但未填企业资料（无 vendor_id） -->
      <div v-else class="dashboard__empty">
        <h3>未完善资料</h3>
        <p>您还未录入企业基本信息与制造能力，完善并通过审核后进入匹配池。</p>
        <NButton type="primary" @click="router.push('/vendor/register/company')">去完善企业信息</NButton>
      </div>
    </div>
  </NSpin>
</template>

<style scoped>
.dashboard__tip {
  padding: var(--space-12) var(--space-16);
  background: var(--color-primary-bg);
  color: var(--color-primary-text);
  border-radius: var(--radius-8);
  margin-bottom: var(--space-24);
}
.dashboard__empty {
  padding: var(--space-24);
  background: var(--color-warning-bg);
  border: var(--border-width-1) solid var(--color-warning);
  border-radius: var(--radius-8);
  margin-bottom: var(--space-24);
}
.dashboard__empty h3 {
  margin: 0 0 var(--space-8);
  font-size: var(--font-size-16);
  color: var(--color-warning-text);
}
.dashboard__empty p {
  margin: 0 0 var(--space-12);
  color: var(--color-text-secondary);
}
.dashboard__cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-16);
}
</style>
