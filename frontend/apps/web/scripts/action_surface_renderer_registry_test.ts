import assert from 'node:assert/strict';
import {
  ACTION_SURFACE_RENDERER_REGISTRY,
  registeredActionSurfaceSemantics,
  resolveActionSurfaceRenderer,
} from '../src/app/renderers/actionSurfaceRendererRegistry';
import { resolveActionCollectionPresentation } from '../src/app/contracts/actionViewSurfaceContract';
import {
  activityCellText,
  resolveActivitySurfaceModel,
  resolveActivitySurfaceModelFromProfile,
} from '../src/app/contracts/actionViewActivityContract';
import { decodeContractV2Snapshot } from '../src/app/contracts/v2/schema';
import { createContractV2Store } from '../src/app/contracts/v2/store';
import { shouldUseCanonicalCollectionDetail } from '../src/app/runtime/actionViewInteractionRuntime';

const readySemantics = [
  'table',
  'card',
  'workflow_board',
  'hierarchy_browser',
  'hierarchy_planner',
  'hierarchical_worksheet',
  'activity',
];
const plannedSemantics = ['pivot', 'graph', 'calendar', 'gantt', 'dashboard'];

assert.deepEqual(registeredActionSurfaceSemantics().sort(), [...readySemantics, ...plannedSemantics].sort());
readySemantics.forEach((semantic) => assert.equal(ACTION_SURFACE_RENDERER_REGISTRY[semantic]?.status, 'ready'));
plannedSemantics.forEach((semantic) => {
  const registration = ACTION_SURFACE_RENDERER_REGISTRY[semantic];
  assert.equal(registration?.status, 'fallback');
  assert.equal(registration?.activeRendererKey, 'core.readable_records');
  const presentation = resolveActionCollectionPresentation({ views: { [semantic]: { fields: ['id', 'name'] } } }, semantic);
  assert.equal(presentation.semantic, semantic);
  assert.equal(resolveActionSurfaceRenderer(presentation, semantic).requestedRendererKey, `core.${semantic}`);
});

const activity = ACTION_SURFACE_RENDERER_REGISTRY.activity;
assert.equal(activity?.status, 'ready');
assert.equal(activity?.activeRendererKey, 'core.activity');
assert.equal(activity?.outlet, 'standard');
assert.equal(shouldUseCanonicalCollectionDetail({ viewMode: 'activity', collectionSemantic: 'activity' }), true);
assert.equal(shouldUseCanonicalCollectionDetail({ viewMode: 'activity', collectionSemantic: '' }), true);

