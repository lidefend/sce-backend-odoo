import assert from 'node:assert/strict';
import { resolveCollectionBatchActionSettlement } from '../src/app/presentation/collectionActionSettlement';

const actions = [
  { key: 'archive', label: '归档', enabled: true },
  { key: 'export', label: '导出', enabled: true },
  { key: 'delete', label: '删除', enabled: false, hint: '无删除权限' },
];
const result = resolveCollectionBatchActionSettlement(actions);
assert.deepEqual(result.direct.map((action) => action.key), ['archive']);
assert.deepEqual(result.overflow.map((action) => action.key), ['export', 'delete']);
assert.deepEqual(result.actionKeys, ['archive', 'export', 'delete']);
assert.equal(result.overflow[1]?.enabled, false);
assert.throws(
  () => resolveCollectionBatchActionSettlement([...actions, actions[0]!]),
  /COLLECTION_BATCH_ACTION_IDENTITY_DUPLICATE/,
);
assert.throws(
  () => resolveCollectionBatchActionSettlement([{ key: '', label: '无身份', enabled: true }]),
  /COLLECTION_BATCH_ACTION_IDENTITY_REQUIRED/,
);
console.log('[collection_action_settlement_test] PASS cases=6');
