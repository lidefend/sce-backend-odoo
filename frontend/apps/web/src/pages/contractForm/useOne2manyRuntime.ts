import { replayOne2manyOnchange } from './one2manyOnchange';
import { computed, reactive } from 'vue';
import { createOne2manyRelationRequestAuthority } from '../../components/template/one2manyRelationQuery';
import type { One2ManyColumn, One2ManyInlineRow, RelationOption } from './types';
import {
  appendOne2manyDraftRow,
  buildOne2manyCommandValue,
  collectOne2manyDraftValidationFromRows,
  ensureOne2manyRows,
  initOne2manyRowsFromRelationSource,
  mergeOne2manyHydratedRecords,
  one2manyRowHintsFromPatches,
  one2manyNativeEvaluationIds,
  removeOne2manyDraftRow,
  resolveOne2manyRowColumnBehavior,
  resolveOne2manyColumnInvisible,
  restoreOne2manyDraftRow,
  setOne2manyDraftRowField,
  visibleOne2manyRows,
} from './one2manyUtils';

function makeOne2manyKey() {
  return `o2m_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
}

export function useOne2manyRuntime(params: {
  model: () => string;
  recordId: () => number;
  originalValues: () => Record<string, unknown>;
  onchangeLinePatches: () => Array<Record<string, unknown>>;
  resolveColumns: (fieldName: string) => One2ManyColumn[];
  resolveDataColumns?: (fieldName: string) => One2ManyColumn[];
  resolvePrimaryColumn: (fieldName: string) => string;
  resolveRelationOptions: (fieldName: string) => RelationOption[];
  parentValues: (fieldName: string) => Record<string, unknown>;
  markFieldChanged: (fieldName: string) => void;
  loadDefaults?: (fieldName: string) => Promise<Record<string, unknown>>;
  loadRowChange?: (fieldName: string, row: { id: number; values: Record<string, unknown>; changed: string[] }) => Promise<Record<string, unknown>>;
  markDirty?: (fieldName: string) => void;
  createScope?: () => unknown;
  createDraftIdentity?: (fieldName: string) => unknown;
  onCreateError?: (error: unknown) => void;
}) {
  const dataColumns = (name: string) => params.resolveDataColumns?.(name) ?? params.resolveColumns(name);
  const rowsByField = reactive<Record<string, One2ManyInlineRow[]>>({});
  const initialized = reactive<Record<string, boolean>>({});
  const requests = createOne2manyRelationRequestAuthority();
  const loadingDefaults = reactive<Record<string, boolean>>({});
  const changing = reactive<Record<string, boolean>>({});
  const changeErrors = reactive<Record<string, string>>({});
  const pendingFields = new Map<string, Set<string>>();
  const defaultsPending = computed(() => Object.values(loadingDefaults).some(Boolean) || Object.values(changing).some(Boolean));

  function projectModifierValues(source: Record<string, unknown>) {
    const values = { ...source };
    const types = values['$native.fieldTypes'] as Record<string, unknown> | undefined;
    for (const name of Object.keys(initialized)) {
      if (initialized[name] && types?.[name] === 'one2many') values[name] = one2manyNativeEvaluationIds(fieldRows(name));
    }
    return values;
  }

  function modifierParentValues(fieldName: string) {
    return projectModifierValues(params.parentValues(fieldName));
  }

  function fieldRows(name: string) {
    return Array.isArray(rowsByField[name]) ? rowsByField[name] : [];
  }

  // 声明可见集合由 one2manyUtils.visibleOne2manyRows 单点裁决：只排除已声明移除的行，
  // 空值展示行不得被丢弃。运行时不在此处新增第二套可见性口径。
  function visibleRows(name: string) {
    return visibleOne2manyRows(rowsByField, name);
  }

  function removedRows(name: string) {
    return fieldRows(name).filter((row) => row.removed);
  }

  function ensureRows(name: string) {
    return ensureOne2manyRows(rowsByField, name);
  }

  function clearRows() {
    pendingFields.clear();
    for (const key of Object.keys(changing)) { requests.invalidate(key); delete changing[key]; }
    for (const key of Object.keys(changeErrors)) delete changeErrors[key];
    Object.keys(rowsByField).forEach((key) => {
      requests.invalidate(key);
      loadingDefaults[key] = false;
      delete rowsByField[key];
      delete initialized[key];
    });
  }

  async function addRow(name: string) {
    if (loadingDefaults[name]) return;
    const revision = requests.begin(name);
    const scope = params.createScope?.();
    const model = params.model();
    const recordId = params.recordId();
    const draftIdentity = () => JSON.stringify(params.createDraftIdentity
      ? params.createDraftIdentity(name) : { parent: params.parentValues(name), rows: rowsByField });
    let parentSnapshot: string | undefined;
    const ownsRequest = () => requests.isCurrent(name, revision) && params.model() === model
      && params.recordId() === recordId && params.createScope?.() === scope
      && (parentSnapshot === undefined || draftIdentity() === parentSnapshot);
    loadingDefaults[name] = true;
    try {
      if (!initialized[name]) initRows(name, params.originalValues()[name]);
      parentSnapshot = draftIdentity();
      const defaults = params.loadDefaults ? await params.loadDefaults(name) : {};
      if (!ownsRequest()) return;
      appendOne2manyDraftRow({
        rowsByField, fieldName: name, key: makeOne2manyKey(),
        primary: params.resolvePrimaryColumn(name), columns: dataColumns(name), defaults,
      });
      params.markFieldChanged(name);
    } catch (error) {
      if (ownsRequest()) params.onCreateError?.(error);
    } finally {
      if (requests.isCurrent(name, revision)) loadingDefaults[name] = false;
    }
  }

  async function setRowField(fieldName: string, rowKey: string, column: One2ManyColumn, value: unknown) {
    if (!params.resolveColumns(fieldName).some(item => item.name === column.name && item.key === column.key)) return;
    const changed = setOne2manyDraftRowField({
      rowsByField, fieldName, rowKey, column, columns: dataColumns(fieldName), value, parentValues: modifierParentValues(fieldName),
    });
    if (!changed) return;
    params.markDirty?.(fieldName);
    if (!params.loadRowChange) { params.markFieldChanged(fieldName); return; }
    const row = fieldRows(fieldName).find(item => item.key === rowKey)!;
    const key = `${fieldName}:${rowKey}`;
    const fields = pendingFields.get(key) || new Set<string>();
    fields.add(column.name); pendingFields.set(key, fields);
    const revision = requests.begin(key);
    const model = params.model(), recordId = params.recordId(), scope = params.createScope?.();
    const ownsRow = () => requests.isCurrent(key, revision)
      && fieldRows(fieldName).some(item => item.key === rowKey && !item.removed);
    const sameSurface = () => ownsRow() && params.model() === model
      && params.recordId() === recordId && params.createScope?.() === scope;
    const draft = () => JSON.stringify(params.createDraftIdentity ? params.createDraftIdentity(fieldName)
      : { parent: params.parentValues(fieldName), rows: rowsByField });
    const before = draft();
    changing[key] = true; delete changeErrors[key];
    try {
      const values = Object.fromEntries((row.dirtyFields || []).map(name => [name, row.values[name]]));
      // Existing rows need their full loaded view frame; new rows retain only
      // actual default/edit/server presence, never UI placeholders.
      const source = row.isNew ? values : Object.fromEntries(dataColumns(fieldName)
        .filter(item => item.name !== 'id' && Object.prototype.hasOwnProperty.call(row.values, item.name))
        .map(item => [item.name, row.values[item.name]]));
      const patch = await params.loadRowChange(fieldName, { id: row.isNew ? 0 : Number(row.id),
        values: JSON.parse(JSON.stringify(source)), changed: [...fields] });
      if (!ownsRow()) return;
      if (!sameSurface() || draft() !== before) throw new Error('明细联动上下文已变化，请重新修改该行');
      prepareOnchangeRows(fieldName, [[1, row.isNew ? row.key : row.id, patch]])();
      pendingFields.delete(key);
      params.markFieldChanged(fieldName);
    } catch (error) {
      if (ownsRow()) changeErrors[key] = error instanceof Error ? error.message : '明细联动未完成';
    } finally {
      if (requests.isCurrent(key, revision)) changing[key] = false;
    }
  }

  function visibleColumns(fieldName: string) {
    return params.resolveColumns(fieldName).filter(column => !resolveOne2manyColumnInvisible(column, modifierParentValues(fieldName)));
  }

  function effectiveColumn(fieldName: string, row: One2ManyInlineRow, column: One2ManyColumn) {
    const behavior = resolveOne2manyRowColumnBehavior(
      column,
      row.values || {},
      modifierParentValues(fieldName),
      row.modifierPatches || {},
      dataColumns(fieldName),
    );
    return {
      ...column,
      invisible: behavior.invisible,
      columnInvisible: behavior.columnInvisible,
      readonly: behavior.readonly,
      required: behavior.required,
    };
  }

  function removeRow(fieldName: string, rowKey: string) {
    if (removeOne2manyDraftRow(rowsByField, fieldName, rowKey)) params.markFieldChanged(fieldName);
  }

  function restoreRow(fieldName: string, rowKey: string) {
    if (restoreOne2manyDraftRow(rowsByField, fieldName, rowKey)) params.markFieldChanged(fieldName);
  }

  function initRows(name: string, source: unknown) {
    rowsByField[name] = initOne2manyRowsFromRelationSource({
      source,
      columns: dataColumns(name),
      relationOptions: params.resolveRelationOptions(name),
      primary: params.resolvePrimaryColumn(name),
    });
    initialized[name] = true;
  }

  function prepareOnchangeRows(name: string, commands: unknown) {
    const baseline = initialized[name] ? fieldRows(name) : initOne2manyRowsFromRelationSource({
      source: params.originalValues()[name], columns: dataColumns(name),
      relationOptions: params.resolveRelationOptions(name), primary: params.resolvePrimaryColumn(name),
    });
    const next = replayOne2manyOnchange({ rows: baseline, commands, columns: dataColumns(name),
      primary: params.resolvePrimaryColumn(name), makeKey: makeOne2manyKey });
    return () => { rowsByField[name] = next; initialized[name] = true; };
  }

  function mergeHydratedRecords(fieldName: string, records: Array<Record<string, unknown>>) {
    mergeOne2manyHydratedRecords({
      rows: ensureRows(fieldName).filter((row) => row.id && !row.isNew),
      columns: dataColumns(fieldName),
      records,
    });
  }

  function buildCommandValue(name: string, mode: 'onchange' | 'write') {
    return buildOne2manyCommandValue(params.originalValues()[name], fieldRows(name), mode, dataColumns(name), modifierParentValues(name));
  }

  function collectValidation() {
    const result = collectOne2manyDraftValidationFromRows({
      rowsByField,
      model: params.model(),
      recordId: params.recordId(),
      resolvePrimaryColumn: params.resolvePrimaryColumn,
      resolveColumns: dataColumns,
      resolveParentValues: modifierParentValues,
    });
    for (const [name, rows] of Object.entries(rowsByField)) for (const row of rows) {
      if (row.removed) continue;
      const key = `${name}:${row.key}`;
      if (changing[key]) result.issues.push('明细联动尚未完成，请稍后保存');
      else if (changeErrors[key]) result.issues.push(changeErrors[key]);
    }
    return result;
  }

  function rowHints(fieldName: string, row: One2ManyInlineRow) {
    return one2manyRowHintsFromPatches({
      patches: params.onchangeLinePatches(),
      fieldName,
      row,
    });
  }

  function applyLinePatches(linePatches: Array<{
    field?: unknown;
    row_key?: unknown;
    row_id?: unknown;
    patch?: unknown;
    modifiers_patch?: unknown;
  }>) {
    if (!Array.isArray(linePatches) || !linePatches.length) return;
    linePatches.forEach((line) => {
      const fieldName = String(line.field || '').trim();
      if (!fieldName) return;
      const rowKey = String(line.row_key || '').trim();
      const rowId = Number(line.row_id || 0);
      const rows = ensureRows(fieldName);
      const row = rows.find((item) => (rowKey && item.key === rowKey) || (rowId > 0 && Number(item.id || 0) === rowId));
      if (!row) return;
      const patch = line.patch;
      if (patch && typeof patch === 'object') {
        row.values = {
          ...(row.values || {}),
          ...(patch as Record<string, unknown>),
        };
        if (row.isNew) row.dirtyFields = [...new Set([...row.dirtyFields, ...Object.keys(patch)])];
      }
      const modifierPatch = line.modifiers_patch;
      if (modifierPatch && typeof modifierPatch === 'object' && !Array.isArray(modifierPatch)) {
        row.modifierPatches = {
          ...(row.modifierPatches || {}),
          ...(modifierPatch as Record<string, Record<string, unknown>>),
        };
      }
    });
  }

  return {
    defaultsPending,
    projectModifierValues,
    rowsByField,
    fieldRows,
    visibleRows,
    removedRows,
    ensureRows,
    clearRows,
    addRow,
    setRowField,
    effectiveColumn,
    visibleColumns,
    removeRow,
    restoreRow,
    initRows,
    prepareOnchangeRows,
    mergeHydratedRecords,
    buildCommandValue,
    collectValidation,
    rowHints,
    applyLinePatches,
  };
}
