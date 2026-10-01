import { computed, type Ref } from 'vue';
import type { SceneListProfile } from '../resolvers/sceneRegistry';
import {
  executeActionViewSelectionExport,
  resolveSelectionActions,
} from '../runtime/actionViewSelectionExportRuntime';
import {
  batchUpdateActionViewRecords,
  unlinkActionViewRecord,
} from '../runtime/actionViewDataRuntime';
import {
  buildBatchUpdateRequest,
  resolveBatchActionFailureMessage,
  resolveBatchActionGuardMessage,
  resolveBatchActionResultMessage,
  resolveBatchDeleteFailureMessage,
} from '../runtime/actionViewBatchRuntime';
import {
  resolveBatchActionGuardDecision,
  resolveBatchDeleteExecutionSeed,
  resolveBatchStandardExecutionSeed,
} from '../runtime/actionViewBatchActionFlowRuntime';

/** The batch declaration the effective contract publishes for this surface. */
export type ActionBatchPolicy = NonNullable<SceneListProfile['batch_policy']>;

type ExportColumnOption = Parameters<typeof executeActionViewSelectionExport>[0]['columnOptions'][number];

/** Only the part of a declared action this surface dispatches on. */
type DeclaredAction = { key: string; enabled?: boolean };

type BatchConfirmation = {
  confirm: (options: { actionLabel: string; message: string }) => Promise<boolean>;
};

type UseActionViewSelectionActionRuntimeOptions<Action extends DeclaredAction> = {
  allowedBatchActions: Readonly<Ref<string[]>>;
  batchPolicy: Readonly<Ref<ActionBatchPolicy>>;
  activeField: Readonly<Ref<string>>;
  selectedIds: Ref<number[]>;
  batchBusy: Ref<boolean>;
  batchMessage: Ref<string>;
  batchConfirmationRef: Readonly<Ref<BatchConfirmation | null>>;
  columns: Readonly<Ref<string[]>>;
  listColumnOptions: Readonly<Ref<ExportColumnOption[]>>;
  listColumnVisibility: Readonly<Ref<Record<string, boolean>>>;
  contractColumnLabels: Readonly<Ref<Record<string, string>>>;
  contractActions: Readonly<Ref<Action[]>>;
  text: (key: string, fallback: string) => string;
  resolveTargetModel: () => string;
  resolveEffectiveRequestContext: () => Record<string, unknown>;
  buildIfMatchMap: (ids: number[]) => Record<number, string>;
  buildIdempotencyKey: (action: string, ids: number[], extra: Record<string, unknown>) => string;
  clearSelection: () => void;
  reload: () => Promise<unknown>;
  runDeclaredAction: (action: Action) => void;
};

/**
 * The selection surface of a collection: which batch actions it offers and what
 * each one executes.
 *
 * The effective contract declares which batch actions exist and the intent each
 * one executes through; this runtime only maps that declaration onto the client
 * executors it actually has, and reports the ones it cannot run instead of
 * dropping them. It never decides that a batch action exists.
 */
