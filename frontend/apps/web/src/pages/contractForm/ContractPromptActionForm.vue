<template>
  <form
    v-if="visible"
    class="contract-mode-prompt"
    data-semantic-component="ContractPromptActionForm"
    @submit.prevent="$emit('submit')"
  >
    <ScFormField
      v-for="field in fields"
      :key="`contract-prompt-${field.name}`"
      class="contract-mode-prompt-field"
      :field-key="field.name"
      :label="field.label"
      :required="field.required"
    >
      <template #default="{ controlId, describedBy }">
        <ScSelect
          v-if="field.options.length"
          :id="controlId"
          :model-value="String(values[field.name] || '')"
          :required="field.required"
          :disabled="busy"
          :described-by="describedBy"
          @update:model-value="$emit('value-change', { fieldName: field.name, value: $event })"
        >
          <option value=""></option>
          <option v-for="option in field.options" :key="option.value" :value="option.value">{{ option.label }}</option>
        </ScSelect>
        <ScInput
          v-else
          :id="controlId"
          :model-value="String(values[field.name] || '')"
          :disabled="busy"
          :described-by="describedBy"
          :aria-required="field.required || undefined"
          @update:model-value="$emit('value-change', { fieldName: field.name, value: $event })"
        />
      </template>
    </ScFormField>
    <div class="contract-mode-prompt-actions" data-semantic-component="ContractPromptActionBar">
      <ScButton type="button" variant="ghost" :disabled="busy" @click="$emit('cancel')">取消</ScButton>
      <ScButton type="submit" variant="primary" :disabled="busy">确定</ScButton>
    </div>
  </form>
</template>

<script setup lang="ts">
import ScButton from '../../components/design-system/ScButton.vue';
import ScFormField from '../../components/design-system/ScFormField.vue';
import ScInput from '../../components/design-system/ScInput.vue';
import ScSelect from '../../components/design-system/ScSelect.vue';
import type { ContractPromptField } from './types';

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
