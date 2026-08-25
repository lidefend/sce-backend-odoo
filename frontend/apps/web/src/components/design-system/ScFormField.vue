<template>
  <ScField
    v-bind="semanticPrimitiveIdentity('ScFormField')"
    :data-state="invalid || error ? 'error' : 'default'"
    :data-required="required || undefined"
    :label="label"
    :field-key="fieldKey"
    :required="required"
    :invalid="invalid"
    :help="help"
    :error="error"
  >
    <template #default="slotProps"><slot v-bind="slotProps" /></template>
  </ScField>
</template>

<script setup lang="ts">
import ScField from './ScField.vue';
import { semanticPrimitiveIdentity } from './primitiveAdapter';

defineProps<{ label: string; fieldKey: string; required?: boolean; invalid?: boolean; help?: string; error?: string }>();
</script>
