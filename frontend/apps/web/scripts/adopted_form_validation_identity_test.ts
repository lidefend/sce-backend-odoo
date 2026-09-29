/**
 * FE-TPL-02R counter-examples: does the shipped save chain bind the official
 * validation to the record/draft it was started for?
 *
 * The host is a real Vue app instance. It calls the shipped
 * `useRecordFormActions` with the shipped `useFormPageLifecycleRuntime`,
 * the shipped adopted-section registry and the shipped
 * `validateBeforeSaveRecord`. Only the network boundary is a counter
 * (`writeContractFormRecord`), exactly as the engine-decision test does.
 *
 * Timing is deterministic: the section validator returns a promise the test
 * resolves by hand, so the "still in flight" window is controlled, never slept.
 *
 * Covered layers: the page composable's save orchestration, the adopted-section
 * registry, and the record-identity watcher. Not covered: the real HTTP client
 * and the server ORM.
 */
import assert from 'node:assert/strict';
import { createRenderer, defineComponent, h, nextTick, onErrorCaptured, ref } from 'vue';

import { useRecordFormActions } from '../src/pages/contractForm/useRecordFormActions';
import { createStandardFormValidationRegistry } from '../src/pages/contractForm/standardFormCompositionRuntime';
import { validateBeforeSaveRecord } from '../src/pages/contractForm/saveRecordHelpers';
import { isFormPageRouteOwner, useFormPageLifecycleRuntime } from '../src/pages/contractForm/useFormPageLifecycleRuntime';

let cases = 0;
const fails: string[] = [];
const check = (actual: unknown, expected: unknown, label: string) => {
  cases += 1;
  try {
    assert.equal(actual, expected, label);
  } catch (error) {
    fails.push(label);
    console.log(`[FAIL] ${label}\n       actual=${JSON.stringify(actual)} expected=${JSON.stringify(expected)}`);
  }
};

// ---------------------------------------------------------------------------
// Host renderer (same minimal host the engine-decision test uses)
// ---------------------------------------------------------------------------
type HostNode = {
  children: HostNode[];
  parent: HostNode | null;
  props: Record<string, unknown>;
  text?: string;
  type?: string;
};
const hostNode = (type?: string): HostNode => ({ children: [], parent: null, props: {}, type });
const renderer = createRenderer<HostNode, HostNode>({
  patchProp(node, key, _previous, value) {
    if (value === null || value === undefined) delete node.props[key];
    else node.props[key] = value;
  },
  insert(child, parent, anchor) {
    child.parent = parent;
    const index = anchor ? parent.children.indexOf(anchor) : -1;
    if (index >= 0) parent.children.splice(index, 0, child);
    else parent.children.push(child);
  },
  remove(child) {
    if (!child.parent) return;
    const index = child.parent.children.indexOf(child);
    if (index >= 0) child.parent.children.splice(index, 1);
    child.parent = null;
  },
  createElement: (type) => hostNode(type),
  createText: (text) => ({ ...hostNode('text'), text }),
  createComment: (text) => ({ ...hostNode('comment'), text }),
  setText: (node, text) => { node.text = text; },
  setElementText: (node, text) => { node.text = text; },
  parentNode: (node) => node.parent,
  nextSibling(node) {
    if (!node.parent) return null;
    const index = node.parent.children.indexOf(node);
    return node.parent.children[index + 1] || null;
  },
  querySelector: () => null,
  setScopeId: () => {},
  cloneNode: (node) => ({ ...node, children: [...node.children], props: { ...node.props }, parent: null }),
  insertStaticContent: () => {
    const node = hostNode('static');
    return [node, node];
  },
});
const listeners: Record<string, unknown[]> = {};
(globalThis as unknown as Record<string, unknown>).document = {
  documentElement: { style: {}, setAttribute: () => {}, getAttribute: () => null },
  addEventListener: () => {},
  removeEventListener: () => {},
};
(globalThis as unknown as Record<string, unknown>).window = {
  location: { href: 'http://localhost/', origin: 'http://localhost' },
  addEventListener: (type: string, handler: unknown) => { (listeners[type] ||= []).push(handler); },
  removeEventListener: () => {},
  setTimeout: (handler: () => void) => { handler(); return 0; },
};

