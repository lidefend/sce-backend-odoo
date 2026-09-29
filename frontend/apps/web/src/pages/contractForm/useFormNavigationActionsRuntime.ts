import type { LocationQueryRaw, Router } from 'vue-router';
import { pickContractNavQuery } from '../../app/navigationContext';

export function useFormNavigationActionsRuntime(params: {
  actionId: () => number;
  currentQuery: () => Record<string, unknown>;
  isIntakeCreateMode: () => boolean;
  resolveLandingPath: (fallback: string) => string;
  resolveWorkspaceContextQuery: () => LocationQueryRaw;
  router: Router;
}) {
  async function cancelIntake() {
    if (!params.isIntakeCreateMode()) return;
    const target = params.resolveLandingPath('/');
    await params.router.replace({ path: target, query: params.resolveWorkspaceContextQuery() });
  }

  async function returnToIntakeList(createdId: number | string) {
    const queryActionId = Number(params.currentQuery().action_id || params.actionId() || 0) || 0;
    if (queryActionId > 0) {
      await params.router.replace({
        path: `/a/${queryActionId}`,
        query: pickContractNavQuery(params.currentQuery(), {
          record_id: String(createdId),
          view_mode: 'tree',
        }),
      });
      return true;
    }
    return false;
  }

  return {
    cancelIntake,
    returnToIntakeList,
  };
}
