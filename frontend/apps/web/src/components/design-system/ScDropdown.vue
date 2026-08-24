<template>
  <TDesignDropdown
    v-bind="semanticPrimitiveIdentity('ScDropdown')"
    :disabled="disabled"
    :trigger="trigger"
    :placement="placement"
    @click="emit('select', $event)"
  >
    <slot name="trigger" />
    <TDesignDropdownMenu>
      <TDesignDropdownItem v-for="item in items" :key="item.value" :value="item.value" :disabled="item.disabled">
        {{ item.label }}
      </TDesignDropdownItem>
    </TDesignDropdownMenu>
  </TDesignDropdown>
</template>

<script setup lang="ts">
import { TDesignDropdown, TDesignDropdownItem, TDesignDropdownMenu } from './tdesignPrimitiveBridge';
import { semanticPrimitiveIdentity } from './primitiveAdapter';

export interface ScDropdownItem {
  value: string | number;
  label: string;
  disabled?: boolean;
}

withDefaults(defineProps<{ items: ScDropdownItem[]; disabled?: boolean; trigger?: 'click' | 'hover'; placement?: string }>(), {
  trigger: 'click',
  placement: 'bottom-right',
});
const emit = defineEmits<{ select: [context: unknown] }>();
</script>
