import assert from 'node:assert/strict';
import fs from 'node:fs';
import { readonlyMainDataCoversFields } from '../src/pages/contractForm/readonlyMainDataCoverage';
import {
  contractLoadProfileOptions,
  resolveContractRenderProfile,
} from '../src/pages/contractForm/contractRenderProfile';

assert.equal(readonlyMainDataCoversFields({
  renderProfile: 'readonly',
  fieldNames: ['id', 'name', 'status'],
  mainData: { id: 7, name: 'Document A', status: 'approved' },
}), true);

assert.equal(readonlyMainDataCoversFields({
  renderProfile: 'readonly',
  fieldNames: ['id', 'name', 'status'],
  mainData: { id: 7, name: 'Document A' },
}), false);

assert.equal(readonlyMainDataCoversFields({
  renderProfile: 'edit',
  fieldNames: ['id'],
  mainData: { id: 7 },
}), false);

assert.equal(readonlyMainDataCoversFields({
  renderProfile: 'readonly',
  fieldNames: [],
  mainData: { id: 7 },
}), false);

assert.equal(resolveContractRenderProfile({
  routeName: 'record',
  contractProfile: 'edit',
  canSave: true,
  recordId: 7,
}), 'readonly');

assert.equal(resolveContractRenderProfile({
  routeName: 'model-form',
  canSave: true,
  recordId: 7,
}), 'edit');

assert.equal(resolveContractRenderProfile({
  routeName: 'model-form',
  canSave: true,
  recordId: null,
}), 'create');

assert.equal(resolveContractRenderProfile({
  routeName: 'model-form',
  contractProfile: 'readonly',
  canSave: true,
  recordId: 7,
}), 'edit', 'the current /f/:model/:id route outranks a stale readonly contract profile');

assert.deepEqual(contractLoadProfileOptions('readonly'), { renderProfile: 'readonly' });

const lifecycleSource = fs.readFileSync(
  'frontend/apps/web/src/pages/contractForm/useRecordPageLifecycle.ts',
  'utf8',
);
assert.equal((lifecycleSource.match(/\.\.\.profileOptions/g) || []).length, 2);
assert.doesNotMatch(lifecycleSource, /recordId\.value\s*\?\s*['"]edit['"]\s*:\s*['"]create['"]/);

console.log('[readonly-main-data-coverage] PASS cases=11');
