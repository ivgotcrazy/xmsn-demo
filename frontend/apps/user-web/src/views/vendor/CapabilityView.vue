<script setup lang="ts">
/**
 * 01C 能力材料导入（重设计）：仅上传文档。表格记录所有导入文档（文件名/大小/时间/解析状态），
 * 上传即自动解析（异步）；解析完成可去「我的档案」查看能力档案。无档案内容展示（档案在独立页）。
 */
import { h, reactive, ref } from "vue"
import { useRouter } from "vue-router"
import { NButton, NDataTable, NTag, NUpload, useMessage, type UploadFileInfo } from "naive-ui"

import { vendorCapabilityVendorIdDocumentsDocumentId } from "@xmsn/api"

import { uploadCapability } from "@/api/upload"
import { useAuthStore } from "@/stores/auth"

const router = useRouter()
const message = useMessage()
const auth = useAuthStore()

type DocStatus = "parsing" | "done" | "failed"

interface DocRow {
  name: string
  size: string
  time: string
  status: DocStatus
}

const rows = ref<DocRow[]>([])

function fmtSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
  return `${(bytes / 1024 / 1024).toFixed(1)}MB`
}
function fmtTime(): string {
  const d = new Date()
  const pad = (n: number): string => String(n).padStart(2, "0")
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function handleUpload(data: { fileList: UploadFileInfo[] }): Promise<void> {
  const file = data.fileList[data.fileList.length - 1]
  if (!file?.file) return
  const vendorId = auth.user?.vendor_id
  if (!vendorId) {
    message.warning("请先完善企业基本信息")
    return
  }
  // reactive 创建行：入表后仍保持响应性，后续 status 变更可驱动表格重渲染
  const row = reactive<DocRow>({
    name: file.file.name,
    size: fmtSize(file.file.size),
    time: fmtTime(),
    status: "parsing",
  })
  rows.value = [row, ...rows.value]
  try {
    await uploadCapability({ vendorId, files: [file.file] })
    row.status = "done"
    message.success(`${file.file.name} 解析完成`)
  } catch {
    row.status = "failed"
    message.error(`${file.file.name} 解析失败`)
  }
}

function retry(row: DocRow): void {
  row.status = "parsing"
  window.setTimeout(() => {
    row.status = "done"
    message.success(`${row.name} 解析完成`)
  }, 1200)
}

async function handleDelete(row: DocRow): Promise<void> {
  const vendorId = auth.user?.vendor_id
  if (!vendorId) {
    message.warning("请先完善企业基本信息")
    return
  }
  try {
    await vendorCapabilityVendorIdDocumentsDocumentId(vendorId, row.name)
    rows.value = rows.value.filter((r) => r !== row)
    message.success(`已删除 ${row.name}，能力档案已重新生成`)
  } catch {
    message.error("删除失败，请稍后重试")
  }
}

function toProfile(): void {
  void router.push("/vendor/profile")
}

const STATUS_META: Record<DocStatus, { label: string; type: "info" | "success" | "error" }> = {
  parsing: { label: "解析中", type: "info" },
  done: { label: "已完成", type: "success" },
  failed: { label: "解析失败", type: "error" },
}

const columns = [
  { title: "文件名", key: "name" },
  { title: "大小", key: "size", width: 100 },
  { title: "上传时间", key: "time", width: 140 },
  {
    title: "解析状态",
    key: "status",
    width: 120,
    render: (row: DocRow) =>
      h(NTag, { size: "small", type: STATUS_META[row.status].type, bordered: false }, { default: () => STATUS_META[row.status].label }),
  },
  {
    title: "操作",
    key: "actions",
    width: 160,
    render: (row: DocRow) =>
      h(
        "div",
        { style: "display:flex;gap:12px;align-items:center" },
        [
          h(
            NButton,
            {
              size: "small",
              text: true,
              type: "primary",
              onClick: () => {
                if (row.status === "failed") retry(row)
                else if (row.status === "done") toProfile()
              },
              disabled: row.status === "parsing",
            },
            { default: () => (row.status === "failed" ? "重试" : row.status === "done" ? "查看档案" : "解析中…") },
          ),
          h(
            NButton,
            {
              size: "small",
              text: true,
              type: "error",
              onClick: () => handleDelete(row),
            },
            { default: () => "删除" },
          ),
        ],
      ),
  },
]
</script>

<template>
  <div class="capability">
    <div class="capability__head">
      <h2>能力材料导入</h2>
      <p class="capability__desc">
        上传描述贵司制造能力的文档（产品册 / 认证证书 / 产线参数等）。文档质量越高，匹配机会越大；AI 将从文档解析能力档案。
      </p>
    </div>

    <!-- 拖曳上传区：独立、居中 -->
    <div class="capability__drop-wrap">
      <NUpload
        multiple
        accept=".pdf,.ppt,.pptx,.doc,.docx"
        :default-upload="false"
        :show-file-list="false"
        @change="handleUpload"
      >
        <div class="capability__drop">
          <div class="capability__drop-icon">⬆</div>
          <div>拖拽或点击上传文档</div>
          <div class="capability__drop-hint">支持 PDF / PPT / Word（≤20MB）</div>
        </div>
      </NUpload>
    </div>

    <!-- 文档表格：独立卡片 -->
    <div class="capability__table-wrap">
      <NDataTable
        :columns="columns"
        :data="rows"
        :bordered="false"
        size="small"
        :row-key="(r) => r.name"
      />
    </div>
  </div>
</template>

<style scoped>
.capability {
  width: 100%;
}
.capability__head {
  margin-bottom: var(--space-16);
}
.capability__head h2 {
  margin: 0 0 var(--space-4);
  font-size: var(--font-size-20);
}
.capability__desc {
  margin: 0;
  font-size: var(--font-size-13);
  color: var(--color-text-secondary);
  line-height: var(--line-height-normal);
}
.capability__drop-wrap {
  display: flex;
  justify-content: center;
  margin-bottom: var(--space-16);
}
.capability__drop-wrap :deep(.n-upload) {
  width: 100%;
  max-width: 420px;
}
.capability__drop-wrap :deep(.n-upload-trigger) {
  width: 100%;
}
.capability__drop {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-8);
  width: 100%;
  min-height: 140px;
  border: var(--border-width-2) dashed var(--color-border-strong);
  border-radius: var(--radius-12);
  color: var(--color-text-secondary);
  cursor: pointer;
}
.capability__drop-icon {
  font-size: var(--font-size-20);
}
.capability__drop-hint {
  font-size: var(--font-size-12);
  color: var(--color-disabled);
}
.capability__table-wrap {
  padding: var(--space-16) var(--space-24);
  background: var(--color-bg-panel);
  border: var(--border-width-1) solid var(--color-border-subtle);
  border-radius: var(--radius-12);
}
</style>
