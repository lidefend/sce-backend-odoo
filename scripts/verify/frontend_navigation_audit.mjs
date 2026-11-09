#!/usr/bin/env node

import fs from 'node:fs';

export function stableLeafKey(row) {
  return [row?.menu_xmlid, row?.action_xmlid, row?.model]
    .map((value) => String(value || '').trim())
    .join('|');
}

export function isDeclaredScene(manifest, row) {
  const target = manifest?.scene_targets?.[row?.menu_xmlid];
  return Boolean(target?.scene_key && target?.route
    && !row?.action_xmlid && !row?.model
    && row?.route === target.route);
}

function invalidNavigationRow(row) {
  const menu = String(row?.menu_xmlid || '').trim();
  const action = String(row?.action_xmlid || '').trim();
  const model = String(row?.model || '').trim();
  const route = String(row?.route || '').trim();
  if (!menu) return true;
  if (Boolean(action) !== Boolean(model)) return true;
  if (!action && !route.startsWith('/s/')) return true;
  return false;
}

export function observeNavigation(rows, roleLogins) {
  const reports = {};
  for (const login of roleLogins) {
    const role = String(login || '').replace(/^(?:demo|fixture)_role_/, '');
    const roleRows = rows.filter((row) => row.role === login);
    const actualKeys = roleRows.map(stableLeafKey).sort();
    const invalid = roleRows
      .filter(invalidNavigationRow)
      .map(stableLeafKey)
      .sort();
    const duplicate = duplicates(actualKeys);
    reports[role] = {
      actual_count: actualKeys.length,
      duplicate_leaf_keys: duplicate,
      invalid_leaf_keys: invalid,
      result: actualKeys.length > 0 && !duplicate.length && !invalid.length ? 'PASS' : 'FAIL',
    };
  }
  const totalActual = Object.values(reports).reduce((sum, row) => sum + row.actual_count, 0);
  return {
    schema_version: 'frontend-navigation-observation/v1',
    source: 'authenticated_runtime_navigation',
    identity: 'menu_xmlid|action_xmlid|model',
    roles: reports,
    total: {
      actual_count: totalActual,
      result: totalActual > 0 && Object.values(reports).every((row) => row.result === 'PASS') ? 'PASS' : 'FAIL',
    },
  };
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
    const expectedKeys = [...(expected.browser_leaf_keys || expected.leaf_keys || [])].sort();
    const actualKeys = rows.filter((row) => row.role === login).map(stableLeafKey).sort();
    const invalid = rows.filter((row) => row.role === login)
      .filter((row) => stableLeafKey(row).split('|').some((part) => !part)
        && !isDeclaredScene(manifest, row)).map(stableLeafKey).sort();
    const expectedSet = new Set(expectedKeys);
    const actualSet = new Set(actualKeys);
    const missing = expectedKeys.filter((key) => !actualSet.has(key));
    const unexpected = [...actualSet].filter((key) => !expectedSet.has(key)).sort();
    const duplicate = duplicates(actualKeys);
    const matched = expectedKeys.filter((key) => actualSet.has(key)).length;
    const result = (
      Number(expected.browser_expected_count ?? expected.expected_count) === expectedKeys.length
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
