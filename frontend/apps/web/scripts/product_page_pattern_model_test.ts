import { strict as assert } from 'node:assert';
import { resolveProductPagePatternModel, type ProductPagePatternModel } from '../src/app/presentation/productPagePattern';

const valid: ProductPagePatternModel[] = [
  { key: 'task-form', presentationMode: 'task', renderProfile: 'create' },
  { key: 'task-form', presentationMode: 'task', renderProfile: 'edit' },
  { key: 'task-form', presentationMode: 'task', renderProfile: 'readonly' },
  { key: 'workspace-form', presentationMode: 'workspace', renderProfile: 'create' },
  { key: 'workspace-form', presentationMode: 'workspace', renderProfile: 'edit' },
  { key: 'workspace-form', presentationMode: 'workspace', renderProfile: 'readonly' },
  { key: 'collection', presentationMode: 'collection', renderProfile: 'readonly' },
  { key: 'dashboard', presentationMode: 'dashboard', renderProfile: 'readonly' },
];
for (const model of valid) assert.deepEqual(resolveProductPagePatternModel(model), model);
assert.throws(() => resolveProductPagePatternModel({ key: 'task-form', presentationMode: 'workspace', renderProfile: 'edit' }), /MODE_MISMATCH/);
assert.throws(() => resolveProductPagePatternModel({ key: 'workspace-form', presentationMode: 'task', renderProfile: 'readonly' }), /MODE_MISMATCH/);
assert.throws(() => resolveProductPagePatternModel({ key: 'collection', presentationMode: 'collection', renderProfile: 'edit' }), /PROFILE_MISMATCH/);
assert.throws(() => resolveProductPagePatternModel({ key: 'dashboard', presentationMode: 'dashboard', renderProfile: 'create' }), /PROFILE_MISMATCH/);
console.log('[product_page_pattern_model_test] PASS cases=12');
