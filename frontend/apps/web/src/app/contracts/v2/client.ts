import { intentRequestRaw } from '../../../api/intents';
import { resolveModelContractRenderProfile } from '../../../api/modelContractProfile';
import { currentContextEpoch } from '../../contextEpoch';
import { useSessionStore } from '../../../stores/session';
import { decodeContractV2Snapshot } from './schema';
import { createContractV2Store } from './store';
import { CONTRACT_V2_CLIENT_CAPABILITIES } from './clientCapabilities';
import {
  decodeContractCarrierCapabilities,
  type ContractCarrierCapabilities,
} from './carrierCapabilities';
import {
  permitsContractV2SnapshotReuse,
  requiresContractV2EtagRevalidation,
} from './runtime';
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
  carrierCapabilities?: ContractCarrierCapabilities;
}

type CachedContractV2LoadResult = Omit<ContractV2LoadResult, 'store'>;
type CreateContractCacheEntry =
  | { policy: 'snapshot'; expiresAt: number; result: CachedContractV2LoadResult }
  | { policy: 'etag'; etag: string; result: CachedContractV2LoadResult };

const CREATE_CONTRACT_CACHE_TTL_MS = 30_000;
const CREATE_CONTRACT_CACHE_MAX_ENTRIES = 16;
const createContractCache = new Map<string, CreateContractCacheEntry>();

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
    carrierCapabilities: result.carrierCapabilities ? cloneJson(result.carrierCapabilities) : undefined,
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
    if (entry.policy === 'snapshot' && entry.expiresAt <= now) createContractCache.delete(key);
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
  params.accepted_contract_versions = ['2.7.x'];
  params.client_contract_capabilities = [...CONTRACT_V2_CLIENT_CAPABILITIES];
  return params;
}

async function loadContractV2(
  params: ContractV2Dictionary,
  ifNoneMatch = '',
): Promise<ContractV2LoadResult | null> {
  const response = await intentRequestRaw<ContractV2Dictionary>({
    intent: 'ui.contract.v2',
    params,
  }, ifNoneMatch ? {
    headers: { 'If-None-Match': ifNoneMatch },
  } : {});
  if (response.notModified) return null;
  const snapshot = decodeContractV2Snapshot(response.data);
  const negotiation = response.meta?.contract_negotiation;
  const carrierCapabilities = negotiation
    ? decodeContractCarrierCapabilities(negotiation)
    : undefined;
  return {
    snapshot,
    store: createContractV2Store(snapshot),
    traceId: response.traceId,
    rawBody: response.rawBody,
    ...(carrierCapabilities ? { carrierCapabilities } : {}),
  };
}

async function requireContractV2Load(params: ContractV2Dictionary): Promise<ContractV2LoadResult> {
  const result = await loadContractV2(params);
  if (!result) throw new Error('ui.contract.v2 returned 304 without a conditional cache candidate');
  return result;
}

function cacheCreateContractResult(
  key: string,
  result: ContractV2LoadResult,
  now: number,
): void {
  const cachedResult: CachedContractV2LoadResult = {
    snapshot: cloneJson(result.snapshot),
    traceId: result.traceId,
    rawBody: cloneJson(result.rawBody),
    carrierCapabilities: result.carrierCapabilities ? cloneJson(result.carrierCapabilities) : undefined,
  };
  if (permitsContractV2SnapshotReuse(result.snapshot.runtimeContract)) {
    createContractCache.set(key, {
      policy: 'snapshot',
      expiresAt: now + CREATE_CONTRACT_CACHE_TTL_MS,
      result: cachedResult,
    });
    return;
  }
  const etag = String(result.snapshot.meta.etag || '').trim();
  if (requiresContractV2EtagRevalidation(result.snapshot.runtimeContract) && etag) {
    createContractCache.set(key, { policy: 'etag', etag, result: cachedResult });
    return;
  }
  createContractCache.delete(key);
}

export function loadActionContractV2(actionId: number, options: ContractV2LoadOptions = {}): Promise<ContractV2LoadResult> {
  const params = applyCommonOptions({
    op: 'action_open',
    action_id: normalizedRecordId(actionId),
  }, options);
  return loadContractV2(params).then((result) => {
    if (!result) throw new Error('ui.contract.v2 returned 304 without a conditional cache candidate');
    return result;
  });
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
  if (!cacheable) return requireContractV2Load(params);

  const now = Date.now();
  pruneCreateContractCache(now);
  const key = createContractCacheKey(params);
  const cached = createContractCache.get(key);
  if (cached?.policy === 'snapshot' && cached.expiresAt > now) {
    return Promise.resolve(restoreCachedResult(cached.result));
  }

  const load = async () => {
    if (cached?.policy === 'etag') {
      const revalidated = await loadContractV2(params, cached.etag);
      if (!revalidated) return restoreCachedResult(cached.result);
      cacheCreateContractResult(key, revalidated, Date.now());
      return revalidated;
    }
    const result = await requireContractV2Load(params);
    cacheCreateContractResult(key, result, Date.now());
    return result;
  };

  return load().catch((error: unknown) => {
    createContractCache.delete(key);
    throw error;
  });
}
