<template>
  <ScDialog
    :open="dialog.open"
    title="新增字段"
    close-label="取消新增字段"
    panel-class="low-code-field-create-dialog"
    @close="$emit('close')"
  >
    <form
      class="low-code-field-create-form"
      data-semantic-component="LowCodeFieldCreateForm"
      @submit.prevent="$emit('submit')"
    >
      <ScFormField label="字段标题" field-key="low-code-field-label" required>
        <template #default="{ controlId, describedBy }">
          <ScInput
            :id="controlId"
            autofocus
            :model-value="dialog.label"
            required
            :disabled="busy"
            :described-by="describedBy"
            @update:model-value="$emit('update:label', $event)"
          />
        </template>
      </ScFormField>
      <ScFormField label="字段类型" field-key="low-code-field-type" required>
        <template #default="{ controlId, describedBy }">
          <ScSelect
            :id="controlId"
            :model-value="dialog.ttype"
            required
            :disabled="busy"
            :described-by="describedBy"
            :options="[
              { value: 'char', label: '单行文本' },
              { value: 'text', label: '多行文本' },
              { value: 'integer', label: '整数' },
              { value: 'float', label: '小数' },
              { value: 'boolean', label: '是/否' },
              { value: 'date', label: '日期' },
              { value: 'datetime', label: '日期时间' },
              { value: 'html', label: '富文本' },
            ]"
            @update:model-value="$emit('update:ttype', $event)"
          />
        </template>
      </ScFormField>
      <footer class="low-code-field-create-actions" data-semantic-component="LowCodeFieldCreateActions">
        <ScButton type="button" variant="ghost" :disabled="busy" @click="$emit('close')">取消</ScButton>
        <ScButton type="submit" variant="primary" :disabled="busy">创建字段</ScButton>
      </footer>
    </form>
  </ScDialog>
</template>

<script setup lang="ts">
import ScButton from '../../components/design-system/ScButton.vue';
import ScDialog from '../../components/design-system/ScDialog.vue';
import ScFormField from '../../components/design-system/ScFormField.vue';
import ScInput from '../../components/design-system/ScInput.vue';
import ScSelect from '../../components/design-system/ScSelect.vue';

export type LowCodeFieldCreateDialogState = {
  open: boolean;
  afterFieldKey: string;
  groupTitle: string;
  sequence: number;
  label: string;
  ttype: string;
};

defineProps<{
  dialog: LowCodeFieldCreateDialogState;
  busy: boolean;
}>();

defineEmits<{
  close: [];
  submit: [];
  'update:label': [value: string];
  'update:ttype': [value: string];
}>();

</script>

<style scoped src="./LowCodeFieldCreateDialog.css"></style>
