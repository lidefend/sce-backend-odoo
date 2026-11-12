import assert from 'node:assert/strict';
import './browser_globals_shim.ts';
import './scenario_surface_parser_test.ts';
import { parseScenarioSurface } from '../src/app/scenarioSurface';
import { createPinia, setActivePinia } from 'pinia';
import { createApp, effectScope, nextTick } from 'vue';
import { routerKey } from 'vue-router';

setActivePinia(createPinia());
const { useSessionStore } = await import('../src/stores/session.ts');
const { beginContextTransition } = await import('../src/app/contextEpoch.ts');
const session = useSessionStore();
session.setToken('workspace-lifecycle-test-token');
session.sessionDb = 'sc_dev_demo';
session.initStatus = 'ready';

type Pending = { intent: string; params: Record<string, unknown>; settle: (data: unknown) => void; fail: (error: Error) => void };
const pending: Pending[] = [];
// Deliberately allow responses after abort: the store must also reject stale
// completions when transport cancellation arrives too late.
globalThis.fetch = ((_url: unknown, init: { body?: string }) => new Promise((resolve, reject) => {
  pending.push({
    intent: JSON.parse(String(init.body)).intent,
    params: JSON.parse(String(init.body)).params,
    settle: data => resolve(new Response(JSON.stringify({ ok: true, data, meta: {} }), {
      status: 200, headers: { 'content-type': 'application/json' },
    })),
    fail: reject,
  });
})) as typeof fetch;

function projection(key: string) {
  return { contract_version: 'workspace_scenario_projection.v1', rows: [{
    scene_key: key, name: key, product_released: true, tenant_enabled: true,
    role_assigned: true, workspace_candidate: true,
  }], workspace_candidate_count: 1 };
}
async function nextRequest(start: () => Promise<unknown>) {
  const count = pending.length;
  const result = start();
  await Promise.resolve();
  assert.equal(pending.length, count + 1, 'must actually issue the request under test');
  return { result, request: pending[count] };
}
const load = () => nextRequest(() => session.loadWorkspaceScenarioProjection());
const startupResponse = () => ({
  user: { id: 1, name: 'Startup test user' },
  capabilities: [],
  feature_flags: {},
  scenes: [],
  workspace_home: null,
  record_context: {
    contract_version: '1.0.0',
    enabled: true,
    company_id: 7,
    company_name: 'Startup test company',
    selected: null,
    options: [],
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
      source: 'startup-test',
      principal_scope: { user_id: 1, company_id: 7, role_code: '' },
      primary_actions: [],
      role_home_actions: [],
      contextual_actions: [],
      admin_actions: [],
      denied_actions: [],
      menu_containers: [],
    },
  },
});

// A response that passes HTTP but fails contract decoding is still a failed
// initialization transaction and must expose a retry path.
const malformedStartup = await nextRequest(() => session.loadAppInit({ force: true }));
malformedStartup.request.settle({
  user: { id: 1 },
  capabilities: undefined,
  navigation: {},
});
await assert.rejects(malformedStartup.result, /system\.init\.capabilities/);
assert.equal(session.initStatus, 'error');
assert.match(session.initError || '', /system\.init\.capabilities/);
assert.equal(session.isReady, false);

const recoveredStartup = await nextRequest(() => session.loadAppInit({ force: true }));
recoveredStartup.request.settle(startupResponse());
await recoveredStartup.result;
assert.equal(session.initStatus, 'ready');
assert.equal(session.initError, null);
assert.equal(session.isReady, true);

// A superseded initialization cannot publish failure over the ready result
// that belongs to the newer context.
const staleStartup = await nextRequest(() => session.loadAppInit({ force: true }));
beginContextTransition();
const currentStartup = await nextRequest(() => session.loadAppInit({ force: true }));
currentStartup.request.settle(startupResponse());
await currentStartup.result;
assert.equal(session.initStatus, 'ready');
staleStartup.request.fail(new Error('stale bootstrap failed'));
await staleStartup.result;
assert.equal(session.initStatus, 'ready');
assert.equal(session.initError, null);
assert.equal(session.isReady, true);
console.log('[startup_transaction_test] PASS cases=3 store=actual transport=controlled');

