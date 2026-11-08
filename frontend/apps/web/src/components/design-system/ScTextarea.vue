<template>
  <TDesignTextarea
    ref="textareaRef"
    v-native-control-projection="nativeProjection"
    class="sc-input sc-textarea"
    data-semantic-component="ScTextarea" data-semantic-primitive="ScTextarea"
    data-semantic-layer="primitive"
    data-focus-ring-owner="component"
    :data-size="normalizePrimitiveSize(size)"
    :data-status="status"
    :data-loading="loading || undefined"
    :data-appearance="appearance"
    data-primitive-driver="tdesign"
    :model-value="modelValue"
    :autosize="{ minRows: rows, maxRows }"
    :disabled="disabled || loading"
    :readonly="readonly"
    :placeholder="placeholder"
    :name="name"
    :aria-busy="loading || undefined"
    :aria-describedby="describedBy"
    :aria-invalid="status === 'error' || undefined"
    @update:model-value="onTDesignInput"
    @change="onTDesignChange"
    @focus="onTDesignFocus"
    @blur="onTDesignBlur"
  ></TDesignTextarea>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, onUpdated, ref } from 'vue';
import { TDesignTextarea } from './tdesignPrimitiveBridge';
import { nativeControlProjection } from './nativeControlProjection';
import {
  normalizePrimitiveSize,
  resolvePrimitiveControlUpdate,
  resolvePrimitiveNativeEvent,
  type ScPrimitiveSize,
  type ScPrimitiveStatus,
} from './primitiveAdapter';

const textareaRef = ref<{ $el?: unknown } | null>(null);
let nativeTextarea: HTMLTextAreaElement | null = null;
let nativeEventDocument: Document | null = null;
const vNativeControlProjection = nativeControlProjection;
let focusStartValue = '';
let lastValue = '';
let lastChangeValue = '';
let lastInputEvent: Event | undefined;
let lastInputValue = '';

const props = withDefaults(defineProps<{
  id?: string;
  name?: string;
  modelValue?: string;
  rows?: number;
  maxRows?: number;
  size?: ScPrimitiveSize;
  status?: ScPrimitiveStatus;
  disabled?: boolean;
  readonly?: boolean;
  required?: boolean;
  loading?: boolean;
  placeholder?: string;
  describedBy?: string;
  ariaLabel?: string;
  appearance?: 'default' | 'form-field';
}>(), {
  id: undefined,
  name: undefined,
  modelValue: '',
  rows: 3,
  maxRows: undefined,
  size: 'medium',
  status: 'default',
  placeholder: undefined,
  describedBy: undefined,
  ariaLabel: undefined,
  appearance: 'default',
});

const emit = defineEmits<{
  'update:modelValue': [value: string];
  input: [value: string, event: Event];
  change: [value: string, event: Event];
  focus: [value: string, event: FocusEvent];
  blur: [value: string, event: FocusEvent];
  keydown: [event: KeyboardEvent];
  keyup: [event: KeyboardEvent];
  compositionstart: [event: CompositionEvent];
  compositionend: [event: CompositionEvent];
}>();

const nativeProjection = computed(() => ({
  selector: 'textarea' as const,
  attributes: {
    id: props.id,
    name: props.name,
    required: props.required,
    'aria-busy': props.loading || undefined,
    'aria-describedby': props.describedBy,
    'aria-invalid': props.status === 'error' || undefined,
    'aria-label': props.ariaLabel,
  },
}));

