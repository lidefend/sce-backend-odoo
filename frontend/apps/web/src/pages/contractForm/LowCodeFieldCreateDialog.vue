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
      @submit.prevent="$emit('submit')"
    >
      <label class="contract-mode-prompt-field">
        <span>字段标题</span>
        <input autofocus :value="dialog.label" required :disabled="busy" @input="$emit('update:label', inputValue($event))" />
      </label>
      <label class="contract-mode-prompt-field">
        <span>字段类型</span>
        <select :value="dialog.ttype" required :disabled="busy" @change="$emit('update:ttype', inputValue($event))">
          <option value="char">单行文本</option>
          <option value="text">多行文本</option>
          <option value="integer">整数</option>
          <option value="float">小数</option>
          <option value="boolean">是/否</option>
          <option value="date">日期</option>
          <option value="datetime">日期时间</option>
          <option value="html">富文本</option>
        </select>
      </label>
      <footer class="low-code-field-create-actions">
        <button type="submit" class="chip-btn" :disabled="busy">创建字段</button>
        <button type="button" class="ghost" :disabled="busy" @click="$emit('close')">取消</button>
      </footer>
    </form>
  </ScDialog>
</template>

<script setup lang="ts">
import ScDialog from '../../components/design-system/ScDialog.vue';

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

function inputValue(event: Event) {
  return String((event.target as HTMLInputElement | HTMLSelectElement).value || '');
}
</script>

<style scoped src="./LowCodeFieldCreateDialog.css"></style>
