<template>
  <TDesignPopup
    v-bind="semanticPrimitiveIdentity('ScPopover')"
    :trigger="trigger"
    :placement="placement"
    :show-arrow="showArrow"
    :disabled="disabled"
    :overlay-class-name="overlayClassName"
    :overlay-style="overlayStyle"
    destroy-on-close
  >
    <template #content>
      <slot />
    </template>
    <slot name="trigger" />
  </TDesignPopup>
</template>

<script setup lang="ts">
import type { CSSProperties } from 'vue';
import { TDesignPopup } from './tdesignPrimitiveBridge';
import { semanticPrimitiveIdentity } from './primitiveAdapter';

export type ScPopoverPlacement =
  | 'top'
  | 'bottom'
  | 'left'
  | 'right'
  | 'top-left'
  | 'top-right'
  | 'bottom-left'
  | 'bottom-right'
  | 'left-top'
  | 'left-bottom'
  | 'right-top'
  | 'right-bottom';

export type ScPopoverTrigger = 'hover' | 'click' | 'focus' | 'mousedown' | 'context-menu';

withDefaults(
  defineProps<{
    trigger?: ScPopoverTrigger;
    placement?: ScPopoverPlacement;
    showArrow?: boolean;
    disabled?: boolean;
    overlayClassName?: string;
    overlayStyle?: CSSProperties;
  }>(),
  {
    trigger: 'click',
    placement: 'bottom',
    showArrow: false,
    disabled: false,
  },
);
</script>
