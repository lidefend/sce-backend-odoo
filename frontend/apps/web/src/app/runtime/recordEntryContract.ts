type Dict = Record<string, unknown>;

export const RECORD_ENTRY_INTENTS = [
  'open',
  'handling',
  'explicit_readonly',
  'explicit_edit',
] as const;

export type RecordOpenIntent = typeof RECORD_ENTRY_INTENTS[number];

/**
 * The only record-open authority consumed by production navigation.
 *
 * `modelWriteAuthority` is a backend contract fact.  It is deliberately not
 * inferred from a route, a label, or a query string.  `null` means the fact is
 * unavailable and therefore fails closed to the readonly route.
 */
export interface RecordEntryContract {
  model: string;
  recordId: number | string;
  entryIntent: RecordOpenIntent;
  modelWriteAuthority: boolean | null;
  actionId?: number;
  menuId?: number;
  carryQuery?: Dict;
}

export interface RecordOpenTarget {
  path: string;
  query: Dict;
}

export function normalizeModelWriteAuthority(raw: unknown): boolean | null {
  return typeof raw === 'boolean' ? raw : null;
}

export function normalizeRecordOpenIntent(raw: unknown): RecordOpenIntent | null {
  const value = typeof raw === 'string' ? raw.trim().toLowerCase() : '';
  return (RECORD_ENTRY_INTENTS as readonly string[]).includes(value)
    ? value as RecordOpenIntent
    : null;
}

/** Compatibility-only spelling support. Never use this for formal payloads. */
export function normalizeLegacyRecordOpenIntent(raw: unknown): RecordOpenIntent {
  const value = String(raw || '').trim().toLowerCase();
  if (['readonly', 'read', 'view', 'explicit-readonly'].includes(value)) return 'explicit_readonly';
  if (['edit', 'write', 'explicit-edit'].includes(value)) return 'explicit_edit';
  if (['process', 'work_on'].includes(value)) return 'handling';
  return normalizeRecordOpenIntent(value) || 'open';
}

export function resolveRecordEntryId(rawId: unknown): number | string | null {
  if (typeof rawId === 'number' && Number.isFinite(rawId)) return rawId;
  if (typeof rawId === 'string' && rawId.trim()) return rawId;
  return null;
}

function positiveInteger(value: unknown): number | undefined {
  const parsed = Number(value || 0);
  return Number.isFinite(parsed) && parsed > 0 ? Math.trunc(parsed) : undefined;
}

function asRecord(value: unknown): Dict {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as Dict
    : {};
}

/**
 * Decode the formal `entry_target.record_entry` carrier.  Invalid or absent
 * authority remains null; it is never recovered from a stringly typed hint.
 */
export function decodeFormalRecordEntry(raw: unknown): RecordEntryContract | null {
  const value = asRecord(raw);
  const model = String(value.model || '').trim();
  const recordId = resolveRecordEntryId(value.record_id);
  if (!model || recordId === null || !Object.prototype.hasOwnProperty.call(value, 'entry_intent')) return null;

  const rawIntent = value.entry_intent;
  const entryIntent = normalizeRecordOpenIntent(rawIntent);
  if (!entryIntent) return {
    model,
    recordId,
    entryIntent: 'explicit_readonly',
    modelWriteAuthority: null,
    actionId: positiveInteger(value.action_id),
    menuId: positiveInteger(value.menu_id),
  };

  return {
    model,
    recordId,
    entryIntent,
    modelWriteAuthority: normalizeModelWriteAuthority(value.model_write_authority),
    actionId: positiveInteger(value.action_id),
    menuId: positiveInteger(value.menu_id),
  };
}

/**
 * Adapts historical top-level payloads at the boundary.  This function is not
 * a contract authority: a legacy route can express an opening intent only and
 * non-boolean values cannot establish write authority.
 */
export function adaptLegacyRecordEntry(raw: unknown, options: {
  fallbackModel?: unknown;
  fallbackRecordId?: unknown;
  legacyRoute?: unknown;
  fallbackActionId?: unknown;
  fallbackMenuId?: unknown;
  carryQuery?: Dict;
} = {}): RecordEntryContract | null {
  const value = asRecord(raw);
  const model = String(value.model || value.res_model || options.fallbackModel || '').trim();
  const recordId = resolveRecordEntryId(value.record_id ?? value.recordId ?? options.fallbackRecordId);
  if (!model || recordId === null) return null;
  const rawIntent = value.entry_intent ?? value.open_intent ?? value.openIntent ?? value.intent;
  const legacyRoute = String(options.legacyRoute || '').trim();
  const entryIntent = rawIntent !== undefined && rawIntent !== null && String(rawIntent).trim()
    ? normalizeLegacyRecordOpenIntent(rawIntent)
    : legacyRoute.startsWith('/f/')
      ? 'explicit_edit'
      : legacyRoute.startsWith('/r/')
        ? 'explicit_readonly'
        : 'open';
  return {
    model,
    recordId,
    entryIntent,
    modelWriteAuthority: normalizeModelWriteAuthority(
      value.model_write_authority ?? value.modelWriteAuthority ?? value.modelWrite ?? value.model_write,
    ),
    actionId: positiveInteger(value.action_id ?? value.actionId ?? options.fallbackActionId),
    menuId: positiveInteger(value.menu_id ?? value.menuId ?? options.fallbackMenuId),
    carryQuery: options.carryQuery,
  };
}

export function resolveRecordOpenTarget(entry: RecordEntryContract): RecordOpenTarget | null {
  const model = String(entry.model || '').trim();
  const recordId = resolveRecordEntryId(entry.recordId);
  if (!model || recordId === null) return null;
  const editable = (entry.entryIntent === 'open' || entry.entryIntent === 'handling' || entry.entryIntent === 'explicit_edit')
    && entry.modelWriteAuthority === true;
  return {
    path: `/${editable ? 'f' : 'r'}/${model}/${recordId}`,
    query: {
      menu_id: entry.menuId || undefined,
      action_id: entry.actionId || undefined,
      ...(entry.carryQuery || {}),
    },
  };
}

export function recordEntryFromModelRights(options: {
  model: string;
  recordId: number | string;
  modelRights?: unknown;
  entryIntent?: RecordOpenIntent;
  actionId?: number;
  menuId?: number;
  carryQuery?: Dict;
}): RecordEntryContract {
  const rights = asRecord(options.modelRights);
  return {
    model: options.model,
    recordId: options.recordId,
    entryIntent: options.entryIntent || 'open',
    modelWriteAuthority: normalizeModelWriteAuthority(rights.write),
    actionId: options.actionId,
    menuId: options.menuId,
    carryQuery: options.carryQuery,
  };
}
