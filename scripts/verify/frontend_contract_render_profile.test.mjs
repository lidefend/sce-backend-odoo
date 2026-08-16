#!/usr/bin/env node

import assert from 'node:assert/strict';
import path from 'node:path';
import { build } from '../../frontend/apps/web/node_modules/esbuild/lib/main.js';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '../..');
const entry = path.join(root, 'frontend/apps/web/src/pages/contractForm/contractRenderProfile.ts');
const output = await build({
  entryPoints: [entry],
  bundle: true,
  format: 'esm',
  platform: 'node',
  write: false,
});
const source = output.outputFiles[0].text;
const moduleUrl = `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`;
const { contractLoadProfileOptions, resolveContractRenderProfile } = await import(moduleUrl);

assert.deepEqual(contractLoadProfileOptions('readonly'), { renderProfile: 'readonly' });

assert.equal(resolveContractRenderProfile({
  routeName: 'record', contractProfile: 'edit', canSave: true, recordId: 41,
}), 'readonly', '/r/:model/:id must remain readonly even when a stale contract says edit');

assert.equal(resolveContractRenderProfile({
  routeName: 'model-form', contractProfile: 'readonly', canSave: true, recordId: 41,
}), 'edit', '/f/:model/:id must request edit from the current route identity');

assert.equal(resolveContractRenderProfile({
  routeName: 'model-form', contractProfile: 'create', canSave: true, recordId: 41,
}), 'edit', 'a saved record must not inherit the preceding create contract profile');

assert.equal(resolveContractRenderProfile({
  routeName: 'model-form', contractProfile: 'edit', canSave: true, recordId: null,
}), 'create', '/f/:model/new must request create from the current route identity');

assert.equal(resolveContractRenderProfile({
  routeName: 'contract-preview', contractProfile: 'readonly', canSave: true, recordId: 41,
}), 'readonly', 'non-record preview routes may still consume an explicit contract profile');

console.log('[frontend_contract_render_profile_test] PASS');
