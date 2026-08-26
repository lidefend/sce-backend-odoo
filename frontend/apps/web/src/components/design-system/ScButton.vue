<template>
  <ScTooltip :content="hint" :disabled="!hint">
  <TDesignButton
    v-bind="attrs"
    ref="buttonRef"
    data-semantic-component="ScButton"
    data-semantic-layer="primitive"
    :data-size="size"
    :data-status="status"
    :data-loading="loading || undefined"
    :data-appearance="appearance"
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
  </ScTooltip>
</template>

<script setup lang="ts">
import { computed, ref, useAttrs } from 'vue';
import { TDesignButton } from './tdesignPrimitiveBridge';
import ScTooltip from './ScTooltip.vue';
import { tdesignButtonPresentation, type ScButtonVariant, type ScPrimitiveSize, type ScPrimitiveStatus } from './primitiveAdapter';

defineOptions({ inheritAttrs: false });

const props = withDefaults(defineProps<{
  type?: 'button' | 'submit' | 'reset';
  variant?: ScButtonVariant;
  size?: ScPrimitiveSize;
  status?: ScPrimitiveStatus;
  disabled?: boolean;
  loading?: boolean;
  loadingLabel?: string;
  appearance?: 'default' | 'section-tab' | 'menu-item' | 'tree-item' | 'toolbar-chip' | 'toolbar-menu-toggle' | 'status-chip' | 'info-action' | 'favorite-toggle' | 'smart-action' | 'relation-tag' | 'surface-tile' | 'outline-action' | 'summary-chip' | 'breadcrumb-item' | 'context-action' | 'auth-link' | 'primary-submit' | 'dashboard-action' | 'dashboard-quick-link' | 'dashboard-recent-link';
}>(), {
  type: 'button',
  variant: 'secondary',
  size: 'medium',
  status: 'default',
  loadingLabel: '处理中',
  appearance: 'default',
});

const presentation = computed(() => tdesignButtonPresentation(props.variant, props.status));
const attrs = useAttrs();
const hint = computed(() => typeof attrs.title === 'string' ? attrs.title : '');
const buttonRef = ref<{ $el?: HTMLElement } | null>(null);

defineExpose({
  focus: () => {
    const root = buttonRef.value?.$el;
    const target = root instanceof HTMLButtonElement ? root : root?.querySelector<HTMLButtonElement>('button');
    target?.focus();
  },
});
</script>
