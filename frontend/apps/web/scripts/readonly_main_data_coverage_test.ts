import assert from 'node:assert/strict';
import { readonlyMainDataCoversFields } from '../src/pages/contractForm/readonlyMainDataCoverage';

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

console.log('[readonly-main-data-coverage] PASS cases=4');
