import type { Router } from 'vue-router';
import { pickContractNavQuery } from '../../app/navigationContext';
import type { ContractAction } from './types';

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
    nextSceneKey: string;
    nextSceneRoute: string;
    refreshPolicy?: ContractAction['refreshPolicy'];
  }) {
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
      query: pickContractNavQuery(params.currentQuery()),
    });
    window.location.replace(new URL(createdRoute.href, window.location.origin).toString());
    await new Promise<never>(() => {});
    return true;
  }

  return {
    navigateCreatedRecord,
  };
}
