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

withDefaults(defineProps<{ content: string; placement?: string; disabled?: boolean; showArrow?: boolean }>(), {
  placement: 'top',
  showArrow: true,
});
</script>
