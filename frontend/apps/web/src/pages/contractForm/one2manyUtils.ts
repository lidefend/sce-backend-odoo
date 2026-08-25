import { buildOne2ManyInlineCommands } from '../../app/x2manyCommands';
import { fieldType, fromDatetimeInputValue, normalizeRelationIds, toDateInputValue, toDatetimeInputValue } from './fieldUtils';
import type { One2ManyColumn, One2ManyInlineRow } from './types';
import type { FieldDescriptor } from '@sc/schema';
import { evaluateNativeModifierValue } from './nativeLayoutUtils';

export function subviewColumnCount(subview: unknown): number {
  if (!subview || typeof subview !== 'object' || Array.isArray(subview)) return 0;
  const tree = (subview as Record<string, unknown>).tree;
  if (!tree || typeof tree !== 'object' || Array.isArray(tree)) return 0;
  const occurrences = (tree as Record<string, unknown>).column_occurrences;
  if (Array.isArray(occurrences) && occurrences.length) return occurrences.length;
  const columns = (tree as Record<string, unknown>).columns;
  if (!Array.isArray(columns)) return 0;
  return columns.length;
}

export function one2manySubviewPolicies(subview: unknown) {
  const policies = subview && typeof subview === 'object' && !Array.isArray(subview)
    ? (subview as Record<string, unknown>).policies
    : undefined;
  return policies && typeof policies === 'object'
    ? policies as Record<string, unknown>
    : {};
}

export function selectOne2manySubview(legacySubview: unknown, nativeSubview: unknown) {
  const nativeColumns = subviewColumnCount(nativeSubview);
  return nativeColumns > 0 ? nativeSubview : (legacySubview || nativeSubview);
}

function staticNativeBoolean(value: unknown): boolean | undefined {
  if (value === true || value === 1 || value === '1' || value === 'True' || value === 'true') return true;
  if (value === false || value === 0 || value === '0' || value === 'False' || value === 'false') return false;
  return undefined;
}

function one2manyColumnLabel(value: unknown, fallback: string) {
  const label = String(value || '').trim();
  if (label === 'display_name' || label === 'name') return '名称';
  if (label) return label;
  return fallback === 'display_name' || fallback === 'name' ? '名称' : fallback;
}

function one2manySelectionOptions(value: unknown): Array<[string, string]> | undefined {
  if (!Array.isArray(value)) return undefined;
  const options = value.flatMap((item): Array<[string, string]> => {
    if (Array.isArray(item) && item.length >= 2) return [[String(item[0]), String(item[1])]];
    if (!item || typeof item !== 'object') return [];
    const row = item as Record<string, unknown>;
    if (row.value === undefined || row.label === undefined) return [];
    return [[String(row.value), String(row.label)]];
  });
  return options.length ? options : undefined;
}

