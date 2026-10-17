import type { RecordContextContract, RecordContextOption } from '@sc/schema';
import { contractGapError } from './contract/contractGap';

const ROUTE_AUTHORITY_DECLARATION_LAYER = 'P0:smart_core:MenuService.build_route_authority';

export type RouteAuthorityKind = 'PRIMARY_NAV' | 'DISCOVERED_PRIMARY_NAV' | 'ROLE_HOME_ACTION' | 'CONTEXTUAL_ROUTE' | 'ADMIN_ROUTE' | 'DENIED';

export interface RouteAuthorityRecordContextSnapshot {
  selected: RecordContextOption | null;
  company_id: number | null;
  company_name: string;
  operation_strategy: string;
  operation_strategy_label: string;
}

export interface RouteAuthorityEntry {
  action_xmlid: string;
  route_kind: RouteAuthorityKind;
  menu_id: number;
  menu_xmlid: string;
  action_id: number;
  name: string;
  action_name?: string;
  model: string;
  view_modes: string[];
  view_id?: number;
  domain: string;
  context: string;
  route: string;
  scene_key?: string;
  entry_target?: Record<string, unknown>;
  allowed_operation: string;
  required_capability: string;
  context_requirements: Record<string, unknown>;
  source: string;
}

export interface RouteAuthorityContract {
  contract_version: '2.0.0';
  schema_version: '2.0.0';
  source: string;
  principal_scope: { user_id: number; company_id: number; role_code: string };
  primary_actions: RouteAuthorityEntry[];
  role_home_actions: RouteAuthorityEntry[];
  contextual_actions: RouteAuthorityEntry[];
  admin_actions: RouteAuthorityEntry[];
  denied_actions: RouteAuthorityEntry[];
  menu_containers: RouteAuthorityEntry[];
}

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function contractGap(missing: string, message: string): never {
  throw contractGapError(
    { kind: 'contract_defect', missing, requiredDeclarationLayer: ROUTE_AUTHORITY_DECLARATION_LAYER },
    message,
  );
}

function positiveInteger(value: unknown): number {
  const parsed = Number(value || 0);
  return Number.isFinite(parsed) && parsed > 0 ? Math.trunc(parsed) : 0;
}

function normalizeEntry(
  value: unknown,
  expectedKind: RouteAuthorityKind,
  location: string,
  allowContainer = false,
  allowDeclaredTarget = false,
): RouteAuthorityEntry {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    contractGap(location, `${location} 必须是对象：前端不静默丢弃已声明条目`);
  }
  const row = record(value);
  const actionId = positiveInteger(row.action_id);
  const actionXmlid = String(row.action_xmlid || '').trim();
  const menuId = positiveInteger(row.menu_id);
  const menuXmlid = String(row.menu_xmlid || '').trim();
  const menuBoundAction = actionId > 0 && menuId > 0 && Boolean(menuXmlid);
  if (row.entry_target !== undefined && row.entry_target !== null
    && (typeof row.entry_target !== 'object' || Array.isArray(row.entry_target))) {
    contractGap(`${location}.entry_target`, `${location}.entry_target 必须是对象`);
  }
  const entryTarget = record(row.entry_target);
  // A contract-declared target entry (scene / record / url) carries no business
  // action; it is authorized by the same (menu_id, action_id 0) pair the backend
  // ``role_home_actions`` bucket publishes.  Admission stays fail-closed: the
  // entry must declare an explicit entry_target or scene_key.
  const declaredTarget = allowDeclaredTarget
    && menuId > 0
    && (Object.keys(entryTarget).length > 0 || Boolean(String(row.scene_key || '').trim()));
  // A denial record may legitimately name a declared action that does not exist
  // yet (action_id 0 + action_xmlid), or only a menu carrier that was not
  // delivered (action_id 0 + menu_xmlid).  Both stay explicit denial records,
  // never silently dropped entries; a denial with no identity at all is still
  // a contract gap.
  const denialRecord = expectedKind === 'DENIED' && (Boolean(actionXmlid) || Boolean(menuXmlid));
  if (!actionId && !(allowContainer && menuId > 0) && !declaredTarget && !denialRecord) {
    contractGap(`${location}.action_id`, `${location} 未声明 action_id，也不是已声明的目标入口`);
  }
  if (!actionXmlid && !menuBoundAction && !(allowContainer && menuId > 0) && !declaredTarget && !denialRecord) {
    contractGap(`${location}.action_xmlid`, `${location} 缺少 action_xmlid 或 menu_xmlid`);
  }
  if (String(row.route_kind || '') !== expectedKind) {
    contractGap(`${location}.route_kind`, `${location}.route_kind 与所属 bucket 不一致`);
  }
  return {
    action_xmlid: actionXmlid,
    route_kind: expectedKind,
    menu_id: menuId,
    menu_xmlid: menuXmlid,
    action_id: actionId,
    name: String(row.name || '').trim(),
    action_name: String(row.action_name || '').trim() || undefined,
    model: String(row.model || '').trim(),
    view_modes: Array.isArray(row.view_modes) ? row.view_modes.map((item) => String(item || '').trim()).filter(Boolean) : [],
    view_id: positiveInteger(row.view_id) || undefined,
    domain: String(row.domain || '').trim(),
    context: String(row.context || '').trim(),
    route: String(row.route || '').trim(),
    scene_key: String(row.scene_key || '').trim() || undefined,
    entry_target: Object.keys(entryTarget).length ? entryTarget : undefined,
    allowed_operation: String(row.allowed_operation || '').trim(),
    required_capability: String(row.required_capability || '').trim(),
    context_requirements: record(row.context_requirements),
    source: String(row.source || '').trim(),
  };
}

