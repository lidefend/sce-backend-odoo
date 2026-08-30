<template>
  <div class="attachment-field">
    <div v-if="attachments.length" class="attachment-list">
      <div v-for="item in attachments" :key="item.id" class="attachment-item">
        <el-icon><Document /></el-icon>
        <button type="button" class="attachment-name" @click="download(item)">{{ item.name || `附件 ${item.id}` }}</button>
        <span>{{ fileSize(item.file_size) }}</span>
        <el-tooltip v-if="!readonly" content="从当前字段移除"><el-button text circle :icon="Close" @click="remove(item.id)" /></el-tooltip>
      </div>
    </div>
    <el-empty v-else description="暂无附件" :image-size="48" />
    <binary-field v-if="!readonly" :model="model" :record-id="recordId" @uploaded="uploaded" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Close, Document } from '@element-plus/icons-vue'
import BinaryField from './BinaryField.vue'
import { downloadFile, listData } from '@/api/odoo'
import type { Dictionary } from '@/types/contracts'
import { normalizeRelationIds } from '@/utils/widget'

const props = defineProps<{
  modelValue: unknown
  model: string
  recordId?: number | null
  readonly?: boolean
}>()
const emit = defineEmits<{ 'update:modelValue': [value: number[]]; change: []; uploaded: [] }>()
const attachments = ref<Dictionary[]>([])

async function hydrate(value: unknown) {
  const attachmentIds = normalizeRelationIds(value)
  if (!attachmentIds.length) { attachments.value = []; return }
  try {
    const result = await listData({
      model: 'ir.attachment',
      fields: ['id', 'name', 'mimetype', 'file_size'],
      domain: [['id', 'in', attachmentIds]],
      limit: attachmentIds.length,
    })
    attachments.value = result.records || result.rows || []
  } catch {
    attachments.value = attachmentIds.map((id) => ({ id, name: `附件 ${id}` }))
  }
}
function remove(id: number) {
  const next = normalizeRelationIds(props.modelValue).filter((item) => item !== Number(id))
  attachments.value = attachments.value.filter((item) => Number(item.id) !== Number(id))
  emit('update:modelValue', next)
  emit('change')
}
async function download(item: Dictionary) {
  try {
    const file = await downloadFile(Number(item.id))
    if (!file.content_b64) return
    const bytes = Uint8Array.from(atob(file.content_b64), (char) => char.charCodeAt(0))
    const url = URL.createObjectURL(new Blob([bytes], { type: file.mimetype || item.mimetype || 'application/octet-stream' }))
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = file.filename || item.name || 'attachment'
    anchor.click()
    URL.revokeObjectURL(url)
  } catch (cause) {
    ElMessage.error(cause instanceof Error ? cause.message : '附件下载失败')
  }
}
function uploaded(result: Dictionary) {
  const id = Number(result.id || result.attachment_id || 0)
  if (id && !normalizeRelationIds(props.modelValue).includes(id)) {
    emit('update:modelValue', [...normalizeRelationIds(props.modelValue), id])
    emit('change')
  }
  emit('uploaded')
}
function fileSize(value: unknown) {
  const size = Number(value || 0)
  if (!size) return ''
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}
watch(() => props.modelValue, hydrate, { immediate: true, deep: true })
</script>

<style scoped>
.attachment-field { display: grid; gap: 10px; }
.attachment-list { display: grid; border: 1px solid var(--el-border-color-lighter); border-radius: 4px; }
.attachment-item { display: grid; grid-template-columns: auto minmax(0,1fr) auto auto; align-items: center; gap: 9px; min-height: 40px; padding: 4px 9px; border-bottom: 1px solid var(--el-border-color-lighter); }
.attachment-item:last-child { border-bottom: 0; }
.attachment-item > span { color: var(--el-text-color-secondary); font-size: 12px; }
.attachment-name { overflow: hidden; padding: 0; border: 0; background: transparent; color: var(--el-color-primary); text-align: left; text-overflow: ellipsis; white-space: nowrap; cursor: pointer; }
</style>
