import type { LocationQueryRaw, Router } from 'vue-router';
import { toPositiveInt } from '../../app/contractRuntime';
import { buildEntryTargetRouteTarget } from '../../app/routeQuery';
import {
  actionResponseNavQuery,
  actionResponseRouteTarget,
} from './actionContract';

export function useActionResponseNavigation(params: {
  router: Router;
  currentQuery: () => LocationQueryRaw;
}) {
  function navQuery(result: object | null | undefined, extra?: Record<string, unknown>) {
    return actionResponseNavQuery(params.currentQuery() as Record<string, unknown>, result, extra);
  }

  function routeTarget(target: unknown, result: object | null | undefined, extra?: Record<string, unknown>) {
    return actionResponseRouteTarget(params.currentQuery() as Record<string, unknown>, target, result, extra);
  }

  async function navigateActionResponseResult(result: unknown) {
    const resultRecord = result && typeof result === 'object'
      ? result as Record<string, unknown>
      : null;
    const entryTarget = resultRecord?.entry_target && typeof resultRecord.entry_target === 'object'
      ? resultRecord.entry_target as Record<string, unknown>
      : null;
    // A plain refresh stays on the current record. When the gateway also
    // supplies an authoritative entry target, the target is the model
    // method's returned action (for example a transient form) and must win.
    if (
      String(resultRecord?.type || '').trim().toLowerCase() === 'refresh'
      && !entryTarget
    ) return false;
    if (entryTarget) {
      const target = routeTarget(buildEntryTargetRouteTarget(entryTarget, {
        query: navQuery(resultRecord),
        actionId: resultRecord.action_id,
      }), resultRecord);
      // Native wizards commonly return an act_window reopening the same
      // transient record after an object button. Vue Router treats that as a
      // no-op, so let the caller refresh the current contract and record.
      if (params.router.resolve(target as never).fullPath === params.router.currentRoute.value.fullPath) return false;
      await params.router.push(target as never);
      return true;
    }
    const nextActionId = toPositiveInt(resultRecord?.action_id);
    if (nextActionId) {
      await params.router.push({
        name: 'action',
        params: { actionId: String(nextActionId) },
        query: navQuery(resultRecord, { action_id: nextActionId }),
      });
      return true;
    }
    return false;
  }

  return {
    actionResponseNavQuery: navQuery,
    actionResponseRouteTarget: routeTarget,
    navigateActionResponseResult,
  };
}
