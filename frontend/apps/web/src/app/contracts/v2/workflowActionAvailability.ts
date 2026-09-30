import type { ContractV2Dictionary } from './types';

export type WorkflowActionIdentity = {
  actionKey?: unknown;
  methodName?: unknown;
  backendIdentity?: unknown;
};

export type WorkflowActionAvailability =
  | { kind: 'unmanaged' }
  | {
    kind: 'managed';
    enabled: boolean;
    reasonCode: string;
    message: string;
    row: ContractV2Dictionary | null;
  }
  | {
    kind: 'error';
    reasonCode: 'WORKFLOW_ACTION_IDENTITY_AMBIGUOUS' | 'WORKFLOW_ACTION_AVAILABILITY_INVALID';
    message: string;
  };

type InspectedWorkflowRow = {
  row: ContractV2Dictionary;
  key: string;
  method: string;
  issue: string;
};

function text(value: unknown): string {
  return String(value ?? '').trim();
}

function record(value: unknown): ContractV2Dictionary {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as ContractV2Dictionary
    : {};
}

function hasOwn(row: ContractV2Dictionary, key: string): boolean {
  return Object.prototype.hasOwnProperty.call(row, key);
}

function inspectWorkflowRow(value: unknown, index: number, declaration = false): InspectedWorkflowRow | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  const row = value as ContractV2Dictionary;
  const target = record(row.target);
  const key = typeof row.key === 'string' ? text(row.key) : '';
  const directMethod = typeof row.method === 'string' ? text(row.method) : '';
  const targetMethod = typeof target.method === 'string' ? text(target.method) : '';
  const method = directMethod || targetMethod;
  let issue = '';
  if ((hasOwn(row, 'key') && typeof row.key !== 'string')
    || (hasOwn(row, 'method') && typeof row.method !== 'string')) {
    issue = `availableActions[${index}] identity must use strings`;
  } else if (hasOwn(row, 'target') && (!row.target || typeof row.target !== 'object' || Array.isArray(row.target))) {
    issue = `availableActions[${index}].target must be an object`;
  } else if (hasOwn(target, 'method') && typeof target.method !== 'string') {
    issue = `availableActions[${index}].target.method must be a string`;
  } else if (directMethod && targetMethod && directMethod !== targetMethod) {
    issue = `actions[${index}] method conflicts with target.method`;
  } else if (!key && !method) {
    issue = `availableActions[${index}] identity is missing`;
  } else if (!declaration && typeof row.enabled !== 'boolean') {
    issue = `availableActions[${index}].enabled must be boolean`;
  }
  return { row, key, method, issue };
}

function rowMatchesIdentity(row: Pick<InspectedWorkflowRow, 'key' | 'method'>, actionKey: string, methodName: string) {
  // A supplied executable method is authoritative; a coincident key cannot
  // redirect it to another method. Key-only callers use the declared key.
  return methodName ? row.method === methodName : Boolean(actionKey) && row.key === actionKey;
}

function invalidAvailability(): WorkflowActionAvailability {
  return { kind: 'error', reasonCode: 'WORKFLOW_ACTION_AVAILABILITY_INVALID', message: '当前流程操作配置无效' };
}

export function resolveWorkflowActionAvailability(
  workflow: ContractV2Dictionary,
  identity: WorkflowActionIdentity,
): WorkflowActionAvailability {
  const actionKey = text(identity.actionKey);
  const methodName = text(identity.methodName);
  if (!actionKey && !methodName) return { kind: 'unmanaged' };
  const hasCatalog = hasOwn(workflow, 'actions');
  if (hasCatalog && !Array.isArray(workflow.actions)) return invalidAvailability();
  const catalog = hasCatalog
    ? (workflow.actions as unknown[]).map((value, index) => inspectWorkflowRow(value, index, true))
    : [];
  if (catalog.some((row) => !row || row.issue)) return invalidAvailability();
  const declarations = catalog.filter((row): row is InspectedWorkflowRow => Boolean(row))
    .filter((row) => rowMatchesIdentity(row, actionKey, methodName));
  if (declarations.length > 1) {
    return { kind: 'error', reasonCode: 'WORKFLOW_ACTION_IDENTITY_AMBIGUOUS', message: '流程操作身份不唯一' };
  }
  if (!hasOwn(workflow, 'availableActions')) {
    if (workflow.availabilityScope === 'declaration_only' && !Number(workflow.record_id || 0)) return { kind: 'unmanaged' };
    return declarations.length ? invalidAvailability() : { kind: 'unmanaged' };
  }
  if (!Array.isArray(workflow.availableActions)) return invalidAvailability();

  const matchingRows = workflow.availableActions
    .map((value, index) => inspectWorkflowRow(value, index))
    .filter((row): row is InspectedWorkflowRow => Boolean(row))
    .filter((row) => rowMatchesIdentity(row, actionKey, methodName));
  if (!matchingRows.length) {
    return declarations.length > 0
      ? {
        kind: 'managed',
        enabled: false,
        reasonCode: 'WORKFLOW_ACTION_NOT_AVAILABLE',
        message: '当前流程状态不允许执行该操作',
        row: null,
      }
      : { kind: 'unmanaged' };
  }
  if ((hasCatalog && !declarations.length) || matchingRows.some((row) => row.issue)) {
    return {
      kind: 'error',
      reasonCode: 'WORKFLOW_ACTION_AVAILABILITY_INVALID',
      message: '当前流程操作配置无效',
    };
  }
  if (matchingRows.length > 1) {
    return {
      kind: 'error',
      reasonCode: 'WORKFLOW_ACTION_IDENTITY_AMBIGUOUS',
      message: `流程操作身份不唯一：${text(identity.backendIdentity) || methodName || actionKey}`,
    };
  }
  const match = matchingRows[0];
  return {
    kind: 'managed',
    enabled: match.row.enabled === true,
    reasonCode: text(match.row.reason_code || match.row.reasonCode),
    message: text(match.row.blocked_message || match.row.message),
    row: match.row,
  };
}

export function workflowActionRows(workflow: ContractV2Dictionary): ContractV2Dictionary[] {
  if (!Array.isArray(workflow.availableActions)) return [];
  return workflow.availableActions
    .map((value, index) => inspectWorkflowRow(value, index))
    .filter((row): row is InspectedWorkflowRow => Boolean(row) && !row?.issue)
    .filter((row) => {
      const availability = resolveWorkflowActionAvailability(workflow, {
        actionKey: row.key,
        methodName: row.method,
      });
      return availability.kind === 'managed' && availability.row === row.row;
    })
    .map((row) => row.row);
}

export function workflowActionRowForMethod(
  workflow: ContractV2Dictionary,
  methodName: string,
): ContractV2Dictionary | null {
  const availability = resolveWorkflowActionAvailability(workflow, { methodName });
  return availability.kind === 'managed' ? availability.row : null;
}

export function isWorkflowTransitionMethod(workflow: ContractV2Dictionary, methodName: string): boolean {
  const method = text(methodName);
  if (!method) return false;
  return resolveWorkflowActionAvailability(workflow, { methodName: method }).kind !== 'unmanaged';
}
