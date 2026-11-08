<template>
  <ScButton
    ref="buttonRef"
    :variant="variant"
    :size="size"
    :disabled="disabled"
    :loading="loading"
    :loading-label="loadingLabel"
    :aria-label="accessibleLabel"
    @pointerdown="rememberFocusSource('pointer')"
    @keydown="onKeydown"
    @keyup="onKeyup"
    @click="onClick"
    @focus="onFocus"
    @blur="onBlur"
  >
    <slot />
  </ScButton>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import type {
  ButtonPortEmits,
  ButtonPortProps,
  ButtonPortSlots,
  PrimitiveHandle,
  PrimitiveEventSource,
} from '@sc/ui/primitive-port';
import ScButton from '../ScButton.vue';

defineOptions({ inheritAttrs: true });

const props = withDefaults(defineProps<ButtonPortProps>(), {
  variant: 'secondary',
  size: 'medium',
  disabled: false,
  loading: false,
  loadingLabel: '处理中',
  accessibleLabel: undefined,
});

const emit = defineEmits<ButtonPortEmits>();
defineSlots<ButtonPortSlots>();

const buttonRef = ref<InstanceType<typeof ScButton> | null>(null);
let keyboardActivationPending = false;
let resetKeyboardActivationTimer: ReturnType<typeof setTimeout> | undefined;
let focusSource: PrimitiveEventSource = 'programmatic';

function clearKeyboardActivationTimer() {
  if (resetKeyboardActivationTimer !== undefined) {
    clearTimeout(resetKeyboardActivationTimer);
    resetKeyboardActivationTimer = undefined;
  }
}

function rememberFocusSource(source: PrimitiveEventSource) {
  focusSource = source;
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Tab') {
    rememberFocusSource('keyboard');
  }
  if (event.key !== 'Enter' && event.key !== ' ') {
    return;
  }
  if (props.disabled || props.loading) {
    keyboardActivationPending = false;
    return;
  }
  clearKeyboardActivationTimer();
  keyboardActivationPending = true;
}

function onKeyup(event: KeyboardEvent) {
  if (event.key !== 'Enter' && event.key !== ' ') {
    return;
  }
  // Space dispatches its native click immediately after keyup. Keep the
  // source marker through the current task so that click remains keyboard.
  clearKeyboardActivationTimer();
  resetKeyboardActivationTimer = setTimeout(() => {
    keyboardActivationPending = false;
    resetKeyboardActivationTimer = undefined;
  }, 0);
}

function onClick(event: MouseEvent) {
  if (props.disabled || props.loading) {
    keyboardActivationPending = false;
    return;
  }
  const source: PrimitiveEventSource = !event.isTrusted
    ? 'programmatic'
    : keyboardActivationPending || event.detail === 0
      ? 'keyboard'
      : 'pointer';
  keyboardActivationPending = false;
  clearKeyboardActivationTimer();
  emit('activate', { source, nativeEvent: event });
}

function onFocus(event: FocusEvent) {
  emit('focus', { source: focusSource, nativeEvent: event });
  focusSource = 'programmatic';
}

function onBlur(event: FocusEvent) {
  emit('blur', { source: focusSource, nativeEvent: event });
  focusSource = 'programmatic';
}

function focus(options?: Parameters<PrimitiveHandle['focus']>[0]) {
  const root: Node | null | undefined = buttonRef.value?.$el;
  const container = root instanceof Element ? root : root?.parentElement;
  const target = container instanceof HTMLButtonElement
    ? container
    : container?.querySelector<HTMLButtonElement>('button');
  target?.focus(options);
}

defineExpose({ focus });
</script>
