import { strict as assert } from 'node:assert';
import {
  professionalComponentRegistrations,
  resolveContractProfessionalComponent,
  resolveProfessionalComponent,
  resolveProfessionalComponentRegistration,
  type ProfessionalComponentRegistration,
} from '../src/app/presentation/professionalComponentRegistry';
import {
  detailAmountBindingConfig,
  optionalDetailCollectionConfig,
  optionalDetailCollectionPresentation,
  optionalDetailCollectionRemovalConfirmation,
} from '../src/components/professional-fields/professionalDetailCollectionModel';

const ready = resolveProfessionalComponent({
  componentKey: 'sc.input.text', fieldType: 'char', presentationMode: 'task', renderProfile: 'edit',
});
assert.equal(ready.readiness, 'ready');
assert.equal(ready.renderer, 'ProfessionalBaseFieldControl');
const contractBound = resolveContractProfessionalComponent({
  componentKey: 'sc.input.text', fieldType: 'char', presentationMode: 'task', renderProfile: 'edit',
  clientType: 'web_pc',
  contractRegistryEntry: { version: '1.0', adapter: { web_pc: 'ElInput' }, selectedAdapter: 'TDesignInput' },
});
assert.equal(contractBound.contractAdapter, 'TDesignInput');
assert.equal(contractBound.contractVersion, '1.0');
assert.throws(() => resolveContractProfessionalComponent({
  componentKey: 'sc.input.text', fieldType: 'char', presentationMode: 'task', renderProfile: 'edit',
  clientType: 'web_pc', contractRegistryEntry: {},
}), /PROFESSIONAL_COMPONENT_CONTRACT_REGISTRY_MISSING/);
assert.throws(() => resolveContractProfessionalComponent({
  componentKey: 'sc.input.text', fieldType: 'char', presentationMode: 'task', renderProfile: 'edit',
  clientType: 'web_pc', contractRegistryEntry: { version: '1.0', adapter: {} },
}), /PROFESSIONAL_COMPONENT_CONTRACT_ADAPTER_MISSING/);
assert.equal(resolveProfessionalComponent({
  componentKey: 'sc.relation.many2one', fieldType: 'many2one', presentationMode: 'task', renderProfile: 'edit',
}).renderer, 'ProfessionalRelationFieldControl');
assert.equal(resolveProfessionalComponent({
  componentKey: 'sc.relation.many2many', fieldType: 'many2many', presentationMode: 'workspace', renderProfile: 'readonly',
}).renderer, 'ProfessionalRelationFieldControl');
assert.equal(resolveProfessionalComponent({
  componentKey: 'sc.relation.table', fieldType: 'one2many', presentationMode: 'workspace', renderProfile: 'edit',
}).renderer, 'ProfessionalDetailCollectionControl');
assert.equal(resolveProfessionalComponent({
  componentKey: 'sc.payment.settlement_detail_collection', fieldType: 'one2many', presentationMode: 'task', renderProfile: 'edit',
}).renderer, 'PaymentSettlementDetailCollectionControl');
const optionalDetails = optionalDetailCollectionConfig({
  key: 'line_ids', name: 'line_ids', label: 'Lines', type: 'one2many', required: false, readonly: false,
  componentConfig: {
    optionalDetails: {
      entryLabel: 'Use details',
      populatedLabel: 'Details',
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
      activeField: 'active', rounding: 'currency', emptyBehavior: 'preserve_last_total',
    },
  },
});
assert.deepEqual(amountBinding, {
  mode: 'sum_when_nonempty', sourceField: 'line_amount', targetField: 'amount',
  activeField: 'active', rounding: 'currency', emptyBehavior: 'preserve_last_total',
});
assert.equal(detailAmountBindingConfig({
  key: 'line_ids', name: 'line_ids', label: 'Lines', type: 'one2many', required: false, readonly: false,
  componentConfig: {
    amountBinding: {
      mode: 'sum_when_nonempty', sourceField: 'amount', targetField: 'amount',
      activeField: 'active', rounding: 'currency', emptyBehavior: 'preserve_last_total',
    },
  },
}), null);
assert.equal(detailAmountBindingConfig({
  key: 'line_ids', name: 'line_ids', label: 'Lines', type: 'one2many', required: false, readonly: false,
  componentConfig: {
    amountBinding: {
      mode: 'sum_always', sourceField: 'line_amount', targetField: 'amount',
      activeField: 'active', rounding: 'currency', emptyBehavior: 'zero',
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
      entryLabel: 'Use details', populatedLabel: 'Details', linkedAmountMessage: 'Linked total',
      lastRowRemovalActionLabel: 'Stop using details', lastRowRemovalMessage: 'Last total is preserved',
    },
  },
} as never;
assert.deepEqual(optionalDetailCollectionPresentation(optionalField, 0), {
  render: true, open: false, title: 'Use details', linkedAmountMessage: '',
});
assert.deepEqual(optionalDetailCollectionPresentation(optionalField, 2), {
  render: true, open: true, title: 'Details（2 条）', linkedAmountMessage: 'Linked total',
});
assert.equal(optionalDetailCollectionPresentation({ ...optionalField, readonly: true } as never, 0)?.render, false);
assert.equal(optionalDetailCollectionRemovalConfirmation(optionalField, 2), null);
assert.deepEqual(optionalDetailCollectionRemovalConfirmation(optionalField, 1), {
  actionLabel: 'Stop using details', message: 'Last total is preserved',
});
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
}), /PROFESSIONAL_COMPONENT_CAPABILITY_MISSING/);
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

assert.equal(professionalComponentRegistrations.length, 26);
console.log('[professional_component_registry_test] PASS cases=43');
