import assert from 'node:assert/strict';
import './browser_globals_shim.ts';
import { createPinia, setActivePinia } from 'pinia';
import {
  DURABLE_SESSION_SCHEMA_VERSION,
  buildDurableSessionSnapshot,
  decodeDurableSessionSnapshot,
  durableSessionStorageKey,
} from '../src/stores/sessionPersistence.ts';
import { resolveEntryAudience, resolveEntryBasePath } from '../src/services/entryNamespace.ts';

let cases = 0;
const check = (condition: unknown, message: string): void => {
  cases += 1;
  assert.ok(condition, message);
};

const scope = `${resolveEntryAudience() || 'unscoped'}:${resolveEntryBasePath() || 'root'}`;
const snapshotKey = durableSessionStorageKey(scope);
const tokenKey = `sc_auth_token:${scope}`;

const baseSource = {
  sessionDb: 'sc_dev_demo',
  user: {
    id: 7,
    name: 'Durable User',
    is_platform_admin: true,
    is_tenant_config_admin: true,
    platform_duty: { audience: 'platform-admin' },
    groups_xmlids: ['base.group_system'],
  },
  recordContext: {
    model: 'project.project',
    company_id: 3,
    company_name: 'Durable Company',
    company_options: [{ company_id: 3, company_name: 'Durable Company' }],
    operation_strategy: 'build',
    operation_strategy_label: '施工',
    operation_options: [{ operation_strategy: 'build', operation_strategy_label: '施工' }],
    selected: {
      id: 2,
      name: 'Project 2',
      display_name: 'Project 2',
      company_id: 3,
      company_name: 'Durable Company',
      operation_strategy: 'build',
      operation_strategy_label: '施工',
      code: 'P-2',
      owner_name: 'Not durable',
      request_context: { project_id: 2 },
    },
    options: [{ id: 2, display_name: 'Project 2' }],
    total: 1,
    query: 'project',
    selector: { intent: 'record.context.search', limit: 20 },
    message: 'live message',
    request_context: { project_id: 2, company_id: 3 },
    clear_request_context: { company_id: 3 },
  },
  activityPages: [{
    key: 'record:project.project:2',
    title: 'Project 2',
    route: '/f/project.project/2',
    kind: 'record_form',
    model: 'project.project',
    record_id: '2',
    record_context: {
      company_id: 3,
      company_name: 'Durable Company',
      selected: { id: 2, display_name: 'Project 2', company_id: 3 },
      request_context: { project_id: 2 },
    },
    runtime_query: { search: 'active', group_by: ['state'], unsafe: 'drop', group_page: 1 },
    dirty: true,
    settling: true,
    created_at: 10,
    last_active_at: 20,
  }],
  activeActivityPageKey: 'record:project.project:2',
  activityPageCacheEpochs: {
    'record:project.project:2': 4,
    orphan: 6,
    invalid: 'not-a-number',
  },
  menuExpandedKeys: ['menu-a', 'menu-a', 'menu-b'],
  scenarioExpandedCenters: ['center-a'],
  scenarioExpandedScenarios: ['scene-a'],
  bootstrapNextIntent: 'system.init',
  menuTree: [{ id: 1, name: 'must not persist' }],
  capabilityCatalog: { 'cap.a': { label: 'must not persist' } },
  lastTraceId: 'must-not-persist',
  initMeta: { effective_db: 'must-not-persist' },
};

const snapshot = buildDurableSessionSnapshot(baseSource);
cases += 1;
assert.deepEqual(Object.keys(snapshot).sort(), [
  'activeTab',
  'activityPages',
  'bootstrapNextIntent',
  'cacheEpochs',
  'menuExpansionPreferences',
  'recordContext',
  'schemaVersion',
  'sessionDb',
  'user',
]);
check(snapshot.schemaVersion === DURABLE_SESSION_SCHEMA_VERSION, 'snapshot must publish its schema version');
assert.deepEqual(snapshot.user, { id: 7, name: 'Durable User' });
cases += 1;
assert.deepEqual(snapshot.recordContext, {
  model: 'project.project',
  company_id: 3,
  company_name: 'Durable Company',
  operation_strategy: 'build',
  operation_strategy_label: '施工',
  selected: {
    id: 2,
    name: 'Project 2',
    display_name: 'Project 2',
    company_id: 3,
    company_name: 'Durable Company',
    operation_strategy: 'build',
    operation_strategy_label: '施工',
  },
  request_context: { project_id: 2, company_id: 3 },
  clear_request_context: { company_id: 3 },
});
cases += 1;
assert.deepEqual(snapshot.menuExpansionPreferences, {
  menuExpandedKeys: ['menu-a', 'menu-b'],
  scenarioExpandedCenters: ['center-a'],
  scenarioExpandedScenarios: ['scene-a'],
});
cases += 1;
assert.deepEqual(snapshot.cacheEpochs, { 'record:project.project:2': 4 });
cases += 1;
assert.equal(snapshot.activityPages.length, 1);
const page = snapshot.activityPages[0];
check(!Object.prototype.hasOwnProperty.call(page, 'dirty'), 'activity dirty is runtime-only');
check(!Object.prototype.hasOwnProperty.call(page, 'settling'), 'activity settling is runtime-only');
cases += 1;
assert.deepEqual(page.runtime_query, { search: 'active', group_by: ['state'], group_page: '1' });
cases += 1;
assert.deepEqual(page.record_context, {
  company_id: 3,
  company_name: 'Durable Company',
  operation_strategy: '',
  operation_strategy_label: '',
  selected: {
    id: 2,
    name: '',
    display_name: 'Project 2',
    company_id: 3,
    company_name: '',
    operation_strategy: '',
    operation_strategy_label: '',
  },
});
const serialized = JSON.stringify(snapshot);
for (const forbidden of [
  'menuTree',
  'capabilityCatalog',
  'lastTraceId',
  'initMeta',
  'is_platform_admin',
  'platform_duty',
  'company_options',
  'operation_options',
  'selector',
  '"dirty"',
  '"settling"',
]) {
  check(!serialized.includes(forbidden), `durable snapshot must not contain ${forbidden}`);
}

