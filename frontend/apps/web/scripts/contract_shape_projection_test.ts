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
import { isContractGapError } from '../src/app/contract/contractGap';
import { projectStoredListPreference } from '../src/app/runtime/listPreferenceProjection';
import { resolveEnabledListColumns, resolveListColumnChoices } from '../src/pages/listPage/listColumnVisibility';
import { ref } from 'vue';

import {
  extractListFieldSemanticsFromContract,
  useActionViewContractShapeRuntime,
} from '../src/app/action_runtime/useActionViewContractShapeRuntime';
import { collectUnifiedPageContractV2Widgets } from '../src/app/contracts/unifiedPageContractV2';
import { resolveDeclaredAssigneeQuery } from '../src/app/runtime/actionViewAssigneeOptionsContract';
import { resolveDeclaredKanbanTitleField } from '../src/app/runtime/actionViewKanbanTitleField';
import {
  resolveDeclaredFilterBudget,
  resolveDeclaredGroupByLabel,
  resolveDeclaredPrimaryFilterBudget,
} from '../src/app/action_runtime/useActionViewFilterComputedRuntime';
import { resolveDeclaredSurfaceBudget } from '../src/app/runtime/actionViewSurfacePolicyBudget';
import {
  resolveContractV2FieldDescriptorMap,
  resolveContractV2FormFieldMap,
} from '../src/app/contracts/v2/store';
import type { ContractV2NormalizedStore } from '../src/app/contracts/v2/types';
import {
  presentCollectionKanbanCell,
} from '../src/app/presentation/collectionKanbanPresentation';
import { presentDeclaredBusinessValue } from '../src/app/presentation/businessValuePresentation';
import { normalizeListRelationValue, presentListCell } from '../src/pages/listPage/listCellPresentation';
import { hasDeclaredAttachmentIdentity } from '../src/utils/fieldSemantics';

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
    componentKey: 'sc.select.tags',
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

// List-column transport declarations remain available, but componentConfig is
// not a second field-semantic authority. A conflicting transport payload must
// not replace the descriptor's type, widget, money field, precision, unit,
// temporal authority, selection or visibility.
const semanticAuthorityWidget = {
  widgetId: 'field.amount_display',
  fieldCode: 'amount_display',
  label: 'Container label',
  widgetType: 'table',
  componentKey: 'sc.value.percentage',
  fieldDescriptor: {
    fieldCode: 'amount_display',
    label: 'Declared amount',
    fieldType: 'float',
    widgetType: 'float_time',
    semanticType: 'duration',
    componentKey: 'sc.value.duration',
    currencyField: 'currency_id',
    digits: [16, 3],
    unit: { kind: 'duration', code: 'hour', label: '小时' },
    temporal: { kind: 'datetime', timezoneAuthority: 'user' },
    sortable: true,
    invisible: false,
  },
  componentConfig: {
    fieldType: 'char',
    nativeWidget: 'text',
    data_type: 'char',
    widget: 'text',
    componentKey: 'sc.value.percentage',
    currency_field: 'wrong_currency_id',
    digits: [4, 1],
    unit: { kind: 'percent', code: 'percent', label: '%' },
    temporal: { kind: 'date', timezoneAuthority: 'record' },
    selection: [['wrong', 'Wrong']],
    relation: 'res.partner',
    invisible: true,
    display_field: 'amount_display',
    value_field: 'amount',
    sort_field: 'amount',
    filter_field: 'amount',
    export_field: 'amount',
    aggregate: 'sum',
  },
};
const semanticAuthorityStore = {
  snapshot: { layoutContract: { listProfile: {} }, actionContract: { surfacePolicies: {} } },
  widgetsById: new Map([[semanticAuthorityWidget.widgetId, semanticAuthorityWidget]]),
  widgetsByFieldCode: new Map([[semanticAuthorityWidget.fieldCode, semanticAuthorityWidget]]),
  widgetsByFieldCodeAll: new Map([[semanticAuthorityWidget.fieldCode, [semanticAuthorityWidget]]]),
  widgetStatusById: new Map(),
  primaryDataSource: {},
} as unknown as ContractV2NormalizedStore;
const semanticAuthorityRows = extractListFieldSemanticsFromContract(semanticAuthorityStore);
check(semanticAuthorityRows[0]?.data_type, 'float', 'request field semantics use descriptor fieldType');
check(semanticAuthorityRows[0]?.widget, 'float_time', 'request field semantics use descriptor widgetType');
check(semanticAuthorityRows[0]?.currency_field, 'currency_id', 'request dependencies use descriptor currencyField');
check(semanticAuthorityRows[0]?.value_field, 'amount', 'list transport keeps its declared value field');
check(semanticAuthorityRows[0]?.sort_field, 'amount', 'list transport keeps its declared sort field');

