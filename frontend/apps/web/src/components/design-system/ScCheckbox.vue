<template>
  <label
    class="sc-checkbox"
    :class="`size-${size}`"
    data-semantic-component="ScCheckbox"
    data-semantic-layer="primitive"
    :data-checked="checked || undefined"
    :data-indeterminate="indeterminate || undefined"
    :data-disabled="disabled || undefined"
  >
    <input
      ref="inputRef"
      type="checkbox"
      :checked="checked"
      :disabled="disabled"
      :required="required"
      :aria-checked="indeterminate ? 'mixed' : checked"
      :aria-label="label"
      :aria-describedby="describedBy"
      @change="onChange"
    />
    <span class="sc-checkbox__indicator" aria-hidden="true" />
    <span v-if="$slots.default || label" class="sc-checkbox__label"><slot>{{ label }}</slot></span>
  </label>
</template>

<script setup lang="ts">
import { ref, watchEffect } from 'vue';
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
const inputRef = ref<HTMLInputElement | null>(null);

watchEffect(() => {
  if (inputRef.value) inputRef.value.indeterminate = props.indeterminate;
});

function onChange(event: Event) {
  if (props.disabled) return;
  const checked = Boolean((event.target as HTMLInputElement | null)?.checked);
  emit('update:checked', checked);
  emit('change', checked, event);
}

defineExpose({ focus: () => inputRef.value?.focus() });
</script>

<style scoped>
.sc-checkbox{display:inline-flex;align-items:center;gap:var(--sc-product-space-2);min-width:0;cursor:pointer;color:var(--sc-app-text-primary);font-size:var(--sc-product-text-sm)}
.sc-checkbox input{position:absolute;inline-size:1px;block-size:1px;opacity:0;pointer-events:none}
.sc-checkbox__indicator{display:inline-grid;place-items:center;flex:0 0 auto;inline-size:16px;block-size:16px;border:1px solid var(--sc-app-border-strong);border-radius:var(--sc-product-radius-control);background:var(--sc-app-panel);transition:border-color var(--sc-base-motion-fast),background var(--sc-base-motion-fast),box-shadow var(--sc-base-motion-fast)}
.sc-checkbox[data-checked='true'] .sc-checkbox__indicator{border-color:var(--sc-app-accent);background:var(--sc-app-accent)}
.sc-checkbox[data-checked='true'] .sc-checkbox__indicator::after{content:'';inline-size:7px;block-size:4px;border-left:2px solid var(--sc-semantic-text-on-interactive);border-bottom:2px solid var(--sc-semantic-text-on-interactive);transform:translateY(-1px) rotate(-45deg)}
.sc-checkbox[data-indeterminate='true'] .sc-checkbox__indicator{border-color:var(--sc-app-accent);background:var(--sc-app-accent)}
.sc-checkbox[data-indeterminate='true'] .sc-checkbox__indicator::after{content:'';inline-size:8px;block-size:2px;border:0;background:var(--sc-semantic-text-on-interactive);transform:none}
.sc-checkbox:has(input:focus-visible) .sc-checkbox__indicator{box-shadow:0 0 0 3px var(--sc-app-focus-ring)}
.sc-checkbox[data-disabled='true']{cursor:not-allowed;color:var(--sc-semantic-text-disabled)}
.sc-checkbox[data-disabled='true'] .sc-checkbox__indicator{background:var(--sc-app-subtle-bg);border-color:var(--sc-app-border)}
.sc-checkbox.size-small{font-size:var(--sc-product-text-xs)}
.sc-checkbox.size-large .sc-checkbox__indicator{inline-size:18px;block-size:18px}
.sc-checkbox__label{min-width:0;overflow-wrap:anywhere}
</style>
