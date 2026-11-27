import assert from 'node:assert/strict';
import {
  buildCanonicalSceneRouteTarget,
  normalizeEmbeddedSceneQuery,
  stripCanonicalSceneIdentityQuery,
} from '../src/app/routeQuery';
import {
  buildBusinessCategoryCreateNavQuery,
  pickContractNavQuery,
} from '../src/app/navigationContext';

const malformedActionQuery = normalizeEmbeddedSceneQuery({
  menu_id: '379&action_id=506&view_mode=tree',
});
assert.equal(malformedActionQuery.changed, true);
assert.deepEqual(malformedActionQuery.query, {
  menu_id: '379',
  action_id: '506',
  view_mode: 'tree',
});

const encodedMalformedActionQuery = normalizeEmbeddedSceneQuery({
  menu_id: '379%26action_id=506%26view_mode=tree',
});
assert.equal(encodedMalformedActionQuery.changed, true);
assert.deepEqual(encodedMalformedActionQuery.query, {
  menu_id: '379',
  action_id: '506',
  view_mode: 'tree',
});

const explicitValuesWin = normalizeEmbeddedSceneQuery({
  menu_id: '379&action_id=999&view_mode=tree',
  action_id: '506',
});
assert.deepEqual(explicitValuesWin.query, {
  menu_id: '379',
  action_id: '506',
  view_mode: 'tree',
});

const canonicalQuery = normalizeEmbeddedSceneQuery({
  menu_id: '379',
  action_id: '506',
  view_mode: 'tree',
});
assert.equal(canonicalQuery.changed, false);
assert.deepEqual(canonicalQuery.query, {
  menu_id: '379',
  action_id: '506',
  view_mode: 'tree',
});

const canonicalSceneRoute = buildCanonicalSceneRouteTarget('workspace.home', {
  scene: {
    label: 'Role home',
    target: { menu_id: 3, action_id: 4 },
  },
  query: {
    scene: 'workspace.home',
    scene_key: 'workspace.home',
    scene_label: 'Role home',
    search: 'risk',
  },
});
assert.deepEqual(canonicalSceneRoute, {
  path: '/s/workspace.home',
  query: {
    search: 'risk',
    menu_id: 3,
    action_id: 4,
  },
});
assert.deepEqual(stripCanonicalSceneIdentityQuery({
  scene_key: 'workspace.home',
  scene_label: 'Role home',
  menu_id: '3',
}), { menu_id: '3' });
assert.deepEqual(pickContractNavQuery({
  scene: 'workspace.home',
  scene_key: 'workspace.home',
  scene_label: 'Role home',
  menu_id: '3',
  action_id: '4',
  domain_raw: '[]',
  context_raw: '{}',
  return_url: '/s/projects.ledger',
}), {
  menu_id: '3',
  action_id: '4',
  domain_raw: '[]',
  context_raw: '{}',
  return_url: '/s/projects.ledger',
});
assert.deepEqual(buildBusinessCategoryCreateNavQuery({
  categoryCode: 'finance.payment.apply.pay',
  option: {
    label: 'Payment request',
    categoryId: 7,
    defaultValues: { project_id: 9 },
  },
}), {
  current_business_category_code: 'finance.payment.apply.pay',
  default_business_category_code: 'finance.payment.apply.pay',
  ctx_source: 'business_category_create_picker',
  default_business_category_id: '7',
  default_project_id: '9',
});

console.log('[route-query-normalization] PASS');
