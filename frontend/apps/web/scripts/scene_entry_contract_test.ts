import { strict as assert } from 'node:assert';
import {
  ownsSceneRoute,
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
