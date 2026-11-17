/**
 * Native Action Contract consumption boundary.
 *
 * The backend owns the Action/Search/View facts. The custom frontend owns two
 * separate obligations: reject contradictory contract carriers while decoding,
 * and refuse a Native Action View Set that cannot provide an ordered view.
 */
import assert from 'node:assert/strict';

import {
  resolveActionViewAvailableModes,
  resolveActionViewDefaultMode,
} from '../src/app/contracts/actionViewSurfaceContract';
import { decodeContractV2Snapshot } from '../src/app/contracts/v2/schema';
import { createContractV2Store } from '../src/app/contracts/v2/store';
import { isContractGapError } from '../src/app/contract/contractGap';

let cases = 0;
const check = (run: () => void) => {
  run();
  cases += 1;
};

function nativeActionView(viewType: string, overrides: Record<string, unknown> = {}) {
  return {
    viewType,
    viewId: viewType === 'tree' ? 11 : 12,
    viewXmlId: `demo.${viewType}`,
    actionViewSequence: viewType === 'tree' ? 1 : 2,
    surfaceRole: viewType === 'form' ? 'record_detail' : 'collection',
    selectable: viewType !== 'form',
    projectionStatus: 'ready',
    rendererStatus: 'ready',
    reasonCode: '',
    profile: viewType,
    ...overrides,
  };
}

function actionContractPayload() {
  return {
    pageInfo: {
      pageId: 'page.project.project',
      sceneKey: 'project.project',
      pageName: '项目',
      model: 'project.project',
      viewType: 'tree',
      layoutType: 'tree',
      renderMode: 'governed',
      contractVersion: '2.5.0',
      clientType: 'web_pc',
    },
    layoutContract: {
      pageId: 'page.project.project',
      layoutType: 'tree',
      adaptMode: 'pc',
      containerTree: [],
      layoutHints: {},
      componentRegistry: {},
      listProfile: {},
    },
    statusContract: {
      globalStatus: {},
      widgetStatus: [],
      buttonStatus: [],
      containerStatus: [],
      selectorStatus: [],
    },
    actionContract: { actionRuleList: [], dependencyGraph: {} },
    dataContract: {
      mainData: {},
      tableRows: {},
      relationRows: {},
      dictData: {},
      pagination: {},
      dataSource: {},
      dataMeta: {},
    },
    runtimeContract: {
      patchStrategy: 'full',
      cachePolicy: 'snapshot',
      optimistic: false,
      lazyContainer: [],
      virtualization: {},
      retryPolicy: {},
    },
    searchContract: {
      nativeIdentity: {
        model: 'project.project',
        actionId: 31,
        viewId: 21,
        viewXmlId: 'demo.project_search',
        authority: 'action_search_view',
        sourceLocator: 'ir.actions.act_window.search_view_id',
      },
    },
    nativeActionContract: {
      schemaVersion: '1.0.0',
      identity: {
        actionType: 'ir.actions.act_window',
        actionId: 31,
        actionXmlId: 'demo.project_action',
        model: 'project.project',
      },
      entryRefs: [{ kind: 'menu', menuId: 41, menuXmlId: 'demo.project_menu' }],
      actionScope: {
        domainRaw: "[]",
        domain: [],
        contextRaw: "{}",
        context: {},
        sourceAuthority: { kind: 'ir.actions.act_window' },
      },
      projectionAvailability: {
        status: 'available',
        reasonCode: '',
        authorityRef: 'existing_action_access_projection',
      },
      search: {
        viewId: 21,
        viewXmlId: 'demo.project_search',
        authority: 'action_search_view',
        profileRef: 'searchContract',
      },
      viewSet: {
        orderAuthority: 'ir.actions.act_window.views',
        defaultViewType: 'tree',
        activeViewType: 'tree',
        orderedViews: [nativeActionView('tree'), nativeActionView('form')],
      },
      readiness: {
        backendContract: { status: 'ready', reasonCodes: [] },
        clientRenderer: { status: 'ready', reasonCodes: [] },
        businessExecution: { status: 'not_applicable', reasonCodes: [] },
      },
      capabilities: ['action_view_set.v1', 'search_identity.v1'],
      sourceAuthority: {
        kind: 'native_action_contract_projection',
        projectionOnly: true,
        noBusinessFactAuthority: true,
      },
    },
    meta: {
      etag: 'native-action-consumption',
      snapshotId: 'native-action-consumption',
      traceId: 'native-action-consumption',
      requestId: 'native-action-consumption',
      sourceType: 'ui.contract',
      lifecycle: {
        lifecycleVersion: '1',
        stage: 'sealed',
        definition: {
          schemaId: 'unified_page_contract_v2',
          schemaVersion: '2.5.0',
          schemaSha256: 'schema',
          contractVersion: '2.5.0',
          normativeStatus: 'active',
        },
        generation: {
          generator: 'test',
          generatorVersion: '1',
          sourceType: 'ui.contract',
          sourceSha256: 'source',
        },
        runtime: {
          requestId: 'native-action-consumption',
          traceId: 'native-action-consumption',
          clientType: 'web_pc',
          traceSource: 'test',
        },
        integrity: { algorithm: 'sha256', contractSha256: 'contract' },
        authority: {},
      },
    },
  };
}

