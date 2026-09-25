import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { createRequire } from 'node:module';

const require = createRequire(new URL('../package.json', import.meta.url));
const ts = require('typescript');

const FORM_DIR = path.resolve(new URL('../src/pages/contractForm', import.meta.url).pathname);

// Loads the real form modules so the roundtrip under test is the shipped one.
// Only the two API modules are faked: the onchange transport is driven by hand
// so response ordering is decided by the test, not by the network.
function createModuleLoader(onchangeTransport, dataTransport) {
  const cache = new Map();
  const fakes = new Map([
    [path.join(FORM_DIR, '../../api/onchange.ts'), { triggerOnchange: onchangeTransport }],
    [path.join(FORM_DIR, '../../app/runtime/contractFormDataRuntime.ts'), dataTransport],
  ]);
  function resolveFile(base) {
    for (const candidate of [`${base}.ts`, `${base}.tsx`, base]) {
      if (fs.existsSync(candidate) && fs.statSync(candidate).isFile()) return candidate;
    }
    return null;
  }
  function load(base) {
    const file = resolveFile(base);
    if (!file) throw new Error(`unresolved module: ${base}`);
    if (fakes.has(file)) return fakes.get(file);
    if (cache.has(file)) return cache.get(file).exports;
    const js = ts.transpileModule(fs.readFileSync(file, 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    }).outputText;
    const module = { exports: {} };
    cache.set(file, module);
    const factory = vm.runInThisContext(
      `(function(exports, require, module, __filename, __dirname, import_meta){${js}})`,
      { filename: file },
    );
    factory(
      module.exports,
      (spec) => (spec.startsWith('.') ? load(path.resolve(path.dirname(file), spec)) : require(spec)),
      module,
      file,
      path.dirname(file),
      { env: {} },
    );
    return module.exports;
  }
  return { load };
}

function makeContext(requests) {
  const timer = { current: null };
  const fields = {
    a: { name: 'a', ttype: 'char' },
    x: { name: 'x', ttype: 'char' },
    y: { name: 'y', ttype: 'char' },
  };
  const context = {
    formFields: { value: fields },
    model: { value: 'x.document' },
    recordId: { value: 1 },
    rights: { value: { write: true } },
    formData: {},
    originalValues: { value: {} },
    submissionFeedback: { value: null },
    relationKeywords: {},
    invalidatedRelationKeywords: {},
    clearedDynamicRelationFields: {},
    relationQueryTimers: {},
    relationOptions: { value: {} },
    validationErrors: { value: [] },
    validationFieldErrors: { value: {} },
    onchangeModifiersPatch: { value: {} },
    onchangeWarnings: { value: [] },
    onchangeLinePatches: { value: [] },
    applyingOnchangePatch: { value: false },
    changedFieldSet: new Set(),
    dirtyFieldSet: new Set(),
    getOnchangeTimer: () => timer.current,
    setOnchangeTimer: (value) => { timer.current = value; },
    contractV2ActionRules: {
      value: ['a', 'x', 'y'].map((name) => ({
        source_widget_id: `field.${name}`, trigger_type: 'change', dispatch_mode: 'server_onchange',
      })),
    },
    layoutNodes: {
      value: ['a', 'x', 'y'].map((name) => ({ kind: 'field', name, readonly: false })),
    },
    nativeStatusbar: { value: {} },
    route: { query: {} },
    isNativeFavoriteField: () => false,
    clearDynamicRelationDependents: () => {},
    openRelationCreateForm: async () => ({}),
    openRelationSearchDialog: async () => ({}),
    openRelationRecordForm: async () => ({}),
    relationOptionsForField: () => [],
    switchFormByRelationOption: async () => ({}),
    queryRelationOptions: async () => [],
    setRelationKeyword: () => {},
    setMany2oneOption: () => {},
    relationKeyword: () => '',
    quickCreateRelation: async () => ({}),
    relationUiLabel: (_descriptor, _key, fallback) => fallback || '',
    relationModel: () => 'x.document',
    relationIds: () => [],
    upsertRelationOption: () => {},
    buildOne2manyCommandValue: () => [],
    one2manyFieldRows: () => [],
    initOne2manyRows: () => {},
    applyOnchangeLinePatches: () => {},
    isWritableFieldVisible: () => true,
    canonicalFieldWritable: () => true,
  };
  context.__requests = requests;
  return context;
}

