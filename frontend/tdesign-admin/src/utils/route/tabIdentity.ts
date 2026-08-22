import type { LocationQueryRaw } from 'vue-router';

const CONTEXT_KEYS = [
  'action_id',
  'menu_id',
  'company_id',
  'current_project_id',
  'operation_strategy',
  'scene_key',
] as const;

const BUSINESS_CONTEXT_KEYS = ['company_id', 'current_project_id', 'operation_strategy'] as const;

export function businessContextSnapshot(context: Record<string, unknown> = {}) {
  return Object.fromEntries(
    BUSINESS_CONTEXT_KEYS.flatMap((key) => {
      const value = context[key];
      return value === undefined || value === null || value === '' ? [] : [[key, value]];
    }),
  );
}

export function sameBusinessContext(left: Record<string, unknown> = {}, right: Record<string, unknown> = {}) {
  return BUSINESS_CONTEXT_KEYS.every((key) => String(left[key] ?? '') === String(right[key] ?? ''));
}

export function businessTabKey(
  path: string,
  query: LocationQueryRaw = {},
  businessContext: Record<string, unknown> = {},
) {
  const values = CONTEXT_KEYS.flatMap((key) => {
    const value = query[key] ?? businessContext[key];
    if (value === undefined || value === null || value === '') return [];
    return [`${key}=${Array.isArray(value) ? value.join(',') : String(value)}`];
  });
  return values.length ? `${path}?${values.join('&')}` : path;
}

const SHAREABLE_RECORD_CONTEXT_KEYS = ['action_id', 'menu_id'] as const;

export function restoreMissingRecordContext(
  initialQuery: LocationQueryRaw,
  currentQuery: LocationQueryRaw,
): LocationQueryRaw | null {
  const restored: LocationQueryRaw = { ...currentQuery };
  let changed = false;

  SHAREABLE_RECORD_CONTEXT_KEYS.forEach((key) => {
    const initialValue = initialQuery[key];
    const currentValue = currentQuery[key];
    if (
      initialValue !== undefined &&
      initialValue !== null &&
      initialValue !== '' &&
      (currentValue === undefined || currentValue === null || currentValue === '')
    ) {
      restored[key] = initialValue;
      changed = true;
    }
  });

  return changed ? restored : null;
}
