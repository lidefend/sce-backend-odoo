/**
 * Executable proof for FE-TPL-01: the official form composition is adopted for
 * the verified surface, its generic validation really gates a save, and every
 * protection the merged fixes established is still the one in the chain.
 *
 * The chain under test is the shipped one:
 *
 *   adoption policy -> ScForm/ScFormItem adapter -> buildContractFormRules
 *                   -> engine result -> failedAdoptedFieldNames
 *                   -> buildRequiredFieldErrorPayload (one error store)
 *                   -> the existing focus entry
 *
 * The counter-examples fail on a composition that claims adoption while
 * validating a second copy of the draft, on a rule that disagrees with the
 * pre-existing emptiness authority, on an error that produces a second message
 * or store key for the same field, and on a section that silently lets a save
 * through when it cannot answer.
 */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { ref } from 'vue';

import {
  STANDARD_FORM_COMPOSITION_PILOT_MODELS,
  resolveStandardFormComposition,
} from '../src/app/presentation/standardFormComposition';
import {
  adoptedValidationValue,
  buildContractFormRules,
  contractFormFieldRules,
  failedAdoptedFieldNames,
  requiredFieldMessage,
} from '../src/components/template/contractFormValidationRules';
import { createStandardFormValidationRegistry } from '../src/pages/contractForm/standardFormCompositionRuntime';
import {
  buildRequiredFieldErrorPayload,
  collectRequiredFieldValidation,
} from '../src/pages/contractForm/saveRecordHelpers';
import { businessErrorKey, errorOwnsRecordScope } from '../src/app/businessValidationError';
import type { FormSectionFieldSchema } from '../src/components/template/formSection.types';
import type { LayoutNode } from '../src/pages/contractForm/types';

let cases = 0;
const check = (actual: unknown, expected: unknown, label: string) => {
  assert.equal(actual, expected, label);
  cases += 1;
};
const checkDeep = (actual: unknown, expected: unknown, label: string) => {
  assert.deepEqual(actual, expected, label);
  cases += 1;
};

const locateSource = (relative: string) => {
  let dir = process.cwd();
  for (let depth = 0; depth < 4; depth += 1) {
    const candidate = path.join(dir, relative);
    if (fs.existsSync(candidate)) return candidate;
    dir = path.dirname(dir);
  }
  return '';
};
const readSource = (relative: string) => fs.readFileSync(locateSource(relative), 'utf8');

const field = (overrides: Partial<FormSectionFieldSchema>): FormSectionFieldSchema => ({
  key: String(overrides.name || 'field'),
  name: String(overrides.name || 'field'),
  label: String(overrides.label || '项目名称'),
  type: String(overrides.type || 'char'),
  required: false,
  readonly: false,
  ...overrides,
});

// ---------------------------------------------------------------------------
// Part 1 — adoption is an explicit scope, never an inference
// ---------------------------------------------------------------------------
check(resolveStandardFormComposition({ model: 'project.project' }).adopted, true, 'the verified surface is adopted');
check(
  resolveStandardFormComposition({ model: 'project.project' }).composition,
  'official-standard-form',
  'the adopted surface reports the official composition',
);
check(
  resolveStandardFormComposition({ model: 'project.project' }).reason,
  'pilot-model-adopted',
  'adoption reports the scope it came from',
);
for (const other of ['payment.request', 'res.partner', 'project.task', 'sc.general.contract.line', '']) {
  check(resolveStandardFormComposition({ model: other }).adopted, false, `adoption does not leak to ${other || 'an empty model'}`);
  check(
    resolveStandardFormComposition({ model: other }).reason,
    'outside-pilot-scope',
    'a surface outside the verified scope keeps the composition it had',
  );
}
check(
  resolveStandardFormComposition({ model: undefined }).adopted,
  false,
  'a page without a declared model is never adopted by default',
);
checkDeep(
  [...STANDARD_FORM_COMPOSITION_PILOT_MODELS],
  ['project.project', 'sc.general.contract'],
  'the adopted scope is exactly the verified surfaces',
);

