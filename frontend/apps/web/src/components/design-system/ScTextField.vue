<template>
  <TInput
    ref="control"
    :class="['sc-design-text-field', attrs.class]"
    :style="attrs.style"
    :model-value="modelValue"
    :type="type"
    :name="name"
    :placeholder="placeholder"
    :autocomplete="autocomplete"
    :disabled="disabled"
    :readonly="readonly"
    :status="invalid ? 'error' : 'default'"
    :maxlength="maxlength"
    :clearable="clearable"
    data-ui-engine="tdesign"
    @update:model-value="onUpdate"
    @change="onChange"
    @focus="$emit('focus', $event)"
    @blur="$emit('blur', $event)"
    @keydown="$emit('keydown', $event)"
    @enter="$emit('enter', $event)"
    @compositionstart="$emit('compositionstart', $event)"
    @compositionend="$emit('compositionend', $event)"
  />
</template>

<script setup lang="ts">
import { nextTick, onMounted, onUpdated, ref, useAttrs, type ComponentPublicInstance } from 'vue';
import { TInput } from './tdesignAdapter';

type InputValue = string | number;

defineOptions({ inheritAttrs: false });

const props = withDefaults(defineProps<{
  modelValue: InputValue;
  type?: 'text' | 'search' | 'password' | 'number' | 'url' | 'tel';
  id?: string;
  name?: string;
  label?: string;
  placeholder?: string;
  autocomplete?: string;
  disabled?: boolean;
  readonly?: boolean;
  required?: boolean;
  invalid?: boolean;
  describedBy?: string;
  maxlength?: number;
  clearable?: boolean;
}>(), {
  type: 'text',
  id: undefined,
  name: undefined,
  label: undefined,
  placeholder: undefined,
  autocomplete: undefined,
  disabled: false,
  readonly: false,
  required: false,
  invalid: false,
  describedBy: undefined,
  maxlength: undefined,
  clearable: false,
});
const emit = defineEmits<{
  'update:modelValue': [value: string];
  change: [value: string];
  focus: [event: FocusEvent];
  blur: [event: FocusEvent];
  keydown: [event: KeyboardEvent];
  enter: [value: string, context?: unknown];
  compositionstart: [event: CompositionEvent];
  compositionend: [event: CompositionEvent];
}>();
const attrs = useAttrs();
const control = ref<ComponentPublicInstance | null>(null);

function nativeInput(): HTMLInputElement | null {
  return (control.value?.$el as HTMLElement | undefined)?.querySelector('input') || null;
}

function syncNativeAccessibility(): void {
  const input = nativeInput();
  if (!input) return;
  const attributes: Record<string, string | undefined> = {
    id: props.id,
    'aria-label': props.label,
    'aria-describedby': props.describedBy,
    'aria-required': props.required ? 'true' : undefined,
    'aria-invalid': props.invalid ? 'true' : undefined,
  };
  Object.entries(attrs).forEach(([name, value]) => {
    if (['role', 'tabindex', 'min', 'max', 'step', 'minlength', 'inputmode', 'spellcheck'].includes(name) || name.startsWith('aria-') || name.startsWith('data-')) {
      attributes[name] = value === undefined || value === null ? undefined : String(value);
    }
  });
  Object.entries(attributes).forEach(([name, value]) => {
    if (value === undefined || value === '') input.removeAttribute(name);
    else input.setAttribute(name, value);
  });
}

function onUpdate(value: InputValue): void {
  emit('update:modelValue', String(value ?? ''));
}
function onChange(value: InputValue): void {
  emit('change', String(value ?? ''));
}
function focus(): void {
  nativeInput()?.focus();
}
defineExpose({ focus });
onMounted(() => nextTick(syncNativeAccessibility));
onUpdated(() => nextTick(syncNativeAccessibility));
</script>