// A committed create retires the exact new activity and its KeepAlive epoch.
session.registerActivityPage({
  key: 'record:x.document:66',
  route: '/f/x.document/66',
  kind: 'record_form',
  model: 'x.document',
  record_id: '66',
  record_context: session.currentActivityRecordContextSnapshot(),
  dirty: true,
});
session.registerActivityPage({
  key: 'new:x.document:page:create-1',
  route: '/f/x.document/new?activity_page_id=create-1',
  kind: 'record_form',
  model: 'x.document',
  record_id: 'new',
  record_context: session.currentActivityRecordContextSnapshot(),
});
assert.equal(session.completeCreatedActivityPage('new:x.document:page:create-1'), true);
assert.equal(session.activityPages.some(page => page.key === 'new:x.document:page:create-1'), false);
assert.equal(session.activityPages.find(page => page.key === 'record:x.document:66')?.dirty, true);
assert.equal(session.activeActivityPageKey, '');
assert.equal(session.activityPageCacheEpochs['new:x.document:page:create-1'], 1);
console.log('[created_activity_retirement_test] PASS cases=4 store=actual');

// Concurrent forced bootstraps queue behind the actual successor. They must not
// let the later waiter snapshot the activity list the earlier waiter cleared.
session.registerActivityPage({
  key: 'record:x.document:77',
  route: '/f/x.document/77',
  kind: 'record_form',
  model: 'x.document',
  record_id: '77',
  record_context: session.currentActivityRecordContextSnapshot(),
});
const queuedFirst = await nextRequest(() => session.loadAppInit({ force: true }));
const pendingCount = pending.length;
const queuedSecond = session.loadAppInit({ force: true });
const queuedThird = session.loadAppInit({ force: true });
await Promise.resolve();
assert.equal(pending.length, pendingCount, 'queued forced refreshes wait for the first transaction');
queuedFirst.request.settle(startupResponse());
await queuedFirst.result;
await new Promise(resolve => setTimeout(resolve, 0));
assert.equal(pending.length, pendingCount + 1, 'the second refresh starts after the first');
pending.at(-1)!.settle(startupResponse());
await queuedSecond;
await new Promise(resolve => setTimeout(resolve, 0));
assert.equal(pending.length, pendingCount + 2, 'the third refresh waits for the second instead of racing it');
pending.at(-1)!.settle(startupResponse());
await queuedThird;
assert.equal(session.activityPages.some(page => page.key === 'record:x.document:77'), true);
assert.equal(session.activeActivityPageKey, 'record:x.document:77');
console.log('[queued_forced_bootstrap_retention_test] PASS cases=3 store=actual transport=controlled');

// A successful read consumes the server result without changing its decisions.
const initial = await load();
initial.request.settle(projection('initial'));
await initial.result;
assert.equal(session.workspaceScenarioProjection?.rows[0].scene_key, 'initial');

// Refresh failure must not leave the previous projection in the store.
const failing = await load();
assert.equal(session.workspaceScenarioProjection, null);
const rejected = assert.rejects(failing.result, /network unavailable/);
failing.request.fail(new Error('network unavailable'));
await rejected;
assert.equal(session.workspaceScenarioProjection, null);

// In one context, the newest request wins even when responses arrive reversed.
const older = await load();
const newer = await load();
newer.request.settle(projection('newer'));
await newer.result;
older.request.settle(projection('older'));
assert.equal(await older.result, null);
assert.equal(session.workspaceScenarioProjection?.rows[0].scene_key, 'newer');

// A company/context transition invalidates even a late successful response.
const oldCompany = await load();
beginContextTransition();
oldCompany.request.settle(projection('old-company'));
assert.equal(await oldCompany.result, null);
assert.equal(session.workspaceScenarioProjection, null);

