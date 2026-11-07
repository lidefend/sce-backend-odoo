import { strict as assert } from 'node:assert';
import {
  componentKeyForSemantic,
  FORM_RELATION_ONE2MANY_CAPABILITY,
  FORM_SECTION_TYPE_DIRECTED_RENDERER,
  isIndustryComponentKey,
  isRegisteredComponentKey,
  PROFESSIONAL_COMPONENT_RENDERERS,
  professionalComponentRegistrations,
  registerIndustryRendererExtensions,
  resolveIndustryRendererForField,
  resolveContractProfessionalComponent,
  resolveProfessionalComponent,
  resolveProfessionalComponentRegistration,
  resolveSemanticRegistration,
  unregisterIndustryRendererExtensions,
  type ProfessionalComponentRegistration,
  type ProfessionalComponentRenderer,
} from '../src/app/presentation/professionalComponentRegistry';
import {
  parseRendererContractVersionRange,
  parseRendererVersion,
  rendererSupportsContractVersion,
} from '../src/app/presentation/rendererProtocolVersion';
import { RENDERER_CAPABILITY_PROVIDERS } from '../src/app/presentation/semantic_registry.generated';
import {
  detailAmountBindingConfig,
  optionalDetailCollectionConfig,
  optionalDetailCollectionPresentation,
  optionalDetailCollectionRemovalConfirmation,
  optionalDetailCollectionSpan,
} from '../src/components/professional-fields/professionalDetailCollectionModel';

assert.deepEqual(RENDERER_CAPABILITY_PROVIDERS, {
  [FORM_RELATION_ONE2MANY_CAPABILITY]: 'FormSection.relationAdapter',
});
assert.deepEqual(parseRendererVersion('2.2.0'), [2, 2, 0]);
assert.equal(parseRendererVersion('02.2.0'), null);
assert.deepEqual(parseRendererContractVersionRange('>=2.0.0 <2.3.0'), {
  minimum: [2, 0, 0],
  maximumExclusive: [2, 3, 0],
});
assert.equal(rendererSupportsContractVersion('>=2.0.0 <2.3.0', '2.0.0'), true);
assert.equal(rendererSupportsContractVersion('>=2.0.0 <2.3.0', '2.2.9'), true);
assert.equal(rendererSupportsContractVersion('>=2.0.0 <2.3.0', '2.3.0'), false);
assert.equal(rendererSupportsContractVersion('>=2.0.0 <2.3.0', '1.9.9'), false);

