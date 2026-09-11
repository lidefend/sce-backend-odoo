import assert from 'node:assert/strict';
import type { CanonicalFormNode } from '../src/app/presentation/canonicalFormRenderModel';
import {
  activeSectionKeyAtAnchor,
  nextBusinessActionLabel,
  nativeSectionNavigationRole,
  sectionScrollDelta,
  workspaceSectionNavigationItems,
  workspaceSurfaceNavigationItems,
} from '../src/pages/contractForm/nativeSectionNavigation';
import {
  collectNativeBusinessSections,
  nativeBusinessSectionIdentity,
} from '../src/pages/contractForm/nativeBusinessSection';

assert.deepEqual(nativeBusinessSectionIdentity({
  type: 'group', string: '基本信息', attributes: { 'data-sc-anchor': 'project-basic' },
}), { anchor: 'project-basic', label: '基本信息' });
assert.equal(nativeBusinessSectionIdentity({
  type: 'group', string: '普通布局组', attributes: {},
}), null, 'a title without explicit section identity remains hidden layout metadata');
assert.equal(nativeBusinessSectionIdentity({
  type: 'group', string: '隐藏章节', visible: false, attributes: { 'data-sc-anchor': 'hidden' },
}), null, 'hidden sections remain hidden even when explicitly anchored');
assert.equal(nativeBusinessSectionIdentity({
  type: 'page', string: '业务页签', attributes: { 'data-sc-anchor': 'tab' },
}), null, 'tabs retain their own navigation and do not become group headings');

const hiddenAncestorSections = collectNativeBusinessSections([node({
  nodeId: 'hidden.parent', kind: 'container', visible: false, children: [node({
    nodeId: 'hidden.child.anchor', title: '隐藏父级中的章节',
    attributes: { 'data-sc-anchor': 'hidden-child' },
  })],
})], { childrenOf: (item) => item.children, isVisible: (item) => item.visible });
assert.deepEqual(hiddenAncestorSections, [], 'a visible-looking anchor below a hidden ancestor cannot activate section mode');

const notebookOnlySections = collectNativeBusinessSections([node({
  nodeId: 'tabs.only', kind: 'notebook', children: [node({
    nodeId: 'tab.page', kind: 'page', children: [node({
      nodeId: 'tab.group.anchor', title: '页签内分区',
      attributes: { 'data-sc-anchor': 'tab-group' },
    })],
  })],
})], { childrenOf: (item) => item.children, isVisible: (item) => item.visible });
assert.deepEqual(notebookOnlySections, [], 'anchors owned by notebook content cannot activate page-level section mode');

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
    componentResolution: { componentKey: '', renderer: '', contractAdapter: '' },
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
  title: '隐藏业务章节', attributes: { 'data-sc-anchor': 'hidden-business-section' },
})]);
assert.deepEqual(hiddenSection, [], 'hidden sections must not create links');

const authoritativeSections = workspaceSectionNavigationItems([
  node({
    nodeId: 'sheet', kind: 'sheet', children: [
      node({
        nodeId: 'section.basic', title: '基本信息', semanticRole: 'context',
        attributes: { 'data-sc-anchor': 'project-basic' },
      }),
      node({
        nodeId: 'section.layout-only', title: '布局容器', semanticRole: 'context',
      }),
      node({
        nodeId: 'project.tabs', kind: 'notebook', children: [node({
          nodeId: 'tab.wbs', kind: 'page', title: 'WBS结构',
          attributes: { 'data-sc-anchor': 'wbs' },
        })],
      }),
    ],
    fields: [field({
      widgetId: 'labels', fieldType: 'many2many', semanticRole: 'relation', label: '标签',
    })],
  }),
]);
assert.deepEqual(
  authoritativeSections.map(({ label, sourceType, sourceIdentity }) => ({ label, sourceType, sourceIdentity })),
  [{ label: '基本信息', sourceType: 'node', sourceIdentity: 'section.basic' }],
  'explicit visible business sections replace inferred field and nested-tab navigation',
);

const unanchoredTitle = workspaceSectionNavigationItems([node({
  nodeId: 'unanchored.title', title: '不应自动显示', semanticRole: '',
})]);
assert.deepEqual(unanchoredTitle, [], 'an XML title alone must not opt a group into visible navigation');

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
    field({ widgetId: 'resolved.attachments', fieldType: 'many2many', semanticRole: 'relation', label: '其他附件', componentResolution: { componentKey: 'ProfessionalAttachmentCollection', renderer: '', contractAdapter: '' } }),
    field({ widgetId: 'descriptor.attachments', fieldType: 'many2many', semanticRole: 'relation', label: '原生附件', fieldDescriptor: { relation: 'ir.attachment' } }),
  ],
})]);
assert.deepEqual(relationSections.map(({ label, contentKind, sourceIdentity }) => ({ label, contentKind, sourceIdentity })), [
  { label: '合同明细', contentKind: 'relation-collection', sourceIdentity: 'lines.income' },
  { label: '结算明细', contentKind: 'relation-collection', sourceIdentity: 'lines.settlement' },
]);
assert.equal(new Set(relationSections.map((item) => item.selector)).size, 2, 'relation targets must remain distinct');

assert.deepEqual(workspaceSurfaceNavigationItems({ collaborationAvailable: true, auditAvailable: false }).map((item) => item.role), ['activity']);
assert.deepEqual(workspaceSurfaceNavigationItems({ collaborationAvailable: true, auditAvailable: true }).map((item) => item.role), ['activity', 'audit']);

const lowerPagePositions = [
  { key: 'basic', top: -900 },
  { key: 'related', top: -40 },
  { key: 'collaboration', top: 520 },
  { key: 'audit', top: 760 },
];
assert.equal(activeSectionKeyAtAnchor(lowerPagePositions, 120), 'related', 'being at the document bottom cannot make an unreached audit target active');
assert.equal(
  activeSectionKeyAtAnchor(lowerPagePositions, 120, { preferredKey: 'audit', visibleBottom: 900 }),
  'audit',
  'a just-activated target that is visible but cannot reach the anchor at scroll end must remain current after release',
);
assert.equal(
  activeSectionKeyAtAnchor(lowerPagePositions, 120, { preferredKey: 'audit', visibleBottom: 700 }),
  'related',
  'a just-activated target outside the visible scroll owner must not override anchor tracking',
);
assert.equal(activeSectionKeyAtAnchor(lowerPagePositions, 800), 'audit', 'the audit entry becomes current only after its own target reaches the navigation anchor');
assert.equal(sectionScrollDelta(132, 120), 12, 'a target below the active anchor must be advanced to the same anchor used for selection');
assert.equal(sectionScrollDelta(104, 120), -16, 'a target hidden above the active anchor must be moved below sticky surfaces');
assert.equal(sectionScrollDelta(120.5, 120), 0, 'sub-pixel rendering around the active anchor must not cause scroll churn');

console.log('[native_section_navigation_test] PASS authority=7 next_action=3 content_identity=9 active_tracking=7');
