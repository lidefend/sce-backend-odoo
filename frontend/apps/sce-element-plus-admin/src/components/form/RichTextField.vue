<template>
  <div v-if="readonly" class="rich-text-readonly" v-html="safeHtml" />
  <div v-else class="rich-text-field">
    <div class="rich-toolbar">
      <el-tooltip content="加粗"><button type="button" aria-label="加粗" @mousedown.prevent="command('bold')"><strong>B</strong></button></el-tooltip>
      <el-tooltip content="斜体"><button type="button" aria-label="斜体" @mousedown.prevent="command('italic')"><em>I</em></button></el-tooltip>
      <el-tooltip content="无序列表"><button type="button" aria-label="无序列表" @mousedown.prevent="command('insertUnorderedList')">•</button></el-tooltip>
      <el-tooltip content="有序列表"><button type="button" aria-label="有序列表" @mousedown.prevent="command('insertOrderedList')">1.</button></el-tooltip>
      <el-button link size="small" @click="clearFormatting">清除格式</el-button>
    </div>
    <div
      ref="editor"
      class="rich-editor"
      contenteditable="true"
      role="textbox"
      aria-multiline="true"
      @input="update"
      @blur="emit('change')"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'

const props = defineProps<{ modelValue: unknown; readonly?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: string]; change: [] }>()
const editor = ref<HTMLElement>()
const safeHtml = computed(() => sanitizeHtml(String(props.modelValue || '')))

function sanitizeHtml(html: string) {
  const documentNode = new DOMParser().parseFromString(html, 'text/html')
  documentNode.querySelectorAll('script,style,iframe,object,embed,form').forEach((node) => node.remove())
  documentNode.querySelectorAll('*').forEach((node) => {
    for (const attribute of [...node.attributes]) {
      if (/^on/i.test(attribute.name) || (/^(href|src)$/i.test(attribute.name) && /^javascript:/i.test(attribute.value)))
        node.removeAttribute(attribute.name)
    }
  })
  return documentNode.body.innerHTML
}
function syncEditor(value: unknown) {
  void nextTick(() => {
    if (editor.value && document.activeElement !== editor.value) editor.value.innerHTML = sanitizeHtml(String(value || ''))
  })
}
function update() {
  emit('update:modelValue', sanitizeHtml(editor.value?.innerHTML || ''))
}
function command(name: string) {
  editor.value?.focus()
  document.execCommand(name)
  update()
}
function clearFormatting() {
  command('removeFormat')
}
watch(() => props.modelValue, syncEditor, { immediate: true })
</script>

<style scoped>
.rich-text-field { overflow: hidden; border: 1px solid var(--el-border-color); border-radius: 4px; background: #fff; }
.rich-toolbar { display: flex; align-items: center; gap: 3px; min-height: 38px; padding: 4px 8px; border-bottom: 1px solid var(--el-border-color-lighter); background: var(--el-fill-color-extra-light); }
.rich-toolbar button { width: 28px; height: 28px; padding: 0; border: 0; border-radius: 3px; background: transparent; color: var(--el-text-color-regular); cursor: pointer; }
.rich-toolbar button:hover { background: var(--el-fill-color); }
.rich-editor { min-height: 130px; padding: 10px 12px; outline: 0; line-height: 1.65; }
.rich-editor:focus { box-shadow: inset 0 0 0 1px var(--el-color-primary); }
.rich-text-readonly { min-height: 42px; padding: 10px 12px; border-radius: 4px; background: var(--el-fill-color-light); line-height: 1.65; overflow-wrap: anywhere; }
.rich-text-readonly :deep(p:first-child) { margin-top: 0; }
.rich-text-readonly :deep(p:last-child) { margin-bottom: 0; }
</style>