export function one2manyColumnsFromSubview(
  subview: unknown,
  resolveDescriptor: (column: string) => FieldDescriptor | null | undefined,
) {
  const tree = subview && typeof subview === 'object' && !Array.isArray(subview)
    ? (subview as Record<string, unknown>).tree
    : undefined;
  const treeRecord = tree && typeof tree === 'object' && !Array.isArray(tree)
    ? tree as Record<string, unknown>
    : {};
  const occurrences = treeRecord.column_occurrences;
  const businessColumns = Array.isArray(treeRecord.columns) ? treeRecord.columns : [];
  const schemaColumns = Array.isArray(treeRecord.columns_schema) ? treeRecord.columns_schema : [];
  const businessColumnsByName = new Map([...businessColumns, ...schemaColumns].flatMap((item) => {
    if (!item || typeof item !== 'object' || Array.isArray(item)) return [];
    const row = item as Record<string, unknown>;
    const name = String(row.name || '').trim();
    return name ? [[name, row] as const] : [];
  }));
  const businessNames = new Set(businessColumns.map((item) => String(
    item && typeof item === 'object' && !Array.isArray(item)
      ? (item as Record<string, unknown>).name
      : item,
  ).trim()).filter(Boolean));
  const columnsRaw = Array.isArray(occurrences) && occurrences.length
    ? occurrences.filter((item) => item && typeof item === 'object' && businessNames.has(String((item as Record<string, unknown>).name || '').trim()))
    : businessColumns;
  const out: One2ManyColumn[] = [];
  if (Array.isArray(columnsRaw)) {
    columnsRaw.forEach((item) => {
      if (typeof item === 'string') {
        const normalized = item.trim();
        if (!normalized) return;
        const descriptor = resolveDescriptor(normalized);
        const ttype = fieldType(descriptor) || 'char';
        const descriptorSemantics = {
          required: Boolean(descriptor?.required),
          readonly: Boolean(descriptor?.readonly),
          selection: one2manySelectionOptions(descriptor?.selection),
        };
        const businessColumn = businessColumnsByName.get(normalized);
        out.push({
          name: normalized,
          label: one2manyColumnLabel(businessColumn?.label || businessColumn?.string || descriptor?.string, normalized),
          ttype: String(businessColumn?.ttype || businessColumn?.type || ttype),
          required: businessColumn?.required === undefined ? descriptorSemantics.required : Boolean(businessColumn.required),
          readonly: businessColumn?.readonly === undefined ? descriptorSemantics.readonly : Boolean(businessColumn.readonly),
          selection: one2manySelectionOptions(businessColumn?.selection) || descriptorSemantics.selection,
        });
        return;
      }
      if (!item || typeof item !== 'object') return;
      const row = item as Record<string, unknown>;
      const colName = String(row.name || '').trim();
      if (!colName) return;
      const businessColumn = businessColumnsByName.get(colName) || {};
      const descriptor = resolveDescriptor(colName);
      const attributes = row.attributes && typeof row.attributes === 'object' && !Array.isArray(row.attributes)
        ? row.attributes as Record<string, unknown>
        : {};
      const modifiers = row.modifiers && typeof row.modifiers === 'object' && !Array.isArray(row.modifiers)
        ? row.modifiers as Record<string, unknown>
        : {};
      const relationActions = row.relation_active_actions && typeof row.relation_active_actions === 'object' && !Array.isArray(row.relation_active_actions)
        ? row.relation_active_actions as Record<string, unknown>
        : {};
      const locator = String(row.native_locator || '').trim();
      const occurrenceIndex = Number(row.occurrence_index || 0);
      const ttype = String(row.ttype || row.field_type || fieldType(descriptor) || 'char').trim() || 'char';
      const required = staticNativeBoolean(modifiers.required ?? attributes.required ?? row.required);
      const readonly = staticNativeBoolean(modifiers.readonly ?? attributes.readonly ?? row.readonly);
      const relationValueRequiresSelector = ['many2one', 'many2many', 'one2many'].includes(ttype);
      out.push({
        key: locator || `${colName}@@${occurrenceIndex || out.length + 1}`,
        name: colName,
        label: one2manyColumnLabel(
          attributes.string || row.label || row.string || businessColumn.label || businessColumn.string || descriptor?.string,
          colName,
        ),
        ttype,
        required: required ?? Boolean(descriptor?.required),
        readonly: relationValueRequiresSelector || (readonly ?? Boolean(descriptor?.readonly)),
        nativeLocator: locator || undefined,
        occurrenceIndex: occurrenceIndex > 0 ? occurrenceIndex : undefined,
        modifiers: Object.keys(modifiers).length ? modifiers : undefined,
        relationActiveActions: Object.keys(relationActions).length ? relationActions : undefined,
        selection: one2manySelectionOptions(row.selection || businessColumn.selection || descriptor?.selection),
      });
    });
  }
  return out;
}

