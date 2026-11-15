import assert from 'node:assert/strict';
import './browser_globals_shim.ts';
import { createPinia, setActivePinia } from 'pinia';
import { installSessionPersistenceLifecycle } from '../src/stores/sessionPersistence.ts';

let cases = 0;
const check = (condition: unknown, message: string): void => {
  cases += 1;
  assert.ok(condition, message);
};
const waitForScheduledFlush = () => new Promise((resolve) => setTimeout(resolve, 10));

const originalSetItem = localStorage.setItem.bind(localStorage);
let writes: Array<{ key: string; value: string }> = [];
localStorage.setItem = (key: string, value: string) => {
  writes.push({ key, value: String(value) });
  originalSetItem(key, String(value));
};

setActivePinia(createPinia());
const { useSessionStore } = await import('../src/stores/session.ts');
const session = useSessionStore();

localStorage.clear();
sessionStorage.clear();
session.clearSession();
session.token = 'scheduler-test-token';
session.sessionDb = 'sc_dev_demo';
session.initStatus = 'ready';
session.user = { id: 7, name: 'Scheduler User', is_platform_admin: true } as typeof session.user;
session.recordContext = {
  model: 'project.project',
  company_id: 3,
  company_name: 'Company',
  selected: { id: 2, display_name: 'Project 2', company_id: 3 },
  request_context: { project_id: 2 },
};
session.activityPages = [{
  key: 'record:project.project:2',
  title: 'Project 2',
  route: '/f/project.project/2',
  kind: 'record_form',
  model: 'project.project',
  record_id: '2',
  record_context: { company_id: 3 },
  dirty: false,
  settling: true,
  created_at: 1,
  last_active_at: 1,
}];
session.activeActivityPageKey = 'record:project.project:2';

writes = [];
session.toggleMenuExpanded('menu-a');
session.toggleMenuExpanded('menu-b');
session.toggleMenuExpanded('menu-a');
await waitForScheduledFlush();
check(writes.length === 1, 'consecutive durable updates must coalesce into one snapshot write');
cases += 1;
const coalesced = JSON.parse(writes[0].value);
assert.deepEqual(coalesced.menuExpansionPreferences.menuExpandedKeys, ['menu-b']);
check(coalesced.user && Object.keys(coalesced.user).sort().join(',') === 'id,name', 'privilege fields must never enter the durable snapshot');

writes = [];
session.toggleScenarioCenter('center-a');
check(session.flushDurablePersist() === true, 'first explicit flush must consume pending state');
check(session.flushDurablePersist() === false, 'second explicit flush must be a no-op');
check(writes.length === 1, 'explicit flush must write the pending snapshot exactly once');

writes = [];
session.toggleMenuExpanded('immediate-wins');
session.persistDurableNow();
await waitForScheduledFlush();
check(writes.length === 1, 'an immediate durable write must supersede its pending callback');

writes = [];
session.recordIntentTrace({ traceId: 'trace-1', intent: 'ui.contract.v2', latencyMs: 12, writeMode: 'read' });
check(writes.length === 0, 'transient diagnostics must not write durable Session');
check(session.lastTraceId === 'trace-1', 'diagnostic values remain available in memory');
session.settleActivityPage('record:project.project:2');
check(writes.length === 0, 'settling changes must not write durable Session');
check(session.activityPages[0].settling === false, 'settling remains a live in-memory transition');
session.updateActiveActivityDirty(true);
check(writes.length === 0, 'activity dirty changes must not write durable Session');
check(session.activityPages[0].dirty === true, 'activity dirty remains available for SPA navigation');

const fetchRuntime = globalThis.fetch;
globalThis.fetch = (async () => new Response(JSON.stringify({
  ok: true,
  data: {
    schema_version: 'product_configuration_capability.v1',
    login_home: { blocks: [] },
    business_config: { capabilities: [] },
    user_capabilities: { items: [], empty_message: '' },
  },
  meta: {},
}), { status: 200, headers: { 'content-type': 'application/json' } })) as typeof fetch;
await session.loadProductCapabilityCatalog(true);
globalThis.fetch = fetchRuntime;
check(writes.length === 0, 'live product capability catalog must not write durable Session');

const originalSetTimeout = globalThis.setTimeout;
const originalClearTimeout = globalThis.clearTimeout;
const callbacks: Array<() => void> = [];
let clearCalls = 0;
(globalThis as { setTimeout: unknown }).setTimeout = ((callback: () => void) => {
  callbacks.push(callback);
  return callbacks.length;
}) as typeof setTimeout;
(globalThis as { clearTimeout: unknown }).clearTimeout = (() => {
  clearCalls += 1;
}) as typeof clearTimeout;

writes = [];
session.toggleMenuExpanded('queued-before-clear');
session.clearSession();
check(clearCalls > 0, 'cleanup must cancel the queued timer');
callbacks.shift()?.();
check(writes.length === 0, 'a callback from the cleared generation must fail closed');

writes = [];
session.token = 'next-session-token';
session.toggleMenuExpanded('new-generation');
const oldGenerationCallback = callbacks[0];
session.clearSession();
session.token = 'third-session-token';
session.toggleMenuExpanded('current-generation');
const currentGenerationCallback = callbacks[1];
oldGenerationCallback?.();
check(writes.length === 0, 'an old callback must not clear or write the new pending generation');
currentGenerationCallback?.();
check(writes.length === 1, 'the current generation callback must still flush exactly once');

globalThis.setTimeout = originalSetTimeout;
globalThis.clearTimeout = originalClearTimeout;

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
let lifecycleFlushes = 0;
writes = [];
session.toggleMenuExpanded('lifecycle-pending');
const disposeLifecycle = installSessionPersistenceLifecycle({
  windowTarget,
  documentTarget,
  flush: () => {
    if (session.flushDurablePersist()) lifecycleFlushes += 1;
  },
});
check(windowTarget.listeners.get('pagehide')?.size === 1, 'pagehide listener installs once');
check(documentTarget.listeners.get('visibilitychange')?.size === 1, 'visibility listener installs once');
documentTarget.visibilityState = 'visible';
documentTarget.dispatch('visibilitychange');
check(lifecycleFlushes === 0, 'visible state must not flush');
documentTarget.visibilityState = 'hidden';
documentTarget.dispatch('visibilitychange');
windowTarget.dispatch('pagehide');
check(lifecycleFlushes === 1, 'shared lifecycle pending state must flush once');
check(writes.length === 1, 'visibilitychange and pagehide must not duplicate storage writes');
disposeLifecycle();
check(windowTarget.listeners.get('pagehide')?.size === 0, 'pagehide listener is removed on disposal');
check(documentTarget.listeners.get('visibilitychange')?.size === 0, 'visibility listener is removed on disposal');

console.log(`[session_persistence_scheduler_test] PASS cases=${cases}`);
