import assert from 'node:assert/strict';
import type { FieldDescriptor } from '@sc/schema';
import {
  isMissingRequiredValue,
  isRequiredFieldEmptyByType,
  normalizeContractFieldValue,
} from '../src/pages/contractForm/valueUtils';
import { collectRequiredFieldValidation, shouldWriteFieldValue } from '../src/pages/contractForm/saveRecordHelpers';
import { buildLegacyLayoutNodes } from '../src/pages/contractForm/nativeLayoutUtils';
import type { LayoutNode } from '../src/pages/contractForm/types';

const descriptor = (input: Record<string, unknown>) => input as unknown as FieldDescriptor;
const monetary = descriptor({ type: 'monetary', digits: [16, 2], string: '金额', required: true });
const integerField = descriptor({ type: 'integer', string: '数量' });

let cases = 0;
const check = (actual: unknown, expected: unknown, label: string) => {
  assert.equal(actual, expected, label);
  cases += 1;
};

// --- A. one shared required semantics for both validation paths -------------
// `fieldType` is optional because the scene precheck has no type available.
const requiredCases: Array<[unknown, string | undefined, boolean]> = [
  [0, undefined, false],
  [0, 'monetary', false],
  [0, 'float', false],
  [0, 'integer', false],
  [0.0, 'float', false],
  ['0', 'monetary', false],
  [false, 'boolean', false],
  [true, 'boolean', false],
  [null, 'boolean', true],
  [undefined, 'boolean', true],
  [null, undefined, true],
  [undefined, 'monetary', true],
  ['', 'monetary', true],
  ['', undefined, true],
  ['   ', 'char', true],
  [false, 'monetary', true],
  [false, 'many2one', true],
  [0, 'many2one', true],
  [12, 'many2one', false],
  [[], 'many2many', true],
  [[2], 'many2many', false],
  [[], undefined, true],
  ['A', undefined, false],
  [NaN, 'float', true],
];
requiredCases.forEach(([value, type, expected]) => {
  check(isMissingRequiredValue(value, type), expected, `isMissingRequiredValue(${String(value)}, ${String(type)})`);
  // Both paths must answer identically for the same value: no drift.
  check(isRequiredFieldEmptyByType(value, type || ''), expected, `typed alias agrees for ${String(value)}/${String(type)}`);
});
check(isMissingRequiredValue(0), isMissingRequiredValue(0, undefined), 'zero is not missing without type information');

// --- B. empty numeric serialization: untouched / cleared / real 0 -----------
const normalize = (value: unknown, desc: FieldDescriptor = monetary) => normalizeContractFieldValue({
  name: 'amount', value, descriptor: desc, originalValue: undefined, buildOne2manyValue: () => [],
});
check(normalize(undefined), null, 'untouched monetary is null, never false');
check(normalize(null), null, 'absent monetary is null, never false');
check(normalize(''), false, 'explicitly cleared monetary keeps the Odoo empty sentinel');
check(normalize('   '), false, 'blank monetary is an explicit clear');
check(normalize(0), 0, 'numeric zero stays zero');
check(normalize('0'), 0, 'textual zero stays zero');
check(normalize('12.345'), 12.35, 'monetary digits still round');
check(normalizeContractFieldValue({
  name: 'qty', value: undefined, descriptor: integerField, originalValue: undefined, buildOne2manyValue: () => [],
}), null, 'untouched integer is null');
check(normalizeContractFieldValue({
  name: 'qty', value: '', descriptor: integerField, originalValue: undefined, buildOne2manyValue: () => [],
}), false, 'cleared integer keeps the Odoo empty sentinel');
check(normalizeContractFieldValue({
  name: 'qty', value: '0', descriptor: integerField, originalValue: undefined, buildOne2manyValue: () => [],
}), 0, 'integer zero stays zero');

// --- C. payload inclusion: untouched empty never overrides a default --------
check(shouldWriteFieldValue({ recordId: null, dirty: false, value: null, descriptor: monetary }), false, 'untouched null numeric is not written');
check(shouldWriteFieldValue({ recordId: null, dirty: false, value: '', descriptor: descriptor({ type: 'char' }) }), false, 'untouched empty char does not override a model default');
check(shouldWriteFieldValue({ recordId: null, dirty: false, value: false, descriptor: descriptor({ type: 'date' }) }), false, 'untouched empty date does not override a model default');
check(shouldWriteFieldValue({ recordId: null, dirty: false, value: false, descriptor: descriptor({ type: 'many2one' }) }), false, 'untouched empty relation does not override a model default');
check(shouldWriteFieldValue({ recordId: null, dirty: false, value: 0, descriptor: monetary }), true, 'hydrated zero is a real value and is written');
check(shouldWriteFieldValue({ recordId: null, dirty: false, value: 'A', descriptor: descriptor({ type: 'char' }) }), true, 'hydrated non-empty value is written');
check(shouldWriteFieldValue({ recordId: null, dirty: false, value: false, descriptor: descriptor({ type: 'boolean' }) }), true, 'unchecked boolean is a real value and is written');
check(shouldWriteFieldValue({ recordId: null, dirty: true, value: false, descriptor: monetary }), true, 'explicit clear is written');
check(shouldWriteFieldValue({ recordId: null, dirty: true, value: 0, descriptor: monetary }), true, 'explicit zero is written');
check(shouldWriteFieldValue({ recordId: 7, dirty: false, value: 'A', descriptor: descriptor({ type: 'char' }) }), false, 'edit mode keeps untouched values');
check(shouldWriteFieldValue({ recordId: 7, dirty: true, value: '', descriptor: descriptor({ type: 'char' }) }), true, 'edit mode writes an explicit clear');
check(shouldWriteFieldValue({ recordId: 7, dirty: true, value: 0, descriptor: monetary }), true, 'edit mode writes an explicit zero');

