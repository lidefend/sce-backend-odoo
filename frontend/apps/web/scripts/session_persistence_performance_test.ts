import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import './browser_globals_shim.ts';
import { createPinia, setActivePinia } from 'pinia';
import {
  decodeDurableSessionSnapshot,
  durableSessionStorageKey,
} from '../src/stores/sessionPersistence.ts';
import { resolveEntryAudience, resolveEntryBasePath } from '../src/services/entryNamespace.ts';

const scope = `${resolveEntryAudience() || 'unscoped'}:${resolveEntryBasePath() || 'root'}`;
const snapshotKey = durableSessionStorageKey(scope);
const measuredLegacyBytes = 421339;
const legacyFieldBytes: Record<string, number> = {
  menuTree: 242266,
  scenes: 74293,
  workspaceHome: 30323,
  roleSurfaceMap: 27598,
  initMeta: 18914,
  capabilityCatalog: 12996,
  user: 4318,
  currentAction: 1963,
  capabilityGroups: 1904,
  productFacts: 1819,
  capabilities: 1425,
  recordContext: 1269,
  activityPages: 842,
  roleSurface: 427,
  menuExpandedKeys: 187,
  defaultRoute: 76,
  workspaceHomeRef: 67,
  activeActivityPageKey: 46,
  lastTraceId: 38,
  bootstrapNextIntent: 13,
  lastIntent: 10,
  sessionDb: 9,
  lastWriteMode: 6,
  sceneVersion: 4,
  scenarioExpandedCenters: 2,
  scenarioExpandedScenarios: 2,
  activityPageCacheEpochs: 2,
  sceneActionHints: 2,
  lastLatencyMs: 2,
};

// Reconstruct the exact measured legacy payload size without using any
// production data. The derived fields are deliberately opaque: legacy restore
// must ignore them entirely.
const legacyFixture = Object.fromEntries(Object.entries(legacyFieldBytes).map(([key, bytes]) => {
  assert.ok(bytes >= 2, `${key} must fit a JSON string`);
  return [key, 'x'.repeat(bytes - 2)];
}));
const legacySerialized = JSON.stringify(legacyFixture);
assert.equal(Buffer.byteLength(legacySerialized), measuredLegacyBytes);

const originalSetItem = localStorage.setItem.bind(localStorage);
let durableWrites = 0;
let durableWriteBytes = 0;
let setItemElapsedMs = 0;
localStorage.setItem = (key: string, value: string) => {
  const startedAt = performance.now();
  originalSetItem(key, String(value));
  if (key === snapshotKey) {
    durableWrites += 1;
    durableWriteBytes += Buffer.byteLength(String(value));
    setItemElapsedMs += performance.now() - startedAt;
  }
};

let stringifyCalls = 0;
let stringifyElapsedMs = 0;
const originalStringify = JSON.stringify;
JSON.stringify = ((value: unknown, replacer?: Parameters<typeof JSON.stringify>[1], space?: string | number) => {
  const startedAt = performance.now();
  const serialized = originalStringify(value, replacer, space);
  stringifyCalls += 1;
  stringifyElapsedMs += performance.now() - startedAt;
  return serialized;
}) as typeof JSON.stringify;

setActivePinia(createPinia());
const { useSessionStore } = await import('../src/stores/session.ts');
const session = useSessionStore();
localStorage.clear();
sessionStorage.clear();
session.clearSession();
session.token = 'performance-token';
session.sessionDb = 'sc_dev_demo';
session.initStatus = 'ready';
session.user = {
  id: 7,
  name: 'Performance User',
  is_platform_admin: true,
  is_tenant_config_admin: true,
  platform_duty: { audience: 'platform-admin', duty_keys: ['operator'] },
  company_id: 3,
  company_name: 'Performance Company',
  company: { id: 3, name: 'Performance Company', display_name: 'Performance Company' },
} as typeof session.user;
session.recordContext = {
  contract_version: '1.0.0',
  enabled: true,
  model: 'project.project',
  company_id: 3,
  company_name: 'Performance Company',
  company_options: [{ company_id: 3, company_name: 'Performance Company' }],
  operation_strategy: 'build',
  operation_strategy_label: '施工',
  operation_options: [{ operation_strategy: 'build', operation_strategy_label: '施工' }],
  selected: {
    id: 2,
    name: 'Project 2',
    display_name: 'Project 2',
    company_id: 3,
    company_name: 'Performance Company',
    operation_strategy: 'build',
    operation_strategy_label: '施工',
    request_context: { project_id: 2, company_id: 3 },
  },
  options: [{ id: 2, display_name: 'Project 2' }],
  total: 1,
  query: 'project',
  request_context: { project_id: 2, company_id: 3 },
  selector: { intent: 'record.context.search', limit: 20 },
};

