import assert from 'node:assert/strict';
import { one2manyColumnsFromSubview, one2manyRowActionsFromSubview, selectOne2manySubview } from '../src/pages/contractForm/one2manyUtils';
import {
  resolveActionCollectionPresentation,
  resolveGroupedCollectionPresentation,
  resolveActionViewAvailableModes,
} from '../src/app/contracts/actionViewSurfaceContract';
import { resolvePreferredActionViewMode } from '../src/app/runtime/actionViewContractLoadRuntime';
import {
  buildCollectionRouteQuery,
  groupCollectionRecords,
  resolveResponsiveCollectionPresentation,
} from '../src/app/runtime/collectionViewRuntime';
import { buildActionViewRowClickTarget, shouldUseCanonicalCollectionDetail } from '../src/app/runtime/actionViewInteractionRuntime';
import { pickContractNavQuery } from '../src/app/navigationContext';
import {
  extractKanbanFieldsFromContract,
  extractNativeColumnOccurrenceSchema,
} from '../src/app/action_runtime/useActionViewContractShapeRuntime';
import { resolveLoadKanbanFieldApplyState } from '../src/app/runtime/actionViewLoadViewFieldStateRuntime';
import { resolveDesktopListCandidates } from '../src/pages/listPage/listColumnVisibility';

const cardContract = {
  head: { view_type: 'tree,kanban,form' },
  views: {
    tree: { columns: ['id', 'name'] },
    kanban: {
      fields: ['id', 'name'],
      collection_presentation: {
        semantic: 'card', label: '卡片', group_field: null,
        capabilities: { grouped_lanes: false },
      },
    },
  },
};
const workflowContract = {
  head: { view_type: 'kanban,tree,form' },
  views: {
    tree: { columns: ['id', 'name', 'state'] },
    kanban: {
      fields: ['id', 'name', 'state'],
      collection_presentation: {
        semantic: 'workflow_board', label: '流程看板', group_field: 'state',
        capabilities: { grouped_lanes: true },
      },
    },
  },
};

// fresh_project_ledger_defaults_to_table
assert.equal(resolvePreferredActionViewMode({
  contractViewTypeRaw: 'tree,kanban,form', metaViewModesRaw: 'tree,kanban,form',
  contract: cardContract, routeViewModeRaw: '', currentPreferredViewModeRaw: '',
}), 'tree');

// table_and_card_modes_available; detail/form is intentionally not a collection mode.
assert.deepEqual(resolveActionViewAvailableModes({
  contractViewTypeRaw: 'tree,kanban,form', metaViewModesRaw: '', contract: cardContract,
}), ['tree', 'kanban']);

// card_label_not_workflow_board
assert.equal(resolveActionCollectionPresentation(cardContract, 'kanban').label, '卡片');

// workflow_board_requires_group_semantics
assert.deepEqual(resolveActionCollectionPresentation(workflowContract, 'kanban'), {
  semantic: 'workflow_board', label: '流程看板', groupField: 'state', groupedLanes: true, config: {},
});
assert.equal(groupCollectionRecords([
  { id: 1, state: ['draft', '草稿'] }, { id: 2, state: ['done', '完成'] }, { id: 3, state: ['draft', '草稿'] },
], 'state').length, 2);
assert.equal(resolveGroupedCollectionPresentation(
  resolveActionCollectionPresentation(cardContract, 'kanban'), 'state',
).semantic, 'workflow_board');
assert.deepEqual(extractKanbanFieldsFromContract({ views: { kanban: { fields: [
  { field: { name: 'name', label: '名称' } }, { field: { name: 'lifecycle_state', label: '状态' } },
] } } }), ['name', 'lifecycle_state']);
const occurrenceColumns = extractNativeColumnOccurrenceSchema({ views: { tree: {
  columns_schema: [{ name: 'amount_total', label: 'merged legacy column' }],
  column_occurrences: [
    {
      name: 'amount_total', field_type: 'monetary', widget: 'monetary',
      source_position: 0, occurrence_index: 1, native_locator: '/tree/field[1]',
      attributes: { string: 'Untaxed Amount', optional: 'show' },
      modifiers: { readonly: true },
    },
    {
      name: 'amount_total', field_type: 'monetary', widget: 'monetary',
      source_position: 1, occurrence_index: 2, native_locator: '/tree/field[2]',
      attributes: { string: 'Tax Included', optional: 'hide' },
      modifiers: { column_invisible: false },
    },
  ],
} } });

