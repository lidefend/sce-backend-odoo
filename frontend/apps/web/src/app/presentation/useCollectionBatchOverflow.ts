import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue';

export function useCollectionBatchOverflow() {
  const batchOverflowRoot = ref<HTMLElement | null>(null);
  const batchOverflowToggle = ref<HTMLButtonElement | null>(null);
  const batchOverflowOpen = ref(false);

  function toggleBatchOverflow() {
    batchOverflowOpen.value = !batchOverflowOpen.value;
    if (!batchOverflowOpen.value) return;
    void nextTick(() => batchOverflowRoot.value
      ?.querySelector<HTMLElement>('.batch-overflow-menu button:not(:disabled)')
      ?.focus());
  }

  function closeOnOutsidePointer(event: PointerEvent) {
    if (!batchOverflowRoot.value?.contains(event.target as Node)) batchOverflowOpen.value = false;
  }

  function closeOnEscape(event: KeyboardEvent) {
    if (event.key !== 'Escape' || !batchOverflowOpen.value) return;
    batchOverflowOpen.value = false;
    const root = batchOverflowToggle.value;
    const focusTarget = root?.matches('button') ? root : root?.querySelector<HTMLElement>('button');
    focusTarget?.focus();
  }

  onMounted(() => {
    document.addEventListener('pointerdown', closeOnOutsidePointer);
    document.addEventListener('keydown', closeOnEscape);
  });
  onBeforeUnmount(() => {
    document.removeEventListener('pointerdown', closeOnOutsidePointer);
    document.removeEventListener('keydown', closeOnEscape);
  });

  return { batchOverflowRoot, batchOverflowToggle, batchOverflowOpen, toggleBatchOverflow };
}
