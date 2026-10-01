import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { resolveNativeSectionHeading } from '../src/pages/contractForm/nativeBusinessSection';
import {
  collectNativeVisibleFieldNames,
  collectNativeVisibleSectionTitles,
  filterVisibleNativeLayoutNodes,
  isLayoutOnlyGroupContainer,
  type NativeLayoutLikeNode,
} from '../src/pages/contractForm/nativeLayoutUtils';
import {
  FORM_ACTION_PLACEHOLDER_BODY_KINDS,
  classifyFormActionPlaceholderBody,
  formBodyOwnsStructure,
  resolveFormActionPlaceholderGate,
  type FormActionPlaceholderBodyKind,
} from '../src/pages/contractForm/formActionPlaceholderGate';
import {
  isDraftOperationAllowed,
  resolveDesignerDraftOwnership,
  resolveDesignerDraftPolicy,
} from './designer_draft_ownership.mjs';

type Node = NativeLayoutLikeNode;

const field = (name: string, visible = true): Node => ({ type: 'field', name, visible });
const group = (children: Node[], visible = true, extra: Record<string, unknown> = {}): Node => ({ type: 'group', ...extra, visible, children });
const page = (children: Node[]): Node => ({ type: 'page', string: '明细', children });
const notebook = (children: Node[]): Node => ({ type: 'notebook', children });

const isNodeVisible = (node: Node) => node.visible !== false;
const defaultFilter = {
  isNodeVisible,
  groupVisibilityEditable: false,
  normalizeGroupTitle: (value: unknown) => String(value || '').trim(),
  isGroupVisible: () => true,
};

const formal = (nodes: Node[]) => filterVisibleNativeLayoutNodes({ ...defaultFilter, nodes, pruneEmptyContainers: true });
const designer = (nodes: Node[]) => filterVisibleNativeLayoutNodes({ ...defaultFilter, nodes, pruneEmptyContainers: false });

// 1. An emptied header never occupies space; a header that still carries an
//    action keeps its container.
assert.deepEqual(formal([{ type: 'header', children: [] }]), [], 'empty header must be pruned');
assert.equal(formal([{ type: 'header', children: [{ type: 'button', name: 'action_submit' }] }]).length, 1, 'header with a button must survive');
assert.equal(formal([{ type: 'header', visible: false, children: [field('note')] }]).length, 0, 'a hidden header and its content must be pruned');

// 2. Layout wrappers carry no section separator; business sections and the
//    designer target keep theirs.
assert.equal(isLayoutOnlyGroupContainer({ nodeType: 'group', editable: false, sectionTitle: '' }), true);
assert.equal(isLayoutOnlyGroupContainer({ nodeType: 'group', editable: false, sectionTitle: '办理主信息' }), false);
assert.equal(isLayoutOnlyGroupContainer({ nodeType: 'group', editable: true, sectionTitle: '' }), false);
assert.equal(isLayoutOnlyGroupContainer({ nodeType: 'sheet', editable: false, sectionTitle: '' }), false);

// 3. Hidden children are dropped, and a container left without visible content
//    is pruned with them.
const withHiddenChild = [field('note'), { type: 'group', string: '隐藏章节', children: [{ type: 'field', name: 'secret', visible: false }] }];
assert.deepEqual(collectNativeVisibleFieldNames(formal(withHiddenChild), isNodeVisible).has('secret'), false);
assert.equal(formal([group([{ type: 'field', name: 'secret', visible: false }])]).length, 0, 'container left empty by filtering must be pruned');

// 4. A non-empty page tab and a non-empty relation detail keep their content.
const notebookTree = [notebook([page([field('line_ids')]), { type: 'page', string: '空页签', children: [] }])];
const keptNotebook = formal(notebookTree);
assert.equal(keptNotebook.length, 1, 'notebook with one non-empty page survives');
assert.deepEqual((keptNotebook[0].children as Node[]).map((child) => child.string || ''), ['明细'], 'only the emptied page is pruned');
assert.equal(formal([group([field('attachment_ids')], true, { name: 'native_subordinate_relations' })]).length, 1);

// 5. Nested wrappers never stack a second section separator: inside a business
//    section only the section itself is decorated.
const nested = [group([group([field('note')])], true, { string: '办理主信息' })];
const nestedSection = formal(nested)[0];
const nestedWrapper = (nestedSection.children as Node[])[0];
assert.equal(isLayoutOnlyGroupContainer({ nodeType: 'group', editable: false, sectionTitle: nestedSection.string }), false, 'business section keeps the separator');
assert.equal(isLayoutOnlyGroupContainer({ nodeType: 'group', editable: false, sectionTitle: nestedWrapper.string }), true, 'nested wrapper draws no separator');

