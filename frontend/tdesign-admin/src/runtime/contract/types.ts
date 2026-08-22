export type ContractDictionary = Record<string, unknown>;

export const CONTRACT_VERSION = '2.0.0';
export const ACCEPTED_CONTRACT_VERSIONS = ['2.0.x'] as const;
export const CLIENT_CONTRACT_CAPABILITIES = [
  'container_tree.v2',
  'data_source.v2',
  'action_rule.v2',
  'relation_entry.v2',
  'status_contract.v2',
] as const;

export type ContractCompatibilityStatus = 'compatible' | 'legacy' | 'unsupported';

export interface ContractDecodeIssue {
  path: string;
  code: string;
  message: string;
  severity: 'warning' | 'error';
}

export interface ContractRuntimeMeta {
  requestedVersion: string;
  receivedVersion: string;
  compatibility: ContractCompatibilityStatus;
  reasonCode: string;
  traceId: string;
  suggestedAction: string;
  issues: ContractDecodeIssue[];
}

export interface ExecutablePageContract extends ContractDictionary {
  pageInfo: ContractDictionary;
  layoutContract: ContractDictionary;
  statusContract: ContractDictionary;
  actionContract: ContractDictionary;
  dataContract: ContractDictionary;
  runtimeContract: ContractDictionary;
  searchContract: ContractDictionary;
  formStructureContract: ContractDictionary;
  workflowContract: ContractDictionary;
  __contractRuntime: ContractRuntimeMeta;
  __rawContract: ContractDictionary;
}

export interface ContractLoadOptions {
  actionId?: number;
  menuId?: number;
  model?: string;
  recordId?: number;
  viewType?: string;
  renderProfile?: 'create' | 'edit' | 'readonly';
  context?: ContractDictionary;
  deliveryProfile?: 'full' | 'compact';
}
