import assert from 'node:assert/strict';
import { useRecordRelationshipNavigation } from '../src/pages/contractForm/useRecordRelationshipNavigation';
import { relationEntry } from '../src/pages/contractForm/relationDescriptor';

// Relation column descriptors may only be fetched for a relation the backend
// projection explicitly declares readable. A declared-unreadable relation
// (RELATION_READ_FORBIDDEN) must fail closed before I/O: asking the backend for
// its model contract is an unauthorized request and answers 403, which the
// runtime-clean acceptance gate correctly rejects.

type Case = {
  label: string;
  relationEntryShape?: Record<string, unknown>;
  expectFetches: number;
};

const descriptorStore = {
  widgetsByFieldCode: new Map([
    ['line_note', { fieldDescriptor: { name: 'line_note', string: '备注', type: 'char' } }],
  ]),
};

const cases: Case[] = [
  {
    label: 'declared readable',
    relationEntryShape: { model: 'payment.request.line', can_read: true, can_open: true },
    expectFetches: 1,
  },
  {
    label: 'declared unreadable',
    relationEntryShape: { model: 'payment.request.line', can_read: false, can_open: true, reason_code: 'RELATION_READ_FORBIDDEN' },
    expectFetches: 0,
  },
  { label: 'relation entry absent', relationEntryShape: undefined, expectFetches: 0 },
];

let checked = 0;
for (const testCase of cases) {
  const descriptors: Record<string, unknown> = {
    payment_request_line_ids: {
      name: 'payment_request_line_ids',
      type: 'one2many',
      relation: 'payment.request.line',
      ...(testCase.relationEntryShape ? { relation_entry: testCase.relationEntryShape } : {}),
    },
  };
  const relationFieldDescriptors = { value: {} as Record<string, unknown> };
  const fetches: Array<{ model: string; options: unknown }> = [];
  const navigation = useRecordRelationshipNavigation({
    one2manyRelationModel: (name: string) => String(descriptors[name]?.relation || ''),
    relationFieldDescriptors,
    effectiveFieldDescriptor: (name: string) => descriptors[name],
    relationEntry,
    loadModelContractV2: async (model: string, options: unknown) => {
      fetches.push({ model, options });
      return { store: descriptorStore };
    },
  });

  await navigation.ensureRelationFieldDescriptors('payment_request_line_ids');

  assert.equal(
    fetches.length,
    testCase.expectFetches,
    `${testCase.label}: expected ${testCase.expectFetches} contract fetch(es), got ${JSON.stringify(fetches)}`,
  );
  if (testCase.expectFetches === 0) {
    assert.deepEqual(fetches, [], `${testCase.label}: an unreadable relation must not trigger any relation contract request`);
    assert.deepEqual(
      Object.keys(relationFieldDescriptors.value),
      [],
      `${testCase.label}: descriptors must stay empty instead of being guessed`,
    );
  } else {
    assert.equal(fetches[0].model, 'payment.request.line');
    assert.deepEqual(fetches[0].options, { viewType: 'form', renderProfile: 'edit' });
    assert.deepEqual(
      Object.keys(relationFieldDescriptors.value),
      ['payment.request.line'],
      'declared readable: the fetched relation columns must be recorded',
    );
  }
  checked += 1;
}

// Regression case: the exact acceptance defect (settlement detail opened by
// fixture_role_pm) declared payment.request / payment.request.line unreadable
// on the readonly one2many panel, yet both contracts were still requested and
// both answered 403 at every matrix viewport.
const settlementFields: Record<string, Record<string, unknown>> = {
  payment_request_ids: {
    name: 'payment_request_ids', type: 'one2many', relation: 'payment.request',
    relation_entry: { model: 'payment.request', can_read: false, reason_code: 'RELATION_READ_FORBIDDEN' },
  },
  payment_request_line_ids: {
    name: 'payment_request_line_ids', type: 'one2many', relation: 'payment.request.line',
    relation_entry: { model: 'payment.request.line', can_read: false, reason_code: 'RELATION_READ_FORBIDDEN' },
  },
};
const settlementDescriptors = { value: {} as Record<string, unknown> };
const settlementFetches: string[] = [];
const settlementNavigation = useRecordRelationshipNavigation({
  one2manyRelationModel: (name: string) => String(settlementFields[name]?.relation || ''),
  relationFieldDescriptors: settlementDescriptors,
  effectiveFieldDescriptor: (name: string) => settlementFields[name],
  relationEntry,
  loadModelContractV2: async (model: string) => {
    settlementFetches.push(model);
    return { store: descriptorStore };
  },
});
for (const fieldName of Object.keys(settlementFields)) {
  await settlementNavigation.ensureRelationFieldDescriptors(fieldName);
}
assert.deepEqual(
  settlementFetches,
  [],
  'PM settlement panel declared both payment relations unreadable and must issue no relation contract request',
);

console.log(`[relation_column_descriptor_authority_test] PASS cases=${checked} regression_fetches=0`);
