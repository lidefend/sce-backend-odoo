import type { Ref } from 'vue';
import { ApiError } from '../../api/client';
import { listRecords } from '../../api/data';
import { resolveDeclaredAssigneeQuery } from '../runtime/actionViewAssigneeOptionsContract';

type UseActionViewAssigneeRuntimeOptions = {
  hasAssigneeField: Ref<boolean>;
  assigneeOptionsContract: Ref<{
    model?: string;
    fields?: string[];
    domain?: unknown[];
    order?: string;
    limit?: number;
  } | null>;
  assigneeOptions: Ref<Array<{ id: number; name: string }>>;
  selectedAssigneeId: Ref<number | null>;
  batchMessage: Ref<string>;
  pageText: (key: string, fallback: string) => string;
  resolveAssigneeOptionsLoadGuard: (input: { hasAssigneeField: boolean }) => {
    ok: boolean;
    assigneeOptions: Array<{ id: number; name: string }>;
    selectedAssigneeId: number | null;
  };
  resolveAssigneeLoadSuccessState: (input: {
    selectedAssigneeId: number | null;
    assigneeOptions: Array<{ id: number; name: string }>;
  }) => {
    assigneeOptions: Array<{ id: number; name: string }>;
    selectedAssigneeId: number | null;
  };
  resolveAssigneeLoadFailureState: () => {
    assigneeOptions: Array<{ id: number; name: string }>;
    selectedAssigneeId: number | null;
  };
  resolveAssigneeOptions: (rows: unknown[]) => Array<{ id: number; name: string }>;
  resolveAssigneePermissionWarning: (input: {
    reasonCodeRaw?: unknown;
    modelRaw?: unknown;
    opRaw?: unknown;
  }) => unknown;
  resolveAssigneePermissionWarningMessage: (input: {
    warning: unknown;
    text: (key: string, fallback: string) => string;
  }) => string;
};

export function useActionViewAssigneeRuntime(options: UseActionViewAssigneeRuntimeOptions) {
  async function loadAssigneeOptions() {
    const loadGuard = options.resolveAssigneeOptionsLoadGuard({
      hasAssigneeField: options.hasAssigneeField.value,
    });
    if (!loadGuard.ok) {
      options.assigneeOptions.value = loadGuard.assigneeOptions;
      options.selectedAssigneeId.value = loadGuard.selectedAssigneeId;
      return;
    }
    try {
      const query = resolveDeclaredAssigneeQuery(options.assigneeOptionsContract.value);
      const result = await listRecords({ ...query, silentErrors: true });
      const rows = Array.isArray(result.records) ? result.records : [];
      const successState = options.resolveAssigneeLoadSuccessState({
        selectedAssigneeId: options.selectedAssigneeId.value,
        assigneeOptions: options.resolveAssigneeOptions(rows as unknown[]),
      });
      options.assigneeOptions.value = successState.assigneeOptions;
      options.selectedAssigneeId.value = successState.selectedAssigneeId;
    } catch (error) {
      const failureState = options.resolveAssigneeLoadFailureState();
      options.assigneeOptions.value = failureState.assigneeOptions;
      options.selectedAssigneeId.value = failureState.selectedAssigneeId;
      if (error instanceof ApiError) {
        const warning = options.resolveAssigneePermissionWarning({
          reasonCodeRaw: error.reasonCode,
          modelRaw: error.details?.model,
          opRaw: error.details?.op,
        });
        const warningMessage = options.resolveAssigneePermissionWarningMessage({ warning, text: options.pageText });
        if (warningMessage) options.batchMessage.value = warningMessage;
      }
    }
  }

  return {
    loadAssigneeOptions,
  };
}
