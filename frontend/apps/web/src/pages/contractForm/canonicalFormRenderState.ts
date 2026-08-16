import type { ContractV2NormalizedStore } from '../../app/contracts/v2/types';
import type { CanonicalFormRenderMode } from '../../app/presentation/canonicalFormRenderModel';
import { presentContractV2Form } from '../../app/presentation/contractFormPresenter';

export function resolveCanonicalFormRenderState(
  store: ContractV2NormalizedStore | null,
  decodeError: string,
  mode: CanonicalFormRenderMode,
) {
  if (decodeError) return { model: null, error: decodeError };
  if (!store) return { model: null, error: 'NORMALIZED_FORM_CONTRACT_MISSING' };
  try {
    return { model: presentContractV2Form(store, mode), error: '' };
  } catch (error) {
    return {
      model: null,
      error: error instanceof Error ? error.message : 'CANONICAL_FORM_PRESENTATION_FAILED',
    };
  }
}
