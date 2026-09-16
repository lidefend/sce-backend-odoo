import type { NavMeta } from '@sc/schema';
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
  const query = { ...options.query, ...resolveActionWebRouteQuery(authority),
    action_id: String(authority.action_id), menu_id: String(authority.menu_id || options.query.menu_id || '') };
  // A raw-record instance is not a configuration-workbench activity instance.
  delete query.activity_page_id;
  return { path: resolveActionWebRoute(authority) || '/admin/business-config', query, replace: true };
}
