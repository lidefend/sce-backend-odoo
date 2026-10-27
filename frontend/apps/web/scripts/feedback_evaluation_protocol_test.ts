/* eslint-disable @typescript-eslint/no-explicit-any */
import assert from 'node:assert/strict';
import { effectScope, ref } from 'vue';
import {
  FEEDBACK_EVALUATION_VERSION,
  decodeFeedbackDescribeResult,
  decodeFeedbackEvaluationData,
  decodeFeedbackEvaluateResult,
} from '../src/app/contracts/onchangeFeedbackEvaluation';
import { projectNodeComponents } from '../src/app/presentation/nodeComponentPresentation';
import { useDraftFeedbackEvaluation } from '../src/pages/contractForm/useDraftFeedbackEvaluation';

const binding = {
  etag: 'a'.repeat(64),
  model: 'demo.feedback',
  view_id: 7,
  container_id: 'feedback',
  source_container_id: 'source',
  native_locator: '/form[1]/note[1]',
  occurrence_index: 1,
  component_key: 'sc.feedback.message',
  component_version: '1.0.0',
  purpose: 'advisory',
  dependencies: [
    { field: 'business_date', type: 'date' },
    { field: 'note', type: 'text' },
  ],
  visibility_owner: 'feedback_evaluation',
} as const;
const relationBinding = {
  ...binding,
  model: 'sc.company.project.refund.workspace',
  view_id: 1942,
  container_id: 'refund-feedback',
  source_container_id: 'refund-source',
  native_locator: '/form[1]/sheet[1]/div[1]/field[1]',
  dependencies: [
    { field: 'partner_id', type: 'many2one_presence' },
    { field: 'business_date', type: 'date' },
    { field: 'note', type: 'text' },
  ],
} as const;

function snapshot() {
  const source = {
    containerId: 'source',
    type: 'field',
    name: 'note',
    nativeLocator: '/form[1]/note[1]',
    occurrenceIndex: 1,
    sourceAuthority: { kind: 'native_view', model: 'demo.feedback', view_id: 7 },
    fieldInfo: { type: 'text' },
  };
  const host = {
    containerId: 'feedback',
    type: 'div',
    visible: false,
    componentKey: 'sc.feedback.message',
    componentConfig: {
      purpose: 'advisory',
      contentRef: { containerId: 'source' },
      evaluation: { capability: 'form.feedback.draft.v1', visibilityOwner: 'feedback_evaluation' },
    },
    modifiers: { invisible: { kind: 'not', expr: { kind: 'field_truthy', field: 'note' } } },
    children: [source],
  };
  return {
    layoutContract: {
      containerTree: [{
        containerId: 'root',
        type: 'group',
        visible: true,
        children: [host],
      }],
      componentRegistry: { 'sc.feedback.message': { version: '1.0.0' } },
    },
    statusContract: { containerStatus: [{ containerId: 'feedback', visible: false }] },
    dataContract: { mainData: {} },
  };
}

function checkDecoder() {
  const described = decodeFeedbackDescribeResult({
    version: FEEDBACK_EVALUATION_VERSION,
    request_id: 'describe_1',
    status: 'described',
    binding,
  }, 'describe_1');
  assert.equal(described.binding.etag, binding.etag);
  assert.deepEqual(described.binding.dependencies, binding.dependencies);
  assert.throws(() => decodeFeedbackDescribeResult({
    version: FEEDBACK_EVALUATION_VERSION,
    request_id: 'wrong',
    status: 'described',
    binding,
  }, 'describe_1'), /request_id/);
  assert.throws(() => decodeFeedbackDescribeResult({
    version: FEEDBACK_EVALUATION_VERSION,
    request_id: 'describe_1',
    status: 'described',
    binding: { ...binding, extra: true },
  }, 'describe_1'), /binding/);
  const evaluated = decodeFeedbackEvaluateResult({
    version: FEEDBACK_EVALUATION_VERSION,
    request_id: 'evaluate_1',
    status: 'ready',
    binding_etag: binding.etag,
    container_id: 'feedback',
    result: { content: '建议补充办理说明', visible: true },
  }, { requestId: 'evaluate_1', bindingEtag: binding.etag, containerId: 'feedback' });
  assert.deepEqual(evaluated.result, { content: '建议补充办理说明', visible: true });
  assert.throws(() => decodeFeedbackEvaluationData({
    patch: { note: 'must not mix' },
    feedback_evaluation: {
      version: FEEDBACK_EVALUATION_VERSION,
      request_id: 'evaluate_1',
      status: 'ready',
      binding_etag: binding.etag,
      container_id: 'feedback',
      result: { content: 'must not mix', visible: true },
    },
  }, 'evaluate', {
    requestId: 'evaluate_1',
    bindingEtag: binding.etag,
    containerId: 'feedback',
  }), /data\.patch/);
  assert.throws(() => decodeFeedbackEvaluateResult({
    version: FEEDBACK_EVALUATION_VERSION,
    request_id: 'evaluate_1',
    status: 'ready',
    binding_etag: binding.etag,
    container_id: 'feedback',
    result: { content: 'must clear', visible: false },
  }, { requestId: 'evaluate_1', bindingEtag: binding.etag, containerId: 'feedback' }), /result/);
  const relation = decodeFeedbackDescribeResult({
    version: FEEDBACK_EVALUATION_VERSION,
    request_id: 'describe_relation',
    status: 'described',
    binding: relationBinding,
  }, 'describe_relation');
  assert.deepEqual(relation.binding.dependencies[0], {
    field: 'partner_id',
    type: 'many2one_presence',
  });
}

