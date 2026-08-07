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
  semantic: 'workflow_board', label: '流程看板', groupField: 'state', groupedLanes: true,
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

console.log('[collection-view-semantics] PASS');
