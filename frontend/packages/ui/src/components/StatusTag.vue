<script setup lang="ts">
/**
 * 状态徽标（COMP-007）：审核状态 / 匹配三态等语义映射到 NTag。
 */
import { useAttrs } from "vue"
import { NTag } from "naive-ui"
import type { TagProps } from "naive-ui"

type TagType = NonNullable<TagProps["type"]>

const props = defineProps<{
  type?: TagType
  /** round/rect 圆角风格 */
  round?: boolean
  size?: "small" | "medium" | "large"
}>()

const attrs = useAttrs()
</script>

<template>
  <NTag :type="props.type ?? 'default'" :round="props.round ?? true" :size="props.size ?? 'small'" v-bind="attrs">
    <slot />
  </NTag>
</template>