const inlineNativeSubview = { tree: { columns: [{ name: 'partner_id' }], column_occurrences: [
  {
    name: 'partner_id', field_type: 'many2one', native_locator: '/form/field[1]/tree[1]/field[1]', occurrence_index: 1,
    attributes: { string: 'Billing Partner' }, modifiers: { readonly: false }, relation_active_actions: { write: true },
  },
  {
    name: 'partner_id', field_type: 'many2one', native_locator: '/form/field[1]/tree[1]/field[2]', occurrence_index: 2,
    attributes: { string: 'Delivery Partner' }, relation_active_actions: { write: false },
  },
] } };
const inlineSelectedSubview = selectOne2manySubview(
  { tree: { columns: ['display_name'] } },
  inlineNativeSubview,
);
assert.equal(inlineSelectedSubview, inlineNativeSubview);
const inlineOccurrenceColumns = one2manyColumnsFromSubview(inlineSelectedSubview, () => null);
assert.equal(inlineOccurrenceColumns.length, 2);
assert.deepEqual(inlineOccurrenceColumns.map((column) => ({
  key: column.key, name: column.name, label: column.label, readonly: column.readonly,
})), [
  { key: '/form/field[1]/tree[1]/field[1]', name: 'partner_id', label: 'Billing Partner', readonly: true },
  { key: '/form/field[1]/tree[1]/field[2]', name: 'partner_id', label: 'Delivery Partner', readonly: true },
]);
assert.equal(one2manyColumnsFromSubview({ tree: { columns: [], column_occurrences: inlineNativeSubview.tree.column_occurrences } }, () => null).length, 0);
const inlineActions = one2manyRowActionsFromSubview({ tree: { row_actions: [
  {
    label: 'Open Child', kind: 'object', payload: { method: 'action_open', type: 'object' },
    native_identity: { authoritative: true, canonical_region: 'row_actions', native_locator: '/form/field[1]/tree[1]/button[1]' },
    action_safety: { classification: 'safe', requires_confirm: false },
  },
  {
    label: 'Context Child', kind: 'object', payload: { method: 'action_context', type: 'object', context_raw: "{'default_mode': 'edit'}" },
    native_identity: { authoritative: true, canonical_region: 'row_actions', native_locator: '/form/field[1]/tree[1]/button[2]' },
    action_safety: { classification: 'safe', requires_confirm: false },
  },
  {
    label: 'Conditional Child', kind: 'object', payload: { method: 'action_conditional', type: 'object' },
    native_identity: { authoritative: true, canonical_region: 'row_actions', native_locator: '/form/field[1]/tree[1]/button[3]' },
    action_safety: { classification: 'safe', requires_confirm: false },
    visible: { attrs: { invisible: { kind: 'field_truthy', field: 'blocked' } }, domain: [], states: [] },
  },
  { label: 'Synthetic', kind: 'open', payload: { view_mode: 'form' } },
] } });
assert.deepEqual(inlineActions.map((action) => ({ label: action.label, enabled: action.enabled })), [
  { label: 'Open Child', enabled: true },
  { label: 'Context Child', enabled: false },
  { label: 'Conditional Child', enabled: false },
]);
assert.equal(occurrenceColumns.length, 2);
assert.deepEqual(occurrenceColumns.map((column) => ({
  name: column.name,
  label: column.label,
  type: column.type,
  widget: column.widget,
  source_position: column.source_position,
  occurrence_index: column.occurrence_index,
  native_locator: column.native_locator,
  readonly: column.readonly,
  column_invisible: column.column_invisible,
})), [
  {
    name: 'amount_total', label: 'Untaxed Amount', type: 'monetary', widget: 'monetary',
    source_position: 0, occurrence_index: 1, native_locator: '/tree/field[1]',
    readonly: true, column_invisible: undefined,
  },
  {
    name: 'amount_total', label: 'Tax Included', type: 'monetary', widget: 'monetary',
    source_position: 1, occurrence_index: 2, native_locator: '/tree/field[2]',
    readonly: undefined, column_invisible: false,
  },
]);
assert.deepEqual(resolveLoadKanbanFieldApplyState({
  kanbanContractFields: [{ name: 'name' }, { name: 'lifecycle_state' }] as unknown as string[],
  fallbackKanbanFields: [], advancedContractFields: [], uniqueFieldsFn: (fields) => [...new Set(fields)],
  kanbanProfile: { titleField: 'name', primaryFields: [], secondaryFields: [], statusFields: [], metricFields: [], quickActionCount: 0 },
}).kanbanFields, ['name', 'lifecycle_state']);

