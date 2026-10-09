import assert from 'node:assert/strict';
import {
  findRouteAuthority,
  normalizeRouteAuthorityContract,
  routeAuthorityContextAllowed,
  routeAuthorityForPrincipal,
} from '../src/app/routeAuthority';

const raw = {
  contract_version: '2.0.0',
  schema_version: '2.0.0',
  source: 'test',
  principal_scope: { user_id: 7, company_id: 3, role_code: 'pm' },
  primary_actions: [],
  role_home_actions: [],
  contextual_actions: [{
    action_xmlid: 'x.contract_execution',
    route_kind: 'CONTEXTUAL_ROUTE',
    menu_id: 0,
    action_id: 41,
    model: 'x.execution',
    allowed_operation: 'read',
    required_capability: 'contract_read',
    context_requirements: {
      required_query: ['company_id', 'project_id', 'contract_id'],
      company_query: 'company_id',
      project_query: 'project_id',
      record_query: 'contract_id',
    },
  }],
  admin_actions: [{
    action_xmlid: 'x.user_management',
    route_kind: 'ADMIN_ROUTE',
    menu_id: 0,
    action_id: 51,
    model: 'res.users',
    allowed_operation: 'read',
    required_capability: 'business_config_admin',
    context_requirements: {},
  }],
  denied_actions: [],
  menu_containers: [],
};

const contract = normalizeRouteAuthorityContract(raw);
assert.ok(contract);
assert.equal(normalizeRouteAuthorityContract({ ...raw, contract_version: 'route_authority.v1' }), null);
assert.equal(normalizeRouteAuthorityContract({ ...raw, schema_version: '1.0.0' }), null);
const contextual = contract.contextual_actions[0];
assert.equal(routeAuthorityContextAllowed(contextual, {}, { companyId: 3, projectId: 9 }), false);
assert.equal(routeAuthorityContextAllowed(
  contextual,
  { company_id: '3', project_id: '9', contract_id: '12' },
  { companyId: 3, projectId: 9 },
), true);
assert.equal(routeAuthorityContextAllowed(
  contextual,
  { company_id: '4', project_id: '9', contract_id: '12' },
  { companyId: 3, projectId: 9 },
), false);
assert.equal(findRouteAuthority(contract, {
  actionId: 41,
  menuId: 0,
  query: { company_id: '3', project_id: '9', contract_id: '12' },
  companyId: 3,
  projectId: 9,
})?.action_xmlid, 'x.contract_execution');
assert.equal(findRouteAuthority(contract, {
  actionId: 51,
  menuId: 0,
  query: {},
  companyId: 3,
  projectId: 9,
})?.route_kind, 'ADMIN_ROUTE');
assert.equal(findRouteAuthority(contract, {
  actionId: 999,
  menuId: 0,
  query: {},
}), null);

const discoveredContract = normalizeRouteAuthorityContract({
  ...raw,
  primary_actions: [{
    action_xmlid: 'x.project_ledger',
    route_kind: 'DISCOVERED_PRIMARY_NAV',
    menu_id: 379,
    action_id: 506,
    model: 'sc.project',
    allowed_operation: 'read',
    required_capability: 'model_read_acl',
    context_requirements: {},
  }],
});
assert.ok(discoveredContract);
assert.equal(discoveredContract.primary_actions.length, 1);
assert.equal(findRouteAuthority(discoveredContract, {
  actionId: 506,
  menuId: 379,
  query: { menu_id: '379', action_id: '506', view_mode: 'tree' },
})?.route_kind, 'DISCOVERED_PRIMARY_NAV');

const menuBoundActionWithoutActionXmlid = normalizeRouteAuthorityContract({
  ...raw,
  primary_actions: [{
    action_xmlid: '',
    menu_xmlid: 'smart_construction_core.menu_sc_salary_registration_legacy_tenant_fixture_formal',
    route_kind: 'DISCOVERED_PRIMARY_NAV',
    menu_id: 805,
    action_id: 862,
    model: 'sc.hr.payroll.document',
    allowed_operation: 'read',
    required_capability: 'menu_action_read',
    context_requirements: {},
  }],
});
assert.ok(menuBoundActionWithoutActionXmlid);
assert.equal(findRouteAuthority(menuBoundActionWithoutActionXmlid, {
  actionId: 862,
  menuId: 805,
  query: {},
})?.menu_xmlid, 'smart_construction_core.menu_sc_salary_registration_legacy_tenant_fixture_formal');

