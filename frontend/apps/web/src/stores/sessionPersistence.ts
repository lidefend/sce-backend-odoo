export const DURABLE_SESSION_SCHEMA_VERSION = 1;
export const SESSION_SNAPSHOT_KEY_PREFIX = 'sc_frontend_session_v0_6';
export const MAX_DURABLE_ACTIVITY_PAGES = 6;

const ALLOWED_BOOTSTRAP_INTENTS = new Set(['system.init', 'session.bootstrap']);
const ACTIVITY_RUNTIME_QUERY_KEYS = new Set([
  'search',
  'q',
  'active_filter',
  'saved_filter',
  'group_by',
  'group_value',
  'group_sample_limit',
  'group_sort',
  'group_collapsed',
  'group_page',
  'group_offset',
  'group_fp',
  'group_wid',
  'group_wdg',
  'group_wik',
]);

type JsonRecord = Record<string, unknown>;

export interface DurableMenuExpansionPreferences {
  menuExpandedKeys: string[];
  scenarioExpandedCenters: string[];
  scenarioExpandedScenarios: string[];
}

export interface DurableUserIdentity {
  id: number;
  name: string;
}

export interface DurableRecordSelection {
  id: number;
  name: string;
  display_name: string;
  company_id: number | null;
  company_name: string;
  operation_strategy: string;
  operation_strategy_label: string;
}

export interface DurableRecordContext {
  model: string;
  company_id: number | null;
  company_name: string;
  operation_strategy: string;
  operation_strategy_label: string;
  selected: DurableRecordSelection | null;
  request_context: JsonRecord;
  clear_request_context: JsonRecord;
}

export interface DurableActivityRecordContext {
  company_id: number | null;
  company_name: string;
  operation_strategy: string;
  operation_strategy_label: string;
  selected: {
    id: number;
    name: string;
    display_name: string;
    company_id: number | null;
    company_name: string;
    operation_strategy: string;
    operation_strategy_label: string;
  } | null;
}

export interface DurableActivityPage {
  key: string;
  title: string;
  route: string;
  kind: 'menu_action' | 'record_form' | 'scene' | 'workspace' | 'custom';
  model?: string;
  action_id?: number;
  menu_id?: number;
  record_id?: string;
  scene_key?: string;
  record_context: DurableActivityRecordContext | null;
  runtime_query?: Record<string, string | string[]>;
  created_at: number;
  last_active_at: number;
}

export interface DurableSessionSnapshotV1 {
  schemaVersion: 1;
  sessionDb: string;
  user: DurableUserIdentity | null;
  recordContext: DurableRecordContext | null;
  activityPages: DurableActivityPage[];
  activeTab: string;
  cacheEpochs: Record<string, number>;
  menuExpansionPreferences: DurableMenuExpansionPreferences;
  bootstrapNextIntent: string;
}

export interface DurableSessionSource {
  sessionDb: unknown;
  user: unknown;
  recordContext: unknown;
  activityPages: unknown;
  activeActivityPageKey: unknown;
  activityPageCacheEpochs: unknown;
  menuExpandedKeys: unknown;
  scenarioExpandedCenters: unknown;
  scenarioExpandedScenarios: unknown;
  bootstrapNextIntent: unknown;
}

export type DurableSessionDecodeStatus =
  | 'missing'
  | 'legacy'
  | 'current'
  | 'unsupported'
  | 'corrupt';

export interface DurableSessionDecodeResult {
  status: DurableSessionDecodeStatus;
  snapshot: DurableSessionSnapshotV1 | null;
}

function asText(value: unknown): string {
  return typeof value === 'string' ? value.trim() : String(value ?? '').trim();
}

function asRecord(value: unknown): JsonRecord {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as JsonRecord
    : {};
}

function positiveInteger(value: unknown): number {
  const parsed = Number(value || 0);
  return Number.isFinite(parsed) && parsed > 0 ? Math.trunc(parsed) : 0;
}

function nullablePositiveInteger(value: unknown): number | null {
  return positiveInteger(value) || null;
}

function uniqueStrings(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return [...new Set(value.map((item) => asText(item)).filter(Boolean))];
}

function jsonRecord(value: unknown): JsonRecord {
  const row = asRecord(value);
  if (!Object.keys(row).length) return {};
  try {
    const cloned = JSON.parse(JSON.stringify(row)) as unknown;
    return asRecord(cloned);
  } catch {
    return {};
  }
}

