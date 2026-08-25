import { strict as assert } from 'node:assert';
import { resolveCollectionAggregateEntry } from '../src/app/presentation/collectionAggregatePresentation';
import { mapActionViewGroupedRows } from '../src/app/runtime/actionViewLoadResultRuntime';

const displayEntry = { page_sum: 30, sum: 50, aggregation_field: 'amount' };
assert.equal(resolveCollectionAggregateEntry({ request_amount_display: displayEntry }, 'request_amount_display', 'amount'), displayEntry);

const sourceEntry = { page_sum: 10, sum: 20 };
assert.equal(resolveCollectionAggregateEntry({ amount: sourceEntry }, 'request_amount_display', 'amount'), sourceEntry);

const preferredDisplayEntry = { page_sum: 40, sum: 60 };
assert.equal(resolveCollectionAggregateEntry(
  { request_amount_display: preferredDisplayEntry, amount: sourceEntry },
  'request_amount_display',
  'amount',
), preferredDisplayEntry);

assert.deepEqual(resolveCollectionAggregateEntry({}, 'request_amount_display', 'amount'), {});
assert.deepEqual(resolveCollectionAggregateEntry(null, 'request_amount_display', 'amount'), {});

const groupedAggregates = {
  request_amount_display: { page_sum: 480000, sum: 480000, aggregation_field: 'amount' },
};
const [groupedRow] = mapActionViewGroupedRows({
  groupedRowsRaw: [{
    group_key: 'state:draft',
    label: '草稿',
    total_count: 1,
    sample_rows: [{ id: 100, request_amount_display: '¥480,000.00' }],
    aggregates: groupedAggregates,
  }],
  groupPagingRaw: {},
  groupSampleLimit: 3,
  groupPageOffsets: {},
  emptyLabel: '未分组',
  buildGroupKey: () => 'fallback',
  normalizeGroupPageOffset: (offset) => offset,
});
assert.equal(groupedRow?.aggregates, groupedAggregates);

const [groupedRowWithoutAuthority] = mapActionViewGroupedRows({
  groupedRowsRaw: [{
    group_key: 'state:approved',
    label: '已批准',
    total_count: 1,
    sample_rows: [{ id: 101 }],
    aggregates: ['not-authoritative'],
  }],
  groupPagingRaw: {},
  groupSampleLimit: 3,
  groupPageOffsets: {},
  emptyLabel: '未分组',
  buildGroupKey: () => 'fallback',
  normalizeGroupPageOffset: (offset) => offset,
});
assert.equal(groupedRowWithoutAuthority?.aggregates, undefined);

console.log('[collection_aggregate_presentation_test] PASS cases=7');
