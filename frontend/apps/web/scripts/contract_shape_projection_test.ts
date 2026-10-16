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

import { useActionViewContractShapeRuntime } from '../src/app/action_runtime/useActionViewContractShapeRuntime';
import type { ContractV2NormalizedStore } from '../src/app/contracts/v2/types';

let cases = 0;
const check = (actual: unknown, expected: unknown, label: string) => {
  assert.equal(actual, expected, label);
  cases += 1;
};

const runtime = useActionViewContractShapeRuntime({
  pageText: (_key: string, fallback: string) => fallback,
  actionContract: ref<ContractV2NormalizedStore | null>(null),
  advancedFields: ref<string[]>([]),
  activeGroupByField: ref(''),
});

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

console.log(`[frontend.contract.shape.projection] PASS cases=${cases}`);
