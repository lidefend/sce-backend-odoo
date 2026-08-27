import { intentRequestRaw } from '../../../api/intents';
import { resolveModelContractRenderProfile } from '../../../api/modelContractProfile';
import { currentContextEpoch } from '../../contextEpoch';
import { useSessionStore } from '../../../stores/session';
import { decodeContractV2Snapshot } from './schema';
import { createContractV2Store } from './store';
import { permitsContractV2SnapshotReuse } from './runtime';
import type { ContractV2Dictionary, ContractV2NormalizedStore, ContractV2Snapshot } from './types';

export interface ContractV2LoadOptions {
  actionId?: number | null;
  sceneKey?: string | null;
  menuId?: number | null;
  viewId?: number | null;
  recordId?: number;
  viewType?: string;
  renderProfile?: 'create' | 'edit' | 'readonly';
  surface?: 'user' | 'native' | 'hud';
  sourceMode?: string;
  context?: ContractV2Dictionary;
  contextRaw?: string;
  previewToken?: string | null;
  previewRoleKey?: string | null;
}

export interface ContractV2LoadResult {
  snapshot: ContractV2Snapshot;
  store: ContractV2NormalizedStore;
  traceId: string;
  rawBody?: unknown;
}

type CachedContractV2LoadResult = Omit<ContractV2LoadResult, 'store'>;

const CREATE_CONTRACT_CACHE_TTL_MS = 30_000;
const CREATE_CONTRACT_CACHE_MAX_ENTRIES = 16;
const createContractCache = new Map<string, { expiresAt: number; result: CachedContractV2LoadResult }>();

function cloneJson<T>(value: T): T {
  if (value === undefined || value === null) return value;
  return JSON.parse(JSON.stringify(value)) as T;
}

function restoreCachedResult(result: CachedContractV2LoadResult): ContractV2LoadResult {
  const snapshot = cloneJson(result.snapshot);
  return {
    snapshot,
    store: createContractV2Store(snapshot),
    traceId: result.traceId,
    rawBody: cloneJson(result.rawBody),
  };
}

function createContractCacheKey(params: ContractV2Dictionary): string {
  const session = useSessionStore();
  return [
    session.sessionDb,
    session.token || '',
    currentContextEpoch(),
    JSON.stringify(params),
  ].join('|');
}

function pruneCreateContractCache(now: number): void {
  for (const [key, entry] of createContractCache) {
    if (entry.expiresAt <= now) createContractCache.delete(key);
  }
  while (createContractCache.size >= CREATE_CONTRACT_CACHE_MAX_ENTRIES) {
    const oldestKey = createContractCache.keys().next().value;
    if (typeof oldestKey !== 'string') break;
    createContractCache.delete(oldestKey);
  }
}

function normalizedRecordId(value: unknown): number {
  const parsed = Number(value || 0);
  return Number.isFinite(parsed) && parsed > 0 ? Math.trunc(parsed) : 0;
}

function applyCommonOptions(params: ContractV2Dictionary, options: ContractV2LoadOptions = {}): ContractV2Dictionary {
  const recordId = normalizedRecordId(options.recordId);
  if (recordId) params.record_id = recordId;
  if (options.viewType) params.view_type = options.viewType;
  if (options.renderProfile) params.render_profile = options.renderProfile;
  if (options.surface) params.contract_surface = options.surface;
  if (options.sourceMode) params.source_mode = options.sourceMode;
  if (options.context && typeof options.context === 'object' && !Array.isArray(options.context)) {
    params.context = options.context;
  }
  if (options.contextRaw) params.context_raw = options.contextRaw;
  if (options.sceneKey) params.scene_key = options.sceneKey;
  if (normalizedRecordId(options.menuId)) params.menu_id = normalizedRecordId(options.menuId);
  if (normalizedRecordId(options.viewId)) params.view_id = normalizedRecordId(options.viewId);
  if (options.previewToken) params.preview_token = options.previewToken;
  if (options.previewRoleKey) params.preview_role_key = options.previewRoleKey;
  params.delivery_profile = 'full';
  params.client_type = 'web_pc';
  params.accepted_contract_versions = ['2.0.x', '2.1.x', '2.2.x'];
  params.client_contract_capabilities = [
    'container_tree.v2',
    'data_source.v2',
    'action_rule.v2',
    'relation_entry.v2',
    'status_contract.v2',
    'form_layout.children_owner.v1',
  ];
  return params;
}

async function loadContractV2(params: ContractV2Dictionary): Promise<ContractV2LoadResult> {
  const response = await intentRequestRaw<ContractV2Dictionary>({
    intent: 'ui.contract.v2',
    params,
  });
  const snapshot = decodeContractV2Snapshot(response.data);
  return {
    snapshot,
    store: createContractV2Store(snapshot),
    traceId: response.traceId,
    rawBody: response.rawBody,
  };
}

export function loadActionContractV2(actionId: number, options: ContractV2LoadOptions = {}): Promise<ContractV2LoadResult> {
  return loadContractV2(applyCommonOptions({
    op: 'action_open',
    action_id: normalizedRecordId(actionId),
  }, options));
}

export function loadModelContractV2(model: string, options: ContractV2LoadOptions = {}): Promise<ContractV2LoadResult> {
  const renderProfile = resolveModelContractRenderProfile({
    viewType: options.viewType,
    recordId: options.recordId,
    renderProfile: options.renderProfile,
  });
  const params = applyCommonOptions({
    op: 'model',
    model: String(model || '').trim(),
    view_type: options.viewType || 'form',
  }, { ...options, renderProfile: renderProfile || undefined });
  const actionId = normalizedRecordId(options.actionId);
  if (actionId) params.action_id = actionId;
  const cacheable = renderProfile === 'create'
    && !normalizedRecordId(options.recordId)
    && !String(options.previewToken || '').trim();
  if (!cacheable) return loadContractV2(params);

  const now = Date.now();
  pruneCreateContractCache(now);
  const key = createContractCacheKey(params);
  const cached = createContractCache.get(key);
  if (cached && cached.expiresAt > now) return Promise.resolve(restoreCachedResult(cached.result));

  return loadContractV2(params).then((result) => {
    const cachedResult: CachedContractV2LoadResult = {
      snapshot: cloneJson(result.snapshot),
      traceId: result.traceId,
      rawBody: cloneJson(result.rawBody),
    };
    if (permitsContractV2SnapshotReuse(result.snapshot.runtimeContract)) {
      createContractCache.set(key, {
        expiresAt: now + CREATE_CONTRACT_CACHE_TTL_MS,
        result: cachedResult,
      });
    } else {
      createContractCache.delete(key);
    }
    return restoreCachedResult(cachedResult);
  }).catch((error: unknown) => {
    createContractCache.delete(key);
    throw error;
  });
}
