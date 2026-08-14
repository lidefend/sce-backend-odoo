import assert from 'node:assert/strict';
import { nativeSectionNavigationRole } from '../src/pages/contractForm/nativeSectionNavigation';

assert.equal(nativeSectionNavigationRole({}), 'primary');
assert.equal(nativeSectionNavigationRole({ sourceAuthority: { kind: 'released_product_section' } }), 'primary');
assert.equal(nativeSectionNavigationRole({
  sourceAuthority: {
    kind: 'odoo_native_view_subordinate_structure',
    projection_only: true,
    no_business_fact_authority: true,
  },
}), 'subordinate');
assert.equal(nativeSectionNavigationRole({
  source_authority: {
    projectionOnly: true,
    noBusinessFactAuthority: true,
  },
}), 'subordinate');
assert.equal(nativeSectionNavigationRole({
  sourceAuthority: {
    projection_only: true,
    no_business_fact_authority: false,
  },
}), 'primary');

console.log('[native_section_navigation_test] PASS primary=3 subordinate=2');
