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
    @visible-change="visible = $event"
  >
    <template #content>
      <slot />
    </template>
    <slot name="trigger" :visible="visible" />
  </TDesignPopup>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { TDesignPopup } from './tdesignPrimitiveBridge';
import { semanticPrimitiveIdentity } from './primitiveAdapter';

const visible = ref(false);

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

export type ScPopoverOverlayStyle = Record<string, string | number>;

withDefaults(
  defineProps<{
    trigger?: ScPopoverTrigger;
    placement?: ScPopoverPlacement;
    showArrow?: boolean;
    disabled?: boolean;
    overlayClassName?: string;
    overlayStyle?: ScPopoverOverlayStyle;
  }>(),
  {
    trigger: 'click',
    placement: 'bottom',
    overlayClassName: undefined,
    overlayStyle: undefined,
    showArrow: false,
    disabled: false,
  },
);
</script>
