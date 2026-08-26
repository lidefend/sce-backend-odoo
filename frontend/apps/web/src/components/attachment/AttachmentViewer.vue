<template>
  <ScDialog
    :open="visible"
    :title="displayName"
    :description="statusText"
    size="wide"
    panel-class="attachment-viewer"
    appearance="workspace"
    :busy="loading"
    close-label="关闭附件"
    @close="close"
  >
    <template #header-actions>
      <ScButton variant="ghost" :disabled="!canDownload" @click="downloadCurrent">下载</ScButton>
    </template>
    <div class="attachment-viewer-body" data-semantic-component="AttachmentViewerBody">
      <ScLoading v-if="loading" class="attachment-viewer-state" label="附件加载中" />
      <ScErrorState v-else-if="errorMessage" class="attachment-viewer-state" title="附件打开失败" :description="errorMessage" />
      <iframe
        v-else-if="previewUrl"
        class="attachment-viewer-frame"
        :src="previewUrl"
        :title="displayName"
      />
      <div v-else class="attachment-viewer-state">
        <strong>{{ displayName }}</strong>
        <span>{{ unsupportedText }}</span>
      </div>
    </div>
  </ScDialog>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue';
import { downloadFile } from '../../api/files';
import type { FileDownloadRequest, FileDownloadResponse } from '@sc/schema';
import ScButton from '../design-system/ScButton.vue';
import ScDialog from '../design-system/ScDialog.vue';
import ScErrorState from '../design-system/ScErrorState.vue';
import ScLoading from '../design-system/ScLoading.vue';

const INLINE_MIMETYPE_PREFIXES = ['image/', 'text/'];
const INLINE_MIMETYPES = new Set(['application/pdf']);

const visible = ref(false);
const loading = ref(false);
const errorMessage = ref('');
const payload = ref<FileDownloadResponse | null>(null);
const fallbackName = ref('');
const previewUrl = ref('');

const displayName = computed(() => payload.value?.name || fallbackName.value || '附件');
const mimetype = computed(() => payload.value?.mimetype || 'application/octet-stream');
const canDownload = computed(() => Boolean(payload.value?.datas || payload.value?.url));
const statusText = computed(() => {
  if (loading.value) return '正在读取附件';
  if (errorMessage.value) return '附件不可用';
  if (previewUrl.value) return mimetype.value;
  if (payload.value) return '当前文件暂不支持在线预览';
  return '';
});
const unsupportedText = computed(() => {
  if (!payload.value) return '';
  return `当前类型 ${mimetype.value} 暂不支持在线预览，可下载后查看。`;
});

function canPreviewInline(value: string) {
  const normalized = String(value || '').trim().toLowerCase();
  return INLINE_MIMETYPES.has(normalized) || INLINE_MIMETYPE_PREFIXES.some((prefix) => normalized.startsWith(prefix));
}

function base64ToBlob(datas: string, value: string) {
  const binary = atob(datas || '');
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return new Blob([bytes], { type: value || 'application/octet-stream' });
}

function revokePreviewUrl() {
  if (!previewUrl.value || !previewUrl.value.startsWith('blob:')) return;
  URL.revokeObjectURL(previewUrl.value);
  previewUrl.value = '';
}

function resetPayload() {
  revokePreviewUrl();
  payload.value = null;
  errorMessage.value = '';
}

async function open(params: FileDownloadRequest, name?: string) {
  fallbackName.value = name || '';
  visible.value = true;
  loading.value = true;
  resetPayload();
  try {
    const result = await downloadFile(params);
    payload.value = result;
    const data = result.datas || '';
    const type = result.mimetype || 'application/octet-stream';
    if (data && canPreviewInline(type)) {
      previewUrl.value = URL.createObjectURL(base64ToBlob(data, type));
    } else if (!data && result.url && !result.url.startsWith('legacy-file')) {
      previewUrl.value = result.url;
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '附件打开失败';
  } finally {
    loading.value = false;
  }
}

function close() {
  visible.value = false;
  loading.value = false;
  resetPayload();
}

function downloadBlob(blob: Blob, name: string) {
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = name || 'download';
  link.click();
  URL.revokeObjectURL(objectUrl);
}

function downloadCurrent() {
  const current = payload.value;
  if (!current) return;
  if (current.datas) {
    downloadBlob(base64ToBlob(current.datas, current.mimetype || ''), displayName.value);
    return;
  }
  if (current.url && !current.url.startsWith('legacy-file')) {
    window.open(current.url, '_blank', 'noopener');
  }
}

onBeforeUnmount(() => {
  resetPayload();
});

defineExpose({ open, close });
</script>

<style scoped>
:deep(.attachment-viewer) {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  height: min(760px, calc(100dvh - 48px));
  min-height: 420px;
  overflow: hidden;
}

.attachment-viewer-body {
  min-height: 0;
  background: var(--sc-app-muted-bg);
}

.attachment-viewer-frame {
  width: 100%;
  height: 100%;
  border: 0;
  background: var(--sc-app-panel);
}

.attachment-viewer-state {
  display: grid;
  place-items: center;
  align-content: center;
  gap: 8px;
  height: 100%;
  min-height: 260px;
  padding: 24px;
  color: var(--sc-app-text-secondary);
  text-align: center;
}

.attachment-viewer-state strong {
  max-width: 100%;
  color: var(--sc-app-text-primary);
  overflow-wrap: anywhere;
}

.attachment-viewer-state span {
  max-width: 560px;
  line-height: 1.6;
}

@media (max-width: 720px) {
  :deep(.attachment-viewer) {
    width: 100%;
    height: calc(100dvh - var(--sc-product-space-4));
    min-height: 0;
  }
}
</style>
