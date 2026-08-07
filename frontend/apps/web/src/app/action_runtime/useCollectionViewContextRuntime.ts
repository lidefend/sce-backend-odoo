import type { Ref } from 'vue';
import { buildCollectionRouteQuery } from '../runtime/collectionViewRuntime';

type Dict = Record<string, unknown>;

export function useCollectionViewContextRuntime(options: {
  actionId: Ref<number | null>;
  menuId: Ref<number | null>;
  listOffset: Ref<number>;
  currentPath: () => string;
  currentQuery: () => Dict;
  replaceRoute: (target: { path: string; query: Dict }) => void;
  openRow: (row: Dict) => void;
}) {
  const storageKey = () => `sc:collection-scroll:${String(options.actionId.value || '')}:${String(options.menuId.value || '')}`;

  function persistRoute(patch: { viewMode?: string; listOffset?: number }): void {
    options.replaceRoute({
      path: options.currentPath(),
      query: buildCollectionRouteQuery(options.currentQuery(), patch),
    });
  }

  function persistMode(mode: string): void {
    persistRoute({ viewMode: mode, listOffset: options.listOffset.value });
  }

  function persistOffset(offset: number): void {
    options.listOffset.value = Math.max(0, Math.trunc(Number(offset || 0)));
    persistRoute({ listOffset: options.listOffset.value });
  }

  function handleRowClick(row: Dict): void {
    if (typeof window !== 'undefined') {
      window.sessionStorage.setItem(storageKey(), String(Math.max(0, Math.trunc(window.scrollY || 0))));
    }
    options.openRow(row);
  }

  function restoreScroll(): void {
    if (typeof window === 'undefined') return;
    const top = Number(window.sessionStorage.getItem(storageKey()) || 0);
    if (!Number.isFinite(top) || top <= 0) return;
    window.requestAnimationFrame(() => window.scrollTo({ top, behavior: 'auto' }));
  }

  return { handleRowClick, persistMode, persistOffset, restoreScroll };
}