export function useActionViewSelectionActionRuntime<Action extends DeclaredAction>(
  options: UseActionViewSelectionActionRuntimeOptions<Action>,
) {
  const selectionActions = computed(() => {
    // The contract declares which batch actions exist and how each one executes;
    // this surface only maps the declared intent onto a client executor.
    return resolveSelectionActions(
      options.allowedBatchActions.value,
      {
        intents: (options.batchPolicy.value.execution_intents || {}) as Record<string, string>,
        deleteMode: String(options.batchPolicy.value.delete_mode || 'none'),
        activeField: options.activeField.value,
      },
      options.text,
    );
  });

  function handleSelectionAction(key: string) {
    if (key.startsWith('batch:')) {
      const action = key.slice('batch:'.length);
      if (action === 'export') {
        void executeActionViewSelectionExport({
          model: options.resolveTargetModel(),
          ids: [...options.selectedIds.value],
          columns: options.columns.value,
          columnOptions: options.listColumnOptions.value,
          visibility: options.listColumnVisibility.value,
          columnLabels: options.contractColumnLabels.value,
          context: options.resolveEffectiveRequestContext(),
          setBusy: (busy) => { options.batchBusy.value = busy; },
          onSuccess: (count) => {
            options.clearSelection();
            options.batchMessage.value = options.text('batch_msg_export_done', `已导出 ${count} 条记录`);
          },
          onFailure: () => {
            options.batchMessage.value = options.text('batch_msg_export_failed', '导出失败，请稍后重试');
          },
        });
        return;
      }
      if (action === 'archive' || action === 'activate' || action === 'delete') {
        void runBatchPolicyAction(action);
      }
      return;
    }
    const target = options.contractActions.value.find((action) => action.key === key);
    if (!target || !target.enabled) return;
    options.runDeclaredAction(target);
  }

  async function runBatchPolicyAction(action: 'archive' | 'activate' | 'delete') {
    const targetModel = options.resolveTargetModel();
    const selected = [...options.selectedIds.value];
    if (!options.allowedBatchActions.value.includes(action)) {
      options.batchMessage.value = options.text('batch_msg_action_not_allowed', '当前场景不支持该批量操作');
      return;
    }
    const guard = resolveBatchActionGuardDecision({
      targetModel,
      selectedCount: selected.length,
      action,
      hasActiveField: Boolean(options.activeField.value),
      deleteMode: String(options.batchPolicy.value.delete_mode || 'none'),
    });
    if (!guard.ok) {
      options.batchMessage.value = resolveBatchActionGuardMessage({
        reason: guard.reason as 'missing_target_model' | 'missing_selection' | 'active_field_required' | 'delete_mode_unavailable',
        text: options.text,
      });
      return;
    }
    if (action === 'delete') {
      if (!await options.batchConfirmationRef.value?.confirm({ actionLabel: '批量删除', message: options.text('batch_confirm_delete', `确认删除选中的 ${selected.length} 条记录？`) })) {
        return;
      }
      const seed = resolveBatchDeleteExecutionSeed({
        selectedIds: selected,
        buildIfMatchMap: options.buildIfMatchMap,
        buildIdempotencyKey: options.buildIdempotencyKey,
      });
      options.batchBusy.value = true;
      try {
        await unlinkActionViewRecord({
          model: targetModel,
          ids: selected,
          context: options.resolveEffectiveRequestContext(),
          idempotencyKey: seed.dryRunIdempotencyKey,
          dryRun: true,
        });
        const result = await unlinkActionViewRecord({
          model: targetModel,
          ids: selected,
          context: options.resolveEffectiveRequestContext(),
          idempotencyKey: seed.idempotencyKey,
        });
        const resultMessage = resolveBatchActionResultMessage({
          action,
          idempotentReplay: result.idempotent_replay === true,
          succeeded: Array.isArray(result.ids) ? result.ids.length : selected.length,
          failed: 0,
          text: options.text,
        });
        options.clearSelection();
        await options.reload();
        options.batchMessage.value = resultMessage;
      } catch (err) {
        options.batchMessage.value = action === 'delete'
          ? resolveBatchDeleteFailureMessage(err, options.text)
          : resolveBatchActionFailureMessage({ action, text: options.text });
      } finally {
        options.batchBusy.value = false;
      }
      return;
    }
    const activeValue = action === 'activate'
      ? options.batchPolicy.value.activate_value === true
      : options.batchPolicy.value.archive_value === true;
    const seed = resolveBatchStandardExecutionSeed({
      action,
      selectedIds: selected,
      activeField: options.activeField.value,
      activeValue,
      buildIfMatchMap: options.buildIfMatchMap,
      buildIdempotencyKey: options.buildIdempotencyKey,
    });
    options.batchBusy.value = true;
    try {
      const result = await batchUpdateActionViewRecords(buildBatchUpdateRequest({
        model: targetModel,
        ids: selected,
        action,
        ifMatchMap: seed.ifMatchMap,
        idempotencyKey: seed.idempotencyKey,
        context: options.resolveEffectiveRequestContext(),
      }) as Parameters<typeof batchUpdateActionViewRecords>[0]);
      const resultMessage = resolveBatchActionResultMessage({
        action,
        idempotentReplay: result.idempotent_replay === true,
        succeeded: Number(result.succeeded || 0),
        failed: Number(result.failed || 0),
        text: options.text,
      });
      options.clearSelection();
      await options.reload();
      options.batchMessage.value = resultMessage;
    } catch {
      options.batchMessage.value = resolveBatchActionFailureMessage({ action, text: options.text });
    } finally {
      options.batchBusy.value = false;
    }
  }

  return {
    selectionActions,
    handleSelectionAction,
    runBatchPolicyAction,
  };
}