const current = decodeDurableSessionSnapshot(JSON.stringify(snapshot));
check(current.status === 'current', 'current snapshot must be recognized');
cases += 1;
assert.deepEqual(current.snapshot, snapshot);

const legacyRaw = {
  sessionDb: 'legacy_db',
  user: baseSource.user,
  menuTree: '{malformed derived navigation}',
  capabilityCatalog: ['malformed derived catalog'],
  menuExpandedKeys: ['legacy-menu'],
  scenarioExpandedCenters: ['legacy-center'],
  scenarioExpandedScenarios: ['legacy-scene'],
  recordContext: baseSource.recordContext,
  activityPages: baseSource.activityPages,
  activeActivityPageKey: baseSource.activeActivityPageKey,
  activityPageCacheEpochs: baseSource.activityPageCacheEpochs,
  lastTraceId: 'legacy-trace',
  initMeta: 'malformed derived init meta',
  bootstrapNextIntent: 'session.bootstrap',
};
const legacy = decodeDurableSessionSnapshot(JSON.stringify(legacyRaw));
check(legacy.status === 'legacy', 'snapshot without schemaVersion must remain readable as legacy');
cases += 1;
assert.equal(legacy.snapshot?.sessionDb, 'legacy_db');
cases += 1;
assert.equal(legacy.snapshot?.bootstrapNextIntent, 'session.bootstrap');
cases += 1;
assert.deepEqual(legacy.snapshot?.menuExpansionPreferences.menuExpandedKeys, ['legacy-menu']);
cases += 1;
assert.equal(JSON.stringify(legacy.snapshot).includes('malformed derived'), false);

check(decodeDurableSessionSnapshot('{broken').status === 'corrupt', 'broken JSON must be discarded safely');
check(decodeDurableSessionSnapshot(JSON.stringify({ schemaVersion: 99, sessionDb: 'future' })).status === 'unsupported', 'future schema must be rejected');
check(decodeDurableSessionSnapshot(null).status === 'missing', 'missing snapshot is a normal first visit');

setActivePinia(createPinia());
const { useSessionStore } = await import('../src/stores/session.ts');
const session = useSessionStore();

localStorage.clear();
sessionStorage.clear();
localStorage.setItem(snapshotKey, JSON.stringify(legacyRaw));
sessionStorage.setItem(tokenKey, 'legacy-token');
session.restore();
cases += 1;
assert.equal(session.token, 'legacy-token');
cases += 1;
assert.deepEqual(session.user, { id: 7, name: 'Durable User' });
cases += 1;
assert.equal(session.sessionDb, 'legacy_db');
cases += 1;
assert.equal(session.recordContext?.company_options?.length, 0);
cases += 1;
assert.equal(session.recordContext?.operation_options?.length, 0);
cases += 1;
assert.equal(session.recordContext?.options?.length, 0);
cases += 1;
assert.equal(session.activityPages.length, 1, 'matching-company activity must restore');
cases += 1;
assert.equal(session.activityPages[0].dirty, false, 'dirty state must not be restored from a reload');
cases += 1;
assert.equal(session.activityPages[0].settling, false, 'settling state must not be restored');
cases += 1;
assert.equal(session.capabilities.length, 0);
cases += 1;
assert.deepEqual(session.capabilityCatalog, {});
cases += 1;
assert.equal(session.initMeta, null);
cases += 1;
assert.equal(session.lastTraceId, '');

session.clearSession();
localStorage.setItem(snapshotKey, '{broken');
sessionStorage.setItem(tokenKey, 'token-survives-corruption');
session.restore();
cases += 1;
assert.equal(session.token, 'token-survives-corruption');
cases += 1;
assert.equal(localStorage.getItem(snapshotKey), null);

localStorage.setItem(snapshotKey, JSON.stringify({ schemaVersion: 99, sessionDb: 'future' }));
sessionStorage.setItem(tokenKey, 'token-survives-future');
session.restore();
cases += 1;
assert.equal(session.token, 'token-survives-future');
cases += 1;
assert.equal(localStorage.getItem(snapshotKey), null);

console.log(`[session_persistence_snapshot_test] PASS cases=${cases}`);
