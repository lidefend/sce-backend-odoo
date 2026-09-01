export interface RetainedActivityPageLike {
  key: string;
  route?: string;
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

export function normalizeRetainedActivityPageIdentity<T extends RetainedActivityPageLike>(page: T): T {
  const route = String(page.route || '').trim();
  if (!route) return page;
  let parsed: URL;
  try {
    parsed = new URL(route, 'http://activity.local');
  } catch {
    return page;
  }
  const parts = parsed.pathname.split('/').filter(Boolean).map((part) => decodeURIComponent(part));
  if (parts[0] === 'a' && positiveInteger(parts[1])) {
    return {
      ...page,
      kind: 'menu_action',
      action_id: positiveInteger(parts[1]) || positiveInteger(page.action_id) || undefined,
      menu_id: positiveInteger(parsed.searchParams.get('menu_id')) || positiveInteger(page.menu_id) || undefined,
    };
  }
  if (['f', 'r'].includes(parts[0]) && parts[1] && parts[2]) {
    return {
      ...page,
      kind: 'record_form',
      model: parts[1],
      record_id: parts[2],
      action_id: positiveInteger(parsed.searchParams.get('action_id')) || positiveInteger(page.action_id) || undefined,
      menu_id: positiveInteger(parsed.searchParams.get('menu_id')) || positiveInteger(page.menu_id) || undefined,
    };
  }
  return page;
}

export function isSupersededEntryActionActivityPage(
  existing: RetainedActivityPageLike,
  incoming: RetainedActivityPageLike,
): boolean {
  if (existing.key === incoming.key || existing.dirty) return false;
  if (existing.kind !== 'menu_action' || incoming.kind !== 'record_form') return false;
  if (incoming.record_id !== 'new') return false;
  // A governed entry action is an asynchronous carrier, not a usable page.
  // Once its formal create form exists, retaining another clean carrier for a
  // previous record context only exposes an implementation transition.
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

export function shareActivityPageTitleScope(
  left: RetainedActivityPageLike,
  right: RetainedActivityPageLike,
): boolean {
  if (left.kind !== 'record_form' || right.kind !== 'record_form') return false;
  if (left.record_id !== 'new' || right.record_id !== 'new') return false;
  if (String(left.model || '').trim() !== String(right.model || '').trim()) return false;
  const leftMenuId = positiveInteger(left.menu_id);
  const rightMenuId = positiveInteger(right.menu_id);
  if (leftMenuId > 0 || rightMenuId > 0) {
    return leftMenuId > 0 && leftMenuId === rightMenuId;
  }
  const leftActionId = positiveInteger(left.action_id);
  const rightActionId = positiveInteger(right.action_id);
  return leftActionId > 0 && leftActionId === rightActionId;
}

export function reconcileRestoredActivityPages<T extends RetainedActivityPageLike>(
  pages: readonly T[],
): T[] {
  const formalCreatePages = pages.filter((page) => (
    page.kind === 'record_form' && page.record_id === 'new'
  ));
  return pages.filter((page) => !formalCreatePages.some((incoming) => (
    isSupersededEntryActionActivityPage(page, incoming)
  )));
}

export function activityPageTitleTargetKeys<T extends RetainedActivityPageLike>(
  pages: readonly T[],
  activeKey: string,
): Set<string> {
  const activePage = pages.find((page) => page.key === activeKey);
  if (!activePage) return new Set();
  return new Set(pages
    .filter((page) => page.key === activeKey || shareActivityPageTitleScope(page, activePage))
    .map((page) => page.key));
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
