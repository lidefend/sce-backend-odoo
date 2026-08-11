<template>
  <TTextarea
    ref="control"
    :class="['sc-design-text-area', attrs.class]"
    :style="textareaStyle"
    :model-value="modelValue"
    :name="name"
    :placeholder="placeholder"
    :disabled="disabled"
    :readonly="readonly"
    :status="invalid ? 'error' : 'default'"
    :maxlength="maxlength"
    :autosize="false"
    data-ui-engine="tdesign"
    @update:model-value="$emit('update:modelValue', String($event ?? ''))"
    @change="$emit('change', String($event ?? ''))"
    @focus="$emit('focus', $event)"
    @blur="$emit('blur', $event)"
    @keydown="$emit('keydown', $event)"
  />
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUpdated, ref, useAttrs, type ComponentPublicInstance } from 'vue';
import { TTextarea } from './tdesignAdapter';

const props = withDefaults(defineProps<{
  modelValue: string;
  id?: string;
  name?: string;
  label?: string;
  placeholder?: string;
  disabled?: boolean;
  readonly?: boolean;
  required?: boolean;
  invalid?: boolean;
  describedBy?: string;
  maxlength?: number;
  rows?: number;
}>(), {
  id: undefined,
  name: undefined,
  label: undefined,
  placeholder: undefined,
  disabled: false,
  readonly: false,
  required: false,
  invalid: false,
  describedBy: undefined,
  maxlength: undefined,
  rows: 4,
});
defineOptions({ inheritAttrs: false });
defineEmits<{
  'update:modelValue': [value: string];
  change: [value: string];
  focus: [event: FocusEvent];
  blur: [event: FocusEvent];
  keydown: [event: KeyboardEvent];
}>();
const control = ref<ComponentPublicInstance | null>(null);
const attrs = useAttrs();
const textareaStyle = computed(() => ({
  ...(
    attrs.style && typeof attrs.style === 'object' && !Array.isArray(attrs.style)
      ? attrs.style as Record<string, string | number>
      : {}
  ),
  height: `${Math.max(2, props.rows) * 24 + 16}px`,
}));

function syncNativeAccessibility(): void {
  const textarea = (control.value?.$el as HTMLElement | undefined)?.querySelector('textarea');
  if (!textarea) return;
  const attributes: Record<string, string | undefined> = {
    id: props.id,
    'aria-label': props.label,
    'aria-describedby': props.describedBy,
    'aria-required': props.required ? 'true' : undefined,
    'aria-invalid': props.invalid ? 'true' : undefined,
  };
  Object.entries(attrs).forEach(([name, value]) => {
    if (name === 'role' || name === 'tabindex' || name.startsWith('aria-') || name.startsWith('data-')) {
      attributes[name] = value === undefined || value === null ? undefined : String(value);
    }
  });
  Object.entries(attributes).forEach(([name, value]) => {
    if (value === undefined || value === '') textarea.removeAttribute(name);
    else textarea.setAttribute(name, value);
  });
}
function focus(): void {
  (control.value?.$el as HTMLElement | undefined)?.querySelector('textarea')?.focus();
}
defineExpose({ focus });
onMounted(() => nextTick(syncNativeAccessibility));
onUpdated(() => nextTick(syncNativeAccessibility));
</script>