// Forced bootstrap in the SAME epoch also invalidates outstanding projections.
const preBootstrap = await load();
const bootstrap = await nextRequest(() => session.loadAppInit({ force: true }));
assert.equal(session.workspaceScenarioProjection, null);
const bootstrapFailure = assert.rejects(bootstrap.result);
bootstrap.request.fail(new Error('bootstrap unavailable'));
await bootstrapFailure;
preBootstrap.request.settle(projection('pre-bootstrap'));
assert.equal(await preBootstrap.result, null);
assert.equal(session.workspaceScenarioProjection, null);

// Logout and credential replacement cannot be undone by an old response.
session.initStatus = 'ready';
const preLogout = await load();
session.clearSession();
preLogout.request.settle(projection('pre-logout'));
assert.equal(await preLogout.result, null);
assert.equal(session.workspaceScenarioProjection, null);
session.setToken('workspace-lifecycle-next-token');
session.initStatus = 'ready';
const preToken = await load();
session.setToken('workspace-lifecycle-replaced-token');
preToken.request.settle(projection('pre-token'));
assert.equal(await preToken.result, null);
assert.equal(session.workspaceScenarioProjection, null);

session.workspaceScenarioProjection = projection('before-restore');
session.restore();
assert.equal(session.workspaceScenarioProjection, null);

// Capability catalogue obeys the same session lifecycle as navigation.
const capability = (key: string) => ({ login_home: { blocks: [{
  key, label: key, required: true, available: true,
}] } });
session.initStatus = 'ready';
const oldCapability = await nextRequest(() => session.loadProductCapabilityCatalog(true));
const newCapability = await nextRequest(() => session.loadProductCapabilityCatalog(true));
newCapability.request.settle(capability('new'));
await newCapability.result;
oldCapability.request.settle(capability('old'));
assert.equal(await oldCapability.result, null);
assert.equal(session.productCapabilityCatalog?.login_home?.blocks[0].key, 'new');
const beforeCapabilityBootstrap = await nextRequest(() => session.loadProductCapabilityCatalog(true));
const capabilityBootstrap = await nextRequest(() => session.loadAppInit({ force: true }));
const capabilityBootstrapFailure = assert.rejects(capabilityBootstrap.result);
capabilityBootstrap.request.fail(new Error('catalog bootstrap unavailable'));
await capabilityBootstrapFailure;
beforeCapabilityBootstrap.request.settle(capability('before-bootstrap'));
assert.equal(await beforeCapabilityBootstrap.result, null);
assert.equal(session.productCapabilityCatalog, null);
session.initStatus = 'ready';
const beforeCapabilityToken = await nextRequest(() => session.loadProductCapabilityCatalog(true));
session.setToken('catalog-next-token');
beforeCapabilityToken.request.settle(capability('before-token'));
assert.equal(await beforeCapabilityToken.result, null);
assert.equal(session.productCapabilityCatalog, null);
const beforeCapabilityRestore = await nextRequest(() => session.loadProductCapabilityCatalog(true));
session.restore();
beforeCapabilityRestore.request.settle(capability('before-restore'));
assert.equal(await beforeCapabilityRestore.result, null);
assert.equal(session.productCapabilityCatalog, null);
console.log('[capability_catalog_lifecycle_test] PASS cases=4 store=actual transport=controlled');

// A forced bootstrap waiting for an older request must revalidate the epoch
// after waiting, before clearing the new company's already-ready navigation.
session.initStatus = 'ready';
const bootstrapInOldCompany = await nextRequest(() => session.loadAppInit({ force: true }));
const requestCountBeforeQueuedBootstrap = pending.length;
const queuedOldBootstrap = session.loadAppInit({ force: true });
beginContextTransition();
session.initStatus = 'ready';
session.menuTree = [{ id: 999, name: 'Current company', route: '/current-company' }];
bootstrapInOldCompany.request.fail(new Error('obsolete company bootstrap'));
await bootstrapInOldCompany.result;
await new Promise(resolve => setTimeout(resolve, 0));
assert.equal(pending.length, requestCountBeforeQueuedBootstrap, 'obsolete queued bootstrap must not send another request');
await queuedOldBootstrap;
assert.equal(session.initStatus, 'ready');
assert.equal(session.menuTree[0].id, 999);
console.log('[queued_bootstrap_context_test] PASS cases=1 store=actual transport=controlled');