function checkAtomicPresentation() {
  const fixture = snapshot();
  const ready = projectNodeComponents(fixture, new Map([['feedback', {
    status: 'ready' as const,
    content: '建议补充办理说明',
    visible: true,
    binding: { container_id: 'feedback' },
  }]])).presentations.get('feedback');
  assert.equal(ready?.content, '建议补充办理说明');
  assert.equal(ready?.visible, true);
  assert.equal(ready?.visibilityOwner, 'feedback_evaluation');
  assert.equal(ready?.parentVisible, true);
  const hidden = projectNodeComponents(fixture, new Map([['feedback', {
    status: 'unavailable' as const,
    content: '',
    visible: false,
  }]])).presentations.get('feedback');
  assert.equal(hidden?.content, '');
  assert.equal(hidden?.visible, false);
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

async function checkStaleEvaluationIsDropped() {
  const fixture = snapshot();
  const store = ref({
    snapshot: {
      ...fixture,
      meta: { lifecycle: { integrity: { contractSha256: 'contract' } } },
    },
  }) as any;
  const presence = ref(new Set<string>());
  const deferred: Array<{
    request: any;
    resolve: (value: any) => void;
  }> = [];
  const transport = (params: any) => {
    const request = params.feedback_evaluation;
    if (request.operation === 'describe') {
      return Promise.resolve({
        feedback_evaluation: {
          version: FEEDBACK_EVALUATION_VERSION,
          request_id: request.request_id,
          status: 'described',
          binding,
        },
      });
    }
    return new Promise((resolve) => deferred.push({ request, resolve }));
  };
  const scope = effectScope();
  const runtime = scope.run(() => useDraftFeedbackEvaluation({
    store,
    model: () => 'demo.feedback',
    recordId: () => null,
    formData: { business_date: false, note: '' },
    presence,
    contextIdentity: () => 'user|company',
    context: () => ({}),
    active: () => true,
    transport: transport as any,
  }))!;
  await sleep(0);
  presence.value = new Set(['business_date', 'note']);
  await sleep(330);
  assert.equal(deferred.length, 1);
  runtime.onDraftChanged('note');
  await sleep(330);
  assert.equal(deferred.length, 2);
  deferred[1].resolve({
    feedback_evaluation: {
      version: FEEDBACK_EVALUATION_VERSION,
      request_id: deferred[1].request.request_id,
      status: 'ready',
      binding_etag: binding.etag,
      container_id: 'feedback',
      result: { content: 'new', visible: true },
    },
  });
  await sleep(0);
  assert.equal(runtime.states.value.get('feedback')?.content, 'new');
  deferred[0].resolve({
    feedback_evaluation: {
      version: FEEDBACK_EVALUATION_VERSION,
      request_id: deferred[0].request.request_id,
      status: 'ready',
      binding_etag: binding.etag,
      container_id: 'feedback',
      result: { content: 'stale', visible: true },
    },
  });
  await sleep(0);
  assert.equal(runtime.states.value.get('feedback')?.content, 'new');
  scope.stop();
}

function relationSnapshot() {
  const source = {
    containerId: 'refund-source',
    type: 'field',
    name: 'processing_advisory',
    nativeLocator: '/form[1]/sheet[1]/div[1]/field[1]',
    occurrenceIndex: 1,
    sourceAuthority: {
      kind: 'native_view',
      model: 'sc.company.project.refund.workspace',
      view_id: 1942,
    },
    fieldInfo: { type: 'char' },
  };
  const host = {
    containerId: 'refund-feedback',
    type: 'div',
    visible: false,
    componentKey: 'sc.feedback.message',
    componentConfig: {
      purpose: 'advisory',
      contentRef: { containerId: 'refund-source' },
      evaluation: {
        capability: 'form.feedback.draft.v1',
        visibilityOwner: 'feedback_evaluation',
      },
    },
    modifiers: {
      invisible: { kind: 'not', expr: { kind: 'field_truthy', field: 'processing_advisory' } },
    },
    children: [source],
  };
  return {
    layoutContract: {
      containerTree: [{
        containerId: 'root',
        type: 'group',
        visible: true,
        children: [host],
      }],
      componentRegistry: { 'sc.feedback.message': { version: '1.0.0' } },
    },
    statusContract: { containerStatus: [{ containerId: 'refund-feedback', visible: false }] },
    dataContract: { mainData: {} },
  };
}

async function checkRelationPresenceDoesNotLeakIdentity(many = false) {
  const store = ref({
    snapshot: {
      ...relationSnapshot(),
      meta: { lifecycle: { integrity: { contractSha256: 'refund-contract' } } },
    },
  }) as any;
  const presence = ref(new Set(['partner_id', 'business_date', 'note']));
  const formData = {
    partner_id: (many ? [731, 732] : [731, 'Sensitive Partner']) as any,
    business_date: false,
    note: '',
  };
  const evaluations: any[] = [];
  const transport = (params: any) => {
    const request = params.feedback_evaluation;
    if (request.operation === 'describe') {
      return Promise.resolve({
        feedback_evaluation: {
          version: FEEDBACK_EVALUATION_VERSION,
          request_id: request.request_id,
          status: 'described',
          binding: {...relationBinding, dependencies: [
            {field: 'partner_id', type: many ? 'many2many_presence' : 'many2one_presence'},
            ...relationBinding.dependencies.slice(1),
          ]},
        },
      });
    }
    evaluations.push(structuredClone(request));
    const partnerPresent = request.inputs.find((row: any) => row.field === 'partner_id')?.value === true;
    const content = partnerPresent
      ? '建议补充办理日期；建议补充退款原因或办理说明'
      : '建议选择退款方/收款方，便于责任与资金台账归集；建议补充办理日期；建议补充退款原因或办理说明';
    return Promise.resolve({
      feedback_evaluation: {
        version: FEEDBACK_EVALUATION_VERSION,
        request_id: request.request_id,
        status: 'ready',
        binding_etag: request.binding_etag,
        container_id: request.container_id,
        result: { content, visible: true },
      },
    });
  };
  const scope = effectScope();
  const runtime = scope.run(() => useDraftFeedbackEvaluation({
    store,
    model: () => 'sc.company.project.refund.workspace',
    recordId: () => null,
    formData,
    presence,
    contextIdentity: () => 'finance-user|company',
    context: () => ({}),
    active: () => true,
    transport: transport as any,
  }))!;
  await sleep(330);
  assert.equal(evaluations.length, 1);
  const selected = evaluations[0].inputs.find((row: any) => row.field === 'partner_id');
  assert.deepEqual(selected, { field: 'partner_id', present: true, value: true });
  assert.doesNotMatch(JSON.stringify(evaluations[0]), /731|Sensitive Partner/);
  formData.partner_id = false;
  runtime.onDraftChanged('partner_id');
  await sleep(330);
  assert.equal(evaluations.length, 2);
  const cleared = evaluations[1].inputs.find((row: any) => row.field === 'partner_id');
  assert.deepEqual(cleared, { field: 'partner_id', present: true, value: false });
  if (many) {
    formData.partner_id = [[6, 0, []]];
    runtime.onDraftChanged('partner_id');
    await sleep(330);
    assert.equal(evaluations.length, 3, 'empty SET must trigger a new evaluation');
    assert.equal(evaluations.at(-1).inputs[0].value, false);
    formData.partner_id = [[6, 0, [731, 732]]];
    runtime.onDraftChanged('partner_id');
    await sleep(330);
    assert.equal(evaluations.length, 4, 'nonempty SET must trigger a new evaluation');
    assert.equal(evaluations.at(-1).inputs[0].value, true);
    assert.doesNotMatch(JSON.stringify(evaluations.at(-1)), /731|732/);
    const validCount = evaluations.length;
    formData.partner_id = [[4, 731, 0]];
    runtime.onDraftChanged('partner_id');
    await sleep(330);
    assert.equal(evaluations.length, validCount, 'partial commands must not be treated as presence');
    assert.equal(runtime.states.value.get('refund-feedback')?.status, 'unavailable');
  }
  scope.stop();
}


async function checkConditionalInputProjection() {
  const typedBinding = {...binding, dependencies: [
    {field: 'amount', type: 'number_nonzero'}, {field: 'kind', type: 'selection'},
  ]};
  const store = ref({snapshot: {
    ...snapshot(), meta: {lifecycle: {integrity: {contractSha256: 'conditional'}}},
  }}) as any;
  const formData = {amount: 54321.75 as any, kind: 'salary_registration' as any};
  const presence = ref(new Set(['amount', 'kind']));
  const evaluations: any[] = [];
  const scope = effectScope();
  const runtime = scope.run(() => useDraftFeedbackEvaluation({
    store, model: () => 'demo.feedback', recordId: () => null, formData, presence,
    contextIdentity: () => 'user|company', context: () => ({}), active: () => true,
    transport: (async (params: any) => {
      const request = params.feedback_evaluation;
      if (request.operation === 'describe') return {feedback_evaluation: {
        version: FEEDBACK_EVALUATION_VERSION, request_id: request.request_id,
        status: 'described', binding: typedBinding,
      }};
      evaluations.push(structuredClone(request));
      return {feedback_evaluation: {
        version: FEEDBACK_EVALUATION_VERSION, request_id: request.request_id,
        status: 'ready', binding_etag: request.binding_etag,
        container_id: request.container_id, result: {content: '', visible: false},
      }};
    }) as any,
  }))!;
  try {
    await sleep(330);
    assert.equal(evaluations.length, 1);
    assert.deepEqual(evaluations[0].inputs, [
      {field: 'amount', present: true, value: true},
      {field: 'kind', present: true, value: 'salary_registration'},
    ]);
    assert.doesNotMatch(JSON.stringify(evaluations[0]), /54321/);
    for (const [raw, expected] of [[0, false], [-17.25, true], [null, false], ['', false]]) {
      const before = evaluations.length;
      formData.amount = raw;
      runtime.onDraftChanged('amount');
      await sleep(330);
      assert.equal(evaluations.length, before + 1);
      assert.equal(evaluations.at(-1).inputs[0].value, expected);
    }
    for (const invalid of [NaN, Infinity, '1000', true, undefined]) {
      const before = evaluations.length;
      formData.amount = invalid;
      runtime.onDraftChanged('amount');
      await sleep(330);
      assert.equal(evaluations.length, before);
      assert.equal(runtime.states.value.get('feedback')?.status, 'unavailable');
    }
    formData.amount = 0;
    for (const [raw, expected] of [['provident_fund_registration', 'provident_fund_registration'],
                                  [false, false], [null, false], ['', false]]) {
      const before = evaluations.length;
      formData.kind = raw;
      runtime.onDraftChanged('kind');
      await sleep(330);
      assert.equal(evaluations.length, before + 1);
      assert.equal(evaluations.at(-1).inputs[1].value, expected);
    }
    for (const invalid of [true, 1, {}, undefined]) {
      const before = evaluations.length;
      formData.kind = invalid;
      runtime.onDraftChanged('kind');
      await sleep(330);
      assert.equal(evaluations.length, before);
      assert.equal(runtime.states.value.get('feedback')?.status, 'unavailable');
    }
  } finally {
    scope.stop();
  }
}

checkDecoder();
checkAtomicPresentation();
await checkStaleEvaluationIsDropped();
await checkRelationPresenceDoesNotLeakIdentity();
await checkRelationPresenceDoesNotLeakIdentity(true);
await checkConditionalInputProjection();
console.log('feedback_evaluation_protocol_test: PASS');