// ---------------------------------------------------------------------------
// Deferred section validator: the test owns the completion moment
// ---------------------------------------------------------------------------
function deferred<T = string[]>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}

/** A completion moment with no value: used to hold a write or a reload open. */
function deferredVoid() {
  let resolve!: () => void;
  const promise = new Promise<void>((res) => { resolve = res; });
  return { promise, resolve };
}

// ---------------------------------------------------------------------------
// Harness: the shipped page save orchestration on a real Vue instance
// ---------------------------------------------------------------------------
type Write = { model: string; ids: number[]; vals: Record<string, unknown> };
const writes: Write[] = [];
const creates: Array<{ model: string; vals: Record<string, unknown> }> = [];
let validateCalls = 0;

/**
 * The network boundary, controllable. Each write consumes the next queued gate
 * (or runs immediately when none is queued), and `nextWriteError` makes exactly
 * one write reject the way a server refusal would. Everything above this line
 * is the shipped chain.
 */
const writeGates: Array<{ promise: Promise<void>; resolve: () => void }> = [];
let nextWriteError: unknown = null;
const writeBoundary = async (payload: { model: string; ids: number[]; vals: Record<string, unknown> }) => {
  writes.push({ model: String(payload.model), ids: [...(payload.ids || [])], vals: payload.vals });
  const gate = writeGates.shift();
  if (gate) await gate.promise;
  if (nextWriteError) {
    const error = nextWriteError;
    nextWriteError = null;
    throw error;
  }
};
const createBoundary = async (payload: { model: string; vals: Record<string, unknown> }) => {
  creates.push({ model: String(payload.model), vals: payload.vals });
  return { id: 999 };
};

class TestApiError extends Error {
  status: number;
  details: unknown;
  constructor(message: string, status = 0, details: unknown = null) {
    super(message);
    this.status = status;
    this.details = details;
  }
}

const model = ref('project.project');
const recordId = ref<number | null>(10);
const identity = ref('record:project.project:10');
const formData: Record<string, unknown> = { name: '' };
const originalValues = ref<Record<string, unknown>>({ name: 'A-original' });
const validationErrors = ref<string[]>([]);
const validationFieldErrors = ref<Record<string, unknown>>({});
const submissionFeedback = ref<unknown>(null);
const busyKind = ref<string | null>(null);
const status = ref('ok');
const retainedRouteIdentity = ref(identity.value);
const isComponentActive = ref(true);
const instanceRouteIdentity = ref(identity.value);
const layoutNodes = ref([{
  key: 'name', kind: 'field', name: 'name', label: '项目名称', readonly: false, required: true,
  descriptor: { name: 'name', string: '项目名称', required: true, readonly: false, ttype: 'char' },
}]);

let registry = createStandardFormValidationRegistry(() => ({ pageType: 'record-form', reason: 'contract-record-view' } as const));
let sectionGate = deferred();
registry.register({ sectionId: 'section-a', ruleFieldNames: () => ['name'], validate: () => { validateCalls += 1; return sectionGate.promise; } });

