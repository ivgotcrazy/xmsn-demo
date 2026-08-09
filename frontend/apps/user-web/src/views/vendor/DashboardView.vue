<script setup lang="ts">
/**
 * 01B 厂商控制台（原型明确化 §4）：企业信息 + 审核状态 + 未完善资料 / 已通过 X 条能力+摘要。
 */
import { computed, onMounted, ref } from "vue"
import { useRouter } from "vue-router"
import { NButton, NCard, NSpin, NTag } from "naive-ui"

import { vendorCapabilityVendorId, vendorVendorId, type CapabilityOut, type VendorOut } from "@xmsn/api"

import { AUDIT_META, type AuditStatus } from "@xmsn/types"

const router = useRouter()
const vendor = ref<VendorOut | null>(null)
const cap = ref<CapabilityOut | null>(null)
const loading = ref(true)
const auditMeta = computed(() => AUDIT_META[(vendor.value?.audit_status ?? "pending") as AuditStatus])
const capabilityCount = computed(() => (cap.value ? 1 : 0))

onMounted(async () => {
  try {
    const [v, c] = await Promise.all([
      vendorVendorId("v-001"),
      vendorCapabilityVendorId("v-001"),
    ])
    vendor.value = v
    cap.value = c
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <NSpin :show="loading">
    <div class="dashboard" v-if="vendor">
      <div class="dashboard__head">
        <div>
          <h2>{{ vendor.company_name }}</h2>
          <div class="dashboard__meta">
            {{ vendor.location ?? "—" }} · {{ vendor.main_industry ?? "—" }}
          </div>
        </div>
        <NTag size="large" :type="auditMeta.tagType" :bordered="false">
          {{ auditMeta.label }}
        </NTag>
      </div>

      <!-- 原型明确化 §4：未完善资料 提示卡 -->
      <div v-if="!cap" class="dashboard__empty">
        <h3>未完善资料</h3>
        <p>您还未录入制造能力，能力档案生成后经审核进入匹配池。</p>
        <NButton type="primary" @click="router.push('/vendor/capability')">立即录入能力</NButton>
      </div>

      <!-- 原型明确化 §4：已通过 X 条能力 + 一句话摘要 -->
      <div v-else-if="vendor.audit_status === 'passed'" class="dashboard__tip">
        已通过 {{ capabilityCount }} 条能力：{{ cap?.summary_text }}
      </div>
      <div v-else class="dashboard__tip">
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
    </div>
  </NSpin>
</template>

<style scoped>
.dashboard__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-16);
}
.dashboard__head h2 {
  margin: 0;
  font-size: var(--font-size-20);
}
.dashboard__meta {
  margin-top: var(--space-4);
  color: var(--color-text-secondary);
  font-size: var(--font-size-13);
}
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
