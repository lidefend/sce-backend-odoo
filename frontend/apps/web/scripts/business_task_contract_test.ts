import assert from 'node:assert/strict';

import {
  decodeBusinessTaskContractV1,
  presentBusinessTaskContract,
} from '../src/app/contracts/v2/businessTaskContract';
import { decodeContractV2Snapshot, ContractV2DecodeError } from '../src/app/contracts/v2/schema';
import { createContractV2Store, resolveContractV2BusinessTaskPresentation } from '../src/app/contracts/v2/store';

const sha = 'a'.repeat(64);
const terminal = () => ({
  profile_version: 'v1',
  task: {
    key: 'document.review', goal: 'Review the document', outcome: 'Document is decided',
    mode: 'readonly', stage: 'approval', state: 'pending',
  },
  facts: [
    { key: 'identity', label: 'Document', importance: 'primary', group: 'identity', value: 'DOC-1', value_state: 'ready', source_authority: 'domain.fact', applicability: 'applicable' },
    { key: 'legacy', label: 'Legacy fact', importance: 'secondary', group: 'detail', value: null, value_state: 'empty', source_authority: 'domain.fact', applicability: 'not_applicable' },
  ],
  inputs: [
    { key: 'comment', label: 'Comment', group: 'decision', input_kind: 'multiline', value: '', visible: true, readonly: false, required: false, source_authority: 'canonical.widget_status', applicability: 'applicable' },
    { key: 'internal', label: 'Internal', group: 'decision', input_kind: 'text', value: '', visible: false, readonly: true, required: false, source_authority: 'canonical.widget_status', applicability: 'applicable' },
  ],
  blockers: [],
  capabilities: [
    { key: 'document.approve', label: 'Approve', presentation: 'primary', safety: 'confirm', idempotency: 'record_transition', outcome: 'approved', blocked_by: [], handoff: 'approver', visible: true, business_available: true, authorization_allowed: false, enabled: false, reason_code: 'ROLE_HANDOFF_REQUIRED', reason: 'Approver required', source_authority: 'canonical.action_contract' },
    { key: 'document.archive', label: 'Archive', presentation: 'secondary', safety: 'confirm', idempotency: 'record_transition', outcome: 'archived', blocked_by: [], visible: false, business_available: false, authorization_allowed: true, enabled: false, reason_code: 'STATE_NOT_APPLICABLE', reason: 'Wrong state', source_authority: 'canonical.action_contract' },
  ],
  evidence: [
    { key: 'attachments', label: 'Evidence', kind: 'attachment', group: 'evidence', state: 'ready', count: 1, required: true, source_authority: 'domain.evidence' },
  ],
  relations: [
    { key: 'source', label: 'Source', kind: 'anchor', group: 'source', state: 'linked', count: 1, summary: 'Origin', source_authority: 'domain.relation' },
  ],
  completion: { complete: false, next_capability_key: 'document.approve', outcome_code: 'PENDING_APPROVAL' },
  trace: {
    compiler: 'smart_scene.business_task_scene_compiler.v1', profile_key: 'document.review',
    profile_sha256: sha, semantic_supply_sha256: sha, source_authorities: ['canonical.action_contract'],
    sealed_contract_sha256: sha,
  },
});

const issues: Array<{ path: string; message: string }> = [];
const decoded = decodeBusinessTaskContractV1(terminal(), issues);
assert.ok(decoded);
assert.deepEqual(issues, []);
assert.equal(decoded.profileVersion, 'v1');
assert.equal(decoded.capabilities[0].authorizationAllowed, false);
assert.equal(decoded.completion.nextCapabilityKey, 'document.approve');

const presentation = presentBusinessTaskContract(decoded);
assert.deepEqual(presentation.facts.map((row) => row.key), ['identity']);
assert.deepEqual(presentation.inputs.map((row) => row.key), ['comment']);
assert.deepEqual(presentation.capabilities.map((row) => row.key), ['document.approve']);
assert.equal(presentation.primaryCapability, null);
assert.equal(presentation.nextCapability?.key, 'document.approve');
assert.equal(presentation.nextCapability?.enabled, false);

