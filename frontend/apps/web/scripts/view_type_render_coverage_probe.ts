import { ACTION_SURFACE_RENDERER_REGISTRY, resolveActionSurfaceRenderer } from '../src/app/renderers/actionSurfaceRendererRegistry';
import { resolveActionCollectionPresentation } from '../src/app/contracts/actionViewSurfaceContract';
import { resolveActivitySurfaceModel } from '../src/app/contracts/actionViewActivityContract';
import { decodeContractV2Snapshot } from '../src/app/contracts/v2/schema';
import { createContractV2Store } from '../src/app/contracts/v2/store';
import { useActionPageModel } from '../src/app/assemblers/action/useActionPageModel';

const fallbackModes = ['pivot', 'graph', 'calendar', 'gantt', 'dashboard'] as const;

function advancedPageEvidence(viewMode: string) {
  const { vm } = useActionPageModel({
    page: {
      title: 'Readable fallback', status: 'ok', statusLabel: '', subtitle: '', traceId: '', errorMessage: '',
      sceneKey: '', pageMode: '', viewMode, availableViewModes: [viewMode],
    },
    headerActions: [],
    routePreset: { label: '', source: '' },
    filters: { quickPrimary: [], quickOverflow: [], savedPrimary: [], savedOverflow: [], groupByPrimary: [], groupByOverflow: [] },
    focus: { surfaceIntent: null },
    strict: { missingSummary: '', defaultsSummary: '', title: '' },
    groupSummary: { items: [] },
    actions: { primary: [], overflowGroups: [] },
    content: {
      listSummaryItems: [], kanbanOverviewItems: [], advancedTitle: 'Readable records',
      advancedHint: 'Fallback record projection', advancedRows: [{ key: 'record-7', title: 'Record 7', meta: 'id=7' }],
    },
    empty: { reasonText: '' },
    hud: { visible: false, entries: [] },
  });
  return {
    kind: vm.value.content.kind,
    rows: vm.value.content.advanced?.rows || [],
  };
}

const activityProfile = {
  activityTypeSlots: {}, deadlineSlots: {}, assigneeSlots: {},
  fieldOccurrences: [{
    name: 'x_subject', label: 'Subject', widget: '',
    native_locator: 'activity[1]/templates[1]/div[t-name=activity-box]/field[name=x_subject]',
    occurrence_index: 1, source_position: 3, attributes: { name: 'x_subject' }, text: '', tail: '',
    modifiers: '', decorations: [], field_type: '', currency_field: '', digits: [],
  }],
  nativeAttrs: { string: 'Activities' },
  nodeOccurrences: [
    { tag: 'activity', native_locator: 'activity[1]', occurrence_index: 1, source_position: 0, attributes: { string: 'Activities' }, text: '', tail: '' },
    { tag: 'templates', native_locator: 'activity[1]/templates[1]', occurrence_index: 1, source_position: 1, attributes: {}, text: '', tail: '' },
    { tag: 'div', native_locator: 'activity[1]/templates[1]/div[t-name=activity-box]', occurrence_index: 1, source_position: 2, attributes: { 't-name': 'activity-box' }, text: '', tail: '' },
    { tag: 'field', native_locator: 'activity[1]/templates[1]/div[t-name=activity-box]/field[name=x_subject]', occurrence_index: 1, source_position: 3, attributes: { name: 'x_subject' }, text: '', tail: '' },
  ],
  template: {
    native_locator: 'activity[1]/templates[1]', occurrence_index: 1, names: ['activity-box'],
    nodes: [{
      tag: 'div', native_locator: 'activity[1]/templates[1]/div[t-name=activity-box]', occurrence_index: 1,
      source_position: 2, attributes: { 't-name': 'activity-box' }, text: '', tail: '', children: [{
        tag: 'field', native_locator: 'activity[1]/templates[1]/div[t-name=activity-box]/field[name=x_subject]',
        occurrence_index: 1, source_position: 3, attributes: { name: 'x_subject' }, text: '', tail: '', children: [],
      }],
    }],
  },
  templateQwebPresent: true, actions: [], actionCount: 0,
  sourceAuthority: {
    kind: 'native_activity_view_projection',
    authorities: ['ir.ui.view', 'ir.model.fields', 'ir.actions.act_window'],
    projection_only: true, no_business_fact_authority: true,
    runtime_carrier: 'ui.contract.v2.layoutContract.activityProfile',
  },
};

