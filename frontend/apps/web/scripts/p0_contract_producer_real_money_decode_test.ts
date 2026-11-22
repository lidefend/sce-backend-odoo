import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { decodePageOrchestrationContract, resolvePageBlockData, resolvePageBlockCurrencyLabel } from '../src/app/pageOrchestration';
import { presentDeclaredBusinessValue } from '../src/app/presentation/businessValuePresentation';

const path = String(process.env.P0A_MONEY_CONTRACT_PATH || '').trim();
assert.ok(path, 'P0A_MONEY_CONTRACT_PATH is required');
const raw = JSON.parse(readFileSync(path, 'utf8')) as Record<string, unknown>;
const contract = decodePageOrchestrationContract(raw);
assert.equal(contract.contract_version, '2.1.0');
const rows = resolvePageBlockData(contract, 'ds_budget_active_cost_target');
assert.equal(rows.length, 1);
const row = rows[0];
const valueDescriptor = row.fieldDescriptors.value;
assert.equal(valueDescriptor.semanticType, 'money');
assert.equal(valueDescriptor.currencyField, 'company_currency_id');
const currencyLabel = resolvePageBlockCurrencyLabel(row, valueDescriptor.currencyField);
assert.ok(currencyLabel);
const presentation = presentDeclaredBusinessValue({
  field: {
    name: valueDescriptor.fieldCode,
    type: valueDescriptor.fieldType,
    componentKey: valueDescriptor.componentKey,
    widget: valueDescriptor.widgetType,
    digits: valueDescriptor.digits,
    currencyField: valueDescriptor.currencyField,
    currencyLabel,
  },
  value: row.values.value,
});
assert.equal(presentation.kind, 'money');
assert.match(presentation.text, /0\.00/);
console.log(
  `P0_A_REAL_ORM_MONEY_CHAIN=PASS value=${String(row.values.value)} `
  + `currency=${currencyLabel} text=${presentation.text}`,
);
