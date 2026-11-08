import type {
  ButtonPortEmits,
  ButtonPortProps,
  ButtonPortSlots,
  InputPortEmits,
  InputPortProps,
  NoPortSlots,
  PrimitiveBinding,
  PrimitiveCapability,
  PrimitiveComponent,
  ScenePrimitiveAdapter,
  ScenePrimitiveName,
} from '@sc/ui/primitive-port';

function bind<
  Props,
  Emits extends Record<string, unknown[]>,
  Slots extends Record<string, unknown>,
  Name extends ScenePrimitiveName,
>(
  component: PrimitiveComponent<Props, Emits, Slots>,
  primitive: Name,
  capabilities: readonly PrimitiveCapability[],
): PrimitiveBinding<Props, Emits, Slots, Name> {
  return {
    component,
    contract: {
      primitive,
      portVersion: 1,
      capabilities,
    },
  };
}

declare const buttonComponent: PrimitiveComponent<ButtonPortProps, ButtonPortEmits, ButtonPortSlots>;
declare const inputComponent: PrimitiveComponent<InputPortProps, InputPortEmits, NoPortSlots>;

const typedButton = bind(buttonComponent, 'Button', ['activate', 'focus', 'blur', 'keyboard', 'loading']);
const typedInput = bind(inputComponent, 'Input', ['value', 'change', 'focus', 'blur', 'keyboard', 'ime']);
void typedButton;
void typedInput;

declare const validAdapter: ScenePrimitiveAdapter;
void validAdapter;

type MissingModelValueProps = Omit<InputPortProps, 'modelValue'>;
declare const missingModelValueComponent: PrimitiveComponent<
  MissingModelValueProps,
  InputPortEmits,
  NoPortSlots
>;

const invalidPropsBinding: PrimitiveBinding<InputPortProps, InputPortEmits, NoPortSlots, 'Input'> = {
  // @ts-expect-error Required modelValue compatibility must fail.
  component: missingModelValueComponent,
  contract: {
    primitive: 'Input',
    portVersion: 1,
    capabilities: ['value', 'change', 'focus', 'blur', 'keyboard', 'ime'],
  },
};
void invalidPropsBinding;

type MissingCompositionEndEmits = Omit<InputPortEmits, 'compositionend'>;
declare const missingCompositionEndComponent: PrimitiveComponent<
  InputPortProps,
  MissingCompositionEndEmits,
  NoPortSlots
>;

const invalidEmitsBinding: PrimitiveBinding<InputPortProps, InputPortEmits, NoPortSlots, 'Input'> = {
  // @ts-expect-error Required compositionend compatibility must fail.
  component: missingCompositionEndComponent,
  contract: {
    primitive: 'Input',
    portVersion: 1,
    capabilities: ['value', 'change', 'focus', 'blur', 'keyboard', 'ime'],
  },
};
void invalidEmitsBinding;

type EmptyButtonSlots = Record<never, never>;
declare const missingButtonSlotComponent: PrimitiveComponent<
  ButtonPortProps,
  ButtonPortEmits,
  EmptyButtonSlots
>;

const invalidSlotsBinding: PrimitiveBinding<ButtonPortProps, ButtonPortEmits, ButtonPortSlots, 'Button'> = {
  // @ts-expect-error Required default slot compatibility must fail.
  component: missingButtonSlotComponent,
  contract: {
    primitive: 'Button',
    portVersion: 1,
    capabilities: ['activate', 'focus', 'blur', 'keyboard', 'loading'],
  },
};
void invalidSlotsBinding;
