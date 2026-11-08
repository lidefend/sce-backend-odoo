<template>
  <ScDialog
    :open="open"
    :title="title"
    description="该操作需要填写原因，提交后将随操作一并发送。"
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
      <ScButton variant="ghost" @click="settle(null)">取消</ScButton>
      <ScButton variant="primary" :disabled="!reason.trim()" @click="submit">提交操作</ScButton>
    </template>
  </ScDialog>
</template>

<script setup lang="ts">
import { nextTick, ref } from 'vue';
import ScButton from '../../components/design-system/ScButton.vue';
import ScDialog from '../../components/design-system/ScDialog.vue';
import ScFormField from '../../components/design-system/ScFormField.vue';
import ScTextarea from '../../components/design-system/ScTextarea.vue';

const open = ref(false);
const title = ref('填写操作原因');
const label = ref('操作原因');
const help = ref('请说明本次操作原因。');
const reason = ref('');
const reasonRef = ref<InstanceType<typeof ScTextarea> | null>(null);
let pendingResolve: ((value: string | null) => void) | null = null;
let trigger: HTMLElement | null = null;

function request(input: { title?: string; label?: string; help?: string }) {
  if (pendingResolve) return Promise.resolve(null);
  trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  title.value = input.title || '填写操作原因';
  label.value = input.label || '操作原因';
  help.value = input.help || '请说明本次操作原因。';
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