const deps: Record<string, unknown> = {
  ApiError: TestApiError,
  actionId: ref(673),
  activeContractMode: ref(''),
  activeContractModeFieldRows: ref([]),
  buildSaveRecordPayload: () => ({ name: formData.name }),
  busy: ref(false),
  busyKind,
  canSave: ref(true),
  clearIntakeAutosave: () => {},
  closeContractPromptAction: () => {},
  collectSceneValidationPrecheckErrors: () => [],
  collectWritableValues: () => ({ name: formData.name }),
  comparableFieldValue: (_name: string, value: unknown) => value,
  contract: ref(null),
  contractActionConfirmationPrompt: () => null,
  contractModeFeedback: ref(''),
  dirtyFieldSet: new Set<string>(['name']),
  ensureFormInitialReload: () => {},
  executeProjectionRefresh: async (config?: { refreshScene?: () => Promise<void> }) => { await config?.refreshScene?.(); },
  fieldVisibilityDirtyKeys: {},
  fieldVisibilityDraft: {},
  focusFirstValidationError: async () => {},
  formConflict: ref(false),
  formData,
  formFields: ref([]),
  formRouteIdentity: () => identity.value,
  formRouteOwnerIdentity: () => identity.value,
  formUiLabel: (key: string) => key,
  handleRecordContextChanged: () => {},
  hasChanges: ref(true),
  instanceRouteIdentity,
  intentConfirmationRef: ref(null),
  isComponentActive,
  isContractFieldOrderEditable: ref(false),
  isFormPageRouteOwner,
  isWritableFieldVisible: () => true,
  layoutNodes,
  model,
  navigateCreatedRecord: async () => true,
  normalizeFieldValue: (_name: string, value: unknown) => value,
  onErrorCaptured,
  onFieldOrderDragEnd: () => {},
  onFieldOrderWindowDragOver: () => {},
  onFieldOrderWindowDragStop: () => {},
  onRelationDialogDocumentKeydown: () => {},
  one2manyValidation: ref({ cellErrors: {}, issues: [] }),
  originalValues,
  recordContextChangedEvent: 'sc:record-context-changed',
  recordId,
  recordVersionPolicy: () => null,
  recordVersionToken: ref(''),
  reload: async () => {
    validationErrors.value = [];
    validationFieldErrors.value = {};
    retainedRouteIdentity.value = identity.value;
  },
  resolvePendingInlineRelationCreates: async () => [],
  resolvePendingMany2manyTagCreates: async () => [],
  sanitizeUiErrorMessage: (message: unknown, fallback: string) => String(message || fallback),
  retainedRouteIdentity,
  route: { query: {}, params: { model: 'project.project', id: '10' }, path: '/f/project.project/10', name: 'model-form', meta: {} },
  routeIsOwned: () => true,
  router: { push: async () => {}, replace: async () => {} },
  session: { featureFlags: {}, loadAppInit: async () => {}, logout: async () => {}, recordIntentTrace: () => {}, updateActiveActivityDirty: () => {} },
  showOne2manyErrors: ref(false),
  snapshotOriginalFormValues: () => ({ ...formData }),
  status,
  submissionFeedback,
  uploadPendingNativeAttachments: async () => true,
  useFormPageLifecycleRuntime,
  v2ContractStore: ref(null),
  // The surface this host stands in for: a page the effective contract declared
  // as a record form. The page type is page-scoped, so switching the bound
  // record never changes it — only the record identity does.
  contractPageType: () => ({ pageType: 'record-form', reason: 'contract-record-view' } as const),
  validateAdoptedFormSections: () => registry.validateAdoptedFields(),
  validateBeforeSaveRecord,
  validationErrors,
  validationFieldErrors,
  createContractFormRecord: createBoundary,
  writeContractFormRecord: writeBoundary,
};
const proxiedDeps = new Proxy(deps, { get: (target, key) => (key in target ? (target as Record<string, unknown>)[key as string] : undefined) });

let actions: ReturnType<typeof useRecordFormActions> | null = null;
const Root = defineComponent({
  setup() {
    actions = useRecordFormActions(proxiedDeps);
    return () => h('div');
  },
});
const app = renderer.createApp(Root as never) as unknown as { unmount: () => void };
app.mount(hostNode('root') as never);
const saveRecord = () => actions!.saveRecord();

