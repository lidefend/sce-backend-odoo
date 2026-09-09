<template>
  <ScDialog
    :open="open"
    :title="`确认${actionLabel}`"
    close-label="取消操作"
    panel-class="intent-confirmation"
    data-professional-workflow-component="confirm-dialog"
    data-dialog-purpose="intent-confirmation"
    :data-state="open ? 'open' : 'closed'"
    @close="settle(false)"
  >
    <p id="intent-confirmation-message">{{ message }}</p>
    <template #actions>
      <ScButton variant="ghost" autofocus @click="settle(false)">取消</ScButton>
      <ScButton variant="primary" @click="settle(true)">确认{{ actionLabel }}</ScButton>
    </template>
  </ScDialog>
</template>

<script setup lang="ts">
import { nextTick, ref } from 'vue';
import ScButton from '../design-system/ScButton.vue';
import ScDialog from '../design-system/ScDialog.vue';

const open = ref(false);
const actionLabel = ref('操作');
const message = ref('');
let pendingResolve: ((confirmed: boolean) => void) | null = null;
let trigger: HTMLElement | null = null;

function confirm(input: { actionLabel: string; message: string }) {
  if (pendingResolve) return Promise.resolve(false);
  trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  actionLabel.value = input.actionLabel || '操作';
  message.value = input.message || '该操作执行后将立即生效，请确认是否继续。';
  open.value = true;
  return new Promise<boolean>((resolve) => { pendingResolve = resolve; });
}

async function settle(confirmed: boolean) {
  const resolve = pendingResolve;
  pendingResolve = null;
  open.value = false;
  resolve?.(confirmed);
  await nextTick();
  trigger?.focus();
  trigger = null;
}

defineExpose({ confirm });
</script>

<style scoped>
#intent-confirmation-message { margin: var(--sc-product-space-2) 0; line-height: 1.6; }
</style>
