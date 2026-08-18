#!/usr/bin/env node
'use strict';

const path = require('path');
const { pathToFileURL } = require('url');

function assertEqual(label, actual, expected) {
  const ok = JSON.stringify(actual) === JSON.stringify(expected);
  if (!ok) {
    console.error(`FAIL: ${label} -> expected=${JSON.stringify(expected)} actual=${JSON.stringify(actual)}`);
    return false;
  }
  console.log(`PASS: ${label}`);
  return true;
}

async function main() {
  const modulePath = path.resolve(__dirname, '../../frontend/apps/web/src/app/resolvers/sceneRegistryCore.js');
  const moduleUrl = pathToFileURL(modulePath).href;
  const { validateSceneRegistry } = await import(moduleUrl);

  let ok = true;

  const LAYOUT = { kind: 'list', sidebar: 'fixed', header: 'full' };
  const scenes = [
    { key: 'alpha', label: 'Alpha', route: '/alpha', target: { route: '/alpha' }, layout: LAYOUT },
    { key: 'alpha', label: 'DupKey', route: '/beta', target: { route: '/beta' }, layout: LAYOUT },
    { key: 'beta', label: 'DupRoute', route: '/alpha', target: { route: '/alpha' }, layout: LAYOUT },
    { key: 'gamma', label: '', route: '/gamma', target: { route: '/gamma' }, layout: LAYOUT },
  ];

  const result = validateSceneRegistry(scenes);

  ok = assertEqual('invalid scenes count', result.errors.length, 3) && ok;
  ok = assertEqual('valid scenes count', result.validScenes.length, 1) && ok;

  if (!ok) {
    process.exit(1);
  }
}

main().catch((err) => {
  console.error(`FAIL: ${err.message}`);
  process.exit(1);
});
