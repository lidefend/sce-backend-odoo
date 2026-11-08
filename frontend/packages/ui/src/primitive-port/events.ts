import type { ShortEmitsToObject } from 'vue';

export type PrimitiveEventSource = 'pointer' | 'keyboard' | 'programmatic';

/**
 * The adapter determines `source` from the actual event chain. A keyboard
 * activation may still expose a MouseEvent click and must not be classified by
 * the native event's runtime type alone.
 */
export interface PrimitiveEvent<T extends Event = Event> {
  source: PrimitiveEventSource;
  nativeEvent?: T;
}

export type ControlEvents = {
  change: [value: string, event: PrimitiveEvent];
  focus: [value: string, event: PrimitiveEvent<FocusEvent>];
  blur: [value: string, event: PrimitiveEvent<FocusEvent>];
  keydown: [event: PrimitiveEvent<KeyboardEvent>];
  keyup: [event: PrimitiveEvent<KeyboardEvent>];
};

export type ButtonPortEmits = {
  activate: [event: PrimitiveEvent];
  focus: [event: PrimitiveEvent<FocusEvent>];
  blur: [event: PrimitiveEvent<FocusEvent>];
};

export type InputPortEmits = ControlEvents & {
  'update:modelValue': [value: string];
  input: [value: string, event: PrimitiveEvent];
  compositionstart: [event: PrimitiveEvent<CompositionEvent>];
  compositionend: [event: PrimitiveEvent<CompositionEvent>];
};

export type SelectPortEmits = ControlEvents & {
  'update:modelValue': [value: string];
  search: [query: string, event: PrimitiveEvent<InputEvent>];
  popupVisibleChange: [state: { visible: boolean; trigger: string }, event: PrimitiveEvent];
};

export type DateFieldPortEmits<Value> = {
  'update:modelValue': [value: Value];
  change: [value: Value, event: PrimitiveEvent];
  focus: [value: Value, event: PrimitiveEvent<FocusEvent>];
  blur: [value: Value, event: PrimitiveEvent<FocusEvent>];
  keydown: [event: PrimitiveEvent<KeyboardEvent>];
  keyup: [event: PrimitiveEvent<KeyboardEvent>];
};

export type TextareaPortEmits = ControlEvents & {
  'update:modelValue': [value: string];
  input: [value: string, event: PrimitiveEvent];
  compositionstart: [event: PrimitiveEvent<CompositionEvent>];
  compositionend: [event: PrimitiveEvent<CompositionEvent>];
};

export type TablePortEmits<Row> = {
  rowActivate: [row: Row, event: PrimitiveEvent];
};

export type RuntimeEmits<PortEmits extends Record<string, unknown[]>> = ShortEmitsToObject<PortEmits>;
