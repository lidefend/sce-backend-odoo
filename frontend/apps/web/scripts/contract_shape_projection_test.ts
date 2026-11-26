/**
 * Executable proof for PAYMENT-REQUEST-CHAIN-ALIGNMENT F2.
 *
 * Defect this covers (found while confirming the payment-request chain): the
 * list-profile projection built its `batch_policy` object eagerly, so a
 * fail-closed declaration assertion ran before the "no declaration -> no
 * projection" short circuit.  On a real page the first evaluation happens
 * before `ui.contract.v2` resolves, so the call threw `ContractGapError`, the
 * consuming computed stayed cached as `undefined`, and the later contract-ready
 * read crashed with `Cannot read properties of undefined (reading 'map')`.
 *
 * The two directions that must both hold:
 *   - no contract yet, or a contract that declares no list-profile batch
 *     policy, projects nothing and does not throw;
 *   - a declared but incomplete batch policy still fails closed.
 */
import assert from 'node:assert/strict';
import { projectStoredListPreference } from '../src/app/runtime/listPreferenceProjection';
import { resolveEnabledListColumns, resolveListColumnChoices } from '../src/pages/listPage/listColumnVisibility';
import { ref } from 'vue';

import {
  extractListFieldSemanticsFromContract,
  useActionViewContractShapeRuntime,
} from '../src/app/action_runtime/useActionViewContractShapeRuntime';
import type { ContractV2NormalizedStore } from '../src/app/contracts/v2/types';
import { presentCollectionKanbanCell } from '../src/app/presentation/collectionKanbanPresentation';
import { normalizeListRelationValue, presentListCell } from '../src/pages/listPage/listCellPresentation';

let cases = 0;
const check = (actual: unknown, expected: unknown, label: string) => {
  assert.equal(actual, expected, label);
  cases += 1;
};

assert.deepEqual(
  normalizeListRelationValue([71, '德阳市城市某某建设投资集团有限公司'], [71, '德阳市城市某某建设投资集团有限公司']),
  [71, '德阳市城市某某建设投资集团有限公司'],
  'an ORM many2one tuple must not be wrapped a second time when displayField equals valueField',
);
cases += 1;
assert.deepEqual(
  normalizeListRelationValue('张建国', 10),
  [10, '张建国'],
  'a flattened display field still binds to its declared underlying relation identity',
);
cases += 1;
assert.deepEqual(
  normalizeListRelationValue({ id: 10, display_name: '张建国' }, 10),
  { id: 10, display_name: '张建国' },
  'an already structured relation value remains unchanged',
);
cases += 1;
assert.equal(
  normalizeListRelationValue(false, false),
  false,
  'an Odoo false many2one remains empty instead of becoming a labeled relation',
);
cases += 1;
assert.equal(
  normalizeListRelationValue(null, 0),
  null,
  'a missing many2one identity remains empty',
);
cases += 1;
assert.deepEqual(
  normalizeListRelationValue([], []),
  [],
  'an empty many2many value remains empty instead of becoming a nested member',
);
cases += 1;

const runtime = useActionViewContractShapeRuntime({
  pageText: (_key: string, fallback: string) => fallback,
  actionContract: ref<ContractV2NormalizedStore | null>(null),
  advancedFields: ref<string[]>([]),
  activeGroupByField: ref(''),
});

// A table owns the collection container, while its field descriptor owns the
// cell widget. Sending the container type to api.data makes the backend skip
// the x2many display-label projection, leaving raw ids for the renderer.
const tagCollectionWidget = {
  widgetId: 'field.company_ids',
  widgetType: 'table',
  fieldCode: 'company_ids',
  label: '允许公司',
  componentKey: 'sc.select.tags',
  fieldDescriptor: {
    fieldCode: 'company_ids',
    fieldType: 'many2many',
    widgetType: 'many2many_tags',
  },
  componentConfig: {
    fieldType: 'many2many',
    nativeWidget: 'many2many_tags',
  },
};
const tagCollectionStore = {
  snapshot: { layoutContract: { listProfile: {} }, actionContract: { surfacePolicies: {} } },
  widgetsById: new Map([[tagCollectionWidget.widgetId, tagCollectionWidget]]),
  widgetsByFieldCode: new Map([[tagCollectionWidget.fieldCode, tagCollectionWidget]]),
  widgetsByFieldCodeAll: new Map([[tagCollectionWidget.fieldCode, [tagCollectionWidget]]]),
  widgetStatusById: new Map(),
  primaryDataSource: {},
} as unknown as ContractV2NormalizedStore;
const tagCollectionSemantics = extractListFieldSemanticsFromContract(tagCollectionStore);
check(
  tagCollectionSemantics[0]?.widget,
  'many2many_tags',
  'list field semantics preserve the field widget instead of the table container widget',
);

