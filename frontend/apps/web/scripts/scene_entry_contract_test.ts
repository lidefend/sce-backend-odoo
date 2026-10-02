import { strict as assert } from 'node:assert';
import {
  ownsSceneRoute,
  resolveSceneRuntimeDiagnostic,
  resolveSceneContractEntryIntent,
} from '../src/app/sceneEntryContract';

import { getSceneByKey, setSceneRegistryFromSceneReadyContract } from '../src/app/resolvers/sceneRegistry';
let cases = 0;
const equal: typeof assert.equal = (...args) => { cases += 1; assert.equal(...args); };

// The scene runtime owns exactly one route.
equal(ownsSceneRoute('scene'), true);
for (const foreign of ['scene-home', 'scene-my-work', 'business-config', 'action', 'record', '', null, undefined]) {
  equal(ownsSceneRoute(foreign), false, `foreign route must not be owned: ${String(foreign)}`);
}

const base = { declaredTarget: { intent: 'project.dashboard.enter' }, queryEntryIntent: undefined, querySceneIntent: undefined };

// A foreign route never yields a scene entry intent, even when it carries a
// business entry disposition value.
for (const businessDisposition of ['handling', 'query', 'analysis', 'config', 'master_data', 'source_fact']) {
  for (const foreign of ['business-config', 'action', 'record', 'scene-home']) {
    equal(
      resolveSceneContractEntryIntent({ ...base, routeName: foreign, queryEntryIntent: businessDisposition }),
      '',
      `business disposition leaked as a scene intent on ${foreign}: ${businessDisposition}`,
    );
  }
}

// The owned scene route still honours the scene entry intent.
equal(
  resolveSceneContractEntryIntent({ ...base, routeName: 'scene', queryEntryIntent: 'project.dashboard.enter' }),
  'project.dashboard.enter',
);
equal(
  resolveSceneContractEntryIntent({ ...base, routeName: 'scene', querySceneIntent: 'project.initiation.enter' }),
  'project.initiation.enter',
);
equal(
  resolveSceneContractEntryIntent({ ...base, routeName: 'scene', queryEntryIntent: 'project.dashboard.enter', querySceneIntent: 'ignored' }),
  'project.dashboard.enter',
);

// A scene without a query intent falls back to the declared contract intent only.
equal(resolveSceneContractEntryIntent({ ...base, routeName: 'scene' }), 'project.dashboard.enter');
equal(
  resolveSceneContractEntryIntent({ routeName: 'scene', declaredTarget: {}, queryEntryIntent: '', querySceneIntent: '   ' }),
  '',
);
equal(
  resolveSceneContractEntryIntent({ routeName: 'business-config', declaredTarget: base.declaredTarget, queryEntryIntent: '', querySceneIntent: '' }),
  '',
);

// Unknown/new scenes work without a frontend model or scene allowlist.
equal(resolveSceneContractEntryIntent({ ...base, routeName: 'scene', declaredTarget: { intent: 'custom.entry' } }), 'custom.entry');
equal(resolveSceneContractEntryIntent({ ...base, routeName: 'scene', declaredTarget: null }), '');
equal(resolveSceneContractEntryIntent({ ...base, routeName: 'scene', declaredTarget: { entry_intent: 'override.entry', intent: 'base.entry' } }), 'override.entry');

setSceneRegistryFromSceneReadyContract({ scenes: [{
  scene: { key: 'custom.dashboard', title: 'Configured title' },
  page: { route: '/s/custom.dashboard' },
  meta: { target: { intent: 'custom.entry', entry_intent: 'custom.override', model: 'test.item' } },
}] });
const projected = getSceneByKey('custom.dashboard');
equal(projected?.label, 'Configured title');
equal(projected?.target.intent, 'custom.entry');
equal(projected?.target.entry_intent, 'custom.override');
equal(resolveSceneContractEntryIntent({ ...base, routeName: 'scene', declaredTarget: projected?.target }), 'custom.override');
equal(getSceneByKey('project.management'), null, 'no synthetic scene when absent from effective contract');
console.log(`[scene_entry_contract_test] PASS cases=${cases}`);

import { resolveSceneRuntimeFetchRequest } from '../src/app/sceneRuntimeFetchContract';
import { createReadonlyBlockLoader } from '../src/app/readonlyBlockRequest';
const declaredHint = { intent: 'custom.block.fetch', params: { block_key: 'first', project_context: { project_id: 7, allowed: [1, 2] }, filters: [['state', '=', 'done']] }, context: { company_id: 8, nested: { key: 'value' } } };
assert.deepEqual(resolveSceneRuntimeFetchRequest(declaredHint), declaredHint); cases += 1;
assert.deepEqual(resolveSceneRuntimeFetchRequest({ intent: 'custom.unlisted.fetch', params: { arbitrary: { nested: true } } }),
  { intent: 'custom.unlisted.fetch', params: { arbitrary: { nested: true } } }); cases += 1;
assert.deepEqual(resolveSceneRuntimeFetchRequest({ intent: 'custom.block.fetch', params: {}, project_id: 7, block_key: 'legacy' }),
  { intent: 'custom.block.fetch', params: {} }); cases += 1;
for (const hint of [null, [], {}, { intent: 7, params: {} }, { intent: 'fetch', params: [] }, { intent: 'fetch', params: {}, context: false }]) {
  equal(resolveSceneRuntimeFetchRequest(hint), null);
}
let published = 0;
const lifecycle = createReadonlyBlockLoader<number>({ reset() {}, success() { published += 1; }, error() {}, settled() {} });
let current!: () => boolean;
let resolvePending!: (value: number) => void;
const pending = lifecycle.load(isCurrent => { current = isCurrent; return new Promise(resolve => { resolvePending = resolve; }); });
equal(current(), true);
await lifecycle.load(null);
equal(current(), false);
resolvePending(1); await pending;
equal(published, 0);
console.log(`[scene_runtime_fetch_contract_test] PASS total_cases=${cases}`);

const defaultCopy = (_key: string, fallback: string) => fallback;
for (const runtime of [{}, { bridge_aligned: true }, { missing_required_count: 0, active_transition_count: 0 },
  { missing_required_count: true, active_transition_count: Infinity }, { bridge_aligned: 'false' }]) {
  equal(resolveSceneRuntimeDiagnostic(runtime, defaultCopy), '');
}
equal(resolveSceneRuntimeDiagnostic({ missing_required_count: 2 }, defaultCopy), '待补充事项：2');
equal(resolveSceneRuntimeDiagnostic({ active_transition_count: 3 }, defaultCopy), '可办理步骤：3');
equal(resolveSceneRuntimeDiagnostic({ bridge_aligned: false }, defaultCopy), '当前场景语义尚未完全对齐。');
equal(resolveSceneRuntimeDiagnostic({ semantic_bridge_aligned: false }, defaultCopy), '当前场景语义尚未完全对齐。');
equal(resolveSceneRuntimeDiagnostic({ bridge_aligned: true, semantic_bridge_aligned: false }, defaultCopy), '');
equal(resolveSceneRuntimeDiagnostic({ missing_required_count: 1, active_transition_count: 2, bridge_aligned: false }, defaultCopy), '待补充事项：1；可办理步骤：2；当前场景语义尚未完全对齐。');
equal(resolveSceneRuntimeDiagnostic({ active_transition_count: 1 }, () => 'Declared transition'), 'Declared transition：1');
console.log(`[scene_runtime_diagnostic_test] PASS diagnostic_cases=12 total_cases=${cases}`);
