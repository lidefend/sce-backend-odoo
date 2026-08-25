import assert from 'node:assert/strict';
import {
  collectOne2manyDraftValidationFromRows,
  one2manyColumnDisplayValue,
  one2manyColumnsFromSubview,
  one2manyRowActionsFromSubview,
  resolveOne2manyRowColumnBehavior,
  selectOne2manySubview,
  setOne2manyDraftRowField,
} from '../src/pages/contractForm/one2manyUtils';
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
import { buildActionViewRowClickTarget, resolveCollectionWriteAuthority, shouldUseCanonicalCollectionDetail } from '../src/app/runtime/actionViewInteractionRuntime';
import { pickContractNavQuery } from '../src/app/navigationContext';
import { extractKanbanFieldsFromContract } from '../src/app/action_runtime/useActionViewContractShapeRuntime';
import { resolveLoadKanbanFieldApplyState } from '../src/app/runtime/actionViewLoadViewFieldStateRuntime';
import { resolveDesktopListCandidates } from '../src/pages/listPage/listColumnVisibility';
import type { ContractV2NormalizedStore } from '../src/app/contracts/v2/types';

function normalizedCollectionContract(
  viewType: string,
  collectionPresentation: Record<string, unknown>,
  fieldCodes: string[] = [],
): ContractV2NormalizedStore {
  const widgets = fieldCodes.map((fieldCode) => ({ fieldCode }));
  return {
    snapshot: {
      pageInfo: { viewType },
      layoutContract: { listProfile: { collection_presentation: collectionPresentation } },
    },
    widgetsByFieldCode: new Map(widgets.map((widget) => [widget.fieldCode, widget])),
  } as unknown as ContractV2NormalizedStore;
}

