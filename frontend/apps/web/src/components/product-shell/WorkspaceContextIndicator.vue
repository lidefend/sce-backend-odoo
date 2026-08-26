<template>
  <div
    class="workspace-context-indicator"
    :aria-label="showRecord ? `当前公司和${recordSubject}` : '当前公司'"
    data-semantic-component="WorkspaceContextIndicator"
  >
    <ScButton class="workspace-context-indicator__button" appearance="context-action" variant="ghost" size="small" type="button" :title="`切换公司：${companyLabel}`" :aria-label="`切换公司：${companyLabel}`" @click="emit('company')">
      <ScIcon name="building" :size="16" />
      <span class="workspace-context-indicator__label">{{ companyLabel }}</span>
    </ScButton>
    <ScButton v-if="showRecord" class="workspace-context-indicator__button" appearance="context-action" variant="ghost" size="small" type="button" :title="`${recordActionLabel}：${recordLabel}`" :aria-label="`${recordActionLabel}：${recordLabel}`" @click="emit('record')">
      <ScIcon :name="recordIcon" :size="16" />
      <span class="workspace-context-indicator__label">{{ recordLabel }}</span>
    </ScButton>
  </div>
</template>

<script setup lang="ts">
import ScIcon from '../design-system/ScIcon.vue';
import ScButton from '../design-system/ScButton.vue';

withDefaults(defineProps<{
  companyLabel?: string;
  recordSubject: string;
  recordLabel: string;
  recordActionLabel: string;
  recordIcon: 'briefcase' | 'file-text' | 'folder' | 'project';
  showRecord?: boolean;
}>(), {
  companyLabel: '全部公司',
  showRecord: true,
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

.workspace-context-indicator__button {
  min-width: 0;
  max-width: 180px;
  min-height: 32px;
  padding: 0 var(--sc-space-xs);
  overflow: hidden;
  display: inline-flex;
  align-items: center;
  gap: var(--sc-space-2xs);
  font: inherit;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
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

  .workspace-context-indicator__button {
    width: 32px;
    min-width: 32px;
    padding: 0;
    justify-content: center;
  }
}
</style>