export function normalizeRouteAuthorityContract(value: unknown): RouteAuthorityContract | null {
  if (value === null || value === undefined) return null;
  if (typeof value !== 'object' || Array.isArray(value)) {
    contractGap('route_authority', 'route_authority 必须是对象');
  }
  const row = record(value);
  if (String(row.contract_version || '') !== '2.0.0') {
    contractGap('route_authority.contract_version', 'route_authority.contract_version 必须为 2.0.0');
  }
  if (String(row.schema_version || '') !== '2.0.0') {
    contractGap('route_authority.schema_version', 'route_authority.schema_version 必须为 2.0.0');
  }
  const scope = record(row.principal_scope);
  const userId = positiveInteger(scope.user_id);
  const companyId = positiveInteger(scope.company_id);
  if (!userId) contractGap('route_authority.principal_scope.user_id', 'principal_scope.user_id 必须为正整数');
  if (!companyId) contractGap('route_authority.principal_scope.company_id', 'principal_scope.company_id 必须为正整数');
  const bucket = (key: string): unknown[] => {
    const value = row[key];
    if (value === undefined || value === null) return [];
    if (!Array.isArray(value)) contractGap(`route_authority.${key}`, `route_authority.${key} 必须是数组`);
    return value;
  };
  const normalizeBucket = (key: string, kind: RouteAuthorityKind, allowDeclaredTarget = false) => (
    bucket(key).map((item, index) => normalizeEntry(
      item,
      kind,
      `route_authority.${key}[${index}]`,
      false,
      allowDeclaredTarget,
    ))
  );
  return {
    contract_version: '2.0.0',
    schema_version: '2.0.0',
    source: String(row.source || '').trim(),
    principal_scope: {
      user_id: userId,
      company_id: companyId,
      role_code: String(scope.role_code || '').trim(),
    },
    primary_actions: bucket('primary_actions').map((item, index) => {
      const kind = String(record(item).route_kind || '');
      if (!['PRIMARY_NAV', 'DISCOVERED_PRIMARY_NAV'].includes(kind)) {
        contractGap(`route_authority.primary_actions[${index}].route_kind`, 'primary_actions 条目 route_kind 非法');
      }
      return normalizeEntry(item, kind as RouteAuthorityKind, `route_authority.primary_actions[${index}]`);
    }),
    role_home_actions: normalizeBucket('role_home_actions', 'ROLE_HOME_ACTION', true),
    contextual_actions: normalizeBucket('contextual_actions', 'CONTEXTUAL_ROUTE'),
    admin_actions: normalizeBucket('admin_actions', 'ADMIN_ROUTE'),
    denied_actions: normalizeBucket('denied_actions', 'DENIED'),
    menu_containers: bucket('menu_containers').map((item, index) => {
      const kind = String(record(item).route_kind || '');
      if (!['PRIMARY_NAV', 'DISCOVERED_PRIMARY_NAV', 'ROLE_HOME_ACTION', 'CONTEXTUAL_ROUTE', 'ADMIN_ROUTE'].includes(kind)) {
        contractGap(`route_authority.menu_containers[${index}].route_kind`, 'menu_containers 条目 route_kind 非法');
      }
      return normalizeEntry(item, kind as RouteAuthorityKind, `route_authority.menu_containers[${index}]`, true);
    }),
  };
}

export function routeAuthorityForPrincipal(
  value: unknown,
  expected: { userId: number; companyId: number; roleCode: string },
): RouteAuthorityContract | null {
  const contract = normalizeRouteAuthorityContract(value);
  if (!contract) return null;
  const scope = contract.principal_scope;
  // A principal mismatch is an authorization-scope decision, not a contract
  // shape defect.  Malformed or version-mismatched contracts already threw.
  if (
    scope.user_id !== expected.userId
    || (expected.roleCode && scope.role_code !== expected.roleCode)
    || (expected.companyId > 0 && scope.company_id !== expected.companyId)
  ) return null;
  return contract;
}