const ready = resolveProfessionalComponent({
  componentKey: 'sc.input.text', fieldType: 'char', pageContractVersion: '2.2.0', presentationMode: 'task', renderProfile: 'edit',
});
assert.equal(ready.readiness, 'ready');
assert.equal(ready.renderer, 'ProfessionalBaseFieldControl');
const contractBound = resolveContractProfessionalComponent({
  componentKey: 'sc.input.text', fieldType: 'char', presentationMode: 'task', renderProfile: 'edit',
  pageContractVersion: '2.2.0',
  clientType: 'web_pc',
  contractRegistryEntry: { version: '1.0' },
});
assert.equal(contractBound.contractVersion, '1.0');
assert.equal(contractBound.renderer, 'ProfessionalBaseFieldControl');
assert.equal(contractBound.pageContractVersion, '2.2.0');
assert.equal(contractBound.rendererVersion, '1.0.0');
assert.equal(contractBound.supportedContractVersion, '>=2.0.0 <2.3.0');
assert.throws(() => resolveContractProfessionalComponent({
  componentKey: 'sc.input.text', fieldType: 'char', presentationMode: 'task', renderProfile: 'edit',
  pageContractVersion: '2.3.0', clientType: 'web_pc', contractRegistryEntry: { version: '1.0' },
}), /PROFESSIONAL_COMPONENT_CONTRACT_VERSION_UNSUPPORTED/);
assert.throws(() => resolveContractProfessionalComponent({
  componentKey: 'sc.input.text', fieldType: 'char', presentationMode: 'task', renderProfile: 'edit',
  pageContractVersion: '2.3', clientType: 'web_pc', contractRegistryEntry: { version: '1.0' },
}), /PROFESSIONAL_COMPONENT_PAGE_CONTRACT_VERSION_INVALID/);
assert.throws(() => resolveContractProfessionalComponent({
  componentKey: 'sc.input.text', fieldType: 'char', presentationMode: 'task', renderProfile: 'edit',
  pageContractVersion: '2.2.0',
  clientType: 'web_pc', contractRegistryEntry: {},
}), /PROFESSIONAL_COMPONENT_CONTRACT_REGISTRY_MISSING/);
assert.throws(() => resolveContractProfessionalComponent({
  componentKey: 'sc.input.text', fieldType: 'char', presentationMode: 'task', renderProfile: 'edit',
  pageContractVersion: '2.2.0',
  clientType: 'web_pc', contractRegistryEntry: { version: '1.0', adapter: { web_pc: 'ElInput' } },
}), /PROFESSIONAL_COMPONENT_CONTRACT_RENDER_TRAIT_FORBIDDEN:sc\.input\.text:adapter/);
assert.throws(() => resolveContractProfessionalComponent({
  componentKey: 'sc.input.text', fieldType: 'char', presentationMode: 'task', renderProfile: 'edit',
  pageContractVersion: '2.2.0',
  clientType: 'web_pc', contractRegistryEntry: { version: '1.0', selectedAdapter: 'TDesignInput' },
}), /PROFESSIONAL_COMPONENT_CONTRACT_RENDER_TRAIT_FORBIDDEN:sc\.input\.text:selectedAdapter/);
assert.equal(resolveProfessionalComponent({
  componentKey: 'sc.relation.many2one', fieldType: 'many2one', presentationMode: 'task', renderProfile: 'edit',
}).renderer, 'ProfessionalRelationFieldControl');
assert.equal(resolveProfessionalComponent({
  componentKey: 'sc.relation.many2many', fieldType: 'many2many', presentationMode: 'workspace', renderProfile: 'readonly',
}).renderer, 'ProfessionalRelationFieldControl');
assert.equal(resolveProfessionalComponent({
  componentKey: 'sc.relation.table', fieldType: 'one2many', presentationMode: 'workspace', renderProfile: 'edit',
}).renderer, 'ProfessionalDetailCollectionControl');
const paymentRenderer = 'PaymentSettlementDetailCollectionControl';
const paymentRow = {
  componentKey: 'sc.payment.settlement_detail_collection',
  semanticType: 'payment_settlement_detail_collection',
  supportedFieldTypes: ['one2many'],
  readiness: 'ready',
  renderer: paymentRenderer,
  rendererVersion: '1.0.0',
  supportedContractVersion: '>=2.0.0 <2.3.0',
  requiredCapabilities: [FORM_RELATION_ONE2MANY_CAPABILITY],
} as const;
const dummyIndustryComponent = {} as never;
assert.throws(() => resolveProfessionalComponent({
  componentKey: paymentRow.componentKey, fieldType: 'one2many', presentationMode: 'task', renderProfile: 'edit',
}), /PROFESSIONAL_COMPONENT_UNREGISTERED/);
assert.equal(isRegisteredComponentKey(paymentRow.componentKey), false);
assert.equal(isIndustryComponentKey(paymentRow.componentKey), false);
assert.equal(resolveIndustryRendererForField({
  componentKey: paymentRow.componentKey,
  componentRenderer: paymentRenderer,
  fieldType: 'one2many',
  pageContractVersion: '2.2.0',
  presentationMode: 'task',
  renderProfile: 'edit',
  capabilities: [FORM_RELATION_ONE2MANY_CAPABILITY],
}), null);
registerIndustryRendererExtensions([{ row: paymentRow, component: dummyIndustryComponent }]);
assert.equal(isRegisteredComponentKey(paymentRow.componentKey), true);
assert.equal(isIndustryComponentKey(paymentRow.componentKey), true);
assert.equal(resolveSemanticRegistration(paymentRow.semanticType)?.componentKey, paymentRow.componentKey);
assert.equal(componentKeyForSemantic(paymentRow.semanticType), paymentRow.componentKey);
assert.equal(resolveProfessionalComponent({
  componentKey: paymentRow.componentKey, fieldType: 'one2many', pageContractVersion: '2.2.0',
  presentationMode: 'task', renderProfile: 'edit', capabilities: [FORM_RELATION_ONE2MANY_CAPABILITY],
}).renderer, paymentRenderer);
const industryContract = resolveContractProfessionalComponent({
  componentKey: paymentRow.componentKey,
  fieldType: 'one2many',
  pageContractVersion: '2.2.0',
  presentationMode: 'task',
  renderProfile: 'edit',
  clientType: 'web_pc',
  contractRegistryEntry: { version: '1.0.0' },
});
assert.equal(industryContract.renderer, paymentRenderer);
assert.equal(industryContract.contractVersion, '1.0.0');
assert.equal(resolveIndustryRendererForField({
  componentKey: paymentRow.componentKey,
  componentRenderer: paymentRenderer,
  fieldType: 'one2many',
  pageContractVersion: '2.2.0',
  presentationMode: 'task',
  renderProfile: 'edit',
  capabilities: [FORM_RELATION_ONE2MANY_CAPABILITY],
}), dummyIndustryComponent);
assert.equal(resolveIndustryRendererForField({
  componentKey: paymentRow.componentKey,
  componentRenderer: paymentRenderer,
  fieldType: 'one2many',
  pageContractVersion: '2.2.0',
  presentationMode: 'task',
  renderProfile: 'edit',
}), null);
assert.equal(resolveIndustryRendererForField({
  componentKey: paymentRow.componentKey,
  componentRenderer: paymentRenderer,
  fieldType: 'one2many',
  pageContractVersion: '2.3.0',
  presentationMode: 'task',
  renderProfile: 'edit',
  capabilities: [FORM_RELATION_ONE2MANY_CAPABILITY],
}), null);
assert.equal(resolveIndustryRendererForField({
  componentKey: paymentRow.componentKey,
  componentRenderer: 'OtherRenderer',
  fieldType: 'one2many',
  pageContractVersion: '2.2.0',
  presentationMode: 'task',
  renderProfile: 'edit',
  capabilities: [FORM_RELATION_ONE2MANY_CAPABILITY],
}), null);
assert.equal(resolveIndustryRendererForField({
  componentKey: paymentRow.componentKey,
  componentRenderer: paymentRenderer,
  fieldType: 'many2one',
  pageContractVersion: '2.2.0',
  presentationMode: 'task',
  renderProfile: 'edit',
  capabilities: [FORM_RELATION_ONE2MANY_CAPABILITY],
}), null);
assert.equal(resolveIndustryRendererForField({
  componentKey: paymentRow.componentKey,
  componentRenderer: paymentRenderer,
  fieldType: 'one2many',
  pageContractVersion: '2.2.0',
  presentationMode: 'unsupported' as never,
  renderProfile: 'readonly',
  capabilities: [FORM_RELATION_ONE2MANY_CAPABILITY],
}), null);
assert.equal(resolveIndustryRendererForField({
  componentKey: paymentRow.componentKey,
  componentRenderer: paymentRenderer,
  fieldType: 'one2many',
  pageContractVersion: '2.2.0',
  presentationMode: 'task',
  renderProfile: 'unsupported' as never,
  capabilities: [FORM_RELATION_ONE2MANY_CAPABILITY],
}), null);
assert.equal(resolveIndustryRendererForField({
  componentKey: 'sc.payment.other',
  componentRenderer: paymentRenderer,
  fieldType: 'one2many',
  pageContractVersion: '2.2.0',
  presentationMode: 'task',
  renderProfile: 'edit',
  capabilities: [FORM_RELATION_ONE2MANY_CAPABILITY],
}), null);

