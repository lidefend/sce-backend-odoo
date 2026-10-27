import type { ActionFeedbackOwner } from './useNativeActionFeedback';
import { watch } from 'vue';
import { isNavigationFailure } from 'vue-router';
import type { NativeActionNotification } from '@sc/schema';
import { currentContextSignal } from '../../app/contextEpoch';
import { decodeNativeActionNotification } from '../../app/contract/nativeActionNotification';
import { contractGapError } from '../../app/contract/contractGap';
import type { LocationQueryRaw, Router } from 'vue-router';
import { toPositiveInt } from '../../app/contractRuntime';
import { buildEntryTargetRouteTarget } from '../../app/routeQuery';
import {
  actionResponseNavQuery,
  actionResponseRouteTarget,
} from './actionContract';
import { grantButtonNavigationAuthority } from '../../app/buttonNavigationAuthority';

export type ActionResponseNavigationResult = boolean | 'invalidated';

export function useActionResponseNavigation(params: {
  router: Router;
  currentQuery: () => LocationQueryRaw;
  currentModel: () => string;
  notificationIdentity?: () => string;
  showNotification?: (notification: NativeActionNotification, onClosed: () => void) => Promise<() => void>;
}) {
  function navQuery(result: object | null | undefined, extra?: Record<string, unknown>) {
    return actionResponseNavQuery(params.currentQuery() as Record<string, unknown>, result, extra, {
      currentModel: params.currentModel(),
    });
  }

  function routeTarget(target: unknown, result: object | null | undefined, extra?: Record<string, unknown>) {
    return actionResponseRouteTarget(params.currentQuery() as Record<string, unknown>, target, result, extra, {
      currentModel: params.currentModel(),
    });
  }

  async function pushResultTarget(target: Parameters<Router['push']>[0], result: unknown, owner?: ActionFeedbackOwner, replace = false) {
    const notification = decodeNativeActionNotification(result);
    if (!notification) { const navigation = await (replace ? params.router.replace(target) : params.router.push(target)); return !isNavigationFailure(navigation); }
    if (!params.notificationIdentity || !params.showNotification) {
      throw contractGapError({ kind: 'contract_defect', missing: 'native notification navigation owner',
        requiredDeclarationLayer: 'P0: action navigation' }, 'Missing notification navigation owner');
    }
    const ticket = owner?.navigationTicket();
    if (!ticket) return false;
    const source = params.router.currentRoute.value.fullPath;
    const expected = params.router.resolve(target).fullPath;
    const principal = params.notificationIdentity();
    const signal = currentContextSignal();
    let valid = !signal.aborted;
    let completed = false;
    let dismiss: (() => void) | undefined;
    const stopTicket = watch(ticket, current => { if (!current) invalidate(); }, { flush: 'sync' });
    const stopIdentity = watch(params.notificationIdentity, () => invalidate(), { flush: 'sync' });
    const stopRoute = watch(() => params.router.currentRoute.value.fullPath, path => {
      if (path !== expected && (completed || path !== source)) invalidate();
    }, { flush: 'sync' });
    function cleanup() { stopTicket(); stopIdentity(); stopRoute(); signal.removeEventListener('abort', invalidate); }
    function invalidate() { valid = false; dismiss?.(); cleanup(); }
    signal.addEventListener('abort', invalidate, { once: true });
    try {
      const navigation = await (replace ? params.router.replace(target) : params.router.push(target));
      completed = true;
      if (isNavigationFailure(navigation) || !valid || !ticket() || signal.aborted
        || params.notificationIdentity() !== principal || params.router.currentRoute.value.fullPath !== expected) {
        invalidate(); return false;
      }
      // This response's exact governed destination owns the notification. Watchers
      // deliberately outlive the source form until close or identity/navigation change.
      dismiss = await params.showNotification(notification, cleanup);
      if (!valid || !ticket() || signal.aborted || params.router.currentRoute.value.fullPath !== expected) { dismiss(); return false; }
      return true;
    } catch (error) { invalidate(); throw error; }
  }

  async function navigateActionResponseResult(result: unknown, owner?: ActionFeedbackOwner): Promise<ActionResponseNavigationResult> {
    const resultRecord = result && typeof result === 'object'
      ? result as Record<string, unknown>
      : null;
    const rawAction = resultRecord?.raw_action && typeof resultRecord.raw_action === 'object'
      ? resultRecord.raw_action as Record<string, unknown>
      : null;
    const entryTargetSource = resultRecord?.entry_target || rawAction?.entry_target;
    const entryTarget = entryTargetSource && typeof entryTargetSource === 'object'
      ? entryTargetSource as Record<string, unknown>
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
      grantButtonNavigationAuthority(
        toPositiveInt(resultRecord?.action_id),
        params.router.resolve(target as never).fullPath,
      );
      return await pushResultTarget(target as never, result, owner) ? true : 'invalidated';
    }
    const nextActionId = toPositiveInt(resultRecord?.action_id);
    if (nextActionId) {
      const target = {
        name: 'action',
        params: { actionId: String(nextActionId) },
        query: navQuery(resultRecord, { action_id: nextActionId }),
      };
      grantButtonNavigationAuthority(
        nextActionId,
        params.router.resolve(target as never).fullPath,
      );
      const navigated = await pushResultTarget(target as never, result, owner);
      return navigated ? true : 'invalidated';
    }
    return false;
  }

  return {
    actionResponseNavQuery: navQuery,
    actionResponseRouteTarget: routeTarget,
    navigateActionResponseResult,
    navigateNotificationTarget: (target: Parameters<Router['push']>[0], result: unknown, owner: ActionFeedbackOwner) => pushResultTarget(target, result, owner, true),
  };
}
