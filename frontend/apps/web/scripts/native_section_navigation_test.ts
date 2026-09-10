import assert from 'node:assert/strict';
import type { CanonicalFormNode } from '../src/app/presentation/canonicalFormRenderModel';
import {
  nextBusinessActionLabel,
  nativeSectionNavigationRole,
  workspaceSectionNavigationItems,
  workspaceSurfaceNavigationItems,
} from '../src/pages/contractForm/nativeSectionNavigation';

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
assert.equal(nextBusinessActionLabel({ label: '生成付款登记', enabled: true }, []), '生成付款登记');
assert.equal(nextBusinessActionLabel({ label: '不可办理', enabled: false }, [{ label: '补充资料', enabled: true }]), '补充资料');
assert.equal(nextBusinessActionLabel(null, [{ label: '不可办理', enabled: false }]), '');

function field(overrides: Record<string, unknown>) {
  return {
    widgetId: 'field.default', fieldCode: 'field_default', widgetType: '', label: '普通字段',
    visible: true, fieldType: 'char', semanticRole: '', componentKey: '', componentConfig: {}, fieldDescriptor: {},
    ...overrides,
  } as unknown as CanonicalFormNode['fields'][number];
}

function node(overrides: Record<string, unknown>): CanonicalFormNode {
  return {
    nodeId: 'node.default', kind: 'group', title: '', visible: true, semanticRole: '',
    fields: [], children: [],
    ...overrides,
  } as unknown as CanonicalFormNode;
}

const fieldOnlyRoles = workspaceSectionNavigationItems([node({
  fields: [
    field({ widgetId: 'project', fieldType: 'many2one', semanticRole: 'relation', label: '项目名称' }),
    field({ widgetId: 'creator', semanticRole: 'audit', label: '平台录入人' }),
  ],
})]);
assert.deepEqual(fieldOnlyRoles, [], 'field semantic roles must not create section links');
assert.deepEqual(workspaceSectionNavigationItems([node({
  fields: [field({ widgetId: 'context.only', semanticRole: 'context', label: '普通资料字段' })],
})]), [], 'a uniform field role is still not section identity');

const hiddenSection = workspaceSectionNavigationItems([node({
  nodeId: 'hidden.context', visible: false, semanticRole: 'context',
})]);
assert.deepEqual(hiddenSection, [], 'hidden sections must not create links');

const contextSection = workspaceSectionNavigationItems([node({
  nodeId: 'section.context', semanticRole: 'context', fields: [field({})],
})]);
assert.deepEqual(contextSection.map(({ label, role, sourceType, sourceIdentity }) => ({ label, role, sourceType, sourceIdentity })), [{
  label: '基本资料', role: 'context', sourceType: 'node', sourceIdentity: 'section.context',
}]);

const relationSections = workspaceSectionNavigationItems([node({
  nodeId: 'section.relations',
  fields: [
    field({ widgetId: 'lines.income', fieldType: 'one2many', semanticRole: 'relation', label: '合同明细' }),
    field({ widgetId: 'lines.settlement', fieldType: 'many2many', semanticRole: 'relation', label: '结算明细' }),
    field({ widgetId: 'attachments', fieldType: 'many2many', semanticRole: 'relation', label: '附件', componentConfig: { widget: 'many2many_binary' } }),
  ],
})]);
assert.deepEqual(relationSections.map(({ label, contentKind, sourceIdentity }) => ({ label, contentKind, sourceIdentity })), [
  { label: '合同明细', contentKind: 'relation-collection', sourceIdentity: 'lines.income' },
  { label: '结算明细', contentKind: 'relation-collection', sourceIdentity: 'lines.settlement' },
]);
assert.equal(new Set(relationSections.map((item) => item.selector)).size, 2, 'relation targets must remain distinct');

assert.deepEqual(workspaceSurfaceNavigationItems({ collaborationAvailable: true, auditAvailable: false }).map((item) => item.role), ['activity']);
assert.deepEqual(workspaceSurfaceNavigationItems({ collaborationAvailable: true, auditAvailable: true }).map((item) => item.role), ['activity', 'audit']);

console.log('[native_section_navigation_test] PASS authority=5 next_action=3 content_identity=6');