const storeWithListProfile = (listProfile: Record<string, unknown>) => ({
  snapshot: {
    layoutContract: { listProfile },
    actionContract: { surfacePolicies: {} },
  },
}) as unknown as ContractV2NormalizedStore;

// 1) Readiness: the contract has not arrived yet, so there is nothing to
//    project.  This used to throw and poison the consuming computed.
check(runtime.extractListProfile(null), null, 'a missing contract must not project a list profile');
check(runtime.extractListProfile(undefined), null, 'an undefined contract must not project a list profile');

// 2) A loaded contract that declares columns but no list-profile batch policy is
//    not a declaration gap: behaviour comes from surface_policies.
const declared = runtime.extractListProfile(storeWithListProfile({
  columns: ['name', 'amount'],
  preference_policy: { allow_visibility: true, allow_order: true, allow_width: true, locked_columns: [], must_request_columns: ['name', 'amount'] },
  column_labels: { name: '申请单号' },
}));
check(declared?.columns.join(','), 'name,amount', 'declared columns must project');
check(declared?.batch_policy, undefined, 'an undeclared batch policy must stay undeclared');

// 3) A declared-but-incomplete batch policy is a real gap and must still stop.
assert.throws(
  () => runtime.extractListProfile(storeWithListProfile({
    columns: ['name'],
    batch_policy: { available_actions: ['export'] },
  })),
  /list_profile\.batch_policy\.enabled/,
  'a declared batch policy without enabled must still fail closed',
);
cases += 1;

assert.throws(() => runtime.extractListProfile(storeWithListProfile({columns: ['name']})), /preference_policy/);
cases += 1;

// Contract denial must survive the complete parse -> preference -> display chain.
const names = ['normal','optional','invisible','column_invisible','status_hidden','no_auth'];
const configs: Record<string, Record<string, unknown>> = {optional:{optional:'hide'},invisible:{invisible:true},column_invisible:{column_invisible:true}};
const widgets = names.map(name => ({widgetId:name,fieldCode:name,componentConfig:configs[name] || {}}));
const fixture = {
  snapshot: { layoutContract: { listProfile: {} }, actionContract: { surfacePolicies: {} } },
  widgetsById: new Map(widgets.map(widget => [widget.widgetId,widget])),
  widgetsByFieldCode: new Map(widgets.map(widget => [widget.fieldCode,widget])),
  widgetsByFieldCodeAll: new Map(widgets.map(widget => [widget.fieldCode,[widget]])),
  widgetStatusById: new Map([['status_hidden',{visible:false}],['no_auth',{auth:'none'}]]),
  primaryDataSource: { columnsSchema: [{name:'optional',optional:'hide'},{name:'invisible',invisible:true},{name:'column_invisible',column_invisible:true}] },
} as unknown as ContractV2NormalizedStore;
const options = runtime.resolveListColumnOptions(fixture,{columns:names});
assert.deepEqual(options.map(column=>column.name),['normal','optional']);
const policy = {allow_visibility:true,allow_order:true,allow_width:true,locked_columns:[],must_request_columns:['normal']};
const effective = projectStoredListPreference({visible_columns:names},policy,options.map(column=>column.name));
const visibility = Object.fromEntries((effective.visible_columns || []).map(name=>[name,true]));
assert.deepEqual(resolveEnabledListColumns(options,[],visibility),['normal','optional']);
cases += 1;

