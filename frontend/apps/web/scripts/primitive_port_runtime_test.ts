import assert from 'node:assert/strict';
import {
  PRIMITIVE_REQUIRED_CAPABILITIES,
  SCENE_PRIMITIVE_NAMES,
  validatePrimitiveAdapterRuntimeShape,
} from '@sc/ui/primitive-port';

type RuntimeBindingFixture = {
  component: object;
  contract: {
    primitive: string;
    portVersion: number;
    capabilities: string[];
  };
};

function binding(primitive: (typeof SCENE_PRIMITIVE_NAMES)[number]): RuntimeBindingFixture {
  return {
    component: {},
    contract: {
      primitive,
      portVersion: 1,
      capabilities: [...PRIMITIVE_REQUIRED_CAPABILITIES[primitive]],
    },
  };
}

function validAdapter(): Record<string, RuntimeBindingFixture> {
  return Object.fromEntries(SCENE_PRIMITIVE_NAMES.map((primitive) => [primitive, binding(primitive)]));
}

const negativeBoundaries = [
  'missing binding',
  'wrong identity',
  'missing capability',
  'duplicate capability',
  'unknown capability',
  'Button/search',
  'Icon/loading',
  'Table/ime',
  'wrong port version',
] as const;

const valid = validatePrimitiveAdapterRuntimeShape(validAdapter());
assert.deepEqual(valid, { ok: true });

const missing = validAdapter();
delete missing.Input;
const missingResult = validatePrimitiveAdapterRuntimeShape(missing);
assert.equal(missingResult.ok, false);
if (!missingResult.ok) {
  assert.equal(missingResult.error.detail.code, 'SCENE_PRIMITIVE_CONTRACT_ERROR');
  assert.equal(missingResult.error.detail.primitive, 'Input');
  assert.equal(missingResult.error.detail.capability, 'binding');
}

const wrongIdentity = validAdapter();
wrongIdentity.Button.contract.primitive = 'Input';
const identityResult = validatePrimitiveAdapterRuntimeShape(wrongIdentity);
assert.equal(identityResult.ok, false);
if (!identityResult.ok) {
  assert.equal(identityResult.error.detail.primitive, 'Button');
  assert.equal(identityResult.error.detail.capability, 'identity');
}

const missingCapability = validAdapter();
missingCapability.Input.contract.capabilities = ['value', 'change', 'focus', 'blur', 'keyboard'];
const capabilityResult = validatePrimitiveAdapterRuntimeShape(missingCapability);
assert.equal(capabilityResult.ok, false);
if (!capabilityResult.ok) {
  assert.equal(capabilityResult.error.detail.primitive, 'Input');
  assert.equal(capabilityResult.error.detail.capability, 'ime');
}

const duplicateCapability = validAdapter();
duplicateCapability.Icon.contract.capabilities = ['semantic-icon', 'semantic-icon'];
const duplicateResult = validatePrimitiveAdapterRuntimeShape(duplicateCapability);
assert.equal(duplicateResult.ok, false);
if (!duplicateResult.ok) {
  assert.equal(duplicateResult.error.detail.primitive, 'Icon');
  assert.equal(duplicateResult.error.detail.capability, 'capabilities');
}

const unsupportedCapability = validAdapter();
unsupportedCapability.DateField.contract.capabilities = [
  ...PRIMITIVE_REQUIRED_CAPABILITIES.DateField,
  'selection',
];
const unsupportedResult = validatePrimitiveAdapterRuntimeShape(unsupportedCapability);
assert.equal(unsupportedResult.ok, false);
if (!unsupportedResult.ok) {
  assert.equal(unsupportedResult.error.detail.primitive, 'DateField');
  assert.equal(unsupportedResult.error.detail.capability, 'selection');
}

const buttonSearch = validAdapter();
buttonSearch.Button.contract.capabilities = [...PRIMITIVE_REQUIRED_CAPABILITIES.Button, 'search'];
const buttonSearchResult = validatePrimitiveAdapterRuntimeShape(buttonSearch);
assert.equal(buttonSearchResult.ok, false);
if (!buttonSearchResult.ok) {
  assert.equal(buttonSearchResult.error.detail.primitive, 'Button');
  assert.equal(buttonSearchResult.error.detail.capability, 'search');
}

const iconLoading = validAdapter();
iconLoading.Icon.contract.capabilities = [...PRIMITIVE_REQUIRED_CAPABILITIES.Icon, 'loading'];
const iconLoadingResult = validatePrimitiveAdapterRuntimeShape(iconLoading);
assert.equal(iconLoadingResult.ok, false);
if (!iconLoadingResult.ok) {
  assert.equal(iconLoadingResult.error.detail.primitive, 'Icon');
  assert.equal(iconLoadingResult.error.detail.capability, 'loading');
}

const tableIme = validAdapter();
tableIme.Table.contract.capabilities = [...PRIMITIVE_REQUIRED_CAPABILITIES.Table, 'ime'];
const tableImeResult = validatePrimitiveAdapterRuntimeShape(tableIme);
assert.equal(tableImeResult.ok, false);
if (!tableImeResult.ok) {
  assert.equal(tableImeResult.error.detail.primitive, 'Table');
  assert.equal(tableImeResult.error.detail.capability, 'ime');
}

const selectWithPopup = validAdapter();
selectWithPopup.Select.contract.capabilities = [...PRIMITIVE_REQUIRED_CAPABILITIES.Select];
assert.deepEqual(validatePrimitiveAdapterRuntimeShape(selectWithPopup), { ok: true });

const buttonWithLoading = validAdapter();
buttonWithLoading.Button.contract.capabilities = [...PRIMITIVE_REQUIRED_CAPABILITIES.Button];
assert.deepEqual(validatePrimitiveAdapterRuntimeShape(buttonWithLoading), { ok: true });

const wrongVersion = validAdapter();
wrongVersion.Table.contract.portVersion = 2;
const versionResult = validatePrimitiveAdapterRuntimeShape(wrongVersion);
assert.equal(versionResult.ok, false);
if (!versionResult.ok) {
  assert.equal(versionResult.error.detail.primitive, 'Table');
  assert.equal(versionResult.error.detail.capability, 'portVersion');
}

assert.equal(
  validatePrimitiveAdapterRuntimeShape(null).ok,
  false,
  'non-object adapter must fail closed',
);
assert.equal(negativeBoundaries.length, 9);
console.log(`[primitive_port_runtime_test] PASS primitives=${SCENE_PRIMITIVE_NAMES.length} boundaries=${negativeBoundaries.length}`);
