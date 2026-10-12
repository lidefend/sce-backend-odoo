import assert from 'node:assert/strict';

import { resolveRecordDeleteDecision } from '../src/app/presentation/recordDeleteAction';
import type { ContractV2NormalizedStore } from '../src/app/contracts/v2';

/**
 * The record delete control is projected from the contract's own record-operation
 * disposition. These cases pin the two facts that matter: the control appears only
 * when the contract grants the capability, and a declared denial is never relaxed
 * into an enabled control.
 */
function store(overrides: {
  capabilities?: Record<string, boolean>;
  deniedReasons?: Record<string, string>;
  deletePolicy?: Record<string, unknown>;
  mainData?: Record<string, unknown>;
}): ContractV2NormalizedStore {
  return {
    snapshot: {
      statusContract: {
        globalStatus: {
          pageVisible: true,
          pageAuth: 'write',
          ...(overrides.capabilities ? { effectiveRecordCapabilities: overrides.capabilities } : {}),
          ...(overrides.deniedReasons ? { recordDeniedReasons: overrides.deniedReasons } : {}),
        },
      },
      actionContract: overrides.deletePolicy ? { deletePolicy: overrides.deletePolicy } : {},
      dataContract: { mainData: overrides.mainData || {} },
    },
  } as unknown as ContractV2NormalizedStore;
}

const base = { label: '删除' } as const;

// 1. No record (create surface) has nothing to delete.
assert.equal(resolveRecordDeleteDecision({
  store: store({ capabilities: { unlink: true } }), hasRecord: false, renderProfile: 'edit', ...base,
}).action, null, 'a create surface must not offer a record delete');

// 2. The create profile never offers delete, even when the capability is granted.
assert.equal(resolveRecordDeleteDecision({
  store: store({ capabilities: { unlink: true } }), hasRecord: true, renderProfile: 'create', ...base,
}).action, null, 'the create profile must not offer a record delete');

// 3. Configuration preview performs no business write.
assert.equal(resolveRecordDeleteDecision({
  store: store({ capabilities: { unlink: true } }), hasRecord: true, renderProfile: 'edit',
  isConfigurationPreview: true, ...base,
}).action, null, 'a configuration preview must not offer a record delete');

// 4. A contract that grants nothing stays closed (fail-closed default).
assert.equal(resolveRecordDeleteDecision({
  store: store({}), hasRecord: true, renderProfile: 'edit', ...base,
}).action, null, 'an undeclared capability must not enable the control');

// 5. An explicit capability denial keeps the contract's reason and no control.
const capabilityDenied = resolveRecordDeleteDecision({
  store: store({ capabilities: { unlink: false }, deniedReasons: { unlink: 'RECORD_ACTION_DENIED' } }),
  hasRecord: true, renderProfile: 'edit', ...base,
});
assert.equal(capabilityDenied.action, null, 'a denied capability must not render');
assert.equal(capabilityDenied.deniedReason, 'RECORD_ACTION_DENIED', 'the declared reason must survive');

// 6. `deletePolicy.allowed === false` is an authoritative denial.
const policyDenied = resolveRecordDeleteDecision({
  store: store({ capabilities: { unlink: true }, deletePolicy: { allowed: false, reason_code: 'PROJECT_MASTER_DELETE_DENIED' } }),
  hasRecord: true, renderProfile: 'edit', ...base,
});
assert.equal(policyDenied.action, null, 'a declared delete policy denial must not render');
assert.equal(policyDenied.deniedReason, 'PROJECT_MASTER_DELETE_DENIED', 'the policy reason must survive');

// 7. A declared state gate blocks a record outside its allowed states.
const stateBlocked = resolveRecordDeleteDecision({
  store: store({
    capabilities: { unlink: true },
    deletePolicy: { policy_kind: 'state_limited_business_document', state_field: 'state', allowed_states: ['draft'], denied_reason_code: 'STATE_DELETE_DENIED' },
    mainData: { state: 'done' },
  }),
  hasRecord: true, renderProfile: 'edit', ...base,
});
assert.equal(stateBlocked.action, null, 'a state gate must block an out-of-state record');
assert.equal(stateBlocked.deniedReason, 'STATE_DELETE_DENIED', 'the state gate reason must survive');

// 8. A granted capability with a passing state gate renders one enabled control.
const allowed = resolveRecordDeleteDecision({
  store: store({
    capabilities: { unlink: true },
    deletePolicy: { policy_kind: 'state_limited_business_document', state_field: 'state', allowed_states: ['draft'] },
    mainData: { state: 'draft' },
  }),
  hasRecord: true, renderProfile: 'edit', ...base,
});
assert.equal(allowed.action?.key, 'record.delete');
assert.equal(allowed.action?.label, '删除');
assert.equal(allowed.action?.semantic, 'danger');
assert.equal(allowed.action?.enabled, true);

// 9. Busy surfaces disable the control instead of dropping it.
assert.equal(resolveRecordDeleteDecision({
  store: store({ capabilities: { unlink: true } }), hasRecord: true, renderProfile: 'readonly', busy: true, ...base,
}).action?.enabled, false, 'a busy record surface disables rather than hides the control');

// 10. A readonly record with a granted capability still offers delete (Odoo parity).
assert.equal(resolveRecordDeleteDecision({
  store: store({ capabilities: { unlink: true } }), hasRecord: true, renderProfile: 'readonly', ...base,
}).action?.enabled, true, 'a granted readonly record keeps the control');

console.log('[record_delete_action] PASS cases=10');
