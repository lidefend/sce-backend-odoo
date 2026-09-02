import { computed, type Ref } from 'vue';
import { uniqueFields } from '../runtime/actionViewRequestRuntime';
import {
  collectContractV2FieldStatusByCode,
  resolveContractV2FieldDescriptorMap,
  resolveContractV2FieldWidgets,
  resolveContractV2ListProfile,
  resolveContractV2PrimaryDataSource,
  resolveContractV2SearchContract,
  resolveContractV2SurfacePolicies,
} from '../contracts/v2/store';
import type { ContractV2NormalizedStore } from '../contracts/v2/types';

type Dict = Record<string, unknown>;

type UseActionViewContractShapeRuntimeOptions = {
  pageText: (key: string, fallback: string) => string;
  actionContract: Ref<ContractV2NormalizedStore | null>;
  advancedFields: Ref<string[]>;
  activeGroupByField: Ref<string>;
};

type KanbanProfile = {
  titleField: string;
  primaryFields: string[];
  secondaryFields: string[];
  statusFields: string[];
  metricFields: string[];
  quickActionCount: number;
};

type SortOption = {
  label: string;
  value: string;
};

type ListColumnOption = {
  name: string;
  label: string;
  optional: string;
  defaultVisible: boolean;
  sortable?: boolean;
  type?: string;
  widget?: string;
  cellRole?: string;
  mutation?: Record<string, unknown>;
  selection?: Array<{ value: string; label: string }>;
  toneByValue?: Record<string, string>;
  displayField?: string;
  valueField?: string;
  aggregationField?: string;
  dataType?: string;
  currencyField?: string;
  aggregate?: string;
  sortField?: string;
  filterField?: string;
  exportField?: string;
};

function normalizeFieldNames(rows: unknown): string[] {
  if (!Array.isArray(rows)) return [];
  return rows
    .map((item) => {
      if (typeof item === 'string' || typeof item === 'number') return String(item || '').trim();
      const row = (item || {}) as Dict;
      const direct = row.name || row.field_name || row.field_code || row.fieldCode;
      if (typeof direct === 'string' || typeof direct === 'number') return String(direct || '').trim();
      const nested = row.field;
      if (typeof nested === 'string' || typeof nested === 'number') return String(nested || '').trim();
      if (nested && typeof nested === 'object' && !Array.isArray(nested)) {
        const field = nested as Dict;
        return String(field.name || field.field_name || field.field_code || field.fieldCode || '').trim();
      }
      return '';
    })
    .filter((name) => /^[A-Za-z_][A-Za-z0-9_]*$/.test(name));
}

export function extractKanbanFieldsFromContract(store: ContractV2NormalizedStore | null): string[] {
  if (String(store?.snapshot.pageInfo.viewType || '').trim() === 'kanban') {
    return uniqueFields(
      resolveContractV2FieldWidgets(store)
        .map((widget) => String(widget.fieldCode || '').trim())
        .filter((name) => /^[A-Za-z_][A-Za-z0-9_]*$/.test(name)),
    );
  }
  return [];
}

export function extractAdvancedViewFieldsFromContract(store: ContractV2NormalizedStore | null): string[] {
  return uniqueFields(resolveContractV2FieldWidgets(store).map((widget) => widget.fieldCode).filter(Boolean));
}

export function extractViewFieldLabelsFromContract(store: ContractV2NormalizedStore | null): Record<string, string> {
  const labels: Record<string, string> = {};
  resolveContractV2FieldWidgets(store).forEach((widget) => {
    if (widget.fieldCode && widget.label) labels[widget.fieldCode] = widget.label;
  });
  return labels;
}

