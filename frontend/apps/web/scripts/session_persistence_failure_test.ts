import assert from 'node:assert/strict';
import './browser_globals_shim.ts';
import { createPinia, setActivePinia } from 'pinia';
import {
  durableSessionStorageKey,
  installSessionPersistenceLifecycle,
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

class ControlledStorage implements Storage {
  data = new Map<string, string>();
  setCalls: Array<{ key: string; value: string }> = [];
  removeCalls: string[] = [];
  getCalls: string[] = [];
  setFailure: (call: number, key: string) => boolean = () => false;
  getFailure: (key: string) => boolean = () => false;
  removeFailure: (key: string) => boolean = () => false;

  get length() {
    return this.data.size;
  }

  clear(): void {
    this.data.clear();
  }

  getItem(key: string): string | null {
    this.getCalls.push(key);
    if (this.getFailure(key)) throw new DOMException('get denied', 'SecurityError');
    return this.data.has(key) ? this.data.get(key)! : null;
  }

  key(index: number): string | null {
    return [...this.data.keys()][index] ?? null;
  }

  removeItem(key: string): void {
    this.removeCalls.push(key);
    if (this.removeFailure(key)) throw new DOMException('remove denied', 'SecurityError');
    this.data.delete(key);
  }

  setItem(key: string, value: string): void {
    const call = this.setCalls.length + 1;
    this.setCalls.push({ key, value: String(value) });
    if (this.setFailure(call, key)) throw new DOMException('quota exceeded', 'QuotaExceededError');
    this.data.set(key, String(value));
  }
}

class LifecycleTarget {
  listeners = new Map<string, () => void>();
  constructor(public visibilityState = 'visible') {}
  addEventListener(type: string, listener: () => void) {
    this.listeners.set(type, listener);
  }
  removeEventListener(type: string) {
    this.listeners.delete(type);
  }
  fire(type: string) {
    this.listeners.get(type)?.();
  }
}

type Store = ReturnType<typeof import('../src/stores/session.ts').useSessionStore>;

function installStorages(): { local: ControlledStorage; perTab: ControlledStorage } {
  const local = new ControlledStorage();
  const perTab = new ControlledStorage();
  (globalThis as unknown as { localStorage: Storage }).localStorage = local;
  (globalThis as unknown as { sessionStorage: Storage }).sessionStorage = perTab;
  return { local, perTab };
}

function newStore(): Store {
  setActivePinia(createPinia());
  return useSessionStore();
}

function seedState(session: Store, companyId = 3, recordId = 2) {
  session.token = 'review-token';
  session.sessionDb = 'sc_dev_demo';
  session.user = { id: 7, name: 'Review User' } as typeof session.user;
  session.recordContext = {
    model: 'project.project',
    company_id: companyId,
    company_name: `Company ${companyId}`,
    operation_strategy: 'build',
    operation_strategy_label: '施工',
    selected: { id: recordId, display_name: `Project ${recordId}`, company_id: companyId },
    request_context: { company_id: companyId, current_project_id: recordId },
  };
  session.activityPages = [{
    key: `record:project.project:${recordId}`,
    title: `Project ${recordId}`,
    route: `/f/project.project/${recordId}`,
    kind: 'record_form',
    model: 'project.project',
    record_id: String(recordId),
    record_context: { company_id: companyId },
    created_at: 1,
    last_active_at: 2,
  }];
  session.activeActivityPageKey = session.activityPages[0].key;
  session.menuExpandedKeys = ['menu.projects'];
  session.scenarioExpandedCenters = ['project'];
  session.scenarioExpandedScenarios = ['project.delivery'];
}

function lifecycleFlush(session: Store, visibilityState = 'hidden') {
  const windowTarget = new LifecycleTarget('visible');
  const documentTarget = new LifecycleTarget(visibilityState);
  installSessionPersistenceLifecycle({
    windowTarget,
    documentTarget,
    flush: () => { session.flushDurablePersist(); },
  });
  return { windowTarget, documentTarget };
}

const { useSessionStore } = await import('../src/stores/session.ts');

// A. Full failure -> degraded -> pagehide retries the latest full state.
{
  const storage = installStorages();
  const session = newStore();
  seedState(session);
  storage.local.setFailure = (call, key) => key === snapshotKey && call === 1;
  session.toggleMenuExpanded('retry.pending');
  const lifecycle = lifecycleFlush(session);
  lifecycle.documentTarget.fire('visibilitychange');
  const degraded = JSON.parse(storage.local.getItem(snapshotKey) || '{}');
  check(degraded.activityPages?.length === 0, 'first failure is persisted as a degraded snapshot');
  lifecycle.windowTarget.fire('pagehide');
  const full = JSON.parse(storage.local.getItem(snapshotKey) || '{}');
  check(storage.local.setCalls.length === 3, 'pagehide retries exactly one full snapshot');
  check(full.activityPages?.length === 1, 'pagehide retry restores activity recovery state');
  check(full.activeTab === 'record:project.project:2', 'pagehide retry restores active tab');
  check(full.menuExpansionPreferences.menuExpandedKeys.includes('retry.pending'), 'pagehide retry persists latest expansion');
}

// B. Full failure -> degraded -> visibilitychange retries full state.
{
  const storage = installStorages();
  const session = newStore();
  seedState(session);
  storage.local.setFailure = (call, key) => key === snapshotKey && call === 1;
  session.toggleMenuExpanded('retry.visibility');
  const lifecycle = lifecycleFlush(session);
  lifecycle.windowTarget.fire('pagehide');
  lifecycle.documentTarget.fire('visibilitychange');
  const full = JSON.parse(storage.local.getItem(snapshotKey) || '{}');
  check(storage.local.setCalls.length === 3, 'visibilitychange retries after a degraded pagehide');
  check(full.activityPages?.length === 1, 'visibility retry restores activity recovery state');
  check(full.activeTab === 'record:project.project:2', 'visibility retry restores active tab');
}

// C. Full + minimal failure keeps the obligation; the next durable update retries.
{
  const storage = installStorages();
  const session = newStore();
  seedState(session);
  storage.local.setFailure = (call, key) => key === snapshotKey && call <= 2;
  session.toggleMenuExpanded('retry.after.failed');
  const lifecycle = lifecycleFlush(session);
  lifecycle.documentTarget.fire('visibilitychange');
  check(storage.local.setCalls.length === 2, 'first flush attempts full and minimal writes');
  session.toggleMenuExpanded('retry.after.failed');
  await new Promise((resolve) => setTimeout(resolve, 10));
  const stored = JSON.parse(storage.local.getItem(snapshotKey) || '{}');
  check(storage.local.setCalls.length === 3, 'next durable update retries the retained obligation once');
  check(stored.activityPages?.length === 1, 'later durable update eventually restores full recovery state');
}

// D. A degraded snapshot followed by a context switch retries the latest context.
{
  const storage = installStorages();
  const session = newStore();
  seedState(session);
  storage.local.setFailure = (call, key) => key === snapshotKey && call === 1;
  session.toggleMenuExpanded('context.retry');
  const lifecycle = lifecycleFlush(session);
  lifecycle.documentTarget.fire('visibilitychange');
  seedState(session, 4, 5);
  session.toggleMenuExpanded('context.latest');
  await new Promise((resolve) => setTimeout(resolve, 10));
  const stored = JSON.parse(storage.local.getItem(snapshotKey) || '{}');
  check(stored.recordContext?.company_id === 4, 'retry rebuilds the snapshot from the latest company');
  check(stored.recordContext?.selected?.id === 5, 'retry rebuilds the snapshot from the latest record');
  check(stored.activityPages?.[0]?.record_id === '5', 'retry uses latest activity context');
}

// E. A queued retry from a degraded generation cannot write after clearSession.
{
  const storage = installStorages();
  const session = newStore();
  seedState(session);
  storage.local.setFailure = (call, key) => key === snapshotKey && call === 1;
  session.toggleMenuExpanded('degraded.before.clear');
  const lifecycle = lifecycleFlush(session);
  lifecycle.documentTarget.fire('visibilitychange');
  const originalSetTimeout = globalThis.setTimeout;
  const callbacks: Array<() => void> = [];
  globalThis.setTimeout = ((callback: () => void) => {
    callbacks.push(callback);
    return callbacks.length;
  }) as typeof setTimeout;
  session.toggleMenuExpanded('queued.retry');
  const writesBeforeClear = storage.local.setCalls.length;
  session.clearSession();
  callbacks[0]?.();
  check(storage.local.setCalls.length === writesBeforeClear, 'old degraded retry cannot write after clearSession');
  globalThis.setTimeout = originalSetTimeout;
}

// F. Full success consumes the obligation; two lifecycle events write once.
{
  const storage = installStorages();
  const session = newStore();
  seedState(session);
  session.toggleMenuExpanded('single.flush');
  const lifecycle = lifecycleFlush(session);
  lifecycle.documentTarget.fire('visibilitychange');
  lifecycle.windowTarget.fire('pagehide');
  check(storage.local.setCalls.length === 1, 'full success is not duplicated by the second lifecycle event');
}

// G. A failed full retry must not schedule itself in a tight loop.
{
  const storage = installStorages();
  const session = newStore();
  seedState(session);
  storage.local.setFailure = (_call, key) => key === snapshotKey;
  let scheduled = 0;
  const originalSetTimeout = globalThis.setTimeout;
  globalThis.setTimeout = ((callback: () => void) => {
    scheduled += 1;
    return originalSetTimeout(callback, 0);
  }) as typeof setTimeout;
  session.toggleMenuExpanded('no.loop');
  const lifecycle = lifecycleFlush(session);
  lifecycle.documentTarget.fire('visibilitychange');
  lifecycle.windowTarget.fire('pagehide');
  const scheduledAfterFailures = scheduled;
  await new Promise((resolve) => originalSetTimeout(resolve, 10));
  check(scheduledAfterFailures === 1, 'degraded/failed retries do not schedule automatic loops');
  check(scheduled === scheduledAfterFailures, 'failed retries remain event-driven');
  globalThis.setTimeout = originalSetTimeout;
}

// P2-A: localStorage removal failure cannot block per-tab token removal.
{
  const storage = installStorages();
  const session = newStore();
  seedState(session);
  storage.perTab.setItem(tokenKey, 'token-to-remove');
  storage.local.removeFailure = (key) => key === snapshotKey;
  let thrown = '';
  try { session.clearSession(); } catch (error) { thrown = String(error); }
  check(!thrown, 'Snapshot removal failure does not escape clearSession');
  check(session.token === null && session.user === null, 'memory Session is cleared');
  check(storage.perTab.getItem(tokenKey) === null, 'per-tab token is removed despite localStorage failure');
}

// P2-B: localStorage read failure does not block restore or cleanup.
{
  const storage = installStorages();
  storage.perTab.setItem(tokenKey, 'read-survives');
  storage.local.getFailure = () => true;
  const session = newStore();
  let thrown = '';
  try {
    session.restore();
    session.clearSession();
  } catch (error) {
    thrown = String(error);
  }
  check(!thrown, 'localStorage read failure does not block restore/cleanup');
}

// P2-C: both storage media failing still clears memory and invalidates retries.
{
  const storage = installStorages();
  const session = newStore();
  seedState(session);
  const originalSetTimeout = globalThis.setTimeout;
  const callbacks: Array<() => void> = [];
  globalThis.setTimeout = ((callback: () => void) => {
    callbacks.push(callback);
    return callbacks.length;
  }) as typeof setTimeout;
  session.toggleMenuExpanded('generation.must.die');
  storage.local.removeFailure = () => true;
  storage.perTab.removeFailure = () => true;
  const writesBeforeClear = storage.local.setCalls.length;
  let thrown = '';
  try { session.clearSession(); } catch (error) { thrown = String(error); }
  callbacks[0]?.();
  check(!thrown, 'dual storage removal failure does not escape clearSession');
  check(session.token === null && session.user === null && session.activityPages.length === 0, 'memory Session clears under dual storage failure');
  check(storage.local.setCalls.length === writesBeforeClear, 'old generation remains invalid under dual storage failure');
  globalThis.setTimeout = originalSetTimeout;
}

// P2-D: normal cleanup keeps existing behavior.
{
  const storage = installStorages();
  const session = newStore();
  seedState(session);
  session.persistDurableNow();
  storage.perTab.setItem(tokenKey, 'normal-token');
  session.clearSession();
  check(storage.local.getItem(snapshotKey) === null, 'normal clear removes Snapshot');
  check(storage.perTab.getItem(tokenKey) === null, 'normal clear removes token');
  check(session.token === null && session.user === null, 'normal clear removes memory identity');
}

console.log(`[session_persistence_failure_test] PASS cases=${cases}`);
