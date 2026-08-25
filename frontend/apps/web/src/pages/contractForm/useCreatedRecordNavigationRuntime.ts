import type { Router } from 'vue-router';
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

export async function executeRecordFormReturn(params: {
  query: Record<string, unknown>;
  relationModel: string;
  embedded: boolean;
  postCancel: (message: RelationCreateDialogCancelMessage) => void;
  navigateBack: () => void | Promise<void>;
}): Promise<'dialog_cancel' | 'history'> {
  const cancelMessage = resolveRelationCreateDialogCancelMessage(params);
  if (cancelMessage && params.embedded) {
    params.postCancel(cancelMessage);
    return 'dialog_cancel';
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
  returnToIntakeList: (createdId: number | string) => Promise<boolean>;
  router: Router;
}) {
  async function navigateCreatedRecord(options: {
    createdId: number | string;
    createdLabel?: string;
    nextSceneKey: string;
    nextSceneRoute: string;
    refreshPolicy?: ContractAction['refreshPolicy'];
  }) {
    const currentQuery = params.currentQuery();
    const relationDialogMessage = resolveRelationCreateDialogMessage({
      query: currentQuery,
      createdId: options.createdId,
      relationModel: params.modelName(),
      label: options.createdLabel,
    });
    if (relationDialogMessage && window.parent !== window) {
      await params.applyProjectionRefreshPolicy(
        options.refreshPolicy || { on_success: ['record', 'collection'] },
      );
      window.parent.postMessage(relationDialogMessage, window.location.origin);
      return true;
    }
    const resolvedNextRoute = options.nextSceneRoute || (options.nextSceneKey ? `/s/${options.nextSceneKey}` : '');
    if (params.isQuickIntakeMode() || params.isStandardIntakeMode()) {
      await params.applyProjectionRefreshPolicy(options.refreshPolicy || { on_success: ['scene_projection', 'workbench_projection'] });
      if (await params.returnToIntakeList(options.createdId)) return true;
      if (resolvedNextRoute) {
        await params.router.replace({
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
      query: pickContractNavQuery(currentQuery),
    });
    window.location.replace(new URL(createdRoute.href, window.location.origin).toString());
    await new Promise<never>(() => {});
    return true;
  }

  return {
    navigateCreatedRecord,
  };
}