// The actual workspace consumer must not expand shortcuts while the projection
// is unknown, failed, or invalidated. Its decisions still come from the server.
session.clearSession();
session.menuTree = [
  { id: 1, name: 'Allowed', scene_key: 'allowed', route: '/s/allowed' },
  { id: 2, name: 'Denied', scene_key: 'denied', route: '/s/denied' },
];
const { useWorkspaceHome } = await import('../src/composables/shared-surface/useWorkspaceHome.ts');
const app = createApp({});
app.provide(routerKey, { push: async () => undefined } as unknown as import('vue-router').Router);
const scope = effectScope();
const home = app.runWithContext(() => scope.run(() => useWorkspaceHome()))!;
assert.deepEqual(home.quickLinks.value, []);
session.workspaceScenarioProjection = projection('allowed');
assert.deepEqual(home.quickLinks.value.map(row => row.route), ['/s/allowed']);
session.workspaceScenarioProjection = { rows: [], workspace_candidate_count: 0 };
assert.deepEqual(home.quickLinks.value, []);
session.invalidateWorkspaceScenarioProjection();
assert.deepEqual(home.quickLinks.value, []);
// Standard business surface is authoritative even without a legacy scene row.
const nativeEntry = (id: number) => ({ menu_xmlid: `test.menu_${id}`, menu_id: id,
  action_id: id + 100, action_xmlid: `test.action_${id}`, model: 'test.model',
  view_modes: ['list'], route: `/a/${id + 100}?menu_id=${id}`, label: `入口${id}`,
  intent: 'view', intent_label: '查看', configured: true });
const nativeScenario = (id: number) => ({ key: `business.${id}`, name: `业务场景${id}`, type: 'business',
  sequence: 10, entries: [nativeEntry(id)] });
session.workspaceScenarioProjection = { rows: [], workspace_candidate_count: 0 };
session.scenarioSurface = { centers: [{ key: 'business', name: '业务', sequence: 10,
  scenarios: Array.from({ length: 17 }, (_, index) => nativeScenario(index + 1)), entries: [] }] };
assert.equal(home.scenarioCandidateSceneKeys.value.length, 17);
assert.equal(home.quickLinks.value.length, 7, 'home retains existing seven-shortcut presentation limit');
assert.equal(home.quickLinks.value[0].label, '业务场景1');
assert.equal(home.quickLinks.value[0].route, nativeEntry(1).route);
// Each scenario is reachable when delivered, including later entries in the surface.
for (let id = 1; id <= 17; id += 1) {
  session.scenarioSurface.centers[0].scenarios = [nativeScenario(id)];
  assert.deepEqual(home.quickLinks.value.map(row => row.route), [nativeEntry(id).route]);
}
session.scenarioSurface = { centers: [{ key: 'business', name: '业务', sequence: 10, scenarios: [], entries: [nativeEntry(50)] }] };
assert.deepEqual(home.scenarioCandidateSceneKeys.value, []);
assert.deepEqual(home.quickLinks.value.map(row => row.route), [nativeEntry(50).route]);
// An authoritative empty surface never resurrects legacy menu entries.
session.scenarioSurface = parseScenarioSurface({ ok: true, tree: { centers: [] } });
assert.deepEqual(home.quickLinks.value, []);
session.scenarioSurface = null;
session.workspaceScenarioProjection = null;
assert.deepEqual(home.quickLinks.value, []);
console.log('[workspace_business_surface_test] PASS cases=4 consumer=actual transport=controlled');
scope.stop();
// The actual Vue watcher waits for readiness, including a same-token/company
// bootstrap. It must refill the projection that bootstrap invalidated.
session.setToken('workspace-readiness-token');
session.initStatus = 'loading';
session.workspaceScenarioProjection = projection('allowed');
const readinessScope = effectScope();
const requestCount = pending.length;
const readyHome = app.runWithContext(() => readinessScope.run(() => useWorkspaceHome()))!;
await nextTick();
assert.equal(pending.length, requestCount, 'no protected workspace reads before ready');
assert.equal(session.workspaceScenarioProjection, null);
assert.deepEqual(readyHome.quickLinks.value, []);

