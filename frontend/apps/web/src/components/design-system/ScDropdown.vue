<template>
  <TDesignDropdown
    v-bind="semanticPrimitiveIdentity('ScDropdown')"
    :disabled="disabled"
    :trigger="trigger"
    :placement="placement"
    :options="tdesignDropdownOptions(items)"
    @click="onSelect"
  >
    <slot name="trigger" />
  </TDesignDropdown>
</template>

<script setup lang="ts">
import { TDesignDropdown } from './tdesignPrimitiveBridge';
import { semanticPrimitiveIdentity, tdesignDropdownOptions, type ScDropdownOptionInput } from './primitiveAdapter';

export type ScDropdownItem = ScDropdownOptionInput;
export type ScDropdownPlacement = 'top' | 'left' | 'right' | 'bottom' | 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';

const props = withDefaults(defineProps<{ items: ScDropdownItem[]; disabled?: boolean; trigger?: 'click' | 'hover'; placement?: ScDropdownPlacement }>(), {
  trigger: 'click',
  placement: 'bottom-right',
});
const emit = defineEmits<{ select: [item: ScDropdownItem, context: unknown] }>();
function onSelect(option: { value?: unknown }, context: unknown) {
  const item = props.items.find((candidate) => candidate.value === option.value);
  if (item && !item.disabled) emit('select', item, context);
}
</script>
