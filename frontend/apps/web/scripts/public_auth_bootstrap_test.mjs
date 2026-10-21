import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
const source = fs.readFileSync('frontend/apps/web/src/stores/session.ts', 'utf8');
const body = source.split('    async loadPublicPageContracts(force = false) {')[1].split('\n    async loadWorkspaceHomeOnDemand')[0].replace(/\n    },\s*$/, '').replace(' as Record<string, { target?: { kind?: string; path?: string } }> | undefined', '');
const valid = () => ({ ok: true, data: { schema_version: '1.0.0', pages: Object.fromEntries(['login','account_activation','password_recovery'].map(key => [key, { page_orchestration: { action_schema: { actions: Object.fromEntries((key === 'login' ? ['open_account_activation', 'open_password_recovery'] : ['open_login']).map(name => [name, { target: { kind: 'route.path', path: '/public-test-target' } }])) } } }])) } });
function setup() {
  let epoch = 0;
  const pending = [];
  const state = { token: '', pageContracts: {}, publicPageContractStatus: 'idle' };
  const action = new Function('getPublicAuthPageContracts','currentContextEpoch','isCurrentContextEpoch', `let publicPageRequestEpoch=-1; let publicPageRequestSequence=0; return async function(force=false) {${body}}`)(
    () => new Promise((resolve, reject) => pending.push({resolve,reject})), () => epoch, e => e === epoch,
  ).bind(state);
  return { state, action, pending, advance: () => epoch++ };
}
test('anonymous load is single flight and caches success', async () => {
  const h=setup(), task=h.action(); await h.action(); assert.equal(h.pending.length,1);
  h.pending[0].resolve(valid()); await task; assert.equal(h.state.publicPageContractStatus,'ready');
  await h.action(); assert.equal(h.pending.length,1);
});
test('failure can retry without losing existing page state', async () => {
  const h=setup(), task=h.action(); h.pending[0].reject(new Error('offline')); await task;
  assert.equal(h.state.publicPageContractStatus,'error'); const retry=h.action(true);
  h.pending[1].resolve(valid()); await retry; assert.equal(h.state.publicPageContractStatus,'ready');
});
test('private/partial response rejected', async () => {
  const h=setup(), task=h.action(); const payload=valid(); payload.data.pages.home={};
  h.pending[0].resolve(payload); await task; assert.equal(h.state.publicPageContractStatus,'error'); assert.deepEqual(h.state.pageContracts,{});
});
test('late public response cannot overwrite authenticated initialization', async () => {
  const h=setup(), task=h.action(); h.state.token='authenticated'; h.advance(); h.state.pageContracts={ home: { authoritative:true } };
  h.pending[0].resolve(valid()); await task; assert.deepEqual(h.state.pageContracts,{home:{authoritative:true}});
});
test('logout starts new epoch even while old public request is pending', async () => {
  const h=setup(), old=h.action(); h.advance(); const fresh=h.action(); assert.equal(h.pending.length,2);
  h.pending[0].reject(new Error('old')); await old; assert.equal(h.state.publicPageContractStatus,'loading');
  h.pending[1].resolve(valid()); await fresh; assert.equal(h.state.publicPageContractStatus,'ready');
});
test('late old success cannot overwrite newer response', async () => {
  const h=setup(), old=h.action(); h.advance(); const fresh=h.action(); const newer=valid(); newer.data.pages.login.texts={title:'new'};
  h.pending[1].resolve(newer); await fresh; h.pending[0].resolve(valid()); await old;
  assert.equal(h.state.pageContracts.login.texts.title,'new');
});
test('authenticated visitor does not fetch public projection', async () => {
  const h=setup(); h.state.token='authenticated'; await h.action(); assert.equal(h.pending.length,0);
});

test('missing public navigation action fails visibly', async () => {
  const h=setup(), task=h.action(); const payload=valid(); payload.data.pages.password_recovery.page_orchestration.action_schema.actions={};
  h.pending[0].resolve(payload); await task; assert.equal(h.state.publicPageContractStatus,'error');
});

test('clearing the real session invalidates public readiness before dropping declarations', () => {
  const clearBody = source.split('    clearSession() {')[1].split('\n    setActionMeta(')[0].replace(/\n    },\s*$/, '');
  const storage = { removeItem() {} };
  for (const priorStatus of ['ready', 'loading']) {
    const state = { publicPageContractStatus: priorStatus, pageContracts: { login: { texts: { session_expired_notice: 'declared' } } } };
    const writes = [];
    const observed = new Proxy(state, { set(target, key, value) {
      if (key === 'pageContracts') assert.equal(target.publicPageContractStatus, 'idle', 'removed declaration must never remain ready');
      writes.push(key); target[key] = value; return true;
    } });
    const clear = new Function('invalidateContextRequests', 'setSceneRegistry', 'localStorage', 'sessionStorage', 'sessionStorageKey', 'scopedTokenStorageKey', 'TOKEN_STORAGE_KEY_LEGACY',
      `let appInitInFlight=null, appInitEpoch=-1; return function() {${clearBody}}`)(
      () => {}, () => {}, storage, storage, () => 'session', () => 'token', 'legacy');
    clear.call(observed);
    assert.equal(state.publicPageContractStatus, 'idle');
    assert.deepEqual(state.pageContracts, {});
    assert.ok(writes.includes('pageContracts'));
  }
});
