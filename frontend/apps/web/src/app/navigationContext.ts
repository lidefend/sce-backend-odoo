import type { LocationQueryRaw, LocationQueryValueRaw } from 'vue-router';

export const CONTRACT_NAV_QUERY_KEYS = [
  'menu_id',
  'action_id',
  'hud',
  'surface',
  'scene',
  'scene_key',
  'domain_raw',
  'context_raw',
  'preset',
  'preset_filter',
  'search',
  'order',
  'active_filter',
  'saved_filter',
  'group_by',
  'group_value',
  'view_mode',
  'list_offset',
  'ctx_source',
  'entry_context',
  'group_by_cleared',
  'product_domain',
  'entry_intent',
  'disposition_policy',
  'integration_target',
  'entry_target_policy',
  'business_entry_contract_version',
  'entry_title',
  'current_business_category_code',
  'default_business_category_code',
  'allowed_business_category_codes',
  'current_business_category_label',
  'default_business_category_label',
] as const;

export const BUSINESS_ENTRY_NAV_QUERY_KEYS = [
  'product_domain',
  'entry_intent',
  'disposition_policy',
  'integration_target',
  'entry_target_policy',
  'business_entry_contract_version',
  'current_business_category_code',
  'default_business_category_code',
  'allowed_business_category_codes',
  'current_business_category_label',
  'default_business_category_label',
] as const;

const CROSS_MODEL_SHELL_QUERY_KEYS = ['hud'] as const;

function navRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

export function entryTargetModel(entryTarget: unknown): string {
  const target = navRecord(entryTarget);
  const recordEntry = navRecord(target.record_entry);
  const refs = navRecord(target.compatibility_refs);
  return String(recordEntry.model || refs.model || '').trim();
}

export function entryTargetMenuId(entryTarget: unknown): number {
  const target = navRecord(entryTarget);
  const recordEntry = navRecord(target.record_entry);
  const refs = navRecord(target.compatibility_refs);
  const parsed = Number(recordEntry.menu_id || refs.menu_id || 0);
  return Number.isFinite(parsed) && parsed > 0 ? Math.trunc(parsed) : 0;
}

export function contractActionCarryQuery(
  currentQuery: Record<string, unknown>,
  options: { currentModel?: unknown; targetModel?: unknown } = {},
) {
  const currentModel = String(options.currentModel || '').trim();
  const targetModel = String(options.targetModel || '').trim();
  if (!currentModel || !targetModel || currentModel === targetModel) {
    return pickContractNavQuery(currentQuery);
  }
  const shellQuery: Record<string, unknown> = {};
  CROSS_MODEL_SHELL_QUERY_KEYS.forEach((key) => {
    if (currentQuery[key] !== undefined) shellQuery[key] = currentQuery[key];
  });
  return pickContractNavQuery(shellQuery);
}

export function pickContractNavQuery(
  source: Record<string, unknown>,
  extra?: Record<string, unknown>,
) {
  const out: LocationQueryRaw = {};
  const normalize = (value: unknown): LocationQueryValueRaw | LocationQueryValueRaw[] | undefined => {
    if (value === undefined || value === null || value === '') return undefined;
    if (Array.isArray(value)) {
      return value
        .map((item) => (item === undefined || item === null ? '' : String(item)))
        .filter((item) => item !== '');
    }
    if (typeof value === 'boolean') {
      return value ? '1' : '0';
    }
    if (typeof value === 'string' || typeof value === 'number') {
      return value;
    }
    return JSON.stringify(value);
  };
  CONTRACT_NAV_QUERY_KEYS.forEach((key) => {
    const normalized = normalize(source[key]);
    if (normalized !== undefined) {
      out[key] = normalized;
    }
  });
  Object.entries(extra || {}).forEach(([key, value]) => {
    const normalized = normalize(value);
    if (normalized === undefined) {
      delete out[key];
      return;
    }
    out[key] = normalized;
  });
  return out;
}

function asText(value: unknown): string {
  return String(value ?? '').trim();
}

function normalizeNavValue(value: unknown): unknown {
  if (value === undefined || value === null || value === '') return undefined;
  if (Array.isArray(value)) {
    const items = value
      .map((item) => String(item ?? '').trim())
      .filter((item) => item !== '');
    return items.length ? items : undefined;
  }
  if (typeof value === 'boolean') {
    return value ? '1' : '0';
  }
  const text = String(value).trim();
  return text || undefined;
}

export function buildBusinessEntryNavQuery(source: Record<string, unknown> | null | undefined) {
  const raw = source || {};
  const categoryCode = asText(raw.current_business_category_code || raw.default_business_category_code);
  const out: Record<string, unknown> = {};
  BUSINESS_ENTRY_NAV_QUERY_KEYS.forEach((key) => {
    const value = normalizeNavValue(raw[key]);
    if (value !== undefined) out[key] = value;
  });
  if (categoryCode) {
    out.current_business_category_code = asText(out.current_business_category_code) || categoryCode;
    out.default_business_category_code = asText(out.default_business_category_code) || categoryCode;
  }
  return out;
}

export type BusinessCategoryCreateNavOption = {
  code?: unknown;
  label?: unknown;
  categoryId?: unknown;
  defaultValues?: Record<string, unknown> | null;
};

export function buildBusinessCategoryCreateNavQuery(options: {
  categoryCode?: unknown;
  option?: BusinessCategoryCreateNavOption | null;
  fallbackLabel?: unknown;
}): Record<string, unknown> | undefined {
  const code = asText(options.categoryCode);
  if (!code) return undefined;
  const option = options.option || null;
  const defaults: Record<string, string> = {};
  const categoryId = Number(option?.categoryId || 0);
  if (Number.isFinite(categoryId) && categoryId > 0) {
    defaults.default_business_category_id = String(categoryId);
  }
  Object.entries(option?.defaultValues || {}).forEach(([key, value]) => {
    const normalizedKey = asText(key);
    if (!normalizedKey || value === undefined || value === null) return;
    if (Array.isArray(value) || typeof value === 'object') return;
    defaults[`default_${normalizedKey}`] = String(value);
  });
  const label = asText(option?.label || options.fallbackLabel || '办理类型');
  return {
    current_business_category_code: code,
    default_business_category_code: code,
    current_business_category_label: label,
    default_business_category_label: label,
    ctx_source: 'business_category_create_picker',
    ...defaults,
  };
}

export function buildBusinessEntryRequestContext(source: Record<string, unknown>) {
  const raw = source || {};
  const categoryCode = asText(raw.current_business_category_code || raw.default_business_category_code);
  const out: Record<string, unknown> = {};
  [
    'product_domain',
    'entry_intent',
    'disposition_policy',
    'entry_target_policy',
    'business_entry_contract_version',
  ].forEach((key) => {
    const value = asText(raw[key]);
    if (value) out[key] = value;
  });
  if (categoryCode) {
    out.current_business_category_code = categoryCode;
    out.default_business_category_code = asText(raw.default_business_category_code) || categoryCode;
  }
  return out;
}
