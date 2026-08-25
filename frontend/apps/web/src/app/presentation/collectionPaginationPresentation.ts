export type CollectionPaginationMode = 'count' | 'grouped' | 'paged';

export function resolveCollectionPaginationMode(input: {
  groupedWindow: boolean;
  paged: boolean;
}): CollectionPaginationMode {
  if (input.groupedWindow) return 'grouped';
  if (input.paged) return 'paged';
  return 'count';
}

function wholeNumber(value: unknown, fallback: number): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? Math.trunc(parsed) : fallback;
}

export function resolveCollectionPageOffset(input: {
  requestedOffset: unknown;
  total: unknown;
  limit: unknown;
}): number {
  const total = Math.max(0, wholeNumber(input.total, 0));
  const limit = Math.max(1, wholeNumber(input.limit, 1));
  const maximum = total > 0 ? Math.floor((total - 1) / limit) * limit : 0;
  return Math.min(Math.max(wholeNumber(input.requestedOffset, 0), 0), maximum);
}

export function resolveCollectionPageJump(input: {
  requestedPage: unknown;
  currentPage: unknown;
  totalPages: unknown;
  limit: unknown;
  total: unknown;
}): { page: number; offset: number } {
  const totalPages = Math.max(1, wholeNumber(input.totalPages, 1));
  const currentPage = Math.min(Math.max(wholeNumber(input.currentPage, 1), 1), totalPages);
  const requested = wholeNumber(input.requestedPage, currentPage);
  const page = Math.min(Math.max(requested, 1), totalPages);
  return {
    page,
    offset: resolveCollectionPageOffset({
      requestedOffset: (page - 1) * Math.max(1, wholeNumber(input.limit, 1)),
      total: input.total,
      limit: input.limit,
    }),
  };
}

export function resolveCollectionPageLimit(value: unknown, currentLimit: unknown): number {
  const fallback = Math.min(Math.max(wholeNumber(currentLimit, 40), 1), 200);
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(Math.max(Math.trunc(parsed), 1), 200);
}
