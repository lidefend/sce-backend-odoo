import type { RelationOption } from './types';

type InternalRelationContextSwitchParams = {
  fieldName: string;
  formData: Record<string, unknown>;
  relationKeywords: Record<string, string>;
  previousValue: unknown;
  previousKeyword: string;
  replaceRoute: () => Promise<unknown>;
  contextApplied: () => boolean;
  reload: () => Promise<void>;
};

type RelationSelectionContextSwitchParams = {
  switchContext: () => Promise<boolean>;
  finalizeUnswitchedSelection: () => void;
  reportError: (error: unknown) => void;
};

type RelationSwitchEntry = {
  switchContext?: {
    enabled: boolean;
    defaultClearFields: string[];
  };
} | null;

export async function applyInternalRelationContextSwitch(
  params: InternalRelationContextSwitchParams,
): Promise<boolean> {
  const selectedValue = params.formData[params.fieldName];
  const selectedKeyword = params.relationKeywords[params.fieldName] || '';
  params.formData[params.fieldName] = params.previousValue;
  params.relationKeywords[params.fieldName] = params.previousKeyword;
  let applied = false;
  try {
    await params.replaceRoute();
    applied = params.contextApplied();
  } finally {
    params.formData[params.fieldName] = selectedValue;
    params.relationKeywords[params.fieldName] = selectedKeyword;
  }
  if (!applied) return false;
  await params.reload();
  return true;
}

export async function settleRelationSelectionContextSwitch(
  params: RelationSelectionContextSwitchParams,
): Promise<boolean> {
  let switched = false;
  try {
    switched = await params.switchContext();
  } catch (error) {
    params.reportError(error);
  }
  if (!switched) params.finalizeUnswitchedSelection();
  return switched;
}

export async function switchRelationOptionContext(params: {
  fieldName: string;
  option: RelationOption;
  recordId: number | null;
  entry: RelationSwitchEntry;
  routeQuery: Record<string, unknown>;
  normalizeQuery: (query: Record<string, unknown>) => Record<string, string | string[]>;
  transition?: { previousValue: unknown; previousKeyword: string };
  formData: Record<string, unknown>;
  relationKeywords: Record<string, string>;
  replaceRoute: (query: Record<string, string | string[]>) => Promise<unknown>;
  currentContextCode: () => string;
  reload: () => Promise<void>;
}): Promise<boolean> {
  if (params.recordId) return false;
  const switchContext = params.entry?.switchContext;
  const nextCode = params.option.switchContext?.code || '';
  if (!switchContext?.enabled || !nextCode || params.currentContextCode() === nextCode) return false;
  const query = params.normalizeQuery(params.routeQuery);
  for (const key of switchContext.defaultClearFields || []) delete query[`default_${key}`];
  query.current_business_category_code = nextCode;
  query.default_business_category_code = nextCode;
  query.current_business_category_label = params.option.switchContext?.label || params.option.label;
  query.default_business_category_label = params.option.switchContext?.label || params.option.label;
  query.default_business_category_id = String(params.option.id);
  query.ctx_source = 'business_category_relation_switch';
  Object.entries(params.option.switchContext?.defaultValues || {}).forEach(([key, value]) => {
    const normalizedKey = String(key || '').trim();
    if (!normalizedKey || value === undefined || value === null) return;
    if (Array.isArray(value) || typeof value === 'object') return;
    query[`default_${normalizedKey}`] = String(value);
  });
  return applyInternalRelationContextSwitch({
    fieldName: params.fieldName,
    formData: params.formData,
    relationKeywords: params.relationKeywords,
    previousValue: params.transition?.previousValue ?? params.routeQuery[`default_${params.fieldName}`] ?? false,
    previousKeyword: params.transition?.previousKeyword || '',
    replaceRoute: () => params.replaceRoute(query),
    contextApplied: () => params.currentContextCode() === nextCode,
    reload: params.reload,
  });
}