// 6. Body and navigation read one effective tree: a pruned section disappears
//    from the collected titles and field names as well.
const mixed = [group([field('note')], true, { string: '办理主信息' }), group([{ type: 'field', name: 'hidden_field', visible: false }], true, { string: '空章节' })];
const effective = formal(mixed);
assert.deepEqual(collectNativeVisibleSectionTitles(effective), ['办理主信息'], 'navigation must not list a pruned section');
assert.deepEqual(Array.from(collectNativeVisibleFieldNames(effective, isNodeVisible)), ['note']);

// 7. The designer keeps empty groups as drop targets while the business
//    preview prunes them.
const emptyGroup = [group([])];
assert.equal(designer(emptyGroup).length, 1, 'designer canvas keeps the empty group');
assert.equal(formal(emptyGroup).length, 0, 'business rendering prunes the empty group');

// 8. Action placeholders close only with a proven carrier, never on structure
//    authority alone.
const authorityOnly = resolveFormActionPlaceholderGate({
  useNativeFormTree: false,
  nativeStructureAuthority: 'native_authority',
  headerActionKeys: ['action_submit'],
  workflowTransitionActionKeys: ['action_approve'],
  bodyActionKeys: ['action_print'],
});
assert.equal(authorityOnly.suppressWorkflowTransitions, false, 'an uncarried transition keeps its entry');
assert.equal(authorityOnly.suppressBodyActions, false, 'an uncarried body action keeps its entry');
assert.deepEqual(authorityOnly.uncarriedActionKeys, ['action_approve', 'action_print']);
const carried = resolveFormActionPlaceholderGate({
  useNativeFormTree: false,
  nativeStructureAuthority: 'native_authority',
  headerActionKeys: ['action_submit', 'action_approve'],
  workflowTransitionActionKeys: ['action_approve'],
  bodyActionKeys: [],
});
assert.equal(carried.suppressWorkflowTransitions, true, 'a header-carried transition closes its placeholder');
assert.deepEqual(carried.uncarriedActionKeys, []);
const nativeTree = resolveFormActionPlaceholderGate({
  useNativeFormTree: true,
  nativeStructureAuthority: '',
  headerActionKeys: [],
  workflowTransitionActionKeys: ['action_approve'],
  bodyActionKeys: ['action_print'],
});
assert.deepEqual(
  [nativeTree.suppressWorkflowTransitions, nativeTree.suppressBodyActions],
  [true, true],
  'the native tree is itself the carrier',
);
const plainLegacy = resolveFormActionPlaceholderGate({
  useNativeFormTree: false,
  nativeStructureAuthority: '',
  headerActionKeys: [],
  workflowTransitionActionKeys: ['action_approve'],
  bodyActionKeys: [],
});
assert.deepEqual(
  [plainLegacy.suppressWorkflowTransitions, plainLegacy.suppressBodyActions],
  [false, false],
  'a legacy body keeps its own action entries',
);
// The officially composed body owns its presentation (the record-list query block is
// gone from the form entirely), but composition authority is still not structure
// ownership: it must not close an action entry whose carrier is unproven.
const officialComposition = resolveFormActionPlaceholderGate({
  useNativeFormTree: false,
  nativeStructureAuthority: '',
  officialFormComposition: true,
  headerActionKeys: ['action_submit'],
  workflowTransitionActionKeys: ['action_approve'],
  bodyActionKeys: ['action_print'],
});
assert.equal(officialComposition.suppressWorkflowTransitions, false, 'composition authority alone still cannot close an uncarried transition');
assert.equal(officialComposition.suppressBodyActions, false, 'composition authority alone still cannot close an uncarried body action');
assert.deepEqual(officialComposition.uncarriedActionKeys, ['action_approve', 'action_print']);
const officialCompositionCarried = resolveFormActionPlaceholderGate({
  useNativeFormTree: false,
  nativeStructureAuthority: '',
  officialFormComposition: true,
  headerActionKeys: ['action_approve'],
  workflowTransitionActionKeys: ['action_approve'],
  bodyActionKeys: [],
});
assert.equal(officialCompositionCarried.suppressWorkflowTransitions, false, 'a proven carrier closes the transition only on a structure-owned body');
assert.equal(officialCompositionCarried.suppressBodyActions, false);

