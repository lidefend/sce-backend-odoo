#!/usr/bin/env node

import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createNavigationSelectionSnapshot } from '../../frontend/apps/web/src/app/navigationSelectionCore.js';

const authority = {
  contract_version: '2.0.0',
  schema_version: '2.0.0',
  primary_actions: [],
  role_home_actions: [],
  contextual_actions: [],
  menu_containers: [],
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
  meta: {
    action_id: 723,
    model: 'res.users',
    view_modes: ['tree', 'form'],
    entry_target: {
      type: 'compatibility',
      route: '/a/723?menu_id=438',
      compatibility_refs: { menu_id: 438, action_id: 723, model: 'res.users' },
    },
  },
};

const snapshot = createNavigationSelectionSnapshot(node, authority);
assert.ok(snapshot);
assert.equal(snapshot.menuId, 438);
assert.equal(snapshot.actionId, 723);
assert.equal(snapshot.targetKind, 'entry_target');
assert.equal(snapshot.entryTarget.route, '/a/723?menu_id=438');
assert.equal(snapshot.authorityKey, 'ADMIN_ROUTE:smart_construction_core.menu_sc_runtime_user_management:smart_construction_core.action_sc_runtime_user_management');
assert.equal(Object.isFrozen(snapshot), true);
assert.equal(Object.isFrozen(snapshot.meta), true);

const reactiveNode = new Proxy(node, {});
const reactiveSnapshot = createNavigationSelectionSnapshot(reactiveNode, authority);
assert.ok(reactiveSnapshot, 'rendered reactive menu nodes must be snapshot-compatible');
assert.equal(reactiveSnapshot.menuId, 438);
assert.equal(reactiveSnapshot.actionId, 723);

const canonicalAuthority = structuredClone(authority);
canonicalAuthority.admin_actions[0].scene_key = 'people.directory';
canonicalAuthority.admin_actions[0].route = '/s/people.directory';
canonicalAuthority.admin_actions[0].entry_target = {
  type: 'scene',
  scene_key: 'people.directory',
  route: '/s/people.directory',
  compatibility_refs: { menu_id: 438, action_id: 723 },
};
const canonicalSnapshot = createNavigationSelectionSnapshot(node, canonicalAuthority);
assert.equal(canonicalSnapshot.targetKind, 'entry_target');
assert.equal(canonicalSnapshot.entryTarget.type, 'scene');
assert.equal(canonicalSnapshot.entryTarget.route, '/s/people.directory');

node.meta.action_id = 506;
assert.equal(snapshot.actionId, 723, 'selection must not follow later menu mutation');
assert.equal(snapshot.meta.action_id, 723, 'selection metadata must remain immutable');

assert.equal(createNavigationSelectionSnapshot({ ...node, meta: { ...node.meta, action_id: 506 } }, authority), null);
assert.equal(createNavigationSelectionSnapshot(node, null), null);

// Two menus sharing the same action_id must each bind to their own
// server-owned (menu_id, action_id) authority.  Matching action_id alone is a
// menu-identity cross-match and must fail closed.
const sharedActionAuthority = {
  contract_version: '2.0.0',
  schema_version: '2.0.0',
  primary_actions: [
    {
      route_kind: 'PRIMARY_NAV',
      menu_id: 382,
      menu_xmlid: 'smart_construction_core.menu_project_ledger',
      action_id: 590,
      action_xmlid: 'smart_construction_core.action_project_ledger',
      name: '项目台账',
    },
    {
      route_kind: 'PRIMARY_NAV',
      menu_id: 410,
      menu_xmlid: 'smart_construction_core.menu_project_other',
      action_id: 590,
      action_xmlid: 'smart_construction_core.action_project_ledger',
      name: '另一个菜单入口',
    },
  ],
  role_home_actions: [],
  contextual_actions: [],
  admin_actions: [],
};
const ledgerNode = (menuId, label) => ({
  menu_id: menuId,
  label,
  meta: {
    action_id: 590,
    model: 'project.project',
    view_modes: ['tree', 'form'],
    entry_target: {
      type: 'compatibility',
      route: `/a/590?menu_id=${menuId}`,
      compatibility_refs: { menu_id: menuId, action_id: 590, model: 'project.project' },
    },
  },
});