const stagedRow = {
  componentKey: 'sc.fixture.atomic_first',
  semanticType: 'fixture_atomic_first',
  supportedFieldTypes: ['char'],
  readiness: 'ready',
  renderer: 'FixtureAtomicFirstRenderer',
  rendererVersion: '1.0.0',
  supportedContractVersion: '>=2.0.0 <2.3.0',
  requiredCapabilities: [],
} as const;
assert.throws(() => registerIndustryRendererExtensions([
  { row: stagedRow, component: dummyIndustryComponent },
  {
    row: { ...stagedRow, componentKey: 'sc.fixture.atomic_second', semanticType: 'fixture_atomic_second', renderer: 'FixtureAtomicSecondRenderer' },
    component: null as never,
  },
]), /INDUSTRY_RENDERER_COMPONENT_MISSING/);
assert.equal(isRegisteredComponentKey(stagedRow.componentKey), false, 'a rejected batch must not leave a half registration');

assert.throws(() => registerIndustryRendererExtensions([{ row: paymentRow, component: dummyIndustryComponent }]),
  /INDUSTRY_REGISTRATION_DUPLICATE_COMPONENT_KEY/);
assert.throws(() => registerIndustryRendererExtensions([{
  row: { ...paymentRow, componentKey: 'sc.fixture.duplicate_semantic', renderer: 'FixtureDuplicateSemanticRenderer' },
  component: dummyIndustryComponent,
}]), /INDUSTRY_REGISTRATION_DUPLICATE_SEMANTIC/);
assert.throws(() => registerIndustryRendererExtensions([{
  row: { ...paymentRow, componentKey: 'sc.fixture.duplicate_renderer', semanticType: 'fixture_duplicate_renderer' },
  component: dummyIndustryComponent,
}]), /INDUSTRY_RENDERER_DUPLICATE/);
assert.throws(() => registerIndustryRendererExtensions([{
  row: { ...paymentRow, componentKey: 'sc.fixture.reserved_renderer', semanticType: 'fixture_reserved_renderer', renderer: 'ProfessionalBaseFieldControl' },
  component: dummyIndustryComponent,
}]), /INDUSTRY_RENDERER_RESERVED_PLATFORM_RENDERER/);
assert.throws(() => registerIndustryRendererExtensions([{
  row: { ...paymentRow, componentKey: 'sc.fixture.no_field_types', semanticType: 'fixture_no_field_types', renderer: 'FixtureNoFieldTypesRenderer', supportedFieldTypes: [] },
  component: dummyIndustryComponent,
}]), /INDUSTRY_REGISTRATION_FIELD_TYPES_MISSING/);
assert.throws(() => registerIndustryRendererExtensions([{
  row: { ...paymentRow, componentKey: '', semanticType: 'fixture_missing_key', renderer: 'FixtureMissingKeyRenderer' },
  component: dummyIndustryComponent,
}]), /INDUSTRY_REGISTRATION_IDENTITY_MISSING/);
assert.throws(() => registerIndustryRendererExtensions([{
  row: { ...paymentRow, componentKey: 'sc.fixture.bad_renderer_version', semanticType: 'fixture_bad_renderer_version', renderer: 'FixtureBadRendererVersion', rendererVersion: '1.0' },
  component: dummyIndustryComponent,
}]), /SEMANTIC_REGISTRY_RENDERER_VERSION_INVALID/);
assert.throws(() => registerIndustryRendererExtensions([{
  row: { ...paymentRow, componentKey: 'sc.fixture.bad_contract_version', semanticType: 'fixture_bad_contract_version', renderer: 'FixtureBadContractVersion', supportedContractVersion: '^2' },
  component: dummyIndustryComponent,
}]), /SEMANTIC_REGISTRY_CONTRACT_VERSION_INVALID/);
assert.throws(() => registerIndustryRendererExtensions([{
  row: { ...paymentRow, componentKey: 'sc.fixture.unknown_capability', semanticType: 'fixture_unknown_capability', renderer: 'FixtureUnknownCapability', requiredCapabilities: ['form.relation.unknown'] },
  component: dummyIndustryComponent,
}]), /SEMANTIC_REGISTRY_CAPABILITY_UNPROVIDED/);
assert.throws(() => unregisterIndustryRendererExtensions([
  paymentRow.componentKey,
  'sc.fixture.unknown_unregister',
]), /INDUSTRY_REGISTRATION_UNREGISTER_UNKNOWN/);
assert.equal(isRegisteredComponentKey(paymentRow.componentKey), true);
unregisterIndustryRendererExtensions([paymentRow.componentKey]);
assert.equal(isRegisteredComponentKey(paymentRow.componentKey), false);
assert.equal(isIndustryComponentKey(paymentRow.componentKey), false);
assert.equal(resolveIndustryRendererForField({
  componentKey: paymentRow.componentKey,
  componentRenderer: paymentRenderer,
  fieldType: 'one2many',
  pageContractVersion: '2.2.0',
  presentationMode: 'task',
  renderProfile: 'edit',
  capabilities: [FORM_RELATION_ONE2MANY_CAPABILITY],
}), null);
const optionalDetails = optionalDetailCollectionConfig({
  key: 'line_ids', name: 'line_ids', label: 'Lines', type: 'one2many', required: false, readonly: false,
  componentConfig: {
    optionalDetails: {
      entryLabel: 'Use details',
      populatedLabel: 'Details',
      directAmountMessage: 'The amount can be entered directly.',
      linkedAmountMessage: 'The total is authoritative.',
      lastRowRemovalActionLabel: 'Stop using details',
      lastRowRemovalMessage: 'The last total is preserved.',
    },
  },
});
assert.equal(optionalDetails?.entryLabel, 'Use details');
assert.equal(optionalDetails?.populatedLabel, 'Details');
assert.equal(optionalDetails?.lastRowRemovalMessage, 'The last total is preserved.');
const amountBinding = detailAmountBindingConfig({
  key: 'line_ids', name: 'line_ids', label: 'Lines', type: 'one2many', required: false, readonly: false,
  componentConfig: {
    amountBinding: {
      mode: 'sum_when_nonempty', sourceField: 'line_amount', targetField: 'amount',
      activeField: 'active', stateField: 'amount_uses_details',
      rounding: 'currency', emptyBehavior: 'preserve_last_total',
    },
  },
});
assert.deepEqual(amountBinding, {
  mode: 'sum_when_nonempty', sourceField: 'line_amount', targetField: 'amount',
  activeField: 'active', stateField: 'amount_uses_details',
  rounding: 'currency', emptyBehavior: 'preserve_last_total',
});
assert.equal(detailAmountBindingConfig({
  key: 'line_ids', name: 'line_ids', label: 'Lines', type: 'one2many', required: false, readonly: false,
  componentConfig: {
    amountBinding: {
      mode: 'sum_when_nonempty', sourceField: 'amount', targetField: 'amount',
      activeField: 'active', stateField: 'amount_uses_details',
      rounding: 'currency', emptyBehavior: 'preserve_last_total',
    },
  },
}), null);
assert.equal(detailAmountBindingConfig({
  key: 'line_ids', name: 'line_ids', label: 'Lines', type: 'one2many', required: false, readonly: false,
  componentConfig: {
    amountBinding: {
      mode: 'sum_always', sourceField: 'line_amount', targetField: 'amount',
      activeField: 'active', stateField: 'amount_uses_details',
      rounding: 'currency', emptyBehavior: 'zero',
    },
  },
}), null);
assert.equal(optionalDetailCollectionConfig({
  key: 'line_ids', name: 'line_ids', label: 'Lines', type: 'one2many', required: false, readonly: false,
  componentConfig: { optionalDetails: { entryLabel: '', populatedLabel: 'Details' } },
}), null);
const optionalField = {
  key: 'line_ids', name: 'line_ids', label: 'Lines', type: 'one2many', required: false, readonly: false,
  componentKey: 'sc.example.optional_collection',
  componentConfig: {
    optionalDetails: {
      entryLabel: 'Use details', populatedLabel: 'Details',
      directAmountMessage: 'Direct amount', linkedAmountMessage: 'Linked total',
      lastRowRemovalActionLabel: 'Stop using details', lastRowRemovalMessage: 'Last total is preserved',
    },
  },
} as never;
assert.deepEqual(optionalDetailCollectionPresentation(optionalField, 0), {
  render: true, open: false, title: 'Use details', linkedAmountMessage: 'Direct amount',
});
assert.deepEqual(optionalDetailCollectionPresentation(optionalField, 2, true), {
  render: true, open: true, title: 'Details（2 条）', linkedAmountMessage: 'Linked total',
});
assert.deepEqual(optionalDetailCollectionPresentation(optionalField, 0, false, 1), {
  render: true, open: true, title: 'Use details', linkedAmountMessage: 'Direct amount',
}, 'pending removal must keep the optional detail disclosure open so undo remains reachable');
assert.equal(optionalDetailCollectionPresentation(optionalField, 2, false)?.linkedAmountMessage, 'Direct amount');
assert.equal(optionalDetailCollectionPresentation({ ...optionalField, readonly: true } as never, 0)?.render, false);
assert.equal(optionalDetailCollectionRemovalConfirmation(optionalField, 2), null);
assert.deepEqual(optionalDetailCollectionRemovalConfirmation(optionalField, 1), {
  actionLabel: 'Stop using details', message: 'Last total is preserved',
});
assert.equal(
  optionalDetailCollectionRemovalConfirmation(optionalField, 1, false),
  null,
  'an unsaved row is cancelled locally and must not use persistent last-row removal confirmation',
);
assert.equal(optionalDetailCollectionSpan(optionalField, 12), 24);
assert.equal(optionalDetailCollectionSpan({
  ...optionalField,
  componentConfig: {},
} as never, 12), 12);
for (const [componentKey, fieldType] of [
  ['sc.value.money', 'monetary'], ['sc.value.percentage', 'float'],
  ['sc.display.status', 'selection'], ['sc.value.duration', 'float'],
] as const) {
  assert.equal(resolveProfessionalComponent({
    componentKey, fieldType, presentationMode: 'workspace', renderProfile: 'readonly',
  }).renderer, 'ProfessionalBusinessValueControl');
}