const activityModel = resolveActivitySurfaceModelFromProfile({
  fieldOccurrences: [
    { name: 'x_due', label: 'Due', widget: 'date', native_locator: 'activity/field[name=x_due]', occurrence_index: 1, source_position: 1, attributes: { name: 'x_due' }, modifiers: '', decorations: [] },
    { name: 'x_subject', label: 'Subject', widget: '', native_locator: 'activity/templates[1]/div[t-name=activity-box]/field[name=x_subject]', occurrence_index: 1, source_position: 4, attributes: { name: 'x_subject' }, text: '', tail: 'due soon', modifiers: '', decorations: [] },
  ],
  nativeAttrs: { string: 'Activities' },
  nodeOccurrences: [
    { tag: 'activity', native_locator: 'activity', occurrence_index: 1, source_position: 0, attributes: { string: 'Activities' } },
    { tag: 'field', native_locator: 'activity/field[name=x_due]', occurrence_index: 1, source_position: 1, attributes: { name: 'x_due' } },
    { tag: 'templates', native_locator: 'activity/templates[1]', occurrence_index: 1, source_position: 2, attributes: {} },
    { tag: 'div', native_locator: 'activity/templates[1]/div[t-name=activity-box]', occurrence_index: 1, source_position: 3, attributes: { 't-name': 'activity-box' }, text: 'Section' },
    { tag: 'field', native_locator: 'activity/templates[1]/div[t-name=activity-box]/field[name=x_subject]', occurrence_index: 1, source_position: 4, attributes: { name: 'x_subject' }, tail: 'due soon' },
  ],
  template: {
    native_locator: 'activity/templates[1]', occurrence_index: 1, names: ['activity-box'],
    nodes: [{
      tag: 'div', native_locator: 'activity/templates[1]/div[t-name=activity-box]', occurrence_index: 1,
      source_position: 3, attributes: { 't-name': 'activity-box' }, text: 'Section',
      children: [{
        tag: 'field', native_locator: 'activity/templates[1]/div[t-name=activity-box]/field[name=x_subject]', occurrence_index: 1,
        source_position: 4, attributes: { name: 'x_subject' }, text: '', tail: 'due soon', children: [],
      }],
    }],
  },
  templateQwebPresent: true,
  actions: [],
  actionCount: 0,
  sourceAuthority: {
    kind: 'native_activity_view_projection',
    authorities: ['ir.ui.view', 'ir.model.fields', 'ir.actions.act_window'],
    projection_only: true,
    no_business_fact_authority: true,
    runtime_carrier: 'ui.contract.v2.layoutContract.activityProfile',
  },
}, [{ id: 7, x_subject: 'Review', x_due: '2026-08-21' }]);
assert.equal(activityModel.ok, true);
assert.deepEqual(activityModel.requestedFields, ['id', 'x_due', 'x_subject']);
assert.equal(activityModel.fields[0]?.label, 'Subject');
assert.equal(activityModel.fields.some((field) => field.name === 'x_due'), false);
assert.equal(activityModel.records[0]?.x_subject, 'Review');
assert.equal(activityModel.templateNodes[0]?.text, 'Section');
assert.equal(activityModel.templateNodes[0]?.children[0]?.tail, 'due soon');
assert.equal(Object.prototype.hasOwnProperty.call(activityModel, 'template_qweb'), false);
assert.equal(resolveActivitySurfaceModelFromProfile({}, []).ok, false);
const activityProfile = {
  activityTypeSlots: {},
  deadlineSlots: {},
  assigneeSlots: {},
  fieldOccurrences: [
    {
      name: 'x_subject', label: 'Subject', widget: '',
      native_locator: 'activity/templates[1]/div[t-name=activity-box]/field[name=x_subject]',
      occurrence_index: 1, source_position: 4,
      attributes: { name: 'x_subject', 'decoration-info': "state == 'new'" },
      text: '', tail: 'due soon', modifiers: '',
      decorations: [{ class: 'info', expr_raw: "state == 'new'", expr: { kind: 'raw', value: "state == 'new'" } }],
      field_type: '', currency_field: '', digits: [],
    },
  ],
  nativeAttrs: { string: 'Activities' },
  nodeOccurrences: [
    { tag: 'activity', native_locator: 'activity', occurrence_index: 1, source_position: 0, attributes: { string: 'Activities' }, text: '', tail: '' },
    { tag: 'templates', native_locator: 'activity/templates[1]', occurrence_index: 1, source_position: 2, attributes: {}, text: '', tail: '' },
    { tag: 'div', native_locator: 'activity/templates[1]/div[t-name=activity-box]', occurrence_index: 1, source_position: 3, attributes: { 't-name': 'activity-box' }, text: 'Section', tail: '' },
    { tag: 'field', native_locator: 'activity/templates[1]/div[t-name=activity-box]/field[name=x_subject]', occurrence_index: 1, source_position: 4, attributes: { name: 'x_subject', 'decoration-info': "state == 'new'" }, text: '', tail: 'due soon' },
  ],
  template: {
    native_locator: 'activity/templates[1]', occurrence_index: 1, names: ['activity-box'],
    nodes: [{
      tag: 'div', native_locator: 'activity/templates[1]/div[t-name=activity-box]', occurrence_index: 1, source_position: 3,
      attributes: { 't-name': 'activity-box' }, text: 'Section', tail: '', children: [{
        tag: 'field', native_locator: 'activity/templates[1]/div[t-name=activity-box]/field[name=x_subject]', occurrence_index: 1,
        source_position: 4, attributes: { name: 'x_subject', 'decoration-info': "state == 'new'" }, text: '', tail: 'due soon', children: [],
      }],
    }],
  },
  templateQwebPresent: true,
  actions: [], actionCount: 0,
  sourceAuthority: {
    kind: 'native_activity_view_projection',
    authorities: ['ir.ui.view', 'ir.model.fields', 'ir.actions.act_window'],
    projection_only: true,
    no_business_fact_authority: true,
    runtime_carrier: 'ui.contract.v2.layoutContract.activityProfile',
  },
};

