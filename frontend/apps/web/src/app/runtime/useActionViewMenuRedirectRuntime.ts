import type { LocationQueryRaw, RouteLocationNormalizedLoaded, Router } from 'vue-router';
import type { NavMeta, NavNode } from '@sc/schema';
import { resolveMenuAction } from '../resolvers/menuResolver';
import { getSceneByKey } from '../resolvers/sceneRegistry';
import { buildCanonicalSceneRouteTarget, buildEntryTargetRouteTarget } from '../routeQuery';

type ReadRef<T> = { readonly value: T };

type MenuRedirectSession = {
  menuTree: NavNode[];
  setActionMeta: (meta: NavMeta) => void;
};

export function useActionViewMenuRedirectRuntime(options: {
  actionId: ReadRef<number>;
  menuId: ReadRef<number>;
  route: RouteLocationNormalizedLoaded;
  router: Router;
  session: MenuRedirectSession;
  keepSceneRoute: ReadRef<boolean>;
  resolveMenuCarryQuery: (meta?: Record<string, unknown> | null, extra?: Record<string, unknown>) => LocationQueryRaw;
}) {
  function findMenuNodeByLabel(nodes: Array<Record<string, unknown>>, label: string): Record<string, unknown> | null {
    for (const node of nodes) {
      if (!node || typeof node !== 'object') continue;
      const current = String(node.label || node.title || node.name || '').trim();
      if (current === label) return node;
      const found = findMenuNodeByLabel((node.children as Array<Record<string, unknown>>) || [], label);
      if (found) return found;
    }
    return null;
  }

  async function redirectMenuOnlyRouteIfNeeded(): Promise<boolean> {
    const currentMenuId = Number(options.menuId.value || 0);
    if (Number(options.actionId.value || 0) > 0 || currentMenuId <= 0) {
      return false;
    }
    let result = resolveMenuAction(options.session.menuTree, currentMenuId);
    if (result.kind === 'broken' && result.reason === 'menu not found') {
      const fallbackNode = findMenuNodeByLabel(
        options.session.menuTree as unknown as Array<Record<string, unknown>>,
        String(options.route.query.label || ''),
      );
      const fallbackMenuId = Number(fallbackNode?.menu_id || fallbackNode?.id || 0);
      if (fallbackMenuId > 0) {
        result = resolveMenuAction(options.session.menuTree, fallbackMenuId);
      }
    }
    if (result.kind === 'leaf') {
      const entryTarget = result.meta?.entry_target && typeof result.meta.entry_target === 'object'
        ? result.meta.entry_target as Record<string, unknown>
        : null;
      const targetActionId = Number(result.meta.action_id || 0);
      if (targetActionId <= 0) return false;
      options.session.setActionMeta(result.meta);
      if (entryTarget) {
        await options.router.replace(buildEntryTargetRouteTarget(entryTarget, {
          query: options.resolveMenuCarryQuery(result.meta),
          menuId: currentMenuId,
          actionId: targetActionId,
          keepSceneRoute: options.keepSceneRoute.value,
          routePath: options.route.path,
        }) as never);
        return true;
      }
      await options.router.replace({
        name: 'action',
        params: { actionId: targetActionId },
        query: options.resolveMenuCarryQuery(result.meta, { menu_id: currentMenuId, action_id: targetActionId }),
      });
      return true;
    }
    if (result.kind === 'redirect') {
      if (result.target.entry_target) {
        await options.router.replace(buildEntryTargetRouteTarget(result.target.entry_target, {
          query: options.resolveMenuCarryQuery(result.target.meta),
          menuId: result.target.menu_id || currentMenuId,
          actionId: result.target.action_id,
          keepSceneRoute: options.keepSceneRoute.value,
          routePath: options.route.path,
        }) as never);
        return true;
      }
      if (result.target.scene_key) {
        const sceneKey = String(result.target.scene_key || '').trim();
        await options.router.replace(buildCanonicalSceneRouteTarget(sceneKey, {
          scene: getSceneByKey(sceneKey),
          query: options.resolveMenuCarryQuery(result.target.meta),
          menuId: result.target.menu_id || currentMenuId,
          actionId: result.target.action_id,
        }));
        return true;
      }
      const targetActionId = Number(result.target.action_id || 0);
      if (targetActionId > 0) {
        if (result.target.meta) {
          options.session.setActionMeta(result.target.meta);
        }
        await options.router.replace({
          name: 'action',
          params: { actionId: targetActionId },
          query: options.resolveMenuCarryQuery(result.target.meta, {
            menu_id: result.target.menu_id || currentMenuId,
            action_id: targetActionId,
          }),
        });
        return true;
      }
    }
    return false;
  }

  return { redirectMenuOnlyRouteIfNeeded };
}
