type Dict = Record<string, unknown>;

export type RecordOpenIntent = 'open' | 'handling' | 'explicit_readonly' | 'explicit_edit';

export function normalizeRecordOpenIntent(raw: unknown): RecordOpenIntent {
  const value = String(raw || '').trim().toLowerCase();
  if (['readonly', 'read', 'view', 'explicit_readonly', 'explicit-readonly'].includes(value)) {
    return 'explicit_readonly';
  }
  if (['edit', 'write', 'explicit_edit', 'explicit-edit'].includes(value)) {
    return 'explicit_edit';
  }
  if (['handling', 'process', 'work_on'].includes(value)) {
    return 'handling';
  }
  return 'open';
}

export function normalizeModelWriteAuthority(raw: unknown): boolean | null {
  if (typeof raw === 'boolean') return raw;
  return null;
}

export function resolveCollectionWriteAuthority(options: { modelRights?: unknown }): boolean {
  const rights = options.modelRights;
  if (!rights || typeof rights !== 'object' || Array.isArray(rights)) return false;
  const write = (rights as Record<string, unknown>).write;
  return typeof write === 'boolean' ? write : false;
}

export function resolveRecordOpenTarget(options: {
  model: string;
  recordId: number | string;
  actionId?: number;
  menuId?: number;
  requestedIntent?: RecordOpenIntent;
  modelWriteAuthority?: boolean | null;
  carryQuery?: Dict;
}): { path: string; query: Dict } | null {
  const model = String(options.model || '').trim();
  const recordId = resolveActionViewRecordId(options.recordId);
  if (!model || recordId === null) return null;
  const intent = normalizeRecordOpenIntent(options.requestedIntent);
  const editable = (intent === 'open' || intent === 'handling' || intent === 'explicit_edit')
    && options.modelWriteAuthority === true;
  return {
    path: `/${editable ? 'f' : 'r'}/${model}/${recordId}`,
    query: {
      menu_id: options.menuId || undefined,
      action_id: options.actionId || undefined,
      ...(options.carryQuery || {}),
    },
  };
}

export function resolveActionViewRecordId(rawId: unknown): number | string | null {
  if (typeof rawId === 'number') return rawId;
  if (typeof rawId === 'string' && rawId.trim()) return rawId;
  return null;
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
  return resolveRecordOpenTarget({
    model: options.targetModel,
    recordId,
    actionId: options.actionId,
    menuId: options.menuId,
    requestedIntent: recordId === 'new' ? 'explicit_edit' : 'open',
    modelWriteAuthority: options.editable,
    carryQuery: options.carryQuery,
  });
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
