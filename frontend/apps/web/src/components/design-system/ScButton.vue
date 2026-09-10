<template>
  <ScTooltip :content="hint" :disabled="!hint">
  <button
    v-if="usesStructuredDriver"
    v-bind="attrs"
    ref="nativeButtonRef"
    data-semantic-component="ScButton"
    data-semantic-layer="primitive"
    data-primitive-driver="browser-structured"
    :data-size="size"
    :data-status="status"
    :data-loading="loading || undefined"
    :data-appearance="appearance"
    :type="type"
    :class="['sc-btn', `sc-btn-${variant}`]"
    :disabled="disabled || loading"
    :aria-disabled="disabled || loading || undefined"
    :aria-busy="loading || undefined"
  >
    <span class="sc-btn__content"><slot /></span>
    <span v-if="loading" class="sc-visually-hidden">{{ loadingLabel }}</span>
  </button>
  <TDesignButton
    v-else
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
  appearance?: 'default' | 'structured-content' | 'metric' | 'section-tab' | 'menu-item' | 'tree-item' | 'toolbar-chip' | 'toolbar-menu-toggle' | 'status-chip' | 'info-action' | 'favorite-toggle' | 'smart-action' | 'relation-tag' | 'surface-tile' | 'outline-action' | 'column-settings' | 'summary-chip' | 'breadcrumb-item' | 'context-action' | 'auth-link' | 'primary-submit' | 'dashboard-action' | 'dashboard-quick-link' | 'dashboard-recent-link' | 'scope-option' | 'scope-segment' | 'account-context' | 'account-context-compact';
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
const nativeButtonRef = ref<HTMLButtonElement | null>(null);
const usesStructuredDriver = computed(() => ['structured-content', 'metric', 'dashboard-quick-link'].includes(props.appearance));

defineExpose({
  focus: () => {
    if (usesStructuredDriver.value) return nativeButtonRef.value?.focus();
    const root = buttonRef.value?.$el;
    const target = root instanceof HTMLButtonElement ? root : root?.querySelector<HTMLButtonElement>('button');
    target?.focus();
  },
});
</script>

<style scoped>
[data-appearance='section-tab'][aria-current='location'] {
  background: var(--sc-app-info-bg);
  color: var(--sc-app-accent);
  box-shadow: inset 0 -2px 0 var(--sc-app-accent);
}
@media (max-width: 520px) {
  [data-appearance='column-settings'] { min-width: 44px; min-height: 44px; padding-inline: 0; }
}
</style>