function eventFrom(context: unknown): Event | undefined {
  return resolvePrimitiveNativeEvent(context);
}
function onTDesignInput(value: string | number, context?: unknown) {
  const next = resolvePrimitiveControlUpdate({ value, disabled: props.disabled, readonly: props.readonly, loading: props.loading });
  if (next === null) return;
  lastValue = next;
  emit('update:modelValue', next);
  const event = eventFrom(context);
  if (event && lastInputValue !== next) {
    lastInputValue = next;
    lastInputEvent = event;
    emit('input', next, event);
  }
}
function onTDesignChange(value: string | number, context?: unknown) {
  const next = resolvePrimitiveControlUpdate({ value, disabled: props.disabled, readonly: props.readonly, loading: props.loading });
  const event = eventFrom(context);
  if (next === null || !event) return;
  lastValue = next;
  if (event.type === 'input') {
    if (event !== lastInputEvent && lastInputValue !== next) {
      lastInputValue = next;
      lastInputEvent = event;
      emit('input', next, event);
    }
    return;
  }
  lastChangeValue = next;
  emit('change', next, event);
}
function onTDesignFocus(value: string | number, context?: unknown) {
  const event = resolvePrimitiveNativeEvent(context);
  if (event instanceof FocusEvent) {
    focusStartValue = String(value ?? '');
    lastValue = focusStartValue;
    lastChangeValue = focusStartValue;
    emit('focus', String(value ?? ''), event);
  }
}
function onTDesignBlur(value: string | number, context?: unknown) {
  const event = resolvePrimitiveNativeEvent(context);
  if (event instanceof FocusEvent) {
    emit('blur', String(value ?? ''), event);
    if (lastValue !== focusStartValue && lastValue !== lastChangeValue) {
      lastChangeValue = lastValue;
      emit('change', lastValue, event);
    }
  }
}
function resolveNativeTextarea(): HTMLTextAreaElement | null {
  const byId = props.id && typeof document !== 'undefined' ? document.getElementById(props.id) : null;
  if (byId instanceof HTMLTextAreaElement) return byId;
  const root = textareaRef.value?.$el;
  const container = root instanceof Node ? (root instanceof Element ? root : root.parentElement) : null;
  return container instanceof HTMLTextAreaElement
    ? container
    : container?.querySelector<HTMLTextAreaElement>('textarea') ?? null;
}
function onNativeKeydown(event: KeyboardEvent) {
  emit('keydown', event);
}
function onNativeKeyup(event: KeyboardEvent) {
  emit('keyup', event);
}
function onNativeCompositionStart(event: CompositionEvent) {
  emit('compositionstart', event);
}
function onNativeCompositionEnd(event: CompositionEvent) {
  emit('compositionend', event);
}
function onNativeInput(event: Event) {
  const target = event.target;
  if (!(target instanceof HTMLTextAreaElement)) return;
  if (props.id ? target.id !== props.id : target !== nativeTextarea) return;
  nativeTextarea = target;
  lastValue = target.value;
  lastInputValue = target.value;
  emit('input', target.value, event);
}
function onNativeChange(event: Event) {
  const target = event.target;
  if (!(target instanceof HTMLTextAreaElement)) return;
  if (props.id ? target.id !== props.id : target !== nativeTextarea) return;
  nativeTextarea = target;
  lastValue = target.value;
  lastChangeValue = target.value;
  emit('change', target.value, event);
}
function unbindNativeTextarea() {
  if (!nativeTextarea) return;
  nativeTextarea.removeEventListener('keydown', onNativeKeydown);
  nativeTextarea.removeEventListener('keyup', onNativeKeyup);
  nativeTextarea.removeEventListener('compositionstart', onNativeCompositionStart);
  nativeTextarea.removeEventListener('compositionend', onNativeCompositionEnd);
  nativeTextarea = null;
}
function bindNativeDocumentEvents() {
  if (nativeEventDocument || typeof document === 'undefined') return;
  nativeEventDocument = document;
  nativeEventDocument.addEventListener('input', onNativeInput, true);
  nativeEventDocument.addEventListener('change', onNativeChange, true);
}
function unbindNativeDocumentEvents() {
  if (!nativeEventDocument) return;
  nativeEventDocument.removeEventListener('input', onNativeInput, true);
  nativeEventDocument.removeEventListener('change', onNativeChange, true);
  nativeEventDocument = null;
}
function bindNativeTextarea() {
  const target = resolveNativeTextarea();
  if (target === nativeTextarea) return;
  unbindNativeTextarea();
  nativeTextarea = target;
  nativeTextarea?.addEventListener('keydown', onNativeKeydown);
  nativeTextarea?.addEventListener('keyup', onNativeKeyup);
  nativeTextarea?.addEventListener('compositionstart', onNativeCompositionStart);
  nativeTextarea?.addEventListener('compositionend', onNativeCompositionEnd);
}
bindNativeDocumentEvents();
onMounted(() => nextTick(() => {
  bindNativeDocumentEvents();
  bindNativeTextarea();
}));
onUpdated(() => {
  bindNativeDocumentEvents();
  bindNativeTextarea();
});
onBeforeUnmount(() => {
  unbindNativeTextarea();
  unbindNativeDocumentEvents();
});

defineExpose({
  focus: (options?: Parameters<HTMLElement['focus']>[0]) => {
    resolveNativeTextarea()?.focus(options);
  },
});
</script>
