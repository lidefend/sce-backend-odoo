<template>
  <TDesignDrawer :visible="open" :header="false" :footer="false" :close-btn="false"
    :close-on-esc-keydown="false" :close-on-overlay-click="dismissible && closeOnBackdrop" :prevent-scroll-through="false"
    :size="size === 'wide' ? 'var(--sc-component-dialog-wide-width)' : 'var(--sc-component-drawer-width)'"
    :drawer-class-name="['sc-design-drawer', panelClass].filter(Boolean).join(' ')" :z-index="drawerZIndex" @close="emit('close')">
    <aside ref="surface" v-bind="$attrs" role="dialog" tabindex="-1" aria-modal="true" :aria-labelledby="titleId" :aria-describedby="description ? descriptionId : undefined" :aria-busy="busy || undefined"
      data-semantic-component="ScDrawer" data-semantic-driver="tdesign-drawer" data-semantic-layer="primitive"
      data-overlay-kind="drawer" :data-state="open ? 'open' : 'closed'" :aria-hidden="open ? undefined : true" :data-size="size" :data-dismissible="dismissible" @keydown="onKeydown">
      <header class="sc-design-drawer__header">
        <div class="sc-design-drawer__heading"><h2 :id="titleId">{{ title }}</h2><p v-if="description" :id="descriptionId">{{ description }}</p></div>
        <div class="sc-design-drawer__header-actions"><slot name="header-actions" /><ScIconButton v-if="dismissible" :label="closeLabel" @click="emit('close')"><ScIcon name="close" /></ScIconButton></div>
      </header>
      <slot />
      <footer v-if="$slots.actions" class="sc-action-group sc-design-drawer__actions"><slot name="actions" /></footer>
    </aside>
  </TDesignDrawer>
</template>
<script setup lang="ts">
import { ref, useId } from 'vue';
import { TDesignDrawer } from './tdesignPrimitiveBridge';
import { useModalLifecycle } from '../../composables/useModalLifecycle';
import ScIcon from './ScIcon.vue';
import ScIconButton from './ScIconButton.vue';
defineOptions({ inheritAttrs: false });
const props = withDefaults(defineProps<{ open: boolean; title: string; description?: string; closeLabel?: string; panelClass?: string; size?: 'default' | 'wide'; dismissible?: boolean; closeOnBackdrop?: boolean; busy?: boolean }>(), {
  description: '', closeLabel: '关闭', panelClass: '', size: 'default', dismissible: true, closeOnBackdrop: true, busy: false,
});
const emit = defineEmits<{ close: [] }>();
const surface = ref<HTMLElement | null>(null);
const { onKeydown } = useModalLifecycle({
  open: () => props.open,
  surface,
  close: () => emit('close'),
  closeOnEscape: () => props.dismissible !== false,
});
const titleId = `sc-drawer-${useId()}`;
const descriptionId = `${titleId}-description`;
const drawerZIndex = Number.parseInt(getComputedStyle(document.documentElement).getPropertyValue('--sc-component-drawer-z-index'), 10) || 2400;
</script>
<style scoped>
.sc-design-drawer__header{display:flex;align-items:center;justify-content:space-between;gap:var(--sc-product-space-2);margin-bottom:var(--sc-product-space-3);padding-bottom:var(--sc-product-space-3);border-bottom:1px solid var(--sc-app-border)}
.sc-design-drawer__heading{min-width:0}.sc-design-drawer__heading h2{margin:0;font-size:var(--sc-product-text-section);line-height:1.35}.sc-design-drawer__heading p{margin:var(--sc-product-space-1) 0 0;color:var(--sc-app-text-secondary);font-size:var(--sc-product-text-caption)}
.sc-design-drawer__header-actions{display:flex;align-items:center;gap:var(--sc-product-space-2)}.sc-design-drawer__actions{justify-content:flex-end;margin-top:var(--sc-product-space-3);padding-top:var(--sc-product-space-3);border-top:1px solid var(--sc-app-border)}
</style>