const shellOnly = {
  ...raw,
  principal_scope: { user_id: 8, company_id: 3, role_code: 'executive' },
  contextual_actions: [],
  admin_actions: [],
};
const shellOnlyContract = routeAuthorityForPrincipal(
  shellOnly,
  { userId: 8, companyId: 3, roleCode: 'executive' },
);
assert.ok(shellOnlyContract);
assert.equal(findRouteAuthority(shellOnlyContract, {
  actionId: 41,
  menuId: 0,
  query: {},
}), null);
assert.equal(routeAuthorityForPrincipal(
  shellOnly,
  { userId: 9, companyId: 3, roleCode: 'executive' },
), null);
assert.equal(routeAuthorityForPrincipal(
  shellOnly,
  { userId: 8, companyId: 4, roleCode: 'executive' },
), null);
assert.equal(routeAuthorityForPrincipal(
  shellOnly,
  { userId: 8, companyId: 3, roleCode: 'pm' },
), null);

console.log('[route-authority-guard] PASS');

// Dedicated configuration routes must retain the same authority gate on every entry.
import { resolveAuthorizedConfigurationRoute, resolveActionWebRoute } from '../src/services/actionRoutePolicy';
const configAuthority = { action_id: 737, menu_id: 431, model: 'ui.business.config.contract', context: { sc_web_route: '/admin/business-config', business_config_root_menu_xmlid: 'product.root' } };
for (const routeName of ['menu', 'action', 'model-form', 'record']) {
  const target = resolveAuthorizedConfigurationRoute({ routeName, routeModel: configAuthority.model, authority: configAuthority, authorized: true, query: { activity_page_id: 'old-instance' } });
  assert.equal(target?.path, '/admin/business-config');
  assert.equal(target?.query.action_id, '737');
  assert.equal(target?.query.root_menu_xmlid, 'product.root');
  assert.equal(target?.query.activity_page_id, undefined);
}
assert.equal(resolveAuthorizedConfigurationRoute({ routeName: 'action', authority: configAuthority, authorized: false, query: {} }), null);
assert.equal(resolveAuthorizedConfigurationRoute({ routeName: 'action', authority: null, authorized: true, query: {} }), null);
assert.equal(resolveAuthorizedConfigurationRoute({ routeName: 'business-config', authority: configAuthority, authorized: true, query: {} }), null, 'no redirect loop');
assert.equal(resolveAuthorizedConfigurationRoute({ routeName: 'model-form', routeModel: 'sc.document.admin.document', authority: configAuthority, authorized: true, query: { config_mode: 'form_field_configuration' } }), null);
assert.equal(resolveAuthorizedConfigurationRoute({ routeName: 'model-form', routeModel: 'sc.document.admin.document', authority: { action_id: 666, model: 'sc.document.admin.document' }, authorized: true, query: { config_mode: 'form_field_configuration' } }), null, 'business form settings remain embedded');
assert.equal(resolveActionWebRoute({ ...configAuthority, context: "{'sc_web_route': '/admin/business-config'}" }), '/admin/business-config');
console.log('[configuration_entry_routing] PASS cases=10');

import { buildLowCodeReturnQuery } from '../src/pages/contractForm/formConfigHelpers';
const configReturn = buildLowCodeReturnQuery({ routeQuery: { menu_id: '356', config_host_menu_id: '431', view_id: '1703' }, modelName: 'test.document', actionId: 666, openPagesFlag: 'open_pages' });
assert.equal(configReturn.menu_id, '431');
assert.equal(configReturn.action_id, '666');
assert.equal(configReturn.view_id, '1703');
assert.equal(buildLowCodeReturnQuery({ routeQuery: { menu_id: '356' }, modelName: 'test.document', actionId: 666, openPagesFlag: 'open_pages' }).menu_id, '356');
console.log('[route_authority_guard_test] host/target return cases=2 PASS');

