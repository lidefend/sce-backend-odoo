<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="sc-design-dialog-backdrop"
      data-semantic-component="ScDialog"
      data-semantic-layer="primitive"
      data-overlay-kind="dialog"
      data-state="open"
      :data-size="size"
      :data-dismissible="dismissible"
      @mousedown.self="closeFromBackdrop"
      @keydown="onKeydown"
    >
      <section ref="dialog" :class="['sc-dialog', panelClass]" role="dialog" aria-modal="true" :aria-labelledby="titleId" :aria-describedby="description ? descriptionId : undefined" :aria-busy="busy || undefined" tabindex="-1">
        <header class="sc-design-dialog__header">
          <div class="sc-design-dialog__heading">
            <h2 :id="titleId">{{ title }}</h2>
            <p v-if="description" :id="descriptionId">{{ description }}</p>
          </div>
          <div class="sc-design-dialog__header-actions">
            <slot name="header-actions" />
            <ScIconButton v-if="dismissible" :label="closeLabel" @click="emit('close')"><ScIcon name="close" /></ScIconButton>
          </div>
        </header>
        <slot />
        <footer v-if="$slots.actions" class="sc-action-group sc-design-dialog__actions"><slot name="actions" /></footer>
      </section>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, useId } from 'vue';
import { useModalLifecycle } from '../../composables/useModalLifecycle';
import ScIcon from './ScIcon.vue';
import ScIconButton from './ScIconButton.vue';

const props = withDefaults(defineProps<{ open: boolean; title: string; description?: string; closeLabel?: string; panelClass?: string; size?: 'default' | 'wide'; dismissible?: boolean; closeOnBackdrop?: boolean; busy?: boolean }>(), {
  description: '',
  closeLabel: '关闭',
  panelClass: '',
  size: 'default',
  dismissible: true,
  closeOnBackdrop: true,
  busy: false,
});
const emit = defineEmits<{ close: [] }>();
const dialog = ref<HTMLElement | null>(null);
const titleId = `sc-dialog-${useId()}`;
const descriptionId = `${titleId}-description`;
const { onKeydown } = useModalLifecycle({ open: () => props.open, surface: dialog, close: () => emit('close'), closeOnEscape: () => props.dismissible });

function closeFromBackdrop() {
  if (props.dismissible && props.closeOnBackdrop) emit('close');
}
</script>

<style scoped>
.sc-design-dialog-backdrop { position: fixed; inset: 0; z-index: var(--sc-component-dialog-z-index); display: grid; place-items: center; padding: var(--sc-product-page-gutter); background: var(--sc-app-overlay); animation: sc-overlay-fade-in var(--sc-component-dialog-motion-duration) ease-out; }
.sc-dialog { width: min(100%, var(--sc-component-dialog-width)); max-height: var(--sc-component-dialog-max-height); overflow: auto; animation: sc-dialog-enter var(--sc-component-dialog-motion-duration) ease-out; }
.sc-design-dialog-backdrop[data-size="wide"] .sc-dialog { width: min(100%, var(--sc-component-dialog-wide-width)); }
.sc-design-dialog__header { position: sticky; z-index: var(--sc-component-dialog-header-z-index); top: calc(-1 * var(--sc-component-dialog-padding) * 1px); display: flex; align-items: center; justify-content: space-between; gap: var(--sc-product-space-2); margin: calc(-1 * var(--sc-component-dialog-padding) * 1px) calc(-1 * var(--sc-component-dialog-padding) * 1px) var(--sc-product-space-3); padding: calc(var(--sc-component-dialog-padding) * 1px); border-bottom: 1px solid var(--sc-app-border); background: var(--sc-app-panel); }
.sc-design-dialog__heading { min-width: 0; }
.sc-dialog h2 { margin: 0; font-size: var(--sc-product-text-section); line-height: 1.35; }
.sc-design-dialog__heading p { margin: var(--sc-product-space-1) 0 0; color: var(--sc-app-text-secondary); font-size: var(--sc-product-text-caption); }
.sc-design-dialog__header-actions { display: flex; align-items: center; gap: var(--sc-product-space-2); }
.sc-design-dialog__actions { position: sticky; bottom: calc(-1 * var(--sc-component-dialog-padding) * 1px); justify-content: flex-end; margin: var(--sc-product-space-3) calc(-1 * var(--sc-component-dialog-padding) * 1px) calc(-1 * var(--sc-component-dialog-padding) * 1px); padding: calc(var(--sc-component-dialog-padding) * 1px); border-top: 1px solid var(--sc-app-border); background: var(--sc-app-panel); }
@keyframes sc-overlay-fade-in { from { opacity: 0; } }
@keyframes sc-dialog-enter { from { transform: translateY(8px) scale(0.985); opacity: 0; } }
@media (max-width: 520px) { .sc-design-dialog-backdrop { align-items: end; padding: var(--sc-product-space-2); } .sc-dialog { width: 100%; max-height: calc(100dvh - var(--sc-product-space-4)); border-radius: var(--sc-component-dialog-radius) var(--sc-component-dialog-radius) 0 0; } }
@media (prefers-reduced-motion: reduce) { .sc-design-dialog-backdrop, .sc-dialog { animation: none; } }
</style>
