import assert from 'node:assert/strict';
import './browser_globals_shim.ts';
import { createPinia, setActivePinia } from 'pinia';

setActivePinia(createPinia());
const { useSessionStore } = await import('../src/stores/session.ts');
const { listRecords } = await import('../src/api/data.ts');
const session = useSessionStore();
Object.assign(session, { token: 'coalescing-test-token', sessionDb: 'sc_dev_demo', initStatus: 'ready' });

type Pending = { body: { params: { search_term?: string; offset?: number; order?: string } }; settle: (rows: Array<{ id: number; name: string }>) => void; fail: (error: Error) => void };
const pending: Pending[] = [];
(globalThis as { fetch: unknown }).fetch = (url: string, init: { body?: string }) => new Promise((resolve, reject) => {
  const parsed = JSON.parse(String(init?.body ?? '{}'));
  pending.push({
    body: parsed,
    settle: (records) => resolve(new Response(
      JSON.stringify({ ok: true, data: { records }, meta: {} }),
      { status: 200, headers: { 'content-type': 'application/json' } },
    )),
    fail: (error) => reject(error),
  });
});

const rowsFor = (keyword: string) => [{ id: keyword.length, name: `${keyword}-record` }];
const settleAt = (index: number, keyword: string) => pending[index].settle(rowsFor(keyword));

// 1. Identical concurrent reads are coalesced: one request, one shared result.
const first = listRecords({ model: 'res.partner', limit: 40, offset: 0, search_term: 'UM' });
const second = listRecords({ model: 'res.partner', limit: 40, offset: 0, search_term: 'UM' });
await Promise.resolve();
assert.equal(pending.length, 1, 'identical concurrent reads must issue one request');
settleAt(0, 'UM');
const [firstResult, secondResult] = await Promise.all([first, second]);
assert.deepEqual(firstResult.records, rowsFor('UM'));
assert.deepEqual(secondResult.records, rowsFor('UM'));
pending.length = 0;

// 2. A different keyword is a different request: it must never reuse the
//    in-flight response for the previous keyword.
const keywordA = listRecords({ model: 'res.partner', limit: 40, offset: 0, search_term: 'UM-P3' });
const keywordB = listRecords({ model: 'res.partner', limit: 40, offset: 0, search_term: 'P1' });
await Promise.resolve();
assert.equal(pending.length, 2, 'different keywords must not be merged');
assert.equal(pending[0].body.params.search_term, 'UM-P3');
assert.equal(pending[1].body.params.search_term, 'P1');
// Settle out of order: the newer keyword answers first, the older one lands late.
settleAt(1, 'P1');
settleAt(0, 'UM-P3');
const [resultA, resultB] = await Promise.all([keywordA, keywordB]);
assert.deepEqual(resultB.records, rowsFor('P1'), 'the newer keyword keeps its own authoritative rows');
assert.deepEqual(resultA.records, rowsFor('UM-P3'), 'the late older response still answers its own caller');
pending.length = 0;

// 3. Paging and ordering change the result, so they are part of the identity.
const pageOne = listRecords({ model: 'res.partner', limit: 40, offset: 0, search_term: 'UM' });
const pageTwo = listRecords({ model: 'res.partner', limit: 40, offset: 40, search_term: 'UM' });
const ordered = listRecords({ model: 'res.partner', limit: 40, offset: 0, order: 'name desc', search_term: 'UM' });
await Promise.resolve();
assert.equal(pending.length, 3, 'offset and order must not be merged into one request');
assert.deepEqual(pending.map((call) => call.body.params.offset), [0, 40, 0]);
assert.deepEqual(pending.map((call) => call.body.params.order), ['', '', 'name desc']);
for (let index = 0; index < pending.length; index += 1) settleAt(index, `UM-${index}`);
await Promise.all([pageOne, pageTwo, ordered]);
pending.length = 0;

// 4. A failed coalesced read does not poison the identity: the next identical
//    read issues a fresh request instead of replaying the rejected promise.
const failing = listRecords({ model: 'res.partner', limit: 40, offset: 0, search_term: 'boom' });
await Promise.resolve();
assert.equal(pending.length, 1);
pending[0].fail(new Error('network down'));
await assert.rejects(() => failing);
const retry = listRecords({ model: 'res.partner', limit: 40, offset: 0, search_term: 'boom' });
await Promise.resolve();
assert.equal(pending.length, 2, 'a failed read must not be cached for the next caller');
settleAt(1, 'boom');
assert.deepEqual((await retry).records, rowsFor('boom'));

console.log('[intent_request_coalescing_test] PASS coalesced=1 distinct_keys=3 paging=2 ordering=1 retry_after_failure=1');
