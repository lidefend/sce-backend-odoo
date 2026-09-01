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

function sameCreateCarrier(left: RetainedActivityPageLike, right: RetainedActivityPageLike): boolean {
  if (String(left.model || '').trim() !== String(right.model || '').trim()) return false;
  const leftMenuId = positiveInteger(left.menu_id);
  const rightMenuId = positiveInteger(right.menu_id);
  if (leftMenuId > 0 || rightMenuId > 0) return leftMenuId > 0 && leftMenuId === rightMenuId;
  const leftActionId = positiveInteger(left.action_id);
  const rightActionId = positiveInteger(right.action_id);
  return leftActionId > 0 && leftActionId === rightActionId;
}

export function isSupersededCleanCreateActivityPage(
  existing: RetainedActivityPageLike,
  incoming: RetainedActivityPageLike,
): boolean {
  if (existing.key === incoming.key || existing.dirty) return false;
  if (existing.kind !== 'record_form' || incoming.kind !== 'record_form') return false;
  if (existing.record_id !== 'new' || incoming.record_id !== 'new') return false;
  if (contextIdentity(existing) !== contextIdentity(incoming)) return false;
  return sameCreateCarrier(existing, incoming);
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

export function dedupeCleanCreateActivityPages<T extends RetainedActivityPageLike>(pages: readonly T[]): T[] {
  return pages.reduce<T[]>((retained, page) => [
    ...retained.filter((existing) => !isSupersededCleanCreateActivityPage(existing, page)),
    page,
  ], []);
}
