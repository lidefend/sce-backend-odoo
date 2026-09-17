import assert from 'node:assert/strict';
import {
  collectNativeVisibleFieldNames,
  collectNativeVisibleSectionTitles,
  filterVisibleNativeLayoutNodes,
  isLayoutOnlyGroupContainer,
  type NativeLayoutLikeNode,
} from '../src/pages/contractForm/nativeLayoutUtils';
import { resolveFormActionPlaceholderGate } from '../src/pages/contractForm/formActionPlaceholderGate';
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
assert.equal(authorityOnly.suppressSearchFilters, true, 'record-list presets leave a native-structure body');
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
  [nativeTree.suppressSearchFilters, nativeTree.suppressWorkflowTransitions, nativeTree.suppressBodyActions],
  [true, true, true],
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
  [plainLegacy.suppressSearchFilters, plainLegacy.suppressWorkflowTransitions, plainLegacy.suppressBodyActions],
  [false, false, false],
  'a legacy body keeps its own action entries',
);

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

console.log('[native_form_structure_responsibility_test] PASS cases=10');
