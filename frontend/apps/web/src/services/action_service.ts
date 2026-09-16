import type { NavMeta } from '@sc/schema';
import type { Router } from 'vue-router';
import { useSessionStore } from '../stores/session';
import { recordTrace, digestParams, createTraceId } from './trace';
import { buildEntryTargetRouteTarget } from '../app/routeQuery';
import { resolveRecordOpenTarget, type RecordEntryContract } from '../app/runtime/recordEntryContract';
import { isBusinessConfigurationAction, isMenuConfigurationAction, resolveActionWebRoute, resolveActionWebRouteQuery } from './actionRoutePolicy';
export { isBusinessConfigurationAction, isMenuConfigurationAction, resolveActionWebRoute, resolveActionWebRouteQuery } from './actionRoutePolicy';

function normalizeDomain(domain: unknown) {
  return Array.isArray(domain) ? domain : [];
}

function normalizeContext(context: unknown) {
  if (context && typeof context === 'object' && !Array.isArray(context)) {
    return context as Record<string, unknown>;
  }
  return {} as Record<string, unknown>;
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

export function openForm(
  router: Router,
  model: string,
  id: number,
  action?: NavMeta,
  menuId?: number,
  recordEntry: Partial<Omit<RecordEntryContract, 'model' | 'recordId' | 'actionId' | 'menuId' | 'carryQuery'>> = {},
) {
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
    entryIntent: recordEntry.entryIntent || 'open',
    modelWriteAuthority: recordEntry.modelWriteAuthority ?? null,
    carryQuery: query,
  });
  if (target) router.push(target as never);
}
