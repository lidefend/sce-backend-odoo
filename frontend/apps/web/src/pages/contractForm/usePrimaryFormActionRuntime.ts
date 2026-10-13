import type { ActionResponseNavigationResult } from './useActionResponseNavigation';
import type { ActionFeedbackOwner } from './useNativeActionFeedback';
import { relationActionOrigin, workItemActionOrigin } from './relationActionOrigin';
import { nextTick, type Ref } from 'vue';
import { executeButton } from '../../api/executeButton';
import { sanitizeUiErrorMessage } from './fieldUtils';
import { applyFormRuntimeStatusEvent } from './runtimeStateApplier';
import type { BusyKind, ContractAction, SubmissionFeedback, UiStatus } from './types';

export function usePrimaryFormActionRuntime(params: {
  beginActionFeedback?: () => ActionFeedbackOwner;
  actionId: () => number;
  applyProjectionRefreshPolicy: (policy?: ContractAction['refreshPolicy']) => Promise<void>;
  busyKind: Ref<BusyKind>;
  confirmActionSafety: (action: ContractAction) => Promise<boolean>;
  errorMessage: Ref<string>;
  executeButtonRequest?: typeof executeButton;
  hasChanges: () => boolean;
  modelName: () => string;
  navigateActionResponseResult: (result: unknown, owner?: ActionFeedbackOwner) => Promise<ActionResponseNavigationResult>;
  navigateCreatedRecord?: (id: number, policy?: ContractAction['refreshPolicy'], recovery?: 'submit', feedback?: { result: unknown; owner: ActionFeedbackOwner }) => Promise<unknown>;
  primaryCreateFooterAction: () => ContractAction | null;
  primarySubmitAction: () => ContractAction | null;
  recordId: Ref<number>;
  reload: () => Promise<void>;
  routeMenuId: () => unknown;
  currentQuery?: () => Record<string, unknown>;
  saveRecord: (
    refreshPolicy?: ContractAction['refreshPolicy'],
    options?: { navigateAfterCreate?: boolean },
  ) => Promise<boolean | number>;
  status: Ref<UiStatus>;
  submissionFeedback: Ref<SubmissionFeedback>;
  validationErrors: Ref<string[]>;
  validateSubmissionRequirements?: (action: ContractAction) => boolean;
}) {
  async function executePrimarySubmitAction(action: ContractAction, resId: number, created = false) {
    if (!action.enabled) return;
    const owner = params.beginActionFeedback?.();
    if (!await params.confirmActionSafety(action) || (owner && !owner.owns())) return;
    params.busyKind.value = 'action';
    try {
      const response = await (params.executeButtonRequest || executeButton)({
        model: action.targetModel || params.modelName(),
        res_id: resId,
        button: {
          name: action.methodName,
          type: action.kind === 'server' ? 'server' : 'object',
          action_id: String(action.authorityActionId || '').trim(),
          backend_identity: String(action.backendIdentity || '').trim(),
          source_widget_id: String(action.sourceWidgetId || '').trim(),
          server_action_id: action.serverActionId || undefined,
          xml_id: action.serverActionXmlId || undefined,
        },
        context: action.context,
        meta: {
          menu_id: Number(params.routeMenuId() || 0) || undefined,
          action_id: params.actionId() || undefined,
          relation_origin: relationActionOrigin(params.currentQuery?.() || {}),
          work_item_origin: workItemActionOrigin(params.currentQuery?.() || {}),
        },
      });
      if (owner && !owner.owns()) return;
      const result = response?.result;
      const navigation = await params.navigateActionResponseResult(result, owner);
      if (navigation === 'invalidated') return;
      if (navigation) {
        await params.applyProjectionRefreshPolicy(action.refreshPolicy || { on_success: ['scene_projection'] });
        return;
      }
      if (created && params.navigateCreatedRecord) {
        await params.navigateCreatedRecord(resId, action.refreshPolicy, undefined, owner ? { result, owner } : undefined);
        return;
      }
      await params.applyProjectionRefreshPolicy(action.refreshPolicy || { on_success: ['scene_projection'] });
      await params.reload();
      await owner?.publish(result);
    } catch (err) {
      if (owner && !owner.owns()) return;
      const message = sanitizeUiErrorMessage(err instanceof Error ? err.message : err, '提交失败，请检查填写内容');
      params.validationErrors.value = [message];
      params.submissionFeedback.value = { kind: 'error', message: '提交失败，请检查填写内容' };
      applyFormRuntimeStatusEvent(params, {
        kind: 'status',
        transaction: 'primaryAction',
        status: 'error',
      });
      if (created && params.navigateCreatedRecord) {
        await params.navigateCreatedRecord(resId, action.refreshPolicy, 'submit');
      }
    } finally {
      if (!owner || owner.owns()) params.busyKind.value = null;
    }
  }

  async function runPrimaryFormAction() {
    const footerAction = params.primaryCreateFooterAction();
    if (footerAction) {
      if (!footerAction.enabled) return;
      if (params.validateSubmissionRequirements?.(footerAction) === false) return;
      const saved = await params.saveRecord(
        footerAction.refreshPolicy,
        { navigateAfterCreate: false },
      );
      if (!saved) return;
      await nextTick();
      const submittedRecordId = typeof saved === 'number' ? saved : params.recordId.value;
      if (!submittedRecordId) {
        applyFormRuntimeStatusEvent(params, {
          kind: 'status',
          transaction: 'primaryAction',
          status: 'error',
          errorMessage: '操作失败：请先保存记录后再执行',
        });
        return;
      }
      await executePrimarySubmitAction(footerAction, submittedRecordId, true);
      return;
    }
    const submitAction = params.primarySubmitAction();
    if (!submitAction) {
      await params.saveRecord();
      return;
    }
    if (!submitAction.enabled) return;
    if (params.validateSubmissionRequirements?.(submitAction) === false) return;
    let submittedRecordId = params.recordId.value;
    if (params.hasChanges()) {
      const saved = await params.saveRecord(submitAction.refreshPolicy);
      if (!saved) return;
      await nextTick();
      submittedRecordId = typeof saved === 'number' ? saved : params.recordId.value;
    }
    if (!submittedRecordId) {
      applyFormRuntimeStatusEvent(params, {
        kind: 'status',
        transaction: 'primaryAction',
        status: 'error',
        errorMessage: '提交失败：请先保存记录后再提交',
      });
      return;
    }
    await executePrimarySubmitAction(submitAction, submittedRecordId);
  }

  return {
    executePrimarySubmitAction,
    runPrimaryFormAction,
  };
}
