import assert from 'node:assert/strict';
import { resolveSavedSearchMutationCapability as favorite } from '../src/app/action_runtime/useActionViewFilterComputedRuntime';
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
const grant = { save_enabled: true, shared_enabled: false, intent: 'search.favorite.set' };
assert.equal(favorite(undefined).saveEnabled, false);
assert.equal(favorite({}).declared, false);
assert.equal(favorite({ ...grant, save_enabled: 'true' }).saveEnabled, false);
assert.equal(favorite(grant).saveEnabled, true);
assert.equal(favorite(grant).sharedEnabled, false);
assert.equal(favorite({ ...grant, shared_enabled: true }).sharedEnabled, true);
assert.equal(favorite({ ...grant, save_enabled: false, shared_enabled: true }).sharedEnabled, false);
assert.equal(favorite({ ...grant, intent: '' }).saveEnabled, false);
assert.equal(favorite({ ...grant, intent: 'other.write' }).saveEnabled, false);
assert.equal(favorite({ ...grant, save_enabled: false, disabled_reason: 'SAVED_SEARCH_CREATE_DENIED' }).disabledReason, '没有保存收藏的权限');
console.log('[collection_action_settlement_test] PASS cases=16');
