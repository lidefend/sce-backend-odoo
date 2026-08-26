<template>
  <TDesignCheckbox
    ref="checkboxRef"
    v-native-control-projection="nativeProjection"
    class="sc-checkbox"
    :class="`size-${size}`"
    data-semantic-component="ScCheckbox"
    data-semantic-layer="primitive"
    :data-checked="checked || undefined"
    :data-indeterminate="indeterminate || undefined"
    :data-disabled="disabled || undefined"
    data-primitive-driver="tdesign"
    :model-value="checked"
    :indeterminate="indeterminate"
    :disabled="disabled"
    @change="onTDesignChange"
  >
    <span v-if="$slots.default || label" class="sc-checkbox__label"><slot>{{ label }}</slot></span>
  </TDesignCheckbox>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { TDesignCheckbox } from './tdesignPrimitiveBridge';
import { nativeControlProjection } from './nativeControlProjection';
import type { ScPrimitiveSize } from './primitiveAdapter';

const props = withDefaults(defineProps<{
  checked?: boolean;
  indeterminate?: boolean;
  disabled?: boolean;
  required?: boolean;
  label?: string;
  describedBy?: string;
  size?: ScPrimitiveSize;
}>(), {
  checked: false,
  indeterminate: false,
  disabled: false,
  required: false,
  label: '',
  describedBy: undefined,
  size: 'medium',
});

const emit = defineEmits<{
  change: [checked: boolean, event: Event];
  'update:checked': [checked: boolean];
}>();
const checkboxRef = ref<{ focus?: () => void; $el?: HTMLElement } | null>(null);
const vNativeControlProjection = nativeControlProjection;
const nativeProjection = computed(() => ({
  selector: 'input' as const,
  attributes: {
    required: props.required,
    'aria-checked': props.indeterminate ? 'mixed' : String(props.checked),
    'aria-label': props.label,
    'aria-describedby': props.describedBy,
  },
}));

function onTDesignChange(checked: boolean, context: { e?: Event }) {
  if (props.disabled) return;
  emit('update:checked', checked);
  emit('change', checked, context?.e ?? new Event('change'));
}

defineExpose({ focus: () => checkboxRef.value?.focus?.() ?? checkboxRef.value?.$el?.querySelector('input')?.focus() });
</script>

<style scoped>
.sc-checkbox{display:inline-flex;align-items:center;gap:var(--sc-product-space-2);min-width:0;cursor:pointer;color:var(--sc-app-text-primary);font-size:var(--sc-product-text-sm)}
.sc-checkbox[data-disabled='true']{cursor:not-allowed;color:var(--sc-semantic-text-disabled)}
.sc-checkbox.size-small{font-size:var(--sc-product-text-xs)}
.sc-checkbox__label{min-width:0;overflow-wrap:anywhere}
</style>
