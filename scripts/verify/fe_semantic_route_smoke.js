#!/usr/bin/env node
'use strict';

// Semantic route smoke. The retired static frontend scene config
// (frontend/apps/web/src/config/scenesCore.js) was replaced by the
// backend-driven scene registry; well-known semantic routes are now pinned
// in sceneRegistry.ts SCENE_ROUTE_OVERRIDES. This smoke asserts those pins
// statically so accidental removal is caught.

const fs = require('fs');
const path = require('path');

const file = path.resolve(__dirname, '../../frontend/apps/web/src/app/resolvers/sceneRegistry.ts');
const src = fs.readFileSync(file, 'utf8');

function assertContains(label, snippet) {
  if (!src.includes(snippet)) {
    throw new Error(`${label} missing: ${snippet}`);
  }
  console.log(`PASS: ${label}`);
}

function main() {
  assertContains('workspace.home semantic route pinned', "'workspace.home': '/s/workspace.home'");
  assertContains('my_work.workspace semantic route pinned', "'my_work.workspace': '/my-work'");
  assertContains('scene route override resolution kept', 'const override = SCENE_ROUTE_OVERRIDES[code];');
  assertContains('native ui contract prefixes guard kept', "const NATIVE_UI_CONTRACT_ROUTE_PREFIXES = ['/a/', '/f/', '/r/'];");
  console.log('[fe_semantic_route_smoke] PASS');
}

try {
  main();
} catch (err) {
  console.error(`[fe_semantic_route_smoke] FAIL: ${err.message}`);
  process.exit(1);
}
