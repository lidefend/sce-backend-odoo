import {
  resolveContractV2RecordActionStates,
  type ContractV2NormalizedStore,
} from '../contracts/v2';

/**
 * The record-level delete affordance this build may render.
 *
 * The `label` is the declared text the surface renders; `reason` carries the
 * contract's own denial reason when the operation exists but is denied, so a
 * hidden control is never the only signal the terminal gives.
 */
export type RecordDeleteAction = {
  key: 'record.delete';
  label: string;
  semantic: 'danger';
  enabled: boolean;
  reason: string;
};

export type RecordDeleteDecision = {
  action: RecordDeleteAction | null;
  /** The declared reason when the contract names the operation but denies it. */
  deniedReason: string;
};

/**
 * Turn the contract's declared record-operation disposition into the delete
 * control, or into the declared denial reason.
 *
 * The contract owns whether the operation exists and whether this record may run
 * it: `statusContract.globalStatus.effectiveRecordCapabilities.unlink` names the
 * capability the authorities granted, and `actionContract.deletePolicy` adds the
 * state gate a business document declares on top. This module never decides that
 * delete exists, never relaxes a declared denial, and never invents a reason the
 * contract did not publish — it only projects the declared verdict into the one
 * control the record surface renders.
 */
export function resolveRecordDeleteDecision(options: {
  store: ContractV2NormalizedStore | null;
  hasRecord: boolean;
  renderProfile: string;
  label: string;
  busy?: boolean;
  isConfigurationPreview?: boolean;
}): RecordDeleteDecision {
  if (options.isConfigurationPreview) return { action: null, deniedReason: '' };
  if (!options.hasRecord) return { action: null, deniedReason: '' };
  const profile = String(options.renderProfile || '').trim().toLowerCase();
  if (profile === 'create') return { action: null, deniedReason: '' };
  const state = resolveContractV2RecordActionStates(options.store)
    .find((row) => row.operation === 'unlink');
  if (!state) return { action: null, deniedReason: '' };
  if (!state.allowed) return { action: null, deniedReason: String(state.reasonCode || '').trim() };
  return {
    action: {
      key: 'record.delete',
      label: options.label,
      semantic: 'danger',
      enabled: !options.busy,
      reason: '',
    },
    deniedReason: '',
  };
}
