<template>
  <TDesignFormItem
    v-bind="semanticPrimitiveIdentity('ScFormField')"
    :data-state="invalid || error ? 'error' : 'default'"
    :data-required="required || undefined"
    :label="label"
    :for="controlId"
    :name="fieldKey"
    :status="invalid || error ? 'error' : undefined"
  >
    <slot :control-id="controlId" :described-by="describedBy" />
    <template v-if="help" #help>
      <span :id="helpId">{{ help }}</span>
    </template>
    <template v-if="error" #tips>
      <span :id="errorId" role="alert">{{ error }}</span>
    </template>
  </TDesignFormItem>
</template>

<script setup lang="ts">
import { computed, useId } from 'vue';
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
</script>
