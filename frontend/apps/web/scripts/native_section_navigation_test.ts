import assert from 'node:assert/strict';
import type { CanonicalFormNode } from '../src/app/presentation/canonicalFormRenderModel';
import {
  activeSectionKeyAtAnchor,
  governedFormStructureSectionNavigationItems,
  nextBusinessActionLabel,
  nativeSectionNavigationRole,
  relationshipCollectionNavigationItems,
  sectionRevealTargetsContain,
  sectionScrollDelta,
  shouldPreserveAuthoritativeBusinessSections,
  workspaceSectionNavigationItems,
  workspaceSurfaceNavigationItems,
} from '../src/pages/contractForm/nativeSectionNavigation';

assert.equal(sectionRevealTargetsContain('["field:line_ids:relation-collection"]', 'field:line_ids:relation-collection'), true);
assert.equal(sectionRevealTargetsContain('["field:line_ids:relation-collection-extra"]', 'field:line_ids:relation-collection'), false);
assert.equal(sectionRevealTargetsContain('not-json', 'field:line_ids:relation-collection'), false);
import {
  collectNativeBusinessSections,
  governedFormStructureSectionIdentity,
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

const governedProjection = node({
  nodeId: 'payment.contract-basis',
  title: '结算与合同依据',
  semanticSlot: 'configured_form',
  semanticGroup: 'configured_group_2',
  nativePresentation: {
    sourceAuthority: {
      kind: 'unified_page_contract_v2',
      runtime_carrier: 'form_structure_contract',
      no_business_fact_authority: true,
    },
  },
});
assert.deepEqual(governedFormStructureSectionIdentity(governedProjection), {
  anchor: 'form-structure:payment.contract-basis',
  label: '结算与合同依据',
});
assert.deepEqual(governedFormStructureSectionNavigationItems([governedProjection]).map((item) => ({
  key: item.key, label: item.label, selector: item.selector,
})), [{
  key: 'form-structure:payment.contract-basis',
  label: '结算与合同依据',
  selector: '[data-form-section-target="form-structure:payment.contract-basis"]',
}]);
assert.equal(governedFormStructureSectionIdentity(node({
  nodeId: 'plain.layout', title: '普通布局组', nativePresentation: {},
})), null, 'an ordinary titled group must not become a governed business section');
assert.equal(governedFormStructureSectionIdentity(node({
  nodeId: 'projected.contract-basis', title: '合同依据', nativePresentation: {},
  fields: [],
  children: [node({
    nodeId: 'projected.contract-basis.contract', kind: 'field', title: '', nativePresentation: {},
    fields: [field({ semanticSlot: 'handling', semanticGroup: 'contract-basis' })], children: [],
  })],
})), null, 'descendant field placement must not promote an internal layout group into a business section');
assert.equal(governedFormStructureSectionIdentity(node({
  nodeId: 'mixed.layout', title: '普通混合布局', nativePresentation: {}, fields: [],
  children: [
    node({ nodeId: 'mixed.a', kind: 'field', title: '', fields: [field({ semanticSlot: 'a', semanticGroup: 'a' })], children: [] }),
    node({ nodeId: 'mixed.b', kind: 'field', title: '', fields: [field({ semanticSlot: 'b', semanticGroup: 'b' })], children: [] }),
  ],
})), null, 'mixed semantic placements must not promote a layout container by title alone');

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
assert.equal(nativeSectionNavigationRole({
  attributes: { 'data-sc-navigation-role': 'subordinate' },
}), 'subordinate', 'released native views may explicitly keep an auxiliary section out of primary navigation');
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
    nodeId: 'node.default', kind: 'group', title: '', text: '', visible: true, semanticRole: '',
    fields: [field({})], children: [],
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
assert.deepEqual(workspaceSectionNavigationItems([
  node({
    nodeId: 'primary.section', title: '基本信息',
    attributes: { 'data-sc-anchor': 'basic' },
  }),
  node({
    nodeId: 'auxiliary.section', title: '系统追溯',
    attributes: { 'data-sc-anchor': 'trace', 'data-sc-navigation-role': 'subordinate' },
  }),
]).map((item) => item.label), ['基本信息']);
assert.deepEqual(workspaceSectionNavigationItems([node({
  fields: [field({ widgetId: 'context.only', semanticRole: 'context', label: '普通资料字段' })],
})]), [], 'a uniform field role is still not section identity');

const hiddenSection = workspaceSectionNavigationItems([node({
  nodeId: 'hidden.context', visible: false, semanticRole: 'context',
  title: '隐藏业务章节', attributes: { 'data-sc-anchor': 'hidden-business-section' },
})]);
assert.deepEqual(hiddenSection, [], 'hidden sections must not create links');

const emptyProfileSection = workspaceSectionNavigationItems([node({
  nodeId: 'profile.hidden.content', title: '仅只读可见',
  attributes: { 'data-sc-anchor': 'profile-hidden-content' },
  fields: [field({ widgetId: 'readonly.only', visible: false })],
})]);
assert.deepEqual(
  emptyProfileSection,
  [],
  'a visible container whose profile hides all presentable content must not leave a dead navigation link',
);

const partiallyVisibleProfileSection = workspaceSectionNavigationItems([node({
  nodeId: 'profile.partially.visible', title: '部分资料可见',
  attributes: { 'data-sc-anchor': 'profile-partially-visible' },
  fields: [
    field({ widgetId: 'restricted.fact', visible: false }),
    field({ widgetId: 'available.fact', visible: true }),
  ],
})]);
assert.deepEqual(
  partiallyVisibleProfileSection.map(({ label, sourceIdentity }) => ({ label, sourceIdentity })),
  [{ label: '部分资料可见', sourceIdentity: 'profile.partially.visible' }],
  'a section with at least one presentable field must remain reachable when sibling fields are hidden',
);

const collapsedContentSection = workspaceSectionNavigationItems([node({
  nodeId: 'section.collapsed.with.content', title: '默认折叠资料',
  attributes: {
    'data-sc-anchor': 'collapsed-with-content',
    'data-sc-collapsible': '1',
    'data-sc-collapsed-by-default': '1',
  },
  fields: [field({ widgetId: 'collapsed.available.fact', visible: true })],
})]);
assert.deepEqual(
  collapsedContentSection.map(({ label, sourceIdentity }) => ({ label, sourceIdentity })),
  [{ label: '默认折叠资料', sourceIdentity: 'section.collapsed.with.content' }],
  'default-collapsed presentation must not remove a section that still contains presentable content',
);

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
assert.equal(
  shouldPreserveAuthoritativeBusinessSections('task', [node({
    nodeId: 'section.task.authoritative', title: '合同范围',
    attributes: { 'data-sc-anchor': 'contract-scope' },
  })]),
  true,
  'task workflow semantics must not discard an explicitly anchored business section body',
);
assert.equal(
  shouldPreserveAuthoritativeBusinessSections('task', [node({
    nodeId: 'partial.sheet', kind: 'sheet', fields: [], children: [
      node({
        nodeId: 'partial.basic', title: '基本资料',
        fields: [field({ widgetId: 'partial.project', fieldCode: 'project_id' })],
      }),
      node({
        nodeId: 'partial.award', title: '中标事实确认',
        attributes: { 'data-sc-anchor': 'award-confirmation' },
        fields: [field({ widgetId: 'partial.award.amount', fieldCode: 'award_amount' })],
      }),
    ],
  })]),
  false,
  'one explicit section must not replace unanchored sibling business content',
);
assert.deepEqual(
  governedFormStructureSectionNavigationItems([node({
    nodeId: 'embedded.award', title: '中标事实确认',
    attributes: { 'data-sc-anchor': 'award-confirmation' },
  })]).map(({ label, sourceIdentity }) => ({ label, sourceIdentity })),
  [{ label: '中标事实确认', sourceIdentity: 'embedded.award' }],
  'an embedded native section keeps one shared body/navigation identity inside the task floorplan',
);
assert.equal(
  shouldPreserveAuthoritativeBusinessSections('task', [node({
    nodeId: 'section.task.layout-only', title: '普通布局容器', attributes: {},
  })]),
  false,
  'an unanchored task layout group must continue through the ordinary floorplan',
);
assert.equal(
  shouldPreserveAuthoritativeBusinessSections('workspace', [node({
    nodeId: 'section.workspace.authoritative', title: '基本资料',
    attributes: { 'data-sc-anchor': 'workspace-basic' },
  })]),
  false,
  'workspace presentation already consumes native section authority directly',
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
    field({ widgetId: 'lines.income', fieldCode: 'income_line_ids', fieldType: 'one2many', semanticRole: 'relation', label: '合同明细' }),
    field({ widgetId: 'lines.settlement', fieldCode: 'settlement_line_ids', fieldType: 'many2many', semanticRole: 'relation', label: '结算明细' }),
    field({ widgetId: 'attachments', fieldCode: 'attachment_ids', fieldType: 'many2many', semanticRole: 'relation', label: '附件', componentConfig: { widget: 'many2many_binary' } }),
    field({ widgetId: 'resolved.attachments', fieldCode: 'other_attachment_ids', fieldType: 'many2many', semanticRole: 'relation', label: '其他附件', componentResolution: { componentKey: 'ProfessionalAttachmentCollection', renderer: '', contractAdapter: '' } }),
    field({ widgetId: 'descriptor.attachments', fieldCode: 'native_attachment_ids', fieldType: 'many2many', semanticRole: 'relation', label: '原生附件', fieldDescriptor: { relation: 'ir.attachment' } }),
  ],
})]);
assert.deepEqual(relationSections.map(({ label, contentKind, sourceIdentity }) => ({ label, contentKind, sourceIdentity })), [
  { label: '合同明细', contentKind: 'relation-collection', sourceIdentity: 'lines.income' },
  { label: '结算明细', contentKind: 'relation-collection', sourceIdentity: 'lines.settlement' },
]);
assert.equal(new Set(relationSections.map((item) => item.selector)).size, 2, 'relation targets must remain distinct');