const settle = () => new Promise((resolve) => setImmediate(resolve));
async function waitForRequest(requests, index) {
  for (let attempt = 0; attempt < 60 && requests.length <= index; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 20));
  }
  assert.ok(requests.length > index, `roundtrip ${index + 1} was never issued`);
  return requests[index];
}

let checks = 0;
function check(label) { checks += 1; console.log(`  ok ${label}`); }

// A response computed for an earlier draft must not overwrite the newer one.
{
  const requests = [];
  const { load } = createModuleLoader(
    (params) => new Promise((resolve, reject) => requests.push({ params, resolve, reject })),
    { createContractFormRecord: async () => ({}), writeContractFormRecord: async () => ({}) },
  );
  const { useRecordFormState } = load(path.join(FORM_DIR, 'useRecordFormState'));
  const context = makeContext(requests);
  const form = useRecordFormState(context);

  form.setTextField('a', 'first');
  const first = await waitForRequest(requests, 0);
  form.setTextField('a', 'second');
  const second = await waitForRequest(requests, 1);

  second.resolve({ patch: { x: 'from-second' } });
  await settle();
  assert.equal(context.formData.x, 'from-second', 'the newest roundtrip must apply');

  first.resolve({ patch: { x: 'from-first' } });
  await settle();
  await settle();
  assert.equal(context.formData.x, 'from-second', 'a superseded roundtrip overwrote the newer draft');
  check('superseded roundtrip cannot overwrite the newer draft');
}

// A field the user moved after the request was sent keeps the local value.
{
  const requests = [];
  const { load } = createModuleLoader(
    (params) => new Promise((resolve, reject) => requests.push({ params, resolve, reject })),
    { createContractFormRecord: async () => ({}), writeContractFormRecord: async () => ({}) },
  );
  const { useRecordFormState } = load(path.join(FORM_DIR, 'useRecordFormState'));
  const context = makeContext(requests);
  const form = useRecordFormState(context);

  form.setTextField('a', 'drive-x');
  const first = await waitForRequest(requests, 0);
  form.setTextField('x', 'typed-by-user');
  first.resolve({ patch: { x: 'computed-by-server' } });
  await settle();
  await settle();
  assert.equal(context.formData.x, 'typed-by-user', 'the roundtrip overwrote input made after the request');
  check('local input after the request is not overwritten');
}

// A response for another record must not land on the record now on screen.
{
  const requests = [];
  const { load } = createModuleLoader(
    (params) => new Promise((resolve, reject) => requests.push({ params, resolve, reject })),
    { createContractFormRecord: async () => ({}), writeContractFormRecord: async () => ({}) },
  );
  const { useRecordFormState } = load(path.join(FORM_DIR, 'useRecordFormState'));
  const context = makeContext(requests);
  const form = useRecordFormState(context);

  form.setTextField('a', 'drive-x');
  const first = await waitForRequest(requests, 0);
  context.recordId.value = 999;
  first.resolve({ patch: { x: 'from-other-record' } });
  await settle();
  await settle();
  assert.equal(context.formData.x, undefined, 'a response for another record was applied');
  check('a response for another record is not applied');
}

// Control: an unchanged draft still receives the server result.
{
  const requests = [];
  const { load } = createModuleLoader(
    (params) => new Promise((resolve, reject) => requests.push({ params, resolve, reject })),
    { createContractFormRecord: async () => ({}), writeContractFormRecord: async () => ({}) },
  );
  const { useRecordFormState } = load(path.join(FORM_DIR, 'useRecordFormState'));
  const context = makeContext(requests);
  const form = useRecordFormState(context);

  form.setTextField('a', 'drive-x');
  const first = await waitForRequest(requests, 0);
  first.resolve({ patch: { x: 'computed-by-server' }, warnings: [{ message: 'notice' }] });
  await settle();
  await settle();
  assert.equal(context.formData.x, 'computed-by-server', 'a current roundtrip must still apply');
  assert.equal(context.onchangeWarnings.value[0]?.message, 'notice');
  check('a current roundtrip still applies');
}

console.log(`[onchange_roundtrip_race] PASS checks=${checks}`);
