import { ContractGapError } from '../contract/contractGap';

type Dict = Record<string, unknown>;

export const RECORD_ENTRY_INTENTS = [
  'open',
  'handling',
  'explicit_readonly',
  'explicit_edit',
] as const;

export type RecordOpenIntent = typeof RECORD_ENTRY_INTENTS[number];

/**
 * 声明了「进入后可编辑」的意图集合。缺失写权限事实时不得降级为只读，
 * 必须作为ContractGapError停机（T5：分开「明确禁止」与「声明缺失」）。
 */
export const WRITE_IMPLYING_RECORD_ENTRY_INTENTS = ['open', 'handling', 'explicit_edit'] as const;

export function entryIntentImpliesWrite(intent: RecordOpenIntent): boolean {
  return (WRITE_IMPLYING_RECORD_ENTRY_INTENTS as readonly string[]).includes(intent);
}

/** 正式记录入口契约的声明归属层，供停机引用。 */
export const RECORD_ENTRY_DECLARATION_LAYER = 'P0:smart_core:entry_target.record_entry';

function raiseRecordEntryGap(missing: string, message: string): never {
  throw new ContractGapError(
    {
      kind: 'contract_defect',
      missing,
      requiredDeclarationLayer: RECORD_ENTRY_DECLARATION_LAYER,
    },
    message,
  );
}

/**
 * The only record-open authority consumed by production navigation.
 *
 * `modelWriteAuthority` is a backend contract fact.  It is deliberately not
 * inferred from a route, a label, or a query string.
 *
 * Tri-state semantics (T5):
 * - `true`  = backend declared write allowed;
 * - `false` = backend declared write forbidden (explicit deny -> readonly route);
 * - `null`  = not required by the declared intent (readonly entry), never a
 *   silent downgrade of an undeclared write authority.
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
 * Decode the formal `entry_target.record_entry` carrier.
 *
 * Only an absent carrier (`undefined`) returns `null`. A declared carrier
 * whose structure or required declaration is illegal or missing stops
 * with a contract gap instead of being downgraded (T5):
 *
 * - an illegal `entry_intent` value raises a gap (no fallback to explicit_readonly);
 * - a write-implying intent without a declared boolean `model_write_authority`
 *   raises a gap (no silent read-only downgrade);
 * - `model_write_authority === false` is an explicit deny and stays read-only.
 *
 * The write authority is never recovered from a stringly typed hint.
 */
export function decodeFormalRecordEntry(raw: unknown): RecordEntryContract | null {
  if (raw === undefined) return null;
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    raiseRecordEntryGap('entry_target.record_entry', '正式记录入口必须声明对象，前端不得回退到兼容导航');
  }
  const value = raw as Dict;
  const model = typeof value.model === 'string' ? value.model.trim() : '';
  if (!model) {
    raiseRecordEntryGap('entry_target.record_entry.model', '正式记录入口缺少有效 model，前端不得回退到兼容导航');
  }
  const recordId = resolveRecordEntryId(value.record_id);
  if (recordId === null) {
    raiseRecordEntryGap('entry_target.record_entry.record_id', '正式记录入口缺少有效 record_id，前端不得回退到兼容导航');
  }
  if (!Object.prototype.hasOwnProperty.call(value, 'entry_intent')) {
    raiseRecordEntryGap('entry_target.record_entry.entry_intent', '正式记录入口缺少 entry_intent，前端不得回退到兼容导航');
  }

  const entryIntent = normalizeRecordOpenIntent(value.entry_intent);
  if (!entryIntent) {
    raiseRecordEntryGap(
      'entry_target.record_entry.entry_intent',
      `契约声明了非法 entry_intent=${String(value.entry_intent)}：前端不得降级为只读，等待声明层补齐`,
    );
  }

  const hasAuthorityKey = Object.prototype.hasOwnProperty.call(value, 'model_write_authority');
  let modelWriteAuthority: boolean | null = null;
  if (hasAuthorityKey) {
    if (typeof value.model_write_authority !== 'boolean') {
      raiseRecordEntryGap(
        'entry_target.record_entry.model_write_authority',
        `契约声明了非法 model_write_authority=${String(value.model_write_authority)}：前端不得降级为只读，等待声明层补齐`,
      );
    }
    modelWriteAuthority = value.model_write_authority;
  } else if (entryIntentImpliesWrite(entryIntent)) {
    raiseRecordEntryGap(
      'entry_target.record_entry.model_write_authority',
      '契约缺少 model_write_authority：进入写行为的意图必须带出写权限事实，前端不得降级为只读',
    );
  }

  return {
    model,
    recordId,
    entryIntent,
    modelWriteAuthority,
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