export function normalizeDurableActivityRuntimeQuery(
  raw: unknown,
): Record<string, string | string[]> | undefined {
  const source = asRecord(raw);
  const normalized: Record<string, string | string[]> = {};
  Object.entries(source).forEach(([key, value]) => {
    if (!ACTIVITY_RUNTIME_QUERY_KEYS.has(key)) return;
    if (Array.isArray(value)) {
      const values = value.map((item) => asText(item)).filter(Boolean);
      if (values.length) normalized[key] = values;
      return;
    }
    const text = asText(value);
    if (text) normalized[key] = text;
  });
  return Object.keys(normalized).length ? normalized : undefined;
}

function durableUserIdentity(raw: unknown): DurableUserIdentity | null {
  const row = asRecord(raw);
  const id = positiveInteger(row.id);
  if (!id) return null;
  return {
    id,
    name: asText(row.name),
  };
}

function durableRecordSelection(raw: unknown): DurableRecordSelection | null {
  const row = asRecord(raw);
  const id = positiveInteger(row.id);
  if (!id) return null;
  return {
    id,
    name: asText(row.name),
    display_name: asText(row.display_name) || asText(row.name),
    company_id: nullablePositiveInteger(row.company_id),
    company_name: asText(row.company_name),
    operation_strategy: asText(row.operation_strategy),
    operation_strategy_label: asText(row.operation_strategy_label),
  };
}

function durableRecordContext(raw: unknown): DurableRecordContext | null {
  const row = asRecord(raw);
  if (!Object.keys(row).length) return null;
  return {
    model: asText(row.model),
    company_id: nullablePositiveInteger(row.company_id),
    company_name: asText(row.company_name),
    operation_strategy: asText(row.operation_strategy),
    operation_strategy_label: asText(row.operation_strategy_label),
    selected: durableRecordSelection(row.selected),
    request_context: jsonRecord(row.request_context),
    clear_request_context: jsonRecord(row.clear_request_context),
  };
}

function durableActivityRecordContext(raw: unknown): DurableActivityRecordContext | null {
  const row = asRecord(raw);
  if (!Object.keys(row).length) return null;
  const selected = durableRecordSelection(row.selected);
  return {
    company_id: nullablePositiveInteger(row.company_id),
    company_name: asText(row.company_name),
    operation_strategy: asText(row.operation_strategy),
    operation_strategy_label: asText(row.operation_strategy_label),
    selected: selected ? {
      id: selected.id,
      name: selected.name,
      display_name: selected.display_name,
      company_id: selected.company_id,
      company_name: selected.company_name,
      operation_strategy: selected.operation_strategy,
      operation_strategy_label: selected.operation_strategy_label,
    } : null,
  };
}

function durableActivityPages(raw: unknown): DurableActivityPage[] {
  if (!Array.isArray(raw)) return [];
  const pages: DurableActivityPage[] = [];
  for (const item of raw) {
    const row = asRecord(item);
    const key = asText(row.key);
    const route = asText(row.route);
    const kind = asText(row.kind);
    if (!key || !route || !['menu_action', 'record_form', 'scene', 'workspace', 'custom'].includes(kind)) {
      continue;
    }
    const runtimeQuery = normalizeDurableActivityRuntimeQuery(row.runtime_query);
    pages.push({
      key,
      title: asText(row.title),
      route,
      kind: kind as DurableActivityPage['kind'],
      ...(asText(row.model) ? { model: asText(row.model) } : {}),
      ...(positiveInteger(row.action_id) ? { action_id: positiveInteger(row.action_id) } : {}),
      ...(positiveInteger(row.menu_id) ? { menu_id: positiveInteger(row.menu_id) } : {}),
      ...(asText(row.record_id) ? { record_id: asText(row.record_id) } : {}),
      ...(asText(row.scene_key) ? { scene_key: asText(row.scene_key) } : {}),
      record_context: durableActivityRecordContext(row.record_context),
      ...(runtimeQuery ? { runtime_query: runtimeQuery } : {}),
      created_at: Number(row.created_at || 0) || 0,
      last_active_at: Number(row.last_active_at || 0) || 0,
    });
    if (pages.length >= MAX_DURABLE_ACTIVITY_PAGES) break;
  }
  return pages;
}

