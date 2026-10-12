import { strict as assert } from 'node:assert';
import {
  componentKeyForSemantic,
  professionalComponentRegistrations,
  resolveSemanticRegistration,
} from '../src/app/presentation/professionalComponentRegistry';
import { SEMANTIC_REGISTRY_ROWS } from '../src/app/presentation/semantic_registry.generated';

// The runtime resolves a field by the semantic it declares, not by a component
// key the caller has to know in advance.  These are the four meanings the owner
// named; the expected component keys come from the declaration, so a
// declaration edit changes this table's authority without new frontend code.
const NAMED_RESOLUTIONS: ReadonlyArray<readonly [string, string]> = [
  ['money', 'sc.value.money'],
  ['date', 'sc.input.date'],
  ['relation', 'sc.relation.many2one'],
  ['status', 'sc.display.status'],
];

let cases = 0;
for (const [semantic, componentKey] of NAMED_RESOLUTIONS) {
  const registration = resolveSemanticRegistration(semantic);
  assert.ok(registration, `semantic ${semantic} did not resolve to a registration`);
  assert.equal(registration.componentKey, componentKey, `semantic ${semantic} resolved to the wrong component`);
  assert.equal(componentKeyForSemantic(semantic), componentKey);
  cases += 3;
}

// Case and whitespace are normalised; an uppercase contract value must not
// become an undeclared semantic.
assert.equal(componentKeyForSemantic('  Money '), 'sc.value.money');
cases += 1;

// An undeclared semantic is a contract defect, not a silent default.
assert.equal(resolveSemanticRegistration('not_a_declared_semantic'), null);
assert.equal(componentKeyForSemantic('not_a_declared_semantic'), null);
assert.equal(resolveSemanticRegistration(''), null);
assert.equal(resolveSemanticRegistration('   '), null);
assert.equal(componentKeyForSemantic(''), null);
cases += 5;

// The index is the generated table and nothing else: every row resolves to its
// own registration, and no extra row hides in the registry module.
assert.equal(
  SEMANTIC_REGISTRY_ROWS.length,
  professionalComponentRegistrations.length,
  'the semantic index and the component registry must agree on the vocabulary size',
);
cases += 1;
for (const row of SEMANTIC_REGISTRY_ROWS) {
  const registration = resolveSemanticRegistration(row.semanticType);
  assert.ok(registration, `generated semantic ${row.semanticType} is not resolvable`);
  assert.equal(registration.componentKey, row.componentKey);
  assert.equal(registration.renderer, row.renderer);
  assert.equal(registration.readiness, row.readiness);
  cases += 4;
}

console.log(`[semantic_runtime_resolution_test] PASS cases=${cases}`);
