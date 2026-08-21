import assert from 'node:assert/strict';
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
import { extractKanbanFieldsFromContract } from '../src/app/action_runtime/useActionViewContractShapeRuntime';
import { resolveLoadKanbanFieldApplyState } from '../src/app/runtime/actionViewLoadViewFieldStateRuntime';
import { resolveDesktopListCandidates } from '../src/pages/listPage/listColumnVisibility';

const collectionStore = (viewType: string, collectionPresentation: Record<string, unknown>) => ({
  snapshot: {
    pageInfo: { viewType },
    layoutContract: { listProfile: { collection_presentation: collectionPresentation } },
  },
}) as Parameters<typeof resolveActionCollectionPresentation>[0];
const cardContract = collectionStore('kanban', {
  semantic: 'card', label: '卡片', group_field: null,
  capabilities: { grouped_lanes: false },
});
const workflowContract = collectionStore('kanban', {
  semantic: 'workflow_board', label: '流程看板', group_field: 'state',
  capabilities: { grouped_lanes: true },
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
const canonicalKanbanStore = {
  snapshot: { pageInfo: { viewType: 'kanban' } },
  widgetsByFieldCode: new Map([
    ['name', { fieldCode: 'name' }],
    ['lifecycle_state', { fieldCode: 'lifecycle_state' }],
  ]),
} as Parameters<typeof extractKanbanFieldsFromContract>[0];
assert.deepEqual(extractKanbanFieldsFromContract(canonicalKanbanStore), ['name', 'lifecycle_state']);
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
assert.equal(resolveActionCollectionPresentation(collectionStore('kanban', { semantic: 'mystery' }), 'kanban').semantic, 'card');

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
