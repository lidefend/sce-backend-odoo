export function normalizeFormRouteOwnerIdentity(input: {
  routeName: unknown;
  model: unknown;
  recordId: unknown;
  activityPageId?: unknown;
  actionId?: unknown;
  menuId?: unknown;
  viewId?: unknown;
  sceneKey?: unknown;
}): string {
  const routeName = String(input.routeName || '').trim();
  const model = String(input.model || '').trim();
  const recordId = String(input.recordId || '').trim();
  const sceneKey = String(input.sceneKey || '').trim();
  if (routeName === 'scene') return sceneKey ? `scene:${sceneKey}` : '';
  if (!['record', 'model-form'].includes(routeName) || !model || !recordId) return '';
  if (recordId !== 'new') return `record:${model}:${recordId}`;
  const activityPageId = String(input.activityPageId || '').trim();
  if (activityPageId) return `new:${model}:page:${activityPageId}`;
  const actionId = Number(input.actionId || 0) || 0;
  const menuId = Number(input.menuId || 0) || 0;
  const viewId = Number(input.viewId || 0) || 0;
  return `new:${model}:action:${actionId}:menu:${menuId}:view:${viewId}`;
}

export function formRouteInstanceOwnsRoute(instanceIdentity: string, routeIdentity: string): boolean {
  const instance = String(instanceIdentity || '').trim();
  const route = String(routeIdentity || '').trim();
  return Boolean(route) && (!instance || instance === route);
}
