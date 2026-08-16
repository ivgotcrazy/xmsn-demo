<script setup lang="ts">
/**
 * 选项组（v2.1 重设计）：区分三种展示形态——
 * - actions：流程动作按钮（提交匹配 / 按建议填写 / 我自己定 / 跳过），点选即提交；
 * - single ：单选槽位（radio 样式），选择后点「确认选择」提交；
 * - multi  ：多选槽位（checkbox 样式），可勾选多项，点「确认选择」提交数组。
 * select 载荷：actions/single → string；multi → string[]。
 */
import { ref, watch } from "vue"
import { NButton } from "naive-ui"

const props = defineProps<{ options: string[]; optionsType?: "none" | "single" | "multi" | "actions" }>()
const emit = defineEmits<{ select: [value: string | string[]] }>()

const selected = ref("") // single/actions 高亮
const checked = ref<string[]>([]) // multi 勾选

watch(
  () => props.options,
  () => {
    selected.value = ""
    checked.value = []
  },
)

function onAction(o: string): void {
  emit("select", o)
}
function onSingle(o: string): void {
  selected.value = o
}
function onToggle(o: string): void {
  checked.value = checked.value.includes(o)
    ? checked.value.filter((x) => x !== o)
    : [...checked.value, o]
}
function onConfirm(): void {
  if (props.optionsType === "multi") emit("select", [...checked.value])
  else if (selected.value) emit("select", selected.value)
}
</script>

<template>
  <div v-if="options.length && optionsType !== 'none'" class="opt-group">
    <!-- 动作按钮：点选即提交 -->
    <template v-if="optionsType === 'actions'">
      <div class="opt-row">
        <button
          v-for="o in options"
          :key="o"
          class="opt-chip opt-chip--action"
          @click="onAction(o)"
        >
          {{ o }}
        </button>
      </div>
    </template>

    <!-- 单选：radio 样式 + 确认 -->
    <template v-else-if="optionsType === 'single'">
      <div class="opt-row">
        <button
          v-for="o in options"
          :key="o"
          class="opt-chip opt-chip--radio"
          :class="{ 'is-selected': selected === o }"
          @click="onSingle(o)"
        >
          <span class="opt-indicator opt-indicator--dot" />
          <span class="opt-label">{{ o }}</span>
        </button>
      </div>
      <NButton class="opt-confirm" type="primary" size="small" :disabled="!selected" @click="onConfirm">
        确认选择
      </NButton>
    </template>

    <!-- 多选：checkbox 样式 + 确认 -->
    <template v-else-if="optionsType === 'multi'">
      <div class="opt-row">
        <button
          v-for="o in options"
          :key="o"
          class="opt-chip opt-chip--check"
          :class="{ 'is-selected': checked.includes(o) }"
          @click="onToggle(o)"
        >
          <span class="opt-indicator opt-indicator--box" :class="{ 'is-on': checked.includes(o) }" />
          <span class="opt-label">{{ o }}</span>
        </button>
      </div>
      <NButton class="opt-confirm" type="primary" size="small" :disabled="!checked.length" @click="onConfirm">
        确认选择{{ checked.length ? `（${checked.length}）` : "" }}
      </NButton>
    </template>
  </div>
</template>

<style scoped>
.opt-group {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
  margin: 10px 0 6px 44px;
  max-width: 560px;
}
.opt-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.opt-chip {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 7px 13px;
  border-radius: 10px;
  border: 1px solid #dbe0ea;
  background: #fff;
  color: #3a4456;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s ease;
  user-select: none;
}
.opt-chip:hover {
  border-color: #7fb0f5;
  color: #2b7de9;
}
.opt-chip.is-selected {
  border-color: #2b7de9;
  background: #eef4ff;
  color: #1f5fd0;
  font-weight: 600;
}
/* 动作按钮：胶囊 + 主题色 */
.opt-chip--action {
  border-radius: 999px;
  background: #f2f6ff;
  border-color: #dbe6ff;
  color: #2b7de9;
  font-weight: 600;
}
.opt-chip--action:hover {
  background: #e3edff;
  border-color: #2b7de9;
}
/* 指示器：单选圆点 */
.opt-indicator {
  flex: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.opt-indicator--dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid #c3cddd;
  box-sizing: border-box;
}
.opt-chip--radio.is-selected .opt-indicator--dot {
  border-color: #2b7de9;
  background: #2b7de9;
  box-shadow: inset 0 0 0 2px #eef4ff;
}
/* 指示器：多选方框 + ✓ */
.opt-indicator--box {
  width: 14px;
  height: 14px;
  border-radius: 4px;
  border: 2px solid #c3cddd;
  box-sizing: border-box;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  line-height: 1;
}
.opt-indicator--box.is-on {
  background: #2b7de9;
  border-color: #2b7de9;
}
.opt-indicator--box.is-on::after {
  content: "✓";
}
.opt-label {
  white-space: nowrap;
}
.opt-confirm {
  align-self: flex-start; /* 与选项左对齐、紧贴其下，避免"飞到右侧"脱离选项组 */
  margin-top: 2px;
  border-radius: 8px;
}
</style>

<style scoped>
.opt-group {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-8);
  margin: 0 0 var(--space-8) 48px;
}
</style>
