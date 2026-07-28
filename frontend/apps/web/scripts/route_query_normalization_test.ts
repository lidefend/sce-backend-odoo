import assert from 'node:assert/strict';
import { normalizeEmbeddedSceneQuery } from '../src/app/routeQuery';

const malformedActionQuery = normalizeEmbeddedSceneQuery({
  menu_id: '379&action_id=506&view_mode=tree',
});
assert.equal(malformedActionQuery.changed, true);
assert.deepEqual(malformedActionQuery.query, {
  menu_id: '379',
  action_id: '506',
  view_mode: 'tree',
});

const encodedMalformedActionQuery = normalizeEmbeddedSceneQuery({
  menu_id: '379%26action_id=506%26view_mode=tree',
});
assert.equal(encodedMalformedActionQuery.changed, true);
assert.deepEqual(encodedMalformedActionQuery.query, {
  menu_id: '379',
  action_id: '506',
  view_mode: 'tree',
});

const explicitValuesWin = normalizeEmbeddedSceneQuery({
  menu_id: '379&action_id=999&view_mode=tree',
  action_id: '506',
});
assert.deepEqual(explicitValuesWin.query, {
  menu_id: '379',
  action_id: '506',
  view_mode: 'tree',
});

const canonicalQuery = normalizeEmbeddedSceneQuery({
  menu_id: '379',
  action_id: '506',
  view_mode: 'tree',
});
assert.equal(canonicalQuery.changed, false);
assert.deepEqual(canonicalQuery.query, {
  menu_id: '379',
  action_id: '506',
  view_mode: 'tree',
});

console.log('[route-query-normalization] PASS');
