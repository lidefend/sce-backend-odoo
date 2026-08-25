import { strict as assert } from 'node:assert';
import { resolveCollectionAggregateEntry } from '../src/app/presentation/collectionAggregatePresentation';

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

console.log('[collection_aggregate_presentation_test] PASS cases=5');
