import assert from 'node:assert/strict';
import { useRelationRuntime } from '../src/pages/contractForm/useRelationRuntime';

const runtime = useRelationRuntime();
let queryCalls = 0;

const deniedQuery = await runtime.queryRelationOptions({
  fieldName: 'partner_id',
  keyword: 'Acme',
  relation: 'res.partner',
  canRead: false,
  hasDynamicFallback: false,
  currentValue: false,
  fetchOptions: async () => {
    queryCalls += 1;
    return [{ id: 1, label: 'must not be returned' }];
  },
  isDeniedError: () => false,
});
assert.deepEqual(deniedQuery, []);
assert.equal(queryCalls, 0);
assert.equal(runtime.deniedRelationModels.has('res.partner'), true);

runtime.clearRelationRuntime();
let fetchCalls = 0;
const deniedFetch = await runtime.fetchRelationOptions({
  relation: 'res.partner',
  canRead: false,
  keyword: 'Acme',
  fetchOptions: async () => {
    fetchCalls += 1;
    return [{ id: 1, label: 'must not be returned' }];
  },
});
assert.deepEqual(deniedFetch, []);
assert.equal(fetchCalls, 0);

const allowed = await runtime.fetchRelationOptions({
  relation: 'res.partner',
  canRead: true,
  keyword: 'Acme',
  fetchOptions: async () => {
    fetchCalls += 1;
    return [{ id: 7, label: 'Acme' }];
  },
});
assert.deepEqual(allowed, [{ id: 7, label: 'Acme' }]);
assert.equal(fetchCalls, 1);

console.log('[relation_read_closure_test] PASS query_denied=1 fetch_denied=1 fetch_allowed=1');
