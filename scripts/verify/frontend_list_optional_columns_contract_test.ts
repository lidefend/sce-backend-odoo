import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  prioritizeExplicitlyEnabledListColumns,
  resolveEnabledListColumns,
  resolveResponsiveListColumns,
} from '../../frontend/apps/web/src/pages/listPage/listColumnVisibility.ts';
import { deriveListColumnWidth, listColumnAdaptiveFloor, listColumnSemanticTextRole } from '../../frontend/apps/web/src/pages/listPage/listColumnWidth.ts';

const columns = [
  { name: 'name', defaultVisible: true },
  { name: 'company_type', defaultVisible: true },
  { name: 'sc_source_project_name', defaultVisible: false },
];

assert.deepEqual(
  resolveEnabledListColumns(columns, [], {}),
  ['name', 'company_type'],
  'optional=hide columns must not leak into the default desktop or mobile projection',
);

const projectColumns = [
  'name', 'project_code', 'owner_id', 'operation_strategy', 'lifecycle_state', 'user_id', 'manager_id', 'contract_amount',
];
const projectDefaults = Object.fromEntries(projectColumns.map((name) => [name, name !== 'manager_id']));
const criticalColumns = ['name', 'project_code', 'lifecycle_state', 'user_id'];

const actionContractRuntimeSource = readFileSync(
  new URL('../../frontend/apps/web/src/app/action_runtime/useActionViewContractShapeRuntime.ts', import.meta.url),
  'utf8',
);
assert.match(
  actionContractRuntimeSource,
  /cross_device_critical_columns:\s*crossDeviceCriticalColumns/,
  'the action contract shape runtime must explicitly preserve cross-device critical columns',
);

assert.equal(listColumnSemanticTextRole({ field: 'contract_no', label: '合同编号' }), 'identity');
assert.equal(listColumnSemanticTextRole({ field: 'contract_name', label: '合同名称' }), 'description');
assert.equal(listColumnAdaptiveFloor('money'), 128, 'money columns must reserve enough width for business amounts and footer totals');
assert.equal(listColumnAdaptiveFloor('description'), 176, 'business names must retain a readable non-truncating floor');
assert.equal(
  deriveListColumnWidth({ label: '合同金额', type: 'monetary', role: 'money', values: [3665000] }),
  128,
  'derived money width must not shrink below the readable amount floor',
);

for (const client of ['windows-chromium', 'windows-edge', 'harmony-webview']) {
  const defaultDecision = resolveResponsiveListColumns({
    enabledColumns: projectColumns.filter((name) => projectDefaults[name]),
    orderedColumns: projectColumns,
    criticalColumns,
    defaultVisibility: projectDefaults,
    responsiveCandidates: ['name', 'project_code', 'lifecycle_state'],
    capacity: 3,
  });
  assert.equal(defaultDecision.visibleColumns.includes('user_id'), true, `${client}: default project owner must survive responsive capacity`);
  assert.equal(defaultDecision.visibleColumns.includes('manager_id'), false, `${client}: default-hidden project manager must not leak`);
  assert.equal(defaultDecision.trace.find((row) => row.field === 'user_id')?.reasonCode, 'critical_contract');

  const managerEnabled = resolveResponsiveListColumns({
    enabledColumns: projectColumns,
    orderedColumns: projectColumns,
    criticalColumns,
    defaultVisibility: projectDefaults,
    visibility: { manager_id: true },
    responsiveCandidates: ['name', 'project_code', 'lifecycle_state'],
    capacity: 3,
  });
  assert.equal(managerEnabled.visibleColumns.includes('manager_id'), true, `${client}: explicit manager preference must survive responsive capacity`);
  assert.equal(managerEnabled.requiresOverflow, true, `${client}: explicit expansion must become controlled overflow when needed`);
  assert.equal(managerEnabled.trace.find((row) => row.field === 'manager_id')?.reasonCode, 'explicit_visible');

  const ownerHidden = resolveResponsiveListColumns({
    enabledColumns: projectColumns.filter((name) => name !== 'user_id' && name !== 'manager_id'),
    orderedColumns: projectColumns,
    criticalColumns,
    defaultVisibility: projectDefaults,
    visibility: { user_id: false },
    responsiveCandidates: ['name', 'project_code', 'lifecycle_state'],
    capacity: 3,
  });
  assert.equal(ownerHidden.visibleColumns.includes('user_id'), false, `${client}: explicit owner hide must remain authoritative`);
  assert.equal(ownerHidden.trace.find((row) => row.field === 'user_id')?.reasonCode, 'explicit_hidden');
}
assert.deepEqual(
  resolveEnabledListColumns(columns, [], { sc_source_project_name: true }),
  ['name', 'company_type', 'sc_source_project_name'],
  'column settings must still be able to opt in a default-hidden field',
);
assert.deepEqual(
  resolveEnabledListColumns(columns, [], { name: false, company_type: false, sc_source_project_name: true }),
  ['sc_source_project_name'],
  'explicit visibility preferences must remain authoritative',
);
assert.deepEqual(
  prioritizeExplicitlyEnabledListColumns(
    ['name', 'company_type', 'sc_source_project_name'],
    { name: true, company_type: true, sc_source_project_name: false },
    { sc_source_project_name: true },
  ),
  ['sc_source_project_name', 'name', 'company_type'],
  'an explicitly enabled default-hidden field must enter the adaptive desktop budget first',
);

console.log('[frontend_list_optional_columns_contract_test] PASS');
