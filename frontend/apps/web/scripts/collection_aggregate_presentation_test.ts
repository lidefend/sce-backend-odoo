import { strict as assert } from 'node:assert';
import {
  resolveCollectionAggregateCurrencyIdentity,
  resolveCollectionAggregateEntry,
} from '../src/app/presentation/collectionAggregatePresentation';
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

const monetaryAggregate = {
  aggregate: 'sum',
  data_type: 'monetary',
  currency_field: 'currency_id',
  currency_id: 1,
  page_sum: 10,
  sum: 20,
};
assert.deepEqual(
  resolveCollectionAggregateCurrencyIdentity(monetaryAggregate, 'currency_id', [
    { currency_id: [1, 'CNY'] },
  ]),
  { id: 1, label: 'CNY' },
  'matching aggregate currency id resolves its relation label',
);
assert.equal(
  resolveCollectionAggregateCurrencyIdentity(monetaryAggregate, 'currency_id', [
    { currency_id: [2, 'CNY'] },
  ]),
  null,
  'same display label with a different record id is rejected',
);
assert.equal(
  resolveCollectionAggregateCurrencyIdentity({ ...monetaryAggregate, currency_id: undefined }, 'currency_id', [
    { currency_id: [1, 'CNY'] },
  ]),
  null,
  'missing aggregate currency id is rejected',
);
assert.equal(
  resolveCollectionAggregateCurrencyIdentity({ ...monetaryAggregate, currency_id: 0 }, 'currency_id', [
    { currency_id: [0, 'CNY'] },
  ]),
  null,
  'invalid aggregate currency id is rejected',
);
assert.equal(
  resolveCollectionAggregateCurrencyIdentity({ ...monetaryAggregate, currency_id: '1' }, 'currency_id', [
    { currency_id: [1, 'CNY'] },
  ]),
  null,
  'string aggregate currency ids are rejected',
);
assert.equal(
  resolveCollectionAggregateCurrencyIdentity({ ...monetaryAggregate, aggregate: 'none' }, 'currency_id', [
    { currency_id: [1, 'CNY'] },
  ]),
  null,
  'unavailable aggregate is rejected',
);
assert.equal(
  resolveCollectionAggregateCurrencyIdentity({ ...monetaryAggregate, data_type: 'float' }, 'currency_id', [
    { currency_id: [1, 'CNY'] },
  ]),
  null,
  'monetary footer currency is rejected when the aggregate declares another data type',
);
assert.equal(
  resolveCollectionAggregateCurrencyIdentity({ ...monetaryAggregate, data_type: undefined }, 'currency_id', [
    { currency_id: [1, 'CNY'] },
  ]),
  null,
  'missing aggregate data type is rejected',
);
assert.equal(
  resolveCollectionAggregateCurrencyIdentity({ ...monetaryAggregate, currency_field: 'company_currency_id' }, 'currency_id', [
    { company_currency_id: [1, 'CNY'], currency_id: [1, 'CNY'] },
  ]),
  null,
  'aggregate and column currency fields must agree',
);
assert.equal(
  resolveCollectionAggregateCurrencyIdentity(monetaryAggregate, 'currency_id', [
    { currency_id: 1 },
  ]),
  null,
  'bare currency ids do not provide a product-facing label',
);
assert.equal(
  resolveCollectionAggregateCurrencyIdentity(monetaryAggregate, 'currency_id', [
    { currency_id: ['1', 'CNY'] },
  ]),
  null,
  'string relation currency ids are rejected',
);
assert.deepEqual(
  resolveCollectionAggregateCurrencyIdentity(monetaryAggregate, 'currency_id', [
    { currency_id: { id: 1, symbol: '¥' } },
  ]),
  { id: 1, label: '¥' },
  'currency relation objects require and preserve record identity',
);

// api.data.list always declares the grouped page size; the consumer refuses
// to invent one, so the fixture must carry the declaration the response has.
const declaredGroupPaging = { page_size: 3 };

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
  groupPagingRaw: declaredGroupPaging,
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
  groupPagingRaw: declaredGroupPaging,
  groupSampleLimit: 3,
  groupPageOffsets: {},
  emptyLabel: '未分组',
  buildGroupKey: () => 'fallback',
  normalizeGroupPageOffset: (offset) => offset,
});
assert.equal(groupedRowWithoutAuthority?.aggregates, undefined);

console.log('[collection_aggregate_presentation_test] PASS cases=19');
