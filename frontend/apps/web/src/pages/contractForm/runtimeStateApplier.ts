import type { FormRuntimeBusyRefs, FormRuntimeStateEvent, FormRuntimeStatusRefs } from './runtimeStateProtocol';
import { INITIAL_FORM_RUNTIME_STATE, reduceFormRuntimeState } from './runtimeStateReducer';

type FormRuntimeStatusEvent = Extract<FormRuntimeStateEvent, { kind: 'status' }>;
type FormRuntimeBusyEvent = Extract<FormRuntimeStateEvent, { kind: 'begin' } | { kind: 'end' }>;

export function applyFormRuntimeStatusEvent(
  refs: FormRuntimeStatusRefs,
  event: FormRuntimeStatusEvent,
) {
  const next = reduceFormRuntimeState({
    ...INITIAL_FORM_RUNTIME_STATE,
    status: refs.status.value,
    errorMessage: refs.errorMessage.value,
  }, event);
  refs.status.value = next.status;
  refs.errorMessage.value = next.errorMessage;
}

export function applyFormRuntimeBusyEvent(
  refs: FormRuntimeBusyRefs,
  event: FormRuntimeBusyEvent,
) {
  const next = reduceFormRuntimeState({
    ...INITIAL_FORM_RUNTIME_STATE,
    busyKind: refs.busyKind.value,
    busyActionIdentity: refs.busyActionIdentity?.value || '',
  }, event);
  refs.busyKind.value = next.busyKind;
  if (refs.busyActionIdentity) refs.busyActionIdentity.value = next.busyActionIdentity;
}

export function beginFormRuntimeBusy(
  refs: FormRuntimeBusyRefs,
  transaction: FormRuntimeBusyEvent['transaction'],
  busyKind: Extract<FormRuntimeBusyEvent, { kind: 'begin' }>['busyKind'],
  actionIdentity = '',
) {
  applyFormRuntimeBusyEvent(refs, {
    kind: 'begin',
    transaction,
    busyKind,
    actionIdentity,
  });
}

export function endFormRuntimeBusy(
  refs: FormRuntimeBusyRefs,
  transaction: FormRuntimeBusyEvent['transaction'],
  actionIdentity = '',
) {
  applyFormRuntimeBusyEvent(refs, {
    kind: 'end',
    transaction,
    actionIdentity,
  });
}