const activityCarrierPayload = {
  pageInfo: {
    pageId: 'page.x.activity', sceneKey: 'x.activity', pageName: 'Activities', model: 'x.activity',
    viewType: 'activity', layoutType: 'activity', renderMode: 'governed', contractVersion: '2.0.0', clientType: 'web_pc',
  },
  layoutContract: {
    pageId: 'page.x.activity', layoutType: 'activity', adaptMode: 'pc', containerTree: [],
    layoutHints: { density: 'compact' }, componentRegistry: {},
    listProfile: { collection_presentation: { semantic: 'activity' } },
    activityProfile,
  },
  statusContract: {
    globalStatus: {}, widgetStatus: [], buttonStatus: [], containerStatus: [], selectorStatus: [],
  },
  actionContract: { actionRuleList: [], dependencyGraph: {} },
  dataContract: {
    mainData: {}, tableRows: {}, relationRows: {}, dictData: {}, pagination: {}, dataSource: {}, dataMeta: {},
  },
  runtimeContract: {
    patchStrategy: 'full', cachePolicy: 'snapshot', optimistic: false, lazyContainer: [], virtualization: {}, retryPolicy: {},
  },
  meta: {
    etag: 'activity-etag', snapshotId: 'activity-snapshot', traceId: 'activity-trace', requestId: 'activity-request',
    sourceType: 'ui.contract',
    lifecycle: {
      lifecycleVersion: '1', stage: 'sealed',
      definition: { schemaId: 'v2', schemaVersion: '2', schemaSha256: 'schema', contractVersion: '2', normativeStatus: 'active' },
      generation: { generator: 'test', generatorVersion: '1', sourceType: 'ui.contract', sourceSha256: 'source' },
      runtime: { requestId: 'activity-request', traceId: 'activity-trace', clientType: 'web_pc', traceSource: 'test' },
      integrity: { algorithm: 'sha256', contractSha256: 'activity-contract-sha' }, authority: {},
    },
  },
};

const decodedActivityCarrier = decodeContractV2Snapshot(activityCarrierPayload);
assert.deepEqual(decodedActivityCarrier.layoutContract.activityProfile, activityProfile);
assert.deepEqual(decodedActivityCarrier.layoutContract.listProfile, activityCarrierPayload.layoutContract.listProfile);
assert.deepEqual(decodedActivityCarrier.layoutContract.layoutHints, activityCarrierPayload.layoutContract.layoutHints);
const activityCarrierStore = createContractV2Store(decodedActivityCarrier);
assert.deepEqual(activityCarrierStore.snapshot.layoutContract.activityProfile, activityProfile);
const activityFromNormalizedStore = resolveActivitySurfaceModel(activityCarrierStore, [{ id: 7, x_subject: 'Review' }]);
assert.equal(activityFromNormalizedStore.ok, true);
assert.equal(activityFromNormalizedStore.records[0]?.x_subject, 'Review');
assert.equal(activityFromNormalizedStore.sourceAuthority.runtime_carrier, 'ui.contract.v2.layoutContract.activityProfile');

const { activityProfile: omittedActivityProfile, ...layoutWithoutActivityProfile } = activityCarrierPayload.layoutContract;
assert.ok(omittedActivityProfile);
const decodedMissingActivityCarrier = decodeContractV2Snapshot({
  ...activityCarrierPayload,
  layoutContract: layoutWithoutActivityProfile,
});
assert.equal(
  resolveActivitySurfaceModel(createContractV2Store(decodedMissingActivityCarrier), []).reasonCode,
  'ACTIVITY_SOURCE_AUTHORITY_MISSING',
);

const invalidActivityCarrier = structuredClone(activityCarrierPayload);
Object.assign(invalidActivityCarrier.layoutContract.activityProfile, { fieldOccurrences: {} });
assert.throws(
  () => decodeContractV2Snapshot(invalidActivityCarrier),
  /layoutContract\.activityProfile\.fieldOccurrences must be an array/,
);

type DecodedActivityCarrier = ReturnType<typeof decodeContractV2Snapshot>;
function assertInvalidActivityCarrierRejected(
  mutate: (profile: Record<string, unknown>) => void,
  expectedIssue: RegExp,
): void {
  const payload = structuredClone(activityCarrierPayload);
  mutate(payload.layoutContract.activityProfile as unknown as Record<string, unknown>);
  let decoded: DecodedActivityCarrier | undefined;
  assert.throws(() => {
    decoded = decodeContractV2Snapshot(payload);
  }, expectedIssue);
  assert.equal(decoded, undefined, 'invalid profile must not enter the normalized store');
}

function firstActivityField(profile: Record<string, unknown>): Record<string, unknown> {
  return (profile.fieldOccurrences as Array<Record<string, unknown>>)[0];
}

