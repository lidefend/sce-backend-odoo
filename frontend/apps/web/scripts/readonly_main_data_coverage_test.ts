import assert from 'node:assert/strict';
import fs from 'node:fs';
import { readonlyMainDataCoversFields } from '../src/pages/contractForm/readonlyMainDataCoverage';
import {
  contractLoadProfileOptions,
  resolveEffectiveContractRenderProfile,
  resolveRequestedContractRenderProfile,
} from '../src/pages/contractForm/contractRenderProfile';
import {
  resolveContractV2EffectiveFormCapabilities,
} from '../src/app/contracts/v2/store';

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

assert.equal(resolveRequestedContractRenderProfile({
  routeName: 'record',
  recordId: 7,
}), 'readonly');

assert.equal(resolveRequestedContractRenderProfile({
  routeName: 'model-form',
  recordId: 7,
}), 'edit');

assert.equal(resolveRequestedContractRenderProfile({
  routeName: 'model-form',
  recordId: null,
}), 'create');

assert.equal(resolveEffectiveContractRenderProfile({
  backendProfile: 'readonly',
  normalizedReady: true,
  requestedProfile: 'edit',
}), 'readonly', 'backend effective profile must downgrade an /f/:model/:id edit request');
assert.equal(resolveEffectiveContractRenderProfile({
  backendProfile: '',
  normalizedReady: true,
  requestedProfile: 'edit',
}), 'readonly', 'missing normalized verdict must fail closed instead of forcing /f/:id to edit');

assert.deepEqual(contractLoadProfileOptions('readonly'), { renderProfile: 'readonly' });

const authoritativeCapabilities = {
  effective: { read: true, write: false, create: true, unlink: true, duplicate: false },
};
assert.deepEqual(resolveContractV2EffectiveFormCapabilities({
  snapshot: { statusContract: { globalStatus: { effectiveRecordCapabilities: authoritativeCapabilities.effective } } },
} as never), { read: true, write: false, create: true, unlink: true, duplicate: false });
assert.equal(resolveContractV2EffectiveFormCapabilities({
  snapshot: { statusContract: { globalStatus: { effectiveRecordCapabilities: {} } } },
} as never), null, 'missing backend verdict must not be reconstructed by the frontend');

const lifecycleSource = fs.readFileSync(
  'frontend/apps/web/src/pages/contractForm/useRecordPageLifecycle.ts',
  'utf8',
);
assert.equal((lifecycleSource.match(/\.\.\.profileOptions/g) || []).length, 2);
assert.doesNotMatch(lifecycleSource, /recordId\.value\s*\?\s*['"]edit['"]\s*:\s*['"]create['"]/);

console.log('[readonly-main-data-coverage] PASS cases=14');
