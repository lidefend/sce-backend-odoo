<template>
  <TDesignTag size="small" variant="light" :theme="theme" :title="label" class="sc-status-badge"
    data-semantic-component="ScStatusBadge" data-semantic-driver="tdesign-tag"
    data-semantic-layer="primitive" :data-status="value" :data-semantic-status="semantic">
    <span class="sc-visually-hidden">{{ statusPrefix }}</span>{{ label }}
  </TDesignTag>
</template>
<script setup lang="ts">
import { computed } from 'vue';
import { TDesignTag } from './tdesignPrimitiveBridge';
const props = withDefaults(defineProps<{ value?: string; label: string; semantic?: 'default'|'info'|'success'|'warning'|'danger'; statusPrefix?: string }>(), {
  value: '', semantic: 'default', statusPrefix: '状态：',
});
const theme = computed(() => ({
  default: 'default',
  info: 'primary',
  success: 'success',
  warning: 'warning',
  danger: 'danger',
} as const)[props.semantic]);
</script>

<style scoped>
.sc-status-badge[data-semantic-status='info'] {
  border-color: var(--sc-app-info-border);
  background-color: var(--sc-app-info-bg);
  color: var(--sc-app-info-text);
}
</style>
