import type { CanonicalFormAction } from '../../app/presentation/canonicalFormRenderModel';
import type { NativeStatusbarVm } from './types';

export function workflowDisabledReason(action: CanonicalFormAction): string {
  if (action.enabled) return '';
  return String(action.reasonCode || '').trim() || '当前操作不可用';
}

export function resolveWorkflowActionBarAuthority(
  directActions: readonly CanonicalFormAction[],
  overflowActions: readonly CanonicalFormAction[],
  effectivePrimaryKey: string,
) {
  const visible = [...directActions, ...overflowActions].filter((action) => action.visible);
  const primary = visible.filter((action) => action.key === effectivePrimaryKey);
  if (primary.length > 1) throw new Error('PROFESSIONAL_WORKFLOW_PRIMARY_MULTIPLE');
  return Object.freeze({
    actionCount: visible.length,
    directCount: directActions.length,
    overflowCount: overflowActions.length,
    disabledCount: visible.filter((action) => !action.enabled).length,
    primaryKey: primary[0]?.key || '',
  });
}

export function resolveWorkflowStatusAuthority(statusbar: NativeStatusbarVm) {
  if (!statusbar.visible) return Object.freeze({ visible: false, current: '', stateCount: 0, readonly: true });
  if (!statusbar.current || !statusbar.states.length) throw new Error('PROFESSIONAL_WORKFLOW_STATUS_INCOMPLETE');
  return Object.freeze({
    visible: true,
    current: statusbar.current,
    stateCount: statusbar.states.length,
    readonly: statusbar.readonly,
  });
}
