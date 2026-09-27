import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import type { FieldDescriptor } from '@sc/schema';
import {
  isMissingRequiredValue,
  isRequiredFieldEmptyByType,
  normalizeContractFieldValue,
} from '../src/pages/contractForm/valueUtils';
import { fieldType } from '../src/pages/contractForm/fieldUtils';
import { collectRequiredFieldValidation, shouldWriteFieldValue } from '../src/pages/contractForm/saveRecordHelpers';
import { collectSceneValidationPrecheckErrors, type SceneValidationPrecheckInput } from '../src/pages/contractForm/sceneValidation';
import { dispatchTemplateFieldChange } from '../src/components/template/fieldChange.dispatcher';
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
// A non-required numeric follows the same three states: untouched is skipped,
// an explicit clear reaches the payload as the Odoo empty sentinel, and a real
// zero stays a real zero.
check(shouldWriteFieldValue({ recordId: 7, dirty: false, value: null, descriptor: monetary }), false, 'edit mode never writes an untouched non-required numeric');
check(shouldWriteFieldValue({ recordId: 7, dirty: false, value: 0, descriptor: monetary }), false, 'edit mode still skips an untouched stored numeric');
check(shouldWriteFieldValue({ recordId: 7, dirty: true, value: false, descriptor: monetary }), true, 'edit mode writes an explicit clear of a non-required numeric');
check(shouldWriteFieldValue({ recordId: null, dirty: true, value: false, descriptor: monetary }), true, 'create mode writes an explicit clear of a non-required numeric');

// --- C2. what a cleared numeric control actually hands the draft ------------
// The official numeric control is a text input (`type="number"`); clearing it
// emits an empty string. The dispatcher must never turn that into the `null`
// that `shouldWriteFieldValue` skips, otherwise the clear intent is lost.
const draftFromControl = (type: string, value: string | number | boolean | null) => {
  let observed: string | undefined;
  dispatchTemplateFieldChange(
    { name: 'field', type, value },
    { onBoolean: () => {}, onSelection: () => {}, onMany2one: () => {}, onText: (_name, text) => { observed = text; } },
  );
  return observed;
};
check(draftFromControl('monetary', ''), '', 'a cleared monetary control hands the draft an empty string');
check(draftFromControl('float', ''), '', 'a cleared float control hands the draft an empty string');
check(draftFromControl('integer', ''), '', 'a cleared integer control hands the draft an empty string');
check(draftFromControl('monetary', null), '', 'a null-emitting control is normalized to an empty string, never treated as untouched');
check(draftFromControl('monetary', '0'), '0', 'a typed zero reaches the draft as the string it was typed');
check(normalizeContractFieldValue({ name: 'x', value: draftFromControl('monetary', ''), descriptor: descriptor({ type: 'monetary' }), originalValue: 7.5, buildOne2manyValue: () => [] }), false, 'the cleared draft serializes to the Odoo empty sentinel');

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

// --- E. the scene precheck judges with the contract field type --------------
// The scene precheck is a second save-time gate. It used to call the shared
// judgement without a type, so a required boolean answered `false` was blocked
// while an empty relation slipped through. It now resolves the type from the
// contract descriptor before judging — same wiring as production.
const sceneDescriptors: Record<string, FieldDescriptor> = {
  flag: descriptor({ type: 'boolean', string: '标志' }),
  qty: descriptor({ type: 'integer', string: '数量' }),
  amount: descriptor({ type: 'monetary', digits: [16, 2], string: '金额' }),
  relation: descriptor({ type: 'many2one', relation: 'res.partner', string: '往来单位' }),
  note: descriptor({ type: 'char', string: '备注' }),
};
const sceneLabels: Record<string, string> = { flag: '标志', qty: '数量', amount: '金额', relation: '往来单位', note: '备注' };
const scenePrecheck = (
  requiredFields: string[],
  formData: Record<string, unknown>,
  overrides: Partial<SceneValidationPrecheckInput> = {},
) => collectSceneValidationPrecheckErrors({
  requiredFields,
  fieldLabels: sceneLabels,
  isFieldVisible: () => true,
  fieldValue: (field) => formData[field],
  isMissingValue: isMissingRequiredValue,
  fieldType: (field) => fieldType(sceneDescriptors[field]),
  errorCode: 'SCENE_VALIDATION_REQUIRED',
  ...overrides,
});

