<template>
  <TDialog
    :visible="open"
    :header="title"
    :dialog-class-name="dialogClassName"
    :footer="false"
    :close-btn="closeButton"
    :close-on-esc-keydown="true"
    :close-on-overlay-click="true"
    :destroy-on-close="true"
    placement="center"
    width="min(92vw, 560px)"
    role="dialog"
    aria-modal="true"
    :aria-label="title"
    data-ui-engine="tdesign"
    @close="emit('close')"
  >
    <slot />
    <footer v-if="$slots.actions" class="sc-action-group sc-design-dialog__actions">
      <slot name="actions" />
    </footer>
  </TDialog>
</template>

<script setup lang="ts">
import { computed, h } from 'vue';
import ScIcon from './ScIcon.vue';
import ScIconButton from './ScIconButton.vue';
import { TDialog } from './tdesignAdapter';

const props = withDefaults(defineProps<{
  open: boolean;
  title: string;
  closeLabel?: string;
  panelClass?: string;
}>(), { closeLabel: '关闭', panelClass: '' });
const emit = defineEmits<{ close: [] }>();
const dialogClassName = computed(() => ['sc-dialog', 'sc-design-dialog', props.panelClass].filter(Boolean).join(' '));
const closeButton = () => h(ScIconButton, { label: props.closeLabel }, () => h(ScIcon, { name: 'close' }));
</script>

<style scoped>
.sc-design-dialog__actions {
  justify-content: flex-end;
  margin-top: var(--sc-product-space-3);
  padding-top: var(--sc-product-space-2);
  border-top: 1px solid var(--sc-semantic-border-default);
}
</style>
