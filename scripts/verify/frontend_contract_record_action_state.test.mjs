#!/usr/bin/env node
/**
 * A denied record operation must name the authority that denied it.
 *
 * Two facts are proven here, and they are proven separately from the backend
 * producer test:
 *
 * 1. `schema.ts` decodes `statusContract.globalStatus.recordDeniedReasons` and
 *    still refuses an undeclared key, so the projection is a decoded contract
 *    field and not a free-form bag.
 * 2. `store.ts` combines the declared record capability with the delete policy's
 *    declared state gate, and never invents a reason code the contract did not
 *    publish.  Delete stays fail-closed: an undeclared page is not deletable.
 */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { build } from '../../frontend/apps/web/node_modules/esbuild/lib/main.js';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '../..');

async function bundle(relativeEntry) {
  const output = await build({
    entryPoints: [path.join(root, relativeEntry)],
    bundle: true,
    format: 'esm',
    platform: 'node',
    write: false,
  });
  return import(`data:text/javascript;base64,${Buffer.from(output.outputFiles[0].text).toString('base64')}`);
}

const { decodeContractV2Snapshot } = await bundle('frontend/apps/web/src/app/contracts/v2/schema.ts');
const { resolveContractV2RecordActionStates } = await bundle('frontend/apps/web/src/app/contracts/v2/store.ts');

let cases = 0;
function check(fn, message) {
  fn();
  cases += 1;
  void message;
}

const runtimeContract = {
  patchStrategy: 'incremental',
  cachePolicy: 'none',
  optimistic: false,
  lazyContainer: [],
  virtualization: {},
  retryPolicy: { maxRetries: 1 },
};

function snapshot(globalStatus) {
  return {
    pageInfo: {
      pageId: 'contract.form', sceneKey: 'contract.form', pageName: 'Contract', model: 'sc.general.contract',
      viewType: 'form', layoutType: 'form', renderMode: 'governed', contractVersion: '2.2.0', clientType: 'web_pc',
    },
    layoutContract: { pageId: 'contract.form', layoutType: 'form', adaptMode: 'pc', containerTree: [], layoutHints: {}, componentRegistry: {} },
    statusContract: {
      globalStatus,
      containerStatus: [], widgetStatus: [], buttonStatus: [], selectorStatus: [],
    },
    actionContract: { actionRuleList: [], dependencyGraph: {} },
    dataContract: { mainData: {}, tableRows: {}, relationRows: {}, dictData: {}, pagination: {}, dataSource: {}, dataMeta: {} },
    runtimeContract,
    meta: {
      etag: 'test', snapshotId: 'test', traceId: 'test', requestId: 'test', sourceType: 'test',
      lifecycle: {
        lifecycleVersion: '1', stage: 'sealed',
        definition: { schemaId: 'v2', schemaVersion: '2', schemaSha256: 'schema', contractVersion: '2', normativeStatus: 'active' },
        generation: { generator: 'test', generatorVersion: '1', sourceType: 'test', sourceSha256: 'source' },
        runtime: { requestId: 'test', traceId: 'test', clientType: 'web_pc', traceSource: 'test' },
        integrity: { algorithm: 'sha256', contractSha256: 'contract' }, authority: {},
      },
    },
  };
}

// 1. The decoder keeps the published reasons and still rejects an undeclared key.
const decoded = decodeContractV2Snapshot(snapshot({
  pageVisible: true,
  pageAuth: 'read',
  effectiveRecordCapabilities: { read: true, write: false, create: true, unlink: false, duplicate: true },
  recordDeniedReasons: { unlink: 'RECORD_RULE_DENIED', write: 'MODEL_ACCESS_DENIED' },
}));
check(() => assert.deepEqual(
  decoded.statusContract.globalStatus.recordDeniedReasons,
  { unlink: 'RECORD_RULE_DENIED', write: 'MODEL_ACCESS_DENIED' },
), 'recordDeniedReasons must survive decoding');

check(() => assert.throws(
  () => decodeContractV2Snapshot(snapshot({ pageVisible: true, pageAuth: 'read', inventedRecordReasons: { unlink: 'X' } })),
  /recordDeniedReasons|inventedRecordReasons|unknown/i,
), 'an undeclared globalStatus key must still fail closed');