export function resolveOne2manyRowColumnBehavior(
  column: One2ManyColumn,
  rowValues: Record<string, unknown>,
  parentValues: Record<string, unknown> = {},
  modifierPatches: Record<string, Record<string, unknown>> = {},
) {
  const runtimeModifiers = modifierPatches[column.name] && typeof modifierPatches[column.name] === 'object'
    ? modifierPatches[column.name]
    : {};
  const modifiers = { ...(column.modifiers || {}), ...runtimeModifiers };
  const evaluateModifier = (value: unknown) => evaluateNativeModifierValue(value, (field) => {
    const fieldName = String(field || '').trim();
    if (fieldName.startsWith('parent.')) return parentValues[fieldName.slice('parent.'.length)];
    return rowValues[fieldName];
  });
  const isCanonical = (value: unknown): boolean => {
    if (typeof value === 'boolean' || value === 0 || value === 1) return true;
    if (typeof value === 'string') return ['0', '1', 'false', 'False', 'true', 'True'].includes(value.trim());
    if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
    const row = value as Record<string, unknown>;
    const kind = String(row.kind || '').trim();
    if (kind === 'static') return true;
    if (kind === 'not') return isCanonical(row.expr);
    if (kind === 'all' || kind === 'any') return Array.isArray(row.exprs) && row.exprs.every(isCanonical);
    if (kind !== 'field_truthy' && kind !== 'field_compare') return false;
    const fields = [row.field, row.value_field].filter(Boolean).map((field) => String(field));
    return fields.every((field) => !field.startsWith('context.'));
  };
  const verdict = (key: 'invisible' | 'readonly' | 'required' | 'column_invisible') => {
    const value = modifiers[key];
    if (value === undefined) return false;
    if (!isCanonical(value)) return key !== 'required';
    return evaluateModifier(value);
  };
  return {
    invisible: verdict('invisible'),
    columnInvisible: verdict('column_invisible'),
    readonly: Boolean(column.readonly || verdict('readonly')),
    required: Boolean(column.required || verdict('required')),
  };
}

export function one2manyRowActionsFromSubview(subview: unknown) {
  const tree = subview && typeof subview === 'object' && !Array.isArray(subview)
    ? (subview as Record<string, unknown>).tree
    : undefined;
  const actions = tree && typeof tree === 'object' && !Array.isArray(tree)
    ? (tree as Record<string, unknown>).row_actions
    : undefined;
  if (!Array.isArray(actions)) return [];
  return actions.flatMap((item) => {
    if (!item || typeof item !== 'object' || Array.isArray(item)) return [];
    const row = item as Record<string, unknown>;
    const identity = row.native_identity && typeof row.native_identity === 'object' && !Array.isArray(row.native_identity)
      ? row.native_identity as Record<string, unknown>
      : {};
    const payload = row.payload && typeof row.payload === 'object' && !Array.isArray(row.payload)
      ? row.payload as Record<string, unknown>
      : {};
    const safety = row.action_safety && typeof row.action_safety === 'object' && !Array.isArray(row.action_safety)
      ? row.action_safety as Record<string, unknown>
      : {};
    const visible = row.visible && typeof row.visible === 'object' && !Array.isArray(row.visible)
      ? row.visible as Record<string, unknown>
      : {};
    const locator = String(identity.native_locator || '').trim();
    const methodName = String(payload.method || '').trim();
    const kind = String(row.kind || payload.type || '').trim().toLowerCase();
    if (identity.authoritative !== true || identity.canonical_region !== 'row_actions' || !locator) return [];
    const contextRaw = String(payload.context_raw || identity.context_raw || '').trim();
    const confirm = String(payload.confirm || '').trim();
    const visibleAttrs = visible.attrs && typeof visible.attrs === 'object' && !Array.isArray(visible.attrs)
      ? Object.keys(visible.attrs as Record<string, unknown>)
      : [];
    const hasConditionalVisibility = visibleAttrs.length > 0
      || (Array.isArray(visible.domain) && visible.domain.length > 0)
      || (Array.isArray(visible.states) && visible.states.length > 0);
    const enabled = kind === 'object'
      && Boolean(methodName)
      && !contextRaw
      && !confirm
      && safety.classification === 'safe'
      && safety.requires_confirm !== true
      && !hasConditionalVisibility
      && row.allowed !== false
      && row.enabled !== false
      && row.disabled !== true;
    return [{
      key: locator,
      label: String(row.label || identity.string || methodName || '操作').trim(),
      kind,
      methodName: methodName || undefined,
      enabled,
      nativeLocator: locator,
    }];
  });
}

