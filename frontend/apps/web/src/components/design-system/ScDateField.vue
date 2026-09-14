<template>
  <TDesignDatePicker
    v-native-control-projection="nativeProjection"
    data-semantic-component="ScDateField"
    data-semantic-driver="tdesign-date-picker"
    data-semantic-layer="primitive"
    data-focus-ring-owner="component"
    :data-appearance="appearance"
    :value="modelValue"
    :disabled="disabled"
    :readonly="readonly"
    :clearable="clearable"
    :enable-time-picker="withTime"
    :aria-invalid="invalid || undefined"
    :aria-describedby="describedBy"
    @change="emit('update:modelValue', String($event ?? ''))"
  />
</template>
<script setup lang="ts">
import { computed } from 'vue';
import { TDesignDatePicker } from './tdesignPrimitiveBridge';
import { nativeControlProjection } from './nativeControlProjection';

const props = withDefaults(defineProps<{ id?:string; modelValue:string; withTime?:boolean; readonly?:boolean; disabled?:boolean; clearable?:boolean; required?:boolean; invalid?:boolean; describedBy?:string; ariaLabel?:string; appearance?:'default'|'form-field' }>(), {
  id: undefined,
  withTime: false,
  readonly: false,
  disabled: false,
  clearable: false,
  required: false,
  invalid: false,
  describedBy: undefined,
  ariaLabel: undefined,
  appearance:'default',
});
const vNativeControlProjection = nativeControlProjection;
const nativeProjection = computed(() => ({
  selector: 'input' as const,
  attributes: {
    id: props.id,
    required: props.required,
    'aria-required': props.required ? 'true' : undefined,
    'aria-invalid': props.invalid ? 'true' : undefined,
    'aria-describedby': props.describedBy,
    'aria-label': props.ariaLabel,
  },
}));
const emit=defineEmits<{ 'update:modelValue':[value:string] }>();
</script>

<style scoped>
[data-semantic-component='ScDateField'] { width: 100%; }
</style>
