import assert from 'node:assert/strict';
import { ref } from 'vue';
import {
  buildIntakeAutosaveKey,
  clearIntakeAutosavePayload,
  persistIntakeAutosavePayload,
  resolveIntakeAutosavePolicy,
  restoreIntakeAutosavePayload,
  type IntakeAutosavePolicy,
} from '../src/pages/contractForm/intakeAutosave';
import { useIntakeAutosaveRuntime } from '../src/pages/contractForm/useIntakeAutosaveRuntime';

class MemoryStorage {
  private values = new Map<string, string>();
  failWrites = false;

  getItem(key: string) {
    return this.values.get(key) ?? null;
  }

  setItem(key: string, value: string) {
    if (this.failWrites) throw new Error('quota');
    this.values.set(key, value);
  }

  removeItem(key: string) {
    this.values.delete(key);
  }
}

const storage = new MemoryStorage();
Object.defineProperty(globalThis, 'window', {
  configurable: true,
  value: { localStorage: storage },
});

const rawPolicy = {
  schemaVersion: 'intake_autosave_policy.v1',
  policyVersion: 1,
  enabled: true,
  appliesTo: ['create'],
  scope: 'project_intake_standard',
  storage: {
    kind: 'browser_local_storage',
    keyPrefix: 'sc:intake:autosave',
    payloadVersion: 1,
  },
  retention: { seconds: 86400, basis: 'last_valid_input' },
  recovery: {
    strategy: 'prompt_restore_or_discard',
    actions: ['restore', 'discard'],
  },
  identity: {
    requiredScopes: [
      'tenant', 'user', 'company', 'menu', 'action',
      'form_view', 'entry_scope', 'form_instance',
    ],
  },
  fields: [
    {
      name: 'name',
      label: '项目名称',
      type: 'char',
      relation: '',
      inputKind: 'text',
      required: true,
      readonly: false,
      allowEmpty: true,
      source: 'effective_create_form',
      constraints: { maxLength: 120 },
    },
    {
      name: 'manager_id',
      label: '项目经理',
      type: 'many2one',
      relation: 'res.users',
      inputKind: 'relation',
      required: false,
      readonly: false,
      allowEmpty: true,
      source: 'effective_create_form',
      constraints: { mustExist: true },
    },
    {
      name: 'operation_strategy',
      label: '经营方式',
      type: 'selection',
      relation: '',
      inputKind: 'selection',
      required: false,
      readonly: false,
      allowEmpty: true,
      source: 'effective_create_form',
      constraints: { allowedValues: ['direct', 'joint'] },
    },
    {
      name: 'sequence',
      label: '顺序',
      type: 'integer',
      relation: '',
      inputKind: 'integer',
      required: false,
      readonly: false,
      allowEmpty: true,
      source: 'effective_create_form',
      constraints: { numeric: true },
    },
    {
      name: 'active',
      label: '有效',
      type: 'boolean',
      relation: '',
      inputKind: 'boolean',
      required: false,
      readonly: false,
      allowEmpty: true,
      source: 'effective_create_form',
      constraints: {},
    },
  ],
  coverage: {
    fields: true,
    attachments: false,
    binary: false,
    unsavedChildRecords: false,
    workflowState: false,
    serverDefaults: false,
  },
};

const policy = resolveIntakeAutosavePolicy({ intakeAutosave: rawPolicy }) as IntakeAutosavePolicy;
assert.equal(policy.scope, 'project_intake_standard');
assert.equal(policy.retention.seconds, 86400);
assert.equal(policy.fields.length, 5);
const shortRetentionPolicy = resolveIntakeAutosavePolicy({
  intakeAutosave: {
    ...rawPolicy,
    scope: 'project_intake_short_retention',
    retention: { seconds: 60, basis: 'last_valid_input' },
  },
}) as IntakeAutosavePolicy;
assert.equal(shortRetentionPolicy.retention.seconds, 60, 'frontend consumes the declared retention instead of a local 24-hour default');
const missingRetentionPolicy = { ...rawPolicy } as Record<string, unknown>;
delete missingRetentionPolicy.retention;
assert.throws(
  () => resolveIntakeAutosavePolicy({ intakeAutosave: missingRetentionPolicy }),
  (error: unknown) => Boolean(error && typeof error === 'object' && (error as { name?: string }).name === 'ContractGapError'),
  'a missing retention declaration must fail closed',
);
assert.throws(
  () => resolveIntakeAutosavePolicy({ intakeAutosave: { enabled: true } }),
  (error: unknown) => Boolean(error && typeof error === 'object' && (error as { name?: string }).name === 'ContractGapError'),
);

const identity = {
  tenant: '/t/acceptance',
  user: 12,
  company: 2,
  menu: 382,
  action: 590,
  form_view: 1508,
  form_instance: 'new|project.project|standard|defaults-a',
};
const key = buildIntakeAutosaveKey(policy, identity);
assert.match(key, /policy=1/);
assert.match(key, /entry_scope=project_intake_standard/);
assert.equal(buildIntakeAutosaveKey(policy, { ...identity, user: '' }), '');