export function one2manyCanCreateFromPolicies(policies: Record<string, unknown>) {
  return policies.can_create !== false;
}

export function one2manyCreateLabelFromPolicies(
  policies: Record<string, unknown>,
  fallbackLabel: string,
) {
  const labels = policies.ui_labels && typeof policies.ui_labels === 'object' && !Array.isArray(policies.ui_labels)
    ? policies.ui_labels as Record<string, unknown>
    : {};
  const explicit = String(labels.add_row || labels.create || '').trim();
  if (explicit && explicit !== '添加行') return explicit;
  const label = String(fallbackLabel || '').trim();
  return label ? `添加${label}` : (explicit || '添加行');
}

export function one2manyPrimaryColumnFromColumns(columns: One2ManyColumn[]) {
  return columns.length ? columns[0].name : 'name';
}

export function one2manyRowLabelFromPrimary(primary: string, row: One2ManyInlineRow) {
  const value = String(row.values?.[primary] ?? row.values?.name ?? '').trim();
  if (value) return value;
  if (row.id) return `#${row.id}`;
  return '未命名';
}

export function one2manyRowStateLabel(row: One2ManyInlineRow) {
  if (row.removed) return '待删除';
  if (row.isNew) return '新增';
  if (row.dirty) return '已修改';
  return '未变更';
}

export function one2manyDraftSummary(rows: One2ManyInlineRow[]) {
  if (!rows.length) return '';
  let created = 0;
  let updated = 0;
  let removed = 0;
  rows.forEach((row) => {
    if (row.removed) {
      removed += 1;
      return;
    }
    if (row.isNew) {
      created += 1;
      return;
    }
    if (row.dirty) updated += 1;
  });
  const parts: string[] = [];
  if (created) parts.push(`新增 ${created}`);
  if (updated) parts.push(`修改 ${updated}`);
  if (removed) parts.push(`删除 ${removed}`);
  return parts.length ? `待提交：${parts.join(' / ')}` : '待提交：无变更';
}

export function createOne2manyDraftRow(params: {
  key: string;
  primary: string;
  columns: One2ManyColumn[];
}): One2ManyInlineRow {
  const values = params.columns.reduce<Record<string, unknown>>((acc, column) => {
    acc[column.name] = column.ttype === 'boolean' ? false : '';
    return acc;
  }, {});
  return {
    key: params.key,
    id: null,
    isNew: true,
    removed: false,
    dirty: true,
    dirtyFields: Array.from(new Set(params.columns.map((column) => column.name))),
    values: { ...values, [params.primary]: values[params.primary] ?? '' },
  };
}

export function ensureOne2manyRows(
  rowsByField: Record<string, One2ManyInlineRow[]>,
  fieldName: string,
) {
  if (!Array.isArray(rowsByField[fieldName])) {
    rowsByField[fieldName] = [];
  }
  return rowsByField[fieldName];
}

export function appendOne2manyDraftRow(params: {
  rowsByField: Record<string, One2ManyInlineRow[]>;
  fieldName: string;
  key: string;
  primary: string;
  columns: One2ManyColumn[];
}) {
  const rows = ensureOne2manyRows(params.rowsByField, params.fieldName);
  rows.push(createOne2manyDraftRow({ key: params.key, primary: params.primary, columns: params.columns }));
}

