<template>
  <div
    v-if="open"
    class="sc-design-drawer-backdrop"
    data-semantic-component="ScDrawer"
    data-semantic-layer="primitive"
    data-overlay-kind="drawer"
    data-state="open"
    @mousedown.self="emit('close')"
    @keydown="onKeydown"
  >
    <aside ref="drawer" class="sc-design-drawer" role="dialog" aria-modal="true" :aria-labelledby="titleId" tabindex="-1">
      <header class="sc-design-drawer__header">
        <h2 :id="titleId">{{ title }}</h2>
        <ScIconButton :label="closeLabel" @click="emit('close')"><ScIcon name="close" /></ScIconButton>
      </header>
      <slot />
    </aside>
  </div>
</template>

<script setup lang="ts">
import { ref, useId } from 'vue';
import { useModalLifecycle } from '../../composables/useModalLifecycle';
import ScIcon from './ScIcon.vue';
import ScIconButton from './ScIconButton.vue';

const props = withDefaults(defineProps<{ open: boolean; title: string; closeLabel?: string }>(), { closeLabel: '关闭' });
const emit = defineEmits<{ close: [] }>();
const drawer = ref<HTMLElement | null>(null);
const titleId = `sc-drawer-${useId()}`;
const { onKeydown } = useModalLifecycle({ open: () => props.open, surface: drawer, close: () => emit('close') });
</script>

<style scoped>
.sc-design-drawer-backdrop { position: fixed; inset: 0; z-index: var(--sc-component-drawer-z-index); display: flex; justify-content: flex-end; background: var(--sc-app-overlay); animation: sc-drawer-overlay-enter var(--sc-component-drawer-motion-duration) ease-out; }
.sc-design-drawer { width: min(90vw, var(--sc-component-drawer-width)); height: 100%; overflow: auto; padding: calc(var(--sc-component-panel-padding) * 1px); background: var(--sc-app-panel); box-shadow: var(--sc-app-shadow-modal); animation: sc-drawer-enter var(--sc-component-drawer-motion-duration) ease-out; }
.sc-design-drawer__header { position: sticky; z-index: var(--sc-component-drawer-header-z-index); top: calc(-1 * var(--sc-component-panel-padding) * 1px); display: flex; align-items: center; justify-content: space-between; gap: var(--sc-product-space-2); margin: calc(-1 * var(--sc-component-panel-padding) * 1px) calc(-1 * var(--sc-component-panel-padding) * 1px) var(--sc-product-space-3); padding: calc(var(--sc-component-panel-padding) * 1px); border-bottom: 1px solid var(--sc-app-border); background: var(--sc-app-panel); }
.sc-design-drawer h2 { margin: 0; font-size: var(--sc-product-text-section); line-height: 1.35; }
@keyframes sc-drawer-overlay-enter { from { opacity: 0; } }
@keyframes sc-drawer-enter { from { transform: translateX(18px); } }
@media (max-width: 520px) { .sc-design-drawer { width: min(94vw, var(--sc-component-drawer-width)); } }
@media (prefers-reduced-motion: reduce) { .sc-design-drawer-backdrop, .sc-design-drawer { animation: none; } }
</style>
