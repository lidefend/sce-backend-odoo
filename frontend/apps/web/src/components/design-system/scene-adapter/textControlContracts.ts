import type {
  InputPortEmits,
  InputPortProps,
  NoPortSlots,
  PrimitiveBinding,
  TextareaPortEmits,
  TextareaPortProps,
} from '@sc/ui/primitive-port';
import ScSceneInput from './ScSceneInput.vue';
import ScSceneTextarea from './ScSceneTextarea.vue';

export const scSceneInputBinding: PrimitiveBinding<
  InputPortProps,
  InputPortEmits,
  NoPortSlots,
  'Input'
> = {
  component: ScSceneInput,
  contract: {
    primitive: 'Input',
    portVersion: 1,
    capabilities: ['value', 'change', 'focus', 'blur', 'keyboard', 'ime'],
  },
};

export const scSceneTextareaBinding: PrimitiveBinding<
  TextareaPortProps,
  TextareaPortEmits,
  NoPortSlots,
  'Textarea'
> = {
  component: ScSceneTextarea,
  contract: {
    primitive: 'Textarea',
    portVersion: 1,
    capabilities: ['value', 'change', 'focus', 'blur', 'keyboard', 'ime'],
  },
};
