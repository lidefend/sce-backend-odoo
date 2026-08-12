#!/usr/bin/env node

import assert from 'node:assert/strict';
import { compareNavigation } from './frontend_navigation_audit.mjs';

const keyA = 'module.menu_a|module.action_a|model.a';
const keyB = 'module.menu_b|module.action_b|model.b';
const manifest = {
  schema_version: 'frontend-authoritative-navigation/v1',
  source: { kind: 'fixture', source_sha: 'a'.repeat(40) },
  identity: 'menu_xmlid|action_xmlid|model',
  roles: { finance: {
    expected_count: 2,
    leaf_keys: [keyA, keyB],
    browser_expected_count: 1,
    browser_leaf_keys: [keyA],
  } },
};
const row = (key) => {
  const [menu_xmlid, action_xmlid, model] = key.split('|');
  return { role: 'fixture_role_finance', menu_xmlid, action_xmlid, model };
};

assert.equal(compareNavigation(manifest, [row(keyA)], ['fixture_role_finance']).total.result, 'PASS');
const missing = compareNavigation(manifest, [], ['fixture_role_finance']);
assert.equal(missing.total.result, 'FAIL');
assert.deepEqual(missing.roles.finance.missing_leaf_keys, [keyA]);
const unexpected = compareNavigation(manifest, [row(keyA), row('module.menu_c|module.action_c|model.c')], ['fixture_role_finance']);
assert.equal(unexpected.roles.finance.unexpected_leaf_keys.length, 1);
const duplicate = compareNavigation(manifest, [row(keyA), row(keyA)], ['fixture_role_finance']);
assert.deepEqual(duplicate.roles.finance.duplicate_leaf_keys, [keyA]);
console.log('[frontend_navigation_audit.test] PASS missing unexpected duplicate fail closed');
