<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="sc-design-drawer-backdrop"
      data-semantic-component="ScDrawer"
      data-semantic-layer="primitive"
      data-overlay-kind="drawer"
      data-state="open"
      :data-size="size"
      :data-dismissible="dismissible"
      @mousedown.self="closeFromBackdrop"
      @keydown="onKeydown"
    >
      <aside ref="drawer" :class="['sc-design-drawer', panelClass]" role="dialog" aria-modal="true" :aria-labelledby="titleId" :aria-describedby="description ? descriptionId : undefined" :aria-busy="busy || undefined" tabindex="-1">
        <header class="sc-design-drawer__header">
          <div class="sc-design-drawer__heading">
            <h2 :id="titleId">{{ title }}</h2>
            <p v-if="description" :id="descriptionId">{{ description }}</p>
          </div>
          <div class="sc-design-drawer__header-actions">
            <slot name="header-actions" />
            <ScIconButton v-if="dismissible" :label="closeLabel" @click="emit('close')"><ScIcon name="close" /></ScIconButton>
          </div>
        </header>
        <slot />
        <footer v-if="$slots.actions" class="sc-action-group sc-design-drawer__actions"><slot name="actions" /></footer>
      </aside>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, useId } from 'vue';
import { useModalLifecycle } from '../../composables/useModalLifecycle';
import ScIcon from './ScIcon.vue';
import ScIconButton from './ScIconButton.vue';

const props = withDefaults(defineProps<{ open: boolean; title: string; description?: string; closeLabel?: string; panelClass?: string; size?: 'default' | 'wide'; dismissible?: boolean; closeOnBackdrop?: boolean; busy?: boolean }>(), {
  description: '', closeLabel: '关闭', panelClass: '', size: 'default', dismissible: true, closeOnBackdrop: true, busy: false,
});
const emit = defineEmits<{ close: [] }>();
const drawer = ref<HTMLElement | null>(null);
const titleId = `sc-drawer-${useId()}`;
const descriptionId = `${titleId}-description`;
const { onKeydown } = useModalLifecycle({ open: () => props.open, surface: drawer, close: () => emit('close'), closeOnEscape: () => props.dismissible });

function closeFromBackdrop() {
  if (props.dismissible && props.closeOnBackdrop) emit('close');
}
</script>

<style scoped>
.sc-design-drawer-backdrop { position: fixed; inset: 0; z-index: var(--sc-component-drawer-z-index); display: flex; justify-content: flex-end; background: var(--sc-app-overlay); animation: sc-drawer-overlay-enter var(--sc-component-drawer-motion-duration) ease-out; }
.sc-design-drawer { width: min(90vw, var(--sc-component-drawer-width)); height: 100%; overflow: auto; padding: calc(var(--sc-component-panel-padding) * 1px); background: var(--sc-app-panel); box-shadow: var(--sc-app-shadow-modal); animation: sc-drawer-enter var(--sc-component-drawer-motion-duration) ease-out; }
.sc-design-drawer-backdrop[data-size="wide"] .sc-design-drawer { width: min(96vw, var(--sc-component-dialog-wide-width)); }
.sc-design-drawer__header { position: sticky; z-index: var(--sc-component-drawer-header-z-index); top: calc(-1 * var(--sc-component-panel-padding) * 1px); display: flex; align-items: center; justify-content: space-between; gap: var(--sc-product-space-2); margin: calc(-1 * var(--sc-component-panel-padding) * 1px) calc(-1 * var(--sc-component-panel-padding) * 1px) var(--sc-product-space-3); padding: calc(var(--sc-component-panel-padding) * 1px); border-bottom: 1px solid var(--sc-app-border); background: var(--sc-app-panel); }
.sc-design-drawer__heading { min-width: 0; }
.sc-design-drawer h2 { margin: 0; font-size: var(--sc-product-text-section); line-height: 1.35; }
.sc-design-drawer__heading p { margin: var(--sc-product-space-1) 0 0; color: var(--sc-app-text-secondary); font-size: var(--sc-product-text-caption); }
.sc-design-drawer__header-actions { display: flex; align-items: center; gap: var(--sc-product-space-2); }
.sc-design-drawer__actions { position: sticky; bottom: calc(-1 * var(--sc-component-panel-padding) * 1px); justify-content: flex-end; margin: var(--sc-product-space-3) calc(-1 * var(--sc-component-panel-padding) * 1px) calc(-1 * var(--sc-component-panel-padding) * 1px); padding: calc(var(--sc-component-panel-padding) * 1px); border-top: 1px solid var(--sc-app-border); background: var(--sc-app-panel); }
@keyframes sc-drawer-overlay-enter { from { opacity: 0; } }
@keyframes sc-drawer-enter { from { transform: translateX(18px); } }
@media (max-width: 520px) { .sc-design-drawer { width: min(94vw, var(--sc-component-drawer-width)); } }
@media (prefers-reduced-motion: reduce) { .sc-design-drawer-backdrop, .sc-design-drawer { animation: none; } }
</style>