// Runtime persistence uses the live clock; keep the fixture relative so the
// happy path cannot become "expired" merely because the calendar day changed.
const now = Date.now();
assert.equal(persistIntakeAutosavePayload({
  policy,
  key,
  identity,
  draftToken: 'draft-v1',
  now,
  values: {
    name: '',
    manager_id: false,
    operation_strategy: 'direct',
    sequence: 0,
    active: false,
    attachment_ids: [99],
    workflow_state: 'draft',
  },
}), 'saved');

const restored = restoreIntakeAutosavePayload({ policy, key, identity, now: now + 1000 });
assert.equal(restored.status, 'recoverable');
if (restored.status === 'recoverable') {
  assert.deepEqual(restored.candidate.values, {
    name: '',
    manager_id: false,
    operation_strategy: 'direct',
    sequence: 0,
    active: false,
  });
  assert.equal(restored.candidate.values.name, '', 'a deliberate clear remains a restorable value');
  assert.equal(restored.candidate.values.sequence, 0);
  assert.equal(restored.candidate.values.active, false);
}
assert.equal(
  restoreIntakeAutosavePayload({ policy, key, identity, now: now + 86401 * 1000 }).status,
  'expired',
);
const shortIdentity = { ...identity, form_instance: 'new|project.project|short-retention' };
const shortKey = buildIntakeAutosaveKey(shortRetentionPolicy, shortIdentity);
assert.equal(persistIntakeAutosavePayload({
  policy: shortRetentionPolicy,
  key: shortKey,
  identity: shortIdentity,
  draftToken: 'short-retention-v1',
  now,
  values: { name: 'short retention' },
}), 'saved');
assert.equal(
  restoreIntakeAutosavePayload({ policy: shortRetentionPolicy, key: shortKey, identity: shortIdentity, now: now + 59_000 }).status,
  'recoverable',
);
assert.equal(
  restoreIntakeAutosavePayload({ policy: shortRetentionPolicy, key: shortKey, identity: shortIdentity, now: now + 61_000 }).status,
  'expired',
);
assert.equal(
  restoreIntakeAutosavePayload({ policy, key, identity: { ...identity, company: 3 }, now }).status,
  'invalid',
);
assert.equal(clearIntakeAutosavePayload(key, { policyVersion: 2, scope: policy.scope, draftToken: 'draft-v1' }), false);
assert.equal(clearIntakeAutosavePayload(key, { policyVersion: 1, scope: policy.scope, draftToken: 'stale' }), false);
assert.equal(clearIntakeAutosavePayload(key, { policyVersion: 1, scope: policy.scope, draftToken: 'draft-v1' }), true);
assert.equal(
  persistIntakeAutosavePayload({
    policy,
    key,
    identity,
    draftToken: 'invalid-values',
    values: {
      name: 'x'.repeat(121),
      operation_strategy: 'forged',
      sequence: 1.5,
    },
  }),
  'skipped',
);
assert.equal(restoreIntakeAutosavePayload({ policy, key, identity, now }).status, 'none');

storage.setItem(key, '{broken');
assert.equal(restoreIntakeAutosavePayload({ policy, key, identity, now }).status, 'invalid');
storage.removeItem(key);
storage.failWrites = true;
assert.equal(persistIntakeAutosavePayload({ policy, key, identity, draftToken: 'draft-v2', values: { name: 'A' } }), 'failed');
storage.failWrites = false;

const formData: Record<string, unknown> = { name: 'Server default', manager_id: false };
const paused = ref(true);
const notices: string[] = [];
const runtime = useIntakeAutosaveRuntime({
  policy: ref(policy),
  identity: ref(identity),
  hasRecord: ref(null),
  formData,
  isActive: ref(true),
  isDirty: ref(true),
  paused,
  isFieldWritable: () => true,
  applyRestoredValues: async (candidate) => {
    Object.assign(formData, candidate.values);
  },
  onNotice: (notice) => { if (notice) notices.push(notice.kind); },
});
persistIntakeAutosavePayload({
  policy,
  key,
  identity,
  draftToken: 'hook-draft-v1',
  values: { name: '', manager_id: 17, operation_strategy: 'joint', sequence: 0, active: false },
});
assert.equal(runtime.inspect(), 'recoverable');
assert.equal(paused.value, true, 'autosave remains paused until the user chooses');
assert.equal(await runtime.restore(), true);
assert.deepEqual(formData, {
  name: '',
  manager_id: 17,
  operation_strategy: 'joint',
  sequence: 0,
  active: false,
});
assert.equal(paused.value, false, 'autosave starts only after restore hydration');
assert.deepEqual(notices.slice(-2), ['info', 'success']);

const staleCapture = runtime.capture();
formData.name = 'newer draft';
runtime.persist();
assert.equal(runtime.clear(staleCapture), false, 'an older save cannot clear a newer draft revision');
assert.equal(runtime.clear(runtime.capture()), true);

