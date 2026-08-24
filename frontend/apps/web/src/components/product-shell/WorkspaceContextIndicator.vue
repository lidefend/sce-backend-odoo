<template>
  <div
    class="workspace-context-indicator"
    :aria-label="`当前公司和${recordSubject}`"
    data-semantic-component="WorkspaceContextIndicator"
  >
    <button type="button" :title="`切换公司：${companyLabel}`" :aria-label="`切换公司：${companyLabel}`" @click="emit('company')">
      <ScIcon name="building" :size="16" />
      <span class="workspace-context-indicator__label">{{ companyLabel }}</span>
    </button>
    <button type="button" :title="`${recordActionLabel}：${recordLabel}`" :aria-label="`${recordActionLabel}：${recordLabel}`" @click="emit('record')">
      <ScIcon :name="recordIcon" :size="16" />
      <span class="workspace-context-indicator__label">{{ recordLabel }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import ScIcon from '../design-system/ScIcon.vue';

withDefaults(defineProps<{
  companyLabel?: string;
  recordSubject: string;
  recordLabel: string;
  recordActionLabel: string;
  recordIcon: 'briefcase' | 'file-text' | 'folder' | 'project';
}>(), {
  companyLabel: '全部公司',
});
const emit = defineEmits<{ (event: 'company'): void; (event: 'record'): void }>();
</script>

<style scoped>
.workspace-context-indicator {
  min-width: 0;
  max-width: 300px;
  display: flex;
  align-items: center;
  gap: var(--sc-toolbar-gap);
  color: var(--sc-app-text-muted);
  font-size: 12px;
}

.workspace-context-indicator button {
  min-width: 0;
  max-width: 180px;
  min-height: 32px;
  padding: 0 var(--sc-space-xs);
  overflow: hidden;
  display: inline-flex;
  align-items: center;
  gap: var(--sc-space-2xs);
  border: 1px solid transparent;
  border-radius: var(--sc-product-radius-control);
  background: transparent;
  color: var(--sc-app-text-secondary);
  font: inherit;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}

.workspace-context-indicator button:hover {
  color: var(--sc-app-accent);
}

@media (max-width: 960px) {
  .workspace-context-indicator__label {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
    white-space: nowrap;
  }

  .workspace-context-indicator button {
    width: 32px;
    min-width: 32px;
    padding: 0;
    justify-content: center;
  }
}
</style>
