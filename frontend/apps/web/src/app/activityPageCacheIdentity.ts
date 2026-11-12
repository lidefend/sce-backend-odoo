export type ActivityRouteIdentityInput = {
  routeName: string | symbol | null | undefined;
  params?: Record<string, unknown>;
  query?: Record<string, unknown>;
  meta?: { sceneKey?: string } | Record<string, unknown>;
  selectedRecordId?: unknown;
};

function text(value: unknown): string {
  if (Array.isArray(value)) return String(value[0] || '').trim();
  return String(value || '').trim();
}

function positiveInteger(value: unknown): number {
  const parsed = Number(value || 0);
  return Number.isFinite(parsed) && parsed > 0 ? Math.trunc(parsed) : 0;
}

export function activityContextPart(selectedRecordId: unknown): string {
  const id = positiveInteger(selectedRecordId);
  return id > 0 ? `record-context:${id}` : 'all';
}

/** One identity shared by router registration and App's KeepAlive cache key. */
export function resolveActivityRouteKey(input: ActivityRouteIdentityInput): string {
  const routeName = text(input.routeName);
  const params = input.params || {};
  const query = input.query || {};
  const meta = input.meta || {};
  const context = activityContextPart(input.selectedRecordId);
  if (routeName === 'action') {
    const actionId = positiveInteger(params.actionId ?? query.action_id);
    const menuId = positiveInteger(query.menu_id);
    return actionId ? `action:${actionId}:menu:${menuId}:${context}` : '';
  }
  if (routeName === 'record' || routeName === 'model-form') {
    const model = text(params.model);
    const recordId = text(params.id);
    if (!model || !recordId) return '';
    const actionId = positiveInteger(query.action_id);
    const menuId = positiveInteger(query.menu_id);
    const viewId = positiveInteger(query.view_id ?? query.viewId);
    if (recordId === 'new') {
      const activityInstanceId = text(query.activity_page_id);
      return `new:${model}:action:${actionId}:menu:${menuId}:view:${viewId}:${context}:${activityInstanceId || 'route'}`;
    }
    return `record:${model}:${recordId}:action:${actionId}:menu:${menuId}`;
  }
  if (routeName === 'my-work' || routeName === 'scene-my-work') return 'workspace:my-work';
  if (routeName === 'scene' || routeName.startsWith('scene-')) {
    const sceneKey = text(params.sceneKey ?? meta.sceneKey ?? query.scene_key ?? query.scene);
    if (!sceneKey || sceneKey === 'workspace.home') return '';
    return `scene:${sceneKey}:${context}`;
  }
  return '';
}

export function resolveActivityCacheKey(
  input: ActivityRouteIdentityInput,
  epochs: Record<string, number>,
  actorUserId: unknown,
): string {
  const routeKey = resolveActivityRouteKey(input);
  if (!routeKey) return '';
  const epoch = Number(epochs[routeKey] || 0);
  return `activity:user:${positiveInteger(actorUserId)}:${routeKey}:${epoch}`;
}

export function advanceActivityPageCacheEpoch(
  epochs: Record<string, number>,
  routeKey: string,
): Record<string, number> {
  const key = text(routeKey);
  if (!key) return { ...epochs };
  return {
    ...epochs,
    [key]: Number(epochs[key] || 0) + 1,
  };
}