// One form-open-shaped controlled sequence. Transient trace, dirty and settling
// updates are deliberately included to prove they add no durable writes.
durableWrites = 0;
durableWriteBytes = 0;
setItemElapsedMs = 0;
stringifyCalls = 0;
stringifyElapsedMs = 0;
session.registerActivityPage({
  key: 'record:project.project:2',
  title: 'Project 2',
  route: '/f/project.project/2',
  kind: 'record_form',
  model: 'project.project',
  record_id: '2',
  record_context: session.currentActivityRecordContextSnapshot(),
  settling: true,
});
session.settleActivityPage('record:project.project:2');
session.updateActiveActivityDirty(true);
session.updateActiveActivityTitle('Project 2 · 项目概览');
session.updateActiveActivityRuntimeQuery({ search: 'active', group_by: ['state'] });
session.markActivityPageActive('record:project.project:2');
session.toggleMenuExpanded('menu.projects');
session.toggleScenarioCenter('project');
session.toggleScenarioExpanded('project.delivery');
session.ensureMenuExpanded(['menu.projects', 'menu.tasks']);
session.ensureScenarioExpanded('project', 'project.delivery');
session.recordIntentTrace({ traceId: 'perf-trace', intent: 'ui.contract.v2', latencyMs: 9, writeMode: 'read' });
const stringifyCallsBeforeFlush = stringifyCalls;
const stringifyElapsedBeforeFlush = stringifyElapsedMs;
session.flushDurablePersist();
const durablePersistStringifyCalls = stringifyCalls - stringifyCallsBeforeFlush;
const durablePersistStringifyElapsedMs = stringifyElapsedMs - stringifyElapsedBeforeFlush;
await new Promise((resolve) => setTimeout(resolve, 10));

assert.equal(durableWrites, 1, 'controlled form-open sequence must write one durable snapshot');
const stored = localStorage.getItem(snapshotKey);
assert.ok(stored);
const durableSnapshotBytes = Buffer.byteLength(stored);
const decoded = decodeDurableSessionSnapshot(stored);
assert.equal(decoded.status, 'current');
assert.equal(decoded.snapshot?.user && Object.keys(decoded.snapshot.user).sort().join(','), 'id,name');

const restoreSamples: number[] = [];
for (let index = 0; index < 20; index += 1) {
  const startedAt = performance.now();
  session.restore();
  restoreSamples.push(performance.now() - startedAt);
}
restoreSamples.sort((left, right) => left - right);
const restoreMedianMs = restoreSamples[Math.floor(restoreSamples.length / 2)];

JSON.stringify = originalStringify;
localStorage.setItem = originalSetItem;

const report = {
  schema: 'sce-r12-b-session-persistence-performance/v1',
  mode: 'controlled_in_process',
  baseline: {
    legacy_payload_bytes: measuredLegacyBytes,
    form_open_durable_writes: '11-12',
  },
  candidate_fixture: {
    simulated_durable_updates: 12,
    durable_writes: durableWrites,
    merged_updates: 12 - durableWrites,
    durable_snapshot_bytes: durableSnapshotBytes,
    total_durable_write_bytes: durableWriteBytes,
    sequence_stringify_calls: stringifyCalls,
    sequence_stringify_elapsed_ms: Number(stringifyElapsedMs.toFixed(3)),
    durable_persist_stringify_calls: durablePersistStringifyCalls,
    durable_persist_stringify_elapsed_ms: Number(durablePersistStringifyElapsedMs.toFixed(3)),
    set_item_elapsed_ms: Number(setItemElapsedMs.toFixed(3)),
    restore_median_ms: Number(restoreMedianMs.toFixed(3)),
    restore_samples_ms: restoreSamples.map((value) => Number(value.toFixed(3))),
  },
  caveat: 'Controlled Node.js measurement on the production snapshot builder and Session restore path; not browser click-to-interactive or deployed HTTP evidence.',
};

const output = process.env.R12_B_PERFORMANCE_OUTPUT
  ? path.resolve(process.env.R12_B_PERFORMANCE_OUTPUT)
  : '';
if (output) {
  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.writeFileSync(output, `${JSON.stringify(report, null, 2)}\n`);
}
console.log(`[session_persistence_performance_test] PASS ${JSON.stringify(report.candidate_fixture)}`);
