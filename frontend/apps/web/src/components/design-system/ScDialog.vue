<template>
  <TDesignDialog :visible="open" :header="false" :footer="false" :close-btn="false"
    :close-on-esc-keydown="dismissible" :close-on-overlay-click="dismissible && closeOnBackdrop"
    :confirm-loading="busy" :width="size === 'wide' ? 'var(--sc-component-dialog-wide-width)' : 'var(--sc-component-dialog-width)'"
    :dialog-class-name="['sc-dialog', panelClass].filter(Boolean).join(' ')" :z-index="dialogZIndex"
    data-semantic-component="ScDialog" data-semantic-driver="tdesign-dialog" data-semantic-layer="primitive"
    data-overlay-kind="dialog" data-state="open" :data-size="size" :data-dismissible="dismissible" @close="emit('close')">
    <section role="dialog" aria-modal="true" :aria-labelledby="titleId" :aria-describedby="description ? descriptionId : undefined" :aria-busy="busy || undefined">
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
import { useId } from 'vue';
import { TDesignDialog } from './tdesignPrimitiveBridge';
import ScIcon from './ScIcon.vue';
import ScIconButton from './ScIconButton.vue';
withDefaults(defineProps<{ open: boolean; title: string; description?: string; closeLabel?: string; panelClass?: string; size?: 'default' | 'wide'; dismissible?: boolean; closeOnBackdrop?: boolean; busy?: boolean }>(), {
  description: '', closeLabel: '关闭', panelClass: '', size: 'default', dismissible: true, closeOnBackdrop: true, busy: false,
});
const emit = defineEmits<{ close: [] }>();
const titleId = `sc-dialog-${useId()}`;
const descriptionId = `${titleId}-description`;
const dialogZIndex = Number.parseInt(getComputedStyle(document.documentElement).getPropertyValue('--sc-component-dialog-z-index'), 10) || 2500;
</script>
<style scoped>
.sc-design-dialog__header{display:flex;align-items:center;justify-content:space-between;gap:var(--sc-product-space-2);margin-bottom:var(--sc-product-space-3);padding-bottom:var(--sc-product-space-3);border-bottom:1px solid var(--sc-app-border)}
.sc-design-dialog__heading{min-width:0}.sc-design-dialog__heading h2{margin:0;font-size:var(--sc-product-text-section);line-height:1.35}.sc-design-dialog__heading p{margin:var(--sc-product-space-1) 0 0;color:var(--sc-app-text-secondary);font-size:var(--sc-product-text-caption)}
.sc-design-dialog__header-actions{display:flex;align-items:center;gap:var(--sc-product-space-2)}.sc-design-dialog__actions{justify-content:flex-end;margin-top:var(--sc-product-space-3);padding-top:var(--sc-product-space-3);border-top:1px solid var(--sc-app-border)}
</style>
