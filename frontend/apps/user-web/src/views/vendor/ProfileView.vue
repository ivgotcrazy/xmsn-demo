<script setup lang="ts">
/**
 * 01D 能力档案（只读，独立页）：档案元信息（版本/更新时间/文档数）+ 一句话摘要 + 综合评估（文字）+ Schema 驱动能力字段列表 + 原始文档。
 * 加载骨架屏（COMP-016）。
 */
import { onMounted, ref } from "vue"
import { NSkeleton } from "naive-ui"

import { vendorCapabilityVendorId, type CapabilityOut } from "@xmsn/api"

import VendorCapabilityProfile from "@/components/business/VendorCapabilityProfile.vue"
import { useAuthStore } from "@/stores/auth"

const auth = useAuthStore()
const cap = ref<CapabilityOut | null>(null)
const loading = ref(true)

function fmtTime(iso?: string | null): string {
  if (!iso) return "—"
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return "—"
  const pad = (n: number): string => String(n).padStart(2, "0")
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

onMounted(async () => {
  const vendorId = auth.user?.vendor_id
  try {
    if (vendorId) {
      cap.value = await vendorCapabilityVendorId(vendorId)
    }
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="profile">
    <div class="profile__head">
      <h2>能力档案</h2>
      <div v-if="cap" class="profile__meta">
        <span class="profile__version">v{{ cap.version }}</span>
        <span class="profile__time">更新于 {{ fmtTime(cap.updated_at) }}</span>
        <span class="profile__docs">基于 {{ cap.doc_count }} 份文档</span>
      </div>
    </div>

    <div v-if="loading" class="profile__skeleton">
      <NSkeleton v-for="i in 9" :key="i" height="24px" style="margin-bottom: 12px" />
    </div>

    <VendorCapabilityProfile v-else :capability="cap" />
  </div>
</template>

<style scoped>
.profile {
  width: 100%;
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
.profile__meta {
  display: flex;
  align-items: center;
  gap: var(--space-12);
  font-size: var(--font-size-12);
  color: var(--color-text-secondary);
}
.profile__version {
  font-weight: var(--font-weight-600);
  color: var(--color-primary);
  font-size: var(--font-size-13);
}
.profile__time,
.profile__docs {
  white-space: nowrap;
}
.profile__skeleton {
  padding: var(--space-16);
}
</style>