const snapshot = (businessTaskContract: unknown) => ({
  pageInfo: {
    pageId: 'x.document.form', sceneKey: 'x.document.task', pageName: 'Document', model: 'x.document',
    viewType: 'form', layoutType: 'form', renderMode: 'governed', contractVersion: '2.2.0', clientType: 'web_pc',
  },
  layoutContract: { pageId: 'x.document.form', layoutType: 'form', adaptMode: 'pc', containerTree: [], layoutHints: {}, componentRegistry: {} },
  statusContract: { globalStatus: { pageVisible: true }, widgetStatus: [], buttonStatus: [], containerStatus: [], selectorStatus: [] },
  actionContract: { actionRuleList: [], dependencyGraph: {} },
  dataContract: { mainData: {}, tableRows: {}, relationRows: {}, dictData: {}, pagination: {}, dataSource: {}, dataMeta: {} },
  runtimeContract: {
    patchStrategy: 'incremental', cachePolicy: 'etag', optimistic: false, lazyContainer: [], virtualization: {}, retryPolicy: {},
    businessTaskContract,
  },
  meta: {
    etag: 'test', snapshotId: 'snapshot.test', traceId: 'trace.test', requestId: 'request.test', sourceType: 'ui.contract',
    lifecycle: {
      lifecycleVersion: '1.0.0', stage: 'runtime_delivery',
      definition: { schemaId: 'smart_core.unified_page_contract_v2', schemaVersion: '2.2.0', schemaSha256: 'test', contractVersion: '2.2.0', normativeStatus: 'stable' },
      generation: { generator: 'test', generatorVersion: '2.2.0', sourceType: 'ui.contract', sourceSha256: 'test' },
      runtime: { requestId: 'request.test', traceId: 'trace.test', clientType: 'web_pc', traceSource: 'request_context' },
      integrity: { algorithm: 'sha256', contractSha256: 'test' }, authority: {},
    },
  },
});

const store = createContractV2Store(decodeContractV2Snapshot(snapshot(terminal())));
assert.equal(resolveContractV2BusinessTaskPresentation(store)?.task.key, 'document.review');
assert.equal(resolveContractV2BusinessTaskPresentation(store)?.nextCapability?.enabled, false);

const expectRejected = (mutate: (payload: ReturnType<typeof terminal>) => void, message: string) => {
  const payload = terminal();
  mutate(payload);
  assert.throws(
    () => decodeContractV2Snapshot(snapshot(payload)),
    (error: unknown) => error instanceof ContractV2DecodeError
      && error.issues.some((issue) => issue.message.includes(message)),
  );
};

expectRejected((payload) => {
  (payload.facts[0].value as unknown) = { adapter: { resModel: 'x.secret' } };
}, 'native adapter vocabulary is forbidden');
expectRejected((payload) => {
  payload.capabilities[0].enabled = true;
}, 'inconsistent with authoritative verdicts');
expectRejected((payload) => {
  payload.capabilities[0].reason_code = 'OK';
}, 'must explain a disabled capability');
expectRejected((payload) => {
  payload.capabilities.push({ ...payload.capabilities[0], key: 'document.second', authorization_allowed: true, enabled: true });
  payload.capabilities[0].authorization_allowed = true;
  payload.capabilities[0].enabled = true;
}, 'multiple enabled primary capabilities');
expectRejected((payload) => {
  payload.inputs[0].visible = false;
  payload.inputs[0].required = true;
}, 'hidden input cannot be required');
expectRejected((payload) => {
  payload.trace.profile_sha256 = 'not-a-seal';
}, 'sha256 fields must contain 64 hexadecimal characters');

console.log('business task contract frontend tests passed');
