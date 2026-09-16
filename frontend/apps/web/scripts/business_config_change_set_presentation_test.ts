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

import { effectiveConfigurationLabel } from '../src/views/businessConfigSurface/effectiveConfiguration';
const effective = (rows: unknown[]) => ({ formStructureContract: { sourceAuthority: { governance_source: { businessConfigContracts: rows } } } });
assert.match(effectiveConfigurationLabel(effective([]), 'form'), /使用默认配置/);
assert.equal(effectiveConfigurationLabel(effective([{ id: 7, version_no: 2 }, { id: 8, version_no: 15 }]), 'form'), '表单新建态：配置 #7 · v2；配置 #8 · v15');
assert.match(effectiveConfigurationLabel({ snapshot_summary: { status_counts: { published: 258 } } }, 'form'), /尚未核验/);
assert.match(effectiveConfigurationLabel({ runtimeContract: { governance: { view_orchestration: { views: { tree: { business_config_contracts: [] } } } } } }, 'tree'), /使用默认配置/);
assert.match(effectiveConfigurationLabel(effective([{ id: 7, version_no: 2 }]), 'form', { '7': 'product_default' }), /使用默认配置；产品默认 #7 · v2/);
const legacy = effective([]);
Object.assign(legacy.formStructureContract.sourceAuthority.governance_source, { legacyFieldPolicyOverlay: true });
assert.match(effectiveConfigurationLabel(legacy, 'form'), /字段策略覆盖/);
console.log('[configuration_summary] PASS cases=6');
