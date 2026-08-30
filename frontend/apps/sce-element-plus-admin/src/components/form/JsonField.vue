<template>
  <pre v-if="readonly" class="json-readonly">{{ formatted }}</pre>
  <div v-else class="json-field">
    <div class="json-toolbar">
      <el-button link type="primary" size="small" @click="formatDraft">格式化</el-button>
      <span v-if="error" class="json-error">{{ error }}</span>
      <span v-else class="json-valid">JSON 格式正确</span>
    </div>
    <el-input v-model="draft" type="textarea" :rows="8" spellcheck="false" @input="update" @blur="validate" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

const props = defineProps<{ modelValue: unknown; readonly?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: unknown]; change: [] }>()
const draft = ref('')
const error = ref('')
const formatted = computed(() => stringify(props.modelValue))

function stringify(value: unknown) {
  if (typeof value === 'string') {
    try { return JSON.stringify(JSON.parse(value), null, 2) } catch { return value }
  }
  try { return JSON.stringify(value ?? {}, null, 2) } catch { return String(value ?? '') }
}
function parse(value: string) {
  try {
    const parsed = JSON.parse(value || '{}')
    error.value = ''
    return parsed
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message.replace(/^JSON\.parse:\s*/i, '') : 'JSON 格式错误'
    return undefined
  }
}
function update(value: string) {
  const parsed = parse(value)
  if (parsed !== undefined) emit('update:modelValue', typeof props.modelValue === 'string' ? value : parsed)
}
function validate() {
  if (parse(draft.value) !== undefined) emit('change')
}
function formatDraft() {
  const parsed = parse(draft.value)
  if (parsed === undefined) return
  draft.value = JSON.stringify(parsed, null, 2)
  update(draft.value)
}
watch(() => props.modelValue, (value) => { draft.value = stringify(value); error.value = '' }, { immediate: true, deep: true })
</script>

<style scoped>
.json-field { overflow: hidden; border-radius: 4px; }
.json-toolbar { display: flex; align-items: center; justify-content: space-between; min-height: 30px; }
.json-field :deep(textarea), .json-readonly { font-family: Consolas, Monaco, monospace; font-size: 12px; line-height: 1.6; }
.json-readonly { max-height: 360px; margin: 0; padding: 12px; overflow: auto; border-radius: 4px; background: #15181d; color: #d7dae0; white-space: pre-wrap; }
.json-error { color: var(--el-color-danger); font-size: 12px; }
.json-valid { color: var(--el-color-success); font-size: 12px; }
</style>
