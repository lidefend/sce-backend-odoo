import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { evaluateNativeModifierValue } from '../src/app/modifierEngine';
import { bindNativeContext, bindNativeFieldTypes } from '../src/app/nativeModifierContext';
import { isContractGapError } from '../src/app/contract/contractGap';

const cases = JSON.parse(execFileSync('python3', ['addons/smart_core/tests/test_native_modifier.py', '--emit-differential'], { encoding: 'utf8', maxBuffer: 8 * 1024 * 1024 }));
for (const row of cases) {
  if (row.contract) assert.deepEqual(bindNativeFieldTypes(bindNativeContext(row.contract.dataContract.mainData,
    row.contract.dataContract.dataMeta.sourceContext), row.contract.dataContract.dataMeta.nativeModifierFieldTypes), row.record);
  const evaluate = () => evaluateNativeModifierValue(row.node, (name) => row.record[name]);
  if (row.expected === null) assert.throws(evaluate, isContractGapError);
  else assert.equal(evaluate(), row.expected, JSON.stringify(row));
}
for (const node of ['context.get("x")', { kind: 'not' }, { kind: 'any', exprs: [] },
  { kind: 'field_compare', field: 'state', operator: 'bad', value: 1 }]) {
  assert.throws(() => evaluateNativeModifierValue(node, () => 'draft'), isContractGapError);
}
assert.equal(evaluateNativeModifierValue(undefined, () => undefined), false);
console.log(`[native_modifier] PASS ${cases.length + 5} cases; Python native truth / backend / frontend differential`);
