import assert from 'node:assert/strict';
import {
  getSceneByKey,
  setSceneRegistryFromSceneReadyContract,
} from '../src/app/resolvers/sceneRegistry.ts';
import {
  resolveSceneActionTarget,
  resolveSceneHandlingEntryTarget,
} from '../src/app/sceneActionTarget.ts';

const sceneKey = 'entry.smart_construction_core.menu_sc_project_project';
setSceneRegistryFromSceneReadyContract({
  scenes: [{
    scene: { key: sceneKey, title: '项目台账' },
    page: {
      scene_key: sceneKey,
      title: '项目台账',
      route: `/s/${sceneKey}`,
      page_type: 'native_delegate',
      layout_mode: 'single_flow',
    },
    target: {
      route: `/s/${sceneKey}`,
      action_id: 506,
      menu_id: 379,
      model: 'project.project',
      view_mode: 'list,form',
      entry_intent: 'ui.contract',
    },
    permission_surface: {
      visible: true,
      allowed: true,
      reason_code: '',
      required_capabilities: [],
    },
    meta: {
      mode: 'scene_shell',
      content_kind: 'native_delegate',
      designed: false,
      target: {
        route: `/s/${sceneKey}`,
        action_id: 506,
        menu_id: 379,
        model: 'project.project',
        view_mode: 'list,form',
      },
    },
  }],
});

const scene = getSceneByKey(sceneKey);
assert.ok(scene);
assert.equal(scene.route, `/s/${sceneKey}`);
assert.equal(scene.content_kind, 'native_delegate');
assert.equal(scene.target.action_id, 506);
assert.equal(scene.target.menu_id, 379);
assert.equal(scene.target.model, 'project.project');
assert.equal(scene.target.route, `/s/${sceneKey}`);
assert.equal(scene.scene_ready?.permission_surface?.allowed, true);

const menuTree = [{
  id: 310,
  menu_id: 310,
  name: 'Hidden sibling menu',
  scene_key: sceneKey,
  meta: { action_id: 100, menu_id: 310, scene_key: sceneKey },
  children: [
    {
      id: 320,
      menu_id: 320,
      name: 'Child handling entry',
      action_xmlid: 'test.action_child',
      meta: { action_id: 200, menu_id: 320, action_xmlid: 'test.action_child' },
    },
    {
      id: 330,
      menu_id: 330,
      name: 'Descriptor-only handling entry',
      meta: { action_id: 300, menu_id: 330 },
    },
  ],
}];
const hints = { [sceneKey]: { actionId: 100, menuId: 310 } };
const context = {
  sceneKey,
  menuTree,
  sceneActionHints: hints,
  routeQuery: { action_id: '900', menu_id: '901' },
};

assert.deepEqual(
  resolveSceneHandlingEntryTarget({ action_id: 200, menu_id: 320 }, context),
  { actionId: 200, menuId: 320 },
  'a child action identity outranks the parent scene hint',
);
assert.deepEqual(
  resolveSceneHandlingEntryTarget({ action_xmlid: 'test.action_child' }, context),
  { actionId: 200, menuId: 320 },
  'a child action descriptor resolves to its own action instead of the parent hint',
);
assert.deepEqual(
  resolveSceneHandlingEntryTarget({}, {
    ...context,
    internalAction: { action_id: 400, menu_id: 340 },
  }),
  { actionId: 400, menuId: 340 },
  'an internal descriptor action outranks the parent scene hint',
);
assert.deepEqual(
  resolveSceneHandlingEntryTarget({}, context),
  { actionId: 100, menuId: 310 },
  'the parent scene hint remains the fallback when the child declares no identity',
);
assert.deepEqual(
  resolveSceneActionTarget({ action_id: 200, menu_id: 320 }, context),
  { actionId: 200, menuId: 320 },
  'the shared resolver gives explicit child identity priority over route context',
);

console.log('scene_shell_contract_test PASS native_delegate=1 entry_priority=5');
