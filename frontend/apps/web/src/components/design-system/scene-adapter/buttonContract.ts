import type {
  ButtonPortEmits,
  ButtonPortProps,
  ButtonPortSlots,
  PrimitiveBinding,
} from '@sc/ui/primitive-port';
import ScSceneButton from './ScSceneButton.vue';

export const scSceneButtonContract = {
  primitive: 'Button',
  portVersion: 1,
  capabilities: ['activate', 'focus', 'blur', 'keyboard', 'loading'],
} as const;

export const scSceneButtonBinding: PrimitiveBinding<
  ButtonPortProps,
  ButtonPortEmits,
  ButtonPortSlots,
  'Button'
> = {
  component: ScSceneButton,
  contract: scSceneButtonContract,
};