const activityPayload = {
  pageInfo: {
    pageId: 'page.x.activity', sceneKey: 'x.activity', pageName: 'Activities', model: 'x.activity',
    viewType: 'activity', layoutType: 'activity', renderMode: 'governed', contractVersion: '2.2.0', clientType: 'web_pc',
  },
  layoutContract: {
    pageId: 'page.x.activity', layoutType: 'activity', adaptMode: 'pc', containerTree: [],
    layoutHints: {}, componentRegistry: {}, activityProfile,
  },
  statusContract: { globalStatus: {}, widgetStatus: [], buttonStatus: [], containerStatus: [], selectorStatus: [] },
  actionContract: { actionRuleList: [], dependencyGraph: {} },
  dataContract: { mainData: {}, tableRows: {}, relationRows: {}, dictData: {}, pagination: {}, dataSource: {}, dataMeta: {} },
  runtimeContract: { patchStrategy: 'full', cachePolicy: 'snapshot', optimistic: false, lazyContainer: [], virtualization: {}, retryPolicy: {} },
  meta: {
    etag: 'activity-etag', snapshotId: 'activity-snapshot', traceId: 'activity-trace', requestId: 'activity-request',
    sourceType: 'ui.contract', lifecycle: {
      lifecycleVersion: '1.0.0', stage: 'runtime_delivery',
      definition: {
        schemaId: 'smart_core.unified_page_contract_v2', schemaVersion: '2.2.0',
        schemaSha256: 'b4a2614f4aa0f5ad052b6fc0f1351fb74cf511825c5fdee3036afdb0122ee419',
        contractVersion: '2.2.0', normativeStatus: 'stable',
      },
      generation: {
        generator: 'view_type_render_coverage_probe', generatorVersion: '2.2.0', sourceType: 'ui.contract',
        sourceSha256: '44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a',
      },
      runtime: { requestId: 'activity-request', traceId: 'activity-trace', clientType: 'web_pc', traceSource: 'request_context' },
      integrity: { algorithm: 'sha256', contractSha256: 'c5e22672ab0e43d4aaf87378590a511b7132917bd7df3b6d2883d80dcae02526' },
      authority: { kind: 'coverage_probe', projection_only: true, no_business_fact_authority: true },
    },
  },
};

const decodedActivity = decodeContractV2Snapshot(activityPayload);
const activityStore = createContractV2Store(decodedActivity);
const activityModel = resolveActivitySurfaceModel(activityStore, [{ id: 7, x_subject: 'Review' }]);
const { activityProfile: omittedProfile, ...layoutWithoutProfile } = activityPayload.layoutContract;
void omittedProfile;
const missingStore = createContractV2Store(decodeContractV2Snapshot({ ...activityPayload, layoutContract: layoutWithoutProfile }));
const missingActivityModel = resolveActivitySurfaceModel(missingStore, []);
const analysisAuthority = (viewType: 'pivot' | 'graph') => ({
  kind: `native_${viewType}_view_projection`,
  authorities: ['ir.ui.view', 'ir.model.fields', 'ir.actions.act_window'],
  projection_only: true, no_business_fact_authority: true,
  runtime_carrier: `ui.contract.v2.layoutContract.${viewType}Profile`,
});
const pivotProfile = {
  measures: [{ name: 'amount', label: 'Amount' }],
  dimensions: [{ name: 'date', label: 'Date', axis: 'col' }],
  defaults: {}, sourceAuthority: analysisAuthority('pivot'),
};
const graphProfile = {
  measures: [{ name: 'amount', label: 'Amount' }],
  dimensions: [{ name: 'project_id', label: 'Project' }],
  typeDefault: 'bar', sourceAuthority: analysisAuthority('graph'),
};
const decodedPivot = decodeContractV2Snapshot({
  ...activityPayload,
  pageInfo: { ...activityPayload.pageInfo, viewType: 'pivot', layoutType: 'pivot' },
  layoutContract: {
    ...layoutWithoutProfile, layoutType: 'pivot', pivotProfile,
  },
});
const decodedGraph = decodeContractV2Snapshot({
  ...activityPayload,
  pageInfo: { ...activityPayload.pageInfo, viewType: 'graph', layoutType: 'graph' },
  layoutContract: {
    ...layoutWithoutProfile, layoutType: 'graph', graphProfile,
  },
});

const evidence = {
  scope: 'view_type_render_coverage',
  deliveryClaims: { actionRouteProven: false, browserDeliveryProven: false },
  registrations: Object.fromEntries(
    [...fallbackModes, 'activity'].map((mode) => [mode, ACTION_SURFACE_RENDERER_REGISTRY[mode]]),
  ),
  fallback: Object.fromEntries(fallbackModes.map((mode) => {
    const presentation = resolveActionCollectionPresentation(null, mode);
    const descriptor = resolveActionSurfaceRenderer(presentation, mode);
    return [mode, { presentation, descriptor, page: advancedPageEvidence(mode) }];
  })),
  activity: {
    payload: activityPayload,
    decodedCarrier: decodedActivity.layoutContract.activityProfile?.sourceAuthority.runtime_carrier || '',
    storeCarrier: activityStore.snapshot.layoutContract.activityProfile?.sourceAuthority.runtime_carrier || '',
    model: {
      ok: activityModel.ok,
      reasonCode: activityModel.reasonCode,
      requestedFields: activityModel.requestedFields,
      recordCount: activityModel.records.length,
    },
    missingReasonCode: missingActivityModel.reasonCode,
  },
  analysisProfiles: {
    pivot: decodedPivot.layoutContract.pivotProfile,
    graph: decodedGraph.layoutContract.graphProfile,
  },
};

process.stdout.write(`${JSON.stringify(evidence)}\n`);
