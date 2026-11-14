import assert from 'node:assert/strict';
import './browser_globals_shim.ts';
import { createPinia, setActivePinia } from 'pinia';
import { apiRequestRaw } from '../src/api/client.ts';
import { resetSessionExpiredRedirectForTest } from '../src/app/sessionExpiredRecovery.ts';
import {
  buildDurableSessionSnapshot,
  decodeDurableSessionSnapshot,
  durableSessionStorageKey,
  installSessionPersistenceLifecycle,
} from '../src/stores/sessionPersistence.ts';
import { resolveEntryAudience, resolveEntryBasePath } from '../src/services/entryNamespace.ts';

let cases = 0;
const check = (condition: unknown, message: string): void => {
  cases += 1;
  assert.ok(condition, message);
};
const waitForScheduledFlush = () => new Promise((resolve) => setTimeout(resolve, 10));

const scope = `${resolveEntryAudience() || 'unscoped'}:${resolveEntryBasePath() || 'root'}`;
const snapshotKey = durableSessionStorageKey(scope);
const tokenKey = `sc_auth_token:${scope}`;
const originalSetItem = localStorage.setItem.bind(localStorage);
const originalRemoveItem = localStorage.removeItem.bind(localStorage);
let writes: string[] = [];
localStorage.setItem = (key: string, value: string) => {
  if (key === snapshotKey) writes.push(String(value));
  originalSetItem(key, String(value));
};

const startupResponse = (companyId = 3) => ({
  user: {
    id: 7,
    name: 'Recovery User',
    is_platform_admin: true,
    is_tenant_config_admin: true,
    platform_duty: { audience: 'platform-admin' },
  },
  capabilities: [],
  feature_flags: {},
  scenes: [],
  workspace_home: null,
  record_context: {
    contract_version: '1.0.0',
    enabled: true,
    model: 'project.project',
    company_id: companyId,
    company_name: `Company ${companyId}`,
    company_options: [{ company_id: companyId, company_name: `Company ${companyId}` }],
    operation_strategy: 'build',
    operation_strategy_label: '施工',
    operation_options: [{ operation_strategy: 'build', operation_strategy_label: '施工' }],
    selected: { id: 2, display_name: 'Project 2', company_id: companyId },
    options: [],
    request_context: { project_id: 2, company_id: companyId },
    selector: { intent: 'record.context.search', limit: 20 },
  },
  navigation: {
    nav: [],
    integrity: {
      visible_action_count: 0,
      authorized_action_count: 0,
      missing_authority_count: 0,
    },
    route_authority: {
      contract_version: '2.0.0',
      schema_version: '2.0.0',
      source: 'session-persistence-recovery-test',
      principal_scope: { user_id: 7, company_id: companyId, role_code: '' },
      primary_actions: [],
      role_home_actions: [],
      contextual_actions: [],
      admin_actions: [],
      denied_actions: [],
      menu_containers: [],
    },
  },
});

let startupCompanyId = 3;
let logoutCalls = 0;
const fetchRuntime = globalThis.fetch;
globalThis.fetch = (async (_url: string, init: { body?: string }) => {
  const body = JSON.parse(String(init.body || '{}'));
  if (body.intent === 'login') {
    return new Response(JSON.stringify({
      ok: true,
      data: {
        token: 'recovery-token',
        session: { token: 'recovery-token', db: 'sc_dev_demo' },
        bootstrap: { next_intent: 'system.init' },
        user: { id: 7, name: 'Recovery User' },
      },
      meta: {},
    }), { status: 200, headers: { 'content-type': 'application/json' } });
  }
  if (body.intent === 'auth.logout') {
    logoutCalls += 1;
    return new Response(JSON.stringify({ ok: true, data: { message: 'logged out' }, meta: {} }), {
      status: 200,
      headers: { 'content-type': 'application/json' },
    });
  }
  if (body.intent === 'system.init') {
    return new Response(JSON.stringify({ ok: true, data: startupResponse(startupCompanyId), meta: {} }), {
      status: 200,
      headers: { 'content-type': 'application/json' },
    });
  }
  throw new Error(`unexpected intent: ${body.intent}`);
}) as typeof fetch;

setActivePinia(createPinia());
const { useSessionStore } = await import('../src/stores/session.ts');
let session = useSessionStore();