export function extractListFieldSemanticsFromContract(store: ContractV2NormalizedStore | null): Dict[] {
  const schemas: Dict[] = [];
  resolveContractV2FieldWidgets(store).forEach((widget) => {
    const config = (widget.componentConfig || {}) as Dict;
    const fieldCode = String(
      widget.fieldCode
      || config.display_field
      || config.name
      || '',
    ).trim();
    if (!fieldCode) return;
    schemas.push({
      ...config,
      name: fieldCode,
      type: config.data_type || config.fieldType || widget.fieldDescriptor?.fieldType,
    });
  });

  const normalized = schemas
    .map((row) => {
      const displayField = String(row.display_field || row.name || '').trim();
      const valueField = String(row.value_field || row.name || '').trim();
      if (!displayField || !valueField) return null;
      const aggregate = String(row.aggregate || (row.sum ? 'sum' : 'none')).trim();
      return {
        display_field: displayField,
        value_field: valueField,
        aggregation_field: String(row.aggregation_field || (aggregate === 'sum' ? valueField : '')).trim(),
        data_type: String(row.data_type || row.type || '').trim(),
        widget: String(row.widget || '').trim(),
        currency_field: String(row.currency_field || '').trim(),
        precision: row.precision,
        aggregate,
        sort_field: String(row.sort_field || valueField).trim(),
        filter_field: String(row.filter_field || valueField).trim(),
        export_field: String(row.export_field || valueField).trim(),
      };
    })
    .filter(Boolean) as Dict[];
  return Array.from(
    normalized.reduce<Map<string, Dict>>((rows, row) => {
      rows.set(String(row.display_field || ''), row);
      return rows;
    }, new Map()).values(),
  );
}

