import {
  resolveContractV2SearchContract,
  resolveContractV2WorkflowContract,
  type ContractV2NormalizedStore,
} from '../../app/contracts/v2';

export type ContractFormMetaLineInput = {
  store: ContractV2NormalizedStore | null;
  contractMeta: Record<string, unknown> | null;
  rights: { read?: boolean; write?: boolean; create?: boolean; unlink?: boolean };
  renderProfile: string;
};

const PROFILE_LABELS: Record<string, string> = {
  create: '新建',
  edit: '编辑',
  readonly: '只读',
};

const CONTRACT_MODE_LABELS: Record<string, string> = {
  native: '标准表单',
  governed: '受控表单',
  action: '操作页面',
  legacy: '历史承载',
};

const CONTRACT_SURFACE_LABELS: Record<string, string> = {
  native: '标准界面',
  governed: '受控界面',
  business_config: '配置界面',
  lowcode_config: '低代码配置',
};

const VIEW_TYPE_LABELS: Record<string, string> = {
  form: '表单',
  tree: '列表',
  list: '列表',
  kanban: '看板',
  search: '搜索',
  calendar: '日历',
  pivot: '透视',
  graph: '图表',
};

function countArray(value: unknown): number {
  return Array.isArray(value) ? value.length : 0;
}

function labeledValue(value: unknown, labels: Record<string, string>): string {
  const raw = String(value || '-');
  const normalized = raw.trim().toLowerCase();
  if (!normalized || normalized === '-') return '未配置';
  return labels[normalized] || raw;
}

/** Debug meta line for the record form header. Contract/store remain authoritative. */
export function resolveContractFormMetaLine(input: ContractFormMetaLineInput): string {
  if (!input.store) return '';
  const mode = String(input.contractMeta?.contract_mode || '-');
  const surface = String(input.contractMeta?.contract_surface || '-');
  const viewType = String(input.store.snapshot.pageInfo.viewType || '-');
  const filters = countArray(resolveContractV2SearchContract(input.store).filters);
  const transitions = countArray(resolveContractV2WorkflowContract(input.store).transitions);
  const permissionLabels = [
    input.rights.read ? '可查看' : '',
    input.rights.write ? '可编辑' : '',
    input.rights.create ? '可新建' : '',
    input.rights.unlink ? '可删除' : '',
  ].filter(Boolean);
  const profileLabel = PROFILE_LABELS[input.renderProfile] || input.renderProfile;
  return `配置模式：${labeledValue(mode, CONTRACT_MODE_LABELS)} · 承载界面：${labeledValue(surface, CONTRACT_SURFACE_LABELS)} · 视图类型：${labeledValue(viewType, VIEW_TYPE_LABELS)} · 页面状态：${profileLabel} · 筛选项：${filters} · 流转项：${transitions} · 操作权限：${permissionLabels.join('、') || '无可用权限'}`;
}