export function nextRouteAuthorityRecordContext(
  current: RecordContextContract,
  snapshot: RouteAuthorityRecordContextSnapshot,
): RecordContextContract | null {
  const currentSelectedRecordId = positiveInteger(current.selected?.id);
  const nextSelectedRecordId = positiveInteger(snapshot.selected?.id);
  const currentCompanyId = positiveInteger(current.company_id || current.selected?.company_id);
  const nextCompanyId = positiveInteger(snapshot.company_id || snapshot.selected?.company_id);
  const currentOperation = String(current.operation_strategy || current.selected?.operation_strategy || '').trim();
  const nextOperation = String(snapshot.operation_strategy || snapshot.selected?.operation_strategy || '').trim();
  if (
    currentSelectedRecordId === nextSelectedRecordId
    && currentCompanyId === nextCompanyId
    && currentOperation === nextOperation
  ) return null;
  return {
    ...current,
    selected: snapshot.selected ?? null,
    company_id: nextCompanyId || null,
    company_name: String(snapshot.company_name || snapshot.selected?.company_name || '').trim(),
    operation_strategy: nextOperation,
    operation_strategy_label: String(
      snapshot.operation_strategy_label || snapshot.selected?.operation_strategy_label || '',
    ).trim(),
  };
}

export function routeAuthorityEntries(contract: RouteAuthorityContract | null): RouteAuthorityEntry[] {
  if (!contract) return [];
  return [
    ...contract.primary_actions,
    ...contract.role_home_actions,
    ...contract.contextual_actions,
    ...contract.admin_actions,
    ...contract.menu_containers,
  ];
}

function queryValue(query: Record<string, unknown>, key: string): string {
  const raw = query[key];
  return String(Array.isArray(raw) ? raw[0] || '' : raw || '').trim();
}

export function routeAuthorityContextAllowed(
  entry: RouteAuthorityEntry,
  query: Record<string, unknown>,
  currentScope: { companyId?: number | null; selectedRecordId?: number | null },
): boolean {
  const requirements = entry.context_requirements || {};
  const required = Array.isArray(requirements.required_query)
    ? requirements.required_query.map((item) => String(item || '').trim()).filter(Boolean)
    : [];
  if (required.some((key) => !queryValue(query, key))) return false;
  const companyKey = String(requirements.company_query || '').trim();
  const selectedRecordKey = String(requirements.selected_record_query || '').trim();
  const recordKey = String(requirements.record_query || '').trim();
  if (companyKey && currentScope.companyId && positiveInteger(queryValue(query, companyKey)) !== currentScope.companyId) return false;
  if (selectedRecordKey && currentScope.selectedRecordId && positiveInteger(queryValue(query, selectedRecordKey)) !== currentScope.selectedRecordId) return false;
  if (recordKey && !positiveInteger(queryValue(query, recordKey))) return false;
  return true;
}

export function findRouteAuthority(
  contract: RouteAuthorityContract | null,
  input: { actionId: number; menuId: number; query: Record<string, unknown>; companyId?: number | null; selectedRecordId?: number | null },
): RouteAuthorityEntry | null {
  const entry = routeAuthorityEntries(contract).find((row) => (
    (input.actionId > 0 ? row.action_id === input.actionId : input.menuId > 0 && row.menu_id === input.menuId)
    && (input.menuId <= 0 || row.menu_id === input.menuId)
    && (input.menuId > 0 || input.actionId <= 0 || row.menu_id === 0 || row.route_kind === 'CONTEXTUAL_ROUTE')
  ));
  return entry && routeAuthorityContextAllowed(entry, input.query, input) ? entry : null;
}

/**
 * Decide whether a login-return target may be proposed to the router.
 *
 * The session-expired recovery and the 401 redirect replay a path the user had
 * open before the session ended. The router guard denies any authority-bound
 * route that is absent from the *current* released route authority, so replaying
 * such a target straight after login drops the user onto the access-denied page.
 * This consumes the same contract authority the guard consumes: an authority-bound
 * action/form target must resolve in the current surface. Record routes (/r/) keep
 * the guard's relation-read intent path and are never decided here.
 */
export function authorityBoundTargetResolvable(
  contract: RouteAuthorityContract | null,
  target: string,
  scope: { companyId?: number | null; selectedRecordId?: number | null } = {},
): boolean {
  const raw = String(target || '').trim();
  if (!raw) return false;
  let parsed: URL;
  try {
    parsed = new URL(raw, 'https://sce.invalid');
  } catch {
    return false;
  }
  const pathname = parsed.pathname;
  if (!/^\/(a|f)(\/|$)/.test(pathname)) return true;
  const query: Record<string, unknown> = {};
  parsed.searchParams.forEach((value, key) => { query[key] = value; });
  const pathActionId = /^\/a\/(\d+)(?:\/|$)/.exec(pathname);
  const actionId = Number(pathActionId?.[1] || query.action_id || 0);
  const menuId = Number(query.menu_id || 0);
  if (!(actionId > 0 || menuId > 0)) return true;
  return Boolean(findRouteAuthority(contract, {
    actionId: Number.isFinite(actionId) ? actionId : 0,
    menuId: Number.isFinite(menuId) ? menuId : 0,
    query,
    companyId: scope.companyId ?? null,
    selectedRecordId: scope.selectedRecordId ?? null,
  }));
}
