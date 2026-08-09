<script setup lang="ts">
/**
 * 01C 能力录入（原型三步向导）：
 * Step1 模板化表单 + 设备清单动态表格（COMP-010）
 * Step2 自由文本 + 常用模板侧边栏（COMP-011/013）
 * Step3 文档上传 + 解析进度提示 → 提交材料生成档案
 */
import { computed, ref } from "vue"
import { useRouter } from "vue-router"
import {
  NButton,
  NDrawer,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NSelect,
  NUpload,
  useMessage,
  type UploadFileInfo,
} from "naive-ui"

import { REQUEST_SCHEMA_FIELDS, type ParamKey } from "@xmsn/types"

import { uploadCapability } from "@/api/upload"

// 步骤条（COMP-008）自研：规避 naive NSteps.Step 嵌套组件在 script setup 下的渲染问题
const steps = [
  { title: "结构化表单", description: "选择制造能力" },
  { title: "自由文本", description: "补充说明" },
  { title: "文档上传", description: "产能介绍等" },
]

const router = useRouter()
const message = useMessage()

const OPTIONS: Partial<Record<ParamKey, { label: string; value: string }[]>> = {
  product_type: ["机顶盒", "智能音箱", "IoT设备", "其他"].map((v) => ({ label: v, value: v })),
  os_support: ["Linux", "Android", "RTOS", "HarmonyOS"].map((v) => ({ label: v, value: v })),
  certifications: ["ISO9001", "ISO14001", "ISO13485", "CE", "FCC"].map((v) => ({ label: v, value: v })),
  application_scenes: ["家庭娱乐", "智能家居", "工业控制", "医疗", "车载"].map((v) => ({ label: v, value: v })),
  interfaces: ["网口", "USB", "HDMI", "GPIO", "蓝牙", "WiFi"].map((v) => ({ label: v, value: v })),
  process: ["SMT贴片", "组装测试", "整机包装", "模具注塑"].map((v) => ({ label: v, value: v })),
}

const current = ref(0)
const formData = ref<Record<string, unknown>>({})
const freeText = ref("")
const files = ref<UploadFileInfo[]>([])

// 设备清单（COMP-010 动态表格：可增删行）
const deviceRows = ref<{ name: string; qty: number | null }[]>([])
function addDeviceRow(): void {
  deviceRows.value.push({ name: "", qty: null })
}
function removeDeviceRow(i: number): void {
  deviceRows.value.splice(i, 1)
}

// 常用模板（COMP-013 侧边栏）
const templateOpen = ref(false)
const templates = [
  "我们是一家专注于消费电子的制造商，拥有 8 条 SMT 贴片线与组装测试一体化车间，月产能 50 万台，支持 Linux/Android 双系统定制，已通过 ISO9001/ISO14001 认证。",
  "主要工艺包括：SMT 贴片、组装测试、整机包装；关键设备：高速贴片机、AOI 检测仪、老化测试线。",
  "主要产品类型：机顶盒、智能音箱、IoT 设备；支持接口：网口、USB、HDMI、蓝牙、WiFi。",
]
function insertTemplate(t: string): void {
  freeText.value = freeText.value ? `${freeText.value}\n${t}` : t
  templateOpen.value = false
}

// 上传解析状态（原型：解析完成显示"已解析，提取到N条记录"）
const parsedCount = ref<number | null>(null)

// 预生成字段 v-model 模型：避免模板中的类型断言（Vue 模板不支持 as）
const fieldModels = {} as Record<string, { value: any }>
for (const f of REQUEST_SCHEMA_FIELDS) {
  fieldModels[f.key] = computed({
    get: () => formData.value[f.key],
    set: (v: unknown) => {
      formData.value[f.key] = v
    },
  })
}

async function handleUpload(data: { fileList: UploadFileInfo[] }): Promise<void> {
  files.value = data.fileList
  if (data.fileList.length) {
    parsedCount.value = data.fileList.length * 6
    window.setTimeout(() => {
      parsedCount.value = null
    }, 4000)
  } else {
    parsedCount.value = null
  }
}

async function submit(): Promise<void> {
  const realFiles = files.value
    .map((f) => f.file)
    .filter((f): f is File => f !== null && f !== undefined)
  try {
    const res = await uploadCapability({
      vendorId: "v-001",
      formData: formData.value,
      freeText: freeText.value || undefined,
      files: realFiles,
    })
    message.success("能力档案已生成，等待审核")
    await router.push("/vendor/profile")
  } catch (e) {
    message.error((e as Error).message || "提交失败")
  }
}
</script>

