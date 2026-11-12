import type { NavNode } from '@sc/schema';
import { findActionMeta, findMenuNode } from './menu';
import type { SceneTarget } from './resolvers/sceneRegistry';

export interface ResolvedSceneActionTarget {
  actionId: number;
  menuId?: number;
}

export interface SceneActionTargetContext {
  sceneKey?: string;
  menuTree?: NavNode[];
  sceneActionHints?: Record<string, { actionId?: number; menuId?: number }>;
  isSceneContractNav?: boolean;
  routePath?: string;
  routeQuery?: Record<string, unknown>;
  includeSceneHint?: boolean;
  includeSceneNodeFallback?: boolean;
  includeRouteQueryFallback?: boolean;
}

export interface SceneHandlingEntryTargetContext extends SceneActionTargetContext {
  internalAction?: SceneTarget | null;
}

function positiveInteger(value: unknown): number {
  const parsed = Number(value || 0);
  return Number.isFinite(parsed) && parsed > 0 ? Math.trunc(parsed) : 0;
}

function routePathOnly(value: unknown): string {
  const route = String(value || '').trim();
  const queryIndex = route.indexOf('?');
  return queryIndex >= 0 ? route.slice(0, queryIndex) : route;
}

function findActionNodeByMenuXmlid(nodes: NavNode[], menuXmlid: string): NavNode | null {
  const wanted = String(menuXmlid || '').trim();
  if (!wanted) return null;
  const walk = (items: NavNode[]): NavNode | null => {
    for (const node of items) {
      const xmlid = String((node as NavNode & { xmlid?: string }).xmlid || node.meta?.menu_xmlid || '').trim();
      if (xmlid === wanted) return node;
      if (node.children?.length) {
        const found = walk(node.children);
        if (found) return found;
      }
    }
    return null;
  };
  return walk(nodes);
}

function findActionNodeBySceneKey(nodes: NavNode[], sceneKey: string): NavNode | null {
  const wanted = String(sceneKey || '').trim();
  if (!wanted) return null;
  const walk = (items: NavNode[]): NavNode | null => {
    for (const node of items) {
      const nodeSceneKey = String(
        (node as NavNode & { scene_key?: string; sceneKey?: string }).scene_key
          || (node as NavNode & { scene_key?: string; sceneKey?: string }).sceneKey
          || node.meta?.scene_key
          || '',
      ).trim();
      if (nodeSceneKey === wanted && node.meta?.action_id) return node;
      if (node.children?.length) {
        const found = walk(node.children);
        if (found) return found;
      }
    }
    return null;
  };
  return walk(nodes);
}

function findActionNodeByActionXmlid(nodes: NavNode[], actionXmlid: string): NavNode | null {
  const wanted = String(actionXmlid || '').trim();
  if (!wanted) return null;
  const walk = (items: NavNode[]): NavNode | null => {
    for (const node of items) {
      const nodeActionXmlid = String(
        (node as NavNode & { action_xmlid?: string; actionXmlid?: string }).action_xmlid
          || (node as NavNode & { action_xmlid?: string; actionXmlid?: string }).actionXmlid
          || node.meta?.action_xmlid
          || '',
      ).trim();
      if (nodeActionXmlid === wanted && node.meta?.action_id) return node;
      if (node.children?.length) {
        const found = walk(node.children);
        if (found) return found;
      }
    }
    return null;
  };
  return walk(nodes);
}

function findActionNodeByModel(nodes: NavNode[], model: string): NavNode | null {
  const wanted = String(model || '').trim();
  if (!wanted) return null;
  const walk = (items: NavNode[]): NavNode | null => {
    for (const node of items) {
      if (node.meta?.model === wanted && node.meta?.action_id) return node;
      if (node.children?.length) {
        const found = walk(node.children);
        if (found) return found;
      }
    }
    return null;
  };
  return walk(nodes);
}

