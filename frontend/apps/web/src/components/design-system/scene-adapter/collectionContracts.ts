import type {
  IconPortProps,
  NoPortSlots,
  PrimitiveBinding,
  TablePortEmits,
  TablePortProps,
  TablePortRow,
} from '@sc/ui/primitive-port';
import ScSceneIcon from './ScSceneIcon.vue';
import ScSceneTable from './ScSceneTable.vue';

export function createScSceneTableBinding<Row extends TablePortRow>(): PrimitiveBinding<
  TablePortProps<Row>, TablePortEmits<Row>, NoPortSlots, 'Table'
> {
  return {
    component: ScSceneTable,
    contract: { primitive: 'Table', portVersion: 1, capabilities: ['row-activate', 'focus', 'keyboard'] },
  };
}

export const scSceneTableBinding = createScSceneTableBinding<TablePortRow>();
export const scSceneIconBinding: PrimitiveBinding<IconPortProps, Record<never, never>, NoPortSlots, 'Icon'> = {
  component: ScSceneIcon,
  contract: { primitive: 'Icon', portVersion: 1, capabilities: ['semantic-icon'] },
};