const semanticAuthorityOption = runtime.resolveListColumnOptions(
  semanticAuthorityStore,
  { columns: ['amount_display'] },
)[0];
assert.ok(semanticAuthorityOption);
check(semanticAuthorityOption?.label, 'Declared amount', 'list column label comes from fieldDescriptor');
check(semanticAuthorityOption?.type, 'float', 'list column type comes from fieldDescriptor');
check(semanticAuthorityOption?.widget, 'float_time', 'list column widget comes from fieldDescriptor');
check(semanticAuthorityOption?.componentKey, 'sc.value.duration', 'list column component identity comes from fieldDescriptor');
check(semanticAuthorityOption?.currencyField, 'currency_id', 'list column currency field comes from fieldDescriptor');
check(JSON.stringify(semanticAuthorityOption?.digits), JSON.stringify([16, 3]), 'list column digits come from fieldDescriptor');
check(semanticAuthorityOption?.unit?.code, 'hour', 'list column unit comes from fieldDescriptor');
check(semanticAuthorityOption?.temporal?.kind, 'datetime', 'list column temporal authority comes from fieldDescriptor');
check(semanticAuthorityOption?.relation, undefined, 'componentConfig cannot introduce a relation target');
check(semanticAuthorityOption?.selection, undefined, 'componentConfig cannot introduce selection semantics');
check(semanticAuthorityOption?.defaultVisible, true, 'componentConfig cannot override descriptor visibility');
check(semanticAuthorityOption?.sortable, true, 'list column sortability comes from fieldDescriptor');
check(semanticAuthorityOption?.valueField, 'amount', 'list transport keeps its declared value field');
check(semanticAuthorityOption?.sortField, 'amount', 'list transport keeps its declared sort field');

