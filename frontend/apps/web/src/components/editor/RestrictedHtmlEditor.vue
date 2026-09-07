<template>
  <div
    class="restricted-html-editor"
    data-semantic-component="RestrictedHtmlEditor"
    :data-state="disabled ? 'disabled' : 'active'"
  >
    <div class="restricted-html-editor__toolbar" role="toolbar" :aria-label="copy.toolbarLabel">
      <ScButton
        v-for="item in toolbarItems"
        :key="item.command"
        class="restricted-html-editor__tool"
        size="small"
        variant="ghost"
        :disabled="disabled"
        :title="item.title"
        :aria-label="item.title"
        @mousedown.prevent
        @click="execCommand(item)"
      >
        <span :class="item.iconClass">{{ item.label }}</span>
      </ScButton>
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

    <!-- 链接插入：语义对话框（不走 window.prompt 原生 API） -->
    <ScDialog
      :open="linkDialogOpen"
      :title="copy.linkDialogTitle"
      :description="copy.linkDialogHint"
      panel-class="restricted-html-editor__link-dialog"
      @close="cancelLink"
    >
      <ScInput
        v-model="linkUrl"
        type="url"
        :placeholder="copy.linkPlaceholder"
        :status="linkUrlInvalid ? 'error' : 'default'"
        @keydown.enter.prevent="confirmLink"
      />
      <template #actions>
        <ScButton size="small" variant="ghost" @click="cancelLink">{{ copy.linkCancel }}</ScButton>
        <ScButton size="small" variant="primary" :disabled="!linkUrl.trim()" @click="confirmLink">
          {{ copy.linkConfirm }}
        </ScButton>
      </template>
    </ScDialog>
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
import ScButton from '../design-system/ScButton.vue';
import ScDialog from '../design-system/ScDialog.vue';
import ScInput from '../design-system/ScInput.vue';

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
  linkDialogTitle: '插入链接',
  linkDialogHint: '仅支持 http、https 与 mailto 协议地址。',
  linkPlaceholder: 'https://',
  linkCancel: '取消',
  linkConfirm: '插入链接',
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

/** 链接插入会话：保存选区（对话框聚焦后仍可恢复），确认后执行 createLink */
const linkDialogOpen = ref(false);
const linkUrl = ref('');
let savedRange: Range | null = null;

const LINK_URL_RE = /^(https?:|mailto:)/i;
const linkUrlInvalid = computed(
  () => linkUrl.value.trim() !== '' && !LINK_URL_RE.test(linkUrl.value.trim()),
);

function openLinkDialog() {
  const selection = window.getSelection();
  savedRange = selection && selection.rangeCount > 0 ? selection.getRangeAt(0).cloneRange() : null;
  linkUrl.value = '';
  linkDialogOpen.value = true;
}

function cancelLink() {
  linkDialogOpen.value = false;
  savedRange = null;
}

function confirmLink() {
  const url = linkUrl.value.trim();
  if (!LINK_URL_RE.test(url)) return;
  const el = editorRef.value;
  linkDialogOpen.value = false;
  if (!el) return;
  el.focus();
  const selection = window.getSelection();
  if (savedRange && selection) {
    selection.removeAllRanges();
    selection.addRange(savedRange);
  }
  document.execCommand('createLink', false, url);
  savedRange = null;
  onInput();
}

function execCommand(item: ToolbarItem) {
  if (props.disabled) return;
  const el = editorRef.value;
  if (!el) return;
  el.focus();
  if (item.command === 'createLink') {
    openLinkDialog();
    return;
  }
  if (item.command === 'formatBlock') {
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
  font-size: 12px;
  line-height: 1;
}

/* 悬停/禁用视觉由 ScButton ghost 变体自带（根类不拥有视觉铬，
   frontend_primitive_adapter_guard 纪律） */

.restricted-html-editor__tool .is-bold {
  font-weight: 700;
}

.restricted-html-editor__tool .is-italic {
  font-style: italic;
}

.restricted-html-editor__counter {
  margin-left: auto;
  font-size: 12px;
  color: var(--sc-semantic-text-secondary);
}

.restricted-html-editor__counter--over {
  color: var(--sc-semantic-state-danger-text);
  font-weight: 600;
}

.restricted-html-editor__surface {
  min-height: 160px;
  max-height: 420px;
  overflow-y: auto;
  padding: 8px 10px;
  border: 1px solid var(--sc-semantic-border-default);
  border-radius: 4px;
  background: var(--sc-semantic-surface-panel);
  font-size: 14px;
  line-height: 1.6;
  color: var(--sc-semantic-text-primary);
}

.restricted-html-editor__surface:focus {
  outline: none;
  border-color: var(--sc-semantic-surface-interactive);
}

.restricted-html-editor__surface:empty::before {
  content: attr(data-placeholder);
  color: var(--sc-semantic-text-muted);
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
  color: var(--sc-semantic-state-danger-text);
}
</style>
