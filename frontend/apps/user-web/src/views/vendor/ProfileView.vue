<script setup lang="ts">
/**
 * 01D 能力档案（只读，原型三栏）：左"原始输入" / 中"AI提取的结构化标签" / 右"一句话能力摘要"。
 * 顶部状态徽标；底部仅"返回控制台"；加载骨架屏（COMP-016）。
 */
import { onMounted, ref } from "vue"
import { useRouter } from "vue-router"
import { NButton, NSkeleton, NTag } from "naive-ui"

import { vendorCapabilityVendorId, type CapabilityOut } from "@xmsn/api"

import VendorCapabilityProfile from "@/components/business/VendorCapabilityProfile.vue"

const router = useRouter()
const cap = ref<CapabilityOut | null>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    cap.value = await vendorCapabilityVendorId("v-001")
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="profile">
    <div class="profile__head">
      <h2>能力档案</h2>
      <NTag v-if="cap" :type="cap.audit_status === 'passed' ? 'success' : 'warning'" :bordered="false">
        {{ cap.audit_status === "passed" ? "已通过" : "审核中" }}
      </NTag>
    </div>

    <div v-if="loading" class="profile__skeleton">
      <NSkeleton v-for="i in 9" :key="i" height="24px" style="margin-bottom: 12px" />
    </div>

    <VendorCapabilityProfile v-else :capability="cap" />

    <div class="profile__actions">
      <NButton @click="router.push('/vendor/dashboard')">返回控制台</NButton>
    </div>
  </div>
</template>

<style scoped>
.profile {
  max-width: 960px;
}
.profile__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-24);
}
.profile__head h2 {
  margin: 0;
  font-size: var(--font-size-20);
}
.profile__skeleton {
  padding: var(--space-16);
}
.profile__actions {
  margin-top: var(--space-24);
}
</style>