// ---------------------------------------------------------------------------
// Part 1b — the second model is a reuse, not a second implementation
//
// TPL-02: a different business model joins the same composition. The proof is
// structural. The surfaces that actually render the form never learn the model
// name, so nothing about the second model can be satisfied by a copy of the
// first one's orchestration; the only thing that changes is the scope list.
// ---------------------------------------------------------------------------
check(
  resolveStandardFormComposition({ model: 'sc.general.contract' }).adopted,
  true,
  'the second verified surface is adopted by the same policy',
);
check(
  resolveStandardFormComposition({ model: 'sc.general.contract' }).composition,
  'official-standard-form',
  'the second surface reports the same official composition',
);
check(
  resolveStandardFormComposition({ model: 'sc.general.contract' }).reason,
  'pilot-model-adopted',
  'the second surface reports the same scope reason as the first',
);

const compositionCallSites = [
  'frontend/apps/web/src/components/template/FormSection.vue',
  'frontend/apps/web/src/pages/ContractFormPage.vue',
];
for (const callSite of compositionCallSites) {
  const source = readSource(callSite);
  for (const adoptedModel of STANDARD_FORM_COMPOSITION_PILOT_MODELS) {
    check(
      source.includes(adoptedModel),
      false,
      `${callSite} does not name ${adoptedModel}; the surface reads the scope, it does not carry it`,
    );
  }
  check(
    /resolveStandardFormComposition/.test(source),
    false,
    `${callSite} does not re-decide adoption; it consumes the page runtime`,
  );
}
check(
  /standardFormComposition/.test(readSource('frontend/apps/web/src/components/template/FormSection.vue')),
  true,
  'the section still reads the adopted composition from the page runtime',
);
// The scope lives in exactly one place. A second declaration would let the two
// surfaces disagree about which models are adopted.
const pilotDeclarations = compositionCallSites
  .concat(['frontend/apps/web/src/app/presentation/standardFormComposition.ts'])
  .map((file) => [file, /STANDARD_FORM_COMPOSITION_PILOT_MODELS/.test(readSource(file))] as const)
  .filter(([, present]) => present)
  .map(([file]) => file);
checkDeep(
  pilotDeclarations,
  ['frontend/apps/web/src/app/presentation/standardFormComposition.ts'],
  'exactly one module declares the adopted scope',
);