const discardRuntime = useIntakeAutosaveRuntime({
  policy: ref(policy),
  identity: ref(identity),
  hasRecord: ref(null),
  formData: {},
  isActive: ref(true),
  isDirty: ref(true),
  paused,
  isFieldWritable: () => true,
  applyRestoredValues: async () => undefined,
  onNotice: (notice) => { if (notice) notices.push(notice.kind); },
});
persistIntakeAutosavePayload({
  policy,
  key,
  identity,
  draftToken: 'discard-draft-v1',
  values: { name: 'discard me' },
});
assert.equal(discardRuntime.inspect(), 'recoverable');
discardRuntime.discard();
assert.equal(discardRuntime.candidate.value, null);
assert.equal(restoreIntakeAutosavePayload({ policy, key, identity, now }).status, 'none');

const createWithoutRestoreRuntime = useIntakeAutosaveRuntime({
  policy: ref(policy),
  identity: ref(identity),
  hasRecord: ref(null),
  formData: {},
  isActive: ref(true),
  isDirty: ref(false),
  paused,
  isFieldWritable: () => true,
  applyRestoredValues: async () => undefined,
  onNotice: () => undefined,
});
persistIntakeAutosavePayload({
  policy,
  key,
  identity,
  draftToken: 'create-without-restore-v1',
  values: { name: 'unresolved prompt' },
});
assert.equal(createWithoutRestoreRuntime.inspect(), 'recoverable');
assert.deepEqual(createWithoutRestoreRuntime.capture(), {
  key,
  policyVersion: 1,
  scope: policy.scope,
  draftToken: 'create-without-restore-v1',
});
createWithoutRestoreRuntime.persist();
assert.equal(
  restoreIntakeAutosavePayload({ policy, key, identity, now }).status,
  'recoverable',
  'initial clean must not delete a pending restore candidate',
);
assert.equal(createWithoutRestoreRuntime.clear(createWithoutRestoreRuntime.capture()), true);
assert.equal(restoreIntakeAutosavePayload({ policy, key, identity, now }).status, 'none');

const writableIdentity = { ...identity, form_instance: 'writable-intersection' };
const writableKey = buildIntakeAutosaveKey(policy, writableIdentity);
const writable = new Set(['name', 'sequence', 'active']);
const writableFormData: Record<string, unknown> = {
  name: 'Server default',
  manager_id: false,
  operation_strategy: 'direct',
  sequence: 0,
  active: true,
};
const writableRuntime = useIntakeAutosaveRuntime({
  policy: ref(policy),
  identity: ref(writableIdentity),
  hasRecord: ref(null),
  formData: writableFormData,
  isActive: ref(true),
  isDirty: ref(true),
  paused: ref(true),
  isFieldWritable: (name) => writable.has(name),
  applyRestoredValues: async (candidate) => {
    Object.assign(writableFormData, candidate.values);
  },
  onNotice: () => undefined,
});
persistIntakeAutosavePayload({
  policy,
  key: writableKey,
  identity: writableIdentity,
  draftToken: 'writable-intersection-v1',
  now,
  values: {
    name: 'Draft name',
    manager_id: 17,
    operation_strategy: 'joint',
    sequence: 9,
    active: false,
  },
});
assert.equal(writableRuntime.inspect(), 'recoverable');
assert.equal(await writableRuntime.restore(), true);
assert.deepEqual(writableFormData, {
  name: 'Draft name',
  manager_id: false,
  operation_strategy: 'direct',
  sequence: 9,
  active: false,
}, 'restore only writes fields writable in the current form contract');

const cleanIdentity = { ...identity, form_instance: 'clean-reversion' };
const cleanKey = buildIntakeAutosaveKey(policy, cleanIdentity);
const cleanDirty = ref(false);
const cleanFormData: Record<string, unknown> = {
  name: 'Server default',
  manager_id: false,
  operation_strategy: 'direct',
  sequence: 0,
  active: true,
};
const cleanRuntime = useIntakeAutosaveRuntime({
  policy: ref(policy),
  identity: ref(cleanIdentity),
  hasRecord: ref(null),
  formData: cleanFormData,
  isActive: ref(true),
  isDirty: cleanDirty,
  paused: ref(true),
  isFieldWritable: () => true,
  applyRestoredValues: async () => undefined,
  onNotice: () => undefined,
});
assert.equal(cleanRuntime.inspect(), 'none');
cleanDirty.value = true;
cleanFormData.name = 'Temporary change';
cleanRuntime.persist();
assert.equal(
  restoreIntakeAutosavePayload({ policy, key: cleanKey, identity: cleanIdentity, now }).status,
  'recoverable',
);
cleanDirty.value = false;
cleanFormData.name = 'Server default';
cleanRuntime.persist();
assert.equal(
  restoreIntakeAutosavePayload({ policy, key: cleanKey, identity: cleanIdentity, now }).status,
  'none',
  'returning every field to the initial clean values must clear the old draft',
);

console.log('[intake-autosave-runtime] PASS cases=33');
