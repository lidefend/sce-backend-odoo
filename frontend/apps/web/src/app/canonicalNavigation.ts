import type {
  CanonicalNavigationModel,
  CanonicalNavigationNode,
  CanonicalNavigationParent,
  NavNode,
} from '@sc/schema';
import type { RouteAuthorityContract, RouteAuthorityEntry } from './routeAuthority';
import { routeAuthorityEntries } from './routeAuthority';

type UnknownRecord = Record<string, unknown>;

export class CanonicalNavigationError extends Error {
  constructor(public readonly code: string, message: string) {
    super(message);
    this.name = 'CanonicalNavigationError';
  }
}

function record(value: unknown): UnknownRecord {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as UnknownRecord : {};
}

function text(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

function positiveInteger(value: unknown): number {
  const parsed = Number(value || 0);
  return Number.isFinite(parsed) && parsed > 0 ? Math.trunc(parsed) : 0;
}

function nodeMenuId(node: NavNode): number {
  return positiveInteger(node.menu_id || node.id || node.meta?.menu_id);
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

function nodeMeta(node: NavNode): UnknownRecord {
  return record(node.meta);
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

function explicitDisabledReason(node: NavNode): string {
  const raw = node as NavNode & { disabled_reason?: unknown };
  return text(raw.disabled_reason || nodeMeta(node).disabled_reason);
}

function explicitDisabled(node: NavNode): boolean {
  const raw = node as NavNode & {
    is_clickable?: unknown;
    availability_status?: unknown;
    state?: unknown;
  };
  const meta = nodeMeta(node);
  const status = text(raw.availability_status || meta.availability_status || raw.state || meta.state).toLowerCase();
  return raw.is_clickable === false || meta.is_clickable === false || ['disabled', 'blocked', 'unavailable', 'denied'].includes(status);
}

function buildNodes(
  source: NavNode[],
  authorityByPair: Map<string, RouteAuthorityEntry>,
  parentChain: CanonicalNavigationParent[],
): CanonicalNavigationNode[] {
  return source.map((node, index) => {
    const menuId = nodeMenuId(node);
    const actionId = nodeActionId(node);
    const label = nodeLabel(node);
    const key = nodeKey(node, menuId);
    if (!menuId || !key || !label) {
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

    const nextParent: CanonicalNavigationParent = { key, menuId, label };
    const children = buildNodes(node.children || [], authorityByPair, [...parentChain, nextParent]);
    const disabledReason = explicitDisabledReason(node);
    const disabled = explicitDisabled(node);
    if (disabled && !disabledReason) {
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

    const state = disabled ? 'disabled' : actionId ? 'enabled' : 'container';
    const raw = node as NavNode & { icon?: unknown };
    return {
      key,
      menuId,
      actionId: actionId || null,
      parentChain,
      label,
      icon: text(raw.icon || node.meta?.icon) || null,
      route: authority ? text(authority.route) || null : null,
      authority: authority
        ? { state: 'allowed', source: authority.source, key: authorityKey(authority) }
        : { state: 'container', source: 'system.init.navigation.nav', key: `container:${menuId}` },
      state,
      disabledReason: disabledReason || null,
      order: Number.isFinite(Number(node.sequence)) ? Number(node.sequence) : index,
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
  return {
    schemaVersion: '1.0',
    source: 'system.init.navigation',
    principal: {
      userId: routeAuthority.principal_scope.user_id,
      companyId: routeAuthority.principal_scope.company_id,
      roleCode: routeAuthority.principal_scope.role_code,
    },
    nodes: buildNodes(nav, authorityIndex(routeAuthority), []),
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