const cardContract = normalizedCollectionContract('tree,kanban,form', {
  semantic: 'card', label: '卡片', group_field: null, capabilities: { grouped_lanes: false },
});
const workflowContract = normalizedCollectionContract('kanban,tree,form', {
  semantic: 'workflow_board', label: '流程看板', group_field: 'state', capabilities: { grouped_lanes: true },
});

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
assert.deepEqual(extractKanbanFieldsFromContract(
  normalizedCollectionContract('kanban', {}, ['name', 'lifecycle_state']),
), ['name', 'lifecycle_state']);
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
const selectionColumn = {
  name: 'state', label: '状态', ttype: 'selection', required: false,
  selection: [['draft', '草稿'], ['won', '已中标']] as Array<[string, string]>,
};
assert.equal(one2manyColumnDisplayValue(selectionColumn, 'won'), '已中标');
assert.equal(one2manyColumnDisplayValue(selectionColumn, 'unknown'), 'unknown');
const dynamicColumn = {
  name: 'note', label: '说明', ttype: 'char', required: false,
  modifiers: {
    invisible: { kind: 'field_compare', field: 'state', operator: '=', value: 'hidden' },
    readonly: { kind: 'field_compare', field: 'state', operator: '=', value: 'done' },
    required: { kind: 'field_compare', field: 'state', operator: '=', value: 'draft' },
  },
};
assert.deepEqual(resolveOne2manyRowColumnBehavior(dynamicColumn, { state: 'draft', note: '' }), {
  invisible: false, columnInvisible: false, readonly: false, required: true,
});
assert.deepEqual(resolveOne2manyRowColumnBehavior(dynamicColumn, { state: 'done', note: 'locked' }), {
  invisible: false, columnInvisible: false, readonly: true, required: false,
});
assert.deepEqual(resolveOne2manyRowColumnBehavior(dynamicColumn, { state: 'hidden', note: '' }), {
  invisible: true, columnInvisible: false, readonly: false, required: false,
});
assert.equal(resolveOne2manyRowColumnBehavior({
  ...dynamicColumn, modifiers: { column_invisible: "context.get('hide_note')" },
}, {}, {}).columnInvisible, true);
assert.equal(resolveOne2manyRowColumnBehavior({
  ...dynamicColumn,
  modifiers: { column_invisible: { kind: 'field_truthy', field: 'parent.hide_note' } },
}, {}, { hide_note: false }).columnInvisible, false);
const hiddenRequiredColumn = {
  ...dynamicColumn,
  required: true,
  modifiers: { column_invisible: true },
};
const hiddenRows = { line_ids: [{
  key: 'hidden-column', id: 10, isNew: false, removed: false, dirty: false, dirtyFields: [],
  values: { state: 'draft', note: '' },
}] };
assert.equal(setOne2manyDraftRowField({
  rowsByField: hiddenRows, fieldName: 'line_ids', rowKey: 'hidden-column', column: hiddenRequiredColumn, value: 'mutated',
}), false);
assert.equal(hiddenRows.line_ids[0].dirty, false);
assert.deepEqual(collectOne2manyDraftValidationFromRows({
  rowsByField: hiddenRows, recordId: 1, resolvePrimaryColumn: () => 'state', resolveColumns: () => [hiddenRequiredColumn],
}), { issues: [], rowErrors: {} });
const dynamicRows = { line_ids: [{
  key: 'done', id: 7, isNew: false, removed: false, dirty: false, dirtyFields: [],
  values: { state: 'done', note: 'locked' },
}, {
  key: 'draft', id: 8, isNew: false, removed: false, dirty: true, dirtyFields: [],
  values: { state: 'draft', note: '' },
}, {
  key: 'hidden', id: 9, isNew: false, removed: false, dirty: true, dirtyFields: [],
  values: { state: 'hidden', note: '' },
}] };
assert.equal(setOne2manyDraftRowField({
  rowsByField: dynamicRows, fieldName: 'line_ids', rowKey: 'done', column: dynamicColumn, value: 'mutated',
}), false);
assert.equal(dynamicRows.line_ids[0].values.note, 'locked');
assert.equal(dynamicRows.line_ids[0].dirty, false);
dynamicRows.line_ids[1].modifierPatches = { note: { invisible: true, required: true } };
assert.deepEqual(collectOne2manyDraftValidationFromRows({
  rowsByField: dynamicRows, recordId: 1, resolvePrimaryColumn: () => 'state', resolveColumns: () => [dynamicColumn],
}), {
  issues: [],
  rowErrors: {},
});
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
const editableDetail = buildActionViewRowClickTarget({ targetModel: 'x.model', rawId: 7, menuId: 3, actionId: 4, carryQuery: {}, editable: true });
assert.equal(detailFromTable?.path, detailFromCard?.path);
assert.equal(editableDetail?.path, '/f/x.model/7');
assert.equal(resolveCollectionWriteAuthority({ modelRights: undefined }), false);
assert.equal(resolveCollectionWriteAuthority({ modelRights: { write: undefined } }), false);
assert.equal(resolveCollectionWriteAuthority({ modelRights: { write: false } }), false);
assert.equal(resolveCollectionWriteAuthority({ modelRights: { write: true } }), true);
assert.equal(shouldUseCanonicalCollectionDetail({ viewMode: 'kanban', collectionSemantic: 'card' }), true);
assert.equal(shouldUseCanonicalCollectionDetail({ viewMode: 'kanban', collectionSemantic: 'workflow_board' }), false);

// detail_back_restores_collection_context
assert.deepEqual(pickContractNavQuery(switched), switched);

// responsive_auto_card_distinct_from_explicit_card
assert.equal(resolveResponsiveCollectionPresentation({ explicitMode: 'table', compactViewport: true }), 'responsive_table_card');
assert.equal(resolveResponsiveCollectionPresentation({ explicitMode: 'card', compactViewport: true }), 'explicit_card');

// unknown_kanban_semantic_fails_safe
assert.equal(resolveActionCollectionPresentation(
  normalizedCollectionContract('kanban', { semantic: 'mystery' }),
  'kanban',
).semantic, 'card');

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
