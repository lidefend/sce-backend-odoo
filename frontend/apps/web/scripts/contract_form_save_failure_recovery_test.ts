import assert from 'node:assert/strict';
import { ref, type Ref } from 'vue';

import { ApiError } from '../src/api/client';
import { buildSaveRecordPayload, validateBeforeSaveRecord } from '../src/pages/contractForm/saveRecordHelpers';
import { snapshotOriginalFormValues } from '../src/pages/contractForm/recordHydration';
import { sanitizeUiErrorMessage } from '../src/pages/contractForm/fieldUtils';
import { createStandardFormValidationRegistry } from '../src/pages/contractForm/standardFormCompositionRuntime';
import { useRecordFormActions } from '../src/pages/contractForm/useRecordFormActions';
import type { BusinessFieldError } from '../src/app/businessValidationError';

// WEB-FIX-02 / frontend failure recovery. This drives the real saveRecord
// composable (not a copy of it) through the real payload builder, so the
// assertions describe shipped behaviour: a business rejection must keep the
// draft, must not report success, must not refresh the draft away, and must
// stay retryable without duplicating the write.

type WriteCall = { model: string; ids: number[]; vals: Record<string, unknown> };
type CreateCall = { model: string; vals: Record<string, unknown> };
type Feedback = { kind: string; message: string };

type Harness = {
  actions: ReturnType<typeof useRecordFormActions>;
  refs: {
    dirtyFieldSet: Set<string>;
    submissionFeedback: Ref<Feedback | null>;
    busyKind: Ref<string | null>;
    originalValues: Ref<Record<string, unknown>>;
    validationErrors: Ref<string[]>;
  };
  calls: { writes: WriteCall[]; creates: CreateCall[]; reloads: number; created: number[]; redirects: unknown[] };
  failWrite: (error: unknown) => void;
  succeedWrite: () => void;
  failCreate: (error: unknown) => void;
  succeedCreate: (id?: number) => void;
};

