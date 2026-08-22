export type RouteAuthorityKind =
  'PRIMARY_NAV' | 'DISCOVERED_PRIMARY_NAV' | 'ROLE_HOME_ACTION' | 'CONTEXTUAL_ROUTE' | 'ADMIN_ROUTE' | 'DENIED';

export interface RouteAuthorityEntry {
  route_kind: RouteAuthorityKind;
  menu_id: number;
  action_id: number;
  context_requirements: Record<string, unknown>;
}

export interface RouteAuthorityContract {
  contract_version: 'route_authority.v1';
  principal_scope: { user_id: number; company_id: number; role_code: string };
  primary_actions: RouteAuthorityEntry[];
  role_home_actions: RouteAuthorityEntry[];
  contextual_actions: RouteAuthorityEntry[];
  admin_actions: RouteAuthorityEntry[];
  menu_containers: RouteAuthorityEntry[];
}

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

export function positiveInteger(value: unknown) {
  const parsed = Number(value || 0);
  return Number.isFinite(parsed) && parsed > 0 ? Math.trunc(parsed) : 0;
}

function normalizeEntry(value: unknown): RouteAuthorityEntry | null {
  const row = record(value);
  const routeKind = String(row.route_kind || '') as RouteAuthorityKind;
  if (!routeKind) return null;
  return {
    route_kind: routeKind,
    menu_id: positiveInteger(row.menu_id),
    action_id: positiveInteger(row.action_id),
    context_requirements: record(row.context_requirements),
  };
}

export function normalizeRouteAuthorityContract(value: unknown): RouteAuthorityContract | null {
  const row = record(value);
  if (row.contract_version !== 'route_authority.v1') return null;
  const bucket = (key: string) =>
    (Array.isArray(row[key]) ? row[key] : []).map(normalizeEntry).filter(Boolean) as RouteAuthorityEntry[];
  const scope = record(row.principal_scope);
  return {
    contract_version: 'route_authority.v1',
    principal_scope: {
      user_id: positiveInteger(scope.user_id),
      company_id: positiveInteger(scope.company_id),
      role_code: String(scope.role_code || ''),
    },
    primary_actions: bucket('primary_actions'),
    role_home_actions: bucket('role_home_actions'),
    contextual_actions: bucket('contextual_actions'),
    admin_actions: bucket('admin_actions'),
    menu_containers: bucket('menu_containers'),
  };
}

export function routeAuthorityEntries(contract: RouteAuthorityContract | null) {
  if (!contract) return [];
  return [
    ...contract.primary_actions,
    ...contract.role_home_actions,
    ...contract.contextual_actions,
    ...contract.admin_actions,
    ...contract.menu_containers,
  ];
}

function queryValue(query: Record<string, unknown>, key: string) {
  const raw = query[key];
  return String(Array.isArray(raw) ? raw[0] || '' : raw || '').trim();
}

export function findRouteAuthority(
  contract: RouteAuthorityContract | null,
  input: {
    actionId: number;
    menuId: number;
    query: Record<string, unknown>;
    companyId?: number | null;
    selectedRecordId?: number | null;
  },
) {
  const entry = routeAuthorityEntries(contract).find(
    (row) =>
      (input.actionId ? row.action_id === input.actionId : Boolean(input.menuId) && row.menu_id === input.menuId) &&
      (!input.menuId || row.menu_id === input.menuId),
  );
  if (!entry) return null;
  const requirements = entry.context_requirements;
  const required = Array.isArray(requirements.required_query) ? requirements.required_query.map(String) : [];
  if (required.some((key) => !queryValue(input.query, key))) return null;
  const companyKey = String(requirements.company_query || '');
  const recordKey = String(requirements.selected_record_query || requirements.record_query || '');
  if (companyKey && input.companyId && positiveInteger(queryValue(input.query, companyKey)) !== input.companyId)
    return null;
  if (
    recordKey &&
    input.selectedRecordId &&
    positiveInteger(queryValue(input.query, recordKey)) !== input.selectedRecordId
  ) {
    return null;
  }
  return entry;
}

export function routeAuthorityValidationParams(
  authority: RouteAuthorityEntry,
  query: Record<string, unknown>,
): Record<string, unknown> {
  const requirements = authority.context_requirements;
  const contextKeys = new Set<string>(
    (Array.isArray(requirements.required_query) ? requirements.required_query : []).map(String),
  );
  ['company_query', 'selected_record_query', 'record_query'].forEach((requirementKey) => {
    const queryKey = String(requirements[requirementKey] || '').trim();
    if (queryKey) contextKeys.add(queryKey);
  });

  return {
    action_id: authority.action_id,
    ...Object.fromEntries(
      [...contextKeys].flatMap((key) => {
        const value = query[key];
        return value === undefined || value === null || value === '' ? [] : [[key, value]];
      }),
    ),
  };
}

export function requiresRuntimeRouteValidation(authority: RouteAuthorityEntry) {
  const requirements = authority.context_requirements;
  return Boolean(
    (Array.isArray(requirements.required_query) && requirements.required_query.length) ||
      String(requirements.company_query || '').trim() ||
      String(requirements.selected_record_query || '').trim() ||
      String(requirements.record_query || '').trim(),
  );
}
