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
const {
  contractLoadProfileOptions,
  resolveEffectiveContractRenderProfile,
  resolveRequestedContractRenderProfile,
} = await import(moduleUrl);

assert.deepEqual(contractLoadProfileOptions('readonly'), { renderProfile: 'readonly' });

assert.equal(resolveRequestedContractRenderProfile({
  routeName: 'record', recordId: 41,
}), 'readonly', '/r/:model/:id must remain readonly even when a stale contract says edit');

assert.equal(resolveRequestedContractRenderProfile({
  routeName: 'model-form', recordId: 41,
}), 'edit', '/f/:model/:id must request edit from the current route identity');

assert.equal(resolveRequestedContractRenderProfile({
  routeName: 'model-form', recordId: null,
}), 'create', '/f/:model/new must request create from the current route identity');

assert.equal(resolveEffectiveContractRenderProfile({
  backendProfile: 'readonly', normalizedReady: true, requestedProfile: 'edit',
}), 'readonly', 'backend record/view/entry denial must downgrade an /f/:model/:id edit request');

assert.equal(resolveEffectiveContractRenderProfile({
  backendProfile: '', normalizedReady: true, requestedProfile: 'edit',
}), 'readonly', 'a normalized contract without a backend profile verdict must fail closed');

assert.equal(resolveEffectiveContractRenderProfile({
  backendProfile: '', normalizedReady: false, requestedProfile: 'create',
}), 'create', 'before the response arrives the route-derived request profile remains available');

console.log('[frontend_contract_render_profile_test] PASS');
