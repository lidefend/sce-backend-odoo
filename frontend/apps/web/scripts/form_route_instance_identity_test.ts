import assert from 'node:assert/strict';
import {
  formRouteInstanceOwnsRoute,
  normalizeFormRouteOwnerIdentity,
} from '../src/pages/contractForm/formRouteInstanceIdentity.ts';

const createOwner = normalizeFormRouteOwnerIdentity({
  routeName: 'model-form', model: 'project.project', recordId: 'new',
  activityPageId: 'ap_project_first', actionId: 722, menuId: 378,
});
assert.equal(createOwner, 'new:project.project:page:ap_project_first');
assert.equal(formRouteInstanceOwnsRoute('', createOwner), true);
assert.equal(formRouteInstanceOwnsRoute(createOwner, createOwner), true);
assert.equal(formRouteInstanceOwnsRoute(createOwner, 'new:project.project:page:ap_project_second'), false);
assert.equal(formRouteInstanceOwnsRoute(createOwner, 'record:payment.request:167'), false);
assert.equal(
  normalizeFormRouteOwnerIdentity({ routeName: 'record', model: 'project.project', recordId: 2 }),
  'record:project.project:2',
);
assert.equal(
  normalizeFormRouteOwnerIdentity({
    routeName: 'model-form', model: 'project.project', recordId: 'new', actionId: 722, menuId: 378, viewId: 91,
  }),
  'new:project.project:action:722:menu:378:view:91',
);

console.log('[form_route_instance_identity_test] PASS cases=7');
