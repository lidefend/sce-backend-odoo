// A one-navigation read receipt. It never enters session route authority or
// action metadata, and return_* query values are provenance, not permission.
type RelationRoute = {
  name: unknown;
  path: string;
  params: Record<string, unknown>;
  query: Record<string, unknown>;
};
type RelationReadRequest = {
  model: string;
  record_id: number;
  action_id: number;
  menu_id: number;
  route_path: string;
  access_mode: 'read';
  render_profile: 'readonly';
  relation_origin: { model: string; record_id: number; field: string; action_id: number; menu_id: number };
};

function exactId(value: unknown): number {
  if (typeof value !== 'number' && (typeof value !== 'string' || !/^[1-9]\d*$/.test(value))) return 0;
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : 0;
}
function name(value: unknown, field = false): string {
  return typeof value === 'string' && (field ? /^[a-zA-Z_][\w]*$/ : /^[a-zA-Z_][\w.]*$/).test(value) ? value : '';
}

export function relationReadRouteRequest(route: RelationRoute): RelationReadRequest | null {
  if (route.name !== 'record') return null;
  const model = name(route.params.model), recordId = exactId(route.params.id);
  const actionId = exactId(route.query.action_id), menuId = exactId(route.query.menu_id);
  const origin = { model: name(route.query.return_model), record_id: exactId(route.query.return_record_id),
    field: name(route.query.return_field, true), action_id: exactId(route.query.return_action_id),
    menu_id: exactId(route.query.return_menu_id) };
  if (!model || !recordId || !actionId || !menuId || route.path !== `/r/${model}/${recordId}`
    || !origin.model || !origin.record_id || !origin.field || !origin.action_id || !origin.menu_id) return null;
  return { model, record_id: recordId, action_id: actionId, menu_id: menuId, route_path: route.path,
    access_mode: 'read', render_profile: 'readonly', relation_origin: origin };
}

export async function validateRelationReadRoute(
  route: RelationRoute,
  currentScope: () => string,
  request: (params: RelationReadRequest) => Promise<Record<string, unknown>>,
): Promise<boolean> {
  const params = relationReadRouteRequest(route);
  if (!params) return false;
  const scope = currentScope();
  try {
    const receipt = await request(params);
    return currentScope() === scope && receipt.allowed === true
      && receipt.model === params.model && receipt.record_id === params.record_id
      && receipt.action_id === params.action_id && receipt.menu_id === params.menu_id
      && receipt.route_path === params.route_path && receipt.access_mode === 'read'
      && receipt.render_profile === 'readonly';
  } catch {
    return false;
  }
}
