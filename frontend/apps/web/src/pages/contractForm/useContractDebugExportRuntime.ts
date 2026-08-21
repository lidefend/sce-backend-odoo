import type { Ref } from 'vue';
import type { ContractV2NormalizedStore } from '../../app/contracts/v2';

export function useContractDebugExportRuntime(params: {
  actionId: () => number;
  store: Ref<ContractV2NormalizedStore | null>;
  modelName: () => string;
}) {
  function contractDebugPayload() {
    return JSON.stringify(
      {
        action_id: params.actionId(),
        model: params.modelName(),
        contract: params.store.value?.snapshot || null,
        meta: params.store.value?.snapshot.meta || {},
      },
      null,
      2,
    );
  }

  async function copyContractJson() {
    if (!params.store.value) return;
    try {
      await navigator.clipboard.writeText(contractDebugPayload());
    } catch {
      // Clipboard access can be blocked by browser permissions.
    }
  }

  function exportContractJson() {
    if (!params.store.value) return;
    const blob = new Blob([contractDebugPayload()], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `contract_form_${params.modelName() || 'unknown'}_${params.actionId() || 'na'}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return {
    copyContractJson,
    exportContractJson,
  };
}