async function readyAndResolve() {
  const offset = pending.length;
  session.initStatus = 'ready';
  await nextTick();
  await Promise.resolve();
  const requests = pending.slice(offset);
  assert.equal(requests.filter(row => row.intent === 'workspace.scenario.projection.get').length, 1);
  for (const request of requests) {
    request.settle(request.intent === 'workspace.scenario.projection.get' ? projection('allowed') : {});
  }
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.equal(session.workspaceScenarioProjection?.rows[0].scene_key, 'allowed');
  assert.deepEqual(readyHome.quickLinks.value.map(row => row.route), ['/s/allowed']);
}
await readyAndResolve();
// No token/company change: a fresh ready transition must still fetch again.
session.initStatus = 'loading';
await nextTick();
assert.equal(session.workspaceScenarioProjection, null);
assert.deepEqual(readyHome.quickLinks.value, []);
await readyAndResolve();
readinessScope.stop();
// Home catalogue consumers must ignore obsolete success, failure and disposal.
session.invalidateProductCapabilityCatalog();
const catalogHomeScope = effectScope();
const homeRequestStart = pending.length;
const catalogHome = app.runWithContext(() => catalogHomeScope.run(() => useWorkspaceHome()))!;
await flushHome();
const homeRequests = pending.slice(homeRequestStart);
const oldHomeCatalog = homeRequests.find(item => item.intent === 'product.configuration.capability.catalog')!;
assert.ok(oldHomeCatalog);
for (const item of homeRequests) {
  if (item !== oldHomeCatalog) item.settle(item.intent === 'workspace.scenario.projection.get' ? projection('allowed') : {});
}
const newestHomeCatalog = await nextRequest(catalogHome.loadCatalog);
newestHomeCatalog.request.settle(capability('current-home'));
await newestHomeCatalog.result;
oldHomeCatalog.fail(new Error('obsolete catalog failure'));
await flushHome();
assert.equal(catalogHome.loginBlocks.value[0].key, 'current-home');
assert.equal(catalogHome.catalogError.value, '');

session.invalidateProductCapabilityCatalog();
const preHomeBootstrap = await nextRequest(catalogHome.loadCatalog);
session.initStatus = 'loading';
await nextTick();
preHomeBootstrap.request.settle(capability('obsolete-home'));
await preHomeBootstrap.result;
assert.deepEqual(catalogHome.loginBlocks.value, []);
assert.equal(catalogHome.catalogLoading.value, false);

session.initStatus = 'ready';
session.invalidateProductCapabilityCatalog();
await nextTick();
await flushHome();
const beforeDispose = await nextRequest(catalogHome.loadCatalog);
catalogHomeScope.stop();
beforeDispose.request.fail(new Error('disposed catalog failure'));
await beforeDispose.result;
assert.equal(catalogHome.catalogError.value, '');
// Drain requests started by the ready transition; disposed consumers stay inert.
for (const item of pending.slice(homeRequestStart)) item.settle({});
await flushHome();
assert.deepEqual(catalogHome.loginBlocks.value, []);
async function flushHome() { await new Promise(resolve => setTimeout(resolve, 0)); }
console.log('[workspace_catalog_consumer_test] PASS cases=3 consumer=actual transport=controlled');
console.log('[workspace_scenario_lifecycle_test] PASS cases=11 transport=controlled store=actual consumer=actual');

