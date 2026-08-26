<template>
  <TDesignAutoComplete data-semantic-component="ScRelationField" data-semantic-driver="tdesign-auto-complete" data-semantic-layer="primitive" :data-appearance="appearance"
    :value="modelValue" :disabled="disabled" :readonly="readonly" :aria-required="required || undefined"
    :aria-invalid="invalid || undefined" :aria-describedby="describedBy" autocomplete="off"
    @change="emit('update:modelValue', String($event ?? ''))" />
</template>
<script setup lang="ts">
import { TDesignAutoComplete } from './tdesignPrimitiveBridge';
withDefaults(defineProps<{ modelValue:string; readonly?:boolean; disabled?:boolean; required?:boolean; invalid?:boolean; describedBy?:string; appearance?:'default'|'form-field' }>(), { appearance:'default' });
const emit=defineEmits<{ 'update:modelValue':[value:string] }>();
</script>
