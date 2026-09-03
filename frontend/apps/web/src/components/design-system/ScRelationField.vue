<template>
  <TDesignAutoComplete
    data-semantic-component="ScRelationField"
    data-semantic-driver="tdesign-auto-complete"
    data-semantic-layer="primitive"
    :data-appearance="appearance"
    :value="modelValue"
    :disabled="disabled"
    :readonly="readonly"
    :aria-required="required || undefined"
    :aria-invalid="invalid || undefined"
    :aria-describedby="describedBy"
    autocomplete="off"
    @change="emitChange"
    @focus="emit('focus', $event)"
    @blur="emit('blur', $event)"
    @keydown="emit('keydown', $event)"
    @keyup="emit('keyup', $event)"
  />
</template>
<script setup lang="ts">
import { TDesignAutoComplete } from './tdesignPrimitiveBridge';
withDefaults(defineProps<{ modelValue:string; readonly?:boolean; disabled?:boolean; required?:boolean; invalid?:boolean; describedBy?:string; appearance?:'default'|'form-field' }>(), { appearance:'default' });
const emit = defineEmits<{
  'update:modelValue': [value: string];
  focus: [event: FocusEvent];
  blur: [event: FocusEvent];
  keydown: [event: KeyboardEvent];
  keyup: [event: KeyboardEvent];
  change: [event: Event];
}>();
function emitChange(value: string | number) {
  emit('update:modelValue', String(value ?? ''));
  emit('change', { target: { value: String(value ?? '') } } as unknown as Event);
}
</script>