const ledgerSnapshot = createNavigationSelectionSnapshot(ledgerNode(382, '项目台账'), sharedActionAuthority);
assert.ok(ledgerSnapshot);
assert.equal(ledgerSnapshot.menuId, 382);
assert.equal(ledgerSnapshot.actionId, 590);
assert.equal(ledgerSnapshot.authorityKey, 'PRIMARY_NAV:smart_construction_core.menu_project_ledger:smart_construction_core.action_project_ledger');

const otherSnapshot = createNavigationSelectionSnapshot(ledgerNode(410, '另一个菜单入口'), sharedActionAuthority);
assert.ok(otherSnapshot);
assert.equal(otherSnapshot.menuId, 410);
assert.equal(otherSnapshot.actionId, 590);
assert.equal(otherSnapshot.authorityKey, 'PRIMARY_NAV:smart_construction_core.menu_project_other:smart_construction_core.action_project_ledger');

// A group menu resolves to its first actionable child; the snapshot must keep
// the clicked source menu separate from the resolved target and bind authority
// to the target (menu_id, action_id), never to the source container.
const groupNode = {
  menu_id: 100,
  label: '项目中心',
  children: [
    ledgerNode(382, '项目台账'),
  ],
};
const groupSnapshot = createNavigationSelectionSnapshot(groupNode, sharedActionAuthority);
assert.ok(groupSnapshot);
assert.equal(groupSnapshot.sourceMenuId, 100);
assert.equal(groupSnapshot.menuId, 382);
assert.equal(groupSnapshot.actionId, 590);
assert.equal(groupSnapshot.authorityKey, 'PRIMARY_NAV:smart_construction_core.menu_project_ledger:smart_construction_core.action_project_ledger');

// A menu must not reuse another menu's authority record just because they share
// an action_id; the exact (menu_id, action_id) pair must exist.
assert.equal(
  createNavigationSelectionSnapshot(
    ledgerNode(410, '另一个菜单入口'),
    { ...sharedActionAuthority, primary_actions: [sharedActionAuthority.primary_actions[0]] },
  ),
  null,
  'menu 410/action 590 must not reuse menu 382 authority',
);
assert.equal(
  createNavigationSelectionSnapshot(
    ledgerNode(382, '项目台账'),
    { ...sharedActionAuthority, primary_actions: [{ ...sharedActionAuthority.primary_actions[0], action_id: 999 }] },
  ),
  null,
  'wrong action pairing must fail closed',
);
assert.equal(
  createNavigationSelectionSnapshot(ledgerNode(999, '不存在的菜单'), sharedActionAuthority),
  null,
  'missing menu/action pair must fail closed',
);