// --- D. the validation field table is never silently truncated --------------
const fieldNames = Array.from({ length: 40 }, (_, index) => `f${String(index + 1).padStart(2, '0')}`);
fieldNames[34] = 'amount';
const fields: Record<string, FieldDescriptor> = {};
fieldNames.forEach((name) => {
  fields[name] = name === 'amount'
    ? monetary
    : descriptor({ type: 'char', string: `字段${name}`, required: name === 'f39' });
});
const layoutInput = {
  fields,
  order: [],
  containerStatus: {},
  visibleFields: [],
  fallbackFieldNames: [],
  isCreate: true,
  readonly: false,
  resolveFieldLabel: (name: string) => name,
  evaluatePolicy: (_name: string, row: FieldDescriptor) => ({ visible: true, required: Boolean(row.required), readonly: Boolean(row.readonly) }),
  runtimeState: () => ({ invisible: false, readonly: false, required: false }),
};
const layoutNodes = buildLegacyLayoutNodes(layoutInput) as LayoutNode[];
check(layoutNodes.length, 40, 'no fallback field is dropped from the table');
check(layoutNodes.some((node) => node.name === 'amount'), true, 'a field past the old 16-field cut survives');
check(layoutNodes.some((node) => node.name === 'f39'), true, 'the last field survives');

const normalizeFieldValue = (name: string, value: unknown) => normalizeContractFieldValue({
  name, value, descriptor: fields[name], originalValue: undefined, buildOne2manyValue: () => [],
});
const validate = (formData: Record<string, unknown>, values: Record<string, unknown>) => collectRequiredFieldValidation({
  formData,
  isWritableFieldVisible: () => true,
  layoutNodes,
  normalizeFieldValue,
  values,
});
// Nothing is dirty and no value was hydrated: the create payload must stay
// empty so every model default remains owned by the ORM.
const untouchedPayload: Record<string, unknown> = {};
layoutNodes.forEach((node) => {
  const value = normalizeFieldValue(node.name, undefined);
  if (shouldWriteFieldValue({ recordId: null, dirty: false, value, descriptor: fields[node.name] })) {
    untouchedPayload[node.name] = value;
  }
});
check(Object.keys(untouchedPayload).length, 0, 'an untouched create payload stays empty');

// Required fields after the old cut are still validated.
const untouchedValidation = validate({}, untouchedPayload);
check(untouchedValidation.messages.length, 1, 'untouched required fields past the cut are reported');
check(Boolean(untouchedValidation.fieldErrors.amount), true, 'field-level error covers the monetary after the cut');
check(Boolean(untouchedValidation.fieldErrors.f39), true, 'field-level error covers the last required field');

// Numeric zero satisfies the required check; an explicit clear does not.
const filledLate = { amount: 0, f39: '已填' };
check(validate(filledLate, filledLate).messages.length, 0, 'explicit zero passes the required check');
const clearedValidation = validate({ amount: '', f39: '已填' }, { amount: false, f39: '已填' });
check(clearedValidation.messages.length, 1, 'explicit clear fails the required check');
check(Boolean(clearedValidation.fieldErrors.amount), true, 'the cleared required field is located');
check(Boolean(clearedValidation.fieldErrors.f39), false, 'a filled required field is not reported');
// A required boolean is fulfilled by `false`, not treated as unfilled.
const booleanNodes: LayoutNode[] = [{ key: 'field_flag', kind: 'field', name: 'flag', label: '标志', readonly: false, required: true, descriptor: descriptor({ type: 'boolean', required: true }) }];
const booleanValidation = collectRequiredFieldValidation({
  formData: { flag: false }, isWritableFieldVisible: () => true, layoutNodes: booleanNodes,
  normalizeFieldValue: (name, value) => normalizeContractFieldValue({ name, value, descriptor: descriptor({ type: 'boolean' }), originalValue: undefined, buildOne2manyValue: () => [] }),
  values: { flag: false },
});
check(booleanValidation.messages.length, 0, 'unchecked boolean is not reported as missing');

console.log(`[j13_required_value_semantics] shared required semantics, three-state numeric serialization, payload ownership and field-table completeness: ${cases} cases passed`);
