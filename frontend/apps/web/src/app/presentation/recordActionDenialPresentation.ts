import type { ContractRecordActionState } from '../contracts/v2/store';

const operationLabels: Partial<Record<ContractRecordActionState['operation'], string>> = {
  write: '编辑', unlink: '删除',
};
const reasonLabels: Record<string, string> = {
  MODEL_ACCESS_DENIED: '当前账号没有此操作权限',
  RECORD_RULE_DENIED: '当前记录不在可操作范围内',
  RECORD_NOT_FOUND: '记录已不存在或不可访问',
  RECORD_AUTHORITY_UNRESOLVED: '暂时无法确认记录权限',
  BUSINESS_DOCUMENT_STATE_NOT_DELETABLE: '当前业务状态不允许删除',
  DELETE_POLICY_DENIED: '当前记录的删除策略不允许此操作',
};

/** Explain only explicit denials for supported record operations; never grant an action. */
export function describeRecordActionDenials(states: ContractRecordActionState[]): string[] {
  return states.flatMap((state) => {
    const label = operationLabels[state.operation];
    if (!label || state.allowed || !state.reasonCode) return [];
    return [`不可${label}：${reasonLabels[state.reasonCode] || '当前契约未允许此操作'}`];
  });
}
