import assert from 'node:assert/strict';
import test from 'node:test';

import {
  formatMonetaryDisplayValue,
  formatMonetaryInputValue,
  monetaryInputStep,
  resolveMonetaryScale,
} from './money.ts';

test('monetary display keeps two decimal places for CNY', () => {
  assert.match(formatMonetaryDisplayValue(1234.5, [20, 2], 'CNY'), /1,234\.50/);
});

test('zero monetary value is displayed with scale, not as empty', () => {
  assert.match(formatMonetaryDisplayValue(0, [20, 2], 'CNY'), /0\.00/);
});

test('negative monetary value keeps the sign and separators', () => {
  const text = formatMonetaryDisplayValue(-1234.5, [20, 2], 'CNY');
  assert.ok(text.startsWith('-'));
  assert.match(text, /1,234\.50/);
});

test('decimal precision follows the declared scale', () => {
  assert.match(formatMonetaryDisplayValue(1, [20, 3], 'CNY'), /1\.000/);
});

test('thousands separator and large amounts are stable', () => {
  assert.match(formatMonetaryDisplayValue(1234567.89, [20, 2], 'CNY'), /1,234,567\.89/);
});

test('empty and non-finite values use the declared empty text', () => {
  assert.equal(formatMonetaryDisplayValue(null, [20, 2], 'CNY'), '-');
  assert.equal(formatMonetaryDisplayValue('', [20, 2], 'CNY'), '-');
  assert.equal(formatMonetaryDisplayValue(Number.NaN, [20, 2], 'CNY'), '-');
});

test('missing currency code renders a plain localized number', () => {
  assert.equal(formatMonetaryDisplayValue(1234.5, [20, 2], ''), '1,234.50');
});

test('currency code changes the display from the plain number', () => {
  const plain = formatMonetaryDisplayValue(1234.5, [20, 2], '');
  const withCurrency = formatMonetaryDisplayValue(1234.5, [20, 2], 'CNY');
  assert.notEqual(withCurrency, plain);
});

test('input formatting rounds to the declared scale without changing the number semantics', () => {
  assert.equal(formatMonetaryInputValue(1234.567, [20, 2]), '1234.57');
  assert.equal(formatMonetaryInputValue('', [20, 2]), '');
});

test('monetary scale resolution covers explicit digits, currency and fallback', () => {
  assert.equal(resolveMonetaryScale([20, 2]), 2);
  assert.equal(resolveMonetaryScale(undefined, 'CNY'), 2);
  assert.equal(resolveMonetaryScale(undefined, ''), undefined);
});

test('monetary input step is scale-derived', () => {
  assert.equal(monetaryInputStep([20, 0]), '1');
  assert.equal(monetaryInputStep([20, 2]), '0.01');
  assert.equal(monetaryInputStep(undefined, ''), 'any');
});
