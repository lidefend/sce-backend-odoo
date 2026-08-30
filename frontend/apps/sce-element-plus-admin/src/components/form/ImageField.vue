<template>
  <div class="image-field">
    <el-image v-if="source" :src="source" :preview-src-list="[source]" fit="contain" class="image-preview">
      <template #error><div class="image-error"><el-icon><Picture /></el-icon><span>图片无法预览</span></div></template>
    </el-image>
    <el-empty v-else description="暂无图片" :image-size="48" />
    <div v-if="!readonly" class="image-actions">
      <el-upload :auto-upload="false" :show-file-list="false" accept="image/*" :on-change="selectImage">
        <el-button :icon="Upload">选择图片</el-button>
      </el-upload>
      <el-button v-if="source" :icon="Delete" @click="remove">移除</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { UploadFile } from 'element-plus'
import { Delete, Picture, Upload } from '@element-plus/icons-vue'

const props = defineProps<{ modelValue: unknown; readonly?: boolean; mimetype?: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: string | false]; change: [] }>()
const source = computed(() => {
  const value = String(props.modelValue || '')
  if (!value) return ''
  return /^(data:|https?:|blob:)/.test(value) ? value : `data:${props.mimetype || 'image/png'};base64,${value}`
})

function selectImage(file: UploadFile) {
  if (!file.raw) return
  const reader = new FileReader()
  reader.onload = () => {
    const value = String(reader.result || '')
    emit('update:modelValue', value.split(',')[1] || '')
    emit('change')
  }
  reader.readAsDataURL(file.raw)
}
function remove() {
  emit('update:modelValue', false)
  emit('change')
}
</script>

<style scoped>
.image-field { display: grid; gap: 10px; justify-items: start; }
.image-preview { width: min(320px, 100%); height: 190px; border: 1px solid var(--el-border-color-lighter); border-radius: 4px; background: var(--el-fill-color-extra-light); }
.image-error { height: 100%; display: grid; place-items: center; align-content: center; gap: 7px; color: var(--el-text-color-secondary); }
.image-error .el-icon { font-size: 28px; }
.image-actions { display: flex; gap: 8px; }
</style>