function activityPageCacheRouteKey(key: string): string {
  const parts = key.split(':');
  if (parts[0] === 'action' && parts.length >= 4) return parts.slice(0, 4).join(':');
  if (parts[0] === 'scene' && parts.length >= 2) return parts.slice(0, 2).join(':');
  return key;
}

function durableCacheEpochs(raw: unknown, retainedPageKeys: Set<string>): Record<string, number> {
  const row = asRecord(raw);
  const epochs: Record<string, number> = {};
  Object.entries(row).forEach(([key, value]) => {
    const normalizedKey = asText(key);
    const epoch = Number(value);
    if (!normalizedKey || !Number.isFinite(epoch) || epoch < 0) return;
    const retained = retainedPageKeys.has(normalizedKey)
      || [...retainedPageKeys].some((pageKey) => activityPageCacheRouteKey(pageKey) === normalizedKey);
    if (!retained) return;
    epochs[normalizedKey] = Math.trunc(epoch);
  });
  return epochs;
}

function durableBootstrapIntent(raw: unknown): string {
  const intent = asText(raw) || 'system.init';
  return ALLOWED_BOOTSTRAP_INTENTS.has(intent) ? intent : 'system.init';
}

export function durableSessionStorageKey(scope: string): string {
  return `${SESSION_SNAPSHOT_KEY_PREFIX}:${scope}`;
}

export function buildDurableSessionSnapshot(source: DurableSessionSource): DurableSessionSnapshotV1 {
  const activityPages = durableActivityPages(source.activityPages);
  const retainedKeys = new Set(activityPages.map((page) => page.key));
  const activeTab = asText(source.activeActivityPageKey);
  return {
    schemaVersion: DURABLE_SESSION_SCHEMA_VERSION,
    sessionDb: asText(source.sessionDb),
    user: durableUserIdentity(source.user),
    recordContext: durableRecordContext(source.recordContext),
    activityPages,
    activeTab: retainedKeys.has(activeTab) ? activeTab : '',
    cacheEpochs: durableCacheEpochs(source.activityPageCacheEpochs, retainedKeys),
    menuExpansionPreferences: {
      menuExpandedKeys: uniqueStrings(source.menuExpandedKeys),
      scenarioExpandedCenters: uniqueStrings(source.scenarioExpandedCenters),
      scenarioExpandedScenarios: uniqueStrings(source.scenarioExpandedScenarios),
    },
    bootstrapNextIntent: durableBootstrapIntent(source.bootstrapNextIntent),
  };
}

function snapshotFromRaw(raw: JsonRecord, legacy: boolean): DurableSessionSnapshotV1 {
  const menuPreferences = asRecord(raw.menuExpansionPreferences);
  return buildDurableSessionSnapshot({
    sessionDb: raw.sessionDb,
    user: raw.user,
    recordContext: raw.recordContext,
    activityPages: raw.activityPages,
    activeActivityPageKey: legacy ? raw.activeActivityPageKey : (raw.activeTab ?? raw.activeActivityPageKey),
    activityPageCacheEpochs: legacy ? raw.activityPageCacheEpochs : (raw.cacheEpochs ?? raw.activityPageCacheEpochs),
    menuExpandedKeys: menuPreferences.menuExpandedKeys ?? raw.menuExpandedKeys,
    scenarioExpandedCenters: menuPreferences.scenarioExpandedCenters ?? raw.scenarioExpandedCenters,
    scenarioExpandedScenarios: menuPreferences.scenarioExpandedScenarios ?? raw.scenarioExpandedScenarios,
    bootstrapNextIntent: raw.bootstrapNextIntent,
  });
}

export function decodeDurableSessionSnapshot(raw: string | null): DurableSessionDecodeResult {
  if (!raw) return { status: 'missing', snapshot: null };
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return { status: 'corrupt', snapshot: null };
  }
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    return { status: 'corrupt', snapshot: null };
  }
  const row = parsed as JsonRecord;
  if (!Object.prototype.hasOwnProperty.call(row, 'schemaVersion')) {
    return { status: 'legacy', snapshot: snapshotFromRaw(row, true) };
  }
  const version = Number(row.schemaVersion);
  if (!Number.isInteger(version) || version !== DURABLE_SESSION_SCHEMA_VERSION) {
    return { status: 'unsupported', snapshot: null };
  }
  return { status: 'current', snapshot: snapshotFromRaw(row, false) };
}
