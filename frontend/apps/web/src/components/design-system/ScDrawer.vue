<template>
  <TDrawer
    :visible="open"
    :header="title"
    drawer-class-name="sc-design-drawer"
    :footer="false"
    :close-btn="closeButton"
    :close-on-esc-keydown="true"
    :close-on-overlay-click="true"
    :destroy-on-close="true"
    size="min(90vw, 420px)"
    role="dialog"
    aria-modal="true"
    :aria-label="title"
    data-ui-engine="tdesign"
    @close="emit('close')"
  >
    <slot />
  </TDrawer>
</template>

<script setup lang="ts">
import { h } from 'vue';
import ScIcon from './ScIcon.vue';
import ScIconButton from './ScIconButton.vue';
import { TDrawer } from './tdesignAdapter';

const props = withDefaults(defineProps<{
  open: boolean;
  title: string;
  closeLabel?: string;
}>(), { closeLabel: '关闭' });
const emit = defineEmits<{ close: [] }>();
const closeButton = () => h(ScIconButton, { label: props.closeLabel }, () => h(ScIcon, { name: 'close' }));
</script>
