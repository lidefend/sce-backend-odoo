import { resolveMenuActionCore } from './resolvers/menuResolverCore.js';

function positiveInteger(value) {
  const parsed = Number(value || 0);
  return Number.isFinite(parsed) && parsed > 0 ? Math.trunc(parsed) : 0;
}

function cloneJson(value) {
  if (typeof structuredClone === 'function') return structuredClone(value);
  return JSON.parse(JSON.stringify(value));
}

function deepFreeze(value) {
  if (!value || typeof value !== 'object' || Object.isFrozen(value)) return value;
  Object.values(value).forEach((item) => deepFreeze(item));
  return Object.freeze(value);
}

function authorityEntries(contract) {
  if (!contract || typeof contract !== 'object') return [];
  return [
    ...(Array.isArray(contract.primary_actions) ? contract.primary_actions : []),
    ...(Array.isArray(contract.role_home_actions) ? contract.role_home_actions : []),
    ...(Array.isArray(contract.contextual_actions) ? contract.contextual_actions : []),
    ...(Array.isArray(contract.admin_actions) ? contract.admin_actions : []),
  ];
}

function authorityIdentity(authority) {
  return [
    String(authority?.route_kind || '').trim(),
    String(authority?.menu_xmlid || authority?.menu_id || '').trim(),
    String(authority?.action_xmlid || authority?.action_id || '').trim(),
  ].join(':');
}

/**
 * Freeze one menu click into one menu/action/scene/authority tuple.
 * The caller must navigate from this snapshot only; it must not re-read the
 * current action, active scene, or a newer menu tree while building the route.
 */
export function createNavigationSelectionSnapshot(node, routeAuthority) {
  if (!node || typeof node !== 'object' || !routeAuthority) return null;
  const frozenNode = cloneJson(node);
  const sourceMenuId = positiveInteger(frozenNode.menu_id || frozenNode.id);
  if (!sourceMenuId) return null;
  const resolved = resolveMenuActionCore([frozenNode], sourceMenuId);
  if (!resolved || !['leaf', 'redirect'].includes(resolved.kind)) return null;

  const target = resolved.kind === 'leaf'
    ? { menu_id: sourceMenuId, action_id: resolved.meta?.action_id, meta: resolved.meta, node: resolved.node }
    : resolved.target;
  const menuId = positiveInteger(target?.menu_id);
  const actionId = positiveInteger(target?.action_id || target?.meta?.action_id);
  if (!menuId || !actionId) return null;

  const authority = authorityEntries(routeAuthority).find((entry) => (
    positiveInteger(entry?.menu_id) === menuId
    && positiveInteger(entry?.action_id) === actionId
  ));
  if (!authority) return null;

  const rawEntryTarget = target?.entry_target || target?.meta?.entry_target;
  const entryTarget = rawEntryTarget && typeof rawEntryTarget === 'object'
    ? cloneJson(rawEntryTarget)
    : null;
  const sceneKey = String(target?.scene_key || entryTarget?.scene_key || '').trim();
  const meta = cloneJson(target?.meta || {});
  meta.action_id = actionId;
  meta.menu_id = menuId;

  return deepFreeze({
    sourceMenuId,
    menuId,
    actionId,
    sceneKey,
    entryTarget,
    meta,
    authority: cloneJson(authority),
    authorityKey: authorityIdentity(authority),
    targetKind: entryTarget ? 'entry_target' : sceneKey ? 'scene' : 'action',
  });
}