const appShell = fs.readFileSync('frontend/apps/web/src/layouts/AppShell.vue', 'utf8');
assert.match(appShell, /:data-navigation-state="navigationReady \? 'ready' : initStatus === 'error' \? 'error' : 'loading'"/);
assert.match(appShell, /v-else-if="canonicalNavigationBroken"/);
assert.match(appShell, /v-else-if="canonicalNavigationEmpty"/);
assert.match(appShell, /<ProductSideNavigation\s+v-if="navigationReady && navigationNodes\.length"/, 'visible navigation must consume the canonical navigation model');
assert.doesNotMatch(appShell, /<ProductScenarioNavigation\b/, 'visible navigation must not consume the scenario classification component');
assert.match(appShell, /canonicalNavigationBroken = computed\(\(\) => navigationReady\.value && !session\.navigationModel\)/, 'canonical decode failure must drive the navigation error state');
assert.match(appShell, /canonicalNavigationEmpty = computed\(\(\) => \([\s\S]*?navigationNodes\.value\.length === 0[\s\S]*?\)\);/);
assert.doesNotMatch(appShell, /scenarioNavigationBroken|scenarioSurface/, 'scenario classification must not gate visible navigation');
assert.match(appShell, /if \(!navigationReady\.value\) return;/);
assert.match(appShell, /routeAuthorityContextAllowed\(selection\.authority,/);
assert.match(appShell, /createNavigationSelectionSnapshot\(node\.source, session\.routeAuthority\)/, 'canonical menu click must consume the immutable navigation snapshot');
assert.doesNotMatch(appShell, /findRouteAuthority\(session\.routeAuthority/, 'menu click must not re-read mutable route authority');
assert.doesNotMatch(appShell, /node\.menu_id\s*=(?!=)/, 'menu click must not mutate the selected node');

// Execute the current consumer's readiness expression and click handler with
// controlled dependencies. A source spelling match alone cannot prove that a
// loading/stale/unauthorized click is rejected before router navigation.
const readiness = appShell.match(/const navigationReady = computed\(\(\) => \(([\s\S]*?)\)\);/);
assert.ok(readiness, 'readiness must remain explicit and testable');
const ready = new Function('session', `return (${readiness[1]});`);
for (const [state, expected] of [
  [{ isReady: false, initStatus: 'loading', routeAuthority: authority }, false],
  [{ isReady: true, initStatus: 'loading', routeAuthority: authority }, false],
  [{ isReady: true, initStatus: 'error', routeAuthority: authority }, false],
  [{ isReady: true, initStatus: 'ready', routeAuthority: null }, false],
  [{ isReady: true, initStatus: 'ready', routeAuthority: authority }, true],
]) assert.equal(ready(state), expected);

const clickBody = appShell.match(/function handleCanonicalSelect\(node: CanonicalNavigationNode\) \{([\s\S]*?)\n\}/);
assert.ok(clickBody);
const makeClick = new Function('navigationReady', 'session', 'router', 'createNavigationSelectionSnapshot',
  'routeAuthorityContextAllowed', 'query', 'closeMobileSidebar', `return function(node) {${clickBody[1]}};`);
const selectionAuthority = {
  ...authority,
  admin_actions: [{ ...authority.admin_actions[0], route: '/a/723?menu_id=438' }],
};
const canonicalNode = {
  key: 'smart_construction_core.menu_sc_runtime_user_management',
  menuId: 438,
  actionId: 723,
  state: 'enabled',
  route: '/a/723?menu_id=438',
  source: {
    menu_id: 438,
    label: '公司内部人员维护',
    meta: { action_id: 723, entry_target: { type: 'compatibility', route: '/a/723?menu_id=438' } },
  },
};
for (const [isReady, routeAuthority, contextAllowed, expected] of [
  [false, selectionAuthority, true, []], [true, null, true, []],
  [true, selectionAuthority, false, []], [true, selectionAuthority, true, ['/a/723?menu_id=438']],
]) {
  const pushed = [];
  let closed = 0;
  const query = { value: 'search' };
  const selected = { ...canonicalNode };
  const click = makeClick({ value: isReady }, { routeAuthority, recordContext: {} },
    { resolve: () => ({ query: {} }), push: (route) => { pushed.push(route); return Promise.resolve(); } },
    createNavigationSelectionSnapshot,
    () => { selected.route = '/a/stale'; return contextAllowed; }, query, () => { closed += 1; });
  click(selected);
  assert.deepEqual(pushed, expected, 'canonical click must use the authorized immutable snapshot only');
  assert.equal(closed, expected.length);
  assert.equal(query.value, expected.length ? '' : 'search');
}

const session = fs.readFileSync('frontend/apps/web/src/stores/session.ts', 'utf8');
assert.match(session, /this\.isReady = false;[\s\S]*this\.routeAuthority = null;[\s\S]*this\.menuTree = \[\];[\s\S]*this\.currentAction = null;/);
assert.match(session, /appInitEpoch === requestEpoch/);
assert.match(session, /this\.currentAction = null;[\s\S]*this\.scenes = \[\];[\s\S]*this\.defaultRoute = null;/);
assert.match(session, /request_context: nextRequestContext/);
assert.match(session, /clear_request_context: \{[\s\S]*company_id: nextCompanyId \|\| undefined/);

const router = fs.readFileSync('frontend/apps/web/src/router/index.ts', 'utf8');
assert.doesNotMatch(router, /resolveExplicitSceneKeyFromMenuContext/);
assert.match(router, /if \(!session\.isReady \|\| !session\.routeAuthority\) return false;/);

const configWorkbenchAcceptance = fs.readFileSync('frontend/apps/web/scripts/config_workbench_operation_acceptance.mjs', 'utf8');
assert.match(configWorkbenchAcceptance, /waitForSelector\('\[data-navigation-state="ready"\]'/, 'browser journeys must not interrupt authoritative initialization after login');
assert.match(configWorkbenchAcceptance, /synchronizeRuntimeConfigSelection\(page\)/, 'browser journeys must use the action published by the selected runtime page');
assert.match(configWorkbenchAcceptance, /action_id=\$\{runtimeConfigActionId\}&menu_id=\$\{runtimeConfigMenuId\}/, 'form deep links must retain runtime action and menu authority');

console.log('[frontend_navigation_initialization_race.test] PASS immutable tuple fail-closed startup stale-session purge');
