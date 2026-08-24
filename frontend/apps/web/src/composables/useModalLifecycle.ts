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
}) {
  const opener = ref<HTMLElement | null>(null);
  let locked = false;

  function focusInitial() {
    const initial = options.surface.value?.querySelector<HTMLElement>('[autofocus], [data-dialog-primary]');
    (initial || options.surface.value)?.focus();
  }

  function restoreOpener() {
    const target = opener.value;
    opener.value = null;
    if (target?.isConnected) target.focus();
  }

  function release() {
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
      event.preventDefault();
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

  watch(options.open, async (open) => {
    if (!open) {
      release();
      return;
    }
    opener.value = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    lockBodyScroll();
    locked = true;
    await nextTick();
    focusInitial();
  }, { immediate: true });

  onBeforeUnmount(() => {
    if (locked) unlockBodyScroll();
  });

  return { onKeydown };
}