check(() => assert.throws(
  () => decodeContractV2Snapshot(snapshot({ pageVisible: true, pageAuth: 'read', recordDeniedReasons: ['unlink'] })),
  /recordDeniedReasons/,
), 'recordDeniedReasons must be an object, not an array');

check(() => assert.equal(
  Object.prototype.hasOwnProperty.call(
    decodeContractV2Snapshot(snapshot({ pageVisible: true, pageAuth: 'read' })).statusContract.globalStatus,
    'recordDeniedReasons',
  ),
  false,
), 'an absent reason block must not be materialised as an empty object');

// 2. The store projection.
function storeOf({ globalStatus, deletePolicy = {}, mainData = {} }) {
  return {
    snapshot: {
      statusContract: { globalStatus },
      actionContract: { deletePolicy },
      dataContract: { mainData },
    },
  };
}

function stateOf(store, operation) {
  return resolveContractV2RecordActionStates(store).find((row) => row.operation === operation);
}

function globalStatus(overrides = {}) {
  return { pageVisible: true, pageAuth: 'write', ...overrides };
}

const NO_REASON = storeOf({
  globalStatus: globalStatus({
    effectiveRecordCapabilities: { read: true, write: false, create: true, unlink: false, duplicate: false },
  }),
});
check(() => assert.deepEqual(stateOf(NO_REASON, 'unlink'), { operation: 'unlink', allowed: false, reasonCode: '' }),
  'a denied unlink with no published reason stays denied with an empty code');
check(() => assert.deepEqual(stateOf(NO_REASON, 'write'), { operation: 'write', allowed: false, reasonCode: '' }),
  'a denied write with no published reason stays denied with an empty code');
check(() => assert.equal(stateOf(NO_REASON, 'read').allowed, true), 'an allowed read stays allowed');

const PUBLISHED_REASON = storeOf({
  globalStatus: globalStatus({
    effectiveRecordCapabilities: { read: true, write: false, create: true, unlink: false, duplicate: false },
    recordDeniedReasons: { unlink: 'RECORD_RULE_DENIED', write: 'MODEL_ACCESS_DENIED' },
  }),
});
check(() => assert.deepEqual(stateOf(PUBLISHED_REASON, 'unlink'),
  { operation: 'unlink', allowed: false, reasonCode: 'RECORD_RULE_DENIED' }),
  'the published denial reason reaches the record action state');
check(() => assert.equal(stateOf(PUBLISHED_REASON, 'duplicate').reasonCode, ''),
  'a denied operation without a published reason does not borrow another operation reason');

const STATE_GATE = {
  allowed: true,
  delete_mode: 'unlink',
  policy_kind: 'state_limited_business_document',
  state_field: 'state',
  allowed_states: ['cancel', 'cancelled', 'draft'],
  reason_code: 'DRAFT_BUSINESS_DOCUMENT_DELETE_ALLOWED',
  denied_reason_code: 'BUSINESS_DOCUMENT_STATE_NOT_DELETABLE',
};
const CAPABLE = { read: true, write: true, create: true, unlink: true, duplicate: true };

check(() => assert.deepEqual(
  stateOf(storeOf({
    globalStatus: globalStatus({ effectiveRecordCapabilities: CAPABLE }),
    deletePolicy: STATE_GATE,
    mainData: { state: 'approved' },
  }), 'unlink'),
  { operation: 'unlink', allowed: false, reasonCode: 'BUSINESS_DOCUMENT_STATE_NOT_DELETABLE' },
), 'a business document outside the declared deletable states is not deletable, and the reason is the declared one');

check(() => assert.deepEqual(
  stateOf(storeOf({
    globalStatus: globalStatus({ effectiveRecordCapabilities: CAPABLE }),
    deletePolicy: STATE_GATE,
    mainData: { state: 'draft' },
  }), 'unlink'),
  { operation: 'unlink', allowed: true, reasonCode: '' },
), 'a record inside the declared deletable states stays deletable');

check(() => assert.equal(
  stateOf(storeOf({
    globalStatus: globalStatus({ effectiveRecordCapabilities: CAPABLE }),
    deletePolicy: STATE_GATE,
    mainData: {},
  }), 'unlink').allowed,
  true,
), 'a state the contract did not publish must not be treated as a blocked state');

