import assert from 'node:assert/strict';
import {
  prioritizeExplicitlyEnabledListColumns,
  resolveEnabledListColumns,
} from '../../frontend/apps/web/src/pages/listPage/listColumnVisibility.ts';

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