function buildHarness(options: {
  recordId: number | null;
  formData: Record<string, unknown>;
  originalValues: Record<string, unknown>;
  dirty: string[];
  uploadFails?: boolean;
}): Harness {
  const calls: Harness['calls'] = { writes: [], creates: [], reloads: 0, created: [], redirects: [] };

  let writeBehavior: () => Promise<unknown> = async () => ({});
  let createBehavior: () => Promise<{ id: number }> = async () => ({ id: 900 });

  const dirtyFieldSet = new Set<string>(options.dirty);
  const submissionFeedback = ref<Feedback | null>(null);
  const busyKind = ref<string | null>(null);
  const originalValues = ref<Record<string, unknown>>({ ...options.originalValues });
  const validationErrors = ref<string[]>([]);
  const router = { replace: async (target: unknown) => { calls.redirects.push(target); } };

  const dependencies: Record<string, unknown> = {
    ApiError,
    buildFormRequestContext: () => ({}),
    buildSaveRecordPayload,
    busy: ref(false),
    busyKind,
    canSave: ref(true),
    clearIntakeAutosave: () => undefined,
    collectSceneValidationPrecheckErrors: () => [] as string[],
    // Mirrors the real runtime: a relation draft is handed to the write payload
    // as an Odoo command list, not as a bare id array.
    collectWritableValues: () => ({
      title: options.formData.title,
      links: [[6, 0, [...((options.formData.links as number[]) ?? [])]]],
    }),
    contract: ref({}),
    comparableFieldValue: (_name: string, value: unknown) => JSON.stringify(value ?? null),
    createContractFormRecord: async (params: CreateCall) => {
      calls.creates.push(params);
      const created = await createBehavior();
      calls.created.push(created.id);
      return created;
    },
    dirtyFieldSet,
    executeProjectionRefresh: async (params: { refreshScene: () => Promise<void> }) => {
      await params.refreshScene();
    },
    focusFirstValidationError: async () => undefined,
    formConflict: ref(false),
    formCreateContextFromState: () => ({}),
    // The shipped composable keys every save operation to the bound surface, so
    // the harness must publish the same surface identity inputs the page does:
    // component activity, route identity, route owner identity and session scope.
    isComponentActive: ref(true),
    formRouteIdentity: () => 'x.document|action|1|||',
    formRouteOwnerIdentity: () => 'action|1',
    formData: options.formData,
    formUiLabel: (key: string) => key,
    formFields: ref({ title: { type: 'char' }, links: { type: 'many2many' } }),
    isWritableFieldVisible: () => true,
    layoutNodes: ref([]),
    model: ref('x.document'),
    navigateCreatedRecord: async (target: unknown) => { calls.redirects.push(target); return true; },
    normalizeFieldValue: (_name: string, value: unknown) => value,
    onErrorCaptured: () => undefined,
    one2manyValidation: ref({ cellErrors: {}, issues: [] }),
    originalValues,
    recordId: ref(options.recordId),
    route: { fullPath: '/action/1', path: '/action/1', query: {} },
    recordVersionPolicy: () => false,
    recordVersionToken: ref(''),
    reload: async () => { calls.reloads += 1; },
    resolvePendingInlineRelationCreates: async () => [] as string[],
    resolvePendingMany2manyTagCreates: async () => [] as string[],
    router,
    sanitizeUiErrorMessage,
    sceneReadyFormSurface: ref({ nextSceneKey: '', nextSceneRoute: '' }),
    session: { loadAppInit: async () => undefined, logout: async () => undefined, token: 'harness-token', user: { id: 1 }, recordContext: {} },
    showOne2manyErrors: ref(false),
    snapshotOriginalFormValues,
    status: ref('ok'),
    submissionFeedback,
    uploadPendingNativeAttachments: async () => !options.uploadFails,
    v2ContractStore: ref({ snapshot: { pageInfo: { pageName: '付款申请' } } }),
    useFormPageLifecycleRuntime: () => undefined,
    // This harness has no required fields; use the real adopted empty registry.
    validateAdoptedFormSections: createStandardFormValidationRegistry(() => ({ pageType: 'record-form', reason: 'contract-record-view' } as const)).validateAdoptedFields,
    validateBeforeSaveRecord,
    validationErrors,
    validationFieldErrors: ref<Record<string, BusinessFieldError>>({}),
    writeContractFormRecord: async (params: WriteCall) => {
      calls.writes.push(params);
      return writeBehavior();
    },
  };

  const actions = useRecordFormActions(dependencies as never);

  return {
    actions,
    refs: { dirtyFieldSet, submissionFeedback, busyKind, originalValues, validationErrors },
    calls,
    failWrite: (error: unknown) => { writeBehavior = async () => { throw error; }; },
    succeedWrite: () => { writeBehavior = async () => ({}); },
    failCreate: (error: unknown) => { createBehavior = async () => { throw error; }; },
    succeedCreate: (id = 900) => { createBehavior = async () => ({ id }); },
  };
}

const businessRejection = () => new ApiError('金额必须大于零', 422, 'trace-wf02', {
  reasonCode: 'USER_ERROR',
  errorCategory: 'validation',
  suggestedAction: 'fix_input',
  retryable: false,
});

// ---------------------------------------------------------------------------
// edit: business rejection keeps the draft, then a corrected retry succeeds
// ---------------------------------------------------------------------------
{
  const formData = { title: '修订标题', links: [9] };
  const harness = buildHarness({
    recordId: 501,
    formData,
    originalValues: { title: '原标题', links: [7] },
    dirty: ['title', 'links'],
  });
  const { actions, calls, refs } = harness;

  harness.failWrite(businessRejection());
  const rejected = await actions.saveRecord();
  assert.equal(rejected, false, 'a business rejection must not report a successful save');
  assert.deepEqual(Array.from(refs.dirtyFieldSet), ['title', 'links'], 'the field/relation draft must stay dirty');
  assert.deepEqual(formData, { title: '修订标题', links: [9] }, 'the typed draft must survive a rejection');
  assert.equal(calls.reloads, 0, 'a rejected save must not refresh the draft away');
  assert.equal(calls.writes.length, 1);
  assert.equal(refs.submissionFeedback.value?.kind, 'error', 'a rejection is reported as an error, never as success');
  assert.match(refs.submissionFeedback.value?.message ?? '', /金额必须大于零/, 'the user must see the business reason');
  assert.deepEqual(refs.validationErrors.value, ['金额必须大于零']);
  assert.equal(refs.busyKind.value, null, 'the save button must become operable again');

  harness.succeedWrite();
  const accepted = await actions.saveRecord();
  assert.equal(accepted, true, 'a corrected retry must succeed');
  assert.equal(calls.writes.length, 2, 'the retry writes exactly once');
  assert.deepEqual(calls.writes[1].vals, { title: '修订标题', links: [[6, 0, [9]]] }, 'the retry sends the corrected draft');
  assert.equal(refs.dirtyFieldSet.size, 0, 'a successful save clears the draft markers');
  assert.equal(refs.originalValues.value.title, '修订标题', 'a successful save re-baselines the draft');
  assert.equal(refs.submissionFeedback.value?.kind, 'success');
}