/**
 * Lets an in-flight save run until it parks on a gate the test has not opened.
 * Microtask turns, not wall-clock sleeps: the completion moment stays the
 * test's decision, so the race window is controlled rather than hoped for.
 */
const drain = async (turns = 40) => {
  for (let index = 0; index < turns; index += 1) await Promise.resolve();
};

const switchSurfaceTo = async (nextModel: string, nextId: number | null) => {
  model.value = nextModel;
  recordId.value = nextId;
  identity.value = `record:${nextModel}:${nextId ?? 'new'}`;
  // The tab follows its record: the instance now owns the new identity, so the
  // shipped lifecycle watcher runs the shipped reload path for it.
  instanceRouteIdentity.value = identity.value;
  await nextTick();
  await nextTick();
  await drain();
};

/** Replaces the registered section with one whose answer the test controls. */
const stubSection = (validate: () => Promise<string[]>) => {
  registry.unregister('section-a');
  registry.register({
    sectionId: 'section-a',
    ruleFieldNames: () => ['name'],
    validate: () => { validateCalls += 1; return validate(); },
  });
};

/** A section that answers as soon as it is asked: the write is the only slow part. */
const immediateSection = () => stubSection(() => Promise.resolve<string[]>([]));


// ---------------------------------------------------------------------------
// Baseline: the shipped chain does save when nothing moves underneath it
// ---------------------------------------------------------------------------
const baselineGate = deferred();
registry.unregister('section-a');
sectionGate = baselineGate;
registry.register({ sectionId: 'section-a', ruleFieldNames: () => ['name'], validate: () => { validateCalls += 1; return sectionGate.promise; } });
const baselineSave = saveRecord();
await nextTick();
baselineGate.resolve([]);
const baselineResult = await baselineSave;
check(baselineResult, true, 'a quiet surface saves once');
check(writes.length, 1, 'the quiet-path save reaches the write boundary exactly once');
check(writes[0]?.ids?.[0], 10, 'the quiet-path write targets the record it started for');
writes.length = 0;

// ---------------------------------------------------------------------------
// Counter-example C (positive control): one record, one in-flight save
// ---------------------------------------------------------------------------
const singleGate = deferred();
registry.unregister('section-a');
sectionGate = singleGate;
registry.register({ sectionId: 'section-a', ruleFieldNames: () => ['name'], validate: () => { validateCalls += 1; return sectionGate.promise; } });
const callsBefore = validateCalls;
const firstCall = saveRecord();
await nextTick();
const secondCall = saveRecord();
check(firstCall === secondCall, true, 'a second save request for the same surface joins the in-flight one instead of validating twice');
check(validateCalls - callsBefore, 1, 'the shipped single-flight guard means one record cannot have two overlapping validations');
singleGate.resolve([]);
await firstCall;
check(writes.length, 1, 'the joined save still writes exactly once');
writes.length = 0;

// ---------------------------------------------------------------------------
// Counter-example A: A's validation fails after the surface moved to B
// ---------------------------------------------------------------------------
const gateA = deferred();
registry.unregister('section-a');
sectionGate = gateA;
registry.register({ sectionId: 'section-a', ruleFieldNames: () => ['name'], validate: () => { validateCalls += 1; return sectionGate.promise; } });
formData.name = '';
const saveA = saveRecord();
await nextTick();
await switchSurfaceTo('sc.general.contract', 11);
formData.name = 'B clean draft';
submissionFeedback.value = null;
validationErrors.value = [];
validationFieldErrors.value = {};
gateA.reject(new Error('adopted form engine returned an unrecognised validation result'));
const resultA = await saveA;
check(resultA, false, 'A: the failed validation does not save');
check(writes.length, 0, 'A: no write happens for the failed validation');
check(validationErrors.value.length, 0, 'A: a validation that failed for the previous record must not mark the new record red');
check(
  String((submissionFeedback.value as { message?: string } | null)?.message || ''),
  '',
  'A: the new record must not inherit the previous record\'s validation feedback',
);

