<template>
  <TDesignInput
    v-bind="semanticPrimitiveIdentity('ScInput')"
    :model-value="modelValue"
    :size="normalizePrimitiveSize(size)"
    :status="status === 'default' ? undefined : status"
    :disabled="disabled"
    :readonly="readonly"
    :loading="loading"
    :placeholder="placeholder"
    :clearable="clearable"
    :aria-describedby="describedBy"
    :aria-invalid="status === 'error' || undefined"
    @update:model-value="emit('update:modelValue', $event)"
    @change="emit('change', $event)"
    @focus="emit('focus', $event)"
    @blur="emit('blur', $event)"
  />
</template>

<script setup lang="ts">
import { TDesignInput } from './tdesignPrimitiveBridge';
import {
  normalizePrimitiveSize,
  semanticPrimitiveIdentity,
  type ScPrimitiveSize,
  type ScPrimitiveStatus,
} from './primitiveAdapter';

defineProps<{
  modelValue?: string | number;
  size?: ScPrimitiveSize;
  status?: ScPrimitiveStatus;
  disabled?: boolean;
  readonly?: boolean;
  loading?: boolean;
  clearable?: boolean;
  placeholder?: string;
  describedBy?: string;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: string | number];
  change: [value: string | number, context?: unknown];
  focus: [value: string | number, context?: unknown];
  blur: [value: string | number, context?: unknown];
}>();
</script>
