<template>
  <TDesignDatePicker v-native-control-projection="nativeProjection" data-semantic-component="ScDateField" data-semantic-driver="tdesign-date-picker" data-semantic-layer="primitive" :data-appearance="appearance"
    :value="modelValue" :disabled="disabled" :readonly="readonly" :enable-time-picker="withTime"
    :aria-invalid="invalid || undefined" :aria-describedby="describedBy"
    @change="emit('update:modelValue', String($event ?? ''))" />
</template>
<script setup lang="ts">
import { computed } from 'vue';
import { TDesignDatePicker } from './tdesignPrimitiveBridge';
import { nativeControlProjection } from './nativeControlProjection';

const props = withDefaults(defineProps<{ modelValue:string; withTime?:boolean; readonly?:boolean; disabled?:boolean; required?:boolean; invalid?:boolean; describedBy?:string; appearance?:'default'|'form-field' }>(), { appearance:'default' });
const vNativeControlProjection = nativeControlProjection;
const nativeProjection = computed(() => ({
  selector: 'input' as const,
  attributes: {
    required: props.required,
    'aria-required': props.required ? 'true' : undefined,
    'aria-invalid': props.invalid ? 'true' : undefined,
    'aria-describedby': props.describedBy,
  },
}));
const emit=defineEmits<{ 'update:modelValue':[value:string] }>();
</script>