// ---------------------------------------------------------------------------
// Counter-example B: A's validation succeeds after the surface moved to B
// ---------------------------------------------------------------------------
const gateB = deferred();
registry.unregister('section-a');
sectionGate = gateB;
registry.register({ sectionId: 'section-a', ruleFieldNames: () => ['name'], validate: () => { validateCalls += 1; return sectionGate.promise; } });
await switchSurfaceTo('project.project', 10);
formData.name = 'A draft';
originalValues.value = { name: 'A-original' };
const saveB = saveRecord();
await nextTick();
await switchSurfaceTo('sc.general.contract', 11);
gateB.resolve([]);
const resultB = await saveB;
check(writes.length, 0, 'B: a save started for record 10 must not write after the surface moved to record 11');
check(resultB, false, 'B: the stale save must not report success for the new record');
if (writes.length) {
  console.log(`       observed stray write: model=${writes[0].model} ids=${JSON.stringify(writes[0].ids)} vals=${JSON.stringify(writes[0].vals)}`);
}


// ---------------------------------------------------------------------------
// 3a. Leaving and coming back to the same model and id is a new draft session
// ---------------------------------------------------------------------------
writes.length = 0;
creates.length = 0;
await switchSurfaceTo('project.project', 10);
formData.name = 'first session draft';
const gateReentry = deferred();
stubSection(() => gateReentry.promise);
const saveReentry = saveRecord();
await drain();
await switchSurfaceTo('sc.general.contract', 11);
await switchSurfaceTo('project.project', 10);
formData.name = 'second session draft';
submissionFeedback.value = null;
validationErrors.value = [];
gateReentry.resolve([]);
const resultReentry = await saveReentry;
check(resultReentry, false, '3a: a save started before leaving and returning must not resume');
check(writes.length, 0, '3a: returning to the same model and record id does not revive the earlier draft session');
check(validationErrors.value.length, 0, '3a: the abandoned operation leaves the new session without errors');
check(submissionFeedback.value, null, '3a: the abandoned operation writes no feedback onto the new session');

// ---------------------------------------------------------------------------
// 3b. Two unsaved drafts have no record id at all
// ---------------------------------------------------------------------------
writes.length = 0;
creates.length = 0;
await switchSurfaceTo('project.project', null);
formData.name = 'first unsaved draft';
const gateDraft = deferred();
stubSection(() => gateDraft.promise);
const saveDraft = saveRecord();
await drain();
await switchSurfaceTo('project.project', 10);
await switchSurfaceTo('project.project', null);
formData.name = 'second unsaved draft';
submissionFeedback.value = null;
validationErrors.value = [];
gateDraft.resolve([]);
const resultDraft = await saveDraft;
check(resultDraft, false, '3b: an unsaved draft does not resurrect its operation on the next unsaved draft');
check(writes.length, 0, '3b: nothing is written for the abandoned draft session');
check(creates.length, 0, '3b: the abandoned draft session creates nothing');
check(validationErrors.value.length, 0, '3b: an empty record id is still a draft session, and the stale one stays silent');

