<template>
  <TDesignTag size="small" variant="light" :theme="theme" :title="label"
    data-semantic-component="ScStatusBadge" data-semantic-driver="tdesign-tag"
    data-semantic-layer="primitive" :data-status="value">
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
