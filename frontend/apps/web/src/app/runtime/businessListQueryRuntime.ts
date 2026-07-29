type WritableRef<T> = { value: T };
type CustomFilterValue = { label: string; domain: unknown[] } | null;

type BusinessListQueryState = {
  composing: WritableRef<boolean>;
  searchDraft: WritableRef<string>;
  searchTerm: WritableRef<string>;
  filterValue: WritableRef<string>;
  contractFilterKey: WritableRef<string>;
  showMoreContractFilters: WritableRef<boolean>;
  savedFilterKey: WritableRef<string>;
  showMoreSavedFilters: WritableRef<boolean>;
  customFilter: WritableRef<unknown>;
  groupByField: WritableRef<string>;
  groupByLabel: WritableRef<string>;
  listOffset: WritableRef<number>;
  groupWindowOffset: WritableRef<number>;
  clearSelection: () => void;
  syncRoute: () => void;
  reload: () => void;
};

export function countBusinessListConditions(values: unknown[]): number {
  return values.filter((value) => Boolean(String(value ?? '').trim())).length;
}

export function applyBusinessListGroup(
  payload: { key: string; label: string },
  displayLabel: WritableRef<string>,
  apply: (key: string) => void,
): void {
  const key = String(payload.key || '').trim();
  if (!key) return;
  displayLabel.value = String(payload.label || key);
  apply(key);
}

export function clearBusinessListGroup(displayLabel: WritableRef<string>, clear: () => void): void {
  displayLabel.value = '';
  clear();
}

export function applyBusinessListCustomFilter(
  payload: { label: string; domain: unknown[] },
  activeFilter: WritableRef<CustomFilterValue>,
  refresh: () => void,
): void {
  activeFilter.value = {
    label: String(payload.label || '自定义筛选'),
    domain: Array.isArray(payload.domain) ? payload.domain : [],
  };
  refresh();
}

export function clearBusinessListCustomFilter(
  activeFilter: WritableRef<CustomFilterValue>,
  refresh: () => void,
): void {
  activeFilter.value = null;
  refresh();
}

export function clearBusinessListQueryState(state: BusinessListQueryState): void {
  state.composing.value = false;
  state.searchDraft.value = '';
  state.searchTerm.value = '';
  state.filterValue.value = 'all';
  state.contractFilterKey.value = '';
  state.showMoreContractFilters.value = false;
  state.savedFilterKey.value = '';
  state.showMoreSavedFilters.value = false;
  state.customFilter.value = null;
  state.groupByField.value = '';
  state.groupByLabel.value = '';
  state.listOffset.value = 0;
  state.groupWindowOffset.value = 0;
  state.clearSelection();
  state.syncRoute();
  state.reload();
}