export function setOne2manyDraftRowField(params: {
  rowsByField: Record<string, One2ManyInlineRow[]>;
  fieldName: string;
  rowKey: string;
  column: One2ManyColumn;
  value: unknown;
  parentValues?: Record<string, unknown>;
}) {
  const rows = ensureOne2manyRows(params.rowsByField, params.fieldName);
  const row = rows.find((item) => item.key === params.rowKey);
  if (!row) return false;
  const behavior = resolveOne2manyRowColumnBehavior(
    params.column, row.values || {}, params.parentValues || {}, row.modifierPatches || {},
  );
  if (behavior.invisible || behavior.columnInvisible || behavior.readonly) return false;
  const normalized = normalizeOne2manyColumnValue(params.column, params.value);
  row.values = {
    ...(row.values || {}),
    [params.column.name]: normalized,
  };
  row.dirty = true;
  if (!row.dirtyFields.includes(params.column.name)) {
    row.dirtyFields = [...row.dirtyFields, params.column.name];
  }
  return true;
}

export function removeOne2manyDraftRow(rowsByField: Record<string, One2ManyInlineRow[]>, fieldName: string, rowKey: string) {
  const rows = ensureOne2manyRows(rowsByField, fieldName);
  const index = rows.findIndex((item) => item.key === rowKey);
  if (index < 0) return false;
  const row = rows[index];
  if (row.isNew) {
    rows.splice(index, 1);
  } else {
    row.removed = true;
    row.dirty = true;
  }
  return true;
}

export function restoreOne2manyDraftRow(rowsByField: Record<string, One2ManyInlineRow[]>, fieldName: string, rowKey: string) {
  const rows = ensureOne2manyRows(rowsByField, fieldName);
  const row = rows.find((item) => item.key === rowKey);
  if (!row) return false;
  row.removed = false;
  row.dirty = true;
  return true;
}

export function mergeOne2manyHydratedRecords(params: {
  rows: One2ManyInlineRow[];
  columns: One2ManyColumn[];
  records: Array<Record<string, unknown>>;
}) {
  const byId = new Map<number, Record<string, unknown>>();
  params.records.forEach((record) => {
    const id = Number(record.id);
    if (Number.isFinite(id) && id > 0) byId.set(Math.trunc(id), record);
  });
  params.rows.forEach((row) => {
    if (!row.id || row.dirty) return;
    const record = byId.get(Number(row.id));
    if (!record) return;
    row.values = params.columns.reduce<Record<string, unknown>>((acc, column) => {
      acc[column.name] = record[column.name] ?? '';
      return acc;
    }, {
      id: record.id,
      display_name: record.display_name,
      name: record.name ?? record.display_name ?? row.values?.name ?? `#${row.id}`,
    });
  });
}

export function initOne2manyRowsFromRelationSource(params: {
  source: unknown;
  relationOptions: Array<{ id: number; label: string }>;
  primary: string;
}): One2ManyInlineRow[] {
  const ids = normalizeRelationIds(params.source);
  const optionMap = new Map(params.relationOptions.map((item) => [item.id, item.label]));
  return ids.map((id) => ({
    key: `o2m_id_${id}`,
    id,
    isNew: false,
    removed: false,
    dirty: false,
    dirtyFields: [],
    values: {
      [params.primary]: optionMap.get(id) || `#${id}`,
      name: optionMap.get(id) || `#${id}`,
    },
  }));
}

