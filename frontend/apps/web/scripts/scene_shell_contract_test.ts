import assert from 'node:assert/strict';
import {
  getSceneByKey,
  setSceneRegistryFromSceneReadyContract,
} from '../src/app/resolvers/sceneRegistry.ts';

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

console.log('scene_shell_contract_test PASS native_delegate=1');