// 8b. Body-kind completeness. The record-list query block once leaked into a form body
//     because a *new* body kind was added without re-asking whether that kind owns the
//     form structure. The input table below is exhaustive over the declared union, so a
//     future body kind fails to compile here until it is given an explicit case, and the
//     structure-ownership answer is asserted for every kind instead of for the two kinds
//     that happened to exist first.
const bodyKindInputs: Record<FormActionPlaceholderBodyKind, {
  useNativeFormTree: boolean;
  nativeStructureAuthority: string;
  officialFormComposition?: boolean;
}> = {
  native_form_tree: { useNativeFormTree: true, nativeStructureAuthority: '' },
  native_authority: { useNativeFormTree: false, nativeStructureAuthority: 'native_authority' },
  official_composition: { useNativeFormTree: false, nativeStructureAuthority: '', officialFormComposition: true },
  unowned_body: { useNativeFormTree: false, nativeStructureAuthority: '' },
};
assert.deepEqual(
  Object.keys(bodyKindInputs).sort(),
  [...FORM_ACTION_PLACEHOLDER_BODY_KINDS].sort(),
  'every declared body kind must have an explicit gate case',
);
for (const kind of FORM_ACTION_PLACEHOLDER_BODY_KINDS) {
  const bodyKindInput = bodyKindInputs[kind];
  assert.equal(classifyFormActionPlaceholderBody(bodyKindInput), kind, `${kind} must classify as itself`);
  const result = resolveFormActionPlaceholderGate({
    ...bodyKindInput,
    headerActionKeys: ['action_approve'],
    workflowTransitionActionKeys: ['action_approve'],
    bodyActionKeys: [],
  });
  assert.equal(
    result.suppressWorkflowTransitions,
    formBodyOwnsStructure(kind),
    `${kind}: only a structurally owned body may close a carried action entry`,
  );
}

// 9. Cleanup releases only a draft this run proves it authored: a positive `created`
//    credential on a draft it asked to be fresh, confirmed by inventory exclusion. A
//    draft the run merely saved into is never released, and a credential that
//    contradicts the inventory is refused rather than trusted.
assert.equal(
  resolveDesignerDraftOwnership({ changeSetId: 190, inventoryIds: [], created: true, freshRequested: true }).release,
  true,
  'a change set this run created is released by cleanup',
);
const resumed = resolveDesignerDraftOwnership({ changeSetId: 163, inventoryIds: [163], created: false, freshRequested: false });
assert.equal(resumed.release, false, 'a resumed draft must not be released');
assert.equal(resumed.reason, 'creation_not_proven_by_this_run');
assert.equal(
  resolveDesignerDraftOwnership({ changeSetId: 163, inventoryIds: [163], created: true, freshRequested: true }).reason,
  'preexisting_designer_draft_not_authored_by_run',
  'a draft that pre-existed the run is never released, even if `created` claims otherwise',
);
assert.equal(
  resolveDesignerDraftOwnership({ changeSetId: 0, created: true, freshRequested: true }).reason,
  'unidentified_change_set',
  'an unidentified draft is never released',
);

// 10. An existing draft on the designer target stops the run before its first write;
//     only an authorization that names that draft and its operations may continue. The
//     inventory itself is built by the product's resumable-state scope, so this gate
//     refuses every listed draft regardless of its state.
assert.equal(resolveDesignerDraftPolicy({ inventory: [], authorization: '' }).decision, 'proceed');
const blocked = resolveDesignerDraftPolicy({ inventory: [{ id: 163, state: 'draft' }], authorization: '' });
assert.equal(blocked.decision, 'fail_closed');
assert.equal(blocked.reason, 'preexisting_designer_draft:163');
assert.deepEqual(blocked.blocking, [163]);
const authorized = resolveDesignerDraftPolicy({ inventory: [{ id: 163, state: 'draft' }], authorization: '163:stage,publish' });
assert.equal(authorized.decision, 'proceed', 'the operator authorization is the only way past the guard');
assert.deepEqual(authorized.allowed[163], ['stage', 'publish']);
assert.equal(isDraftOperationAllowed({ policy: authorized, changeSetId: 163, operation: 'rollback' }), false,
  'an authorization covers only the operations it names');
