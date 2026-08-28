/* Next-task action resolver factory.
 *
 * legal_next_action_display (task semantic role, shown inside the "当前任务"
 * card) is a plain text hint computed by the backend state machine. The text
 * is already permission-gated on the backend (a user only sees "提交审批" if
 * they may submit), so mapping the label back to its backend method is safe.
 * This turns the dead readonly text into a clickable action entry point.
 *
 * The factory keeps the mapping and matching rules out of ContractFormPage so
 * the page stays under its size budget while still wiring the resolver via
 * ScTaskActionResolverKey.
 */
import type { ScTaskActionResolver } from './taskActionResolver';

const NEXT_ACTION_METHOD_BY_LABEL: Record<string, string> = {
  '提交审批': 'action_submit',
  '重新提交审批': 'action_submit',
  '审批处理': 'action_approve',
  '生成付款登记': 'action_create_payment_execution',
  '查看付款登记': 'action_view_payment_execution',
  '确认办结': 'action_done',
};

export type NextTaskActionDeps = {
  getRecordId: () => number | undefined;
  runAction: (label: string, methodName: string) => Promise<void>;
};

export function createNextTaskActionResolver(deps: NextTaskActionDeps): ScTaskActionResolver {
  return (field) => {
    if (!field || String(String(field.name || '')).trim() !== 'legal_next_action_display') return null;
    if (!deps.getRecordId()) return null;
    const label = String((field.value as string | undefined) ?? '').trim();
    const methodName = NEXT_ACTION_METHOD_BY_LABEL[label];
    if (!methodName) return null;
    return {
      label,
      run: () => deps.runAction(label, methodName),
    };
  };
}