check(() => assert.deepEqual(
  stateOf(storeOf({
    globalStatus: globalStatus({ effectiveRecordCapabilities: CAPABLE }),
    deletePolicy: STATE_GATE,
    mainData: { state: 'approved' },
  }), 'write'),
  { operation: 'write', allowed: true, reasonCode: '' },
), 'the delete state gate must not leak onto other operations');

check(() => assert.deepEqual(
  stateOf(storeOf({
    globalStatus: globalStatus({ effectiveRecordCapabilities: CAPABLE }),
    deletePolicy: { allowed: false, delete_mode: 'none', reason_code: 'DELETE_POLICY_DENIED' },
  }), 'unlink'),
  { operation: 'unlink', allowed: false, reasonCode: 'DELETE_POLICY_DENIED' },
), 'a model the policy denies outright is denied with the model-level reason');

check(() => assert.deepEqual(
  stateOf(storeOf({
    globalStatus: globalStatus({ effectiveRecordCapabilities: CAPABLE }),
    deletePolicy: { ...STATE_GATE, denied_reason_code: undefined },
    mainData: { state: 'approved' },
  }), 'unlink'),
  { operation: 'unlink', allowed: false, reasonCode: '' },
), 'a state gate without a declared denial reason denies without inventing one');

check(() => {
  const states = resolveContractV2RecordActionStates(null);
  assert.deepEqual(states.map((row) => row.operation), ['read', 'write', 'create', 'unlink', 'duplicate']);
  assert.ok(states.every((row) => row.allowed === false && row.reasonCode === ''));
}, 'a page without a normalized contract stays fully denied');

check(() => {
  const operations = resolveContractV2RecordActionStates(storeOf({
    globalStatus: globalStatus({ effectiveRecordCapabilities: CAPABLE, recordDeniedReasons: { unlink: 'RECORD_RULE_DENIED' } }),
    deletePolicy: STATE_GATE,
    mainData: { state: 'draft' },
  }));
  assert.ok(operations.every((row) => row.allowed === true));
}, 'a published reason for an allowed operation never flips the verdict');

// 3. Wiring: the page consumes the resolver instead of re-deriving delete rights.
const pageSource = fs.readFileSync(path.join(root, 'frontend/apps/web/src/pages/ContractFormPage.vue'), 'utf8');
check(() => assert.match(pageSource, /resolveContractV2RecordActionStates/),
  'ContractFormPage must import the record action state resolver');
check(() => assert.match(pageSource, /recordActionStates\.value\.find\(\(state\) => state\.operation === 'unlink'\)/),
  "ContractFormPage's delete right must come from the resolved unlink state");

const { describeRecordActionDenials } = await bundle('frontend/apps/web/src/app/presentation/recordActionDenialPresentation.ts');
check(() => assert.deepEqual(describeRecordActionDenials([{ operation: 'write', allowed: false, reasonCode: 'MODEL_ACCESS_DENIED' }]), ['不可编辑：当前账号没有此操作权限']), 'show a declared ACL denial');
check(() => assert.deepEqual(describeRecordActionDenials([{ operation: 'unlink', allowed: false, reasonCode: 'BUSINESS_DOCUMENT_STATE_NOT_DELETABLE' }]), ['不可删除：当前业务状态不允许删除']), 'show a declared state gate');
check(() => assert.deepEqual(describeRecordActionDenials([{ operation: 'write', allowed: true, reasonCode: 'MODEL_ACCESS_DENIED' }]), []), 'allowed operations never show stale denial');
check(() => assert.deepEqual(describeRecordActionDenials(resolveContractV2RecordActionStates(null)), []), 'missing contract does not invent reasons');
check(() => assert.deepEqual(describeRecordActionDenials([{ operation: 'duplicate', allowed: false, reasonCode: 'MODEL_ACCESS_DENIED' }]), []), 'no unsupported copy action manufactured');
check(() => assert.deepEqual(describeRecordActionDenials([{ operation: 'unlink', allowed: false, reasonCode: 'NEW_BACKEND_REASON' }]), ['不可删除：当前页面未允许此操作']), 'unknown reasons stay neutral and denied');
check(() => assert.match(pageSource, /data-record-action-denials/), 'shared header notice consumes the denial projection');

console.log(`[frontend_contract_record_action_state] PASS cases=${cases}`);