export function collectOne2manyDraftValidationFromRows(params: {
  rowsByField: Record<string, One2ManyInlineRow[]>;
  recordId: number;
  resolvePrimaryColumn: (fieldName: string) => string;
  resolveColumns: (fieldName: string) => One2ManyColumn[];
  parentValues?: Record<string, unknown>;
}) {
  const issues: string[] = [];
  const rowErrors: Record<string, string[]> = {};
  Object.entries(params.rowsByField).forEach(([fieldName, rows]) => {
    if (!Array.isArray(rows) || !rows.length) return;
    const hasTouchedRows = rows.some((row) => row.isNew || row.dirty || row.removed);
    if (params.recordId && !hasTouchedRows) return;
    const primary = params.resolvePrimaryColumn(fieldName);
    const columns = params.resolveColumns(fieldName);
    const labels = new Set<string>();
    rows.forEach((row, index) => {
      if (row.removed) return;
      const rowKey = `${fieldName}:${row.key}`;
      const perRow: string[] = [];
      const checkedRequiredFields = new Set<string>();
      columns.forEach((column) => {
        const behavior = resolveOne2manyRowColumnBehavior(
          column, row.values || {}, params.parentValues || {}, row.modifierPatches || {},
        );
        if (!behavior.required || behavior.invisible || behavior.columnInvisible || checkedRequiredFields.has(column.name)) return;
        checkedRequiredFields.add(column.name);
        const value = row.values?.[column.name];
        if (isOne2manyEmptyValue(column, value)) {
          perRow.push(`${column.label}不能为空`);
          issues.push(`${fieldName} 第${index + 1}行${column.label}不能为空`);
        }
      });
      const label = String(row.values?.[primary] ?? row.values?.name ?? '').trim();
      if (label) {
        const key = label.toLowerCase();
        if (labels.has(key)) {
          perRow.push(`主值重复：${label}`);
          issues.push(`${fieldName} 存在重复行值：${label}`);
        } else {
          labels.add(key);
        }
      }
      if (perRow.length) {
        rowErrors[rowKey] = perRow;
      }
    });
  });
  return { issues, rowErrors };
}

export function buildOne2manyCommandValue(
  original: unknown,
  rows: One2ManyInlineRow[],
  mode: 'onchange' | 'write',
) {
  return buildOne2ManyInlineCommands({
    original,
    draftRows: rows.map((row) => ({
      id: row.id,
      isNew: row.isNew,
      removed: row.removed,
      dirty: row.dirty,
      values: row.isNew
        ? row.values || {}
        : Object.fromEntries((row.dirtyFields || []).map((key) => [key, row.values?.[key]])),
    })),
    mode,
  });
}

export function normalizeOne2manyColumnValue(column: One2ManyColumn, value: unknown) {
  const ttype = String(column.ttype || '').trim().toLowerCase();
  if (ttype === 'boolean') return Boolean(value);
  if (ttype === 'integer') {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? Math.trunc(parsed) : false;
  }
  if (ttype === 'float' || ttype === 'monetary') {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : false;
  }
  if (ttype === 'date') return toDateInputValue(value) || false;
  if (ttype === 'datetime') return fromDatetimeInputValue(value);
  if (ttype === 'selection') return String(value ?? '').trim() || false;
  return String(value ?? '');
}

export function one2manyColumnInputType(column: One2ManyColumn) {
  const ttype = String(column.ttype || '').trim().toLowerCase();
  if (ttype === 'integer' || ttype === 'float' || ttype === 'monetary') return 'number';
  if (ttype === 'date') return 'date';
  if (ttype === 'datetime') return 'datetime-local';
  return 'text';
}

export function one2manyColumnDisplayValue(column: One2ManyColumn, value: unknown) {
  const ttype = String(column.ttype || '').trim().toLowerCase();
  if (value === false || value === null || value === undefined) return '';
  if (ttype === 'date') return toDateInputValue(value);
  if (ttype === 'datetime') return toDatetimeInputValue(value);
  if (ttype === 'selection') {
    const option = (column.selection || []).find(([key]) => String(key) === String(value));
    if (option) return String(option[1]);
  }
  return String(value ?? '');
}

export function isOne2manyEmptyValue(column: One2ManyColumn, value: unknown) {
  const ttype = String(column.ttype || '').trim().toLowerCase();
  if (ttype === 'boolean') return value === false || value === null || value === undefined;
  if (ttype === 'integer' || ttype === 'float' || ttype === 'monetary') {
    return value === false || value === null || value === undefined || Number.isNaN(Number(value));
  }
  if (ttype === 'date' || ttype === 'datetime' || ttype === 'selection') {
    return !String(value ?? '').trim() || value === false;
  }
  return !String(value ?? '').trim();
}

