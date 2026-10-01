/**
 * Whether the viewport is at or below a width, reported as a reactive flag.
 *
 * A presentation helper: it reports the viewport, it never decides what a page
 * may show or who may see it. It lives in its own module so a component that is
 * kept off the global object — the adopted form section is guarded against
 * rebinding it, because that object carries the fail-closed predicate — can
 * still adapt a layout to a narrow screen.
 */
import { onBeforeUnmount, ref, type Ref } from 'vue';

export function useNarrowViewport(maxWidthPx: number): Ref<boolean> {
  const query = typeof window !== 'undefined' && typeof window.matchMedia === 'function'
    ? window.matchMedia(`(max-width: ${maxWidthPx}px)`)
    : null;
  const narrow = ref(Boolean(query?.matches));
  if (query) {
    const apply = () => { narrow.value = Boolean(query.matches); };
    query.addEventListener('change', apply);
    onBeforeUnmount(() => query.removeEventListener('change', apply));
  }
  return narrow;
}
