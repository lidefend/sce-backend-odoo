import type { FieldDescriptor } from '@sc/schema';
import { getCurrentScope, onScopeDispose, reactive, ref } from 'vue';
import type { RelationSearchDialogState } from './RelationSearchDialog.vue';
import {
  closedRelationSearchDialogState,
  mergeRelationOptionRows,
  openRelationSearchDialogState,
  relationOptionsWithSelectedFallback,
  selectedRelationOptionsFromValue,
  upsertRelationOptionRows,
} from './relationDescriptor';
import type { RelationOption, RelationSearchColumn, RelationSearchRow, RelationUiLabels } from './types';

export function useRelationRuntime() {
  const relationOptions = ref<Record<string, RelationOption[]>>({});
  const relationFieldDescriptors = ref<Record<string, Record<string, FieldDescriptor>>>({});
  const relationKeywords = reactive<Record<string, string>>({});
  const invalidatedRelationKeywords = reactive<Record<string, string>>({});
  const clearedDynamicRelationFields = reactive<Record<string, boolean>>({});
  const relationSearchDialog = reactive<RelationSearchDialogState>(closedRelationSearchDialogState());
  const deniedRelationModels = new Set<string>();
  const relationQueryTimers: Record<string, ReturnType<typeof setTimeout>> = {};

  const relationRuntimeGeneration = ref(0);
  const requestOwners = new Map<string, object>();
  let disposed = false;
  function captureRelationRequest(key: string): () => boolean {
    const generation = relationRuntimeGeneration.value;
    const owner = {};
    requestOwners.set(key, owner);
    return () => !disposed && relationRuntimeGeneration.value === generation && requestOwners.get(key) === owner;
  }
  if (getCurrentScope()) onScopeDispose(() => {
    disposed = true;
    invalidateRelationRequests();
  });

  function relationKeyword(name: string) {
    return String(relationKeywords[name] || '');
  }

  function relationOptionsForField(name: string, value: unknown) {
    return relationOptionsWithSelectedFallback(relationOptions.value[name], value);
  }

  function selectedRelationOptions(name: string, value: unknown) {
    return selectedRelationOptionsFromValue(relationOptions.value[name], value);
  }

  function setRelationKeywordValue(name: string, keyword: string) {
    relationKeywords[name] = keyword;
  }

  function filteredRelationOptions(name: string, value: unknown) {
    const rows = relationOptionsForField(name, value);
    const kw = relationKeyword(name).trim().toLowerCase();
    if (!kw) return rows;
    return rows.filter((row) => row.label.toLowerCase().includes(kw) || String(row.id).includes(kw));
  }

  function upsertRelationOption(fieldName: string, option: RelationOption | null) {
    const merged = upsertRelationOptionRows(relationOptions.value[fieldName], option);
    if (merged === relationOptions.value[fieldName]) return;
    relationOptions.value = {
      ...relationOptions.value,
      [fieldName]: merged,
    };
  }

  function mergeRelationOptions(fieldName: string, options: RelationOption[]) {
    relationOptions.value = {
      ...relationOptions.value,
      [fieldName]: mergeRelationOptionRows(relationOptions.value[fieldName], options),
    };
  }

  // Leaving a retained page cancels pending work without discarding its settled
  // labels or draft. A real record reload additionally clears those caches.
  function invalidateRelationRequests() {
    relationRuntimeGeneration.value += 1;
    requestOwners.clear();
    Object.keys(relationQueryTimers).forEach((key) => {
      clearTimeout(relationQueryTimers[key]);
      delete relationQueryTimers[key];
    });
    closeRelationSearchDialog();
  }

  function clearRelationRuntime() {
    invalidateRelationRequests();
    Object.keys(relationKeywords).forEach((key) => {
      delete relationKeywords[key];
    });
    Object.keys(invalidatedRelationKeywords).forEach((key) => {
      delete invalidatedRelationKeywords[key];
    });
    Object.keys(clearedDynamicRelationFields).forEach((key) => {
      delete clearedDynamicRelationFields[key];
    });
    relationOptions.value = {};
    relationFieldDescriptors.value = {};
    Object.assign(relationSearchDialog, closedRelationSearchDialogState());
    deniedRelationModels.clear();
  }

  let searchGeneration = 0;

  function closeRelationSearchDialog() {
    searchGeneration += 1;
    Object.assign(relationSearchDialog, closedRelationSearchDialogState());
  }

  function setRelationSearchKeyword(keyword: string) {
    relationSearchDialog.keyword = keyword;
  }

  function selectRelationSearchRow(row: { id: number }) {
    relationSearchDialog.selectedId = row.id;
  }

  async function openRelationSearch(params: {
    fieldName: string;
    descriptor?: FieldDescriptor;
    labels: RelationUiLabels;
    keyword: string;
    columns: RelationSearchColumn[];
    createMode: 'none' | 'quick' | 'page' | 'dialog';
    loadColumns: () => Promise<RelationSearchColumn[]>;
    runSearch: () => Promise<void>;
  }) {
    const generation = ++searchGeneration;
    Object.assign(relationSearchDialog, openRelationSearchDialogState({
      fieldName: params.fieldName,
      descriptor: params.descriptor,
      labels: params.labels,
      keyword: params.keyword,
      columns: params.columns,
      createMode: params.createMode,
    }));
    const columns = await params.loadColumns();
    if (generation !== searchGeneration || !relationSearchDialog.open || relationSearchDialog.fieldName !== params.fieldName) return;
    relationSearchDialog.columns = columns;
    await params.runSearch();
  }

  async function runRelationSearch(params: {
    fetchRows: (fieldName: string, keyword: string) => Promise<RelationSearchRow[]>;
    sanitizeError: (error: unknown, fallback: string) => string;
  }) {
    const fieldName = relationSearchDialog.fieldName;
    if (!fieldName) return;
    const generation = ++searchGeneration;
    relationSearchDialog.loading = true;
    relationSearchDialog.error = '';
    relationSearchDialog.rows = [];
    relationSearchDialog.options = [];
    relationSearchDialog.selectedId = null;
    try {
      const rows = await params.fetchRows(fieldName, relationSearchDialog.keyword);
      if (generation !== searchGeneration || !relationSearchDialog.open) return;
      relationSearchDialog.rows = rows;
      relationSearchDialog.options = rows.map((row) => ({ id: row.id, label: row.label }));
      relationSearchDialog.selectedId = null;
      relationOptions.value = {
        ...relationOptions.value,
        [fieldName]: relationSearchDialog.options,
      };
    } catch (err) {
      if (generation !== searchGeneration || !relationSearchDialog.open) return;
      relationSearchDialog.error = params.sanitizeError(err, relationSearchDialog.labels.search_failed || '');
    } finally {
      if (generation === searchGeneration) relationSearchDialog.loading = false;
    }
  }

  function confirmRelationSearchSelection(selectOption: (option: RelationOption) => void, rowArg?: RelationSearchRow) {
    if (!relationSearchDialog.open || relationSearchDialog.loading || relationSearchDialog.error) return;
    const row = relationSearchDialog.rows.find((item) => item.id === (rowArg?.id ?? relationSearchDialog.selectedId));
    if (!row) return;
    selectOption({ id: row.id, label: row.label });
  }

  function selectRelationSearchOption(option: RelationOption, applyOption: (fieldName: string, option: RelationOption) => void) {
    const fieldName = relationSearchDialog.fieldName;
    if (!fieldName) return;
    applyOption(fieldName, option);
    closeRelationSearchDialog();
  }

  async function createRelationFromSearchDialog(params: {
    resolveDescriptor: (fieldName: string) => FieldDescriptor | undefined;
    resolveMode: (descriptor?: FieldDescriptor) => 'none' | 'quick' | 'page' | 'dialog';
    selectOption: (option: RelationOption) => void;
    quickCreate: (fieldName: string, descriptor: FieldDescriptor | undefined, label: string) => Promise<void>;
    readValidationErrors: () => string[];
    clearValidationErrors: () => void;
    openCreateForm: (fieldName: string, descriptor?: FieldDescriptor) => Promise<void>;
  }) {
    const { fieldName } = relationSearchDialog;
    if (!fieldName) return;
    const descriptor = params.resolveDescriptor(fieldName);
    const label = relationSearchDialog.keyword.trim();
    const mode = params.resolveMode(descriptor);
    const exact = label
      ? relationSearchDialog.options.find((item) => item.label.trim().toLowerCase() === label.toLowerCase())
      : null;
    if (exact && mode !== 'page' && mode !== 'dialog') return params.selectOption(exact);
    if (mode === 'quick') {
      if (!label) {
        relationSearchDialog.error = relationSearchDialog.labels.missing_name || '';
        return;
      }
      params.clearValidationErrors();
      await params.quickCreate(fieldName, descriptor, label);
      const errors = params.readValidationErrors();
      if (!errors.length) closeRelationSearchDialog();
      else relationSearchDialog.error = errors.join('；');
      params.clearValidationErrors();
      return;
    }
    relationSearchDialog.open = false;
    await params.openCreateForm(fieldName, descriptor);
  }


  async function queryRelationOptions(params: {
    fieldName: string;
    keyword: string;
    relation: string;
    canRead: boolean;
    hasDynamicFallback: boolean;
    currentValue: unknown;
    optionsLimit: number;
    optionsSearchLimit: number;
    fetchOptions: (keyword: string, limit: number) => Promise<RelationOption[]>;
    isDeniedError: (error: unknown) => boolean;
  }): Promise<RelationOption[]> {
    const isCurrent = captureRelationRequest(`query:${params.fieldName}`);
    if (!isCurrent()) return [];
    const relation = String(params.relation || '').trim();
    if (!relation) return [];
    if (!params.canRead) {
      deniedRelationModels.add(relation);
      return [];
    }
    if (deniedRelationModels.has(relation)) return [];
    let search = String(params.keyword || '').trim();
    if (search && invalidatedRelationKeywords[params.fieldName] === search && !params.currentValue) {
      search = '';
      relationKeywords[params.fieldName] = '';
    }
    // Only the newest candidate query per field may publish its rows. Search
    // responses can settle out of order, and different keywords are separate
    // requests now, so a late response for an earlier keyword must neither
    // repaint the panel nor become selectable.
    try {
      const mapped = await params.fetchOptions(search, search ? params.optionsSearchLimit : params.optionsLimit);
      if (!isCurrent()) return [];
      if (search && !mapped.length && params.hasDynamicFallback) {
        return queryRelationOptions({ ...params, keyword: '' });
      }
      if (mapped.length || !search) {
        relationOptions.value = {
          ...relationOptions.value,
          [params.fieldName]: mapped,
        };
      }
      return mapped;
    } catch (err) {
      if (isCurrent() && params.isDeniedError(err)) deniedRelationModels.add(relation);
      return [];
    }
  }

  async function fetchRelationOptions(params: {
    relation: string;
    canRead: boolean;
    keyword: string;
    optionsLimit: number;
    optionsSearchLimit: number;
    fetchOptions: (keyword: string, limit: number) => Promise<RelationOption[]>;
  }): Promise<RelationOption[]> {
    const relation = String(params.relation || '').trim();
    if (!relation || !params.canRead || deniedRelationModels.has(relation)) return [];
    const keyword = String(params.keyword || '').trim();
    return params.fetchOptions(keyword, keyword ? params.optionsSearchLimit : params.optionsLimit);
  }

  return {
    relationOptions,
    relationFieldDescriptors,
    relationKeywords,
    invalidatedRelationKeywords,
    clearedDynamicRelationFields,
    relationSearchDialog,
    deniedRelationModels,
    relationQueryTimers,
    relationKeyword,
    relationOptionsForField,
    selectedRelationOptions,
    setRelationKeywordValue,
    filteredRelationOptions,
    upsertRelationOption,
    mergeRelationOptions,
    closeRelationSearchDialog,
    setRelationSearchKeyword,
    selectRelationSearchRow,
    openRelationSearch,
    runRelationSearch,
    confirmRelationSearchSelection,
    selectRelationSearchOption,
    createRelationFromSearchDialog,
    queryRelationOptions,
    fetchRelationOptions,
    clearRelationRuntime,
    invalidateRelationRequests,
    captureRelationRequest,
    relationRuntimeGeneration,
  };
}