import { isRecordWorkItemNavigation } from '../src/services/actionRoutePolicy';
const reviewParams = { model: 'sc.payment.execution', id: '201' };
const reviewQuery = { work_item_source: 'tier.review', work_item_id: '505' };
assert.equal(isRecordWorkItemNavigation('record', reviewParams, reviewQuery), true);
assert.equal(isRecordWorkItemNavigation('model-form', reviewParams, reviewQuery), true);
assert.equal(isRecordWorkItemNavigation('action', reviewParams, reviewQuery), false);
for (const id of ['new', '0', '-1', '1.5', ''])
  assert.equal(isRecordWorkItemNavigation('record', { ...reviewParams, id }, reviewQuery), false);
assert.equal(isRecordWorkItemNavigation('record', reviewParams, {}), false);
assert.equal(isRecordWorkItemNavigation('record', reviewParams, { ...reviewQuery, work_item_source: 'anything' }), false);
assert.equal(isRecordWorkItemNavigation('record', reviewParams, { ...reviewQuery, work_item_id: '0' }), false);
assert.equal(isRecordWorkItemNavigation('record', { ...reviewParams, model: '' }, reviewQuery), false);
console.log('[work_item_empty_menu_shell] PASS cases=12 authorization=backend');


import { isAuthorizedSceneNavigation } from '../src/services/actionRoutePolicy';
const sceneGrant = { ...contract.admin_actions[0], scene_key: 'custom.scene', route: '/s/custom.scene' };
const sceneAuthority = { ...contract, admin_actions: [sceneGrant] };
const sceneInput = { routeName: 'scene', sceneKey: 'custom.scene', authority: sceneAuthority, query: {}, companyId: 3 };
assert.equal(isAuthorizedSceneNavigation(sceneInput), true);
assert.equal(isAuthorizedSceneNavigation({ ...sceneInput, authority: null }), false);
assert.equal(isAuthorizedSceneNavigation({ ...sceneInput, sceneKey: 'unknown.scene' }), false);
assert.equal(isAuthorizedSceneNavigation({ ...sceneInput, routeName: 'action' }), false);
assert.equal(isAuthorizedSceneNavigation({ ...sceneInput, sceneKey: ['custom.scene'] }), false);
assert.equal(isAuthorizedSceneNavigation({ ...sceneInput, query: { action_id: '999' } }), false);
assert.equal(isAuthorizedSceneNavigation({ ...sceneInput, query: { menu_id: '999' } }), false);
assert.equal(isAuthorizedSceneNavigation({ ...sceneInput, authority: { ...sceneAuthority, admin_actions: [], denied_actions: [sceneGrant] } }), false);
assert.equal(isAuthorizedSceneNavigation({ ...sceneInput, authority: { ...sceneAuthority, admin_actions: [{ ...sceneGrant, allowed_operation: '' }] } }), false);
assert.equal(isAuthorizedSceneNavigation({ ...sceneInput, authority: { ...sceneAuthority, admin_actions: [{ ...sceneGrant, scene_key: 'other.scene' }] } }), false);
const scopedScene = { ...sceneGrant, context_requirements: { required_query: ['company_id'], company_query: 'company_id' } };
const scopedInput = { ...sceneInput, authority: { ...sceneAuthority, admin_actions: [scopedScene] } };
assert.equal(isAuthorizedSceneNavigation(scopedInput), false);
assert.equal(isAuthorizedSceneNavigation({ ...scopedInput, query: { company_id: '4' } }), false);
assert.equal(isAuthorizedSceneNavigation({ ...scopedInput, query: { company_id: '3' } }), false);
assert.equal(isAuthorizedSceneNavigation({ ...sceneInput, authority: { ...sceneAuthority, admin_actions: [{ ...sceneGrant, scene_key: undefined, route: '', entry_target: { scene_key: 'custom.scene' } }] } }), true);
assert.equal(isAuthorizedSceneNavigation({ ...sceneInput, authority: { ...sceneAuthority, admin_actions: [{ ...sceneGrant, scene_key: undefined }] } }), true);
assert.equal(isAuthorizedSceneNavigation({ ...sceneInput, authority: { ...sceneAuthority, admin_actions: [{ ...sceneGrant, context_requirements: { record_query: 'record_id' } }] }, query: { record_id: '999' } }), false);
console.log('[scene_empty_menu_shell] PASS cases=16 authority=final_route_contract');

