<template>
  <TDesignButton
    ref="buttonRef"
    data-semantic-component="ScButton"
    data-semantic-layer="primitive"
    :data-size="size"
    :data-status="status"
    :data-loading="loading || undefined"
    :type="type"
    :class="['sc-btn', `sc-btn-${variant}`]"
    :theme="presentation.theme"
    :variant="presentation.variant"
    :size="size"
    :loading="loading"
    :disabled="disabled || loading"
    :aria-disabled="disabled || loading || undefined"
    :aria-busy="loading || undefined"
  >
    <span class="sc-btn__content"><slot /></span>
    <span v-if="loading" class="sc-visually-hidden">{{ loadingLabel }}</span>
  </TDesignButton>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { TDesignButton } from './tdesignPrimitiveBridge';
import { tdesignButtonPresentation, type ScButtonVariant, type ScPrimitiveSize, type ScPrimitiveStatus } from './primitiveAdapter';

const props = withDefaults(defineProps<{
  type?: 'button' | 'submit' | 'reset';
  variant?: ScButtonVariant;
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

const presentation = computed(() => tdesignButtonPresentation(props.variant, props.status));
const buttonRef = ref<{ $el?: HTMLButtonElement } | null>(null);

defineExpose({
  focus: () => buttonRef.value?.$el?.focus(),
});
</script>
