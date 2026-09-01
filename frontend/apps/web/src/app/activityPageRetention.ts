export interface RetainedActivityPageLike {
  key: string;
  kind: string;
  model?: string;
  action_id?: number;
  menu_id?: number;
  record_id?: string;
  record_context?: {
    selected?: { id?: number | null } | null;
    company_id?: number | null;
  } | null;
  dirty?: boolean;
  last_active_at?: number;
}

function positiveInteger(value: unknown): number {
  const parsed = Number(value || 0);
  return Number.isFinite(parsed) && parsed > 0 ? Math.trunc(parsed) : 0;
}

function contextIdentity(page: RetainedActivityPageLike): string {
  const companyId = positiveInteger(page.record_context?.company_id);
  const selectedId = positiveInteger(page.record_context?.selected?.id);
  return `company:${companyId}:record:${selectedId}`;
}

export function isSupersededEntryActionActivityPage(
  existing: RetainedActivityPageLike,
  incoming: RetainedActivityPageLike,
): boolean {
  if (existing.key === incoming.key || existing.dirty) return false;
  if (existing.kind !== 'menu_action' || incoming.kind !== 'record_form') return false;
  if (incoming.record_id !== 'new') return false;
  if (contextIdentity(existing) !== contextIdentity(incoming)) return false;
  const existingMenuId = positiveInteger(existing.menu_id);
  const incomingMenuId = positiveInteger(incoming.menu_id);
  if (existingMenuId > 0 || incomingMenuId > 0) {
    return existingMenuId > 0 && existingMenuId === incomingMenuId;
  }
  const existingActionId = positiveInteger(existing.action_id);
  const incomingActionId = positiveInteger(incoming.action_id);
  return existingActionId > 0 && existingActionId === incomingActionId;
}

export function retainIndependentActivityPages<T extends RetainedActivityPageLike>(
  pages: readonly T[],
  incoming: T,
  supersedesEntryAction: boolean,
): T[] {
  return pages.filter((page) => (
    page.key !== incoming.key
    && !(supersedesEntryAction && isSupersededEntryActionActivityPage(page, incoming))
  ));
}

export function trimRetainedActivityPages<T extends RetainedActivityPageLike>(
  pages: readonly T[],
  activeKey: string,
  limit: number,
): T[] {
  const normalizedLimit = Math.max(1, Math.trunc(Number(limit || 0)));
  const keep = [...pages];
  while (keep.length > normalizedLimit) {
    const removable = keep
      .filter((page) => page.key !== activeKey && !page.dirty)
      .sort((a, b) => Number(a.last_active_at || 0) - Number(b.last_active_at || 0))[0];
    if (!removable) break;
    const index = keep.findIndex((page) => page.key === removable.key);
    if (index < 0) break;
    keep.splice(index, 1);
  }
  return keep;
}
