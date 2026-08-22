import type { Router } from 'vue-router';
import { pickContractNavQuery } from '../../app/navigationContext';
import type { ContractAction } from './types';

export type RelationCreateDialogMessage = {
  type: 'sc.relation_record_created.v1';
  nonce: string;
  fieldName: string;
  parentModel: string;
  relationModel: string;
  id: number;
  label: string;
};

export type RelationCreateDialogCancelMessage = Omit<RelationCreateDialogMessage, 'type' | 'id' | 'label'> & {
  type: 'sc.relation_record_cancelled.v1';
};

function resolveRelationCreateDialogContext(params: {
  query: Record<string, unknown>;
  relationModel: string;
}) {
  if (String(params.query.relation_create_mode || '').trim() !== 'dialog') return null;
  const nonce = String(params.query.relation_dialog_nonce || '').trim();
  const fieldName = String(params.query.relation_return_field || '').trim();
  const parentModel = String(params.query.relation_return_model || '').trim();
  const relationModel = String(params.relationModel || '').trim();
  if (!/^[a-zA-Z0-9-]{8,128}$/.test(nonce)
    || !/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(fieldName)
    || !/^[a-zA-Z0-9_.]+$/.test(parentModel)
    || !/^[a-zA-Z0-9_.]+$/.test(relationModel)) return null;
  return { nonce, fieldName, parentModel, relationModel };
}

export function resolveRelationCreateDialogMessage(params: {
  query: Record<string, unknown>;
  createdId: number | string;
  relationModel: string;
  label?: string;
}): RelationCreateDialogMessage | null {
  const context = resolveRelationCreateDialogContext(params);
  const id = Number(params.createdId || 0);
  if (!context || !Number.isFinite(id) || id <= 0) return null;
  return {
    type: 'sc.relation_record_created.v1',
    ...context,
    id: Math.trunc(id),
    label: String(params.label || '').trim() || `记录 ${Math.trunc(id)}`,
  };
}

export function resolveRelationCreateDialogCancelMessage(params: {
  query: Record<string, unknown>;
  relationModel: string;
}): RelationCreateDialogCancelMessage | null {
  const context = resolveRelationCreateDialogContext(params);
  return context ? { type: 'sc.relation_record_cancelled.v1', ...context } : null;
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
