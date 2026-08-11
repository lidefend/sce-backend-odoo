<template>
  <form
    v-if="visible"
    class="contract-mode-prompt"
    @submit.prevent="$emit('submit')"
  >
    <label
      v-for="field in fields"
      :key="`contract-prompt-${field.name}`"
      class="contract-mode-prompt-field"
    >
      <span>{{ field.label }}</span>
      <ScSelect
        v-if="field.options.length"
        :model-value="String(values[field.name] || '')"
        :label="field.label"
        :required="field.required"
        :disabled="busy"
        @update:model-value="$emit('value-change', { fieldName: field.name, value: $event })"
      >
        <option value=""></option>
        <option v-for="option in field.options" :key="option.value" :value="option.value">{{ option.label }}</option>
      </ScSelect>
      <ScTextField
        v-else
        :model-value="String(values[field.name] || '')"
        :label="field.label"
        :required="field.required"
        :disabled="busy"
        @update:model-value="$emit('value-change', { fieldName: field.name, value: $event })"
      />
    </label>
    <ScButton type="submit" variant="primary" class="chip-btn" :disabled="busy">确定</ScButton>
    <ScButton type="button" variant="ghost" class="ghost" :disabled="busy" @click="$emit('cancel')">取消</ScButton>
  </form>
</template>

<script setup lang="ts">
import type { ContractPromptField } from './types';
import ScButton from '../../components/design-system/ScButton.vue';
import ScSelect from '../../components/design-system/ScSelect.vue';
import ScTextField from '../../components/design-system/ScTextField.vue';

defineProps<{
  visible: boolean;
  fields: ContractPromptField[];
  values: Record<string, string>;
  busy: boolean;
}>();

defineEmits<{
  submit: [];
  cancel: [];
  'value-change': [payload: { fieldName: string; value: string }];
}>();

</script>

<style scoped src="./ContractPromptActionForm.css"></style>
