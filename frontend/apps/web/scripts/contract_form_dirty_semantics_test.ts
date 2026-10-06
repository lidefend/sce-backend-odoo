import assert from 'node:assert/strict';
import { computed, ref } from 'vue';

import { useRecordFormState } from '../src/pages/contractForm/useRecordFormState';

// Dirty semantics are a consumer responsibility, not a permission decision.
// The record form delivers the persisted record baseline; a value setter that
// receives a value identical to that baseline (for example a relation component
// writing its selection back on mount) has changed nothing. It must not mark the
// field dirty and must not dispatch an onchange. The dispatch trigger used here
// is the same declaration shape the runtime consumes (a `change` + `server`
// widget rule), so the negative case proves the guard is value-based and not a
// suppression of the declared action.

const SERVER_RULE = { sourceWidgetId: 'field.name', triggerType: 'change', dispatchMode: 'server' };

function harness(options: {
  fields: Record<string, any>;
  formData: Record<string, unknown>;
  originalValues: Record<string, unknown>;
  rules?: Array<Record<string, unknown>>;
}) {
  const fields = options.fields;
  const formData = { ...options.formData };
  const originalValues = ref<Record<string, unknown>>({ ...options.originalValues });
  const dirtyFieldSet = new Set<string>();
  const changedFieldSet = new Set<string>();
  const applyingOnchangePatch = ref(false);
  const validationErrors = ref<string[]>([]);
  const validationFieldErrors = ref<Record<string, unknown>>({});
  let timer: ReturnType<typeof setTimeout> | null = null;

  const context: any = {
    formFields: computed(() => fields),
    model: computed(() => 'project.project'),
    recordId: computed(() => 581),
    rights: computed(() => ({ write: true })),
    formData,
    originalValues,
    submissionFeedback: ref(null),
    relationKeywords: {},
    invalidatedRelationKeywords: {},
    clearedDynamicRelationFields: {},
    relationQueryTimers: {},
    relationOptions: ref({}),
    validationErrors,
    validationFieldErrors,
    onchangeModifiersPatch: ref({}),
    onchangeWarnings: ref([]),
    onchangeLinePatches: ref([]),
    applyingOnchangePatch,
    changedFieldSet,
    dirtyFieldSet,
    getOnchangeTimer: () => timer,
    setOnchangeTimer: (value: ReturnType<typeof setTimeout> | null) => { timer = value; },
    contractV2ActionRules: computed(() => options.rules || []),
    layoutNodes: computed(() => Object.keys(fields).map((name) => ({ kind: 'field', name, readonly: false, descriptor: fields[name] }))),
    nativeStatusbar: computed(() => ({ field: '', readonly: false })),
    route: { query: {} },
    isNativeFavoriteField: () => false,
    clearDynamicRelationDependents: () => {},
    openRelationCreateForm: async () => undefined,
    openRelationSearchDialog: async () => undefined,
    openRelationRecordForm: async () => undefined,
    relationOptionsForField: () => [],
    switchFormByRelationOption: async () => undefined,
    queryRelationOptions: async () => [],
    setRelationKeyword: () => {},
    setMany2oneOption: () => {},
    relationKeyword: () => '',
    quickCreateRelation: async () => undefined,
    relationUiLabel: (_d: unknown, _k: string, fallback?: string) => fallback || '',
    relationModel: () => 'res.partner',
    relationIds: (name: string) => (Array.isArray((formData as any)[name]) ? (formData as any)[name] : []),
    upsertRelationOption: () => {},
    buildOne2manyCommandValue: () => [],
    one2manyFieldRows: () => [],
    initOne2manyRows: () => {},
    applyOnchangeLinePatches: () => {},
    isWritableFieldVisible: () => true,
    canonicalFieldWritable: () => true,
    fieldOccurrenceDecision: () => 'writable',
    pendingInlineCreateFields: ref([]),
  };

  const api = useRecordFormState(context);
  return {
    api,
    dirtyFieldSet,
    changedFieldSet,
    hasTimer: () => timer !== null,
    stopTimer: () => { if (timer) { clearTimeout(timer); timer = null; } },
  };
}

// 1. A relation write-back that repeats the loaded value is not a change.
{
  const h = harness({
    fields: { tag_ids: { ttype: 'many2many', name: 'tag_ids' } },
    formData: { tag_ids: [3, 1] },
    originalValues: { tag_ids: [1, 3] },
    rules: [{ sourceWidgetId: 'field.tag_ids', triggerType: 'change', dispatchMode: 'server' }],
  });
  h.api.setRelationIds('tag_ids', [3, 1]);
  assert.equal(h.dirtyFieldSet.size, 0, 'an identical relation value must not be dirty');
  assert.equal(h.changedFieldSet.size, 0, 'an identical relation value must not dispatch onchange');
  assert.equal(h.hasTimer(), false, 'no onchange timer for an identical value');
}

// 2. A relation write-back that adds an id is a change and still dispatches.
{
  const h = harness({
    fields: { tag_ids: { ttype: 'many2many', name: 'tag_ids' } },
    formData: { tag_ids: [1, 3] },
    originalValues: { tag_ids: [1] },
    rules: [{ sourceWidgetId: 'field.tag_ids', triggerType: 'change', dispatchMode: 'server' }],
  });
  h.api.setRelationIds('tag_ids', [1, 3]);
  assert.equal(h.dirtyFieldSet.has('tag_ids'), true, 'a changed relation value is dirty');
  assert.equal(h.changedFieldSet.has('tag_ids'), true, 'a changed relation value dispatches onchange');
  h.stopTimer();
}

// 3. Setting the same scalar back leaves no dirty state; reverting clears it.
{
  const h = harness({
    fields: { name: { ttype: 'char', name: 'name' } },
    formData: { name: 'A' },
    originalValues: { name: 'A' },
    rules: [SERVER_RULE],
  });
  h.api.setTextField('name', 'A');
  assert.equal(h.dirtyFieldSet.size, 0, 'identical text must not be dirty');
  assert.equal(h.changedFieldSet.size, 0, 'identical text must not dispatch onchange');

  h.api.setTextField('name', 'B');
  assert.equal(h.dirtyFieldSet.has('name'), true, 'changed text is dirty');
  assert.equal(h.changedFieldSet.has('name'), true, 'changed text dispatches onchange');
  assert.equal(h.hasTimer(), true, 'changed text schedules onchange');

  h.api.setTextField('name', 'A');
  assert.equal(h.dirtyFieldSet.has('name'), false, 'reverting to the record value clears dirty');
  assert.equal(h.changedFieldSet.has('name'), false, 'reverting clears the pending onchange field');
  assert.equal(h.hasTimer(), false, 'reverting cancels the pending onchange timer');
}

// 4. An identical selection or boolean is not a change; a different one is.
{
  const h = harness({
    fields: { state: { ttype: 'selection', name: 'state' }, active: { ttype: 'boolean', name: 'active' } },
    formData: { state: 'done', active: true },
    originalValues: { state: 'done', active: true },
    rules: [],
  });
  h.api.setSelectionField('state', 'done');
  h.api.setBooleanField('active', true);
  assert.equal(h.dirtyFieldSet.size, 0, 'identical selection/boolean must not be dirty');

  h.api.setSelectionField('state', 'cancel');
  assert.equal(h.dirtyFieldSet.has('state'), true, 'a different selection is dirty');
  h.api.setBooleanField('active', false);
  assert.equal(h.dirtyFieldSet.has('active'), true, 'a different boolean is dirty');
}

process.stdout.write('contract_form_dirty_semantics_test: PASS\n');
