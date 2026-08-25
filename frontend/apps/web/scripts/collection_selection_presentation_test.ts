import assert from 'node:assert/strict';
import { resolveCollectionSelectionPresentation } from '../src/app/presentation/collectionSelectionPresentation';

assert.deepEqual(resolveCollectionSelectionPresentation({ checked: false }), { state: 'unchecked', interactive: true });
assert.deepEqual(resolveCollectionSelectionPresentation({ checked: true }), { state: 'checked', interactive: true });
assert.deepEqual(resolveCollectionSelectionPresentation({ checked: false, indeterminate: true }), { state: 'mixed', interactive: true });
assert.deepEqual(resolveCollectionSelectionPresentation({ checked: true, indeterminate: true }), { state: 'mixed', interactive: true });
assert.deepEqual(resolveCollectionSelectionPresentation({ checked: true, disabled: true }), { state: 'checked', interactive: false });
console.log('[collection_selection_presentation_test] PASS cases=5');
