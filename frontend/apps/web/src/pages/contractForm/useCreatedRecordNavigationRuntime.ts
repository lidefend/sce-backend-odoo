import type { ActionFeedbackOwner } from './useNativeActionFeedback';
import { decodeNativeActionNotification } from '../../app/contract/nativeActionNotification';
import { contractGapError } from '../../app/contract/contractGap';
import type { RouteLocationNormalizedLoaded, Router } from 'vue-router';
import { pickContractNavQuery } from '../../app/navigationContext';
import type { ContractAction } from './types';
import {
  buildProfessionalRelationCancelledMessage,
  buildProfessionalRelationCreatedMessage,
  type ProfessionalRelationCancelledMessage,
  type ProfessionalRelationCreatedMessage,
} from './professionalRelationLifecycleModel';

export type RelationCreateDialogMessage = ProfessionalRelationCreatedMessage;
export type RelationCreateDialogCancelMessage = ProfessionalRelationCancelledMessage;

export function resolveRelationCreateDialogMessage(params: {
  query: Record<string, unknown>;
  createdId: number | string;
  relationModel: string;
  label?: string;
}): RelationCreateDialogMessage | null {
  return buildProfessionalRelationCreatedMessage(params);
}

export function resolveRelationCreateDialogCancelMessage(params: {
  query: Record<string, unknown>;
  relationModel: string;
}): RelationCreateDialogCancelMessage | null {
  return buildProfessionalRelationCancelledMessage(params);
}

export function hasInAppReturnHistory(historyState: unknown): boolean {
  const state = historyState && typeof historyState === 'object'
    ? historyState as Record<string, unknown>
    : null;
  return typeof state?.back === 'string' && String(state.back).trim() !== '';
}

export function resolveRecordFormReturnFallbackRoute(authorityRoute: unknown): string {
  const route = String(authorityRoute ?? '').trim();
  return route.startsWith('/') ? route : '';
}

export type RecordFormReturnMode = 'dialog_cancel' | 'history' | 'fallback';

export async function executeRecordFormReturn(params: {
  query: Record<string, unknown>;
  relationModel: string;
  embedded: boolean;
  postCancel: (message: RelationCreateDialogCancelMessage) => void;
  navigateBack: () => void | Promise<void>;
  hasInAppHistoryEntry?: () => boolean;
  fallbackRoute?: () => string;
  navigateFallback?: (route: string) => void | Promise<void>;
}): Promise<RecordFormReturnMode> {
  const cancelMessage = resolveRelationCreateDialogCancelMessage(params);
  if (cancelMessage && params.embedded) {
    params.postCancel(cancelMessage);
    return 'dialog_cancel';
  }
  // A record form opened without a usable in-app predecessor (direct link,
  // reload) cannot rely on browser history. Fall back to the entry route the
  // route authority already declares for this form instead of leaving the app.
  const canNavigateBack = params.hasInAppHistoryEntry ? params.hasInAppHistoryEntry() : true;
  if (!canNavigateBack && params.navigateFallback) {
    const fallbackRoute = params.fallbackRoute ? params.fallbackRoute() : '';
    if (fallbackRoute) {
      await params.navigateFallback(fallbackRoute);
      return 'fallback';
    }
  }
  await params.navigateBack();
  return 'history';
}

