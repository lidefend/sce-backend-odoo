<template>
  <TDesignAutoComplete
    v-native-control-projection="nativeProjection"
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
import { computed } from 'vue';
import { TDesignAutoComplete } from './tdesignPrimitiveBridge';
import { nativeControlProjection } from './nativeControlProjection';
const props = withDefaults(defineProps<{ modelValue:string; readonly?:boolean; disabled?:boolean; required?:boolean; invalid?:boolean; describedBy?:string; appearance?:'default'|'form-field' }>(), { appearance:'default' });
const vNativeControlProjection = nativeControlProjection;
const nativeProjection = computed(() => ({
  selector: 'input' as const,
  attributes: {
    'aria-required': props.required || undefined,
    'aria-invalid': props.invalid || undefined,
    'aria-describedby': props.describedBy,
  },
}));
const emit = defineEmits<{
  'update:modelValue': [value: string];
  focus: [event: unknown];
  blur: [event: unknown];
  keydown: [event: unknown];
  keyup: [event: unknown];
  change: [event: Event];
}>();
function emitChange(value: string | number) {
  emit('update:modelValue', String(value ?? ''));
  emit('change', { target: { value: String(value ?? '') } } as unknown as Event);
}
</script>
