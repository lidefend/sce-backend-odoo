/**
 * Behavioural lock for the single frontend contract-stop primitive.
 *
 * The primitive's job is to make a missing or invalid declaration stop the surface
 * instead of letting the frontend repair it. These cases drive the production
 * helpers, so a regression that re-introduces coercion cannot pass by matching a
 * declaration string: `true` must not become `1`, `'20'` must not become `20`,
 * `1.9` must not be truncated to `1`, and a legal declaration must be returned
 * unchanged.
 */
import assert from 'node:assert/strict';

import {
  isContractGapError,
  optionalDeclaredNumber,
  requireDeclaredNumber,
  requireDeclaredNumberList,
} from '../src/app/contract/contractGap';
import type { ContractGapError } from '../src/app/contract/contractGap';

let cases = 0;

const spec = {
  missing: 'config.list.page_size',
  requiredDeclarationLayer: 'P0:smart_core:test',
};

function rejected(value: unknown, run: () => unknown, label: string): void {
  try {
    run();
  } catch (error) {
    assert.ok(isContractGapError(error), `${label}: expected ContractGapError, got ${String(error)}`);
    assert.equal((error as ContractGapError).defect.missing, spec.missing, `${label}: defect path`);
    assert.equal((error as ContractGapError).defect.requiredDeclarationLayer, spec.requiredDeclarationLayer, `${label}: owner layer`);
    cases += 1;
    return;
  }
  assert.fail(`${label}: expected the surface to stop, but the primitive returned a value`);
}

function accepted(value: unknown, expected: unknown, label: string): void {
  assert.deepEqual(value, expected, label);
  cases += 1;
}

// --- requireDeclaredNumber: a legal declaration is returned unchanged --------
accepted(requireDeclaredNumber(20, spec), 20, 'declared 20 is returned unchanged');
accepted(requireDeclaredNumber(1, spec), 1, 'the inclusive lower bound 1 is legal');
accepted(requireDeclaredNumber(200, { ...spec, max: 200 }), 200, 'the inclusive upper bound is legal');
accepted(requireDeclaredNumber(0, { ...spec, min: 0, integer: false }), 0, 'a non-integer declaration accepts 0 when min is 0');
accepted(requireDeclaredNumber(0.5, { ...spec, min: 0, integer: false }), 0.5, 'a fractional declaration survives as declared');

// --- requireDeclaredNumber: every illegal declaration stops ------------------
rejected(undefined, () => requireDeclaredNumber(undefined, spec), 'undefined');
rejected(null, () => requireDeclaredNumber(null, spec), 'null');
rejected(true, () => requireDeclaredNumber(true, spec), 'a boolean true must not become 1');
rejected(false, () => requireDeclaredNumber(false, spec), 'a boolean false must not become 0');
rejected('20', () => requireDeclaredNumber('20', spec), 'a numeric string must not be parsed');
rejected('', () => requireDeclaredNumber('', spec), 'an empty string must not become 0');
rejected([], () => requireDeclaredNumber([], spec), 'an array must not be coerced');
rejected([20], () => requireDeclaredNumber([20], spec), 'a single-element array must not be coerced');
rejected({}, () => requireDeclaredNumber({}, spec), 'an object must not be coerced');
rejected(NaN, () => requireDeclaredNumber(NaN, spec), 'NaN');
rejected(Infinity, () => requireDeclaredNumber(Infinity, spec), 'Infinity');
rejected(1.9, () => requireDeclaredNumber(1.9, spec), 'a fractional integer declaration must not be truncated');
rejected(0, () => requireDeclaredNumber(0, spec), 'below the default lower bound');
rejected(-1, () => requireDeclaredNumber(-1, spec), 'a negative declaration');
rejected(201, () => requireDeclaredNumber(201, { ...spec, max: 200 }), 'above the declared upper bound');
rejected(1.5, () => requireDeclaredNumber(1.5, { ...spec, min: 0, integer: false, max: 1 }), 'a fractional value above an integer upper bound');

// --- requireDeclaredNumberList: legal lists pass through unmodified ----------
accepted(requireDeclaredNumberList([10, 20, 50], spec), [10, 20, 50], 'a declared option list is returned unchanged');
accepted(requireDeclaredNumberList([5], { ...spec, min: 5 }), [5], 'a list item at the declared lower bound is legal');

// --- requireDeclaredNumberList: illegal lists stop ---------------------------
rejected(undefined, () => requireDeclaredNumberList(undefined, spec), 'a missing list');
rejected(null, () => requireDeclaredNumberList(null, spec), 'a null list');
rejected([], () => requireDeclaredNumberList([], spec), 'an empty list declares nothing');
rejected('10,20', () => requireDeclaredNumberList('10,20', spec), 'a string list must not be split');
rejected([10, '20'], () => requireDeclaredNumberList([10, '20'], spec), 'a numeric string item must not be parsed');
rejected([10, 1.5], () => requireDeclaredNumberList([10, 1.5], spec), 'a fractional item must not be truncated');
rejected([10, 0], () => requireDeclaredNumberList([10, 0], spec), 'an item below the lower bound must not be dropped');
rejected([true], () => requireDeclaredNumberList([true], spec), 'a boolean item must not become 1');
rejected([10, 20], () => requireDeclaredNumberList([10, 20], { ...spec, min: 15 }), 'an item below a declared item bound');
rejected([10, 500], () => requireDeclaredNumberList([10, 500], { ...spec, max: 200 }), 'an item above the declared item bound');

// --- optionalDeclaredNumber: absence is allowed, an illegal presence is not --
accepted(optionalDeclaredNumber(undefined, spec), undefined, 'an absent optional declaration resolves to undefined');
accepted(optionalDeclaredNumber(null, spec), undefined, 'a null optional declaration resolves to undefined');
accepted(optionalDeclaredNumber('', spec), undefined, 'an empty optional declaration resolves to undefined');
accepted(optionalDeclaredNumber(30, spec), 30, 'a present optional declaration is returned unchanged');
rejected(0, () => optionalDeclaredNumber(0, spec), 'a present-but-illegal optional declaration still stops');
rejected('30', () => optionalDeclaredNumber('30', spec), 'a present optional numeric string must not be parsed');
rejected(true, () => optionalDeclaredNumber(true, spec), 'a present optional boolean must not become 1');

console.log(`[contract_gap_primitive_test] PASS cases=${cases}`);
