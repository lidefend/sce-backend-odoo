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
  key: 'root', menu_id: 1, label: 'Root', sequence: 20, children: [{
    key: 'group', menu_id: 2, label: 'Group', children: [{
      key: 'leaf', menu_id: 3, label: 'Leaf', sequence: 7, icon: 'folder',
      meta: { action_id: 30 }, children: [],
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

assert.throws(
  () => createCanonicalNavigationModel(nav, { ...authority, primary_actions: [] }),
  (error) => error instanceof CanonicalNavigationError && error.code === 'CANONICAL_NAVIGATION_AUTHORITY_MISSING',
);

const disabledNav = structuredClone(nav);
const disabledLeaf = disabledNav[0].children?.[0]?.children?.[0] as NavNode & {
  availability_status?: string;
  disabled_reason?: string;
};
disabledLeaf.availability_status = 'disabled';
disabledLeaf.disabled_reason = 'Backend declared reason';
const disabled = canonicalNavigationNodeByMenuId(createCanonicalNavigationModel(disabledNav, authority).nodes, 3);
assert.equal(disabled?.state, 'disabled');
assert.equal(disabled?.disabledReason, 'Backend declared reason');

delete disabledLeaf.disabled_reason;
assert.throws(
  () => createCanonicalNavigationModel(disabledNav, authority),
  (error) => error instanceof CanonicalNavigationError && error.code === 'CANONICAL_NAVIGATION_DISABLED_REASON_MISSING',
);

assert.throws(
  () => createCanonicalNavigationModel([{ key: 'empty', menu_id: 9, label: 'Empty' }], authority),
  (error) => error instanceof CanonicalNavigationError && error.code === 'CANONICAL_NAVIGATION_EMPTY_NODE',
);

console.log('[canonical_navigation_model_test] PASS cases=6');
