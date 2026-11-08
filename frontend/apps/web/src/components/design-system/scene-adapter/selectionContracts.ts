import type {
  CanonicalDateValue,
  DateFieldPortEmits,
  DateFieldPortProps,
  NoPortSlots,
  PrimitiveBinding,
  SelectPortEmits,
  SelectPortProps,
} from '@sc/ui/primitive-port';
import ScSceneDateField from './ScSceneDateField.vue';
import ScSceneSelect from './ScSceneSelect.vue';

export const scSceneSelectBinding: PrimitiveBinding<SelectPortProps, SelectPortEmits, NoPortSlots, 'Select'> = {
  component: ScSceneSelect,
  contract: { primitive: 'Select', portVersion: 1, capabilities: ['value', 'change', 'search', 'popup', 'focus', 'blur', 'keyboard'] },
};
export const scSceneDateFieldBinding: PrimitiveBinding<DateFieldPortProps, DateFieldPortEmits<CanonicalDateValue>, NoPortSlots, 'DateField'> = {
  component: ScSceneDateField,
  contract: { primitive: 'DateField', portVersion: 1, capabilities: ['value', 'change', 'clear', 'focus', 'blur', 'keyboard'] },
};
