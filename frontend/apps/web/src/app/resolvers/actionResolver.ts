import type { NavMeta, NavNode } from '@sc/schema';
import { findActionMeta, findActionMetaByMenu } from '../menu';
import { loadActionContractStore } from '../../api/contract';
import {
  resolveContractV2PrimaryDataSource,
  resolveContractV2SourceContext,
  type ContractV2NormalizedStore,
} from '../contracts/v2';

export interface ActionResolution {
  meta: NavMeta;
  contract: Awaited<ReturnType<typeof loadActionContractStore>>;
}

function splitViewModes(raw: unknown): string[] {
  if (Array.isArray(raw)) {
    return raw
      .map((item) => String(item || '').trim().toLowerCase())
      .filter(Boolean);
  }
  return String(raw || '')
    .split(',')
    .map((item) => item.trim().toLowerCase())
    .filter(Boolean);
}

function resolveMetaFromContract(contract: ContractV2NormalizedStore, actionId: number): NavMeta {
  const pageInfo = contract.snapshot.pageInfo;
  const primaryDataSource = resolveContractV2PrimaryDataSource(contract);
  const sourceContext = resolveContractV2SourceContext(contract);
  const model = String(pageInfo.model || '').trim();
  const name = String(pageInfo.pageName || '').trim();
  const viewType = String(pageInfo.viewType || '').trim().toLowerCase();
  const out: NavMeta = {
    action_id: Number(actionId || 0),
    action_type: 'ir.actions.act_window',
  };
  if (model) out.model = model;
  if (name) out.name = name;
  if (viewType) out.view_modes = [viewType === 'list' ? 'tree' : viewType];
  if (Array.isArray(primaryDataSource.domain)) out.domain = primaryDataSource.domain;
  if (typeof primaryDataSource.domain_raw === 'string') out.domain_raw = primaryDataSource.domain_raw;
  if (sourceContext.context) out.context = sourceContext.context;
  if (sourceContext.contextRaw) out.context_raw = sourceContext.contextRaw;
  return out;
}

function mergeMeta(base: NavMeta | null, fallback: NavMeta): NavMeta {
  const merged: NavMeta = { ...(base || {}), ...fallback };
  const contractModelChanged = Boolean(fallback.model && base?.model && fallback.model !== base.model);
  const baseDomain = base?.domain;
  const baseHasDomain = Array.isArray(baseDomain)
    ? baseDomain.length > 0
    : typeof baseDomain === 'string' && baseDomain.trim().length > 0;
  const baseContext = base?.context;
  const baseHasContext = typeof baseContext === 'string'
    ? baseContext.trim().length > 0
    : Boolean(baseContext && typeof baseContext === 'object' && !Array.isArray(baseContext) && Object.keys(baseContext).length);
  if (base?.action_type) merged.action_type = base.action_type;
  if (base?.menu_id) merged.menu_id = base.menu_id;
  if (base?.menu_xmlid) merged.menu_xmlid = base.menu_xmlid;
  if (base?.groups_xmlids?.length) merged.groups_xmlids = base.groups_xmlids;
  if (fallback.model) merged.model = fallback.model;
  else if (base?.model) merged.model = base.model;
  if (baseHasDomain && !contractModelChanged) merged.domain = baseDomain;
  if (baseHasContext && !contractModelChanged) merged.context = baseContext as NavMeta['context'];
  const baseModes = splitViewModes(base?.view_modes || []);
  if (baseModes.length && !contractModelChanged) {
    merged.view_modes = baseModes;
  } else if (fallback.view_modes?.length) {
    merged.view_modes = fallback.view_modes;
  }
  return merged;
}

export async function resolveAction(
  menuTree: NavNode[],
  actionId: number,
  currentAction?: NavMeta | null,
  options?: { sceneKey?: string | null; menuId?: number | null; viewType?: string | null; contextRaw?: string | null; previewToken?: string | null; previewRoleKey?: string | null },
): Promise<ActionResolution> {
  const currentMatches = Boolean(currentAction && Number(currentAction.action_id || 0) === Number(actionId || 0));
  const currentMenuId = Number(options?.menuId || currentAction?.menu_id || 0);
  const contractOptions = {
    sceneKey: String(options?.sceneKey || '').trim() || undefined,
    menuId: currentMenuId > 0 ? currentMenuId : undefined,
    viewType: String(options?.viewType || '').trim().toLowerCase() as Parameters<typeof loadActionContractStore>[1] extends infer T
      ? T extends { viewType?: infer V } ? V : never
      : never,
    contextRaw: String(options?.contextRaw || '').trim() || undefined,
    previewToken: String(options?.previewToken || '').trim() || undefined,
    previewRoleKey: String(options?.previewRoleKey || '').trim() || undefined,
  };
  const metaFromMenu = (
    currentMenuId > 0
      ? findActionMetaByMenu(menuTree, currentMenuId, actionId)
      : null
  ) || findActionMeta(menuTree, actionId);
  // Always prefer menuTree meta to avoid stale/incomplete currentAction snapshots.
  const seedMeta = metaFromMenu || (currentMatches ? currentAction : null);

  const canonicalStore = await loadActionContractStore(actionId, contractOptions);
  const meta = mergeMeta(seedMeta, resolveMetaFromContract(canonicalStore, actionId));
  if (!meta.action_id) meta.action_id = Number(actionId || 0);
  return { meta, contract: canonicalStore };
}
