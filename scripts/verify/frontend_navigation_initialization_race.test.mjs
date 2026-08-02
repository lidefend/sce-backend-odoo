#!/usr/bin/env node

import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createNavigationSelectionSnapshot } from '../../frontend/apps/web/src/app/navigationSelectionCore.js';

const authority = {
  contract_version: 'route_authority.v1',
  primary_actions: [],
  role_home_actions: [],
  contextual_actions: [],
  admin_actions: [{
    route_kind: 'ADMIN_ROUTE',
    menu_id: 438,
    menu_xmlid: 'smart_construction_core.menu_sc_runtime_user_management',
    action_id: 723,
    action_xmlid: 'smart_construction_core.action_sc_runtime_user_management',
    name: '公司内部人员维护',
  }],
};
const node = {
  menu_id: 438,
  label: '公司内部人员维护',
  meta: { action_id: 723, model: 'res.users', view_modes: ['tree', 'form'] },
};

const snapshot = createNavigationSelectionSnapshot(node, authority);
assert.ok(snapshot);
assert.equal(snapshot.menuId, 438);
assert.equal(snapshot.actionId, 723);
assert.equal(snapshot.targetKind, 'action');
assert.equal(snapshot.authorityKey, 'ADMIN_ROUTE:smart_construction_core.menu_sc_runtime_user_management:smart_construction_core.action_sc_runtime_user_management');
assert.equal(Object.isFrozen(snapshot), true);
assert.equal(Object.isFrozen(snapshot.meta), true);

node.meta.action_id = 506;
assert.equal(snapshot.actionId, 723, 'selection must not follow later menu mutation');
assert.equal(snapshot.meta.action_id, 723, 'selection metadata must remain immutable');

assert.equal(createNavigationSelectionSnapshot({ ...node, meta: { ...node.meta, action_id: 506 } }, authority), null);
assert.equal(createNavigationSelectionSnapshot(node, null), null);

const appShell = fs.readFileSync('frontend/apps/web/src/layouts/AppShell.vue', 'utf8');
assert.match(appShell, /:data-navigation-state="navigationReady \? 'ready' : initStatus === 'error' \? 'error' : 'loading'"/);
assert.match(appShell, /<PrimaryNavigation[\s\S]*v-if="navigationReady"/);
assert.match(appShell, /if \(!navigationReady\.value\) return;/);
assert.match(appShell, /createNavigationSelectionSnapshot\(node, session\.routeAuthority\)/);
assert.doesNotMatch(appShell, /node\.menu_id\s*=(?!=)/, 'menu click must not mutate the selected node');

const session = fs.readFileSync('frontend/apps/web/src/stores/session.ts', 'utf8');
assert.match(session, /this\.isReady = false;[\s\S]*this\.routeAuthority = null;[\s\S]*this\.menuTree = \[\];[\s\S]*this\.currentAction = null;/);
assert.match(session, /appInitEpoch === requestEpoch/);
assert.match(session, /this\.currentAction = null;[\s\S]*this\.scenes = \[\];[\s\S]*this\.defaultRoute = null;/);

const router = fs.readFileSync('frontend/apps/web/src/router/index.ts', 'utf8');
assert.doesNotMatch(router, /resolveExplicitSceneKeyFromMenuContext/);
assert.match(router, /if \(!session\.isReady \|\| !session\.routeAuthority\) return false;/);

console.log('[frontend_navigation_initialization_race.test] PASS immutable tuple fail-closed startup stale-session purge');