assert.throws(() => resolveProfessionalComponent({
  componentKey: 'sc.unknown', fieldType: 'char', presentationMode: 'task', renderProfile: 'edit',
}), /PROFESSIONAL_COMPONENT_UNREGISTERED/);
assert.throws(() => resolveProfessionalComponent({
  componentKey: 'sc.input.text', fieldType: 'many2one', presentationMode: 'task', renderProfile: 'edit',
}), /PROFESSIONAL_COMPONENT_FIELD_TYPE_MISMATCH/);
assert.throws(() => resolveProfessionalComponent({
  componentKey: 'sc.input.text', fieldType: '', presentationMode: 'task', renderProfile: 'edit',
}), /PROFESSIONAL_COMPONENT_FIELD_TYPE_MISSING/);

const restricted: ProfessionalComponentRegistration = {
  ...ready,
  componentKey: 'sc.test.restricted',
  supportedPresentationModes: ['task'],
  supportedRenderProfiles: ['edit'],
  requiredCapabilities: ['relation.read'],
  rendererByFieldType: {},
};
const testRegistry = new Map([[restricted.componentKey, restricted]]);
const fallbackRegistry = new Map([["sc.test.fallback", {
  ...restricted,
  componentKey: 'sc.test.fallback',
  readiness: 'readable_fallback' as const,
  fallback: 'ReadableFieldValue',
}]]);
assert.equal(resolveProfessionalComponentRegistration(fallbackRegistry, {
  componentKey: 'sc.test.fallback', fieldType: 'char', presentationMode: 'task', renderProfile: 'edit', capabilities: ['relation.read'],
}).fallback, 'ReadableFieldValue');
assert.throws(() => resolveProfessionalComponentRegistration(testRegistry, {
  componentKey: restricted.componentKey, fieldType: 'char', presentationMode: 'workspace', renderProfile: 'edit',
}), /PROFESSIONAL_COMPONENT_PRESENTATION_MODE_MISMATCH/);
assert.throws(() => resolveProfessionalComponentRegistration(testRegistry, {
  componentKey: restricted.componentKey, fieldType: 'char', presentationMode: 'task', renderProfile: 'readonly',
}), /PROFESSIONAL_COMPONENT_RENDER_PROFILE_MISMATCH/);
assert.throws(() => resolveProfessionalComponentRegistration(testRegistry, {
  componentKey: restricted.componentKey, fieldType: 'char', presentationMode: 'task', renderProfile: 'edit',
  capabilities: [],
}), /PROFESSIONAL_COMPONENT_CAPABILITY_MISSING/);
assert.throws(() => resolveProfessionalComponentRegistration(testRegistry, {
  componentKey: restricted.componentKey,
  fieldType: 'char',
  pageContractVersion: '2.3.0',
  presentationMode: 'task',
  renderProfile: 'edit',
  capabilities: ['relation.read'],
}), /PROFESSIONAL_COMPONENT_CONTRACT_VERSION_UNSUPPORTED/);
assert.equal(resolveProfessionalComponentRegistration(testRegistry, {
  componentKey: restricted.componentKey,
  fieldType: 'char',
  presentationMode: 'task',
  renderProfile: 'edit',
  capabilities: ['relation.read'],
}).componentKey, restricted.componentKey);

