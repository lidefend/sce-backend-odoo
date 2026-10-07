<template>
  <ScTooltip :content="hint" :disabled="!hint">
  <button
    v-if="usesStructuredDriver"
    ref="nativeButtonRef"
    data-semantic-component="ScButton"
    data-semantic-primitive="ScButton"
    data-semantic-layer="primitive"
    data-primitive-driver="browser-structured"
    :data-size="size"
    :data-status="status"
    :data-loading="loading || undefined"
    :data-appearance="appearance"
    :type="type"
    :class="['sc-btn', `sc-btn-${variant}`]"
    :disabled="disabled || loading"
    :aria-disabled="ariaDisabled || disabled || loading || undefined"
    :aria-busy="loading || undefined"
    v-bind="attrs"
  >
    <span class="sc-btn__content"><slot /></span>
    <span v-if="loading" class="sc-visually-hidden">{{ loadingLabel }}</span>
  </button>
  <TDesignButton
    v-else
    ref="buttonRef"
    data-semantic-component="ScButton"
    data-semantic-primitive="ScButton"
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
    :aria-disabled="ariaDisabled || disabled || loading || undefined"
    :aria-busy="loading || undefined"
    v-bind="attrs"
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
  ariaDisabled?: boolean;
  loading?: boolean;
  loadingLabel?: string;
  appearance?: 'default' | 'structured-content' | 'metric' | 'section-tab' | 'menu-item' | 'tree-item' | 'toolbar-chip' | 'toolbar-menu-toggle' | 'status-chip' | 'info-action' | 'favorite-toggle' | 'smart-action' | 'relation-tag' | 'surface-tile' | 'outline-action' | 'column-settings' | 'summary-chip' | 'breadcrumb-item' | 'context-action' | 'auth-link' | 'readonly-relation' | 'primary-submit' | 'dashboard-action' | 'dashboard-quick-link' | 'dashboard-recent-link' | 'scope-option' | 'scope-segment' | 'account-context' | 'account-context-compact';
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
/* The list-surface narrow layout owns its own breakpoint (max-width: 760px): the
   leading/query tracks and the reserved auxiliary track are declared there, and
   the mobile record presentation is active for the whole band. The column-settings
   control must therefore keep its declared touch size across that same band, not
   only below 520px, or the 521-760px slice reports a desktop-sized control inside
   the mobile presentation and overflows the reserved auxiliary track. */
@media (max-width: 760px) {
  [data-appearance='column-settings'] { min-width: 44px; min-height: 44px; padding-inline: 0; }
}
</style>
