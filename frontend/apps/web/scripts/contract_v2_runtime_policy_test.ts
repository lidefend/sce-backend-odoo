import assert from 'node:assert/strict';

import { permitsContractV2SnapshotReuse } from '../src/app/contracts/v2/runtime';
import { resolveContractV2RuntimePolicy } from '../src/app/contracts/v2/store';
import type { ContractV2RuntimeContract } from '../src/app/contracts/v2/types';
import { resolveContractFormReadContext } from '../src/pages/contractForm/contractRuntimeVm';

function runtime(cachePolicy: ContractV2RuntimeContract['cachePolicy']): ContractV2RuntimeContract {
  return {
    patchStrategy: 'incremental',
    cachePolicy,
    optimistic: false,
    lazyContainer: [],
    virtualization: {},
    retryPolicy: { maxRetries: 1 },
  };
}

assert.equal(permitsContractV2SnapshotReuse(runtime('snapshot')), true);
assert.equal(permitsContractV2SnapshotReuse(runtime('etag')), false);
assert.equal(permitsContractV2SnapshotReuse(runtime('none')), false);

const runtimePayload = {
  ...runtime('snapshot'),
  renderStrategy: 'incremental',
  hydration: { mode: 'eager' },
  patchOperations: ['replace'],
  tracePolicy: { level: 'full' },
  complexityBudget: { fields: 100 },
  aiEnvelope: { mode: 'suggestion', executable: false, allowed: false, capabilities: [] },
  interactionMode: 'form',
  actionTarget: 'record',
  collaboration: { enabled: true },
  businessWorkspace: { enabled: true },
  businessActions: [{ action: 'submit' }],
  deliveryProfile: 'full',
  intakeAutosave: { enabled: true },
  fieldSemantics: { amount: { semanticType: 'money' } },
  validationRules: [{ field: 'amount', required: true }],
  governance: { owner: 'platform' },
  recordVersionPolicy: { mode: 'etag' },
};
const fakeStore = { snapshot: { runtimeContract: runtimePayload } } as never;
const projected = resolveContractV2RuntimePolicy(fakeStore);
for (const [key, value] of Object.entries(runtimePayload)) {
  assert.deepEqual(projected[key], value, `runtime policy field ${key} must survive store projection`);
}

const inactiveActionStore = {
  snapshot: {
    dataContract: {
      dataMeta: {
        sourceContext: {
          context: { active_test: false, sc_runtime_user_management: true },
        },
      },
    },
  },
} as never;
assert.deepEqual(
  resolveContractFormReadContext(inactiveActionStore),
  { active_test: false, sc_runtime_user_management: true },
  'an explicit false from the server-projected action context reaches record reads',
);
assert.deepEqual(
  resolveContractFormReadContext({ snapshot: { dataContract: { dataMeta: {} } } } as never),
  {},
  'an action without active_test keeps the api.data default filtering behavior',
);

console.log('contract v2 runtime policy: PASS cases=6 fields=23');

// A preview has no published contract row. Its explicit provenance must survive
// decoding without granting the same zero-ID exception to published sources.
const { decodeContractV2Snapshot } = await import('../src/app/contracts/v2/schema');
const previewSnapshot = {
  pageInfo: { pageId: 'preview.form', sceneKey: 'preview.form', pageName: 'Preview', model: 'x.preview',
    viewType: 'form', layoutType: 'form', renderMode: 'governed', contractVersion: '2.2.0', clientType: 'web_pc' },
  layoutContract: { pageId: 'preview.form', layoutType: 'form', adaptMode: 'pc', containerTree: [], layoutHints: {}, componentRegistry: {} },
  statusContract: { globalStatus: { pageVisible: true, pageAuth: 'read' }, containerStatus: [], widgetStatus: [], buttonStatus: [], selectorStatus: [] },
  actionContract: { actionRuleList: [], dependencyGraph: {} },
  dataContract: { mainData: {}, tableRows: {}, relationRows: {}, dictData: {}, pagination: {}, dataSource: {}, dataMeta: {} },
  runtimeContract: runtime('none'),
  meta: { etag: 'test', snapshotId: 'test', traceId: 'test', requestId: 'test', sourceType: 'test',
    lifecycle: {
      lifecycleVersion: '1', stage: 'sealed',
      definition: { schemaId: 'v2', schemaVersion: '2', schemaSha256: 'schema', contractVersion: '2', normativeStatus: 'active' },
      generation: { generator: 'test', generatorVersion: '1', sourceType: 'test', sourceSha256: 'source' },
      runtime: { requestId: 'test', traceId: 'test', clientType: 'web_pc', traceSource: 'test' },
      integrity: { algorithm: 'sha256', contractSha256: 'contract' }, authority: {},
    } },
  formStructureContract: {
    source: 'ui.contract.v2.form_structure_contract', structureVersion: '1.1', model: 'x.preview', viewType: 'form',
    mode: 'native_structured_form', presentationMode: 'task', layoutPolicy: 'container_tree_authority',
    objectProfile: { model: 'x.preview', kind: 'business_form', factAuthority: 'business_object_model_and_view' },
    navigation: { title: 'Preview' }, slots: [], fieldRoles: {},
    sourceAuthority: { kind: 'unified_page_contract_v2', runtime_carrier: 'ui.contract.v2.form_structure_contract',
      projection_only: true, no_business_fact_authority: true, governed_form_structure: true,
      governance_source: { source: 'business_view_orchestration', formStructureAuthority: 'native_authority',
        businessConfigContracts: [{ id: 0, name: 'preview:test', source_kind: 'change_set_preview' }] } },
  },
};
assert.equal(decodeContractV2Snapshot(previewSnapshot).formStructureContract?.sourceAuthority.governance_source.businessConfigContracts?.[0].source_kind, 'change_set_preview');
previewSnapshot.formStructureContract.sourceAuthority.governance_source.businessConfigContracts[0].source_kind = 'published';
assert.throws(() => decodeContractV2Snapshot(previewSnapshot), /positive published ID/);
console.log('[contract_v2_runtime_policy_test] preview provenance cases=2 passed');

previewSnapshot.formStructureContract.sourceAuthority.governance_source.businessConfigContracts[0].source_kind = 'change_set_preview';
const unnamedTree = decodeContractV2Snapshot({ ...previewSnapshot, layoutContract: {
  ...previewSnapshot.layoutContract, containerTree: [{ containerId: 'native.group', containerType: 'group', type: 'group',
    name: '', title: 'Group', nativeLocator: '/form/group[2]', occurrenceIndex: 2, children: [], widgetList: [] }],
} }).layoutContract.containerTree;
const { bindNode } = await import('../src/pages/contractForm/boundFormConfiguration');
assert.equal(bindNode(unnamedTree[0]).expected.name, '', 'decode -> designer must preserve the unnamed native occurrence');
console.log('[contract_v2_runtime_policy_test] unnamed node binding cases=1 passed');