function activityAuthority(profile: Record<string, unknown>): Record<string, unknown> {
  return profile.sourceAuthority as Record<string, unknown>;
}

const nullActivityCarrier = structuredClone(activityCarrierPayload);
Object.assign(nullActivityCarrier.layoutContract, { activityProfile: null });
let decodedNullActivityCarrier: DecodedActivityCarrier | undefined;
assert.throws(() => {
  decodedNullActivityCarrier = decodeContractV2Snapshot(nullActivityCarrier);
}, /layoutContract\.activityProfile must be an object/);
assert.equal(decodedNullActivityCarrier, undefined, 'null profile must not enter the normalized store');

assertInvalidActivityCarrierRejected((profile) => { firstActivityField(profile).digits = [16]; }, /digits must be empty or contain precision and scale/);
assertInvalidActivityCarrierRejected((profile) => { firstActivityField(profile).digits = [16, 2, 1]; }, /digits must be empty or contain precision and scale/);
assertInvalidActivityCarrierRejected((profile) => { firstActivityField(profile).digits = '16,2'; }, /digits must be empty or contain precision and scale/);
assertInvalidActivityCarrierRejected((profile) => { firstActivityField(profile).digits = [16, '2']; }, /digits must contain valid precision and scale integers/);
assertInvalidActivityCarrierRejected((profile) => { firstActivityField(profile).digits = [-1, 0]; }, /digits must contain valid precision and scale integers/);
assertInvalidActivityCarrierRejected((profile) => { firstActivityField(profile).occurrence_index = '1'; }, /occurrence_index must be an integer greater than or equal to 1/);
assertInvalidActivityCarrierRejected((profile) => { profile.actionCount = '0'; }, /actionCount must be an integer greater than or equal to 0/);
assertInvalidActivityCarrierRejected((profile) => {
  firstActivityField(profile).decorations = [{ class: 'info' }, 'invalid'];
}, /decorations\[1\] must be an object/);
assertInvalidActivityCarrierRejected((profile) => {
  activityAuthority(profile).authorities = ['ir.ui.view', 'ir.model.fields', 7];
}, /authorities must exactly match the governed native authorities/);
assertInvalidActivityCarrierRejected((profile) => {
  activityAuthority(profile).authorities = ['ir.ui.view', 'ir.model.fields', 'unknown.authority'];
}, /authorities must exactly match the governed native authorities/);
assertInvalidActivityCarrierRejected((profile) => {
  activityAuthority(profile).authorities = ['ir.ui.view', 'ir.model.fields'];
}, /authorities must exactly match the governed native authorities/);
assertInvalidActivityCarrierRejected((profile) => {
  activityAuthority(profile).authorities = ['ir.ui.view', 'ir.model.fields', 'ir.model.fields'];
}, /authorities must exactly match the governed native authorities/);

