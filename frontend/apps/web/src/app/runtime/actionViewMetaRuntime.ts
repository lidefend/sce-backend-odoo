import type { ContractV2NormalizedStore } from '../contracts/v2/types';

function resolveFirstRenderableViewMode(value: unknown): string {
  const rawModes = Array.isArray(value)
    ? value
    : String(value || '').split(',');
  const modes = rawModes
    .map((item) => String(item || '').trim())
    .filter(Boolean);
  const supported = new Set(['tree', 'list', 'kanban', 'form']);
  return modes.find((mode) => supported.has(mode)) || modes[0] || '';
}

export function resolveActionViewType(meta: unknown, contract: ContractV2NormalizedStore | null): string {
  const metaViewModes = (meta as { view_modes?: unknown } | null)?.view_modes;
  const normalizedMetaViewMode = resolveFirstRenderableViewMode(metaViewModes);
  const v2ViewType = String(contract?.snapshot.pageInfo.viewType || '').trim();
  if (v2ViewType) {
    const normalizedV2ViewType = v2ViewType === 'list' ? 'tree' : v2ViewType;
    return normalizedV2ViewType;
  }
  if (normalizedMetaViewMode) return normalizedMetaViewMode;
  return '';
}

export function parseNumericId(raw: unknown): number | null {
  if (typeof raw === 'number' && Number.isFinite(raw) && raw > 0) return raw;
  if (typeof raw === 'string' && raw.trim()) {
    const parsed = Number(raw.trim());
    if (Number.isFinite(parsed) && parsed > 0) return parsed;
  }
  return null;
}

export function extractActionResId(contract: unknown, routeQuery: Record<string, unknown>): number | null {
  void contract;
  const routeResId = parseNumericId(routeQuery.res_id);
  if (routeResId) return routeResId;
  return null;
}