// ---------------------------------------------------------------------------
// 4. A newer save on the surface outlives the older, superseded one
// ---------------------------------------------------------------------------
writes.length = 0;
creates.length = 0;
await switchSurfaceTo('project.project', 10);
formData.name = 'older operation draft';
immediateSection();
const writeGate1 = deferredVoid();
const writeGate2 = deferredVoid();
writeGates.push(writeGate1, writeGate2);
const olderSave = saveRecord();
await drain();
check(busyKind.value, 'save', '4: the older save owns the busy flag while it writes');
await switchSurfaceTo('sc.general.contract', 11);
formData.name = 'newer operation draft';
const newerSave = saveRecord();
await drain();
check(olderSave === newerSave, false, '4: a save for another record is never joined to the in-flight one');
check(writes.length, 2, '4: each operation reaches the write boundary once');
check(writes[0]?.ids?.[0], 10, '4: the older write kept the record it started for');
check(writes[1]?.ids?.[0], 11, '4: the newer write targets the record on screen');
writeGate1.resolve();
const olderResult = await olderSave;
check(olderResult, false, '4: the superseded operation reports no success for the surface it no longer owns');
check(busyKind.value, 'save', '4: the superseded finally does not clear the newer operation\'s loading state');
check(submissionFeedback.value, null, '4: the superseded operation writes no feedback for the newer record');
check(validationErrors.value.length, 0, '4: the superseded operation writes no error for the newer record');
writeGate2.resolve();
check(await newerSave, true, '4: the newer operation completes normally');
check(busyKind.value, null, '4: the newer operation releases its own loading state');
writeGates.length = 0;

// ---------------------------------------------------------------------------
// 5. An edit during validation must not ride on the older, passing answer
// ---------------------------------------------------------------------------
writes.length = 0;
creates.length = 0;
await switchSurfaceTo('project.project', 10);
formData.name = 'value the engine validated';
const gateDrift = deferred();
stubSection(() => gateDrift.promise);
const driftingSave = saveRecord();
await drain();
formData.name = 'value typed while the engine was deciding';
gateDrift.resolve([]);
const driftResult = await driftingSave;
check(driftResult, false, '5: a draft edited while validating is not written on the older answer');
check(writes.length, 0, '5: nothing is written for a value the engine never saw');
check(formData.name, 'value typed while the engine was deciding', '5: the newer draft is kept so the user can save it deliberately');
check(
  String((submissionFeedback.value as { kind?: string } | null)?.kind || ''),
  'warn',
  '5: the user is told to save again rather than being told the save succeeded',
);

// ---------------------------------------------------------------------------
// 6. The ordinary path still behaves: reject, correct once, refuse and retry
// ---------------------------------------------------------------------------
writes.length = 0;
creates.length = 0;
await switchSurfaceTo('project.project', 10);
formData.name = '';
const gateReject = deferred();
stubSection(() => gateReject.promise);
const rejectedSave = saveRecord();
await drain();
gateReject.resolve(['name']);
const rejectedResult = await rejectedSave;
check(rejectedResult, false, '6: the engine\'s own rejection stops the save');
check(writes.length, 0, '6: a rejected form performs zero writes');
check(validationErrors.value.length > 0, true, '6: the rejection is presented against the record on screen');

formData.name = 'corrected';
const gateAccept = deferred();
stubSection(() => gateAccept.promise);
const correctedSave = saveRecord();
await drain();
gateAccept.resolve([]);
check(await correctedSave, true, '6: a corrected form saves');
check(writes.length, 1, '6: the corrected form writes exactly once');
writes.length = 0;

formData.name = 'the server will refuse this';
immediateSection();
nextWriteError = new TestApiError('金额必须大于零', 422);
check(await saveRecord(), false, '6: a server refusal fails the save');
check(writes.length, 1, '6: the refused draft reached the boundary once');
check(formData.name, 'the server will refuse this', '6: the refused draft is kept so the user can retry');
check(validationErrors.value.length, 1, '6: the server message is presented once');

formData.name = 'corrected after the refusal';
check(await saveRecord(), true, '6: the kept draft can be saved again');
check(writes.length, 2, '6: the retry writes once more, for the corrected draft');
writes.length = 0;
creates.length = 0;

app.unmount();
console.log(`[adopted_form_validation_identity] cases=${cases} failed=${fails.length} engine=shipped-save-chain host=real-vue-instance`);
if (fails.length) {
  console.log('[adopted_form_validation_identity] DEFECT REPRODUCED:');
  fails.forEach((label) => console.log(`  - ${label}`));
  process.exitCode = 1;
} else {
  console.log('[adopted_form_validation_identity] no cross-identity leak observed');
}