export function useCreatedRecordNavigationRuntime(params: {
  applyProjectionRefreshPolicy: (policy?: ContractAction['refreshPolicy']) => Promise<void>;
  currentQuery: () => Record<string, unknown>;
  isQuickIntakeMode: () => boolean;
  isStandardIntakeMode: () => boolean;
  modelName: () => string;
  resolveWorkspaceContextQuery: () => Record<string, unknown>;
  returnToIntakeList: (createdId: number | string, navigate?: (target: Parameters<Router['replace']>[0]) => Promise<unknown>) => Promise<boolean>;
  navigateNotificationTarget?: (target: Parameters<Router['replace']>[0], result: unknown, owner: ActionFeedbackOwner) => Promise<boolean>;
  router: Router;
}) {
  async function navigateCreatedRecord(options: {
    createdId: number | string;
    createdLabel?: string;
    nextSceneKey: string;
    nextSceneRoute: string;
    refreshPolicy?: ContractAction['refreshPolicy'];
    recovery?: 'upload' | 'submit';
    feedback?: { result: unknown; owner: ActionFeedbackOwner };
  }) {
    const currentQuery = params.currentQuery();
    const feedback = options.feedback && decodeNativeActionNotification(options.feedback.result) ? options.feedback : undefined;
    if (feedback && !feedback.owner.owns()) return false;
    const navigate = feedback && params.navigateNotificationTarget
      ? (target: Parameters<Router['replace']>[0]) => params.navigateNotificationTarget!(target, feedback.result, feedback.owner)
      : undefined;
    const relationDialogMessage = resolveRelationCreateDialogMessage({
      query: currentQuery,
      createdId: options.createdId,
      relationModel: params.modelName(),
      label: options.createdLabel,
    });
    if (!options.recovery && relationDialogMessage && window.parent !== window) {
      await params.applyProjectionRefreshPolicy(
        options.refreshPolicy || { on_success: ['record', 'collection'] },
      );
      if (feedback && !feedback.owner.owns()) return false;
      if (feedback) relationDialogMessage.notification = decodeNativeActionNotification(feedback.result)!;
      window.parent.postMessage(relationDialogMessage, window.location.origin);
      return true;
    }
    if (feedback && !navigate) {
      throw contractGapError({ kind: 'contract_defect', missing: 'created notification navigation owner',
        requiredDeclarationLayer: 'P0: created record navigation' }, 'Missing created notification handoff');
    }
    const resolvedNextRoute = options.nextSceneRoute || (options.nextSceneKey ? `/s/${options.nextSceneKey}` : '');
    if (!options.recovery && (params.isQuickIntakeMode() || params.isStandardIntakeMode())) {
      await params.applyProjectionRefreshPolicy(options.refreshPolicy || { on_success: ['scene_projection', 'workbench_projection'] });
      if (feedback && !feedback.owner.owns()) return false;
      if (await params.returnToIntakeList(options.createdId, navigate)) return true;
      if (resolvedNextRoute) {
        await (navigate || params.router.replace.bind(params.router))({
          path: resolvedNextRoute,
          query: {
            record_id: String(options.createdId),
            ...params.resolveWorkspaceContextQuery(),
          },
        });
        return true;
      }
    }
    const createdRoute = params.router.resolve({
      name: 'model-form',
      params: { model: params.modelName(), id: String(options.createdId) },
      query: { ...pickContractNavQuery(currentQuery), ...(options.recovery ? { create_recovery: options.recovery } : {}) },
    });
    if (navigate) return await navigate(createdRoute);
    window.location.replace(new URL(createdRoute.href, window.location.origin).toString());
    await new Promise<never>(() => {});
    return true;
  }

  return {
    navigateCreatedRecord,
  };
}

/** Bind return navigation to live route/context getters, behind the unsaved guard. */
export function createRecordFormReturnHandler(params: {
  route: Pick<RouteLocationNormalizedLoaded, 'query'>;
  router: Router;
  model: () => string;
  authorityRoute: () => unknown;
  navigateAfterConfirm: (navigate: () => Promise<void>) => Promise<boolean>;
}) {
  return async () => {
    await params.navigateAfterConfirm(async () => {
      await executeRecordFormReturn({
        query: params.route.query as Record<string, unknown>,
        relationModel: params.model(),
        embedded: window.parent !== window,
        postCancel: (message) => window.parent.postMessage(message, window.location.origin),
        navigateBack: () => params.router.back(),
        hasInAppHistoryEntry: () => hasInAppReturnHistory(params.router.options.history?.state),
        fallbackRoute: () => resolveRecordFormReturnFallbackRoute(params.authorityRoute()),
        navigateFallback: async (target) => { await params.router.replace(target); },
      });
    });
  };
}