<template>
  <div class="capability">
    <div class="capability__steps">
      <div
        v-for="(s, i) in steps"
        :key="s.title"
        class="capability__step"
        :class="{ 'is-current': i === current, 'is-done': i < current }"
      >
        <div class="capability__step-dot">{{ i < current ? "✓" : i + 1 }}</div>
        <div class="capability__step-text">
          <div class="capability__step-title">{{ s.title }}</div>
          <div class="capability__step-desc">{{ s.description }}</div>
        </div>
      </div>
    </div>

    <div class="capability__panel">
      <!-- Step 1：模板化表单 + 设备清单 -->
      <template v-if="current === 0">
        <NForm label-placement="top">
          <div class="capability__grid">
            <NFormItem v-for="f in REQUEST_SCHEMA_FIELDS" :key="f.key" :label="f.label">
              <NSelect
                v-if="f.kind === 'multi' && OPTIONS[f.key]"
                v-model:value="fieldModels[f.key].value"
                multiple
                clearable
                :options="OPTIONS[f.key]"
                placeholder="可多选"
              />
              <NInputNumber
                v-else-if="f.kind === 'number'"
                v-model:value="fieldModels[f.key].value"
                :min="0"
                :placeholder="f.key === 'min_order_qty' ? '起订量' : '交期(天)'"
                style="width: 100%"
              />
              <NInput
                v-else
                v-model:value="fieldModels[f.key].value"
                :placeholder="`填写${f.label}`"
              />
            </NFormItem>
          </div>
        </NForm>

        <section class="capability__devices">
          <div class="capability__devices-head">
            <h4>设备清单</h4>
            <NButton size="small" dashed @click="addDeviceRow()">+ 添加设备</NButton>
          </div>
          <div v-for="(r, i) in deviceRows" :key="i" class="capability__device-row">
            <NInput v-model:value="r.name" placeholder="设备名称，如：高速贴片机" />
            <NInputNumber v-model:value="r.qty" :min="0" placeholder="数量" style="width: 120px" />
            <NButton size="small" quaternary type="error" @click="removeDeviceRow(i)">删除</NButton>
          </div>
        </section>

        <div class="capability__actions">
          <NButton type="primary" @click="current = 1">下一步</NButton>
        </div>
      </template>

      <!-- Step 2：自由文本 + 常用模板 -->
      <template v-else-if="current === 1">
        <div class="capability__toolbar">
          <NButton size="small" @click="templateOpen = true">插入常用模板</NButton>
        </div>
        <NInput
          v-model:value="freeText"
          type="textarea"
          :rows="8"
          placeholder="用自然语言补充描述贵司制造能力，如产线配置、产能、擅长的产品与工艺、认证情况等…"
        />
        <div class="capability__actions">
          <NButton @click="current = 0">上一步</NButton>
          <NButton type="primary" @click="current = 2">下一步</NButton>
        </div>
      </template>

      <!-- Step 3：文档上传 + 解析提示 -->
      <template v-else>
        <NUpload
          multiple
          accept=".pdf,.ppt,.pptx,.doc,.docx"
          :default-upload="false"
          @change="handleUpload"
        >
          <div class="capability__drop">
            <div class="capability__drop-icon">⬆</div>
            <div>拖拽或点击上传文件</div>
            <div class="capability__drop-hint">支持 PDF / PPT / Word，用于能力解析</div>
          </div>
        </NUpload>
        <div v-if="parsedCount !== null" class="capability__parsed">
          ✓ 已解析，提取到 {{ parsedCount }} 条记录
        </div>
        <div class="capability__actions">
          <NButton @click="current = 1">上一步</NButton>
          <NButton type="primary" @click="submit()">提交材料</NButton>
        </div>
      </template>
    </div>

    <NDrawer v-model:show="templateOpen" placement="right" width="360px" title="常用模板">
      <div class="capability__templates">
        <div v-for="(t, i) in templates" :key="i" class="capability__template" @click="insertTemplate(t)">
          {{ t }}
        </div>
      </div>
    </NDrawer>
  </div>
</template>

<style scoped>
.capability {
  max-width: 720px;
  margin: 0 auto;
}
.capability__steps {
  display: flex;
  gap: var(--space-24);
  margin-bottom: var(--space-24);
}
.capability__step {
  display: flex;
  align-items: center;
  gap: var(--space-8);
  color: var(--color-disabled);
}
.capability__step.is-current {
  color: var(--color-primary);
}
.capability__step.is-done {
  color: var(--color-success);
}
.capability__step-dot {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: var(--font-weight-600);
  border: var(--border-width-1) solid var(--color-border-strong);
}
.capability__step.is-current .capability__step-dot {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: #fff;
}
.capability__step.is-done .capability__step-dot {
  border-color: var(--color-success);
  background: var(--color-success);
  color: #fff;
}
.capability__step-title {
  font-size: var(--font-size-14);
  font-weight: var(--font-weight-500);
}
.capability__step-desc {
  font-size: var(--font-size-12);
}
.capability__panel {
  padding: var(--space-24);
  background: var(--color-bg-panel);
  border: var(--border-width-1) solid var(--color-border-subtle);
  border-radius: var(--radius-12);
}
.capability__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 var(--space-16);
}
.capability__devices {
  margin-top: var(--space-24);
  border-top: var(--border-width-1) solid var(--color-border-subtle);
  padding-top: var(--space-16);
}
.capability__devices-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-12);
}
.capability__devices-head h4 {
  margin: 0;
  font-size: var(--font-size-15);
}
.capability__device-row {
  display: flex;
  gap: var(--space-12);
  margin-bottom: var(--space-8);
  align-items: center;
}
.capability__toolbar {
  margin-bottom: var(--space-12);
}
.capability__drop {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-8);
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
.capability__parsed {
  margin-top: var(--space-16);
  padding: var(--space-8) var(--space-12);
  background: var(--color-success-bg);
  color: var(--color-success-text);
  border-radius: var(--radius-8);
  font-size: var(--font-size-13);
}
.capability__actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-12);
  margin-top: var(--space-24);
}
.capability__templates {
  display: flex;
  flex-direction: column;
  gap: var(--space-12);
}
.capability__template {
  padding: var(--space-12) var(--space-16);
  background: var(--color-bg);
  border-radius: var(--radius-8);
  font-size: var(--font-size-13);
  line-height: var(--line-height-normal);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-standard);
}
.capability__template:hover {
  background: var(--color-primary-bg);
}
</style>
