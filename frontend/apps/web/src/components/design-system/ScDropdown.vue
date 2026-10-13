<template>
  <TDesignDropdown
    v-bind="semanticPrimitiveIdentity('ScDropdown')"
    :disabled="disabled"
    :trigger="trigger"
    :placement="placement"
    :options="options"
    @click="onSelect"
  >
    <slot name="trigger" />
  </TDesignDropdown>
</template>

<script setup lang="ts">
import { computed, h } from 'vue';
import ScPopover from './ScPopover.vue';
import { TDesignDropdown } from './tdesignPrimitiveBridge';
import { semanticPrimitiveIdentity, tdesignDropdownOptions, type ScDropdownOptionInput } from './primitiveAdapter';

export type ScDropdownItem = ScDropdownOptionInput;
export type ScDropdownPlacement = 'top' | 'left' | 'right' | 'bottom' | 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';

const props = withDefaults(defineProps<{ items: ScDropdownItem[]; disabled?: boolean; trigger?: 'click' | 'hover'; placement?: ScDropdownPlacement }>(), {
  trigger: 'click',
  placement: 'bottom-right',
});
const options = computed(() => tdesignDropdownOptions(props.items).map(option => ({
  ...option,
  ...(option.disabled && option.reasonMessage ? { content: () => h(ScPopover, { trigger: 'click' }, {
    default: () => option.reasonMessage,
    trigger: () => h('span', {
      tabindex: 0, role: 'button', 'aria-label': `${option.content}: ${option.reasonMessage}`,
      onClick: (event: MouseEvent) => event.stopPropagation(),
      onKeydown: (event: KeyboardEvent) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault(); event.stopPropagation(); (event.currentTarget as HTMLElement).click();
        }
      },
    }, option.content),
  }) } : {}),
})));
const emit = defineEmits<{ select: [item: ScDropdownItem, context: unknown] }>();
function onSelect(option: { value?: unknown }, context: unknown) {
  const item = props.items.find((candidate) => candidate.value === option.value);
  if (item && !item.disabled) emit('select', item, context);
}
</script>
