<template>
  <div
    v-if="open"
    class="sc-design-dialog-backdrop"
    data-semantic-component="ScDialog"
    data-semantic-layer="primitive"
    data-overlay-kind="dialog"
    data-state="open"
    @mousedown.self="emit('close')"
    @keydown="onKeydown"
  >
    <section ref="dialog" :class="['sc-dialog', panelClass]" role="dialog" aria-modal="true" :aria-labelledby="titleId" tabindex="-1">
      <header class="sc-design-dialog__header">
        <h2 :id="titleId">{{ title }}</h2>
        <ScIconButton :label="closeLabel" @click="emit('close')"><ScIcon name="close" /></ScIconButton>
      </header>
      <slot />
      <footer v-if="$slots.actions" class="sc-action-group sc-design-dialog__actions"><slot name="actions" /></footer>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, useId } from 'vue';
import { useModalLifecycle } from '../../composables/useModalLifecycle';
import ScIcon from './ScIcon.vue';
import ScIconButton from './ScIconButton.vue';

const props = withDefaults(defineProps<{ open: boolean; title: string; closeLabel?: string; panelClass?: string }>(), {
  closeLabel: '关闭',
  panelClass: '',
});
const emit = defineEmits<{ close: [] }>();
const dialog = ref<HTMLElement | null>(null);
const titleId = `sc-dialog-${useId()}`;
const { onKeydown } = useModalLifecycle({ open: () => props.open, surface: dialog, close: () => emit('close') });
</script>

<style scoped>
.sc-design-dialog-backdrop { position: fixed; inset: 0; z-index: var(--sc-component-dialog-z-index); display: grid; place-items: center; padding: var(--sc-product-page-gutter); background: var(--sc-app-overlay); animation: sc-overlay-fade-in var(--sc-component-dialog-motion-duration) ease-out; }
.sc-dialog { width: min(100%, var(--sc-component-dialog-width)); max-height: var(--sc-component-dialog-max-height); overflow: auto; animation: sc-dialog-enter var(--sc-component-dialog-motion-duration) ease-out; }
.sc-design-dialog__header { position: sticky; z-index: var(--sc-component-dialog-header-z-index); top: calc(-1 * var(--sc-component-dialog-padding) * 1px); display: flex; align-items: center; justify-content: space-between; gap: var(--sc-product-space-2); margin: calc(-1 * var(--sc-component-dialog-padding) * 1px) calc(-1 * var(--sc-component-dialog-padding) * 1px) var(--sc-product-space-3); padding: calc(var(--sc-component-dialog-padding) * 1px); border-bottom: 1px solid var(--sc-app-border); background: var(--sc-app-panel); }
.sc-dialog h2 { margin: 0; font-size: var(--sc-product-text-section); line-height: 1.35; }
.sc-design-dialog__actions { position: sticky; bottom: calc(-1 * var(--sc-component-dialog-padding) * 1px); justify-content: flex-end; margin: var(--sc-product-space-3) calc(-1 * var(--sc-component-dialog-padding) * 1px) calc(-1 * var(--sc-component-dialog-padding) * 1px); padding: calc(var(--sc-component-dialog-padding) * 1px); border-top: 1px solid var(--sc-app-border); background: var(--sc-app-panel); }
@keyframes sc-overlay-fade-in { from { opacity: 0; } }
@keyframes sc-dialog-enter { from { transform: translateY(8px) scale(0.985); opacity: 0; } }
@media (max-width: 520px) { .sc-design-dialog-backdrop { align-items: end; padding: var(--sc-product-space-2); } .sc-dialog { width: 100%; max-height: calc(100dvh - var(--sc-product-space-4)); border-radius: var(--sc-component-dialog-radius) var(--sc-component-dialog-radius) 0 0; } }
@media (prefers-reduced-motion: reduce) { .sc-design-dialog-backdrop, .sc-dialog { animation: none; } }
</style>
