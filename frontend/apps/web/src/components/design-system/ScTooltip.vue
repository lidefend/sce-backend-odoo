<template>
  <TDesignTooltip
    v-bind="semanticPrimitiveIdentity('ScTooltip')"
    :content="content"
    :placement="placement"
    :disabled="disabled"
    :show-arrow="showArrow"
  >
    <slot />
  </TDesignTooltip>
</template>

<script setup lang="ts">
import { TDesignTooltip } from './tdesignPrimitiveBridge';
import { semanticPrimitiveIdentity } from './primitiveAdapter';

export type ScTooltipPlacement = 'top' | 'bottom' | 'left' | 'right' | 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';

withDefaults(defineProps<{ content: string; placement?: ScTooltipPlacement; disabled?: boolean; showArrow?: boolean }>(), {
  placement: 'top',
  showArrow: true,
});
</script>
