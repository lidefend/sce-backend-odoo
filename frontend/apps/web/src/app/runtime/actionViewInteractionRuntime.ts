import {
  recordEntryFromModelRights,
  resolveRecordEntryId,
  resolveRecordOpenTarget as resolveFormalRecordOpenTarget,
} from './recordEntryContract';

type Dict = Record<string, unknown>;

export function resolveCollectionWriteAuthority(options: { modelRights?: unknown }): boolean {
  const rights = options.modelRights;
  if (!rights || typeof rights !== 'object' || Array.isArray(rights)) return false;
  const write = (rights as Record<string, unknown>).write;
  return typeof write === 'boolean' ? write : false;
}

export function resolveActionViewRecordId(rawId: unknown): number | string | null {
  return resolveRecordEntryId(rawId);
}

export function buildActionViewRowClickTarget(options: {
  targetModel: string;
  rawId: unknown;
  menuId: number;
  actionId: number;
  carryQuery: Dict;
  editable: boolean;
}): { path: string; query: Dict } | null {
  const recordId = resolveActionViewRecordId(options.rawId) || '';
  return resolveFormalRecordOpenTarget(recordEntryFromModelRights({
    model: options.targetModel,
    recordId,
    modelRights: { write: options.editable },
    entryIntent: recordId === 'new' ? 'explicit_edit' : 'open',
    actionId: options.actionId,
    menuId: options.menuId,
    carryQuery: options.carryQuery,
  }));
}

export function shouldUseCanonicalCollectionDetail(options: {
  viewMode: unknown;
  collectionSemantic: unknown;
}): boolean {
  const semantic = String(options.collectionSemantic || '').trim().toLowerCase();
  const viewMode = String(options.viewMode || '').trim().toLowerCase();
  if (viewMode === 'activity') return true;
  if (semantic === 'hierarchy_browser' || semantic === 'hierarchy_planner' || semantic === 'hierarchical_worksheet') return true;
  return viewMode === 'kanban' && semantic === 'card';
}

export function resolveListControlTransition(options: {
  control: 'search' | 'sort' | 'filter';
  value: string;
}): {
  nextSearchTerm: string | null;
  nextSortValue: string | null;
  nextFilterValue: 'all' | 'active' | 'archived' | null;
  nextGroupWindowOffset: number;
  shouldClearSelection: boolean;
} {
  return {
    nextSearchTerm: options.control === 'search' ? options.value : null,
    nextSortValue: options.control === 'sort' ? options.value : null,
    nextFilterValue: options.control === 'filter' ? (options.value as 'all' | 'active' | 'archived') : null,
    nextGroupWindowOffset: 0,
    shouldClearSelection: options.control === 'filter',
  };
}

export function resolveSelectionAfterToggle(options: {
  selectedIds: number[];
  id: number;
  selected: boolean;
}): number[] {
  const set = new Set(options.selectedIds);
  if (options.selected) {
    set.add(options.id);
  } else {
    set.delete(options.id);
  }
  return Array.from(set);
}

export function resolveSelectionAfterToggleAll(options: {
  selectedIds: number[];
  ids: number[];
  selected: boolean;
}): number[] {
  if (!options.ids.length) return options.selectedIds;
  const set = new Set(options.selectedIds);
  options.ids.forEach((id) => {
    if (options.selected) set.add(id);
    else set.delete(id);
  });
  return Array.from(set);
}