const synthesizedV2Widgets = collectUnifiedPageContractV2Widgets({
  pageInfo: {
    pageId: 'contract-closure',
    contractVersion: '2.7.0',
    clientType: 'web_pc',
  },
  layoutContract: {
    containerTree: [{
      containerId: 'root',
      children: [],
      widgetList: [{
        widgetId: 'field.partner_id',
        widgetType: 'many2one',
        fieldCode: 'partner_id',
        label: 'Partner',
        componentKey: 'sc.relation',
        fieldDescriptor: {
          fieldType: 'many2one',
          relation: 'res.partner',
        },
        componentConfig: {
          fieldType: 'char',
          relation: 'res.users',
          relationEntry: { page_size: 999 },
          relationActiveActions: { create: true, write: true },
          widgetOptions: { readonly_empty_text: 'forged' },
          subview: { policies: { can_create: true } },
          selection: [['forged', 'Forged']],
          nativeWidget: 'many2one',
        },
      }],
    }],
  },
  actionContract: { actionRuleList: [] },
});
const synthesizedV2Widget = synthesizedV2Widgets[0];
assert.ok(synthesizedV2Widget);
check(synthesizedV2Widget?.fieldType, 'many2one', 'legacy widget projection reads field type from fieldDescriptor');
check(synthesizedV2Widget?.relation, 'res.partner', 'legacy widget projection reads relation from fieldDescriptor');
check(synthesizedV2Widget?.componentConfig?.nativeWidget, 'many2one', 'transport-only widget config is preserved');
for (const key of [
  'fieldType', 'relation', 'relationEntry', 'relationActiveActions',
  'widgetOptions', 'subview', 'selection',
]) {
  check(
    synthesizedV2Widget?.componentConfig?.[key],
    undefined,
    `legacy widget projection removes ${key} from componentConfig`,
  );
}

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
const descriptors: Record<string, Record<string, unknown>> = {
  invisible: {fieldCode:'invisible',label:'Invisible',fieldType:'char',widgetType:'text',componentKey:'sc.display.text',invisible:true},
  column_invisible: {fieldCode:'column_invisible',label:'Column invisible',fieldType:'char',widgetType:'text',componentKey:'sc.display.text',invisible:true},
};
const widgets = names.map(name => ({
  widgetId:name,
  fieldCode:name,
  componentConfig:configs[name] || {},
  fieldDescriptor:descriptors[name] || {
    fieldCode:name,
    label:name,
    fieldType:'char',
    widgetType:'text',
    componentKey:'sc.display.text',
  },
}));
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
    componentKey: 'sc.value.duration',
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
    componentKey: 'sc.value.percentage',
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

// The strict widget descriptor is the final declaration carrier. The form
// projection must retain every semantic that has a downstream consumer; a
// second projection cannot silently reduce it back to the Odoo scalar shape.
const declaredFacetWidgets = [
  {
    widgetId: 'source-reference',
    fieldCode: 'sc_source_res_id',
    label: 'Source',
    widgetType: 'many2one_reference',
    componentConfig: { fieldType: 'many2one_reference' },
    fieldDescriptor: {
      fieldCode: 'sc_source_res_id',
      fieldType: 'many2one_reference',
      semanticType: 'reference',
      componentKey: 'sc.display.text',
      referenceModelField: 'sc_source_model',
    },
  },
  {
    widgetId: 'binary-content',
    fieldCode: 'binary_content',
    label: 'Attachment',
    widgetType: 'binary',
    componentConfig: { fieldType: 'binary' },
    fieldDescriptor: {
      fieldCode: 'binary_content',
      fieldType: 'binary',
      filename: 'attachment_name',
    },
  },
  {
    widgetId: 'progress',
    fieldCode: 'progress',
    label: 'Progress',
    widgetType: 'percentage',
    componentConfig: { fieldType: 'float' },
    fieldDescriptor: {
      fieldCode: 'progress',
      fieldType: 'float',
      semanticType: 'percentage',
      componentKey: 'sc.value.percentage',
      digits: [16, 2],
      unit: { kind: 'percent', code: 'percent', label: '%' },
    },
  },
  {
    widgetId: 'occurred-at',
    fieldCode: 'occurred_at',
    label: 'Occurred at',
    widgetType: 'datetime',
    componentConfig: { fieldType: 'datetime' },
    fieldDescriptor: {
      fieldCode: 'occurred_at',
      fieldType: 'datetime',
      semanticType: 'datetime',
      temporal: { kind: 'datetime', timezoneAuthority: 'user' },
    },
  },
  {
    widgetId: 'evidence',
    fieldCode: 'evidence_ids',
    label: 'Evidence',
    widgetType: 'many2many',
    componentConfig: { fieldType: 'many2many' },
    fieldDescriptor: {
      fieldCode: 'evidence_ids',
      fieldType: 'many2many',
      relation: 'ir.attachment',
      attachmentRole: 'evidence',
    },
  },
];
const declaredFacetStore = {
  snapshot: { layoutContract: { listProfile: {} }, actionContract: { surfacePolicies: {} } },
  widgetsById: new Map(declaredFacetWidgets.map(widget => [widget.widgetId, widget])),
  widgetsByFieldCode: new Map(declaredFacetWidgets.map(widget => [widget.fieldCode, widget])),
  widgetsByFieldCodeAll: new Map(declaredFacetWidgets.map(widget => [widget.fieldCode, [widget]])),
  widgetStatusById: new Map(),
  primaryDataSource: {},
} as unknown as ContractV2NormalizedStore;
const canonicalFacetFields = resolveContractV2FieldDescriptorMap(declaredFacetStore);
const formFacetFields = resolveContractV2FormFieldMap(declaredFacetStore);
check(
  canonicalFacetFields.sc_source_res_id?.referenceModelField,
  'sc_source_model',
  'normalized field descriptor preserves the polymorphic model pointer',
);
check(
  formFacetFields.sc_source_res_id?.referenceModelField,
  'sc_source_model',
  'form field projection preserves the polymorphic model pointer',
);
check(
  canonicalFacetFields.binary_content?.filename,
  'attachment_name',
  'descriptor-only filename survives normalization',
);
check(
  formFacetFields.binary_content?.filename,
  'attachment_name',
  'descriptor-only filename survives form projection',
);
check(
  JSON.stringify(formFacetFields.progress?.digits),
  JSON.stringify([16, 2]),
  'form field projection preserves declared digits',
);
check(
  formFacetFields.progress?.unit?.label,
  '%',
  'form field projection preserves declared unit',
);
check(
  formFacetFields.occurred_at?.temporal?.timezoneAuthority,
  'user',
  'form field projection preserves declared temporal authority',
);
check(
  formFacetFields.evidence_ids?.attachmentRole,
  'evidence',
  'form field projection preserves declared attachment role',
);
check(
  presentDeclaredBusinessValue({
    field: formFacetFields.progress!,
    value: 12.34,
  }).text,
  '12.34%',
  'business-value presentation consumes digits and unit from the form projection',
);
check(
  hasDeclaredAttachmentIdentity(formFacetFields.evidence_ids),
  true,
  'attachment behavior consumes the form projection without recovering a second carrier',
);

