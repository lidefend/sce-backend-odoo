import { parseMaybeJsonRecord } from '../../app/contractRuntime';
import { contractGapError } from '../../app/contract/contractGap';
import { dictOrEmpty } from './recordUtils';
import type { FieldDescriptor } from '@sc/schema';
import { resolveContractV2WorkflowContract, type ContractV2NormalizedStore } from '../../app/contracts/v2';
import type { NativeStatusbarVm, StatusbarState } from './types';
import { workflowActionRows } from '../../app/contracts/v2/workflowActionAvailability';

export type NativeFormStatusbarInput = {
  recordId: number;
  formView: unknown;
  fields: Record<string, FieldDescriptor>;
  formData: Record<string, unknown>;
  mainData: Record<string, unknown>;
  fieldReadonly: (field: string) => boolean;
  readonly: boolean;
  fallback: NativeStatusbarVm;
};

export function normalizeWorkflowActionRows(
  workflow: Record<string, unknown>,
  modelName: string,
): Array<Record<string, unknown>> {
  return workflowActionRows(workflow)
    .map((row) => {
      const target = parseMaybeJsonRecord(row.target);
      const method = String(row.method || target.method || '').trim();
      const key = String(row.key || method || '').trim();
      return {
        key,
        label: String(row.label || key).trim() || key,
        kind: method ? 'object' : 'client',
        level: 'header',
        selection: 'none',
        intent: String(row.intent || '').trim(),
        allowed: row.enabled !== false,
        blocked_message: String(row.blocked_message || row.message || '').trim(),
        reason_code: String(row.reason_code || row.reasonCode || '').trim(),
        target_model: String(target.model || row.model || modelName || '').trim(),
        payload: {
          method,
          context_raw: target.context_raw,
        },
        target: {
          ...target,
          method,
        },
        visible_profiles: ['edit', 'readonly'],
        source_widget_id: 'workflow.contract',
        workflow_contract_action: true,
      };
    })
    .filter((row) => String(row.key || '').trim());
}

export function normalizeWorkflowEvidenceGateRows(workflow: Record<string, unknown>) {
  const rows = Array.isArray(workflow.evidenceGate) ? workflow.evidenceGate : [];
  const seen = new Set<string>();
  return rows
    .map((raw) => (raw && typeof raw === 'object' && !Array.isArray(raw) ? raw as Record<string, unknown> : null))
    .filter((row): row is Record<string, unknown> => Boolean(row))
    .map((row, index) => {
      const reasonCode = String(row.reasonCode || row.reason_code || `workflow_gate_${index}`).trim();
      return {
        reasonCode,
        message: String(row.message || reasonCode).trim(),
        blocking: row.blocking !== false,
        severity: String(row.severity || '').trim(),
      };
    })
    .filter((row) => {
      if (!row.message || seen.has(row.reasonCode)) return false;
      seen.add(row.reasonCode);
      return true;
    });
}

export function normalizeWorkflowPhaseStatusbar(workflow: Record<string, unknown>): NativeStatusbarVm {
  const raw = workflow.statusbar;
  if (raw === undefined || raw === null) {
    return { visible: false, field: '', current: '', states: [], reachedValues: [], readonly: true };
  }
  const gap = (detail: string): never => {
    throw contractGapError({
      kind: 'contract_defect',
      missing: 'workflowContract.statusbar',
      requiredDeclarationLayer: 'P1:smart_construction_core:workflow_contract_service',
    }, `workflowContract.statusbar ${detail}`);
  };
  if (typeof raw !== 'object' || Array.isArray(raw)) gap('must be an object');
  const statusbar = raw as Record<string, unknown>;
  const field = typeof statusbar.field === 'string' ? statusbar.field.trim() : '';
  const current = typeof statusbar.current === 'string' ? statusbar.current.trim() : '';
  if (!field) gap('field must be a non-empty string');
  if (!current) gap('current must be a non-empty string');
  if (statusbar.readonly !== true) gap('readonly must be true');
  if (statusbar.source !== 'workflowContract') gap('source must be workflowContract');
  if (!Array.isArray(statusbar.states) || !statusbar.states.length) gap('states must be a non-empty array');
  const seen = new Set<string>();
  const states = (statusbar.states as unknown[]).map((item, index) => {
    if (!item || typeof item !== 'object' || Array.isArray(item)) gap(`states[${index}] must be an object`);
    const state = item as Record<string, unknown>;
    const value = typeof state.value === 'string' ? state.value.trim() : '';
    const label = typeof state.label === 'string' ? state.label.trim() : '';
    if (!value || !label) gap(`states[${index}] requires non-empty value and label`);
    if (seen.has(value)) gap(`states[${index}] duplicates ${value}`);
    seen.add(value);
    return { value, label };
  });
  if (!seen.has(current)) gap(`current ${current} is not listed in states`);
  return {
    visible: true,
    field,
    current,
    states,
    // Selection order describes display order, not the record's transition history.
    reachedValues: [],
    readonly: true,
  };
}

export function normalizeNativeFormStatusbar(input: NativeFormStatusbarInput): NativeStatusbarVm {
  const formView = dictOrEmpty(input.formView);
  const raw = dictOrEmpty(formView.statusbar);
  const field = String(raw.field || '').trim();
  const descriptor = field ? input.fields[field] : undefined;
  const rawStates = Array.isArray(raw.states) ? raw.states as Array<Record<string, unknown>> : [];
  const selectionStates = Array.isArray(descriptor?.selection)
    ? descriptor.selection.map((item) => {
      const pair = item as unknown[];
      return { value: String(pair[0] ?? ''), label: String(pair[1] ?? pair[0] ?? '') };
    })
    : [];
  const states: StatusbarState[] = (rawStates.length
    ? rawStates.map((item) => ({ value: item.value as string | number, label: String(item.label || item.value || '') }))
    : selectionStates)
    .filter((item) => String(item.value ?? '').trim() && String(item.label || '').trim());
  if (!input.recordId) {
    return { visible: false, field, current: '', states, reachedValues: [], readonly: true };
  }
  const rawFormStatus = input.formData[field];
  const formStatusValue = rawFormStatus === false || rawFormStatus == null ? '' : String(rawFormStatus).trim();
  const current = String(
    formStatusValue
      || (Object.prototype.hasOwnProperty.call(input.mainData, field) ? input.mainData[field] : '')
      || '',
  ).trim();
  const currentIndex = states.findIndex((item) => String(item.value) === current);
  if (!field || !states.length) return input.fallback;
  return {
    visible: true,
    field,
    current,
    states,
    reachedValues: currentIndex >= 0 ? states.slice(0, currentIndex).map((item) => String(item.value)) : [],
    readonly: Boolean(input.fieldReadonly(field) || input.readonly),
  };
}

export function resolveStatusbarSelectionValue(descriptor: FieldDescriptor | undefined, value: unknown) {
  const raw = String(value || '').trim();
  const selection = Array.isArray(descriptor?.selection) ? descriptor.selection : [];
  if (!selection.length) return raw || false;
  const byCode = selection.find((item) => String((item as unknown[])[0] ?? '') === raw);
  const byLabel = selection.find((item) => String((item as unknown[])[1] ?? '') === raw);
  const matched = byCode || byLabel;
  return matched ? String((matched as unknown[])[0] ?? raw) || false : raw || false;
}

export function resolveWorkflowContractFromStore(
  store: ContractV2NormalizedStore | null,
): Record<string, unknown> {
  return resolveContractV2WorkflowContract(store);
}
