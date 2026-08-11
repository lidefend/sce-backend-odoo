<template>
  <TButton
    :type="type"
    :class="['sc-btn', 'sc-design-button', `sc-btn-${variant}`]"
    :theme="tdTheme"
    :variant="tdVariant"
    :disabled="disabled"
    :loading="loading"
    data-ui-engine="tdesign"
    :aria-busy="loading || undefined"
  >
    <span v-if="loading" class="sc-visually-hidden">{{ loadingLabel }}</span>
    <slot />
  </TButton>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { TButton } from './tdesignAdapter';

const props = withDefaults(defineProps<{
  type?: 'button' | 'submit' | 'reset';
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  disabled?: boolean;
  loading?: boolean;
  loadingLabel?: string;
}>(), {
  type: 'button',
  variant: 'secondary',
  disabled: false,
  loading: false,
  loadingLabel: '处理中',
});

const tdTheme = computed(() => props.variant === 'primary'
  ? 'primary'
  : props.variant === 'danger' ? 'danger' : 'default');
const tdVariant = computed(() => props.variant === 'ghost'
  ? 'text'
  : props.variant === 'primary' ? 'base' : 'outline');
</script>
