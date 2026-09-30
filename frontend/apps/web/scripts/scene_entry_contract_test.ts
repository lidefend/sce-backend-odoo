import { strict as assert } from 'node:assert';
import {
  SCENE_CONTRACT_ENTRY_INTENTS,
  ownsSceneRoute,
  resolveSceneContractEntryIntent,
} from '../src/app/sceneEntryContract';

// The scene runtime owns exactly one route.
assert.equal(ownsSceneRoute('scene'), true);
for (const foreign of ['scene-home', 'scene-my-work', 'business-config', 'action', 'record', '', null, undefined]) {
  assert.equal(ownsSceneRoute(foreign), false, `foreign route must not be owned: ${String(foreign)}`);
}

const base = { sceneKey: 'project.management', queryEntryIntent: undefined, querySceneIntent: undefined };

// A foreign route never yields a scene entry intent, even when it carries a
// business entry disposition value.
for (const businessDisposition of ['handling', 'query', 'analysis', 'config', 'master_data', 'source_fact']) {
  for (const foreign of ['business-config', 'action', 'record', 'scene-home']) {
    assert.equal(
      resolveSceneContractEntryIntent({ ...base, routeName: foreign, queryEntryIntent: businessDisposition }),
      '',
      `business disposition leaked as a scene intent on ${foreign}: ${businessDisposition}`,
    );
  }
}

// The owned scene route still honours the scene entry intent.
assert.equal(
  resolveSceneContractEntryIntent({ ...base, routeName: 'scene', queryEntryIntent: 'project.dashboard.enter' }),
  'project.dashboard.enter',
);
assert.equal(
  resolveSceneContractEntryIntent({ ...base, routeName: 'scene', querySceneIntent: 'project.initiation.enter' }),
  'project.initiation.enter',
);
assert.equal(
  resolveSceneContractEntryIntent({ ...base, routeName: 'scene', queryEntryIntent: 'project.dashboard.enter', querySceneIntent: 'ignored' }),
  'project.dashboard.enter',
);

// A scene without a query intent falls back to the declared contract intent only.
assert.equal(resolveSceneContractEntryIntent({ ...base, routeName: 'scene' }), 'project.dashboard.enter');
assert.equal(
  resolveSceneContractEntryIntent({ routeName: 'scene', sceneKey: 'projects.list', queryEntryIntent: '', querySceneIntent: '   ' }),
  '',
);
assert.equal(
  resolveSceneContractEntryIntent({ routeName: 'business-config', sceneKey: 'project.management', queryEntryIntent: '', querySceneIntent: '' }),
  '',
);

assert.deepEqual(Object.keys(SCENE_CONTRACT_ENTRY_INTENTS), ['workspace.home', 'dashboard.company', 'project.management']);
console.log('[scene_entry_contract_test] PASS cases=40');
