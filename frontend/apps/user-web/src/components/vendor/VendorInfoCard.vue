<script setup lang="ts">
/**
 * 控制台 · 厂商基本信息卡（B2B Service / MASTER.md）
 * 只读展示：企业基本信息 + 审核状态徽章 + 能力概览 + 入驻时间。
 * 根元素加 .theme-b2b 使用 MASTER 语义 token（藏青 #0F172A + 蓝 CTA #0369A1 + Plus Jakarta Sans）。
 */
import { computed } from "vue"

import { AUDIT_META, type AuditStatus } from "@xmsn/types"
import type { VendorOut } from "@xmsn/api"

const props = defineProps<{
  vendor: VendorOut
}>()

const audit = computed(() => AUDIT_META[(props.vendor.audit_status ?? "pending") as AuditStatus])

const createdDate = computed(() => {
  if (!props.vendor.created_at) return "—"
  const d = new Date(props.vendor.created_at)
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleDateString("zh-CN")
})
</script>

<template>
  <section class="vendor-info theme-b2b" aria-label="厂商基本信息">
    <header class="vendor-info__head">
      <h2 class="vendor-info__title">厂商基本信息</h2>
      <span class="vendor-info__badge" :class="`is-${vendor.audit_status ?? 'pending'}`">{{ audit.label }}</span>
    </header>

    <dl class="vendor-info__grid">
      <div class="vendor-info__field">
        <dt>企业名称</dt>
        <dd class="vendor-info__strong">{{ vendor.company_name }}</dd>
      </div>
      <div class="vendor-info__field">
        <dt>所在地</dt>
        <dd>{{ vendor.location || "—" }}</dd>
      </div>
      <div class="vendor-info__field">
        <dt>主营行业</dt>
        <dd>{{ vendor.main_industry || "—" }}</dd>
      </div>
      <div class="vendor-info__field">
        <dt>统一社会信用代码</dt>
        <dd>
          <template v-if="vendor.credit_code">{{ vendor.credit_code }}</template>
          <template v-else>
            <span class="vendor-info__placeholder">—</span>
            <span class="vendor-info__hint">补齐后进入匹配池</span>
          </template>
        </dd>
      </div>
    </dl>

    <footer class="vendor-info__foot">入驻时间 {{ createdDate }}</footer>
  </section>
</template>

<style scoped>
.vendor-info {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  box-shadow: var(--shadow-md);
  padding: var(--space-lg);
  margin-bottom: var(--space-lg);
  font-family: var(--font-family-base);
}
.vendor-info__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
}
.vendor-info__title {
  margin: 0;
  font-size: 17px;
  font-weight: 800;
  color: var(--color-primary);
}
.vendor-info__badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
  border: 1px solid;
}
.vendor-info__badge.is-pending { background: #fff7ed; color: #c2410c; border-color: #fdba74; }
.vendor-info__badge.is-passed { background: #f0fdf4; color: #15803d; border-color: #86efac; }
.vendor-info__badge.is-rejected { background: #fef2f2; color: #b91c1c; border-color: #fca5a5; }

.vendor-info__grid {
  margin: var(--space-lg) 0 0;
  padding: 0;
  list-style: none;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-md) var(--space-lg);
}
.vendor-info__field dt {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-muted-foreground);
  margin-bottom: 4px;
}
.vendor-info__field dd {
  margin: 0;
  font-size: 15px;
  color: var(--color-foreground);
}
.vendor-info__strong { font-size: 16px; font-weight: 700; }
.vendor-info__placeholder { color: var(--color-muted-foreground); }
.vendor-info__hint {
  display: inline-block;
  margin-left: 8px;
  font-size: 13px;
  color: var(--color-accent);
}

.vendor-info__foot {
  margin-top: var(--space-md);
  font-size: 13px;
  color: var(--color-muted-foreground);
}

@media (max-width: 640px) {
  .vendor-info__grid { grid-template-columns: 1fr; }
}
</style>