const policySource = readSource('frontend/apps/web/src/app/presentation/standardFormComposition.ts');
check(/from ['"]vue['"]/.test(policySource), false, 'the adoption policy is independent of a rendering framework');
check(/\bdocument\./.test(policySource), false, 'the adoption policy does not read the DOM');
check(/tdesign/i.test(policySource), false, 'the adoption policy is independent of the component vendor');

// ---------------------------------------------------------------------------
// Part 2 — the rule engine and the pre-existing authority cannot disagree
// ---------------------------------------------------------------------------
const requiredName = field({ name: 'name', label: '项目名称', required: true });
checkDeep(
  contractFormFieldRules(requiredName).map((rule) => rule.message),
  [requiredFieldMessage('项目名称')],
  'a required field declares the engine message the form already shows',
);
check(contractFormFieldRules(field({ name: 'code', required: false })).length, 0, 'an optional field declares no rule');
check(
  contractFormFieldRules(field({ name: 'code', required: true, readonly: true })).length,
  0,
  'a read-only position never becomes a correction site',
);
check(contractFormFieldRules(field({ name: '  ', required: true })).length, 0, 'a nameless field declares no rule');

// The engine's answer and the save precheck's answer must be the same answer.
const emptinessProbes: { value: unknown; type: string; empty: boolean }[] = [
  { value: '', type: 'char', empty: true },
  { value: '   ', type: 'char', empty: true },
  { value: null, type: 'char', empty: true },
  { value: false, type: 'char', empty: true },
  { value: 'x', type: 'char', empty: false },
  { value: 0, type: 'integer', empty: false },
  { value: 0, type: 'many2one', empty: true },
  { value: 12, type: 'many2one', empty: false },
  { value: false, type: 'boolean', empty: false },
  { value: [], type: 'many2many', empty: true },
  { value: [1], type: 'many2many', empty: false },
];
for (const probe of emptinessProbes) {
  const probeField = field({ name: 'probe', required: true, type: probe.type, inputValue: probe.value as never });
  const rule = contractFormFieldRules(probeField)[0];
  check(
    rule.validator(),
    !probe.empty,
    `the engine accepts exactly what the precheck accepts for ${probe.type}=${JSON.stringify(probe.value)}`,
  );
}
check(
  adoptedValidationValue(field({ name: 'a', inputValue: 'draft', value: 'stored' })),
  'draft',
  'a rule reads the draft the page already holds',
);
check(
  adoptedValidationValue(field({ name: 'a', value: 'stored' })),
  'stored',
  'a rule falls back to the value when no input projection exists',
);

checkDeep(
  Object.keys(buildContractFormRules([
    field({ name: 'name', required: true }),
    field({ name: 'code', required: false }),
    field({ name: 'partner_id', required: true, type: 'many2one' }),
  ])),
  ['name', 'partner_id'],
  'the section only declares rules for the fields that take part',
);

// ---------------------------------------------------------------------------
// Part 3 — reading the engine result, including what it cannot tell us
// ---------------------------------------------------------------------------
checkDeep(failedAdoptedFieldNames(true), [], 'the engine reports a pass as true');
checkDeep(
  failedAdoptedFieldNames({ name: [{ result: false, message: '项目名称不能为空' }] }),
  ['name'],
  'the engine reports rejected field codes',
);
checkDeep(failedAdoptedFieldNames({}), [], 'an empty result object rejects nothing, so it is a real pass');
check(
  failedAdoptedFieldNames(undefined) === null,
  true,
  'a missing result cannot be read as a pass: the caller must fail closed',
);
check(
  failedAdoptedFieldNames(null) === null,
  true,
  'a null result cannot be read as a pass',
);
check(
  failedAdoptedFieldNames('unexpected') === null,
  true,
  'an unrecognised result is refused rather than guessed at',
);
check(
  failedAdoptedFieldNames(['name']) === null,
  true,
  'a list is not read as an error map, so it is refused rather than treated as a pass',
);

// ---------------------------------------------------------------------------
// Part 4 — one rejection produces one message, one key, one focus entry
// ---------------------------------------------------------------------------
const rejected = [{ name: 'name', label: '项目名称' }];
const scope = { model: 'project.project', recordId: 501 };
const adoptedPayload = buildRequiredFieldErrorPayload(rejected, scope);
const precheckLayout: LayoutNode[] = [{ kind: 'field', name: 'name', label: '项目名称', readonly: false, descriptor: { required: true, type: 'char' } } as unknown as LayoutNode];
const precheckPayload = collectRequiredFieldValidation({
  formData: { name: '' },
  isWritableFieldVisible: () => true,
  layoutNodes: precheckLayout,
  model: 'project.project',
  normalizeFieldValue: (_name, value) => value,
  recordId: 501,
  values: { name: '' },
});
checkDeep(adoptedPayload.messages, precheckPayload.messages, 'an adopted rejection speaks the same summary as the precheck');
checkDeep(Object.keys(adoptedPayload.fieldErrors), Object.keys(precheckPayload.fieldErrors), 'an adopted rejection keys the store the same way');
check(
  adoptedPayload.fieldErrors.name.message,
  precheckPayload.fieldErrors.name.message,
  'an adopted rejection shows the same field message as the precheck',
);
check(
  adoptedPayload.fieldErrors.name.target.model,
  'project.project',
  'an adopted rejection names the owning model',
);
check(adoptedPayload.fieldErrors.name.target.recordId, 501, 'an adopted rejection names the owning record');
check(adoptedPayload.fieldErrors.name.target.fieldCode, 'name', 'an adopted rejection names the business field');
check(businessErrorKey(adoptedPayload.fieldErrors.name.target), 'name', 'an adopted rejection uses the page display key');
checkDeep(buildRequiredFieldErrorPayload([], scope), { messages: [], fieldErrors: {} }, 'nothing rejected is nothing reported');

// ---------------------------------------------------------------------------
// Part 5 — the registry fails closed and never validates silently
// ---------------------------------------------------------------------------
const registry = createStandardFormValidationRegistry(() => 'project.project');
check(registry.adopted.value, true, 'the page runtime reports the adopted scope');
let validated = 0;
registry.register({ sectionId: 'a', ruleFieldNames: () => ['name'], validate: async () => { validated += 1; return ['name', 'name']; } });
registry.register({ sectionId: 'b', ruleFieldNames: () => ['partner_id'], validate: async () => { validated += 1; return ['partner_id']; } });
const collected = await registry.validateAdoptedFields();
check(collected.ok, true, 'a registry whose sections answered reports ok');
checkDeep(collected.fieldNames, ['name', 'partner_id'], 'rejected codes are collected once per field across sections');
checkDeep(collected.coveredFieldNames, ['name', 'partner_id'], 'the registry reports exactly the positions the official engine evaluated');
check(validated, 2, 'every registered section is asked');
registry.unregister('a');
const afterUnregister = await registry.validateAdoptedFields();
checkDeep(afterUnregister.fieldNames, ['partner_id'], 'an unregistered section stops contributing');
checkDeep(afterUnregister.coveredFieldNames, ['partner_id'], 'an unregistered section stops being covered as well, so its positions stay with the precheck');
registry.register({ sectionId: 'boom', ruleFieldNames: () => ['name'], validate: async () => { throw new Error('engine unavailable'); } });
const failed = await registry.validateAdoptedFields();
check(failed.ok, false, 'a section that cannot answer blocks the save instead of passing it');
checkDeep(failed.fieldNames, [], 'a failed validation reports no field it cannot name');
checkDeep(failed.coveredFieldNames, [], 'a failed run covers nothing, so nothing may be dropped from the precheck');

const unadopted = createStandardFormValidationRegistry(() => 'payment.request');
check(unadopted.adopted.value, false, 'an unverified surface is not adopted');
unadopted.register({ sectionId: 'x', ruleFieldNames: () => ['name'], validate: async () => ['name'] });
const unadoptedResult = await unadopted.validateAdoptedFields();
checkDeep(unadoptedResult, { ok: true, fieldNames: [], coveredFieldNames: [] }, 'an unadopted surface contributes nothing to the save gate');

// A model or record switch must not carry the previous surface with it: the
// page unmounts the old sections and mounts new ones, and the registry has to
// answer for the new surface only.
const liveModel = ref('project.project');
const switching = createStandardFormValidationRegistry(() => liveModel.value);
check(switching.adopted.value, true, 'the first model is inside the adopted scope');
switching.register({ sectionId: 'surface-a', ruleFieldNames: () => ['name'], validate: async () => ['name'] });
const beforeSwitch = await switching.validateAdoptedFields();
checkDeep(beforeSwitch.coveredFieldNames, ['name'], 'the first model reports the positions its own sections cover');
switching.unregister('surface-a');
liveModel.value = 'sc.general.contract';
switching.register({ sectionId: 'surface-b', ruleFieldNames: () => ['contract_no'], validate: async () => [] });
const afterSwitch = await switching.validateAdoptedFields();
check(switching.adopted.value, true, 'the second model is adopted by the same policy, not by a second policy');
checkDeep(afterSwitch.fieldNames, [], 'the previous model\'s rejection cannot reach the new surface');
checkDeep(afterSwitch.coveredFieldNames, ['contract_no'], 'the new surface covers only the positions it declares');
check(
  afterSwitch.coveredFieldNames.includes('name'),
  false,
  'a stale field code cannot remain covered after the surface changed',
);
liveModel.value = 'payment.request';
check(switching.adopted.value, false, 'a surface outside the scope is not adopted later either');
checkDeep(
  await switching.validateAdoptedFields(),
  { ok: true, fieldNames: [], coveredFieldNames: [] },
  'leaving the adopted scope stops gating the save without a page reload',
);

const recordScopeError = buildRequiredFieldErrorPayload(rejected, { model: 'project.project', recordId: 501 }).fieldErrors.name;
check(errorOwnsRecordScope(recordScopeError, { model: 'project.project', recordId: 501 }), true, 'an adopted rejection owns the record it was raised for');
check(errorOwnsRecordScope(recordScopeError, { model: 'project.project', recordId: 502 }), false, 'the same rejection cannot leak onto the next record');
check(errorOwnsRecordScope(recordScopeError, { model: 'sc.general.contract', recordId: 501 }), false, 'the same rejection cannot leak onto another model');

const runtimeSource = readSource('frontend/apps/web/src/pages/contractForm/standardFormCompositionRuntime.ts');
check(/provide\(/.test(runtimeSource), true, 'the page-level runtime provides the registry to the sections');
check(
  runtimeSource.indexOf('createStandardFormValidationRegistry') < runtimeSource.indexOf('provide('),
  true,
  'the registry is created before it is provided',
);

// ---------------------------------------------------------------------------
// Part 6 — the shipped call sites are the ones under test
// ---------------------------------------------------------------------------
const sectionSource = readSource('frontend/apps/web/src/components/template/FormSection.vue');
check(sectionSource.includes('<ScForm'), true, 'the section renders the official form container');
check(sectionSource.includes('<ScFormItem'), true, 'the section renders the official form item');
check(
  sectionSource.includes(':bare="!adoptedComposition"'),
  true,
  'an unadopted section keeps the exact DOM it had instead of a half-applied form',
);
check(sectionSource.includes('instance.validate()'), true, 'the section validates through the engine, not a local rule checker');
check(
  sectionSource.includes('data-validation-target'),
  true,
  'the correction positions the error layer resolves are still registered',
);
check(
  sectionSource.includes('standardFormComposition?.register({'),
  true,
  'the section registers its validation with the page runtime',
);
check(
  sectionSource.includes('onBeforeUnmount(() => {'),
  true,
  'a section that leaves stops being validated',
);
check(
  sectionSource.includes(':rules="adoptedRules[field.name]"'),
  true,
  'the field item receives the rules declared for that business field',
);

const actionsSource = readSource('frontend/apps/web/src/pages/contractForm/useRecordFormActions.ts');
check(
  actionsSource.indexOf('await runAdoptedFormValidation()') < actionsSource.indexOf('await validateBeforeSaveRecord({'),
  true,
  'the adopted engine is asked before the write, not after it',
);
check(
  actionsSource.includes('resolveStandardFormComposition({ model: model.value }).adopted'),
  true,
  'the save gate derives adoption from the declared model, not from whether a callback was passed',
);
check(
  actionsSource.includes('coverageMissing'),
  true,
  'an adopted surface with required positions but no registered section fails closed instead of passing',
);
check(
  actionsSource.includes('excludedRequiredFieldNames: adoptedValidation.coveredFieldNames'),
  true,
  'exactly the engine-covered positions are excluded from the page-level precheck',
);
check(
  sectionSource.includes('adopted form engine returned an unrecognised validation result'),
  true,
  'a section whose engine cannot be read refuses to answer "passed"',
);
check(
  actionsSource.includes('validationFieldErrors.value = payload.fieldErrors;'),
  true,
  'an adopted rejection enters the single error store',
);
check(
  actionsSource.includes('await focusFirstValidationError();'),
  true,
  'an adopted rejection uses the existing focus entry',
);
check(
  actionsSource.includes("payload.messages"),
  true,
  'an adopted rejection reaches the form-level summary',
);
check(
  actionsSource.includes('表单校验未能完成，请重试。'),
  true,
  'a section that cannot answer stops the save with a form-level message',
);

const pageSource = readSource('frontend/apps/web/src/pages/ContractFormPage.vue');
check(
  pageSource.includes('createStandardFormCompositionRuntime(() => model.value)'),
  true,
  'the page runtime is scoped to the model the contract declared',
);
check(
  pageSource.includes('validateAdoptedFormSections: () => standardFormComposition.validateAdoptedFields()'),
  true,
  'the page hands the adopted validation to the save chain',
);

const scFormSource = readSource('frontend/apps/web/src/components/design-system/ScForm.vue');
for (const method of ['clearValidate', 'reset', 'setValidateMessage', 'submit', 'validate', 'validateOnly']) {
  check(scFormSource.includes(`${method}:`), true, `the adapter exposes the engine method ${method}`);
}
check(/tdesign-vue-next/.test(scFormSource), false, 'the adapter reaches the vendor only through the project bridge');
check(/from ['"]\.\/tdesignPrimitiveBridge['"]/.test(scFormSource), true, 'the adapter names the project bridge as its only vendor boundary');

console.log(`[standard-form-composition-adoption] explicit adoption scope, shared emptiness authority, engine result reading, single error store, fail-closed registry, shipped call sites: ${cases} cases passed`);
