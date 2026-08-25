<template>
  <ScDialog
    :open="dialog.open"
    :title="dialog.title"
    close-label="关闭新建窗口"
    panel-class="relation-create-dialog"
    data-professional-relation-lifecycle="create"
    @close="$emit('close')"
  >
    <iframe
      v-if="dialog.open && dialog.src"
      ref="frameRef"
      class="relation-create-dialog__frame"
      data-relation-create-form
      :src="dialog.src"
      :title="dialog.title"
    />
  </ScDialog>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue';
import ScDialog from '../../components/design-system/ScDialog.vue';
import {
  resolveRelationCreateDialogEvent,
  type RelationCreateDialogState,
  type RelationCreatedDialogResult,
} from './relationCreateDialogRuntime';

const props = defineProps<{ dialog: RelationCreateDialogState }>();
const emit = defineEmits<{
  close: [];
  created: [result: RelationCreatedDialogResult];
}>();
const frameRef = ref<HTMLIFrameElement | null>(null);

function onMessage(event: MessageEvent) {
  const resolved = resolveRelationCreateDialogEvent({
    dialog: props.dialog,
    eventOrigin: event.origin,
    expectedOrigin: window.location.origin,
    sourceMatches: event.source === frameRef.value?.contentWindow,
    payload: event.data,
  });
  if (resolved?.kind === 'created') emit('created', resolved.result);
  if (resolved?.kind === 'cancelled') emit('close');
}

function stopListening() {
  window.removeEventListener('message', onMessage);
  frameRef.value = null;
}

watch(
  () => props.dialog.open,
  (open) => {
    stopListening();
    if (open) window.addEventListener('message', onMessage);
  },
  { immediate: true },
);
onBeforeUnmount(stopListening);
</script>

<style scoped src="./RelationCreateDialog.css"></style>