const declaredAssigneeQuery = resolveDeclaredAssigneeQuery({
  model: 'res.users',
  fields: ['id', 'display_name'],
  domain: [['active', '=', true]],
  order: 'display_name asc',
  limit: 25,
});
check(declaredAssigneeQuery.model, 'res.users', 'assignee query consumes the declared model');
check(declaredAssigneeQuery.fields.join(','), 'id,display_name', 'assignee query consumes declared fields verbatim');
check(declaredAssigneeQuery.order, 'display_name asc', 'assignee query consumes declared ordering');
check(declaredAssigneeQuery.limit, 25, 'assignee query consumes declared limit');
for (const [invalidContract, expected] of [
  [null, 'assignee_options.fields'],
  [{ model: 'res.users', fields: [], domain: [], order: 'name asc', limit: 80 }, 'assignee_options.fields'],
  [{ model: 'res.users', fields: ['id'], domain: 'bad', order: 'name asc', limit: 80 }, 'assignee_options.domain'],
  [{ model: 'res.users', fields: ['id'], domain: [], order: '', limit: 80 }, 'assignee_options.order'],
  [{ model: 'res.users', fields: ['id'], domain: [], order: 'name asc', limit: 0 }, 'assignee_options.limit'],
] as const) {
  assert.throws(
    () => resolveDeclaredAssigneeQuery(invalidContract),
    (error: unknown) => isContractGapError(error) && error.defect.missing.includes(expected),
    `assignee options must stop when ${expected} is missing or invalid`,
  );
}
check(
  resolveDeclaredKanbanTitleField('project_title', ['id', 'project_title']),
  'project_title',
  'Kanban consumes the declared title field',
);
check(
  resolveDeclaredKanbanTitleField('', []),
  '',
  'non-Kanban views do not invent a title field',
);
for (const [hint, fields] of [
  ['', ['name', 'display_name']],
  ['missing_title', ['name', 'display_name']],
] as const) {
  assert.throws(
    () => resolveDeclaredKanbanTitleField(hint, fields),
    (error: unknown) => isContractGapError(error)
      && error.defect.missing === 'list_profile.kanban_profile.title_field',
    'Kanban must stop instead of falling back to name/display_name/first field/id',
  );
}
check(
  resolveDeclaredPrimaryFilterBudget({ filters_primary_max: 0 }),
  0,
  'primary filter budget preserves an explicit zero',
);
check(
  resolveDeclaredPrimaryFilterBudget({ filters_primary_max: 3 }),
  3,
  'primary filter budget consumes the declared value',
);
check(
  resolveDeclaredGroupByLabel([
    { field: 'manager_id', label: '按项目经理' },
    { field: 'state', label: '' },
  ], 'manager_id'),
  '按项目经理',
  'active grouping consumes the declared group label',
);
check(
  resolveDeclaredGroupByLabel([{ field: 'manager_id', label: '按项目经理' }], 'unknown_field'),
  '',
  'an unknown grouping field never falls back to the technical field name',
);
check(
  resolveDeclaredGroupByLabel([{ field: 'state', label: '' }], 'state'),
  '',
  'an undeclared grouping label remains empty',
);
const unsupportedSortOptions = runtime.buildListSortOptions({
  snapshot: {
    layoutContract: { listProfile: {} },
    actionContract: { surfacePolicies: {} },
    searchContract: {
      default_order: 'name asc',
      sort_options: [{ value: 'hidden_order', label: 'Undeclared sort' }],
    },
  },
  widgetsById: new Map(),
  widgetsByFieldCode: new Map(),
  widgetsByFieldCodeAll: new Map(),
  widgetStatusById: new Map(),
  primaryDataSource: {},
} as unknown as ContractV2NormalizedStore, '', '排序');
check(
  unsupportedSortOptions.some((option) => option.value === 'hidden_order'),
  false,
  'the frontend ignores a sort carrier rejected by the current contract decoder',
);
for (const invalid of [{}, { filters_primary_max: -1 }, { filters_primary_max: 1.5 }, { filters_primary_max: '3' }]) {
  assert.throws(
    () => resolveDeclaredPrimaryFilterBudget(invalid),
    (error: unknown) => isContractGapError(error)
      && error.defect.missing === 'surface_policies.filters_primary_max',
    'primary filter budget must stop instead of defaulting or clamping',
  );
}
check(
  resolveDeclaredFilterBudget({ filters_max: 0 }, 'filters_max'),
  0,
  'total filter budget preserves an explicit zero',
);
check(
  resolveDeclaredFilterBudget({ filters_max: 12 }, 'filters_max'),
  12,
  'total filter budget consumes the declared value instead of the former eight-item cap',
);
for (const invalid of [{}, { filters_max: -1 }, { filters_max: 2.5 }, { filters_max: '12' }]) {
  assert.throws(
    () => resolveDeclaredFilterBudget(invalid, 'filters_max'),
    (error: unknown) => isContractGapError(error)
      && error.defect.missing === 'surface_policies.filters_max',
    'total filter budget must stop instead of silently truncating to eight',
  );
}
check(
  resolveDeclaredSurfaceBudget({ actions_primary_max: 3 }, 'actions_primary_max'),
  3,
  'primary action budget consumes the declared value',
);
for (const invalid of [{}, { actions_primary_max: -1 }, { actions_primary_max: 2.5 }, { actions_primary_max: '3' }]) {
  assert.throws(
    () => resolveDeclaredSurfaceBudget(invalid, 'actions_primary_max'),
    (error: unknown) => isContractGapError(error)
      && error.defect.missing === 'surface_policies.actions_primary_max',
    'primary action budget must stop instead of defaulting to four',
  );
}

console.log(`[frontend.contract.shape.projection] PASS cases=${cases}`);
