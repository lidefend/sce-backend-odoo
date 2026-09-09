import type { ContractV2Dictionary, ContractV2NormalizedStore } from '../../app/contracts/v2/types';
import type {
  CanonicalFormNode,
  CanonicalFormRenderMode,
  CanonicalFormRenderModel,
} from '../../app/presentation/canonicalFormRenderModel';
import { presentContractV2Form } from '../../app/presentation/contractFormPresenter';

export function applyCanonicalFormValidation(
  model: CanonicalFormRenderModel,
  validationFieldErrors: Record<string, string> = {},
): CanonicalFormRenderModel {
  const decorateNode = (node: CanonicalFormNode): CanonicalFormNode => ({
    ...node,
    fields: node.fields.map((field) => {
      const errorText = String(validationFieldErrors[field.fieldCode] || '').trim();
      return { ...field, invalid: Boolean(errorText), errorText };
    }),
    children: node.children.map(decorateNode),
  });
  return {
    ...model,
    zones: {
      primary: model.zones.primary.map(decorateNode),
      subordinate: model.zones.subordinate.map(decorateNode),
    },
  };
}

export function resolveCanonicalFormRenderState(
  store: ContractV2NormalizedStore | null,
  decodeError: string,
  mode: CanonicalFormRenderMode,
  runtimeValues?: ContractV2Dictionary,
  validationFieldErrors: Record<string, string> = {},
) {
  if (decodeError) return { model: null, error: decodeError };
  if (!store) return { model: null, error: 'NORMALIZED_FORM_CONTRACT_MISSING' };
  try {
    return {
      model: applyCanonicalFormValidation(presentContractV2Form(store, mode, runtimeValues), validationFieldErrors),
      error: '',
    };
  } catch (error) {
    return {
      model: null,
      error: error instanceof Error ? error.message : 'CANONICAL_FORM_PRESENTATION_FAILED',
    };
  }
}