const repeatedRelationOccurrences = workspaceSectionNavigationItems([node({
  nodeId: 'section.repeated.relation',
  fields: [
    field({
      widgetId: 'purchase.tags', fieldCode: 'purchase_order_ids', fieldType: 'many2many',
      semanticRole: 'relation', label: '采购订单', componentConfig: { nativeWidget: 'many2many_tags' },
    }),
    field({
      widgetId: 'purchase.table', fieldCode: 'purchase_order_ids', fieldType: 'many2many',
      semanticRole: 'relation', label: '采购订单', fieldDescriptor: { subview: { tree: { columns: ['name'] } } },
    }),
  ],
})]);
assert.deepEqual(
  repeatedRelationOccurrences.map(({ label, sourceIdentity }) => ({ label, sourceIdentity })),
  [{ label: '采购订单', sourceIdentity: 'purchase.table' }],
  'tag and table occurrences of one field must yield one navigation target owned by the richer visible occurrence',
);
const repeatedFieldAcrossBusinessSections = relationshipCollectionNavigationItems([
  node({
    nodeId: 'section.procurement.source', title: '采购来源',
    attributes: { 'data-sc-anchor': 'procurement-source' },
    fields: [field({
      widgetId: 'purchase.source.table', fieldCode: 'purchase_order_ids', fieldType: 'many2many',
      semanticRole: 'relation', semanticSlot: 'source_trace', semanticGroup: 'purchase_orders',
      label: '来源采购订单',
    })],
  }),
  node({
    nodeId: 'section.procurement.audit', title: '采购追溯',
    attributes: { 'data-sc-anchor': 'procurement-audit' },
    fields: [field({
      widgetId: 'purchase.audit.table', fieldCode: 'purchase_order_ids', fieldType: 'many2many',
      semanticRole: 'relation', semanticSlot: 'source_trace', semanticGroup: 'purchase_orders',
      label: '追溯采购订单',
    })],
  }),
]);
assert.deepEqual(
  repeatedFieldAcrossBusinessSections.map(({ label, sourceIdentity }) => ({ label, sourceIdentity })),
  [
    { label: '来源采购订单', sourceIdentity: 'purchase.source.table' },
    { label: '追溯采购订单', sourceIdentity: 'purchase.audit.table' },
  ],
  'explicit business anchors must keep the same canonical field in two regions distinct even when both occurrences carry the same semantic slot/group',
);
const repeatedFieldAcrossUnanchoredSemanticRegions = relationshipCollectionNavigationItems([
  node({ nodeId: 'unrelated.leading.root', fields: [] }),
  node({
    nodeId: 'unanchored.semantic.wrapper', fields: [], children: [
      node({
        nodeId: 'semantic.procurement.source', semanticSlot: 'source_trace', semanticGroup: 'purchase_source',
        fields: [field({
          widgetId: 'semantic.purchase.source.table', fieldCode: 'purchase_order_ids', fieldType: 'many2many',
          semanticRole: 'relation', label: '语义来源采购订单',
        })],
      }),
      node({
        nodeId: 'semantic.procurement.audit', semanticSlot: 'source_trace', semanticGroup: 'purchase_audit',
        fields: [field({
          widgetId: 'semantic.purchase.audit.table', fieldCode: 'purchase_order_ids', fieldType: 'many2many',
          semanticRole: 'relation', label: '语义追溯采购订单',
        })],
      }),
    ],
  }),
]);
assert.deepEqual(
  repeatedFieldAcrossUnanchoredSemanticRegions.map(({ label, sourceIdentity }) => ({ label, sourceIdentity })),
  [
    { label: '语义来源采购订单', sourceIdentity: 'semantic.purchase.source.table' },
    { label: '语义追溯采购订单', sourceIdentity: 'semantic.purchase.audit.table' },
  ],
  'root-array iteration metadata must not leak into region inheritance or merge distinct unanchored semantic regions',
);
assert.deepEqual(
  workspaceSectionNavigationItems([node({
    nodeId: 'section.hidden.relation.occurrences',
    fields: [
      field({ widgetId: 'purchase.tags.hidden', fieldCode: 'purchase_order_ids', fieldType: 'many2many', visible: false }),
      field({ widgetId: 'purchase.table.hidden', fieldCode: 'purchase_order_ids', fieldType: 'many2many', visible: false }),
    ],
  })]),
  [],
  'a relation whose occurrences are all hidden must not produce a dead navigation target',
);

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

console.log('[native_section_navigation_test] PASS authority=7 next_action=3 content_identity=11 active_tracking=7');
