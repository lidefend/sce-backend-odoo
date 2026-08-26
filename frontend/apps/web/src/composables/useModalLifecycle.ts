import { nextTick, onBeforeUnmount, ref, watch, type Ref } from 'vue';
import { resolveModalKeyboardAction } from './modalKeyboard';

const FOCUSABLE = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

let bodyLockDepth = 0;
let savedBodyOverflow = '';
let savedBodyPaddingRight = '';

function lockBodyScroll() {
  if (bodyLockDepth === 0) {
    savedBodyOverflow = document.body.style.overflow;
    savedBodyPaddingRight = document.body.style.paddingRight;
    const scrollbarWidth = Math.max(0, window.innerWidth - document.documentElement.clientWidth);
    document.body.style.overflow = 'hidden';
    if (scrollbarWidth) document.body.style.paddingRight = `${scrollbarWidth}px`;
  }
  bodyLockDepth += 1;
}

function unlockBodyScroll() {
  bodyLockDepth = Math.max(0, bodyLockDepth - 1);
  if (bodyLockDepth) return;
  document.body.style.overflow = savedBodyOverflow;
  document.body.style.paddingRight = savedBodyPaddingRight;
}

export function useModalLifecycle(options: {
  open: () => boolean;
  surface: Ref<HTMLElement | null>;
  close: () => void;
  closeOnEscape?: () => boolean;
}) {
  const opener = ref<HTMLElement | null>(null);
  let locked = false;
  let focusGeneration = 0;

  function focusInitial() {
    const initial = options.surface.value?.querySelector<HTMLElement>('[autofocus], [data-dialog-primary]');
    (initial || options.surface.value)?.focus();
  }

  function focusInitialWhenVisible(generation: number, attempt = 0) {
    const surface = options.surface.value;
    if (generation !== focusGeneration || !options.open() || !surface || attempt > 120) return;
    if (surface.contains(document.activeElement)) return;
    if (surface.getClientRects().length > 0) {
      focusInitial();
    }
    requestAnimationFrame(() => focusInitialWhenVisible(generation, attempt + 1));
  }

  function restoreOpener(attempt = 0) {
    const target = opener.value;
    if (!target?.isConnected) {
      opener.value = null;
      return;
    }
    target.focus();
    if (attempt < 4) {
      requestAnimationFrame(() => restoreOpener(attempt + 1));
      return;
    }
    opener.value = null;
  }

  function release() {
    focusGeneration += 1;
    if (locked) {
      unlockBodyScroll();
      locked = false;
    }
    void nextTick(restoreOpener);
  }

  function onKeydown(event: KeyboardEvent) {
    const focusable = options.surface.value
      ? Array.from(options.surface.value.querySelectorAll<HTMLElement>(FOCUSABLE))
        .filter((element) => element.getClientRects().length > 0 && element.getAttribute('aria-hidden') !== 'true')
      : [];
    const activeIndex = focusable.findIndex((element) => element === document.activeElement);
    const action = resolveModalKeyboardAction({
      key: event.key,
      shiftKey: event.shiftKey,
      focusableCount: focusable.length,
      activeIndex,
      surfaceActive: document.activeElement === options.surface.value,
    });
    if (action === 'close') {
      if (options.closeOnEscape && !options.closeOnEscape()) return;
      event.preventDefault();
      event.stopPropagation();
      options.close();
      return;
    }
    if (action === 'focus-surface') {
      event.preventDefault();
      options.surface.value?.focus();
      return;
    }
    if (action === 'focus-last') {
      event.preventDefault();
      focusable.at(-1)?.focus();
    } else if (action === 'focus-first') {
      event.preventDefault();
      focusable[0]?.focus();
    }
  }

  watch([options.open, () => options.surface.value] as const, async ([open, surface]) => {
    if (!open) {
      release();
      return;
    }
    if (!locked) {
      opener.value = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      lockBodyScroll();
      locked = true;
    }
    if (!surface) return;
    await nextTick();
    focusGeneration += 1;
    focusInitialWhenVisible(focusGeneration);
  }, { immediate: true });

  onBeforeUnmount(() => {
    if (locked) unlockBodyScroll();
  });

  return { onKeydown };
}
