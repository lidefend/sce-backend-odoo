import assert from 'node:assert/strict';

import { permitsContractV2SnapshotReuse } from '../src/app/contracts/v2/runtime';
import type { ContractV2RuntimeContract } from '../src/app/contracts/v2/types';

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

console.log('contract v2 runtime policy: PASS cases=3');
