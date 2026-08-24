import type {
  CanonicalNavigationModel,
  CanonicalNavigationAuthority,
  CanonicalNavigationNode,
  CanonicalNavigationParent,
  NavNode,
} from '@sc/schema';
import type { RouteAuthorityContract, RouteAuthorityEntry } from './routeAuthority';
import { routeAuthorityEntries } from './routeAuthority';

export class CanonicalNavigationError extends Error {
  constructor(public readonly code: string, message: string) {
    super(message);
    this.name = 'CanonicalNavigationError';
  }
}

function text(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

function positiveInteger(value: unknown): number {
  const parsed = Number(value || 0);
  return Number.isFinite(parsed) && parsed > 0 ? Math.trunc(parsed) : 0;
}

function nodeMenuId(node: NavNode): number {
  const meta = node.meta && typeof node.meta === 'object' ? node.meta : {};
  const raw = node as NavNode & {
    config_menu_id?: unknown;
    config_ref?: { model?: unknown; id?: unknown };
    synthetic?: unknown;
  };
  const metaConfigRef = meta.config_ref && typeof meta.config_ref === 'object'
    ? meta.config_ref as { model?: unknown; id?: unknown }
    : {};
  const configRef = raw.config_ref && typeof raw.config_ref === 'object' ? raw.config_ref : metaConfigRef;
  const configuredMenuId = positiveInteger(
    raw.config_menu_id
    || meta.config_menu_id
    || (text(configRef.model || 'ir.ui.menu') === 'ir.ui.menu' ? configRef.id : 0),
  );
  if (configuredMenuId) return configuredMenuId;
  if (raw.synthetic === true || meta.synthetic === true) return 0;
  return positiveInteger(node.menu_id || node.id || meta.menu_id);
}

function nodeActionId(node: NavNode): number {
  const raw = node as NavNode & { action_id?: unknown; actionId?: unknown; native_action_id?: unknown };
  return positiveInteger(raw.action_id || raw.actionId || raw.native_action_id || node.meta?.action_id);
}

function nodeLabel(node: NavNode): string {
  return text(node.title || node.label || node.name).replace(/\s*\(\d+\)\s*$/g, '');
}

function nodeKey(node: NavNode, menuId: number): string {
  return text(node.xmlid || node.xml_id || node.key) || (menuId ? `menu_${menuId}` : '');
}

function authorityKey(entry: RouteAuthorityEntry): string {
  return [entry.route_kind, entry.menu_xmlid || entry.menu_id, entry.action_xmlid || entry.action_id].join(':');
}

function authorityIndex(contract: RouteAuthorityContract): Map<string, RouteAuthorityEntry> {
  const result = new Map<string, RouteAuthorityEntry>();
  for (const entry of routeAuthorityEntries(contract)) {
    if (entry.menu_id > 0 && entry.action_id > 0) {
      result.set(`${entry.menu_id}:${entry.action_id}`, entry);
    }
  }
  return result;
}

function buildNodes(
  source: NavNode[],
  authorityByPair: Map<string, RouteAuthorityEntry>,
  parentChain: CanonicalNavigationParent[],
): CanonicalNavigationNode[] {
  return source.map((node, index) => {
    const carrier = node.canonical_navigation;
    if (!carrier || carrier.schema_version !== '1.0') {
      throw new CanonicalNavigationError(
        'CANONICAL_NAVIGATION_CARRIER_MISSING',
        'navigation node requires the server-owned canonical_navigation v1 carrier',
      );
    }
    const menuId = nodeMenuId(node);
    const actionId = nodeActionId(node);
    const label = nodeLabel(node);
    const key = nodeKey(node, menuId);
    if (!key || !label || (actionId > 0 && !menuId)) {
      throw new CanonicalNavigationError(
        'CANONICAL_NAVIGATION_NODE_IDENTITY_INVALID',
        `navigation node requires menuId, key and label (key=${key || 'missing'})`,
      );
    }

    const authority = actionId ? authorityByPair.get(`${menuId}:${actionId}`) : undefined;
    if (actionId && !authority) {
      throw new CanonicalNavigationError(
        'CANONICAL_NAVIGATION_AUTHORITY_MISSING',
        `navigation action lacks exact menu/action authority (${menuId}/${actionId})`,
      );
    }

    const carrierParents = carrier.parent_chain.map((parent) => ({
      key: text(parent.key),
      menuId: positiveInteger(parent.menu_id) || null,
      label: text(parent.label),
    }));
    const expectedIdentity = {
      key,
      menuId: menuId || null,
      actionId: actionId || null,
      label,
      parentChain,
    };
    const actualIdentity = {
      key: text(carrier.key),
      menuId: positiveInteger(carrier.menu_id) || null,
      actionId: positiveInteger(carrier.action_id) || null,
      label: text(carrier.label),
      parentChain: carrierParents,
    };
    if (JSON.stringify(actualIdentity) !== JSON.stringify(expectedIdentity)) {
      throw new CanonicalNavigationError(
        'CANONICAL_NAVIGATION_CARRIER_IDENTITY_MISMATCH',
        `canonical navigation carrier does not match its tree identity (${key})`,
      );
    }

    const nextParent: CanonicalNavigationParent = { key, menuId: menuId || null, label };
    const children = buildNodes(node.children || [], authorityByPair, [...parentChain, nextParent]);
    const disabledReason = text(carrier.disabled_reason);
    if (carrier.state === 'disabled' && !disabledReason) {
      throw new CanonicalNavigationError(
        'CANONICAL_NAVIGATION_DISABLED_REASON_MISSING',
        `disabled navigation node requires a backend reason (${menuId})`,
      );
    }
    if (!actionId && !children.length) {
      throw new CanonicalNavigationError(
        'CANONICAL_NAVIGATION_EMPTY_NODE',
        `navigation node has neither an authorized target nor children (${menuId})`,
      );
    }

    const expectedState = actionId ? 'enabled' : 'container';
    if (carrier.state !== 'disabled' && carrier.state !== expectedState) {
      throw new CanonicalNavigationError(
        'CANONICAL_NAVIGATION_STATE_MISMATCH',
        `canonical navigation state conflicts with its target identity (${key})`,
      );
    }
    const expectedAuthority: CanonicalNavigationAuthority = authority
      ? { state: 'allowed', source: authority.source, key: authorityKey(authority) }
      : { state: 'container', source: 'system.init.navigation.nav', key: `container:${menuId || key}` };
    if (JSON.stringify(carrier.authority) !== JSON.stringify(expectedAuthority)) {
      throw new CanonicalNavigationError(
        'CANONICAL_NAVIGATION_AUTHORITY_MISMATCH',
        `canonical navigation carrier authority conflicts with route authority (${key})`,
      );
    }
    const expectedRoute = authority ? text(authority.route) || null : null;
    if ((text(carrier.route) || null) !== expectedRoute) {
      throw new CanonicalNavigationError(
        'CANONICAL_NAVIGATION_ROUTE_MISMATCH',
        `canonical navigation route conflicts with route authority (${key})`,
      );
    }
    return {
      key,
      menuId: menuId || null,
      actionId: actionId || null,
      parentChain,
      label,
      icon: text(carrier.icon) || null,
      route: expectedRoute,
      authority: expectedAuthority,
      state: carrier.state,
      disabledReason: disabledReason || null,
      order: Number.isFinite(Number(carrier.order)) ? Number(carrier.order) : index,
      source: node,
      children,
    } satisfies CanonicalNavigationNode;
  });
}

export function createCanonicalNavigationModel(
  nav: NavNode[],
  routeAuthority: RouteAuthorityContract,
): CanonicalNavigationModel {
  if (!routeAuthority?.principal_scope?.user_id) {
    throw new CanonicalNavigationError(
      'CANONICAL_NAVIGATION_PRINCIPAL_MISSING',
      'navigation requires an authenticated route-authority principal',
    );
  }
  const nodes = buildNodes(nav, authorityIndex(routeAuthority), []);
  const keys = new Set<string>();
  const menuIds = new Set<number>();
  const visit = (items: CanonicalNavigationNode[]) => {
    for (const node of items) {
      if (keys.has(node.key) || (node.menuId !== null && menuIds.has(node.menuId))) {
        throw new CanonicalNavigationError(
          'CANONICAL_NAVIGATION_IDENTITY_DUPLICATED',
          `canonical navigation identity must be unique (${node.key})`,
        );
      }
      keys.add(node.key);
      if (node.menuId !== null) menuIds.add(node.menuId);
      visit(node.children);
    }
  };
  visit(nodes);
  return {
    schemaVersion: '1.0',
    source: 'system.init.navigation',
    principal: {
      userId: routeAuthority.principal_scope.user_id,
      companyId: routeAuthority.principal_scope.company_id,
      roleCode: routeAuthority.principal_scope.role_code,
    },
    nodes,
  };
}

export function canonicalNavigationNodeByMenuId(
  nodes: CanonicalNavigationNode[],
  menuId: number,
): CanonicalNavigationNode | null {
  for (const node of nodes) {
    if (node.menuId === menuId) return node;
    const child = canonicalNavigationNodeByMenuId(node.children, menuId);
    if (child) return child;
  }
  return null;
}
