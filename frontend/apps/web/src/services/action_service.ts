import type { NavMeta } from '@sc/schema';
import type { Router } from 'vue-router';
import { useSessionStore } from '../stores/session';
import { recordTrace, digestParams, createTraceId } from './trace';
import { buildEntryTargetRouteTarget } from '../app/routeQuery';
import { normalizeRecordOpenIntent, resolveRecordOpenTarget, type RecordOpenIntent } from '../app/runtime/actionViewInteractionRuntime';
import { BUSINESS_CONFIG_MODELS, MENU_CONFIG_POLICY_MODEL } from '../app/businessConfigBoundaries';

function normalizeDomain(domain: unknown) {
  return Array.isArray(domain) ? domain : [];
}

function normalizeContext(context: unknown) {
  if (context && typeof context === 'object' && !Array.isArray(context)) {
    return context as Record<string, unknown>;
  }
  return {} as Record<string, unknown>;
}

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

export function openAction(
  router: Router,
  action: NavMeta,
  menuId?: number,
  options: { setCurrentAction?: boolean } = {},
) {
  const model = action.model ?? '';
  const viewMode = Array.isArray(action.view_modes) && action.view_modes.length
    ? String(action.view_modes[0] || '')
    : '';
  const query = {
    menu_id: menuId?.toString(),
    action_id: action.action_id?.toString(),
  } as Record<string, string>;
  if (viewMode.trim()) {
    query.view_mode = viewMode;
  }

  const session = useSessionStore();
  if (options.setCurrentAction !== false) {
    session.setActionMeta(action);
  }

  if (isMenuConfigurationAction(action)) {
    router.push({ path: '/admin/menu-config', query });
    return;
  }

  if (isBusinessConfigurationAction(action)) {
    router.push({
      path: resolveActionWebRoute(action) || '/admin/business-config',
      query: { ...query, ...resolveActionWebRouteQuery(action) },
    });
    return;
  }

  recordTrace({
    ts: Date.now(),
    trace_id: createTraceId(),
    intent: 'action.open',
    status: 'ok',
    menu_id: menuId,
    action_id: action.action_id,
    model,
    view_mode: viewMode,
    params_digest: digestParams({ domain: normalizeDomain(action.domain), context: normalizeContext(action.context) }),
  });

  const entryTarget = (action.entry_target && typeof action.entry_target === 'object')
    ? action.entry_target as Record<string, unknown>
    : null;
  if (entryTarget) {
    router.push(buildEntryTargetRouteTarget(entryTarget, {
      query,
      menuId,
      actionId: action.action_id,
    }) as never);
    return;
  }

  router.push({ path: `/a/${action.action_id}`, query });
}

export function openForm(router: Router, model: string, id: number, action?: NavMeta, menuId?: number, modelWriteAuthority?: boolean | null, requestedIntent?: RecordOpenIntent) {
  const query = {
    menu_id: menuId?.toString(),
    action_id: action?.action_id?.toString(),
  } as Record<string, string>;
  query.view_mode = 'form';

  recordTrace({
    ts: Date.now(),
    trace_id: createTraceId(),
    intent: 'action.open_form',
    status: 'ok',
    menu_id: menuId,
    action_id: action?.action_id,
    model,
    view_mode: 'form',
    params_digest: digestParams({ id }),
  });

  const target = resolveRecordOpenTarget({
    model,
    recordId: id,
    actionId: action?.action_id,
    menuId,
    requestedIntent: normalizeRecordOpenIntent(requestedIntent),
    modelWriteAuthority,
    carryQuery: query,
  });
  if (target) router.push(target as never);
}
