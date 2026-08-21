import { computed, type Ref } from 'vue';
import { resolveContractV2SurfacePolicies } from '../contracts/v2/store';
import type { ContractV2NormalizedStore } from '../contracts/v2/types';

type Dict = Record<string, unknown>;

type UseActionViewSurfaceIntentRuntimeOptions = {
  actionContract: Ref<ContractV2NormalizedStore | null>;
  strictContractMode: Ref<boolean>;
  strictSurfaceContract: Ref<Dict>;
  pageText: (key: string, fallback?: string) => string;
  resolveActionViewSurfaceIntent: (input: Dict) => unknown;
};

export function useActionViewSurfaceIntentRuntime(options: UseActionViewSurfaceIntentRuntimeOptions) {
  const contractSurfaceIntent = computed<Dict>(() => {
    const surfacePolicies = resolveContractV2SurfacePolicies(options.actionContract.value);
    const fromSurfacePolicies = surfacePolicies.intent_profile;
    if (fromSurfacePolicies && typeof fromSurfacePolicies === 'object' && !Array.isArray(fromSurfacePolicies)) {
      return fromSurfacePolicies as Dict;
    }
    return {};
  });

  const surfaceIntent = computed(() => {
    return options.resolveActionViewSurfaceIntent({
      strictContractMode: options.strictContractMode.value,
      strictSurfaceContract: options.strictSurfaceContract.value,
      contractSurfaceIntent: contractSurfaceIntent.value,
      pageText: options.pageText,
    });
  });

  return {
    contractSurfaceIntent,
    surfaceIntent,
  };
}
