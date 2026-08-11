<template>
  <ScTextField
    class="sc-input"
    type="text"
    :model-value="modelValue"
    :readonly="readonly"
    :disabled="disabled"
    :required="required"
    :invalid="invalid"
    :described-by="describedBy"
    autocomplete="off"
    @update:model-value="$emit('update:modelValue', $event)"
    @change="$emit('change', $event)"
    @focus="$emit('focus', $event)"
    @blur="$emit('blur', $event)"
    @keydown="$emit('keydown', $event)"
  />
</template>
<script setup lang="ts">
import ScTextField from './ScTextField.vue';
defineProps<{ modelValue:string; readonly?:boolean; disabled?:boolean; required?:boolean; invalid?:boolean; describedBy?:string }>();
defineEmits<{
  'update:modelValue':[value:string];
  change:[value:string];
  focus:[event:FocusEvent];
  blur:[event:FocusEvent];
  keydown:[event:KeyboardEvent];
}>();
</script>
