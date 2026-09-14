<template>
  <TDesignInputNumber
    v-native-control-projection="nativeProjection"
    v-bind="{ ...$attrs, ...semanticPrimitiveIdentity('ScNumberInput') }"
    data-focus-ring-owner="component"
    :value="modelValue"
    :disabled="disabled"
    :readonly="readonly"
    :decimal-places="decimalPlaces"
    :status="status"
    :placeholder="placeholder"
    @change="emit('update:modelValue', $event as number | undefined)"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { TDesignInputNumber } from './tdesignPrimitiveBridge';
import { nativeControlProjection } from './nativeControlProjection';
import { semanticPrimitiveIdentity } from './primitiveAdapter';

defineOptions({ inheritAttrs: false });
const props = defineProps<{
  id?: string;
  modelValue?: number;
  disabled?: boolean;
  readonly?: boolean;
  required?: boolean;
  invalid?: boolean;
  describedBy?: string;
  ariaLabel?: string;
  decimalPlaces?: number;
  status?: 'default' | 'success' | 'warning' | 'error';
  placeholder?: string;
}>();
const emit = defineEmits<{ 'update:modelValue': [value: number | undefined] }>();
const vNativeControlProjection = nativeControlProjection;
const nativeProjection = computed(() => ({
  selector: 'input' as const,
  attributes: {
    id: props.id,
    required: props.required,
    'aria-required': props.required || undefined,
    'aria-invalid': props.invalid || props.status === 'error' || undefined,
    'aria-describedby': props.describedBy,
    'aria-label': props.ariaLabel,
  },
}));
</script>
