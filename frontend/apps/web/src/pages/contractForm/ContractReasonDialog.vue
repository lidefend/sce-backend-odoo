<template>
  <ScDialog
    :open="open"
    :title="title"
    panel-class="contract-reason-dialog"
    @close="settle(null)"
  >
    <ScFormField
      field-key="action-reason"
      :label="label"
      required
      :help="help"
    >
      <template #default="{ controlId, describedBy }">
        <ScTextarea
          :id="controlId"
          ref="reasonRef"
          v-model="reason"
          :rows="3"
          required
          :described-by="describedBy"
          @keydown.ctrl.enter.prevent="submit"
          @keydown.meta.enter.prevent="submit"
        />
      </template>
    </ScFormField>
    <template #actions>
      <ScButton variant="ghost" @click="settle(null)">{{ cancelLabel }}</ScButton>
      <ScButton variant="primary" :disabled="!reason.trim()" @click="submit">{{ submitLabel }}</ScButton>
    </template>
  </ScDialog>
</template>

<script setup lang="ts">
import { nextTick, ref } from 'vue';
import ScButton from '../../components/design-system/ScButton.vue';
import ScDialog from '../../components/design-system/ScDialog.vue';
import ScFormField from '../../components/design-system/ScFormField.vue';
import ScTextarea from '../../components/design-system/ScTextarea.vue';
import type { ContractAction } from './types';

const open = ref(false);
const title = ref('');
const label = ref('');
const help = ref('');
const submitLabel = ref('');
const cancelLabel = ref('');
const reason = ref('');
const reasonRef = ref<InstanceType<typeof ScTextarea> | null>(null);
let pendingResolve: ((value: string | null) => void) | null = null;
let trigger: HTMLElement | null = null;

function request(input: NonNullable<ContractAction['reasonPresentation']>) {
  if (pendingResolve) return Promise.resolve(null);
  trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  title.value = input.title;
  label.value = input.label;
  help.value = input.help;
  submitLabel.value = input.submitLabel;
  cancelLabel.value = input.cancelLabel;
  reason.value = '';
  open.value = true;
  void nextTick(() => reasonRef.value?.focus());
  return new Promise<string | null>((resolve) => {
    pendingResolve = resolve;
  });
}

function submit() {
  const value = reason.value.trim();
  if (!value) return;
  settle(value);
}

async function settle(value: string | null) {
  const resolve = pendingResolve;
  pendingResolve = null;
  open.value = false;
  resolve?.(value);
  await nextTick();
  trigger?.focus();
  trigger = null;
}

defineExpose({ request });
</script>