// table_card_record_set_equivalent
const rows = [{ id: 1, name: 'A' }, { id: 2, name: 'B' }];
assert.deepEqual(groupCollectionRecords(rows, '')[0].records.map((row) => row.id), [1, 2]);

// query_context_preserved_across_switch
const switched = buildCollectionRouteQuery({ search: 'alpha', group_by: 'state', order: 'name asc', list_offset: '20' }, { viewMode: 'kanban', listOffset: 20 });
assert.deepEqual(switched, { search: 'alpha', group_by: 'state', order: 'name asc', list_offset: '20', view_mode: 'kanban' });

// card_opens_same_detail_form
const detailFromTable = buildActionViewRowClickTarget({ targetModel: 'x.model', rawId: 7, menuId: 3, actionId: 4, carryQuery: { view_mode: 'tree' } });
const detailFromCard = buildActionViewRowClickTarget({ targetModel: 'x.model', rawId: 7, menuId: 3, actionId: 4, carryQuery: { view_mode: 'kanban' } });
assert.equal(detailFromTable?.path, detailFromCard?.path);
assert.equal(shouldUseCanonicalCollectionDetail({ viewMode: 'kanban', collectionSemantic: 'card' }), true);
assert.equal(shouldUseCanonicalCollectionDetail({ viewMode: 'kanban', collectionSemantic: 'workflow_board' }), false);

// detail_back_restores_collection_context
assert.deepEqual(pickContractNavQuery(switched), switched);

// responsive_auto_card_distinct_from_explicit_card
assert.equal(resolveResponsiveCollectionPresentation({ explicitMode: 'table', compactViewport: true }), 'responsive_table_card');
assert.equal(resolveResponsiveCollectionPresentation({ explicitMode: 'card', compactViewport: true }), 'explicit_card');

// unknown_kanban_semantic_fails_safe
assert.equal(resolveActionCollectionPresentation({ views: { kanban: { collection_presentation: { semantic: 'mystery' } } } }, 'kanban').semantic, 'card');

// Native desktop tree columns within the product budget remain authoritative;
// narrow widths use horizontal scrolling instead of silently hiding fields.
const twelveNativeColumns = Array.from({ length: 12 }, (_, index) => ({ field: `field_${index + 1}`, width: 160 }));
assert.deepEqual(resolveDesktopListCandidates({
  fields: twelveNativeColumns,
  availableWidth: 900,
  capacity: 12,
}), twelveNativeColumns.map((item) => item.field));
assert.equal(resolveDesktopListCandidates({
  fields: [...twelveNativeColumns, { field: 'field_13', width: 160 }],
  availableWidth: 900,
  capacity: 12,
}).length <= 12, true);

console.log('[collection-view-semantics] PASS');