const deniedOptions = runtime.resolveListColumnOptions(fixture,{columns:['status_hidden','no_auth']});
const deniedChoices = resolveListColumnChoices(deniedOptions,() => { throw new Error('revived denied columns'); });
assert.deepEqual(resolveEnabledListColumns(deniedChoices,['status_hidden','no_auth'],{status_hidden:true,no_auth:true}),[]);
cases += 1;

const duplicate = {widgetId:'normal-denied',fieldCode:'normal'};
fixture.widgetsByFieldCodeAll.set('normal',[widgets[0],duplicate] as never);
fixture.widgetStatusById.set('normal-denied',{widgetId:'normal-denied',visible:false});
assert.throws(() => runtime.resolveListColumnOptions(fixture,{columns:['normal']}), /Ambiguous list column authority/);
cases += 1;

// A duration column must cross the real Contract V2 column-option producer
// before List or Kanban consumes it. Injecting componentKey directly into the
// presentation helpers would miss this projection boundary.
const durationWidget = {
  widgetId: 'duration-hours',
  fieldCode: 'duration_hours',
  label: 'Hours',
  widgetType: 'number',
  componentKey: 'sc.value.duration',
  componentConfig: { fieldType: 'float', nativeWidget: 'float_time' },
  fieldDescriptor: {
    fieldType: 'float',
    digits: [16, 3],
    unit: { kind: 'duration', code: 'hour', label: '小时' },
  },
};
const durationStore = {
  snapshot: { layoutContract: { listProfile: {} }, actionContract: { surfacePolicies: {} } },
  widgetsById: new Map([[durationWidget.widgetId, durationWidget]]),
  widgetsByFieldCode: new Map([[durationWidget.fieldCode, durationWidget]]),
  widgetsByFieldCodeAll: new Map([[durationWidget.fieldCode, [durationWidget]]]),
  widgetStatusById: new Map(),
  primaryDataSource: {},
} as unknown as ContractV2NormalizedStore;
const durationOption = runtime.resolveListColumnOptions(durationStore, { columns: ['duration_hours'] })[0];
assert.ok(durationOption);
check(durationOption?.componentKey, 'sc.value.duration', 'collection projection preserves duration component identity');
check(durationOption?.unit?.label, '小时', 'collection projection preserves declared duration unit');
check(presentListCell({
  raw: 1.5,
  column: { ...durationOption, field: durationOption.name },
}).text, '1.500 小时', 'List consumes projected duration identity and unit');
check(presentCollectionKanbanCell({
  field: 'duration_hours',
  value: 1.5,
  columnOptions: [durationOption],
}).text, '1.500 小时', 'Kanban consumes projected duration identity and unit');

// Percentage is an existing declared component identity. It must cross the same
// Contract V2 collection producer before List or Kanban interprets the value.
const percentageWidget = {
  widgetId: 'percentage',
  fieldCode: 'completion_ratio',
  label: 'Ratio',
  widgetType: 'percentage',
  componentKey: 'sc.value.percentage',
  componentConfig: { fieldType: 'float', digits: [16, 4] },
  fieldDescriptor: {
    fieldType: 'float',
    digits: [16, 4],
    unit: { kind: 'percent', code: 'percent', label: '%' },
  },
};
const percentageStore = {
  snapshot: { layoutContract: { listProfile: {} }, actionContract: { surfacePolicies: {} } },
  widgetsById: new Map([[percentageWidget.widgetId, percentageWidget]]),
  widgetsByFieldCode: new Map([[percentageWidget.fieldCode, percentageWidget]]),
  widgetsByFieldCodeAll: new Map([[percentageWidget.fieldCode, [percentageWidget]]]),
  widgetStatusById: new Map(),
  primaryDataSource: {},
} as unknown as ContractV2NormalizedStore;
const percentageOption = runtime.resolveListColumnOptions(percentageStore, { columns: ['completion_ratio'] })[0];
check(percentageOption?.componentKey, 'sc.value.percentage', 'collection projection preserves percentage component identity');
check(JSON.stringify(percentageOption?.digits), JSON.stringify([16, 4]), 'collection projection preserves declared float digits');
check(presentListCell({
  raw: 12.5,
  column: { ...percentageOption, field: percentageOption.name },
}).text, '12.5000%', 'List consumes projected percentage identity and precision');
check(presentCollectionKanbanCell({
  field: 'completion_ratio',
  value: 12.5,
  columnOptions: [percentageOption],
}).text, '12.5000%', 'Kanban consumes projected percentage identity and precision');