// Actual business management consumer: server-declared actions, explicit company
// scope, refresh after commit and stale transport completion rejection.
const { useScenarioActivation } = await import('../src/composables/useScenarioActivation.ts');
session.initStatus = 'ready';
session.recordContext = { ...session.recordContext, company_id: 1 } as NonNullable<typeof session.recordContext>;
const managementScope = effectScope();
const management = managementScope.run(() => useScenarioActivation())!;
const catalogResponse = (company = 1, actions = true) => ({ company_id: company, business_scenarios: [{
  scene_key: 'project.management', name: '项目管理', enablement_scope: 'business.v1',
  status_label: '未启用', release_label: '已发布',
  actions: actions ? [{ key: 'enable', label: '启用', enabled: true }] : [],
}] });
const flush = () => new Promise(resolve => setTimeout(resolve, 0));
pending.at(-1)!.settle(catalogResponse());
await flush();
assert.equal(management.rows.value[0].enablement_scope, 'business.v1');

// The client never constructs an action absent from the server contract.
const beforeInvented = pending.length;
await management.execute(management.rows.value[0], { key: 'invented', label: '启用', enabled: true });
assert.equal(pending.length, beforeInvented);
const originalBootstrap = session.loadAppInit;
let bootstraps = 0;
session.loadAppInit = async () => {
  bootstraps += 1;
  session.initStatus = 'loading';
  await nextTick();
  session.initStatus = 'ready';
  await nextTick();
};
const row = management.rows.value[0];
const mutationRequest = await nextRequest(() => management.execute(row, row.actions[0]));
assert.equal(mutationRequest.request.intent, 'scenario.activation.set');
assert.deepEqual(mutationRequest.request.params, { company_id: 1, scene_key: 'project.management',
  enablement_scope: 'business.v1', enabled: true });
const countDuringMutation = pending.length;
await management.execute(row, row.actions[0]);
assert.equal(pending.length, countDuringMutation, 'double-click cannot submit twice');
mutationRequest.request.settle({ scene_key: row.scene_key, enabled: true });
await flush();
assert.equal(bootstraps, 1);
assert.equal(pending.at(-1)!.intent, 'scenario.activation.catalog.get');
pending.at(-1)!.settle(catalogResponse());
await mutationRequest.result;
assert.equal(management.state.value, 'ready');

// A failed mutation does not claim success or retain enabled controls.
const failedRow = management.rows.value[0];
const failedMutation = await nextRequest(() => management.execute(failedRow, failedRow.actions[0]));
failedMutation.request.fail(new Error('mutation denied'));
await failedMutation.result;
assert.equal(management.state.value, 'error');
assert.deepEqual(management.rows.value, []);
assert.equal(bootstraps, 1);

// The old legacy catalog is a contract gap, never silently an empty success.
const legacy = await nextRequest(management.load);
legacy.request.settle({ rows: [] });
await legacy.result;
assert.equal(management.state.value, 'error');
assert.match(management.errorMessage.value, /契约/);
const reload = await nextRequest(management.load);
reload.request.settle(catalogResponse());
await reload.result;

// Changing company blocks a click immediately, even before Vue flushes watches.
const previousRow = management.rows.value[0];
session.recordContext = { ...session.recordContext, company_id: 2 } as NonNullable<typeof session.recordContext>;
const beforeStaleClick = pending.length;
await management.execute(previousRow, previousRow.actions[0]);
assert.equal(pending.slice(beforeStaleClick).filter(item => item.intent === 'scenario.activation.set').length, 0);
await nextTick();
pending.at(-1)!.settle(catalogResponse(2));
await flush();
assert.equal(management.state.value, 'ready');
const companyTwoRow = management.rows.value[0];
const oldMutation = await nextRequest(() => management.execute(companyTwoRow, companyTwoRow.actions[0]));
session.recordContext = { ...session.recordContext, company_id: 1 } as NonNullable<typeof session.recordContext>;
await nextTick();
oldMutation.request.settle({ enabled: true });
await oldMutation.result;
assert.equal(bootstraps, 1, 'old-company commit must not rebootstrap the new company');
pending.at(-1)!.settle(catalogResponse(1, false));
await flush();
assert.deepEqual(management.rows.value[0].actions, []);

