import { intent } from '@/api/odoo';

import { contractClientDeclaration } from './clientCapabilities';
import { decodeExecutableContract } from './decoder';
import type { ContractDictionary, ContractLoadOptions, ExecutablePageContract } from './types';

function positiveId(value: unknown): number | undefined {
  const parsed = Number(value || 0);
  return Number.isFinite(parsed) && parsed > 0 ? Math.trunc(parsed) : undefined;
}

function commonParams(options: ContractLoadOptions): ContractDictionary {
  return {
    ...contractClientDeclaration(),
    action_id: positiveId(options.actionId),
    menu_id: positiveId(options.menuId),
    record_id: positiveId(options.recordId),
    view_type: options.viewType || undefined,
    render_profile: options.renderProfile || undefined,
    context: options.context || {},
    delivery_profile: options.deliveryProfile || 'full',
  };
}

async function loadContract(params: ContractDictionary): Promise<ExecutablePageContract> {
  return decodeExecutableContract(await intent<ContractDictionary>('ui.contract.v2', params));
}

export function loadActionContract(options: ContractLoadOptions): Promise<ExecutablePageContract> {
  return loadContract({
    ...commonParams(options),
    op: 'action_open',
  });
}

export function loadFormContract(options: ContractLoadOptions): Promise<ExecutablePageContract> {
  return loadContract({
    ...commonParams({ ...options, viewType: options.viewType || 'form' }),
    op: 'model',
    model: String(options.model || '').trim(),
  });
}
