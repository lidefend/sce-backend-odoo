export type ListGroupPage = {
  count: number;
  pageOffset?: number;
  pageLimit?: number;
  pageCurrent?: number;
  pageTotal?: number;
  pageRangeStart?: number;
  pageRangeEnd?: number;
  pageWindow?: { start?: unknown; end?: unknown };
  pageHasPrev?: boolean;
  pageHasNext?: boolean;
};

export function resolveListGroupPageLimit(group: Pick<ListGroupPage, 'pageLimit'>, fallbackLimit: number) {
  const limitRaw = Number(group.pageLimit || fallbackLimit);
  return Number.isFinite(limitRaw) && limitRaw > 0 ? Math.trunc(limitRaw) : 3;
}

export function resolveListGroupPageOffset(
  group: Pick<ListGroupPage, 'count' | 'pageOffset' | 'pageLimit'>,
  fallbackLimit: number,
) {
  const limit = resolveListGroupPageLimit(group, fallbackLimit);
  const maxOffset = Math.max(0, Number(group.count || 0) - limit);
  const offsetRaw = Number(group.pageOffset || 0);
  if (!Number.isFinite(offsetRaw)) return 0;
  const clamped = Math.min(Math.max(Math.trunc(offsetRaw), 0), maxOffset);
  return Math.floor(clamped / limit) * limit;
}

export function resolveListGroupPageMeta(group: ListGroupPage, fallbackLimit: number) {
  const total = Math.max(0, Number(group.count || 0));
  const limit = Math.max(1, resolveListGroupPageLimit(group, fallbackLimit));
  const offset = resolveListGroupPageOffset(group, fallbackLimit);
  const fallbackTotal = Math.max(1, Math.ceil(total / limit));
  const fallbackCurrent = Math.floor(offset / limit) + 1;
  const fallbackStart = total > 0 ? offset + 1 : 0;
  const fallbackEnd = total > 0 ? Math.min(total, offset + limit) : 0;
  const backendTotal = Math.trunc(Number(group.pageTotal || 0));
  const backendCurrent = Math.trunc(Number(group.pageCurrent || 0));
  const backendStart = Math.trunc(Number(group.pageRangeStart || 0));
  const backendEnd = Math.trunc(Number(group.pageRangeEnd || 0));
  const backendWindowStart = Math.trunc(Number(group.pageWindow?.start || 0));
  const backendWindowEnd = Math.trunc(Number(group.pageWindow?.end || 0));
  return {
    totalPages: backendTotal > 0 ? backendTotal : fallbackTotal,
    currentPage: backendCurrent > 0 ? backendCurrent : fallbackCurrent,
    rangeStart: backendWindowStart > 0 ? backendWindowStart : (backendStart > 0 ? backendStart : fallbackStart),
    rangeEnd: backendWindowEnd > 0 ? backendWindowEnd : (backendEnd > 0 ? backendEnd : fallbackEnd),
  };
}

export function canListGroupPagePrev(group: ListGroupPage, fallbackLimit: number) {
  if (typeof group.pageHasPrev === 'boolean') return group.pageHasPrev;
  return resolveListGroupPageOffset(group, fallbackLimit) > 0;
}

export function canListGroupPageNext(group: ListGroupPage, fallbackLimit: number) {
  if (typeof group.pageHasNext === 'boolean') return group.pageHasNext;
  const offset = resolveListGroupPageOffset(group, fallbackLimit);
  const limit = resolveListGroupPageLimit(group, fallbackLimit);
  return offset + limit < Number(group.count || 0);
}

export function listGroupPageRangeText(group: ListGroupPage, fallbackLimit: number) {
  const total = Math.max(0, Number(group.count || 0));
  if (!total) return '0 / 0';
  const meta = resolveListGroupPageMeta(group, fallbackLimit);
  return `${meta.rangeStart}-${meta.rangeEnd} / ${total}`;
}
