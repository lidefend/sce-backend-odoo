#!/usr/bin/env node
import assert from 'node:assert/strict';

import {
  applyReleasedNavigationTarget,
  findReleasedNavigationTargetByMenuXmlid,
  findReleasedNavigationTargetBySceneKey,
} from './released_navigation_target.mjs';
import {
  declaredRowSceneNavigation,
  deniedRoleCandidatesFor,
  entryFingerprint,
  loadDeclaredSceneEntries,
  loadOverlay,
  matrixSucceeded,
  negativePlanByCandidate,
  recordedEntryStatus,
  runtimeRoleSceneTarget,
  sceneBehaviour,
  sceneNavigationMatchesUrl,
} from './business_entry_matrix_model.mjs';

let cases = 0;
const check = (actual, expected, label) => {
  assert.deepEqual(actual, expected, label);
  cases += 1;
};

const action = 'smart_construction_core.action_shared';
const nav = [{
  menu_xmlid: 'smart_construction_core.menu_scene_first',
  menu_id: 10,
  action_id: 0,
  route: '/s/entry.first',
  scene_key: 'entry.first',
  entry_target: { type: 'scene', scene_key: 'entry.first', route: '/s/entry.first' },
  children: [],
}, {
  menu_xmlid: 'smart_construction_core.menu_action_one',
  menu_id: 11,
  action_id: 200,
  action_xmlid: action,
  route: '/a/200?menu_id=11',
  meta: {
    action_xmlid: action,
    menu_xmlid: 'smart_construction_core.menu_action_one',
    entry_target: { type: 'action', route: '/a/200?menu_id=11' },
  },
  children: [],
}, {
  menu_xmlid: 'smart_construction_core.menu_action_two',
  menu_id: 12,
  action_id: 200,
  action_xmlid: action,
  route: '/a/200?menu_id=12',
  meta: {
    action_xmlid: action,
    menu_xmlid: 'smart_construction_core.menu_action_two',
    entry_target: { type: 'compatibility', route: '/a/200?menu_id=12' },
  },
  children: [],
}];

check(
  findReleasedNavigationTargetByMenuXmlid(nav, 'smart_construction_core.menu_scene_first'),
  {
    action_id: 0,
    menu_id: 10,
    route: '/s/entry.first',
    scene_key: 'entry.first',
    entry_target: { type: 'scene', scene_key: 'entry.first', route: '/s/entry.first' },
    entry_target_type: 'scene',
    action_xmlid: '',
    menu_xmlid: 'smart_construction_core.menu_scene_first',
  },
  'a no-action scene preserves its declared runtime route and scene identity',
);

check(
  findReleasedNavigationTargetByMenuXmlid(nav, 'smart_construction_core.menu_action_two', action)?.route,
  '/a/200?menu_id=12',
  'the same action is addressed through the selected menu, not the first action occurrence',
);

check(
  findReleasedNavigationTargetByMenuXmlid(nav, 'smart_construction_core.menu_action_two', 'other.action'),
  null,
  'a menu identity cannot borrow another action identity',
);

check(
  findReleasedNavigationTargetBySceneKey([{
    menu_xmlid: 'scene.contract.workspace_home',
    menu_id: 42,
    action_id: 0,
    route: '/s/workspace.home',
    scene_key: 'workspace.home',
  }, ...nav], 'workspace.home')?.menu_xmlid,
  'scene.contract.workspace_home',
  'a released actionless scene carrier is resolved by its scene identity when the catalogue XMLID aliases it',
);
check(
  findReleasedNavigationTargetBySceneKey([{
    menu_xmlid: 'smart_construction_core.menu_action_scene',
    menu_id: 43,
    action_id: 201,
    route: '/s/entry.action_scene',
    scene_key: 'entry.action_scene',
  }], 'entry.action_scene'),
  null,
  'an action-bearing scene cannot be accepted as the actionless carrier',
);

const contextualScene = declaredRowSceneNavigation([{
  action_id: 676,
  rowRules: [{
    target: {
      route: '/s/project.management',
      scene_key: 'project.management',
      entry_intent: 'project.dashboard.enter',
      query: { project_id: '${id}' },
    },
  }],
}], 676, 130);
check(contextualScene?.scene_key, 'project.management', 'a declared contextual row scene is recognized');
check(contextualScene?.query.project_id, '130', 'the row identity materializes into declared scene query');
check(
  sceneNavigationMatchesUrl(
    contextualScene,
    'http://fixture.invalid/s/project.management?scene_key=project.management&project_id=130&entry_intent=project.dashboard.enter',
  ),
  true,
  'the resulting scene route carries every declared query identity',
);
check(
  sceneNavigationMatchesUrl(
    contextualScene,
    'http://fixture.invalid/s/project.management?scene_key=project.management&entry_intent=project.dashboard.enter',
  ),
  false,
  'a scene route without the selected project is not accepted',
);

const targets = { entry: {} };
applyReleasedNavigationTarget(targets, ['entry'], findReleasedNavigationTargetByMenuXmlid(
  nav,
  'smart_construction_core.menu_action_one',
  action,
));
check(targets.entry.route, '/a/200?menu_id=11', 'the released route is copied with entry identity');
check(targets.entry.menu_id, 11, 'the selected menu identity is copied');
check(targets.entry.entry_target_type, 'action', 'the runtime entry target type is preserved');

