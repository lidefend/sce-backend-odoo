<template>
  <div
    class="restricted-html-editor"
    data-semantic-component="RestrictedHtmlEditor"
    :data-state="disabled ? 'disabled' : 'active'"
  >
    <div class="restricted-html-editor__toolbar" role="toolbar" :aria-label="copy.toolbarLabel">
      <button
        v-for="item in toolbarItems"
        :key="item.command"
        type="button"
        class="restricted-html-editor__tool"
        :disabled="disabled"
        :title="item.title"
        :aria-label="item.title"
        @mousedown.prevent
        @click="execCommand(item)"
      >
        <span :class="item.iconClass">{{ item.label }}</span>
      </button>
      <span
        class="restricted-html-editor__counter"
        :class="{ 'restricted-html-editor__counter--over': overLimit }"
      >
        {{ currentLength }} / {{ maxLength }}
      </span>
    </div>

    <div
      ref="editorRef"
      class="restricted-html-editor__surface"
      contenteditable="true"
      :data-placeholder="copy.placeholder"
      :aria-disabled="disabled ? 'true' : 'false'"
      @input="onInput"
    ></div>

    <div v-if="overLimit" class="restricted-html-editor__hint" data-state="over-limit" role="alert">
      {{ copy.overLimit }}
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 受限富文本输入控件（共享层，无业务语义）。
 *
 * 职责边界（服务端净化权威，本控件仅输入面）：
 * - 工具栏只暴露受限格式命令（加粗/斜体/标题/列表/链接），
 *   与服务端 canonical 白名单子集对齐；不提供源码编辑、
 *   不加载外部编辑器依赖；
 * - 长度上限为预校验提示（服务端仍按契约为准）；
 * - 内容提交为原始草稿，净化与落库由服务端权威完成
 *   （sanitized_input_changed 提示由消费方依据响应渲染）。
 */
import { computed, onMounted, ref, watch } from 'vue';

const props = defineProps<{
  modelValue: string;
  maxLength: number;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  (event: 'update:modelValue', value: string): void;
}>();

const editorRef = ref<HTMLDivElement | null>(null);
/** 最近一次由本控件发出的内容（外部同步防光标跳动） */
let lastEmitted = '';

const copy = {
  toolbarLabel: '格式工具栏',
  placeholder: '输入内容…（支持加粗、斜体、标题、列表与链接）',
  overLimit: '内容超出长度上限，请精简后再保存。',
};

type ToolbarItem = {
  command: string;
  value?: string;
  label: string;
  title: string;
  iconClass?: string;
};

const toolbarItems: ToolbarItem[] = [
  { command: 'bold', label: 'B', title: '加粗', iconClass: 'is-bold' },
  { command: 'italic', label: 'I', title: '斜体', iconClass: 'is-italic' },
  { command: 'formatBlock', value: 'h1', label: 'H1', title: '一级标题' },
  { command: 'formatBlock', value: 'h2', label: 'H2', title: '二级标题' },
  { command: 'formatBlock', value: 'h3', label: 'H3', title: '三级标题' },
  { command: 'formatBlock', value: 'p', label: '正文', title: '正文段落' },
  { command: 'insertUnorderedList', label: '•', title: '无序列表' },
  { command: 'insertOrderedList', label: '1.', title: '有序列表' },
  { command: 'createLink', label: '🔗', title: '插入链接' },
];

const currentLength = computed(() => String(props.modelValue ?? '').length);
const overLimit = computed(() => currentLength.value > props.maxLength);

onMounted(() => {
  const el = editorRef.value;
  if (el) {
    el.innerHTML = String(props.modelValue ?? '');
    lastEmitted = el.innerHTML;
  }
});

/** 外部值同步：仅当与最近发出值不同（避免编辑中光标复位） */
watch(
  () => props.modelValue,
  (value) => {
    const next = String(value ?? '');
    if (next === lastEmitted) return;
    const el = editorRef.value;
    if (!el) return;
    el.innerHTML = next;
    lastEmitted = next;
  },
);

function onInput() {
  const el = editorRef.value;
  if (!el) return;
  lastEmitted = el.innerHTML;
  emit('update:modelValue', lastEmitted);
}

function execCommand(item: ToolbarItem) {
  if (props.disabled) return;
  const el = editorRef.value;
  if (!el) return;
  el.focus();
  if (item.command === 'createLink') {
    const url = window.prompt('链接地址（http/https/mailto）', 'https://');
    if (!url || !/^(https?:|mailto:)/i.test(url.trim())) return;
    document.execCommand('createLink', false, url.trim());
  } else if (item.command === 'formatBlock') {
    document.execCommand('formatBlock', false, item.value);
  } else {
    document.execCommand(item.command, false);
  }
  onInput();
}
</script>

<style scoped>
.restricted-html-editor {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.restricted-html-editor__toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
}

.restricted-html-editor__tool {
  min-width: 28px;
  height: 26px;
  padding: 0 6px;
  border: 1px solid var(--sc-border, #dcdcdc);
  border-radius: 4px;
  background: var(--sc-surface, #fff);
  color: var(--sc-text, #333);
  font-size: 12px;
  line-height: 1;
  cursor: pointer;
}

.restricted-html-editor__tool:hover:not(:disabled) {
  border-color: var(--sc-primary, #0052d9);
  color: var(--sc-primary, #0052d9);
}

.restricted-html-editor__tool:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.restricted-html-editor__tool .is-bold {
  font-weight: 700;
}

.restricted-html-editor__tool .is-italic {
  font-style: italic;
}

.restricted-html-editor__counter {
  margin-left: auto;
  font-size: 12px;
  color: var(--sc-text-secondary, #666);
}

.restricted-html-editor__counter--over {
  color: var(--sc-danger, #d54941);
  font-weight: 600;
}

.restricted-html-editor__surface {
  min-height: 160px;
  max-height: 420px;
  overflow-y: auto;
  padding: 8px 10px;
  border: 1px solid var(--sc-border, #dcdcdc);
  border-radius: 4px;
  background: var(--sc-surface, #fff);
  font-size: 14px;
  line-height: 1.6;
  color: var(--sc-text, #333);
}

.restricted-html-editor__surface:focus {
  outline: none;
  border-color: var(--sc-primary, #0052d9);
}

.restricted-html-editor__surface:empty::before {
  content: attr(data-placeholder);
  color: var(--sc-text-placeholder, #999);
  pointer-events: none;
}

.restricted-html-editor__surface :deep(h1) {
  font-size: 1.4em;
  margin: 0.5em 0 0.3em;
}

.restricted-html-editor__surface :deep(h2) {
  font-size: 1.25em;
  margin: 0.5em 0 0.3em;
}

.restricted-html-editor__surface :deep(h3) {
  font-size: 1.1em;
  margin: 0.5em 0 0.3em;
}

.restricted-html-editor__surface :deep(ul),
.restricted-html-editor__surface :deep(ol) {
  padding-left: 1.4em;
  margin: 0.3em 0;
}

.restricted-html-editor__hint {
  font-size: 12px;
  color: var(--sc-danger, #d54941);
}
</style>
