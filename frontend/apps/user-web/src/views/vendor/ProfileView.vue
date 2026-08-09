<script setup lang="ts">
/**
 * 01D 能力档案（只读，原型三栏）：左"原始输入" / 中"AI提取的结构化标签" / 右"一句话能力摘要"。
 * 顶部状态徽标；底部仅"返回控制台"；加载骨架屏（COMP-016）。
 */
import { onMounted, ref } from "vue"
import { useRouter } from "vue-router"
import { NButton, NSkeleton, NTag } from "naive-ui"

import { vendorCapabilityVendorId, type CapabilityOut } from "@xmsn/api"

const router = useRouter()
const cap = ref<CapabilityOut | null>(null)
const loading = ref(true)

const TAG_LABEL: Record<string, string> = {
  product_types: "产品类型",
  process_types: "工艺",
  certifications: "认证",
  os_support: "操作系统",
  interfaces: "接口",
  min_order_qty: "起订量",
  lead_time_days: "交期(天)",
  application_scenarios: "应用场景",
}

function display(v: unknown): string {
  return Array.isArray(v) ? v.join("、") : String(v ?? "")
}

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

    <div v-else-if="cap" class="profile__cols">
      <!-- 左栏：原始输入 -->
      <section class="profile__col">
        <h3>原始输入</h3>
        <div class="profile__source">
          <div class="profile__source-title">表单摘要</div>
          <div class="profile__source-text">见中栏结构化标签（来源：表单）</div>
          <div v-if="cap.raw_text" class="profile__source-title">文本片段</div>
          <p v-if="cap.raw_text" class="profile__source-text">{{ cap.raw_text }}</p>
          <div v-if="cap.doc_urls?.length" class="profile__source-title">文档</div>
          <ul v-if="cap.doc_urls?.length" class="profile__source-list">
            <li v-for="d in cap.doc_urls" :key="d">{{ d }}</li>
          </ul>
        </div>
      </section>

      <!-- 中栏：AI 提取的结构化标签（只读） -->
      <section class="profile__col">
        <h3>AI 提取的结构化标签</h3>
        <div class="profile__tags">
          <div v-for="(v, k) in cap.structured_tags" :key="k" class="profile__tag" title="来源：表单 / 文本 / 文档">
            <span class="profile__k">{{ TAG_LABEL[k] ?? k }}</span>
            <span class="profile__v">{{ display(v) }}</span>
          </div>
        </div>
      </section>

      <!-- 右栏：一句话能力摘要 -->
      <section class="profile__col">
        <h3>一句话能力摘要</h3>
        <p class="profile__summary">{{ cap.summary_text }}</p>
      </section>
    </div>

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
.profile__cols {
  display: grid;
  grid-template-columns: 2fr 3fr 2fr;
  gap: var(--space-16);
  align-items: start;
}
.profile__col {
  background: var(--color-bg-panel);
  border: var(--border-width-1) solid var(--color-border-subtle);
  border-radius: var(--radius-12);
  padding: var(--space-16);
}
.profile__col h3 {
  margin: 0 0 var(--space-12);
  font-size: var(--font-size-15);
  font-weight: var(--font-weight-600);
}
.profile__source-title {
  margin-top: var(--space-12);
  font-size: var(--font-size-13);
  color: var(--color-text-secondary);
}
.profile__source-text {
  margin: var(--space-4) 0 0;
  font-size: var(--font-size-13);
  line-height: var(--line-height-normal);
  word-break: break-all;
}
.profile__source-list {
  margin: var(--space-4) 0 0;
  padding-left: var(--space-16);
  font-size: var(--font-size-13);
}
.profile__tags {
  display: flex;
  flex-direction: column;
  gap: var(--space-8);
}
.profile__tag {
  display: flex;
  justify-content: space-between;
  gap: var(--space-16);
  padding: var(--space-8) var(--space-12);
  background: var(--color-bg);
  border-radius: var(--radius-8);
}
.profile__k {
  color: var(--color-text-secondary);
}
.profile__v {
  font-weight: var(--font-weight-500);
}
.profile__summary {
  margin: 0;
  line-height: var(--line-height-loose);
  font-size: var(--font-size-14);
}
.profile__actions {
  margin-top: var(--space-24);
}
</style>
