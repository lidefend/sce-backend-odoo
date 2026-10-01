import type { NavMeta } from '@sc/schema';
import { routeAuthorityContextAllowed, routeAuthorityEntries, type RouteAuthorityContract } from '../app/routeAuthority';
import { BUSINESS_CONFIG_MODELS, MENU_CONFIG_POLICY_MODEL } from '../app/businessConfigBoundaries';

function contextValue(action: NavMeta | null | undefined, key: string): string {
  const context = action?.context;
  if (context && typeof context === 'object' && !Array.isArray(context)) {
    return String((context as Record<string, unknown>)[key] || '').trim();
  }
  if (typeof context === 'string') {
    const escaped = key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const match = context.match(new RegExp(`['"]${escaped}['"]\\s*:\\s*['"]([^'"]+)['"]`));
    return String(match?.[1] || '').trim();
  }
  return '';
}

export function isMenuConfigurationAction(action: NavMeta | null | undefined) {
  const model = String(action?.model || action?.res_model || '').trim();
  return model === MENU_CONFIG_POLICY_MODEL;
}

export function resolveActionWebRoute(action: NavMeta | null | undefined): string {
  const entryTarget = action?.entry_target && typeof action.entry_target === 'object' && !Array.isArray(action.entry_target)
    ? action.entry_target as Record<string, unknown>
    : {};
  const entryRoute = String(entryTarget.route || '').trim();
  if (entryRoute.startsWith('/admin/')) return entryRoute;

  const context = action?.context;
  if (context && typeof context === 'object' && !Array.isArray(context)) {
    const route = contextValue(action, 'sc_web_route');
    return route.startsWith('/admin/') ? route : '';
  }
  if (typeof context === 'string') {
    const route = contextValue(action, 'sc_web_route');
    return route.startsWith('/admin/') ? route : '';
  }
  return '';
}

export function resolveActionWebRouteQuery(action: NavMeta | null | undefined): Record<string, string> {
  const rootMenuXmlid = contextValue(action, 'business_config_root_menu_xmlid');
  if (rootMenuXmlid) return { root_menu_xmlid: rootMenuXmlid };
  return {};
}

export function isBusinessConfigurationAction(action: NavMeta | null | undefined) {
  const model = String(action?.model || action?.res_model || '').trim();
  const route = resolveActionWebRoute(action);
  return route === '/admin/business-config'
    || model === BUSINESS_CONFIG_MODELS.contract;
}

/** Use only after the backend route authority and context checks succeed. */
export function resolveAuthorizedConfigurationRoute(options: {
  routeName: string;
  routeModel?: string;
  authority: NavMeta | null;
  authorized: boolean;
  query: Record<string, unknown>;
}) {
  const { authority, routeName } = options;
  if (!options.authorized || !authority || !['menu', 'action', 'record', 'model-form'].includes(routeName)) return null;
  if (!isBusinessConfigurationAction(authority)) return null;
  const model = String(authority.model || authority.res_model || '');
  if (['record', 'model-form'].includes(routeName) && options.routeModel !== model) return null;
  const query: Record<string, unknown> = { ...options.query, ...resolveActionWebRouteQuery(authority),
    action_id: String(authority.action_id), menu_id: String(authority.menu_id || options.query.menu_id || '') };
  // A raw-record instance is not a configuration-workbench activity instance.
  delete query.activity_page_id;
  return { path: resolveActionWebRoute(authority) || '/admin/business-config', query, replace: true };
}

/** Allow contract loading without a menu; this does not authorize record access. */
export function isRecordWorkItemNavigation(routeName: unknown, params: Record<string, unknown>, query: Record<string, unknown>): boolean {
  return ['record', 'model-form'].includes(String(routeName || ''))
    && typeof params.model === 'string' && /^[a-z][a-z0-9_.]*$/.test(params.model)
    && /^[1-9]\d*$/.test(String(params.id || ''))
    && query.work_item_source === 'tier.review'
    && /^[1-9]\d*$/.test(String(query.work_item_id || ''));
}

/** Shell mounting only; a scene declaration does not grant publication or data access.
 * Contextual entries needing fresh server validation remain on the action route.
 */
export function isAuthorizedSceneNavigation(options: {
  routeName: unknown;
  sceneKey: unknown;
  authority: RouteAuthorityContract | null;
  query: Record<string, unknown>;
  companyId?: number | null;
  selectedRecordId?: number | null;
}): boolean {
  if (options.routeName !== 'scene' || typeof options.sceneKey !== 'string' || !options.sceneKey.trim()) return false;
  const key = options.sceneKey;
  return routeAuthorityEntries(options.authority).some((entry) => {
    if (entry.action_id <= 0 || !['read', 'write'].includes(entry.allowed_operation)) return false;
    const requirements = entry.context_requirements || {};
    if ((Array.isArray(requirements.required_query) && requirements.required_query.length > 0)
      || requirements.record_query || requirements.selected_record_query) return false;
    const declaredKey = entry.scene_key || entry.entry_target?.scene_key;
    if (declaredKey !== key && entry.route !== `/s/${key}`) return false;
    // A conflicting declared identity must never be rescued by a matching URL.
    if (declaredKey && declaredKey !== key) return false;
    if (options.query.action_id && String(options.query.action_id) !== String(entry.action_id)) return false;
    if (options.query.menu_id && String(options.query.menu_id) !== String(entry.menu_id)) return false;
    return routeAuthorityContextAllowed(entry, options.query, options);
  });
}