check(() => {
  const decoded = decodeContractV2Snapshot(actionContractPayload());
  assert.equal(decoded.nativeActionContract?.search?.viewXmlId, 'demo.project_search');
  const store = createContractV2Store(decoded);
  assert.deepEqual(resolveActionViewAvailableModes({
    contractViewTypeRaw: 'tree,form',
    metaViewModesRaw: 'tree,kanban,graph',
    contract: store,
  }), ['tree']);
  assert.equal(resolveActionViewDefaultMode(store), 'tree');
});

for (const [label, mutate] of [
  ['viewId', (contract: unknown) => { (contract as { search: Record<string, unknown> }).search.viewId = 22; }],
  ['viewXmlId', (contract: unknown) => { (contract as { search: Record<string, unknown> }).search.viewXmlId = 'demo.other_search'; }],
  ['authority', (contract: unknown) => { (contract as { search: Record<string, unknown> }).search.authority = 'model_default_search_view'; }],
] as const) {
  check(() => {
    const payload = actionContractPayload();
    mutate(payload.nativeActionContract);
    assert.throws(() => decodeContractV2Snapshot(payload), /must agree with searchContract\.nativeIdentity/, label);
  });
}

check(() => {
  const payload = actionContractPayload();
  delete (payload.nativeActionContract as Record<string, unknown>).search;
  assert.throws(
    () => decodeContractV2Snapshot(payload),
    /nativeActionContract\.search is required when searchContract\.nativeIdentity is present/,
  );
});

check(() => {
  const payload = actionContractPayload();
  delete (payload.searchContract as Record<string, unknown>).nativeIdentity;
  assert.throws(
    () => decodeContractV2Snapshot(payload),
    /nativeActionContract\.search requires searchContract\.nativeIdentity as its profile/,
  );
});

check(() => {
  const payload = actionContractPayload();
  payload.nativeActionContract.viewSet.orderedViews = [];
  const store = createContractV2Store(decodeContractV2Snapshot(payload));
  for (const run of [
    () => resolveActionViewAvailableModes({
      contractViewTypeRaw: 'tree',
      metaViewModesRaw: 'tree,kanban',
      contract: store,
    }),
    () => resolveActionViewDefaultMode(store),
  ]) {
    assert.throws(run, (error) => isContractGapError(error)
      && error.defect.missing === 'nativeActionContract.viewSet.orderedViews');
  }
});

console.log(`[native_action_contract_consumption_test] PASS cases=${cases}`);
