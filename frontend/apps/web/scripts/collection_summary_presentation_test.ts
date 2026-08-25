import { strict as assert } from 'node:assert';
import { resolveCollectionSummaryTone } from '../src/app/presentation/collectionSummaryPresentation';

for (const tone of ['neutral', 'danger', 'warning', 'success', 'info'] as const) {
  assert.equal(resolveCollectionSummaryTone(tone), tone);
}

assert.equal(resolveCollectionSummaryTone(' danger '), 'danger');
assert.equal(resolveCollectionSummaryTone('critical'), 'neutral');
assert.equal(resolveCollectionSummaryTone(''), 'neutral');
assert.equal(resolveCollectionSummaryTone(null), 'neutral');
assert.equal(resolveCollectionSummaryTone(true), 'neutral');

console.log('[collection_summary_presentation_test] PASS cases=10');
