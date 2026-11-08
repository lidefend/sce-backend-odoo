import type {
  ComponentOptionsMixin,
  ComputedOptions,
  DefineComponent,
  MethodOptions,
  PublicProps,
} from 'vue';
import type {
  ButtonPortEmits,
  DateFieldPortEmits,
  InputPortEmits,
  RuntimeEmits,
  SelectPortEmits,
  TablePortEmits,
  TextareaPortEmits,
} from './events';
import type { ButtonPortSlots, NoPortSlots, RuntimeSlots } from './slots';

type EmptyVueOptions = Record<never, never>;

export const SCENE_PRIMITIVE_NAMES = [
  'Button',
  'Input',
  'Select',
  'DateField',
  'Textarea',
  'Table',
  'Icon',
] as const;

export type ScenePrimitiveName = (typeof SCENE_PRIMITIVE_NAMES)[number];
export type ScenePrimitiveSize = 'small' | 'medium' | 'large';
export type SceneControlStatus = 'default' | 'error';
export type SceneDensity = 'compact' | 'cozy';

export type PrimitiveCapability =
  | 'activate'
  | 'value'
  | 'change'
  | 'focus'
  | 'blur'
  | 'keyboard'
  | 'ime'
  | 'search'
  | 'popup'
  | 'loading'
  | 'row-activate'
  | 'semantic-icon';

export const PRIMITIVE_REQUIRED_CAPABILITIES = {
  Button: ['activate', 'focus', 'blur', 'keyboard', 'loading'],
  Input: ['value', 'change', 'focus', 'blur', 'keyboard', 'ime'],
  Select: ['value', 'change', 'search', 'popup', 'focus', 'blur', 'keyboard'],
  DateField: ['value', 'change', 'focus', 'blur', 'keyboard'],
  Textarea: ['value', 'change', 'focus', 'blur', 'keyboard', 'ime'],
  Table: ['row-activate', 'focus', 'keyboard'],
  Icon: ['semantic-icon'],
} as const satisfies Record<ScenePrimitiveName, readonly PrimitiveCapability[]>;

export interface PrimitiveHandle {
  focus(options?: FocusOptions): void;
}

export interface PrimitiveCommonProps {
  id?: string;
  name?: string;
  size?: ScenePrimitiveSize;
  status?: SceneControlStatus;
  disabled?: boolean;
  readonly?: boolean;
  required?: boolean;
  loading?: boolean;
  describedBy?: string;
  ariaLabel?: string;
}

export interface ButtonPortProps {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: ScenePrimitiveSize;
  disabled?: boolean;
  loading?: boolean;
  loadingLabel?: string;
  accessibleLabel?: string;
}

export interface InputPortProps extends PrimitiveCommonProps {
  modelValue: string;
  type?: 'text' | 'search' | 'number';
  inputMode?: 'text' | 'decimal' | 'numeric';
  placeholder?: string;
}

export interface SelectPortOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface SelectPortProps extends PrimitiveCommonProps {
  modelValue: string;
  options: readonly SelectPortOption[];
  placeholder?: string;
  filterable?: boolean;
  emptyText?: string;
}

export type CanonicalDateValue =
  | { precision: 'date'; value: string }
  | { precision: 'datetime'; value: string };

export interface DateFieldPortProps extends PrimitiveCommonProps {
  modelValue: CanonicalDateValue;
  placeholder?: string;
}

export interface TextareaPortProps extends PrimitiveCommonProps {
  modelValue: string;
  placeholder?: string;
  rows?: number;
  maxRows?: number;
}

export interface TablePortColumn {
  key: string;
  label: string;
  width?: string;
  align?: 'left' | 'center' | 'right';
}

export interface TablePortRow {
  id: string | number;
}

export interface TablePortProps<Row extends TablePortRow> {
  rows: readonly Row[];
  columns: readonly TablePortColumn[];
  rowKey?: keyof Row & string;
  loading?: boolean;
  emptyText?: string;
  interactiveRows?: boolean;
  accessibleLabel: string;
}

export interface IconPortProps {
  name: 'check' | 'close' | 'chevron-down' | 'chevron-right' | 'file';
  size?: 14 | 16 | 18 | 20 | 24;
  label?: string;
  decorative?: boolean;
}

export interface PrimitivePortDefinition<
  Props,
  Emits extends Record<string, unknown[]>,
  Slots extends Record<string, unknown>,
> {
  primitive: ScenePrimitiveName;
  portVersion: 1;
  capabilities: readonly PrimitiveCapability[];
  readonly __types?: {
    props: Props;
    emits: Emits;
    slots: Slots;
  };
}

export type PrimitiveComponent<
  Props,
  Emits extends Record<string, unknown[]>,
  Slots extends Record<string, unknown>,
> = DefineComponent<
  Props,
  EmptyVueOptions,
  EmptyVueOptions,
  ComputedOptions,
  MethodOptions,
  ComponentOptionsMixin,
  ComponentOptionsMixin,
  RuntimeEmits<Emits>,
  string,
  PublicProps,
  Props,
  EmptyVueOptions,
  RuntimeSlots<Slots>
>;

export interface PrimitiveBinding<
  Props,
  Emits extends Record<string, unknown[]>,
  Slots extends Record<string, unknown>,
  Name extends ScenePrimitiveName = ScenePrimitiveName,
> {
  component: PrimitiveComponent<Props, Emits, Slots>;
  contract: PrimitivePortDefinition<Props, Emits, Slots> & { primitive: Name };
}

export interface ScenePrimitiveAdapter {
  Button: PrimitiveBinding<ButtonPortProps, ButtonPortEmits, ButtonPortSlots, 'Button'>;
  Input: PrimitiveBinding<InputPortProps, InputPortEmits, NoPortSlots, 'Input'>;
  Select: PrimitiveBinding<SelectPortProps, SelectPortEmits, NoPortSlots, 'Select'>;
  DateField: PrimitiveBinding<DateFieldPortProps, DateFieldPortEmits<CanonicalDateValue>, NoPortSlots, 'DateField'>;
  Textarea: PrimitiveBinding<TextareaPortProps, TextareaPortEmits, NoPortSlots, 'Textarea'>;
  Table: PrimitiveBinding<TablePortProps<TablePortRow>, TablePortEmits<TablePortRow>, NoPortSlots, 'Table'>;
  Icon: PrimitiveBinding<IconPortProps, Record<never, never>, NoPortSlots, 'Icon'>;
}

export interface SceneCompositionContext {
  primitives: ScenePrimitiveAdapter;
  density: SceneDensity;
}
