import assert from 'node:assert/strict';
import type { NavNode } from '@sc/schema';
import {
  CanonicalNavigationError,
  canonicalNavigationNodeByMenuId,
  createCanonicalNavigationModel,
} from '../src/app/canonicalNavigation.ts';
import type { RouteAuthorityContract } from '../src/app/routeAuthority.ts';

const authority: RouteAuthorityContract = {
  contract_version: '2.0.0',
  schema_version: '2.0.0',
  source: 'test',
  principal_scope: { user_id: 50, company_id: 1, role_code: 'admin' },
  primary_actions: [{
    action_xmlid: 'test.action_leaf', route_kind: 'PRIMARY_NAV', menu_id: 3,
    menu_xmlid: 'test.menu_leaf', action_id: 30, name: 'Leaf', model: 'x.test',
    view_modes: ['list'], domain: '', context: '', route: '/a/30?menu_id=3',
    allowed_operation: 'read', required_capability: '', context_requirements: {}, source: 'route_authority',
  }],
  role_home_actions: [], contextual_actions: [], admin_actions: [], denied_actions: [], menu_containers: [],
};

const nav: NavNode[] = [{
  key: 'root', menu_id: 1, label: 'Root', sequence: 20,
  canonical_navigation: {
    schema_version: '1.0', key: 'root', menu_id: 1, action_id: null, parent_chain: [], label: 'Root',
    icon: null, route: null, authority: { state: 'container', source: 'system.init.navigation.nav', key: 'container:1' },
    state: 'container', disabled_reason: null, order: 0,
  },
  children: [{
    key: 'group', menu_id: 2, label: 'Group',
    canonical_navigation: {
      schema_version: '1.0', key: 'group', menu_id: 2, action_id: null,
      parent_chain: [{ key: 'root', menu_id: 1, label: 'Root' }], label: 'Group', icon: null, route: null,
      authority: { state: 'container', source: 'system.init.navigation.nav', key: 'container:2' },
      state: 'container', disabled_reason: null, order: 0,
    },
    children: [{
      key: 'leaf', menu_id: 3, label: 'Leaf', sequence: 7, icon: 'folder',
      meta: { action_id: 30 },
      canonical_navigation: {
        schema_version: '1.0', key: 'leaf', menu_id: 3, action_id: 30,
        parent_chain: [
          { key: 'root', menu_id: 1, label: 'Root' },
          { key: 'group', menu_id: 2, label: 'Group' },
        ],
        label: 'Leaf', icon: 'folder', route: '/a/30?menu_id=3',
        authority: { state: 'allowed', source: 'route_authority', key: 'PRIMARY_NAV:test.menu_leaf:test.action_leaf' },
        state: 'enabled', disabled_reason: null, order: 0,
      },
      children: [],
    }],
  }],
}];

const model = createCanonicalNavigationModel(nav, authority);
assert.equal(model.schemaVersion, '1.0');
assert.deepEqual(model.principal, { userId: 50, companyId: 1, roleCode: 'admin' });
const leaf = canonicalNavigationNodeByMenuId(model.nodes, 3);
assert.ok(leaf);
assert.equal(leaf.state, 'enabled');
assert.equal(leaf.route, '/a/30?menu_id=3');
assert.equal(leaf.authority.key, 'PRIMARY_NAV:test.menu_leaf:test.action_leaf');
assert.deepEqual(leaf.parentChain, [
  { key: 'root', menuId: 1, label: 'Root' },
  { key: 'group', menuId: 2, label: 'Group' },
]);

const syntheticRoot = structuredClone(nav);
syntheticRoot[0].menu_id = undefined;
syntheticRoot[0].key = 'root:synthetic';
if (!syntheticRoot[0].canonical_navigation) throw new Error('test carrier missing');
syntheticRoot[0].canonical_navigation.key = 'root:synthetic';
syntheticRoot[0].canonical_navigation.menu_id = null;
syntheticRoot[0].canonical_navigation.authority.key = 'container:root:synthetic';
const syntheticGroup = syntheticRoot[0].children?.[0];
if (!syntheticGroup?.canonical_navigation) throw new Error('test group carrier missing');
syntheticGroup.canonical_navigation.parent_chain[0] = { key: 'root:synthetic', menu_id: null, label: 'Root' };
const syntheticLeaf = syntheticGroup.children?.[0];
if (!syntheticLeaf?.canonical_navigation) throw new Error('test leaf carrier missing');
syntheticLeaf.canonical_navigation.parent_chain[0] = { key: 'root:synthetic', menu_id: null, label: 'Root' };
assert.equal(createCanonicalNavigationModel(syntheticRoot, authority).nodes[0].menuId, null);

const configuredSyntheticGroup = structuredClone(nav);
const configuredGroup = configuredSyntheticGroup[0].children?.[0] as NavNode & {
  synthetic?: boolean;
  meta?: NavNode['meta'] & { config_menu_id?: number };
};
if (!configuredGroup?.canonical_navigation) throw new Error('test configured synthetic group carrier missing');
configuredGroup.menu_id = 883881237;
configuredGroup.synthetic = true;
configuredGroup.meta = { ...(configuredGroup.meta || {}), synthetic: true, config_menu_id: 2 };
assert.equal(createCanonicalNavigationModel(configuredSyntheticGroup, authority).nodes[0].children[0].menuId, 2);

