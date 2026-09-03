<template>
  <TDesignDialog :visible="open" :header="false" :footer="false" :close-btn="false" :destroy-on-close="true"
    :close-on-esc-keydown="false" :close-on-overlay-click="dismissible && closeOnBackdrop" :prevent-scroll-through="false"
    :confirm-loading="busy" :dialog-style="{ width: size === 'wide' ? 'var(--sc-component-dialog-wide-width)' : 'var(--sc-component-dialog-width)' }"
    :dialog-class-name="['sc-dialog', panelClass].filter(Boolean).join(' ')" :z-index="dialogZIndex" @close="emit('close')">
    <section ref="surface" v-bind="$attrs" role="dialog" tabindex="-1" aria-modal="true" :aria-labelledby="titleId" :aria-describedby="description ? descriptionId : undefined" :aria-busy="busy || undefined"
      data-semantic-component="ScDialog" data-semantic-driver="tdesign-dialog" data-semantic-layer="primitive"
      data-overlay-kind="dialog" :data-state="open ? 'open' : 'closed'" :aria-hidden="open ? undefined : true" :data-size="size" :data-appearance="appearance" :data-dismissible="dismissible" @keydown="onKeydown">
      <header class="sc-design-dialog__header">
        <div class="sc-design-dialog__heading"><h2 :id="titleId">{{ title }}</h2><p v-if="description" :id="descriptionId">{{ description }}</p></div>
        <div class="sc-design-dialog__header-actions"><slot name="header-actions" /><ScIconButton v-if="dismissible" :label="closeLabel" @click="emit('close')"><ScIcon name="close" /></ScIconButton></div>
      </header>
      <slot />
      <footer v-if="$slots.actions" class="sc-action-group sc-design-dialog__actions"><slot name="actions" /></footer>
    </section>
  </TDesignDialog>
</template>
<script setup lang="ts">
import { ref, useId } from 'vue';
import { TDesignDialog } from './tdesignPrimitiveBridge';
import { useModalLifecycle } from '../../composables/useModalLifecycle';
import ScIcon from './ScIcon.vue';
import ScIconButton from './ScIconButton.vue';
defineOptions({ inheritAttrs: false });
const props = withDefaults(defineProps<{ open: boolean; title: string; description?: string; closeLabel?: string; panelClass?: string; size?: 'default' | 'wide'; appearance?: 'default' | 'workspace'; dismissible?: boolean; closeOnBackdrop?: boolean; busy?: boolean }>(), {
  description: '', closeLabel: '关闭', panelClass: '', size: 'default', appearance: 'default', dismissible: true, closeOnBackdrop: true, busy: false,
});
const emit = defineEmits<{ close: [] }>();
const surface = ref<HTMLElement | null>(null);
const { onKeydown } = useModalLifecycle({
  open: () => props.open,
  surface,
  close: () => emit('close'),
  closeOnEscape: () => props.dismissible !== false,
});
const titleId = `sc-dialog-${useId()}`;
const descriptionId = `${titleId}-description`;
const dialogZIndex = Number.parseInt(getComputedStyle(document.documentElement).getPropertyValue('--sc-component-dialog-z-index'), 10) || 2500;
</script>
<style scoped>
.sc-design-dialog__header{display:flex;align-items:center;justify-content:space-between;gap:var(--sc-product-space-2);margin-bottom:var(--sc-product-space-3);padding-bottom:var(--sc-product-space-3);border-bottom:1px solid var(--sc-app-border)}
.sc-design-dialog__heading{min-width:0}.sc-design-dialog__heading h2{margin:0;font-size:var(--sc-product-text-section);line-height:1.35}.sc-design-dialog__heading p{margin:var(--sc-product-space-1) 0 0;color:var(--sc-app-text-secondary);font-size:var(--sc-product-text-caption)}
.sc-design-dialog__header-actions{display:flex;align-items:center;gap:var(--sc-product-space-2)}.sc-design-dialog__actions{justify-content:flex-end;margin-top:var(--sc-product-space-3);padding-top:var(--sc-product-space-3);border-top:1px solid var(--sc-app-border)}
</style>
