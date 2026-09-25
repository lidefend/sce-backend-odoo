export type ActivityQuery = Record<string, unknown>;

export interface CreateFormActivityRedirect {
  name: unknown;
  params: unknown;
  query: ActivityQuery;
  hash: unknown;
}

function queryText(value: unknown): string {
  if (Array.isArray(value)) return String(value[0] ?? '').trim();
  return String(value ?? '').trim();
}

function isCreateFormRouteName(routeName: unknown): boolean {
  return routeName === 'record' || routeName === 'model-form';
}

/**
 * Create-form activity identity injection.
 *
 * The returned redirect deliberately carries no `replace` flag. The caller must
 * keep the navigation mode it received: a user-initiated create stays a push so
 * the collection entry it started from survives in history, and only an
 * already-replacing navigation (entry carrier, first load) collapses entries.
 * Forcing `replace` here is what previously made a record form's own return
 * action skip its source collection.
 */
export function resolveCreateFormActivityRedirect(params: {
  routeName: unknown;
  routeParams: Record<string, unknown> | null | undefined;
  query: unknown;
  hash: unknown;
  createActivityInstanceId: () => string;
}): CreateFormActivityRedirect | null {
  if (!isCreateFormRouteName(params.routeName)) return null;
  const routeParams = params.routeParams && typeof params.routeParams === 'object' ? params.routeParams : {};
  if (queryText(routeParams.id) !== 'new') return null;
  const query = params.query && typeof params.query === 'object' ? params.query as ActivityQuery : {};
  if (queryText(query.activity_page_id)) return null;
  return {
    name: params.routeName,
    params: params.routeParams,
    query: { ...query, activity_page_id: params.createActivityInstanceId() },
    hash: params.hash,
  };
}