assert.equal(resolveActivitySurfaceModelFromProfile({ ...activityProfile, nodeOccurrences: [] }, []).reasonCode, 'ACTIVITY_NATIVE_EVIDENCE_INVALID');
assert.equal(resolveActivitySurfaceModelFromProfile({ ...activityProfile, nativeAttrs: { string: 'Changed' } }, []).reasonCode, 'ACTIVITY_NATIVE_EVIDENCE_INVALID');
const shiftedProfile = structuredClone(activityProfile);
shiftedProfile.template.nodes[0].source_position = 9;
assert.equal(resolveActivitySurfaceModelFromProfile(shiftedProfile, []).reasonCode, 'ACTIVITY_NATIVE_EVIDENCE_INVALID');
const changedTextProfile = structuredClone(activityProfile);
changedTextProfile.template.nodes[0].text = 'Changed';
assert.equal(resolveActivitySurfaceModelFromProfile(changedTextProfile, []).reasonCode, 'ACTIVITY_NATIVE_EVIDENCE_INVALID');
const changedTailProfile = structuredClone(activityProfile);
changedTailProfile.template.nodes[0].children[0].tail = 'Changed';
assert.equal(resolveActivitySurfaceModelFromProfile(changedTailProfile, []).reasonCode, 'ACTIVITY_NATIVE_EVIDENCE_INVALID');
const changedNameProfile = structuredClone(activityProfile);
changedNameProfile.fieldOccurrences[0].name = 'x_other';
assert.equal(resolveActivitySurfaceModelFromProfile(changedNameProfile, []).reasonCode, 'ACTIVITY_NATIVE_EVIDENCE_INVALID');
assert.equal(resolveActivitySurfaceModelFromProfile({ ...activityProfile, actionCount: 1, actions: [{ native_identity: { authoritative: true, native_locator: 'activity/button[name=run]', name: 'run', type: 'object' } }] }, []).reasonCode, 'ACTIVITY_ACTION_RENDERER_UNSUPPORTED');
const hiddenProfile = structuredClone(activityProfile);
hiddenProfile.fieldOccurrences[0].attributes.invisible = '1';
hiddenProfile.nodeOccurrences[3].attributes.invisible = '1';
hiddenProfile.template.nodes[0].children[0].attributes.invisible = '1';
const hiddenActivity = resolveActivitySurfaceModelFromProfile(hiddenProfile, [{ id: 8, x_subject: 'Hidden' }]);
assert.equal(hiddenActivity.ok, true);
assert.equal(hiddenActivity.fields.length, 0);
const qwebProfile = structuredClone(activityProfile);
qwebProfile.nodeOccurrences[2].attributes['t-if'] = 'record.x_subject';
qwebProfile.template.nodes[0].attributes['t-if'] = 'record.x_subject';
assert.equal(resolveActivitySurfaceModelFromProfile(qwebProfile, []).reasonCode, 'ACTIVITY_QWEB_DIRECTIVE_UNSUPPORTED');
assert.equal(activityCellText({ display_name: 'guessed', raw: 1 }), '{"display_name":"guessed","raw":1}');
assert.equal(activityCellText([7, 'Not guessed']), '[7,"Not guessed"]');
assert.equal(activityCellText([7, 'Explicit relation'], {
  key: 'relation', name: 'x_relation', label: 'Relation', widget: '', nativeLocator: 'activity/field[name=x_relation]',
  occurrenceIndex: 1, attributes: {}, decorations: [], fieldType: 'many2one', currencyField: '',
}), 'Explicit relation');
assert.match(activityCellText(12.5, {
  key: 'amount', name: 'x_amount', label: 'Amount', widget: 'monetary', nativeLocator: 'activity/field[name=x_amount]',
  occurrenceIndex: 1, attributes: {}, decorations: [], fieldType: 'monetary', currencyField: 'company_currency_id', digits: [16, 2],
}, { company_currency_id: [1, 'USD'] }), /12\.50/);

const hierarchy = resolveActionSurfaceRenderer({
  semantic: 'hierarchy_browser', label: 'Hierarchy', groupField: '', groupedLanes: false, config: { tree: {} },
}, 'tree');
assert.equal(hierarchy.activeRendererKey, 'core.hierarchy_browser');
assert.equal(hierarchy.outlet, 'component');
assert.deepEqual(hierarchy.config, { tree: {} });

const standardTable = resolveActionSurfaceRenderer({
  semantic: 'table', label: 'Table', groupField: '', groupedLanes: false, config: {},
}, 'tree', { eligible: false, config: {}, reasonCode: 'SCENE_DRIVER_POLICY_DISABLED' });
assert.equal(standardTable.activeRendererKey, 'core.standard_collection');
assert.equal(standardTable.outlet, 'standard');

const sceneTable = resolveActionSurfaceRenderer({
  semantic: 'table', label: 'Table', groupField: '', groupedLanes: false, config: {},
}, 'tree', { eligible: true, config: { contract: { readonly: true } } });
assert.equal(sceneTable.activeRendererKey, 'core.scene_collection');
assert.equal(sceneTable.outlet, 'component');

const invalidTargetedTable = resolveActionSurfaceRenderer({
  semantic: 'table', label: 'Table', groupField: '', groupedLanes: false, config: {},
}, 'tree', {
  eligible: false,
  contractError: true,
  config: {},
  reasonCode: 'SCENE_DRIVER_NORMALIZED_ADAPTER_REJECTED',
});
assert.equal(invalidTargetedTable.status, 'unsupported');
assert.equal(invalidTargetedTable.activeRendererKey, 'core.unsupported');
assert.equal(invalidTargetedTable.reasonCode, 'SCENE_DRIVER_NORMALIZED_ADAPTER_REJECTED');

const unsupported = resolveActionSurfaceRenderer({
  semantic: 'unknown' as never, label: '', groupField: '', groupedLanes: false, config: {},
}, 'unknown');
assert.equal(unsupported.status, 'unsupported');
assert.equal(unsupported.activeRendererKey, 'core.unsupported');
assert.equal(unsupported.reasonCode, 'ACTION_SURFACE_RENDERER_NOT_REGISTERED');

console.log('[action-surface-renderer-registry] PASS');