export function resolveSceneActionTarget(
  target: SceneTarget,
  context: SceneActionTargetContext = {},
): ResolvedSceneActionTarget | null {
  const menuTree = Array.isArray(context.menuTree) ? context.menuTree : [];
  const sceneKey = String(context.sceneKey || '').trim();
  const isSceneContractNav = Boolean(context.isSceneContractNav);
  const actionIsResolvable = (actionId: number) => actionId > 0
    && (!menuTree.length || Boolean(findActionMeta(menuTree, actionId)) || isSceneContractNav);

  // An entry's own declaration is authoritative. A parent scene capability hint
  // is only a default for a target that does not identify its own action.
  const explicitActionId = positiveInteger(target.action_id);
  if (explicitActionId > 0) {
    const targetRoute = String(target.route || '').trim();
    if (sceneKey && routePathOnly(targetRoute) === `/s/${sceneKey}`) {
      return { actionId: explicitActionId, menuId: positiveInteger(target.menu_id) || undefined };
    }
    if (actionIsResolvable(explicitActionId)) {
      return { actionId: explicitActionId, menuId: positiveInteger(target.menu_id) || undefined };
    }
  }

  const targetMenuId = positiveInteger(target.menu_id);
  if (targetMenuId > 0) {
    const menuNode = findMenuNode(menuTree, targetMenuId);
    const actionId = positiveInteger(menuNode?.meta?.action_id);
    if (actionId > 0) {
      return { actionId, menuId: positiveInteger(menuNode?.menu_id || menuNode?.id || targetMenuId) || undefined };
    }
  }

  const menuXmlid = String(target.menu_xmlid || '').trim();
  if (menuXmlid) {
    const menuNode = findActionNodeByMenuXmlid(menuTree, menuXmlid);
    const actionId = positiveInteger(menuNode?.meta?.action_id);
    if (actionId > 0) {
      return { actionId, menuId: positiveInteger(menuNode?.menu_id || menuNode?.id || targetMenuId) || undefined };
    }
  }

  const actionXmlid = String(target.action_xmlid || '').trim();
  if (actionXmlid) {
    const actionNode = findActionNodeByActionXmlid(menuTree, actionXmlid);
    const actionId = positiveInteger(actionNode?.meta?.action_id);
    if (actionId > 0) {
      return { actionId, menuId: positiveInteger(actionNode?.menu_id || actionNode?.id || targetMenuId) || undefined };
    }
  }

  const model = String(target.model || '').trim();
  if (model) {
    const modelNode = findActionNodeByModel(menuTree, model);
    const actionId = positiveInteger(modelNode?.meta?.action_id);
    if (actionId > 0) {
      return { actionId, menuId: positiveInteger(modelNode?.menu_id || modelNode?.id || targetMenuId) || undefined };
    }
  }

  if (context.includeSceneNodeFallback !== false && sceneKey) {
    const sceneNode = findActionNodeBySceneKey(menuTree, sceneKey);
    const actionId = positiveInteger(sceneNode?.meta?.action_id);
    if (actionId > 0) {
      return { actionId, menuId: positiveInteger(sceneNode?.menu_id || sceneNode?.id) || undefined };
    }
  }

  if (context.includeSceneHint !== false && sceneKey) {
    const hinted = context.sceneActionHints?.[sceneKey];
    const hintedActionId = positiveInteger(hinted?.actionId);
    if (actionIsResolvable(hintedActionId)) {
      return {
        actionId: hintedActionId,
        menuId: positiveInteger(hinted?.menuId) || targetMenuId || undefined,
      };
    }
  }

  if (context.includeRouteQueryFallback !== false) {
    const routeActionId = positiveInteger(context.routeQuery?.action_id);
    if (routeActionId > 0) {
      return {
        actionId: routeActionId,
        menuId: positiveInteger(context.routeQuery?.menu_id) || undefined,
      };
    }
  }

  return null;
}

export function resolveSceneHandlingEntryTarget(
  target: SceneTarget,
  context: SceneHandlingEntryTargetContext = {},
): ResolvedSceneActionTarget | null {
  const explicitTarget = resolveSceneActionTarget(target, {
    ...context,
    includeSceneHint: false,
    includeSceneNodeFallback: false,
    includeRouteQueryFallback: false,
  });
  if (explicitTarget) return explicitTarget;

  const internalActionId = positiveInteger(context.internalAction?.action_id);
  if (internalActionId > 0) {
    return {
      actionId: internalActionId,
      menuId: positiveInteger(context.internalAction?.menu_id) || undefined,
    };
  }

  return resolveSceneActionTarget(target, {
    ...context,
    includeSceneHint: true,
    includeSceneNodeFallback: true,
    includeRouteQueryFallback: true,
  });
}