check(scenePrecheck(['flag'], { flag: false }).length, 0, 'an unchecked required boolean passes the scene precheck');
check(scenePrecheck(['flag'], { flag: true }).length, 0, 'a checked required boolean passes the scene precheck');
check(scenePrecheck(['flag'], { flag: null }).length, 1, 'an unanswered required boolean is still reported by the scene precheck');
check(scenePrecheck(['qty'], { qty: 0 }).length, 0, 'numeric zero passes the scene precheck');
check(scenePrecheck(['amount'], { amount: 0 }).length, 0, 'monetary zero passes the scene precheck');
check(scenePrecheck(['amount'], { amount: '' }).length, 1, 'a cleared required monetary is still reported by the scene precheck');
check(scenePrecheck(['relation'], { relation: 12 }).length, 0, 'a chosen relation passes the scene precheck');
check(scenePrecheck(['relation'], { relation: false }).length, 1, 'an empty relation (`false`) is still reported by the scene precheck');
check(scenePrecheck(['note'], { note: '   ' }).length, 1, 'blank text is still reported by the scene precheck');
check(scenePrecheck(['relation', 'flag'], { relation: false, flag: false }).length, 1, 'the scene precheck tells a real boolean false apart from an empty relation');

// The type must actually be forwarded: an "accept every false" shortcut would
// hide the empty relation above.
const forwarded: Array<[unknown, unknown]> = [];
scenePrecheck(['flag', 'relation'], { flag: false, relation: false }, {
  isMissingValue: (value, type) => { forwarded.push([value, type]); return isMissingRequiredValue(value, type); },
});
check(JSON.stringify(forwarded), JSON.stringify([[false, 'boolean'], [false, 'many2one']]), 'the scene precheck forwards each contract field type');
// No descriptor means no invented type: the legacy type-blind answer stays.
check(scenePrecheck(['ghost'], { ghost: false }).length, 1, 'an unknown scene field keeps the type-blind answer');

// --- F. call-site wiring guard ---------------------------------------------
// A behavioural test cannot catch the production call site drifting back to an
// untyped judgement, which is exactly how the two paths diverged before.
const locateSource = (relative: string) => {
  let dir = process.cwd();
  for (let depth = 0; depth < 4; depth += 1) {
    const candidate = path.join(dir, relative);
    if (fs.existsSync(candidate)) return candidate;
    dir = path.dirname(dir);
  }
  return '';
};
const presentationPath = locateSource('frontend/apps/web/src/pages/contractForm/useRecordActionPresentation.ts');
check(presentationPath !== '', true, 'the record action presentation source is locatable for the wiring guard');
const presentationSource = fs.readFileSync(presentationPath, 'utf8');
const precheckStart = presentationSource.indexOf('collectSceneValidationPrecheckErrorsFromRules({');
const precheckCall = precheckStart >= 0 ? presentationSource.slice(precheckStart, precheckStart + 900) : '';
check(precheckStart >= 0, true, 'the wiring guard finds the scene precheck call');
check(precheckCall.includes('isMissingValue: isMissingRequiredValue'), true, 'the scene precheck still uses the shared judgement');
check(precheckCall.includes('fieldType:'), true, 'the scene precheck call supplies a field type resolver');
check(precheckCall.includes('formFields.value['), true, 'the field type resolver reads the contract form fields');

console.log(`[j13_required_value_semantics] shared required semantics, scene-precheck type wiring, three-state numeric serialization incl. non-required clear, payload ownership and field-table completeness: ${cases} cases passed`);