// Login-return targets must be consumed against the *current* released route
// authority, exactly like the router guard. A replayed target that the guard
// would deny (retired/unified entry, mismatched menu binding, missing context)
// must be dropped so the caller falls back to the contract-declared landing,
// instead of landing the user on the access-denied page right after login.
import { authorityBoundTargetResolvable } from '../src/app/routeAuthority';
const landingScope = { companyId: 3, selectedRecordId: null };
assert.equal(authorityBoundTargetResolvable(contract, '/s/projects.list', landingScope), true, 'scene routes are not authority-bound');
assert.equal(authorityBoundTargetResolvable(contract, '/', landingScope), true, 'root is not authority-bound');
assert.equal(authorityBoundTargetResolvable(contract, '/f/sc.project/12', landingScope), true, 'model form without action/menu is not authority-bound');
assert.equal(authorityBoundTargetResolvable(contract, '/r/sc.project/12', landingScope), true, 'record routes keep the relation-read intent path');
assert.equal(authorityBoundTargetResolvable(contract, '/a/51?action_id=51', landingScope), true, 'admin route resolves in the surface');
assert.equal(authorityBoundTargetResolvable(contract, '/a/41?company_id=3&project_id=9&contract_id=12', landingScope), true, 'contextual route resolves with its declared context');
assert.equal(authorityBoundTargetResolvable(contract, '/a/41?company_id=3&project_id=9', landingScope), false, 'contextual route without its required record query is dropped');
assert.equal(authorityBoundTargetResolvable(contract, '/a/999', landingScope), false, 'unknown action target is dropped');
assert.equal(authorityBoundTargetResolvable(contract, '/a/1176?menu_id=969&action_id=1176', landingScope), false, 'retired unified-entry target is dropped');
assert.equal(authorityBoundTargetResolvable(discoveredContract, '/f/sc.project/12?action_id=506&menu_id=379', landingScope), true, 'menu-bound action-form target resolves');
assert.equal(authorityBoundTargetResolvable(discoveredContract, '/f/sc.project/12?action_id=506&menu_id=805', landingScope), false, 'mismatched menu binding is dropped');
assert.equal(authorityBoundTargetResolvable(null, '/a/51', landingScope), false, 'an absent contract cannot authorize an authority-bound target');
assert.equal(authorityBoundTargetResolvable(null, '/', landingScope), true, 'an absent contract still allows a non-authority-bound landing');
// A contract-declared scene entry carries no business action, so the backend
// publishes it in role_home_actions with action_id 0 and an explicit
// entry_target.  The normalizer must admit exactly that shape.
const declaredTargetContract = normalizeRouteAuthorityContract({
  ...raw,
  role_home_actions: [{
    route_kind: 'ROLE_HOME_ACTION',
    menu_id: 1004,
    menu_xmlid: 'smart_construction_core.menu_sc_workspace_home',
    action_id: 0,
    name: '角色首页',
    scene_key: 'workspace.home',
    route: '/s/workspace.home',
    entry_target: { type: 'scene', scene_key: 'workspace.home', route: '/s/workspace.home' },
    allowed_operation: 'read',
    required_capability: 'menu_container_visible',
    context_requirements: {},
    source: 'nav.declared_entry',
  }],
});
assert.ok(declaredTargetContract);
assert.equal(declaredTargetContract.role_home_actions.length, 1);
assert.equal(declaredTargetContract.role_home_actions[0].menu_id, 1004);
assert.equal(declaredTargetContract.role_home_actions[0].action_id, 0);
assert.equal(declaredTargetContract.role_home_actions[0].scene_key, 'workspace.home');
assert.equal(declaredTargetContract.role_home_actions[0].route, '/s/workspace.home');

// An actionless role-home row without any declared target stays rejected, so the
// admission cannot be widened into "any menu id is authorized".
const bareRoleHomeContract = normalizeRouteAuthorityContract({
  ...raw,
  role_home_actions: [{ route_kind: 'ROLE_HOME_ACTION', menu_id: 1004, action_id: 0, route: '/x' }],
});
assert.ok(bareRoleHomeContract);
assert.equal(bareRoleHomeContract.role_home_actions.length, 0);

console.log('[login_return_authority] PASS cases=16 source=contract_route_authority');
