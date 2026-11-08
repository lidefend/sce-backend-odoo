import type {
  ButtonPortEmits,
  ButtonPortProps,
  ButtonPortSlots,
  PrimitiveBinding,
} from '@sc/ui/primitive-port';
import {
  ScSceneButton,
  scSceneButtonBinding,
  scSceneButtonContract,
} from '../src/components/design-system/scene-adapter';

const realButtonBinding: PrimitiveBinding<
  ButtonPortProps,
  ButtonPortEmits,
  ButtonPortSlots,
  'Button'
> = scSceneButtonBinding;
void realButtonBinding;
void ScSceneButton;
void scSceneButtonContract;

const wrongIdentity = {
  component: ScSceneButton,
  contract: {
    primitive: 'Button',
    portVersion: 1,
    capabilities: ['activate', 'focus', 'blur', 'keyboard', 'loading'],
  },
};
// @ts-expect-error The real Button wrapper must not be mislabeled as Input.
const invalidIdentityBinding: PrimitiveBinding<
  ButtonPortProps,
  ButtonPortEmits,
  ButtonPortSlots,
  'Input'
> = wrongIdentity;
void invalidIdentityBinding;