// Out-of-order catalog responses cannot restore the previous state.
const olderCatalog = await nextRequest(management.load);
const newerCatalog = await nextRequest(management.load);
newerCatalog.request.settle(catalogResponse(1, false));
await newerCatalog.result;
olderCatalog.request.settle(catalogResponse(1, true));
await olderCatalog.result;
assert.deepEqual(management.rows.value[0].actions, []);
// Commit acknowledgement and navigation recovery are separate operations.
const recoveryCatalog = await nextRequest(management.load);
recoveryCatalog.request.settle(catalogResponse());
await recoveryCatalog.result;
const failBootstrap = async () => {
  bootstraps += 1;
  session.initStatus = 'loading';
  await nextTick();
  session.initStatus = 'error';
  await nextTick();
  throw new Error('navigation unavailable');
};
session.loadAppInit = failBootstrap;
const committedRow = management.rows.value[0];
const committed = await nextRequest(() => management.execute(committedRow, committedRow.actions[0]));
committed.request.settle({ enabled: true });
await committed.result;
assert.equal(management.state.value, 'error');
assert.match(management.errorMessage.value, /状态已保存.*导航刷新失败/);
assert.deepEqual(management.rows.value, []);
const writesAfterCommit = pending.filter(item => item.intent === 'scenario.activation.set').length;

// A failed retry remains recoverable and never repeats the committed write.
await management.refresh();
assert.equal(management.state.value, 'error');
assert.equal(management.busy.value, false);
assert.equal(pending.filter(item => item.intent === 'scenario.activation.set').length, writesAfterCommit);
let releaseBootstrap!: () => void;
session.loadAppInit = async () => {
  bootstraps += 1;
  session.initStatus = 'loading';
  await new Promise<void>(resolve => { releaseBootstrap = resolve; });
  session.initStatus = 'ready';
  await nextTick();
};
const recovering = management.refresh();
await nextTick();
const retryBootstraps = bootstraps;
await management.refresh();
await management.execute(committedRow, committedRow.actions[0]);
assert.equal(bootstraps, retryBootstraps, 'duplicate refresh cannot bootstrap twice');
releaseBootstrap();
await flush();
assert.equal(pending.at(-1)!.intent, 'scenario.activation.catalog.get');
pending.at(-1)!.settle(catalogResponse());
await recovering;
assert.equal(management.state.value, 'ready');
assert.equal(management.busy.value, false);
assert.equal(pending.filter(item => item.intent === 'scenario.activation.set').length, writesAfterCommit);

// Company changes also invalidate an in-flight recovery.
session.initStatus = 'error';
await nextTick();
const obsoleteRecovery = management.refresh();
await nextTick();
session.recordContext = { ...session.recordContext, company_id: 2 } as NonNullable<typeof session.recordContext>;
await nextTick();
releaseBootstrap();
await obsoleteRecovery;
await flush();
assert.equal(pending.at(-1)!.params.company_id, 2);
pending.at(-1)!.settle(catalogResponse(2, false));
await flush();
assert.equal(management.state.value, 'ready');
assert.deepEqual(management.rows.value[0].actions, []);
// A global bootstrap uses the actual store, not the management mutation
// wrapper. Its failure must terminate loading and invalidate pending reads.
session.loadAppInit = originalBootstrap;
const catalogBeforeGlobalRefresh = await nextRequest(management.load);
const globalBootstrap = await nextRequest(() => session.loadAppInit({ force: true }));
const globalFailure = assert.rejects(globalBootstrap.result, /global bootstrap unavailable/);
await nextTick();
assert.deepEqual(management.rows.value, []);
globalBootstrap.request.fail(new Error('global bootstrap unavailable'));
await globalFailure;
await nextTick();
assert.equal(management.state.value, 'error', 'failed global bootstrap cannot leave an infinite spinner');
assert.equal(management.errorMessage.value, session.initError);
catalogBeforeGlobalRefresh.request.settle(catalogResponse(2, true));
await catalogBeforeGlobalRefresh.result;
assert.equal(management.state.value, 'error', 'old catalogue cannot clear session failure');
assert.deepEqual(management.rows.value, []);

