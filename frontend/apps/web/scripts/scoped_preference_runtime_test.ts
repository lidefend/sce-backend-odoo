import assert from 'node:assert/strict';
import { projectStoredListPreference, readStoredListPreference } from '../src/app/runtime/listPreferenceProjection';
import { readFileSync } from 'node:fs';
import { currentContextEpoch, beginContextTransition } from '../src/app/contextEpoch';
import { createScopedPreferenceRuntime, enqueuePreferenceWrite } from '../src/app/runtime/scopedPreferenceRuntime';

type Value = { hidden_columns: string[] };
function fixture() {
  const pending: Array<{ scope: string; resolve: (value: Value) => void; reject: (error: unknown) => void }> = [];
  const applied: Value[] = [];
  const errors: unknown[] = [];
  let clears = 0;
  const runtime = createScopedPreferenceRuntime({
    load: (scope: string) => new Promise<Value>((resolve, reject) => pending.push({ scope, resolve, reject })),
    apply: (value) => applied.push(value), clear: () => { clears += 1; }, onError: (error) => errors.push(error),
  });
  return { runtime, pending, applied, errors, get clears() { return clears; } };
}
const tick = async () => { await Promise.resolve(); await Promise.resolve(); };
let passed = 0;
async function check(name: string, run: () => Promise<void> | void) {
  await run(); passed += 1; console.log(`PASS ${name}`);
}
await check('first contract arrival applies parallel response without a second GET', async () => {
  const f = fixture(); f.runtime.sync('A', 'scope-A', null);
  f.pending[0].resolve({ hidden_columns: ['x'] }); await tick();
  assert.equal(f.applied.length, 0);
  f.runtime.sync('A', 'scope-A', 'policy-1');
  assert.equal(f.pending.length, 1); assert.deepEqual(f.applied[0], { hidden_columns: ['x'] });
});
await check('contract before response also needs only one GET', async () => {
  const f = fixture(); f.runtime.sync('A', 'scope-A', null); f.runtime.sync('A', 'scope-A', 'policy-1');
  f.pending[0].resolve({ hidden_columns: ['x'] }); await tick();
  assert.equal(f.pending.length, 1); assert.equal(f.applied.length, 1);
});
await check('scope switch clears and rejects previous response', async () => {
  const f = fixture(); f.runtime.sync('A', 'scope-A', 'policy'); f.runtime.sync('B', 'scope-B', 'policy');
  f.pending[0].resolve({ hidden_columns: ['wrong'] }); f.pending[1].resolve({ hidden_columns: ['right'] }); await tick();
  assert.deepEqual(f.applied, [{ hidden_columns: ['right'] }]); assert.equal(f.clears, 2);
});
await check('policy tightening and loosening both reload server sanitized preference', async () => {
  const f = fixture(); f.runtime.sync('A', 'scope-A', 'allow');
  f.pending[0].resolve({ hidden_columns: ['x'] }); await tick();
  f.runtime.sync('A', 'scope-A', 'deny'); f.pending[1].resolve({ hidden_columns: [] }); await tick();
  f.runtime.sync('A', 'scope-A', 'allow'); f.pending[2].resolve({ hidden_columns: ['x'] }); await tick();
  assert.deepEqual(f.applied.map(x => x.hidden_columns), [['x'], [], ['x']]);
});
await check('local edit/reset defeats slow GET and does not revive stale snapshot', async () => {
  const f = fixture(); f.runtime.sync('A', 'scope-A', null);
  f.runtime.edit({ hidden_columns: [] }); f.pending[0].resolve({ hidden_columns: ['old'] }); await tick();
  f.runtime.sync('A', 'scope-A', 'policy'); assert.deepEqual(f.applied, [{ hidden_columns: [] }]);
});
await check('queued save retains original scope and rejects state after A-B-A navigation', async () => {
  const f = fixture(); f.runtime.sync('A', 'scope-A', 'policy'); const owner = f.runtime.capture();
  f.runtime.sync('B', 'scope-B', 'policy'); f.runtime.sync('A', 'scope-A', 'policy');
  assert.equal(owner.scope, 'scope-A'); assert.equal(owner.isCurrent(), false);
});
await check('contract withdrawal and recovery reload instead of losing preference', async () => {
  const f = fixture(); f.runtime.sync('A', 'scope-A', 'policy'); f.runtime.sync('A', 'scope-A', null);
  f.pending[0].resolve({ hidden_columns: ['stale'] }); await tick();
  f.runtime.sync('A', 'scope-A', 'policy'); assert.equal(f.pending.length, 2);
  f.pending[1].resolve({ hidden_columns: ['fresh'] }); await tick(); assert.deepEqual(f.applied, [{ hidden_columns: ['fresh'] }]);
});
await check('same contract does not refetch; authority context change does', () => {
  const f = fixture(); f.runtime.sync('A-company1', 'scope-A', 'policy'); f.runtime.sync('A-company1', 'scope-A', 'policy');
  assert.equal(f.pending.length, 1); f.runtime.sync('A-company2', 'scope-A', 'policy'); assert.equal(f.pending.length, 2);
});
await check('failed read clears state and remains an explicit error', async () => {
  const f = fixture(); f.runtime.sync('A', 'scope-A', 'policy'); f.pending[0].reject(new Error('denied')); await tick();
  assert.equal(f.errors.length, 1); assert.equal(f.applied.length, 0);
});
await check('page wires scoped save and policy/context invalidation', () => {
  const page = readFileSync('frontend/apps/web/src/views/ActionView.vue', 'utf8');
  assert.ok(page.includes('setUserViewPreference(owner.scope, preference)'));
  assert.ok(page.includes('owner.isCurrent() && saveSeq === listColumnSaveSeq'));
  assert.ok(page.includes('listColumnPreferenceRuntime.edit(preference)'));
  assert.ok(page.includes('JSON.stringify([currentContextEpoch(), session.user?.id, session.recordContext, session.roleSurface])'));
  const watch = page.slice(page.indexOf('identity: isComponentActive.value'), page.indexOf('identity: isComponentActive.value') + 900);
  for (const source of ['listColumnPreferenceAuthorityIdentity()', 'listProfile.value.preference_policy', 'listColumnPreferenceRuntime.sync']) assert.ok(watch.includes(source), source);
});
for (const transition of ['policy', 'A-B-A']) {
  await check(`read after ${transition} waits for real pending write`, async () => {
    let stored = { hidden_columns: ['old'] };
    let release!: () => void;
    const writeGate = new Promise<void>(resolve => { release = resolve; });
    let writes: Promise<void> = Promise.resolve();
    let reads = 0;
    const applied: Value[] = [];
    const runtime = createScopedPreferenceRuntime({
      waitForWrites: () => writes,
      load: async () => { reads += 1; return stored; },
      apply: value => applied.push(value), clear: () => {}, onError: error => { throw error; },
    });
    runtime.sync('A', 'scope-A', 'allow'); await tick();
    runtime.edit({ hidden_columns: ['new'] });
    const owner = runtime.capture();
    writes = enqueuePreferenceWrite(writes, async () => { await writeGate; assert.equal(owner.scope, 'scope-A'); stored = { hidden_columns: ['new'] }; }, () => true);
    if (transition === 'policy') runtime.sync('A', 'scope-A', 'changed-policy');
    else { runtime.sync('B', 'scope-B', 'allow'); runtime.sync('A', 'scope-A', 'allow'); }
    await tick(); assert.equal(reads, 1);
    release(); await writes; await tick();
    assert.equal(reads, 2); assert.deepEqual(applied.at(-1), { hidden_columns: ['new'] });
  });
}
await check('queued write refuses changed authentication authority', async () => {
  let release!: () => void;
  const previous = new Promise<void>(resolve => { release = resolve; });
  let sameAuthority = true;
  let writes = 0;
  const queued = enqueuePreferenceWrite(previous, async () => { writes += 1; }, () => sameAuthority);
  sameAuthority = false; release();
  await assert.rejects(queued, /authority changed/); assert.equal(writes, 0);
});
await check('authority A-B-A cannot revive queued write after context epoch changes', async () => {
  let release!: () => void;
  const previous = new Promise<void>(resolve => { release = resolve; });
  const epoch = currentContextEpoch();
  let writes = 0;
  const queued = enqueuePreferenceWrite(previous, async () => { writes += 1; }, () => currentContextEpoch() === epoch);
  beginContextTransition(); beginContextTransition(); release();
  await assert.rejects(queued, /authority changed/); assert.equal(writes, 0);
});
await check('inactive retained page does not reload on authority or policy changes', async () => {
  const f = fixture(); f.runtime.sync('A', 'scope-A', 'policy');
  f.runtime.sync('', 'scope-A', 'policy'); f.runtime.sync('', 'scope-A', 'new-policy');
  f.pending[0].resolve({ hidden_columns: ['old'] }); await tick();
  assert.equal(f.pending.length, 1); assert.equal(f.applied.length, 0);
  f.runtime.sync('A-new-context', 'scope-A', 'new-policy'); assert.equal(f.pending.length, 2);
});
await check('stored projection cannot masquerade as an effective or undeclared response', () => {
  assert.throws(() => readStoredListPreference({preference:{}}), /preference.projection/);
  assert.deepEqual(readStoredListPreference({projection:'stored',policy_source:'current_page_contract',preference:{}}),{});
});
await check('stored choices consume declared policy without adding forbidden columns', () => {
  const policy = {allow_visibility:true,allow_order:false,allow_width:false,locked_columns:['name'],must_request_columns:['name']};
  const raw = {visible_columns:['secret','name'],hidden_columns:['locked','name','optional'],column_order:['secret','name'],column_widths:{secret:100,name:180}};
  assert.deepEqual(projectStoredListPreference(raw,policy,['name','optional']), {
    visible_columns:['name'], hidden_columns:['optional'], column_order:[], column_widths:{},
  });
  assert.deepEqual(projectStoredListPreference(raw,{...policy,allow_order:true,allow_width:true},['name','optional']).column_widths,{name:180});
  assert.deepEqual(projectStoredListPreference(raw,{...policy,allow_visibility:false},['name']).visible_columns,[]);
});
await check('missing or invalid policy never defaults to allowed', () => {
  for (const policy of [undefined,{}, {allow_visibility:'true'}, {allow_visibility:true,allow_order:true,allow_width:true}]) {
    assert.throws(() => projectStoredListPreference({},policy,['name']),error => (error as Error).name === 'ContractGapError');
  }
});
await check('deferred contract application errors reach the page error channel', async () => {
  const errors: unknown[] = [];
  let clears = 0;
  const runtime = createScopedPreferenceRuntime({load: async () => ({}), apply: () => {throw new Error('contract gap');}, clear: () => {clears++;}, onError: error => errors.push(error)});
  runtime.sync('A','scope',null); await tick();
  runtime.sync('A','scope','policy');
  assert.equal(errors.length,1); assert.ok(clears >= 2);
});
console.log(`${passed} tests passed`);
