import type { ActionResponseNavigationResult } from './useActionResponseNavigation';
import type { ActionFeedbackOwner } from './useNativeActionFeedback';
import { relationActionOrigin, workItemActionOrigin } from './relationActionOrigin';
import type { Ref } from 'vue';
import type { Router, LocationQueryRaw } from 'vue-router';
import { executeButton } from '../../api/executeButton';
import { pickContractNavQuery } from '../../app/navigationContext';
import { buildFormActionExecutionPlan } from './actionExecutionPlan';
import { applyFormRuntimeStatusEvent } from './runtimeStateApplier';
import type { BusyKind, ContractAction, SubmissionFeedback, UiStatus } from './types';

type SceneMutationInput = {
  mutation: NonNullable<ContractAction['mutation']>;
  actionKey: string;
  recordId: number | null;
  model: string;
  context?: Record<string, unknown>;
  params: Record<string, unknown>;
};

export function useFormActionRuntime(params: {
  beginActionFeedback?: () => ActionFeedbackOwner;
  actionId: () => number;
  applyClientMode: (mode: string, toggle?: boolean) => boolean | void;
  applyProjectionRefreshPolicy: (policy?: ContractAction['refreshPolicy']) => Promise<void>;
  busyKind: Ref<BusyKind>;
  collectActionParams: (action: ContractAction) => Promise<Record<string, unknown> | null>;
  confirmActionSafety: (action: ContractAction) => Promise<boolean>;
  currentQuery: () => LocationQueryRaw;
  ensureSavedBeforeRecordAction: () => Promise<boolean>;
  errorMessage: Ref<string>;
  executeSceneMutation: (input: SceneMutationInput) => Promise<unknown>;
  modelName: () => string;
  navigateActionResponseResult: (result: unknown, owner?: ActionFeedbackOwner) => Promise<ActionResponseNavigationResult>;
  recordId: () => number | null;
  reload: () => Promise<void>;
  resolveNavigationUrl: (url: string) => string;
  routeMenuId: () => unknown;
  router: Router;
  saveRecord: (refreshPolicy?: ContractAction['refreshPolicy']) => Promise<boolean | number>;
  status: Ref<UiStatus>;
  submissionFeedback: Ref<SubmissionFeedback>;
  validateSubmissionRequirements?: (action: ContractAction) => boolean;
}) {
  async function runAction(action: ContractAction) {
    if (!action.enabled) return;
    if (params.validateSubmissionRequirements?.(action) === false) return;
    const owner = params.beginActionFeedback?.();
    if (!await params.confirmActionSafety(action) || (owner && !owner.owns())) return;
    const plan = buildFormActionExecutionPlan({
      action,
      modelName: params.modelName(),
      recordId: params.recordId(),
    });
    if (plan.kind === 'disabled') return;
    if (plan.kind === 'local_mode') {
      params.applyClientMode(plan.mode, plan.toggle);
      return;
    }
    if (plan.kind === 'save') {
      await params.saveRecord(plan.refreshPolicy);
      return;
    }
    if (plan.kind === 'cancel') {
      await params.router.push({
        name: 'workbench',
        query: pickContractNavQuery(params.currentQuery() as Record<string, unknown>, {
          scene: undefined,
        }),
      });
      return;
    }
    if (plan.kind === 'open_action') {
      await params.router.push({
        name: 'action',
        params: { actionId: String(plan.actionId) },
        query: pickContractNavQuery(params.currentQuery() as Record<string, unknown>, {
          action_id: plan.actionId,
          menu_id: plan.menuId || undefined,
          target: plan.target || undefined,
          domain_raw: plan.domainRaw || undefined,
        }),
      });
      return;
    }
    if (plan.kind === 'open_url') {
      const navUrl = params.resolveNavigationUrl(plan.url);
      if (plan.target === 'self') {
        const destination = new URL(navUrl, window.location.origin);
        if (destination.origin === window.location.origin) {
          await params.router.push(`${destination.pathname}${destination.search}${destination.hash}`);
          return;
        }
      }
      window.open(navUrl, plan.target === 'self' ? '_self' : '_blank', 'noopener,noreferrer');
      return;
    }
    if (plan.kind === 'open_missing_target') {
      applyFormRuntimeStatusEvent(params, {
        kind: 'status',
        transaction: 'runAction',
        status: 'error',
        errorMessage: '打开操作缺少目标页面',
      });
      return;
    }
    if (plan.kind === 'scene_mutation') {
      const actionParams = await params.collectActionParams(action);
      if (actionParams === null) return;
      params.busyKind.value = 'action';
      try {
        const response = await params.executeSceneMutation({
          mutation: plan.mutation,
          actionKey: plan.actionKey,
          recordId: plan.recordId,
          model: plan.model,
          context: plan.context,
          params: actionParams,
        });
        if (owner && !owner.owns()) return;
        const data = response && typeof response === 'object' ? (response as { data?: unknown }).data : undefined;
        await params.applyProjectionRefreshPolicy(plan.refreshPolicy);
        await owner?.publish(data);
        return;
      } catch (err) {
        applyFormRuntimeStatusEvent(params, {
          kind: 'status',
          transaction: 'runAction',
          status: 'error',
          errorMessage: err instanceof Error ? err.message : '场景操作执行失败',
        });
        return;
      } finally {
        if (!owner || owner.owns()) params.busyKind.value = null;
      }
    }
    if (plan.kind === 'record_button') {
      if (!await params.ensureSavedBeforeRecordAction() || (owner && !owner.owns())) return;
      params.busyKind.value = 'action';
      try {
        const response = await executeButton({
          model: plan.model,
          res_id: plan.recordId,
          button: {
            name: plan.methodName,
            type: plan.buttonType,
            action_id: plan.authorityActionId,
            backend_identity: plan.backendIdentity,
            source_widget_id: plan.sourceWidgetId,
            server_action_id: plan.serverActionId || undefined,
            xml_id: plan.serverActionXmlId || undefined,
          },
          context: plan.context,
          meta: {
            menu_id: Number(params.routeMenuId() || 0) || undefined,
            action_id: params.actionId() || undefined,
            relation_origin: relationActionOrigin(params.currentQuery()),
            work_item_origin: workItemActionOrigin(params.currentQuery()),
          },
        });
        if (owner && !owner.owns()) return;
        const result = response?.result;
        const navigation = await params.navigateActionResponseResult(result, owner);
      if (navigation === 'invalidated') return;
      if (navigation) {
          if (plan.refreshPolicy) {
            await params.applyProjectionRefreshPolicy(plan.refreshPolicy);
          }
          return;
        }
        const refresh = result?.type;
        if (refresh === 'refresh' && !plan.refreshPolicy) {
          await params.reload();
          await owner?.publish(result);
          return;
        }
        if (plan.refreshPolicy) {
          await params.applyProjectionRefreshPolicy(plan.refreshPolicy);
        } else {
          await params.reload();
        }
        await owner?.publish(result);
        return;
      } catch (err) {
        if (owner && !owner.owns()) return;
        applyFormRuntimeStatusEvent(params, {
          kind: 'status',
          transaction: 'runAction',
          status: 'error',
          errorMessage: err instanceof Error ? err.message : '操作执行失败',
        });
      } finally {
        if (!owner || owner.owns()) params.busyKind.value = null;
      }
    }
  }

  return {
    runAction,
  };
}