// `ready` is resumable: the product opened a `ready` change set on a real run, which is
// why the gate must refuse it as well.
assert.equal(
  resolveDesignerDraftPolicy({ inventory: [{ id: 192, state: 'ready' }], authorization: '' }).reason,
  'preexisting_designer_draft:192',
  'a ready change set is resumable and must stop the run',
);
assert.equal(
  resolveDesignerDraftPolicy({ inventory: [{ id: 163, state: 'draft' }], authorization: '1:stage' }).decision,
  'fail_closed',
  'an authorization for a draft outside the inventory must not widen access',
);

// 11. A section heading is contract-authored content. The renderer may not
//     invent a business label from a semantic role: every role on its own must
//     resolve to no heading, so a missing contract title stays visible as a
//     gap instead of being silently filled with a placeholder. This is the
//     counterexample for the defect where every section of a contract form
//     rendered as "基本资料".
const SEMANTIC_ROLES = ['context', 'relation', 'activity', 'task', 'summary', 'risk', 'audit'];
for (const role of SEMANTIC_ROLES) {
  assert.equal(
    resolveNativeSectionHeading({ type: 'group', attributes: { semanticFormRole: role } }),
    '',
    `${role}: a role alone must never produce a business heading`,
  );
}
assert.equal(
  resolveNativeSectionHeading({ type: 'group', string: '金额与条款', attributes: { semanticFormRole: 'context' } }),
  '金额与条款',
  'the contract-authored group title wins over the semantic role',
);
assert.equal(
  resolveNativeSectionHeading({ type: 'group', semanticTitle: '办理信息' }),
  '办理信息',
  'the governed form-structure semantic title is contract-authored heading content',
);
assert.equal(
  resolveNativeSectionHeading({ type: 'group', string: '合同基本信息', attributes: { 'data-sc-anchor': 'contract.basic', semanticFormRole: '' } }),
  '合同基本信息',
  'an empty semantic role must not suppress an authored heading',
);
assert.equal(
  resolveNativeSectionHeading({ type: 'group', attributes: { 'data-sc-anchor': 'contract.basic', }, string: '合同基本信息' }),
  '合同基本信息',
  'the released native opt-in keeps its section label',
);
assert.equal(
  resolveNativeSectionHeading({ type: 'group', string: '合同基本信息' }, { fieldConfigEditable: true }),
  '',
  'the designer canvas keeps its own editing target instead of a runtime heading',
);
assert.equal(
  resolveNativeSectionHeading({ type: 'field', name: 'amount', string: '金额' }),
  '',
  'only a group container owns a business section heading',
);

// 12. Both native consumers share contract-derived detail adoption. Authored
// notebook tabs remain; only generated whole-page navigation is suppressed.
const sourceRoot = path.resolve(process.cwd(), 'frontend/apps/web/src');
const source = (file: string) => fs.readFileSync(path.join(sourceRoot, file), 'utf8');
const treeSource = source('components/template/NativeFormTreeRenderer.vue');
assert.ok(treeSource.includes('detailComposition?.adopted.value === true'));
assert.ok(treeSource.includes('!props.insideDetailCard'));
assert.ok(treeSource.includes(':is="isDetailCard(node) ? ScCard'));
assert.ok(treeSource.includes(':inside-detail-card="insideDetailCard || isDetailCard(node)"'));
assert.ok(treeSource.includes("nodeType(node) === 'notebook'"));
assert.ok(treeSource.includes(':model-value="activePageIndex"'));
assert.ok(treeSource.includes(':nodes="notebookPageChildren(node, activePageIndex)"'));
for (const file of ['CanonicalNativeFormSurface.vue', 'ObjectTaskPage.vue']) {
  assert.ok(source(`pages/contractForm/${file}`).includes('!detailComposition?.adopted.value && sectionLinks.length > 1'));
}
const nativeCanvasSource = source('pages/contractForm/ContractFormNativeCanvas.vue');
assert.ok(nativeCanvasSource.includes('!props.designerMode'));
assert.ok(nativeCanvasSource.includes(':prefer-readonly-facts="adoptedDetail"'));
assert.ok(nativeCanvasSource.includes('!adoptedDetail && sectionItems.length > 2'));
assert.ok(source('pages/contractForm/CanonicalNativeFormSurface.vue').includes("? 'collaboration' : undefined"));
assert.ok(source('pages/ContractFormPage.vue').includes("'card--detail': standardDetailComposition.adopted.value"));

console.log('[native_form_structure_responsibility_test] PASS cases=12');
