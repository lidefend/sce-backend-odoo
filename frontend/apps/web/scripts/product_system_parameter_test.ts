/**
 * Behavioural lock for the controlled system parameter consumption surface.
 *
 * Catalog, impact preview and change records are consumed exactly as declared;
 * a declared surface that is malformed must stop with a ContractGapError, and a
 * planned parameter is never presented as editable. The frontend does not derive
 * value validity, impact scope or rollback semantics.
 */
import assert from 'node:assert/strict';

import {
  isProductSystemParameterGap,
  parameterStatusLabel,
  projectChangeRecord,
  projectImpactPreview,
  projectSystemParameterCatalog,
} from '../src/app/productSystemParameterProjection';

let cases = 0;

function rejected(run: () => unknown, label: string, missing: string): void {
  try {
    run();
  } catch (error) {
    assert.ok(isProductSystemParameterGap(error), `${label}: expected ContractGapError`);
    assert.equal((error as Error & { defect?: { missing?: string } }).defect?.missing, missing, `${label}: defect path`);
    cases += 1;
    return;
  }
  assert.fail(`${label}: expected the surface to stop`);
}

const catalog = {
  schema_version: 'product_system_parameter_catalog.v1',
  status: 'locked',
  objective: '',
  categories: [{ key: 'business_rules', label: '业务规则' }],
  parameters: [
    {
      key: 'cost_ledger_source',
      category: 'business_rules',
      label: '成本台账自动归集来源',
      description: '成本来源',
      type: 'selection',
      default: 'account_move',
      allowed_values: ['account_move', 'purchase_order', 'stock_move', 'disabled'],
      scope: 'company',
      maintainer_role: 'business_config_admin',
      status: 'available',
      available: true,
      authority: 'res.company.sc_cost_from_account_move',
      impact: { surfaces: ['成本台账'], summary: '影响成本归集', risk_level: 'medium' },
      current_value: 'account_move',
    },
    {
      key: 'tax_rate',
      category: 'finance_accounting',
      label: '默认税率',
      description: '税率',
      type: 'number',
      default: 0.09,
      min: 0,
      max: 1,
      scope: 'company',
      maintainer_role: 'business_config_admin',
      status: 'planned',
      available: false,
      authority: 'sc.product.system.settings',
      impact: { surfaces: ['财务'], summary: '影响税率', risk_level: 'medium' },
    },
  ],
  guardrails: ['no_raw_ir_config_parameter_in_user_entry'],
  success: true,
  reason_code: 'OK',
};

// --- catalog projection preserves declared status and availability -----------
const projected = projectSystemParameterCatalog(catalog);
assert.equal(projected.categories.length, 1);
assert.equal(projected.parameters.length, 2);
assert.equal(projected.parameters[0].available, true, 'available parameter');
assert.equal(projected.parameters[0].status, 'available');
assert.equal(projected.parameters[1].available, false, 'planned parameter is not available');
assert.equal(projected.parameters[1].status, 'planned');
assert.equal(projected.parameters[0].current_value, 'account_move', 'current value preserved');
cases += 5;

// --- malformed catalog stops -------------------------------------------------
rejected(
  () => projectSystemParameterCatalog({ ...catalog, parameters: 'not-a-list' }),
  'non-list parameters',
  'sc.product.system_parameter.catalog.parameters',
);
rejected(
  () => projectSystemParameterCatalog({ ...catalog, parameters: [{ ...catalog.parameters[0], available: 'yes' }] }),
  'non-boolean available',
  'sc.product.system_parameter.catalog.parameters[0].available',
);
rejected(
  () => projectSystemParameterCatalog({ ...catalog, parameters: [{ ...catalog.parameters[0], impact: { surfaces: 'x', summary: 'y' } }] }),
  'malformed impact',
  'sc.product.system_parameter.catalog.parameters[0].impact',
);

// --- impact preview: ok requires impact; rejected preserves reason -----------
const okPreview = projectImpactPreview({
  ok: true,
  parameter: 'cost_ledger_source',
  status: 'available',
  proposed_value: 'stock_move',
  impact: { surfaces: ['成本台账'], summary: '影响', risk_level: 'medium' },
  audit_required: true,
  rollback_required: true,
  change_set_required: true,
});
assert.equal(okPreview.ok, true);
assert.equal(okPreview.parameter, 'cost_ledger_source');
assert.equal(okPreview.change_set_required, true);
cases += 3;

const rejectedPreview = projectImpactPreview({ ok: false, parameter: 'tax_rate', reason: 'not_implemented' });
assert.equal(rejectedPreview.ok, false);
assert.equal(rejectedPreview.reason, 'not_implemented');
cases += 2;

rejected(
  () => projectImpactPreview({ ok: true, parameter: 'cost_ledger_source', impact: {} }),
  'ok preview missing impact',
  'sc.product.system_parameter.preview.impact',
);

// --- change record: valid id passes, invalid id stops ------------------------
const change = projectChangeRecord({
  id: 7,
  parameter_key: 'cost_ledger_source',
  proposed_value: 'stock_move',
  previous_value: 'account_move',
  state: 'published',
  company_id: 1,
  change_reason: '',
  risk_level: 'medium',
  published_at: '2026-10-20',
  rolled_back_at: false,
  audit_json: {},
});
assert.equal(change.id, 7);
assert.equal(change.state, 'published');
cases += 2;

rejected(
  () => projectChangeRecord({ ...change, id: 0 }),
  'zero change id',
  'sc.product.system_parameter.change.id',
);

// --- renderer dispatch on declared statuses ----------------------------------
assert.equal(parameterStatusLabel('available'), '可用');
assert.equal(parameterStatusLabel('planned'), '未发布');
assert.equal(parameterStatusLabel('unknown'), 'unknown');
cases += 3;

console.log(`[product_system_parameter_test] PASS cases=${cases}`);