// The same refresh control retries the actual bootstrap, with no scenario write.
const writesBeforeGlobalRetry = pending.filter(item => item.intent === 'scenario.activation.set').length;
const globalRetry = await nextRequest(management.refresh);
assert.equal(globalRetry.request.intent, 'system.init');
globalRetry.request.fail(new Error('global retry unavailable'));
await globalRetry.result;
assert.equal(management.state.value, 'error');
assert.equal(management.busy.value, false);
assert.equal(pending.filter(item => item.intent === 'scenario.activation.set').length, writesBeforeGlobalRetry);
managementScope.stop();
session.loadAppInit = originalBootstrap;
console.log('[business_scenario_management_test] PASS cases=13 consumer=actual transport=controlled');

// Readiness consumes native remediation and never displays another company's late response.
const { useEnterpriseReadiness } = await import('../src/composables/useEnterpriseReadiness.ts');
session.initStatus = 'ready';
const diagnosisScope = effectScope();
const diagnosis = diagnosisScope.run(() => useEnterpriseReadiness())!;
await flush();
const diagnosisResponse = (company: number, label = 'Native label') => ({
  contract_version: 'enterprise_readiness.v2', company_id: company, rules: [{
    rule_key: 'test', label, applicability: true, status: 'CONFIGURED', status_label: '已配置',
    failure_reason: '', suggested_responsible_party: '',
    remediation: { kind: 'handling_entry', key: 'native.action', label: 'Native entry' },
  }],
});
const oldDiagnosis = pending.at(-1)!;
assert.equal(oldDiagnosis.intent, 'enterprise.readiness.diagnosis.get');
assert.equal(oldDiagnosis.params.company_id, 2);
session.recordContext = { ...session.recordContext, company_id: 1 } as NonNullable<typeof session.recordContext>;
await flush();
const currentDiagnosis = pending.at(-1)!;
assert.equal(currentDiagnosis.params.company_id, 1);
currentDiagnosis.settle(diagnosisResponse(1));
await flush();
assert.equal(diagnosis.state.value, 'ready');
assert.equal(diagnosis.rules.value[0].remediation?.key, 'native.action');
oldDiagnosis.settle(diagnosisResponse(2, 'Stale'));
await flush();
assert.equal(diagnosis.rules.value[0].label, 'Native label');
const malformedDiagnosis = await nextRequest(diagnosis.load);
malformedDiagnosis.request.settle({ company_id: 1, rules: [] });
await malformedDiagnosis.result;
assert.equal(diagnosis.state.value, 'error');
assert.deepEqual(diagnosis.rules.value, []);
const wrongCompany = await nextRequest(diagnosis.load);
wrongCompany.request.settle(diagnosisResponse(2));
await wrongCompany.result;
assert.equal(diagnosis.state.value, 'error');
const beforeActivation = await nextRequest(diagnosis.load);
session.initStatus = 'loading';
await flush();
beforeActivation.request.settle(diagnosisResponse(1));
await beforeActivation.result;
assert.deepEqual(diagnosis.rules.value, []);
session.initStatus = 'ready';
await flush();
assert.equal(pending.at(-1)!.intent, 'enterprise.readiness.diagnosis.get');
pending.at(-1)!.settle(diagnosisResponse(1, 'After activation'));
await flush();
assert.equal(diagnosis.rules.value[0].label, 'After activation');
const afterUnmount = await nextRequest(diagnosis.load);
diagnosisScope.stop();
afterUnmount.request.settle(diagnosisResponse(1));
await afterUnmount.result;
assert.deepEqual(diagnosis.rules.value, []);
console.log('[enterprise_readiness_lifecycle_test] PASS cases=6 consumer=actual transport=controlled');