assert.throws(
  () => createCanonicalNavigationModel(nav, { ...authority, primary_actions: [] }),
  (error) => error instanceof CanonicalNavigationError && error.code === 'CANONICAL_NAVIGATION_AUTHORITY_MISSING',
);

const disabledNav = structuredClone(nav);
const disabledLeaf = disabledNav[0].children?.[0]?.children?.[0] as NavNode & {
  availability_status?: string;
  disabled_reason?: string;
};
if (!disabledLeaf.canonical_navigation) throw new Error('test disabled carrier missing');
disabledLeaf.canonical_navigation.state = 'disabled';
disabledLeaf.canonical_navigation.disabled_reason = 'Backend declared reason';
const disabled = canonicalNavigationNodeByMenuId(createCanonicalNavigationModel(disabledNav, authority).nodes, 3);
assert.equal(disabled?.state, 'disabled');
assert.equal(disabled?.disabledReason, 'Backend declared reason');

disabledLeaf.canonical_navigation.disabled_reason = null;
assert.throws(
  () => createCanonicalNavigationModel(disabledNav, authority),
  (error) => error instanceof CanonicalNavigationError && error.code === 'CANONICAL_NAVIGATION_DISABLED_REASON_MISSING',
);

assert.throws(
  () => createCanonicalNavigationModel([{
    key: 'empty', menu_id: 9, label: 'Empty',
    canonical_navigation: {
      schema_version: '1.0', key: 'empty', menu_id: 9, action_id: null, parent_chain: [], label: 'Empty',
      icon: null, route: null, authority: { state: 'container', source: 'system.init.navigation.nav', key: 'container:9' },
      state: 'container', disabled_reason: null, order: 0,
    },
  }], authority),
  (error) => error instanceof CanonicalNavigationError && error.code === 'CANONICAL_NAVIGATION_EMPTY_NODE',
);

const duplicateNav = structuredClone(nav);
const duplicateLeaf = structuredClone(duplicateNav[0].children?.[0]?.children?.[0]);
if (!duplicateLeaf) throw new Error('test duplicate leaf missing');
duplicateNav[0].children?.[0]?.children?.push(duplicateLeaf);
assert.throws(
  () => createCanonicalNavigationModel(duplicateNav, authority),
  (error) => error instanceof CanonicalNavigationError && error.code === 'CANONICAL_NAVIGATION_IDENTITY_DUPLICATED',
);

// Server-promoted menu containers (route_authority.menu_containers) are
// enabled, route-bearing nodes without their own action (PR #399 semantics).
const promotedAuthority: RouteAuthorityContract = {
  ...structuredClone(authority),
  menu_containers: [{
    action_xmlid: '', route_kind: 'PRIMARY_NAV', menu_id: 2,
    menu_xmlid: 'test.menu_group', action_id: 0, name: 'Group', model: '',
    view_modes: [], domain: '', context: '', route: '/m/2',
    allowed_operation: 'navigate', required_capability: 'menu_container_visible',
    context_requirements: {}, source: 'role_surface.menu_xmlids',
  }],
};
const promotedNav = structuredClone(nav);
const promotedGroup = promotedNav[0].children?.[0];
if (!promotedGroup?.canonical_navigation) throw new Error('test promoted carrier missing');
promotedGroup.canonical_navigation.state = 'enabled';
promotedGroup.canonical_navigation.route = '/m/2';
promotedGroup.canonical_navigation.authority = {
  state: 'allowed', source: 'role_surface.menu_xmlids', key: 'PRIMARY_NAV:test.menu_group:container',
};
const promotedModel = createCanonicalNavigationModel(promotedNav, promotedAuthority);
const promotedNode = canonicalNavigationNodeByMenuId(promotedModel.nodes, 2);
assert.ok(promotedNode);
assert.equal(promotedNode.state, 'enabled');
assert.equal(promotedNode.route, '/m/2');
assert.equal(promotedNode.authority.state, 'allowed');
assert.equal(promotedNode.authority.key, 'PRIMARY_NAV:test.menu_group:container');
assert.equal(promotedNode.actionId, null);

// A childless directory menu stays valid once it carries a container route.
const childlessPromoted = structuredClone(promotedNav);
const childlessGroup = childlessPromoted[0].children?.[0];
if (!childlessGroup) throw new Error('test childless group missing');
childlessGroup.children = [];
const childlessModel = createCanonicalNavigationModel(childlessPromoted, promotedAuthority);
assert.equal(canonicalNavigationNodeByMenuId(childlessModel.nodes, 2)?.children.length, 0);

// The guard must still reject a stale carrier that ignores the promotion.
const stalePromoted = structuredClone(promotedNav);
const staleGroup = stalePromoted[0].children?.[0];
if (!staleGroup?.canonical_navigation) throw new Error('test stale carrier missing');
staleGroup.canonical_navigation.state = 'container';
staleGroup.canonical_navigation.route = null;
staleGroup.canonical_navigation.authority = {
  state: 'container', source: 'system.init.navigation.nav', key: 'container:2',
};
assert.throws(
  () => createCanonicalNavigationModel(stalePromoted, promotedAuthority),
  (error) => error instanceof CanonicalNavigationError && error.code === 'CANONICAL_NAVIGATION_STATE_MISMATCH',
);

console.log('[canonical_navigation_model_test] PASS cases=12');