export function formRuntimeReasonLabel(reason: unknown): string {
  const raw = String(reason || '').trim();
  const key = raw.toUpperCase();
  const mapping: Record<string, string> = {
    ACTION_UNSUPPORTED: '当前操作暂不可用',
    BUSINESS_RULE_FAILED: '业务规则限制',
    CONFLICT: '数据已变化',
    FIELD_CREATE_DISABLED: '当前字段暂不支持新增',
    INLINE_CREATE_READY: '可在明细中新增',
    MISSING_PARAMS: '参数不完整',
    NETWORK_ERROR: '网络连接问题',
    NOT_FOUND: '记录不存在',
    PERMISSION_DENIED: '权限不足',
    RELATION_CREATE_FORBIDDEN: '关联数据暂不允许新增',
    RELATION_READ_FORBIDDEN: '关联数据暂不可查看',
    SYSTEM_ERROR: '系统处理问题',
    VALIDATION_ERROR: '校验未通过',
    WRITE_FAILED: '保存失败',
  };
  if (!raw) return '待确认';
  return mapping[key] || raw.replace(/[_-]+/g, ' ').toLowerCase().replace(/(^|\s)\S/g, (s) => s.toUpperCase());
}

export function formRuntimeRowStateLabel(state: unknown): string {
  const raw = String(state || '').trim().toLowerCase();
  const mapping: Record<string, string> = {
    create: '新增明细',
    update: '已更新明细',
    remove: '已移除明细',
    keep: '保持当前明细',
  };
  return mapping[raw] || '已同步明细变化';
}

export function formRuntimeCommandHintLabel(commands: unknown[]): string {
  const values = commands.map((item) => Number(item)).filter((item) => Number.isFinite(item));
  if (!values.length) return '请检查明细变化';
  const labels = values.map((item) => {
    if (item === 0) return '新增';
    if (item === 1) return '更新';
    if (item === 2) return '删除';
    if (item === 3) return '解除关联';
    if (item === 4) return '关联已有';
    if (item === 5) return '清空';
    if (item === 6) return '替换为指定明细';
    return '同步明细';
  });
  return Array.from(new Set(labels)).join('、');
}

export function one2manyRowHintsFromPatches(params: {
  patches: Array<Record<string, unknown>>;
  fieldName: string;
  row: One2ManyInlineRow;
}) {
  const messages: string[] = [];
  params.patches.forEach((patch) => {
    if (String(patch.field || '') !== params.fieldName) return;
    const rowKey = String(patch.row_key || '').trim();
    const rowId = Number(patch.row_id || 0);
    const matched = (rowKey && rowKey === params.row.key) || (rowId > 0 && Number(params.row.id || 0) === rowId);
    if (!matched) return;
    const warns = Array.isArray(patch.warnings) ? patch.warnings : [];
    warns.forEach((warn) => {
      const item = warn && typeof warn === 'object' && !Array.isArray(warn)
        ? warn as Record<string, unknown>
        : {};
      const message = String(item.message || item.title || '').trim();
      if (message) messages.push(message);
      const reasonCode = String(item.reason_code || '').trim();
      if (reasonCode) messages.push(`处理原因：${formRuntimeReasonLabel(reasonCode)}`);
    });
    const rowState = String(patch.row_state || '').trim().toLowerCase();
    if (rowState) messages.push(`处理结果：${formRuntimeRowStateLabel(rowState)}`);
    if (Array.isArray(patch.command_hint) && patch.command_hint.length) {
      messages.push(`处理建议：${formRuntimeCommandHintLabel(patch.command_hint)}`);
    }
  });
  return Array.from(new Set(messages));
}
