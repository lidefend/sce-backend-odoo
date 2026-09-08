import type { Ref } from 'vue';
import { buildCollectionRouteQuery } from '../runtime/collectionViewRuntime';

type Dict = Record<string, unknown>;

export function collectionContextStorageKey(kind: 'scroll' | 'anchor', actionId: unknown, menuId: unknown): string {
  return `sc:collection-${kind}:${String(actionId || '')}:${String(menuId || '')}`;
}

export function resolveCollectionAnchorId(row: Dict): string {
  const raw = row.id;
  if (typeof raw === 'number' && Number.isFinite(raw) && raw > 0) return String(Math.trunc(raw));
  if (typeof raw === 'string' && raw.trim()) return raw.trim();
  return '';
}

export function useCollectionViewContextRuntime(options: {
  actionId: Ref<number | null>;
  menuId: Ref<number | null>;
  listOffset: Ref<number>;
  currentPath: () => string;
  currentQuery: () => Dict;
  replaceRoute: (target: { path: string; query: Dict }) => void;
  openRow: (row: Dict) => void;
}) {
  const storageKey = (kind: 'scroll' | 'anchor') => collectionContextStorageKey(
    kind,
    options.actionId.value,
    options.menuId.value,
  );

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
      window.sessionStorage.setItem(storageKey('scroll'), String(Math.max(0, Math.trunc(window.scrollY || 0))));
      const anchorId = resolveCollectionAnchorId(row);
      if (anchorId) window.sessionStorage.setItem(storageKey('anchor'), anchorId);
    }
    options.openRow(row);
  }

  function restoreScroll(): void {
    if (typeof window === 'undefined') return;
    const top = Number(window.sessionStorage.getItem(storageKey('scroll')) || 0);
    const anchorId = String(window.sessionStorage.getItem(storageKey('anchor')) || '').trim();
    window.requestAnimationFrame(() => {
      if (Number.isFinite(top) && top > 0) window.scrollTo({ top, behavior: 'auto' });
      document.querySelectorAll<HTMLElement>('[data-return-anchor="active"]').forEach((element) => {
        element.removeAttribute('data-return-anchor');
      });
      if (!anchorId) return;
      const anchor = Array.from(document.querySelectorAll<HTMLElement>('[data-record-key]'))
        .find((element) => element.dataset.recordKey === anchorId);
      if (!anchor) return;
      anchor.setAttribute('data-return-anchor', 'active');
      const focusTarget = anchor.matches('button,[tabindex]')
        ? anchor
        : anchor.querySelector<HTMLElement>('button,[tabindex]');
      focusTarget?.focus({ preventScroll: true });
      window.sessionStorage.removeItem(storageKey('anchor'));
    });
  }

  return { handleRowClick, persistMode, persistOffset, restoreScroll };
}
