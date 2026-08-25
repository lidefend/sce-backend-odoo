<template>
  <button
    data-semantic-component="ScButton"
    data-semantic-layer="primitive"
    :data-size="size"
    :data-status="status"
    :data-loading="loading || undefined"
    :type="type"
    :class="['sc-btn', `sc-btn-${variant}`]"
    :disabled="disabled || loading"
    :aria-disabled="disabled || loading || undefined"
    :aria-busy="loading || undefined"
  >
    <span v-if="loading" class="sc-btn__spinner" aria-hidden="true" />
    <span class="sc-btn__content"><slot /></span>
    <span v-if="loading" class="sc-visually-hidden">{{ loadingLabel }}</span>
  </button>
</template>

<script setup lang="ts">
import type { ScPrimitiveSize, ScPrimitiveStatus } from './primitiveAdapter';

withDefaults(defineProps<{
  type?: 'button' | 'submit' | 'reset';
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: ScPrimitiveSize;
  status?: ScPrimitiveStatus;
  disabled?: boolean;
  loading?: boolean;
  loadingLabel?: string;
}>(), {
  type: 'button',
  variant: 'secondary',
  size: 'medium',
  status: 'default',
  loadingLabel: '处理中',
});
</script>