const statusWidget = {
  widgetId: 'status',
  fieldCode: 'state',
  label: 'State',
  widgetType: 'selection',
  componentKey: 'sc.display.status',
  componentConfig: {
    fieldType: 'selection',
    selection: [['pending', '待处理']],
  },
  fieldDescriptor: {
    fieldType: 'selection',
    componentKey: 'sc.display.status',
    selection: [['pending', '待处理']],
  },
};
const statusStore = {
  snapshot: { layoutContract: { listProfile: {} }, actionContract: { surfacePolicies: {} } },
  widgetsById: new Map([[statusWidget.widgetId, statusWidget]]),
  widgetsByFieldCode: new Map([[statusWidget.fieldCode, statusWidget]]),
  widgetsByFieldCodeAll: new Map([[statusWidget.fieldCode, [statusWidget]]]),
  widgetStatusById: new Map(),
  primaryDataSource: {},
} as unknown as ContractV2NormalizedStore;
const statusOption = runtime.resolveListColumnOptions(statusStore, { columns: ['state'] })[0];
check(statusOption?.componentKey, 'sc.display.status', 'collection projection preserves status component identity');
check(presentListCell({
  raw: 'pending',
  column: { ...statusOption, field: statusOption.name },
}).text, '待处理', 'List consumes projected status identity');

const unknownWidget = {
  ...statusWidget,
  widgetId: 'unknown-component',
  fieldCode: 'unknown_component',
  componentKey: 'sc.unknown.component',
  fieldDescriptor: { ...statusWidget.fieldDescriptor, componentKey: 'sc.unknown.component' },
};
const unknownStore = {
  ...statusStore,
  widgetsById: new Map([[unknownWidget.widgetId, unknownWidget]]),
  widgetsByFieldCode: new Map([[unknownWidget.fieldCode, unknownWidget]]),
  widgetsByFieldCodeAll: new Map([[unknownWidget.fieldCode, [unknownWidget]]]),
} as unknown as ContractV2NormalizedStore;
assert.throws(
  () => runtime.resolveListColumnOptions(unknownStore, { columns: ['unknown_component'] }),
  { name: 'ContractGapError' },
  'an unregistered declared component identity must stop instead of being dropped',
);
cases += 1;

// Attachment actions cross the same producer as any other field identity. A
// relation target and role are both required before List or FieldValue may
// expose link behavior.
const attachmentWidget = {
  widgetId: 'invoice-evidence',
  fieldCode: 'invoice_evidence_ids',
  label: '发票证据',
  widgetType: 'many2many',
  componentConfig: { fieldType: 'many2many' },
  fieldDescriptor: {
    fieldCode: 'invoice_evidence_ids',
    fieldType: 'many2many',
    relation: 'ir.attachment',
    attachmentRole: 'invoice_evidence',
  },
};
const attachmentStore = {
  snapshot: { layoutContract: { listProfile: {} }, actionContract: { surfacePolicies: {} } },
  widgetsById: new Map([[attachmentWidget.widgetId, attachmentWidget]]),
  widgetsByFieldCode: new Map([[attachmentWidget.fieldCode, attachmentWidget]]),
  widgetsByFieldCodeAll: new Map([[attachmentWidget.fieldCode, [attachmentWidget]]]),
  widgetStatusById: new Map(),
  primaryDataSource: {},
} as unknown as ContractV2NormalizedStore;
const attachmentOption = runtime.resolveListColumnOptions(
  attachmentStore,
  { columns: ['invoice_evidence_ids'] },
)[0];
check(attachmentOption?.relation, 'ir.attachment', 'collection projection preserves attachment relation identity');
check(attachmentOption?.attachmentRole, 'invoice_evidence', 'collection projection preserves attachment role');

console.log(`[frontend.contract.shape.projection] PASS cases=${cases}`);