for (const componentKey of [
  'sc.auth.credential_entry',
  'sc.auth.secret_confirmation',
  'sc.auth.challenge_status',
  'sc.auth.one_time_secret',
  'sc.auth.support_action',
] as const) {
  assert.ok(
    professionalComponentRegistrations.some((registration) => registration.componentKey === componentKey),
    `missing auth registration ${componentKey}`,
  );
}

assert.equal(professionalComponentRegistrations.length, 25);
const registeredRenderers: ReadonlySet<string> = new Set<string>(PROFESSIONAL_COMPONENT_RENDERERS);
const everyFieldType = [
  'char', 'text', 'html', 'integer', 'float', 'monetary', 'date', 'datetime', 'boolean',
  'selection', 'binary', 'many2one', 'one2many', 'many2many', 'action', 'reference',
];
let sweepCases = 0;
for (const entry of professionalComponentRegistrations) {
  assert.ok(
    registeredRenderers.has(entry.renderer),
    `registration ${entry.componentKey} declares an unregistered renderer ${entry.renderer}`,
  );
  sweepCases += 1;
  for (const [fieldType, fieldTypeRenderer] of Object.entries(entry.rendererByFieldType)) {
    assert.ok(
      registeredRenderers.has(fieldTypeRenderer),
      `registration ${entry.componentKey} maps ${fieldType} to an unregistered renderer ${fieldTypeRenderer}`,
    );
    sweepCases += 1;
  }
  if (entry.readiness === 'fail_closed') continue;
  const fieldTypes = entry.supportedFieldTypes.includes('*') ? everyFieldType : entry.supportedFieldTypes;
  for (const fieldType of fieldTypes) {
    const resolved: ProfessionalComponentRenderer = resolveProfessionalComponent({
      componentKey: entry.componentKey, fieldType, presentationMode: 'task', renderProfile: 'edit',
    }).renderer;
    assert.ok(
      registeredRenderers.has(resolved),
      `resolution produced an unregistered renderer ${entry.componentKey}:${fieldType}:${resolved}`,
    );
    sweepCases += 1;
  }
}
assert.equal(FORM_SECTION_TYPE_DIRECTED_RENDERER, 'FormSectionField');
assert.equal(
  resolveProfessionalComponent({
    componentKey: 'sc.display.text', fieldType: 'char', presentationMode: 'task', renderProfile: 'edit',
  }).renderer,
  FORM_SECTION_TYPE_DIRECTED_RENDERER,
  'the default display registration keeps routing to the type-directed control',
);
sweepCases += 2;
console.log(`[professional_component_registry_test] PASS cases>=${92 + sweepCases}`);
