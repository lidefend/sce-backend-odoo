import type { NavMeta } from '@sc/schema';
import { routeAuthorityContextAllowed, routeAuthorityEntries, type RouteAuthorityContract } from '../app/routeAuthority';
import { contractGapError } from '../app/contract/contractGap';

const ADMIN_SURFACE_DECLARATION_LAYER = 'P0:smart_core:navigation_entry_target.build_web_surface_entry_target';
const ADMIN_SURFACES = new Set(['business_config', 'menu_config']);

type AdminSurfaceTarget = { surface: string; route: string; rootMenuXmlid: string };

function declaredEntryTarget(action: NavMeta | null | undefined): Record<string, unknown> | null {
  const target = action?.entry_target;
  return target && typeof target === 'object' && !Array.isArray(target)
    ? target as Record<string, unknown>
    : null;
}

function adminSurfaceTarget(action: NavMeta | null | undefined): AdminSurfaceTarget | null {
  const target = declaredEntryTarget(action);
  if (!target || String(target.type || '').trim() !== 'admin_surface') return null;
  const surface = String(target.surface || '').trim();
  const route = String(target.route || '').trim();
  if (!ADMIN_SURFACES.has(surface)) {
    throw contractGapError(
      {
        kind: 'contract_defect',
        missing: 'route_authority.entry.entry_target.surface',
        requiredDeclarationLayer: ADMIN_SURFACE_DECLARATION_LAYER,
      },
      `契约声明了未知的管理面 entry_target.surface=${surface || '<empty>'}：前端不猜测页面行为`,
    );
  }
  if (!route.startsWith('/')) {
    throw contractGapError(
      {
        kind: 'contract_defect',
        missing: 'route_authority.entry.entry_target.route',
        requiredDeclarationLayer: ADMIN_SURFACE_DECLARATION_LAYER,
      },
      '契约声明了 admin_surface 但缺少合法的 entry_target.route：前端不停机兜底',
    );
  }
  return { surface, route, rootMenuXmlid: String(target.root_menu_xmlid || '').trim() };
}

export function isMenuConfigurationAction(action: NavMeta | null | undefined) {
  return adminSurfaceTarget(action)?.surface === 'menu_config';
}

export function resolveActionWebRoute(action: NavMeta | null | undefined): string {
  return adminSurfaceTarget(action)?.route || '';
}

export function resolveActionWebRouteQuery(action: NavMeta | null | undefined): Record<string, string> {
  const rootMenuXmlid = adminSurfaceTarget(action)?.rootMenuXmlid || '';
  if (rootMenuXmlid) return { root_menu_xmlid: rootMenuXmlid };
  return {};
}

export function isBusinessConfigurationAction(action: NavMeta | null | undefined) {
  return adminSurfaceTarget(action)?.surface === 'business_config';
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
  const target = adminSurfaceTarget(authority);
  if (!target || target.surface !== 'business_config') return null;
  const model = String(authority.model || authority.res_model || '');
  if (['record', 'model-form'].includes(routeName) && options.routeModel !== model) return null;
  const query: Record<string, unknown> = { ...options.query, ...resolveActionWebRouteQuery(authority),
    action_id: String(authority.action_id), menu_id: String(authority.menu_id || options.query.menu_id || '') };
  // A raw-record instance is not a configuration-workbench activity instance.
  delete query.activity_page_id;
  return { path: target.route, query, replace: true };
}

/** Allow contract loading without a menu; this does not authorize record access. */
export function isRecordWorkItemNavigation(routeName: unknown, params: Record<string, unknown>, query: Record<string, unknown>): boolean {
  return ['record', 'model-form'].includes(String(routeName || ''))
    && typeof params.model === 'string' && params.model.trim() !== ''
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
