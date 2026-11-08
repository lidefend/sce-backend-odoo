import type { SlotsType, VNode } from 'vue';

export type ButtonPortSlots = {
  default: () => VNode[];
};

export type NoPortSlots = Record<never, never>;

export type RuntimeSlots<PortSlots extends Record<string, unknown>> = SlotsType<PortSlots>;
