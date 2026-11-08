<template>
  <TDesignFormItem
    v-bind="semanticPrimitiveIdentity('ScFormField')"
    :data-state="invalid || error ? 'error' : 'default'"
    :data-required="required || undefined"
    :label="label"
    :for="controlId"
    :name="fieldKey"
    :status="invalid || error ? 'error' : undefined"
    :help="helpContent"
    :tips="errorContent"
  >
    <slot :control-id="controlId" :described-by="describedBy" />
  </TDesignFormItem>
</template>

<script setup lang="ts">
import { computed, h, useId } from 'vue';
import { TDesignFormItem } from './tdesignPrimitiveBridge';
import { semanticPrimitiveIdentity } from './primitiveAdapter';

const props = defineProps<{
  label: string;
  fieldKey: string;
  required?: boolean;
  invalid?: boolean;
  help?: string;
  error?: string;
}>();

const suffix = useId().replace(/[^A-Za-z0-9_-]/g, '-');
const fieldToken = computed(() => props.fieldKey.replace(/[^A-Za-z0-9_-]/g, '-'));
const controlId = computed(() => `sc-field-${fieldToken.value}-${suffix}`);
const helpId = computed(() => `${controlId.value}-help`);
const errorId = computed(() => `${controlId.value}-error`);
const describedBy = computed(() => [
  props.help ? helpId.value : '',
  props.error ? errorId.value : '',
].filter(Boolean).join(' ') || undefined);
const helpContent = computed(() => (
  props.help ? () => h('span', { id: helpId.value }, props.help) : undefined
));
const errorContent = computed(() => (
  props.error ? () => h('span', { id: errorId.value, role: 'alert' }, props.error) : undefined
));
</script>