// ---------------------------------------------------------------------------
// duplicate clicks share one in-flight write (no duplicate submit)
// ---------------------------------------------------------------------------
{
  const harness = buildHarness({
    recordId: 501,
    formData: { title: '并发标题' },
    originalValues: { title: '原标题' },
    dirty: ['title'],
  });
  harness.failWrite(businessRejection());
  const first = harness.actions.saveRecord();
  const second = harness.actions.saveRecord();
  await Promise.all([first, second]);
  assert.equal(harness.calls.writes.length, 1, 'double-clicking save must not duplicate the write');
}

// ---------------------------------------------------------------------------
// create: rejection keeps the draft, retry creates exactly one record
// ---------------------------------------------------------------------------
{
  const formData = { title: '新建标题', links: [4] };
  const harness = buildHarness({ recordId: null, formData, originalValues: {}, dirty: ['title', 'links'] });
  const { actions, calls, refs } = harness;

  harness.failCreate(businessRejection());
  const rejected = await actions.saveRecord();
  assert.equal(rejected, false, 'a rejected create must not report success');
  assert.deepEqual(formData, { title: '新建标题', links: [4] }, 'the create draft must survive a rejection');
  assert.equal(calls.creates.length, 1, 'the rejected attempt really reached the create write');
  assert.equal(calls.created.length, 0, 'a rejected create leaves no record behind');
  assert.equal(calls.reloads, 0);
  assert.equal(refs.dirtyFieldSet.has('title'), true, 'the create draft stays dirty');
  assert.equal(refs.submissionFeedback.value?.kind, 'error');

  harness.succeedCreate(900);
  const accepted = await actions.saveRecord();
  assert.equal(accepted, true, 'a corrected create must succeed');
  assert.equal(calls.creates.length, 2, 'the retry creates exactly once');
  assert.deepEqual(calls.created, [900], 'no duplicate record is created');
}

// ---------------------------------------------------------------------------
// permission denial stays a distinct, non-silent outcome
// ---------------------------------------------------------------------------
{
  const formData = { title: '越权标题' };
  const harness = buildHarness({ recordId: 501, formData, originalValues: { title: '原标题' }, dirty: ['title'] });

  harness.failWrite(new ApiError('无写入权限', 403, 'trace-wf02', { reasonCode: 'PERMISSION_DENIED' }));
  const rejected = await harness.actions.saveRecord();

  assert.equal(rejected, false);
  assert.deepEqual(harness.calls.redirects, [{ name: 'access-denied' }], 'a permission denial routes to access-denied');
  assert.deepEqual(formData, { title: '越权标题' }, 'the draft is not discarded by the redirect');
  assert.equal(harness.refs.submissionFeedback.value, null, 'a permission denial is never reported as a successful save');
}

console.log('[contract-form-save-failure-recovery] PASS: edit-retry, single-flight, create-retry, permission-denial');

{
  const harness = buildHarness({ recordId: null, formData: { title: 'Created before upload failure' }, originalValues: {}, dirty: ['title'], uploadFails: true });
  const outcome = await harness.actions.saveRecord(undefined, { navigateAfterCreate: false });
  assert.equal(outcome, false, 'upload failure must not proceed to submission');
  assert.deepEqual(harness.calls.created, [900]);
  assert.equal(harness.calls.creates.length, 1);
  assert.deepEqual(harness.calls.redirects, [{ createdId: 900, nextSceneKey: '', nextSceneRoute: '', refreshPolicy: undefined, recovery: 'upload' }]);
  assert.equal(harness.calls.reloads, 0, 'never reload the empty new route');
}
console.log('[contract-form-save-failure-recovery] post-create upload failure opens generated record PASS count=1');
