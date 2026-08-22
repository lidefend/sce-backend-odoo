import type { RouteLocationRaw, RouteRecordNormalized } from 'vue-router';

export interface BusinessTarget {
  route?: string;
  scene_key?: string;
  model?: string;
  record_id?: number | string;
  action_id?: number | string;
  menu_id?: number | string;
  mode?: 'view' | 'edit' | 'create' | string;
}

function positiveInteger(value: unknown) {
  const parsed = Number(value || 0);
  return Number.isFinite(parsed) && parsed > 0 ? Math.trunc(parsed) : 0;
}

function queryContext(target: BusinessTarget) {
  const query: Record<string, string> = {};
  const actionId = positiveInteger(target.action_id);
  const menuId = positiveInteger(target.menu_id);
  if (actionId) query.action_id = String(actionId);
  if (menuId) query.menu_id = String(menuId);
  return query;
}

export function resolveBusinessTarget(
  target: BusinessTarget | null | undefined,
  routes: RouteRecordNormalized[] = [],
): RouteLocationRaw | null {
  if (!target) return null;
  const query = queryContext(target);
  const directRoute = String(target.route || '').trim();
  if (directRoute.startsWith('/')) return { path: directRoute, query };

  const sceneKey = String(target.scene_key || '').trim();
  if (sceneKey) return { name: 'SceneRuntimePage', params: { sceneKey }, query };

  const model = String(target.model || '').trim();
  const recordId = positiveInteger(target.record_id);
  if (model && (recordId || target.mode === 'create')) {
    return {
      name: target.mode === 'edit' || target.mode === 'create' ? 'OdooRecordForm' : 'OdooRecordDetail',
      params: { model, id: target.mode === 'create' ? 'new' : String(recordId) },
      query,
    };
  }

  const actionId = positiveInteger(target.action_id);
  const menuId = positiveInteger(target.menu_id);
  const matched = routes.find((route) => {
    const metaActionId = positiveInteger(route.meta.actionId);
    const metaMenuId = positiveInteger(route.meta.menuId);
    return (
      (actionId && metaActionId === actionId && (!menuId || metaMenuId === menuId)) ||
      (!actionId && menuId && metaMenuId === menuId)
    );
  });
  return matched ? { name: matched.name, query } : null;
}