localStorage.clear();
sessionStorage.clear();
session.clearSession();
writes = [];
await session.login('recovery-user', 'password');
check(writes.length === 1, 'login must persist identity immediately');
check(sessionStorage.getItem(tokenKey) === 'recovery-token', 'token remains in sessionStorage');
const loginSnapshot = decodeDurableSessionSnapshot(localStorage.getItem(snapshotKey));
check(loginSnapshot.status === 'current', 'login writes the versioned durable schema');
check(loginSnapshot.snapshot?.user === null, 'login persists bootstrap context before authoritative identity exists');

session.initStatus = 'ready';
await session.loadAppInit({ force: true });
const initializedSnapshot = decodeDurableSessionSnapshot(localStorage.getItem(snapshotKey));
cases += 1;
assert.deepEqual(initializedSnapshot.snapshot?.user, { id: 7, name: 'Recovery User' });
session.registerActivityPage({
  key: 'record:project.project:2',
  title: 'Project 2',
  route: '/f/project.project/2',
  kind: 'record_form',
  model: 'project.project',
  record_id: '2',
  scene_key: '',
  record_context: session.currentActivityRecordContextSnapshot(),
});
session.updateActiveActivityDirty(true);
session.updateActiveActivityTitle('Project 2 - dirty');
session.updateActiveActivityRuntimeQuery({ search: 'active', group_by: ['state'] });
session.toggleMenuExpanded('menu.projects');
session.toggleScenarioExpanded('project.delivery');
session.flushDurablePersist();

const liveDirty = session.activityPages[0].dirty;
check(liveDirty === true, 'SPA activity dirty state remains live');
const storedBeforeReload = JSON.parse(localStorage.getItem(snapshotKey) || '{}');
check(!JSON.stringify(storedBeforeReload).includes('"dirty"'), 'dirty state never enters the durable snapshot');
check(!JSON.stringify(storedBeforeReload).includes('"settling"'), 'settling state never enters the durable snapshot');

setActivePinia(createPinia());
session = useSessionStore();
session.restore();
check(session.token === 'recovery-token', 'refresh restores token independently');
check(session.sessionDb === 'sc_dev_demo', 'refresh restores database recovery identity');
check(session.recordContext?.selected?.id === 2, 'refresh restores record identity');
check(session.recordContext?.company_id === 3, 'refresh restores company identity');
check(session.activityPages.length === 1, 'refresh restores matching-company activity');
check(session.activityPages[0].dirty === false, 'refresh resets non-durable dirty state');
check(session.activityPages[0].title === 'Project 2 - dirty', 'refresh restores latest title');
check(session.menuExpandedKeys.includes('menu.projects'), 'refresh restores menu expansion preference');
check(session.scenarioExpandedScenarios.includes('project.delivery'), 'refresh restores scenario expansion preference');
check(session.capabilities.length === 0 && Object.keys(session.capabilityCatalog).length === 0, 'live authority stays empty before init');

startupCompanyId = 4;
session.initStatus = 'ready';
await session.selectBusinessScope({ company_id: 4, operation_strategy: 'build' });
check(session.recordContext?.company_id === 4, 'company context change publishes authoritative company');
check(session.activityPages.length === 0, 'company scope change clears old activity pages');
const companySnapshot = decodeDurableSessionSnapshot(localStorage.getItem(snapshotKey));
check(companySnapshot.snapshot?.recordContext?.company_id === 4, 'company context change writes the new durable scope');

const mixedPagesSnapshot = buildDurableSessionSnapshot({
  sessionDb: 'sc_dev_demo',
  user: { id: 7, name: 'Recovery User' },
  recordContext: {
    model: 'project.project',
    company_id: 4,
    selected: { id: 2, company_id: 4 },
    request_context: { project_id: 2, company_id: 4 },
  },
  activityPages: [
    {
      key: 'record:project.project:2', title: 'Company 4 project', route: '/f/project.project/2',
      kind: 'record_form', record_id: '2', record_context: { company_id: 4 },
    },
    {
      key: 'record:project.project:3', title: 'Company 3 project', route: '/f/project.project/3',
      kind: 'record_form', record_id: '3', record_context: { company_id: 3 },
    },
  ],
  activeActivityPageKey: 'record:project.project:2',
  activityPageCacheEpochs: {
    'record:project.project:2': 2,
    'record:project.project:3': 1,
  },
  menuExpandedKeys: [],
  scenarioExpandedCenters: [],
  scenarioExpandedScenarios: [],
  bootstrapNextIntent: 'system.init',
});
originalSetItem(snapshotKey, JSON.stringify(mixedPagesSnapshot));
setActivePinia(createPinia());
session = useSessionStore();
session.restore();
check(session.activityPages.length === 1, 'restore must filter activity by company scope');
check(session.activityPages[0].record_id === '2', 'only current-company activity survives restore');

