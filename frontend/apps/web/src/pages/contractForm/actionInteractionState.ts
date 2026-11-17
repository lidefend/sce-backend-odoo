import { inject, provide, readonly, ref, type Ref } from 'vue';
import type { CanonicalFormAction } from '../../app/presentation/canonicalFormRenderModel';

const ACTION_EXECUTION_IDENTITY = Symbol('contract-form-action-execution-identity');
const NO_ACTION_EXECUTION_IDENTITY = '';
const EMPTY_ACTION_EXECUTION_IDENTITY = readonly(ref(NO_ACTION_EXECUTION_IDENTITY));

function text(value: unknown): string {
  return String(value ?? '').trim();
}

/**
 * Page-level identity of the action whose request currently owns the busy state.
 * The contract supplies action identity; this ref only records which declared
 * action is executing so every presentation surface can consume the same fact.
 */
export function provideActionExecutionIdentity(identity: Ref<string>): void {
  provide(ACTION_EXECUTION_IDENTITY, identity);
}

export function useActionExecutionIdentity(): Readonly<Ref<string>> {
  const identity = inject<Readonly<Ref<string>>>(ACTION_EXECUTION_IDENTITY, undefined);
  return identity || EMPTY_ACTION_EXECUTION_IDENTITY;
}

export function actionExecutionCandidates(action: CanonicalFormAction): string[] {
  return [
    text(action.actionRef.backendIdentity),
    text(action.actionRef.actionId),
    text(action.actionRef.actionKey),
    text(action.key),
  ].filter(Boolean);
}

export function resolveActionInteractionState(
  action: CanonicalFormAction,
  busyActionIdentity = '',
) {
  const identity = text(busyActionIdentity);
  const identifiedAsBusy = Boolean(identity) && actionExecutionCandidates(action).includes(identity);
  const loading = action.loading === true || identifiedAsBusy;
  return {
    loading,
    disabled: !action.enabled || loading,
  };
}