export function useActionViewContractShapeRuntime(options: UseActionViewContractShapeRuntimeOptions) {
  const contractColumnLabels = computed<Record<string, string>>(() => {
    const store = options.actionContract.value;
    const labels = Object.values(resolveContractV2FieldDescriptorMap(store)).reduce<Record<string, string>>((acc, row) => {
      if (row.fieldCode && row.label) acc[row.fieldCode] = row.label;
      return acc;
    }, {});
    const listProfile = resolveContractV2ListProfile(store);
    Object.entries((listProfile.column_labels || {}) as Dict).forEach(([name, labelRaw]) => {
      const label = String(labelRaw || '').trim();
      if (label) labels[name] = label;
    });
    return labels;
  });

  function extractColumnsFromContract(contract: unknown, sceneColumns: string[] = []) {
    if (Array.isArray(sceneColumns) && sceneColumns.length) {
      return sceneColumns;
    }
    const store = contract as ContractV2NormalizedStore | null;
    const profile = resolveContractV2ListProfile(store);
    const columns = Array.isArray(profile.columns)
      ? profile.columns.map((item) => String(item || '').trim()).filter(Boolean)
      : [];
    return columns.length ? columns : resolveContractV2FieldWidgets(store).map((widget) => widget.fieldCode).filter(Boolean);
  }

  function extractColumnSchemaFromContract(contract: unknown): Dict[] {
    const store = contract as ContractV2NormalizedStore | null;
    return resolveContractV2FieldWidgets(store).map((widget) => ({
      name: widget.fieldCode,
      label: widget.label,
      string: widget.label,
      widget: widget.widgetType,
      componentKey: widget.componentKey,
      ...(widget.componentConfig || {}),
    }));
  }

  function resolveListColumnOptions(contract: unknown, profile: { columns?: string[]; hidden_columns?: string[]; column_labels?: Record<string, string> } | null): ListColumnOption[] {
    const store = contract as ContractV2NormalizedStore | null;
    const fieldsMap = resolveContractV2FieldDescriptorMap(store);
    const preferred = Array.isArray(profile?.columns) ? profile?.columns || [] : [];
    const hidden = new Set(Array.isArray(profile?.hidden_columns) ? profile?.hidden_columns || [] : []);
    const v2FieldStatus = collectContractV2FieldStatusByCode(store);
    const schemaRows = extractColumnSchemaFromContract(contract);
    const schemaByName = schemaRows.reduce<Record<string, Dict>>((acc, row) => {
      const name = String(row.name || '').trim();
      if (name && !acc[name]) acc[name] = row;
      return acc;
    }, {});
    const baseColumns = preferred.length ? preferred : extractColumnsFromContract(contract, []);
    const labels = {
      ...contractColumnLabels.value,
      ...((profile?.column_labels || {}) as Record<string, string>),
    };
    return uniqueFields([...baseColumns, ...Array.from(hidden)])
      .map((name) => {
        const schema = schemaByName[name] || {};
        const field = fieldsMap[name];
        const status = v2FieldStatus[name];
        const optional = String(schema.optional || '').trim();
        const invisible = schema.invisible === true || schema.column_invisible === true || status?.visible === false;
        const sortableRaw = Object.prototype.hasOwnProperty.call(schema, 'sortable')
          ? schema.sortable
          : undefined;
        const type = String(schema.type || field?.fieldType || '').trim();
        const widget = String(schema.widget || field?.widgetType || field?.fieldType || '').trim();
        const valueField = String(schema.value_field || name).trim() || name;
        const aggregate = String(schema.aggregate || (schema.sum ? 'sum' : '')).trim();
        const rawSelection = Array.isArray(schema.selection) ? schema.selection : field?.selection;
        return {
          name,
          label: String(labels[name] || schema.label || schema.string || field?.label || name).trim() || name,
          optional,
          defaultVisible: !hidden.has(name) && optional !== 'hide' && !invisible,
          sortable: sortableRaw === false ? false : undefined,
          type: type || undefined,
          widget: widget || undefined,
          cellRole: String(schema.cell_role || schema.cellRole || '').trim() || undefined,
          mutation: schema.mutation && typeof schema.mutation === 'object'
            ? schema.mutation as Record<string, unknown>
            : undefined,
          selection: Array.isArray(rawSelection)
            ? rawSelection
                .map((item) => {
                  if (Array.isArray(item)) {
                    return {
                      value: String(item[0] ?? '').trim(),
                      label: String(item[1] ?? '').trim(),
                    };
                  }
                  const row = (item || {}) as Dict;
                  return { value: String(row.value ?? '').trim(), label: String(row.label ?? '').trim() };
                })
                .filter((item) => item.value && item.label)
            : undefined,
          toneByValue: typeof schema.tone_by_value === 'object' && schema.tone_by_value
            ? Object.entries(schema.tone_by_value as Dict).reduce<Record<string, string>>((acc, [value, tone]) => {
                const key = String(value || '').trim();
                const normalizedTone = String(tone || '').trim();
                if (key && normalizedTone) acc[key] = normalizedTone;
                return acc;
              }, {})
            : undefined,
          displayField: String(schema.display_field || name).trim() || name,
          valueField,
          aggregationField: String(schema.aggregation_field || (aggregate === 'sum' ? valueField : '')).trim() || undefined,
          dataType: String(schema.data_type || type || '').trim() || undefined,
          currencyField: String(schema.currency_field || '').trim() || undefined,
          aggregate: aggregate || 'none',
          sortField: String(schema.sort_field || valueField).trim() || undefined,
          filterField: String(schema.filter_field || valueField).trim() || undefined,
          exportField: String(schema.export_field || valueField).trim() || undefined,
        };
      });
  }

  function convergeColumnsForSurface(rawColumns: string[]) {
    const normalized = rawColumns.filter(Boolean);
    if (!normalized.length) return normalized;
    return normalized;
  }

  function extractKanbanFields(contract: ContractV2NormalizedStore | null) {
    return extractKanbanFieldsFromContract(contract);
  }

  function extractKanbanProfile(contract: unknown): KanbanProfile {
    const profile = (resolveContractV2ListProfile(contract as ContractV2NormalizedStore | null).kanban_profile || {}) as Dict;
    const normalize = (rows: unknown) => normalizeFieldNames(rows);
    return {
      titleField: String(profile.title_field || '').trim(),
      primaryFields: normalize(profile.primary_fields),
      secondaryFields: normalize(profile.secondary_fields),
      statusFields: normalize(profile.status_fields),
      metricFields: normalize(profile.metric_fields),
      quickActionCount: Number(profile.quick_action_count || 0),
    };
  }

  function extractListOrderFromContract(contract: unknown): string {
    const store = contract as ContractV2NormalizedStore | null;
    const primary = resolveContractV2PrimaryDataSource(store);
    const params = (primary.params || {}) as Dict;
    const search = resolveContractV2SearchContract(store);
    const searchDefaults = (search.defaults || {}) as Dict;
    const candidates = [
      params.order,
      searchDefaults?.order,
      search.default_order,
    ];
    for (const item of candidates) {
      const value = String(item || '').trim();
      if (value) return value;
    }
    return '';
  }

  function buildListSortOptions(contract: unknown, currentSort: string, fallbackLabel: string): SortOption[] {
    const rows: SortOption[] = [];
    const add = (valueRaw: unknown, labelRaw?: unknown) => {
      const value = String(valueRaw || '').trim();
      if (!value || rows.some((item) => item.value === value)) return;
      const label = String(labelRaw || value || fallbackLabel).trim() || fallbackLabel;
      rows.push({ label, value });
    };
    const search = resolveContractV2SearchContract(contract as ContractV2NormalizedStore | null);
    const sortOptions = search.sort_options;
    if (Array.isArray(sortOptions)) {
      sortOptions.forEach((row) => {
        const raw = row as Dict;
        add(raw.value || raw.order, raw.label);
      });
    }
    add(extractListOrderFromContract(contract), fallbackLabel);
    add(currentSort, fallbackLabel);
    return rows;
  }

  function extractAdvancedViewFields(contract: unknown, mode: string) {
    void mode;
    return extractAdvancedViewFieldsFromContract(contract as ContractV2NormalizedStore | null);
  }

  function extractViewFieldLabels(contract: unknown, mode: string) {
    void mode;
    return extractViewFieldLabelsFromContract(contract as ContractV2NormalizedStore | null);
  }

  function advancedRowTitle(row: Record<string, unknown>) {
    return String(row.display_name || row.name || row.id || options.pageText('advanced_row_title_fallback', '记录')).trim();
  }

  function advancedFieldLabel(field: string) {
    return String(contractColumnLabels.value[field] || field).trim();
  }

  function advancedRowMeta(row: Record<string, unknown>) {
    const preferredKeys = options.advancedFields.value.length
      ? options.advancedFields.value
      : Object.keys(row);
    const entries = preferredKeys
      .filter((key) => key !== 'id' && key !== 'name' && key !== 'display_name' && key in row)
      .slice(0, 3)
      .map((key) => `${advancedFieldLabel(key)}: ${String(row[key] ?? '-')}`);
    if (!entries.length) return options.pageText('advanced_row_meta_empty', '无附加字段');
    return entries.join(' · ');
  }

  function buildGroupKey(field: unknown, value: unknown, fallback: unknown) {
    const fieldPart = String(field || options.activeGroupByField.value || 'group').trim() || 'group';
    const valuePart = typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean'
      ? String(value)
      : JSON.stringify(value ?? fallback);
    return `${fieldPart}:${valuePart}`;
  }

  function resolveModelFromContract(contract: unknown) {
    return String((contract as ContractV2NormalizedStore | null)?.snapshot.pageInfo.model || '').trim();
  }

  function extractListProfile(contract: unknown) {
    const store = contract as ContractV2NormalizedStore | null;
    const rawProfile = resolveContractV2ListProfile(store);
    const surfacePolicies = resolveContractV2SurfacePolicies(store);
    const columns = Array.isArray(rawProfile.columns)
      ? rawProfile.columns.map((item) => String(item || '').trim()).filter(Boolean)
      : [];
    const hiddenColumns = Array.isArray(rawProfile.hidden_columns)
      ? rawProfile.hidden_columns.map((item) => String(item || '').trim()).filter(Boolean)
      : [];
    const factColumns = Array.isArray(rawProfile.fact_columns)
      ? rawProfile.fact_columns.map((item) => String(item || '').trim()).filter(Boolean)
      : [];
    const crossDeviceCriticalColumns = Array.isArray(rawProfile.cross_device_critical_columns)
      ? rawProfile.cross_device_critical_columns
          .map((item) => String(item || '').trim())
          .filter(Boolean)
      : [];
    const columnLabels: Record<string, string> = {};
    Object.entries((rawProfile.column_labels || {}) as Dict).forEach(([name, labelRaw]) => {
      const label = String(labelRaw || '').trim();
      if (label) columnLabels[name] = label;
    });
    const rowPrimary = String(rawProfile.row_primary || '').trim();
    const rowSecondary = String(rawProfile.row_secondary || '').trim();
    const showRowNumber = rawProfile.show_row_number !== false;
    const statusField = String(rawProfile.status_field || '').trim();
    const metricFields = Array.isArray(rawProfile.metric_fields)
      ? (rawProfile.metric_fields as unknown[])
          .map((item) => String(item || '').trim())
          .filter(Boolean)
      : [];
    const rawBatchPolicy = (rawProfile.batch_policy || {}) as Dict;
    const hasRawBatchPolicy = Object.keys(rawBatchPolicy).length > 0;
    const batchPolicy = {
      enabled: rawBatchPolicy.enabled === true,
      active_field: String(rawBatchPolicy.active_field || '').trim() || undefined,
      assignee_field: String(rawBatchPolicy.assignee_field || '').trim() || undefined,
      archive_value: typeof rawBatchPolicy.archive_value === 'boolean' ? rawBatchPolicy.archive_value : null,
      activate_value: typeof rawBatchPolicy.activate_value === 'boolean' ? rawBatchPolicy.activate_value : null,
      assignee_options: rawBatchPolicy.assignee_options && typeof rawBatchPolicy.assignee_options === 'object'
        ? rawBatchPolicy.assignee_options as Dict
        : null,
      delete_mode: String(rawBatchPolicy.delete_mode || '').trim() || undefined,
      available_actions: Array.isArray(rawBatchPolicy.available_actions)
        ? rawBatchPolicy.available_actions.map((item) => String(item || '').trim()).filter(Boolean)
        : undefined,
      execution_intents: Object.fromEntries(Object.entries((rawBatchPolicy.execution_intents || {}) as Dict)
        .map(([action, intent]) => [action, String(intent || '').trim()]).filter(([, intent]) => Boolean(intent))),
      execution_operations: Object.fromEntries(Object.entries((rawBatchPolicy.execution_operations || {}) as Dict)
        .map(([action, operation]) => [action, String(operation || '').trim()]).filter(([, operation]) => Boolean(operation))),
    };
    const rawSelectionPolicy = (rawProfile.selection_policy || surfacePolicies.selection_policy || {}) as Dict;
    const selectionPolicy = {
      enabled: rawSelectionPolicy.enabled !== false,
      mode: String(rawSelectionPolicy.mode || 'multiple').trim(),
      scope: String(rawSelectionPolicy.scope || 'current_page').trim(),
      requires_batch_action: rawSelectionPolicy.requires_batch_action === true,
      action_source: String(rawSelectionPolicy.action_source || 'batch_policy.available_actions').trim(),
    };
    const rawGrouping = (rawProfile.grouping || {}) as Dict;
    const rawGroupingSort = (rawGrouping.sort || {}) as Dict;
    const grouping = {
      sample_limits: Array.isArray(rawGrouping.sample_limits)
        ? rawGrouping.sample_limits
            .map((item) => Number(item))
            .filter((item) => Number.isFinite(item) && item > 0)
            .map((item) => Math.trunc(item))
        : undefined,
      default_sample_limit: Number.isFinite(Number(rawGrouping.default_sample_limit))
        ? Math.trunc(Number(rawGrouping.default_sample_limit))
        : undefined,
      sort: {
        key: String(rawGroupingSort.key || '').trim() || undefined,
        default_direction: String(rawGroupingSort.default_direction || '').trim() || undefined,
        directions: Array.isArray(rawGroupingSort.directions)
          ? rawGroupingSort.directions.map((item) => String(item || '').trim()).filter(Boolean)
          : undefined,
      },
    };
    const rawPreferencePolicy = (rawProfile.preference_policy || {}) as Dict;
    const preferencePolicy = {
      scope: String(rawPreferencePolicy.scope || '').trim() || undefined,
      allow_visibility: rawPreferencePolicy.allow_visibility !== false,
      allow_order: rawPreferencePolicy.allow_order !== false,
      allow_width: rawPreferencePolicy.allow_width !== false,
      locked_columns: Array.isArray(rawPreferencePolicy.locked_columns)
        ? rawPreferencePolicy.locked_columns.map((item) => String(item || '').trim()).filter(Boolean)
        : [],
      must_request_columns: Array.isArray(rawPreferencePolicy.must_request_columns)
        ? rawPreferencePolicy.must_request_columns.map((item) => String(item || '').trim()).filter(Boolean)
        : [],
    };
    if (!columns.length && !crossDeviceCriticalColumns.length && !Object.keys(columnLabels).length && !rowPrimary && !rowSecondary && !statusField && !metricFields.length && !Object.keys(rawBatchPolicy).length && !Object.keys(rawGrouping).length) {
      return null;
    }
    return {
      columns,
      fact_columns: factColumns,
      cross_device_critical_columns: crossDeviceCriticalColumns,
      hidden_columns: hiddenColumns,
      column_labels: columnLabels,
      preference_policy: preferencePolicy,
      row_primary: rowPrimary,
      row_secondary: rowSecondary,
      show_row_number: showRowNumber,
      status_field: statusField,
      metric_fields: metricFields,
      selection_policy: selectionPolicy,
      ...(hasRawBatchPolicy ? { batch_policy: batchPolicy } : {}),
      grouping,
    };
  }

  return {
    contractColumnLabels,
    extractListProfile,
    resolveListColumnOptions,
    extractColumnsFromContract,
    extractListOrderFromContract,
    buildListSortOptions,
    convergeColumnsForSurface,
    extractKanbanFields,
    extractKanbanProfile,
    extractAdvancedViewFields,
    extractViewFieldLabels,
    advancedRowTitle,
    advancedFieldLabel,
    advancedRowMeta,
    buildGroupKey,
    resolveModelFromContract,
  };
}
