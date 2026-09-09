import assert from 'node:assert/strict';
import { resolveBusinessConfigChangeSetPresentation } from '../src/views/businessConfigSurface/changeSetPresentation';
import type { BusinessConfigChangeSet, BusinessConfigChangeSetState } from '../src/api/businessConfig';

function changeSet(state: BusinessConfigChangeSetState, itemCount: number, failureMessage = ''): BusinessConfigChangeSet {
  return {
    id: 1,
    token: 'test-token',
    state,
    name: 'test',
    user_id: 1,
    company_id: 1,
    role_key: '',
    database_name: 'test',
    expires_at: '',
    published_at: '',
    failure_message: failureMessage,
    item_count: itemCount,
    items: Array.from({ length: itemCount }, (_, index) => ({
      id: index + 1,
      config_type: 'form' as const,
      target_key: `target-${index}`,
      model: 'test.model',
      view_type: 'form',
      action_id: 1,
      view_id: 1,
      role_key: '',
      current_contract_id: 0,
      current_version: 0,
      current_payload_hash: '',
      diff_summary: {},
      reversible: true,
      risk_level: 'low' as const,
      validation_result: {},
      publish_result: {},
    })),
    publish_result: {},
  };
}

const loading = resolveBusinessConfigChangeSetPresentation(null, { loading: true });
assert.equal(loading.kind, 'loading');
assert.equal(loading.statusLabel, '读取中');

const empty = resolveBusinessConfigChangeSetPresentation(changeSet('draft', 0));
assert.equal(empty.kind, 'empty');
assert.equal(empty.title, '当前没有未发布修改');
assert.equal(empty.statusLabel, '无待发布修改');
assert.equal(empty.canDiscard, false);

const draft = resolveBusinessConfigChangeSetPresentation(changeSet('draft', 2));
assert.equal(draft.kind, 'draft');
assert.equal(draft.statusLabel, '有未发布修改');
assert.equal(draft.canPublish, true);

const publishing = resolveBusinessConfigChangeSetPresentation(changeSet('ready', 2), { publishing: true });
assert.equal(publishing.kind, 'draft');
assert.equal(publishing.statusLabel, '发布中');
assert.equal(publishing.canPublish, false);
assert.equal(publishing.canDiscard, false);

const failed = resolveBusinessConfigChangeSetPresentation(changeSet('failed', 1, '字段校验失败'));
assert.equal(failed.kind, 'failed');
assert.equal(failed.description, '字段校验失败');
assert.equal(failed.canPublish, false);
assert.equal(failed.canValidate, true);

const readFailure = resolveBusinessConfigChangeSetPresentation(null, { requestError: '读取失败' });
assert.equal(readFailure.kind, 'failed');
assert.equal(readFailure.canRetryLoad, true);

const published = resolveBusinessConfigChangeSetPresentation(changeSet('published', 2));
assert.equal(published.kind, 'published');
assert.equal(published.statusLabel, '已发布');
assert.equal(published.canRollback, true);
assert.equal(published.canDiscard, false);

console.log('[business_config_change_set_presentation_test] PASS cases=7');
