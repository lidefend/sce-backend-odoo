<template>
  <div v-if="widget === 'statusbar'" class="statusbar-field" role="list" :aria-label="field.label">
    <button
      v-for="(option, index) in options"
      :key="String(option.value)"
      type="button"
      class="status-step"
      :class="{ active: isCurrent(option.value), completed: index < currentIndex }"
      :disabled="readonly"
      @click="select(option.value)"
    >
      <span class="status-step__dot" />
      <span>{{ option.label }}</span>
    </button>
  </div>
  <el-statistic v-else-if="widget === 'statinfo'" :value="statValue" class="stat-field" />
  <el-tag v-else :type="tagType" effect="light" class="status-tag">
    <span v-if="widget === 'status_with_color'" class="status-color" :style="{ backgroundColor: statusColor }" />
    {{ displayFieldValue(modelValue, field.code, field.selection, field.type) }}
  </el-tag>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { FieldSpec } from '@/types/contracts'
import { displayFieldValue } from '@/utils/format'
import { statusTagType } from '@/utils/widget'

const props = defineProps<{
  field: FieldSpec
  modelValue: unknown
  widget: 'statusbar' | 'badge' | 'statinfo' | 'status_with_color'
  readonly?: boolean
}>()
const emit = defineEmits<{ 'update:modelValue': [value: unknown]; change: [] }>()

const options = computed(() => props.field.selection.length
  ? props.field.selection
  : [{ value: props.modelValue, label: displayFieldValue(props.modelValue, props.field.code, [], props.field.type) }])
const currentIndex = computed(() => options.value.findIndex((option) => String(option.value) === String(props.modelValue)))
const statValue = computed(() => {
  const value = Number(props.modelValue)
  return Number.isFinite(value) ? value : 0
})
const tagType = computed(() => statusTagType(props.modelValue))
const statusColor = computed(() => {
  const colors = props.field.config.colors || props.field.config.color_map || props.field.config.colorMap || {}
  return String(colors[String(props.modelValue)] || ({ success: '#67c23a', warning: '#e6a23c', danger: '#f56c6c', info: '#909399', primary: '#409eff' } as Record<string, string>)[tagType.value])
})

function isCurrent(value: unknown) {
  return String(value) === String(props.modelValue)
}
function select(value: unknown) {
  if (props.readonly || isCurrent(value)) return
  emit('update:modelValue', value)
  emit('change')
}
</script>

<style scoped>
.statusbar-field { display: flex; align-items: flex-start; width: 100%; min-height: 66px; min-width: 0; overflow: hidden; padding: 5px 0 8px; }
.status-step { position: relative; flex: 1 1 0; display: flex; flex-direction: column; align-items: center; gap: 7px; min-width: 0; padding: 0 8px; border: 0; color: var(--el-text-color-secondary); background: transparent; cursor: pointer; }
.status-step:not(:last-child)::after { content: ''; position: absolute; z-index: 0; top: 7px; left: 50%; right: -50%; height: 2px; background: var(--el-border-color); }
.status-step__dot { position: relative; z-index: 1; flex: 0 0 16px; width: 16px; height: 16px; border: 3px solid var(--el-border-color); border-radius: 50%; background: #fff; }
.status-step.completed::after { background: var(--el-color-primary); }
.status-step.completed .status-step__dot { border-color: var(--el-color-primary); background: var(--el-color-primary); }
.status-step.active { color: var(--el-color-primary); font-weight: 600; }
.status-step.active .status-step__dot { border-color: var(--el-color-primary); box-shadow: 0 0 0 3px var(--el-color-primary-light-9); }
.status-step > span:last-child { position: relative; z-index: 1; max-width: 100%; overflow-wrap: anywhere; text-align: center; white-space: normal; }
.status-step:disabled { cursor: default; }
.status-tag { min-height: 26px; }
.status-color { display: inline-block; width: 7px; height: 7px; margin-right: 6px; border-radius: 50%; vertical-align: 1px; }
.stat-field :deep(.el-statistic__number) { font-size: 22px; color: var(--el-text-color-primary); }
</style>