session.initStatus = 'ready';
await session.logout();
check(logoutCalls === 1, 'logout still performs its existing server intent');
check(localStorage.getItem(snapshotKey) === null, 'logout removes durable Session');
check(sessionStorage.getItem(tokenKey) === null, 'logout removes the per-tab token');

session = useSessionStore();
session.token = 'expired-token';
session.sessionDb = 'sc_dev_demo';
session.initStatus = 'ready';
session.persistDurableNow();
sessionStorage.setItem(tokenKey, 'expired-token');
resetSessionExpiredRedirectForTest();
const redirects: string[] = [];
(window.location as Location & { assign: (url: string) => void }).assign = (url: string) => {
  redirects.push(url);
};
globalThis.fetch = (async () => new Response('', { status: 401 })) as typeof fetch;
await assert.rejects(() => apiRequestRaw('/api/v1/protected', {
  method: 'POST',
  headers: { 'content-type': 'application/json' },
  body: '{}',
}));
check(session.token === null, '401 clears the live token');
check(localStorage.getItem(snapshotKey) === null, '401 removes durable Session');
check(sessionStorage.getItem(tokenKey) === null, '401 removes the per-tab token');
check(redirects.some((url) => url.includes('/login?reason=session_expired')), '401 retains existing login redirect behavior');

globalThis.fetch = fetchRuntime;
localStorage.setItem = originalSetItem;

const snapshotA = buildDurableSessionSnapshot({
  sessionDb: 'sc_dev_demo', user: { id: 7, name: 'Recovery User' },
  recordContext: { company_id: 3, selected: { id: 2, company_id: 3 } },
  activityPages: [], activeActivityPageKey: '', activityPageCacheEpochs: {},
  menuExpandedKeys: ['tab-a'], scenarioExpandedCenters: [], scenarioExpandedScenarios: [],
  bootstrapNextIntent: 'system.init',
});
const snapshotB = {
  ...snapshotA,
  menuExpansionPreferences: { ...snapshotA.menuExpansionPreferences, menuExpandedKeys: ['tab-b'] },
};
originalSetItem(snapshotKey, JSON.stringify(snapshotA));
originalSetItem(snapshotKey, JSON.stringify(snapshotB));
check(decodeDurableSessionSnapshot(localStorage.getItem(snapshotKey)).snapshot?.menuExpansionPreferences.menuExpandedKeys[0] === 'tab-b', 'multi-tab persistence remains last-write-wins');

let throwWrites = 2;
let removedForQuota = false;
localStorage.setItem = (key: string, value: string) => {
  if (key === snapshotKey && throwWrites > 0) {
    throwWrites -= 1;
    throw new DOMException('quota exceeded', 'QuotaExceededError');
  }
  originalSetItem(key, value);
};
localStorage.removeItem = (key: string) => {
  if (key === snapshotKey) removedForQuota = true;
  originalRemoveItem(key);
};
check((() => {
  session.persistDurableNow();
  return true;
})(), 'quota errors must not escape persistence');
check(removedForQuota, 'failed durable and minimal retries remove stale storage');
localStorage.removeItem = originalRemoveItem;
localStorage.setItem = originalSetItem;

type Listener = () => void;
class LifecycleTarget {
  listeners = new Map<string, Set<Listener>>();
  visibilityState = 'visible';
  addEventListener(type: string, listener: Listener) {
    const set = this.listeners.get(type) || new Set<Listener>();
    set.add(listener);
    this.listeners.set(type, set);
  }
  removeEventListener(type: string, listener: Listener) {
    this.listeners.get(type)?.delete(listener);
  }
  dispatch(type: string) {
    this.listeners.get(type)?.forEach((listener) => listener());
  }
}
const windowTarget = new LifecycleTarget();
const documentTarget = new LifecycleTarget();
let lifecycleWrites = 0;
session.token = 'lifecycle-token';
session.toggleMenuExpanded('lifecycle');
const dispose = installSessionPersistenceLifecycle({
  windowTarget,
  documentTarget,
  flush: () => {
    if (session.flushDurablePersist()) lifecycleWrites += 1;
  },
});
documentTarget.visibilityState = 'hidden';
documentTarget.dispatch('visibilitychange');
windowTarget.dispatch('pagehide');
check(lifecycleWrites === 1, 'visibilitychange and pagehide share one pending flush');
dispose();

console.log(`[session_persistence_recovery_test] PASS cases=${cases}`);
