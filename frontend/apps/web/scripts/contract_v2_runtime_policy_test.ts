import assert from 'node:assert/strict';

import { permitsContractV2SnapshotReuse } from '../src/app/contracts/v2/runtime';
import { resolveContractV2RuntimePolicy } from '../src/app/contracts/v2/store';
import type { ContractV2RuntimeContract } from '../src/app/contracts/v2/types';
import { resolveContractFormReadContext } from '../src/pages/contractForm/contractRuntimeVm';

function runtime(cachePolicy: ContractV2RuntimeContract['cachePolicy']): ContractV2RuntimeContract {
  return {
    patchStrategy: 'incremental',
    cachePolicy,
    optimistic: false,
    lazyContainer: [],
    virtualization: {},
    retryPolicy: { maxRetries: 1 },
  };
}

assert.equal(permitsContractV2SnapshotReuse(runtime('snapshot')), true);
assert.equal(permitsContractV2SnapshotReuse(runtime('etag')), false);
assert.equal(permitsContractV2SnapshotReuse(runtime('none')), false);

const runtimePayload = {
  ...runtime('snapshot'),
  renderStrategy: 'incremental',
  hydration: { mode: 'eager' },
  patchOperations: ['replace'],
  tracePolicy: { level: 'full' },
  complexityBudget: { fields: 100 },
  aiEnvelope: { mode: 'suggestion', executable: false, allowed: false, capabilities: [] },
  interactionMode: 'form',
  actionTarget: 'record',
  collaboration: { enabled: true },
  businessWorkspace: { enabled: true },
  businessActions: [{ action: 'submit' }],
  deliveryProfile: 'full',
  intakeAutosave: { enabled: true },
  fieldSemantics: { amount: { semanticType: 'money' } },
  validationRules: [{ field: 'amount', required: true }],
  governance: { owner: 'platform' },
  recordVersionPolicy: { mode: 'etag' },
};
const fakeStore = { snapshot: { runtimeContract: runtimePayload } } as never;
const projected = resolveContractV2RuntimePolicy(fakeStore);
for (const [key, value] of Object.entries(runtimePayload)) {
  assert.deepEqual(projected[key], value, `runtime policy field ${key} must survive store projection`);
}

const inactiveActionStore = {
  snapshot: {
    dataContract: {
      dataMeta: {
        sourceContext: {
          context: { active_test: false, sc_runtime_user_management: true },
        },
      },
    },
  },
} as never;
assert.deepEqual(
  resolveContractFormReadContext(inactiveActionStore),
  { active_test: false, sc_runtime_user_management: true },
  'an explicit false from the server-projected action context reaches record reads',
);
assert.deepEqual(
  resolveContractFormReadContext({ snapshot: { dataContract: { dataMeta: {} } } } as never),
  {},
  'an action without active_test keeps the api.data default filtering behavior',
);

console.log('contract v2 runtime policy: PASS cases=6 fields=23');