const negativePlan = negativePlanByCandidate([{
  row: {
    menu_xmlid: 'smart_construction_core.menu_sc_my_work',
    action_xmlid: 'smart_construction_core.action_sc_my_work',
    role_authority: JSON.stringify({ action_groups: ['base.group_user'] }),
  },
  behaviour: {
    negative_authority: 'not_applicable_internal_workspace',
    negative_authority_reason: 'No internal-user navigation denial is legitimate.',
  },
}], ['fixture_role_read'], new Map([
  ['fixture_role_read', {
    role: 'fixture_role_read',
    eligible: true,
    missing: false,
    roleXmlids: ['base.group_user'],
    releasedTargets: 4,
    company: 1,
  }],
]));
check(negativePlan.byCandidate.size, 0, 'an inapplicable internal workspace opens no fake denial candidate');
check(negativePlan.undecidable.length, 0, 'an explicitly inapplicable denial is not misreported as undecidable');
check(negativePlan.notApplicable[0].kind, 'not_applicable_internal_workspace',
  'the workspace data-boundary responsibility is preserved explicitly');

const scenes = loadDeclaredSceneEntries('config/frontend/role_surface_exposure_declarations_v1.json');
check(scenes.length, 1, 'the declared no-action delivery carrier is represented separately from action CSV rows');
check(scenes[0].menu_xmlid, 'smart_construction_core.menu_sc_workspace_home',
  'the no-action carrier retains its menu identity');
check(scenes[0].route, '/s/workspace.home', 'the no-action carrier retains its declared scene route');

const overlay = loadOverlay('scripts/verify/business_entry_matrix_overlay.json');
check(deniedRoleCandidatesFor(overlay, '').includes('fixture_role_project_a_member'), true,
  'the default fixture profile keeps its declared candidate identities');
check(deniedRoleCandidatesFor(overlay, 'daily').includes('demo_role_project_a_member'), true,
  'the daily profile resolves actual demo identities without changing the default profile');
check(deniedRoleCandidatesFor(overlay, 'daily').includes('fixture_role_project_a_member'), false,
  'the daily profile does not claim fixture identities that are absent from the demo tenant');

const sceneRow = scenes[0];
const runtimeScene = runtimeRoleSceneTarget({
  role_home_menu_xmlids: [sceneRow.menu_xmlid],
  landing_entry_target: { type: 'scene', scene_key: sceneRow.scene_key, route: sceneRow.route },
}, sceneRow);
check(runtimeScene.route, sceneRow.route, 'a declared runtime landing target supplies the executable scene route');
check(runtimeRoleSceneTarget({
  role_home_menu_xmlids: [sceneRow.menu_xmlid],
}, sceneRow), null, 'the local declaration cannot substitute for a missing runtime landing target');
check(runtimeRoleSceneTarget({
  role_home_menu_xmlids: [sceneRow.menu_xmlid],
  landing_entry_target: { scene_key: 'other.scene', route: '/s/other.scene' },
}, sceneRow), null, 'a mismatched runtime scene identity is refused');

check(recordedEntryStatus({ assertions: { collection: 'error' } }), 'collection_failed',
  'an assertion error cannot fold as checked');
check(recordedEntryStatus({ status: 'form-error', assertions: { collection: 'error' } }), 'form-error',
  'an explicit form failure keeps its non-success status');
check(recordedEntryStatus({ assertions: { detail: 'passed' } }), 'checked',
  'a successful entry still folds as checked');
check(matrixSucceeded({
  completeness: 'complete',
  problems: [],
  entries: [{ status: 'exception' }],
}), false, 'an unrecovered route exception makes the aggregate result fail');
check(matrixSucceeded({
  completeness: 'complete',
  problems: [],
  entries: [{ assertions: { detail: 'passed' } }],
}), true, 'a complete problem-free entry set succeeds');

const sceneOverlay = {
  defaults: { detail: true, expect_write: null },
  entries: {
    [sceneRow.menu_xmlid]: { presentation: 'workspace' },
  },
};
const changedSceneOverlay = {
  defaults: { detail: true, expect_write: null },
  entries: {
    [sceneRow.menu_xmlid]: { presentation: 'table' },
  },
};
const sceneFingerprint = (behaviour) => entryFingerprint({
  row: sceneRow,
  behaviour,
  environment: { login: 'reviewer' },
  surfaceInputs: { scope: 'whole_artifact', sha256: 'a'.repeat(64) },
  derived: { candidate: null },
  permissionContext: null,
  modelRevision: 'model',
  probeRevision: 'probe',
});
assert.notEqual(
  sceneFingerprint(sceneBehaviour(sceneOverlay, sceneRow.menu_xmlid)),
  sceneFingerprint(sceneBehaviour(changedSceneOverlay, sceneRow.menu_xmlid)),
  'a changed scene overlay assertion invalidates its unit',
);
cases += 1;

console.log(`[business_entry_matrix_runtime_route_test] PASS cases=${cases}`);
