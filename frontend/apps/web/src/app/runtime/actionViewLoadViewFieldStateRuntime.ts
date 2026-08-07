type KanbanProfile = {
  titleField: string;
  primaryFields: string[];
  secondaryFields: string[];
  statusFields: string[];
  metricFields: string[];
  quickActionCount: number;
};

type ListProfileLike = {
  columns?: string[];
};

function normalizeRuntimeFieldName(raw: unknown): string {
  if (typeof raw === 'string' || typeof raw === 'number') {
    const text = String(raw || '').trim();
    if (/^[A-Za-z_][A-Za-z0-9_]*$/.test(text)) return text;
    return text.match(/(?:^|[,{])\s*name\s*[:.]\s*\.?([A-Za-z_][A-Za-z0-9_]*)/i)?.[1] || '';
  }
  const row = raw && typeof raw === 'object' && !Array.isArray(raw) ? raw as Record<string, unknown> : {};
  for (const candidate of [row.name, row.field_name, row.field_code, row.fieldCode, row.field]) {
    const name = candidate === raw ? '' : normalizeRuntimeFieldName(candidate);
    if (name) return name;
  }
  return '';
}

function normalizeRuntimeFieldNames(rows: unknown[]): string[] {
  return rows.map(normalizeRuntimeFieldName).filter(Boolean);
}

export function resolveLoadKanbanFieldApplyState(options: {
  kanbanContractFields: string[];
  fallbackKanbanFields: string[];
  kanbanProfile: KanbanProfile;
  advancedContractFields: string[];
  uniqueFieldsFn: (fields: string[]) => string[];
}): {
  advancedFields: string[];
  kanbanFields: string[];
  kanbanTitleFieldHint: string;
  kanbanPrimaryFields: string[];
  kanbanSecondaryFields: string[];
  kanbanStatusFields: string[];
  kanbanMetricFields: string[];
  kanbanQuickActionCount: number;
} {
  const contractFields = normalizeRuntimeFieldNames(options.kanbanContractFields);
  const fallbackFields = normalizeRuntimeFieldNames(options.fallbackKanbanFields);
  const effectiveKanbanFields = contractFields.length
    ? options.uniqueFieldsFn(contractFields)
    : options.uniqueFieldsFn([...fallbackFields, 'id', 'name']);
  const normalizeProfile = (rows: string[]) => normalizeRuntimeFieldNames(rows);
  return {
    advancedFields: options.advancedContractFields,
    kanbanFields: effectiveKanbanFields,
    kanbanTitleFieldHint: options.kanbanProfile.titleField,
    kanbanPrimaryFields: options.uniqueFieldsFn(
      normalizeProfile(options.kanbanProfile.primaryFields).filter((name) => effectiveKanbanFields.includes(name)),
    ),
    kanbanSecondaryFields: options.uniqueFieldsFn(
      normalizeProfile(options.kanbanProfile.secondaryFields).filter((name) => effectiveKanbanFields.includes(name)),
    ),
    kanbanStatusFields: options.uniqueFieldsFn(
      normalizeProfile(options.kanbanProfile.statusFields).filter((name) => effectiveKanbanFields.includes(name)),
    ),
    kanbanMetricFields: options.uniqueFieldsFn(
      normalizeProfile(options.kanbanProfile.metricFields).filter((name) => effectiveKanbanFields.includes(name)),
    ),
    kanbanQuickActionCount: Number(options.kanbanProfile.quickActionCount || 0),
  };
}

export function resolveLoadRequestedFieldsApplyState(options: {
  viewMode: string;
  kanbanFields: string[];
  contractColumns: string[];
  listProfile: ListProfileLike;
  advancedFields: string[];
  resolveRequestedFieldsFn: (columns: string[], listProfile: ListProfileLike) => string[];
}): {
  requestedFields: string[];
} {
  if (options.viewMode === 'kanban') {
    return { requestedFields: options.kanbanFields };
  }
  if (options.viewMode === 'tree') {
    return {
      requestedFields: options.resolveRequestedFieldsFn(options.contractColumns, options.listProfile),
    };
  }
  return { requestedFields: options.advancedFields };
}

export function resolveLoadMissingColumnsApplyState(options: {
  missingColumnsState: { message: string; recordsLength: number } | null;
  currentErrorMessage: string;
}): {
  shouldBlock: boolean;
  message: string;
  statusInput: { error: string; recordsLength: number };
} {
  if (!options.missingColumnsState) {
    return {
      shouldBlock: false,
      message: '',
      statusInput: {
        error: options.currentErrorMessage,
        recordsLength: 0,
      },
    };
  }
  return {
    shouldBlock: true,
    message: options.missingColumnsState.message,
    statusInput: {
      error: options.currentErrorMessage,
      recordsLength: options.missingColumnsState.recordsLength,
    },
  };
}
