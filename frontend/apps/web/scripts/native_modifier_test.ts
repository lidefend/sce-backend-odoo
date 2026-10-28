import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { evaluateNativeModifierValue } from '../src/app/modifierEngine';
import { bindNativeContext, bindNativeFieldTypes } from '../src/app/nativeModifierContext';
import { resolveNativeOperand } from '../src/app/nativeModifierContext';
import { nativeModifierRelationValue } from '../src/app/nativeModifierRelationValue';
import { isContractGapError } from '../src/app/contract/contractGap';

const cases = JSON.parse(execFileSync('python3', ['addons/smart_core/tests/test_native_modifier.py', '--emit-differential'], { encoding: 'utf8', maxBuffer: 8 * 1024 * 1024 }));
for (const row of cases) {
  if (row.contract) assert.deepEqual(bindNativeFieldTypes(bindNativeContext(row.contract.dataContract.mainData,
    row.contract.dataContract.dataMeta.sourceContext), row.contract.dataContract.dataMeta.nativeModifierFieldTypes, row.contract.dataContract.dataMeta.nativeModifierRelationSnapshots), row.record);
  const evaluate = () => evaluateNativeModifierValue(row.node, (name) => row.record[name]);
  if (row.expected === null) assert.throws(evaluate, isContractGapError);
  else assert.equal(evaluate(), row.expected, JSON.stringify(row));
}
for (const node of ['context.get("x")', { kind: 'not' }, { kind: 'any', exprs: [] },
  { kind: 'field_compare', field: 'state', operator: 'bad', value: 1 }]) {
  assert.throws(() => evaluateNativeModifierValue(node, () => 'draft'), isContractGapError);
}
assert.equal(evaluateNativeModifierValue(undefined, () => undefined), false);
// Explicit empty relation values are valid; missing dependencies must fail closed.
for (const empty of [false, '']) {
  assert.equal(nativeModifierRelationValue(empty, 'many2one'), false, `many2one empty ${String(empty)}`);
}
assert.equal(nativeModifierRelationValue(7, 'many2one'), 7);
assert.equal(nativeModifierRelationValue([7, 'Display'], 'many2one'), 7);
for (const empty of ['']) {
  assert.deepEqual(nativeModifierRelationValue(empty, 'one2many'), []);
}
assert.deepEqual(nativeModifierRelationValue([1, 2, 3], 'many2many'), [1, 2, 3]);
assert.throws(() => nativeModifierRelationValue('Journal', 'many2one'), isContractGapError);
assert.throws(() => nativeModifierRelationValue(null, 'many2one'), isContractGapError);
assert.throws(() => nativeModifierRelationValue([0, 0, { name: 'x' }], 'one2many'), isContractGapError);
// context.get(key) without a default resolves to falsy when the key is absent,
// matching Python None truthiness; a missing default key must not fail the form.
assert.equal(
  resolveNativeOperand({ kind: 'context_get', key: 'default_journal_id' }, (name) => (name === '$native.context' ? {} : undefined)),
  false,
);
assert.equal(
  resolveNativeOperand({ kind: 'context_get', key: 'move_type', default: 'entry' }, (name) => (name === '$native.context' ? {} : undefined)),
  'entry',
);
console.log(`[native_modifier] PASS ${cases.length + 5} cases; Python native truth / backend / frontend differential`);

for (const type of ['many2one','one2many','many2many']) {
  assert.throws(() => nativeModifierRelationValue(undefined, type), isContractGapError);
}

// Identity predicate remains strict after moving it to a declaration-only module shape.
for (const invalid of [0, -1, 1.5, Number.NaN, Number.POSITIVE_INFINITY, Number.MAX_SAFE_INTEGER + 1, true, '7']) {
  assert.throws(() => nativeModifierRelationValue(invalid, 'many2one'), isContractGapError);
  assert.throws(() => nativeModifierRelationValue([invalid], 'many2many'), isContractGapError);
}
assert.equal(nativeModifierRelationValue(Number.MAX_SAFE_INTEGER, 'many2one'), Number.MAX_SAFE_INTEGER);
console.log('[native_modifier] identity declaration regression PASS assertions=17');
