import type { ContractV2Dictionary, ContractV2NormalizedStore } from '../../app/contracts/v2/types';
import type {
  CanonicalFormField,
  CanonicalFormNode,
  CanonicalFormRenderMode,
  CanonicalFormRenderModel,
} from '../../app/presentation/canonicalFormRenderModel';
import { presentContractV2Form } from '../../app/presentation/contractFormPresenter';
import { errorOwnsField, type BusinessFieldError } from '../../app/businessValidationError';

export type CanonicalValidationErrorScope = {
  model?: string;
  recordId?: number | null;
};

/**
 * One field code can be rendered at several positions. The business error is
 * owned by the field, not by one of those positions, so the message is shown
 * once, on the position the user can correct. A read-only occurrence of the same
 * field keeps showing the value and is not decorated as a correction site.
 *
 * The occurrence that produced the value is preferred while it is still a
 * correctable position of the same field, so the message and the focus resolve
 * to the same place. When that source is gone or no longer correctable the
 * choice is deterministic rather than document order.
 */
function correctableOccurrence(field: CanonicalFormField): boolean {
  if (!field.visible || field.readonly || field.disabled) return false;
  return field.renderProfile !== 'readonly';
}

function collectFields(model: CanonicalFormRenderModel): CanonicalFormField[] {
  const fields: CanonicalFormField[] = [];
  const walk = (node: CanonicalFormNode) => {
    node.fields.forEach((field) => fields.push(field));
    node.children.forEach(walk);
  };
  [...model.zones.primary, ...model.zones.subordinate].forEach(walk);
  return fields;
}

export function applyCanonicalFormValidation(
  model: CanonicalFormRenderModel,
  validationFieldErrors: Record<string, BusinessFieldError> = {},
  errorScope: CanonicalValidationErrorScope = {},
): CanonicalFormRenderModel {
  const scope = {
    model: String(errorScope.model || model.identity.model || '').trim(),
    recordId: errorScope.recordId ?? null,
  };
  const occurrences = collectFields(model);
  const decoration = new Map<string, { widgetId: string; message: string }>();
  occurrences.forEach((field) => {
    const fieldCode = String(field.fieldCode || '').trim();
    if (!fieldCode || decoration.has(fieldCode)) return;
    // The store is keyed by the business display key, which for a record-level
    // field error is the field code itself, so the direct lookup is the
    // authoritative one and can never match a row error of the same relation
    // field. The scan is only a fallback for a key that was not trimmed.
    const direct = validationFieldErrors[field.fieldCode];
    const error = errorOwnsField(direct, {
      model: scope.model,
      recordId: scope.recordId,
      fieldCode,
    })
      ? direct
      : Object.values(validationFieldErrors || {}).find((candidate) => errorOwnsField(candidate, {
        model: scope.model,
        recordId: scope.recordId,
        fieldCode,
      }));
    if (!error) return;
    const siblings = occurrences.filter((candidate) => candidate.fieldCode === fieldCode);
    const source = String(error.sourceOccurrenceKey || '').trim();
    const chosen = siblings.find((candidate) => candidate.widgetId === source && correctableOccurrence(candidate))
      || siblings.find(correctableOccurrence)
      || siblings.find((candidate) => candidate.visible);
    if (chosen) decoration.set(fieldCode, { widgetId: chosen.widgetId, message: error.message });
  });
  const decorateNode = (node: CanonicalFormNode): CanonicalFormNode => ({
    ...node,
    fields: node.fields.map((field) => {
      const entry = decoration.get(field.fieldCode);
      const errorText = entry && entry.widgetId === field.widgetId ? entry.message : '';
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
  validationFieldErrors: Record<string, BusinessFieldError> = {},
  errorScope: CanonicalValidationErrorScope = {},
) {
  if (decodeError) return { model: null, error: decodeError };
  if (!store) return { model: null, error: 'NORMALIZED_FORM_CONTRACT_MISSING' };
  try {
    return {
      model: applyCanonicalFormValidation(
        presentContractV2Form(store, mode, runtimeValues, {
          recordPersisted: Number(errorScope?.recordId || 0) > 0,
        }),
        validationFieldErrors,
        errorScope,
      ),
      error: '',
    };
  } catch (error) {
    return {
      model: null,
      error: error instanceof Error ? error.message : 'CANONICAL_FORM_PRESENTATION_FAILED',
    };
  }
}
