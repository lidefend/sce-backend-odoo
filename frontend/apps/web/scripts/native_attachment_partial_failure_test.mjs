import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import { createRequire } from 'node:module';
import test from 'node:test';

const require = createRequire(new URL('../package.json', import.meta.url));
const ts = require('typescript');
const vue = require('vue');
const source = fs.readFileSync(new URL('../src/pages/contractForm/useNativeAttachmentRuntime.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;

function runtime({ failUpload = () => false, failRead = () => false, failEncode = () => false } = {}) {
  const calls = [], errors = [], refreshes = [];
  const api = {
    fileToBase64: async file => {
      if (failEncode(file.name)) throw new Error('cannot read file');
      return { data: file.name, mimetype: 'text/plain' };
    },
    uploadFile: async params => {
      calls.push(params);
      if (failUpload(params.name)) throw new Error('upload rejected');
      return { id: calls.length };
    },
  };
  const exports = {};
  vm.runInNewContext(compiled, { exports, require: name => name === 'vue' ? vue : api, Date, Math });
  const state = exports.useNativeAttachmentRuntime({
    model: () => 'x.document', recordId: () => 0, maxBytes: () => 100,
    canUpload: () => true, resolveLabel: (_key, fallback) => fallback,
    reloadTimeline: async (id, model) => { refreshes.push([id, model]); if (failRead()) throw new Error('read unavailable'); },
    viewerRef: vue.ref(null), onPendingUploadFailed: message => errors.push(message),
  });
  return { state, calls, errors, refreshes, add: name => state.onAttachmentSelected({ name, size: 1 }) };
}

test('partial failure retries only failed and unattempted files on the same record', async () => {
  let reject = true;
  const r = runtime({ failUpload: name => reject && name === 'second' });
  for (const name of ['first', 'second', 'third']) await r.add(name);
  assert.equal(await r.state.uploadPendingAttachments(91), false);
  assert.deepEqual(r.calls.map(p => p.name), ['first', 'second']);
  assert.deepEqual(Array.from(r.state.pendingAttachments.value, p => p.name), ['second', 'third']);
  assert.equal(r.errors.length, 1);
  assert.equal(r.state.uploading.value, false);
  reject = false;
  assert.equal(await r.state.uploadPendingAttachments(91), true);
  assert.deepEqual(r.calls.map(p => p.name), ['first', 'second', 'second', 'third']);
  assert.ok(r.calls.every(p => p.model === 'x.document' && p.res_id === 91));
  assert.equal(r.state.pendingAttachments.value.length, 0);
  assert.deepEqual(r.refreshes, [[91, 'x.document']]);
});

test('file conversion failure retains the remaining queue without replaying confirmed upload', async () => {
  const r = runtime({ failEncode: name => name === 'second' });
  await r.add('first'); await r.add('second');
  assert.equal(await r.state.uploadPendingAttachments(91), false);
  assert.deepEqual(r.calls.map(p => p.name), ['first']);
  assert.deepEqual(Array.from(r.state.pendingAttachments.value, p => p.name), ['second']);
});

test('first upload failure removes no file', async () => {
  const r = runtime({ failUpload: () => true });
  await r.add('first'); await r.add('second');
  assert.equal(await r.state.uploadPendingAttachments(91), false);
  assert.deepEqual(Array.from(r.state.pendingAttachments.value, p => p.name), ['first', 'second']);
});

test('timeline failure after confirmed uploads does not requeue uploaded files', async () => {
  const r = runtime({ failRead: () => true });
  await r.add('first'); await r.add('second');
  assert.equal(await r.state.uploadPendingAttachments(91), false);
  assert.equal(r.state.pendingAttachments.value.length, 0);
  assert.equal(await r.state.uploadPendingAttachments(91), true);
  assert.deepEqual(r.calls.map(p => p.name), ['first', 'second']);
});
