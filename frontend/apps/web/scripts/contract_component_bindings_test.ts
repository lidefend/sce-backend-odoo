import assert from 'node:assert/strict';
import {
  CONTRACT_BASE_COMPONENT_BINDINGS,
  contractBaseComponentBindingKeys,
  resolveContractBaseComponentBinding,
  type ContractBaseImplementationId,
} from '../src/components/professional-fields/contractComponentBindings';
import { PROFESSIONAL_BASE_FIELD_TYPES } from '../src/components/professional-fields/professionalBaseFieldModel';
import { SEMANTIC_REGISTRY_ROWS } from '../src/app/presentation/semantic_registry.generated';

const baseFieldTypes = new Set<string>(PROFESSIONAL_BASE_FIELD_TYPES);
const platformRows = SEMANTIC_REGISTRY_ROWS.filter((row) => (
  row.readiness !== 'fail_closed'
  && row.renderer === 'FormSectionField'
));
const expectedBaseKeys = [...new Set(platformRows.flatMap((row) => {
  const hasBaseImplementation = row.supportedFieldTypes.includes('*')
    || row.supportedFieldTypes.some((fieldType) => baseFieldTypes.has(fieldType));
  return hasBaseImplementation ? [row.componentKey] : [];
}))].sort();

assert.deepEqual(
  [...contractBaseComponentBindingKeys()].sort(),
  expectedBaseKeys,
  'base binding keys must equal the generated ready Contract base-field identities',
);

const implementations = new Set<ContractBaseImplementationId>([
  'ScInput',
  'ScTextarea',
  'RestrictedHtmlEditor',
  'ScNumberInput',
  'ScSelect',
  'ScCheckbox',
  'ScDateField',
]);
const variants = new Set<string>();
let cases = 0;

for (const binding of CONTRACT_BASE_COMPONENT_BINDINGS) {
  assert.ok(implementations.has(binding.implementation), `unknown implementation ${binding.implementation}`);
  for (const fieldType of binding.fieldTypes) {
    const variant = `${binding.componentKey}:${fieldType}`;
    assert.equal(variants.has(variant), false, `duplicate binding variant ${variant}`);
    variants.add(variant);

    const row = SEMANTIC_REGISTRY_ROWS.find((candidate) => candidate.componentKey === binding.componentKey);
    assert.ok(row, `binding names unregistered componentKey ${binding.componentKey}`);
    assert.ok(
      row.supportedFieldTypes.includes('*') || row.supportedFieldTypes.includes(fieldType),
      `${binding.componentKey} does not declare field type ${fieldType}`,
    );
    const resolved = resolveContractBaseComponentBinding({
      componentKey: binding.componentKey,
      type: fieldType,
    });
    assert.equal(resolved?.bindingId, binding.bindingId, `resolver missed ${variant}`);
    cases += 1;
  }
}

assert.equal(
  resolveContractBaseComponentBinding({ componentKey: 'sc.input.textarea', type: 'html' })?.implementation,
  'RestrictedHtmlEditor',
);
assert.equal(
  resolveContractBaseComponentBinding({ componentKey: 'sc.input.datetime', type: 'datetime' })?.controlKind,
  'datetime',
);
assert.equal(
  resolveContractBaseComponentBinding({ componentKey: 'sc.input.boolean', type: 'boolean' })?.implementation,
  'ScCheckbox',
);
assert.equal(
  resolveContractBaseComponentBinding({ componentKey: 'sc.input.date', type: 'date' })?.implementation,
  'ScDateField',
);
assert.equal(
  resolveContractBaseComponentBinding({ componentKey: 'sc.input.number', type: 'monetary' }),
  null,
  'monetary values remain on the business-value renderer, not the generic number binding',
);
assert.equal(
  resolveContractBaseComponentBinding({ componentKey: 'sc.input.text', type: 'text' }),
  null,
  'field-type mismatch must not fall through',
);
assert.equal(
  resolveContractBaseComponentBinding({ componentKey: 'sc.unknown', type: 'char' }),
  null,
  'unknown componentKey must fail closed',
);
assert.equal(
  resolveContractBaseComponentBinding({ componentKey: '', type: 'char' }),
  null,
  'legacy fields without a Contract componentKey use the compatibility host',
);

console.log(
  `[contract_component_bindings_test] PASS keys=${expectedBaseKeys.length} variants=${cases} implementations=${implementations.size}`,
);
