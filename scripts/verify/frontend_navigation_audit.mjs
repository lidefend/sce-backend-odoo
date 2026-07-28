#!/usr/bin/env node

import fs from 'node:fs';

export function stableLeafKey(row) {
  return [row?.menu_xmlid, row?.action_xmlid, row?.model]
    .map((value) => String(value || '').trim())
    .join('|');
}

function duplicates(values) {
  const counts = new Map();
  for (const value of values) counts.set(value, (counts.get(value) || 0) + 1);
  return [...counts.entries()].filter(([, count]) => count > 1).map(([value]) => value).sort();
}

export function compareNavigation(manifest, rows, roleLogins) {
  const reports = {};
  for (const login of roleLogins) {
    const role = String(login || '').replace(/^(?:demo|fixture)_role_/, '');
    const expected = manifest?.roles?.[role];
    if (!expected) throw new Error(`NAVIGATION_MANIFEST_ROLE_MISSING:${role}`);
    const expectedKeys = [...(expected.leaf_keys || [])].sort();
    const actualKeys = rows.filter((row) => row.role === login).map(stableLeafKey).sort();
    const invalid = actualKeys.filter((key) => key.split('|').some((part) => !part));
    const expectedSet = new Set(expectedKeys);
    const actualSet = new Set(actualKeys);
    const missing = expectedKeys.filter((key) => !actualSet.has(key));
    const unexpected = [...actualSet].filter((key) => !expectedSet.has(key)).sort();
    const duplicate = duplicates(actualKeys);
    const matched = expectedKeys.filter((key) => actualSet.has(key)).length;
    const result = (
      Number(expected.expected_count) === expectedKeys.length
      && actualKeys.length === expectedKeys.length
      && !missing.length
      && !unexpected.length
      && !duplicate.length
      && !invalid.length
    ) ? 'PASS' : 'FAIL';
    reports[role] = {
      expected_count: expectedKeys.length,
      actual_count: actualKeys.length,
      matched_count: matched,
      missing_leaf_keys: missing,
      unexpected_leaf_keys: unexpected,
      duplicate_leaf_keys: duplicate,
      invalid_leaf_keys: invalid,
      result,
    };
  }
  const totals = Object.values(reports).reduce((out, row) => ({
    expected_count: out.expected_count + row.expected_count,
    actual_count: out.actual_count + row.actual_count,
    matched_count: out.matched_count + row.matched_count,
  }), { expected_count: 0, actual_count: 0, matched_count: 0 });
  return {
    schema_version: manifest.schema_version,
    source: manifest.source,
    identity: manifest.identity,
    roles: reports,
    total: {
      ...totals,
      result: Object.values(reports).every((row) => row.result === 'PASS') ? 'PASS' : 'FAIL',
    },
  };
}

export function loadNavigationManifest(path) {
  const manifest = JSON.parse(fs.readFileSync(path, 'utf8'));
  if (manifest?.schema_version !== 'frontend-authoritative-navigation/v1') {
    throw new Error('NAVIGATION_MANIFEST_SCHEMA_INVALID');
  }
  return manifest;
}
