<template>
  <TDesignDatePicker data-semantic-component="ScDateField" data-semantic-driver="tdesign-date-picker" data-semantic-layer="primitive" :data-appearance="appearance"
    :value="modelValue" :disabled="disabled" :readonly="readonly" :enable-time-picker="withTime"
    :aria-required="required || undefined" :aria-invalid="invalid || undefined" :aria-describedby="describedBy"
    @change="emit('update:modelValue', String($event ?? ''))" />
</template>
<script setup lang="ts">
import { TDesignDatePicker } from './tdesignPrimitiveBridge';
withDefaults(defineProps<{ modelValue:string; withTime?:boolean; readonly?:boolean; disabled?:boolean; required?:boolean; invalid?:boolean; describedBy?:string; appearance?:'default'|'form-field' }>(), { appearance:'default' });
const emit=defineEmits<{ 'update:modelValue':[value:string] }>();
</script>
