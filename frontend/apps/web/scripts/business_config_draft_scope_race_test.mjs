import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import { createRequire } from 'node:module';
const require = createRequire(new URL('../package.json', import.meta.url));
const ts = require('typescript');
const vue = require('vue');
const source = fs.readFileSync(new URL('../src/views/businessConfigSurface/useBusinessConfigDraftSession.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
const draft = (token, state = 'draft') => ({ token: String(token), state, item_count: 1, items: [], publish_result: { ok: true, published_content_verified: true } });
let cases = 0;
async function scenario(method, endpoint, switchKind = 'action') {
  const target = vue.ref(666), role = vue.ref('admin'), company = vue.ref(1);
  let release;
  const writes = [];
  const api = {
    resumeBusinessConfigChangeSet: async () => draft(target.value),
    openBusinessConfigChangeSet: async () => draft(target.value),
    validateBusinessConfigChangeSet: async p => draft(p.change_set_token, 'ready'),
    publishBusinessConfigChangeSet: async p => { writes.push(p.change_set_token); return draft(p.change_set_token, 'published'); },
  };
  api[endpoint] = () => new Promise(resolve => { release = resolve; });
  const exports = {};
  vm.runInNewContext(compiled, { exports, require: name => name === 'vue' ? vue : api, Date, Math });
  const scope = vue.effectScope();
  const session = scope.run(() => exports.useBusinessConfigDraftSession(() => role.value, () => ({ model: 'same.document', actionId: target.value, companyId: company.value })));
  await session.resumeScope();
  const pending = session[method]({ model: 'same.document', action_id: 666 });
  const rejected = assert.rejects(pending, /配置对象已变化/);
  assert.equal(session.busy.value, true, `${method} must lock synchronously`);
  await assert.rejects(session.discardDraft(), /配置操作正在进行/);
  for (let n = 0; n < 6 && !release; n++) await Promise.resolve();
  assert(release, `${endpoint} was not reached`);
  if (switchKind === 'action') target.value = 862;
  else if (switchKind === 'role') role.value = 'other';
  else company.value = 2;
  await session.resumeScope();
  const newDraft = session.changeSet.value;
  release(draft(666, 'ready'));
  await rejected;
  assert.equal(session.changeSet.value, newDraft, 'late response overwrote current scope');
  assert.equal(writes.length, 0, 'stale validation continued to publication');
  assert.equal(session.busy.value, false);
  scope.stop(); cases++;
}
for (const [method, endpoint] of [
  ['publishDraft', 'validateBusinessConfigChangeSet'],
  ['validateDraft', 'validateBusinessConfigChangeSet'],
  ['previewDraft', 'previewBusinessConfigChangeSet'],
  ['rollbackPublished', 'rollbackBusinessConfigChangeSet'],
  ['discardDraft', 'discardBusinessConfigChangeSet'],
  ['stageItem', 'stageBusinessConfigChangeSetItem'],
]) await scenario(method, endpoint);
await scenario('publishDraft', 'validateBusinessConfigChangeSet', 'role');
await scenario('publishDraft', 'validateBusinessConfigChangeSet', 'company');
// A stable target still completes validation and publication once.
{
  const exports = {}; let writes = 0;
  const api = { resumeBusinessConfigChangeSet: async () => draft(666), validateBusinessConfigChangeSet: async () => draft(666, 'ready'), publishBusinessConfigChangeSet: async () => { writes++; return draft(666, 'published'); } };
  vm.runInNewContext(compiled, { exports, require: name => name === 'vue' ? vue : api, Date, Math });
  const scope = vue.effectScope();
  const session = scope.run(() => exports.useBusinessConfigDraftSession(() => 'admin', () => ({ model: 'same.document', actionId: 666 })));
  await session.resumeScope();
  assert.equal((await session.publishDraft()).state, 'published');
  assert.equal(writes, 1); assert.equal(session.busy.value, false);
  scope.stop(); cases++;
}
console.log(`[business_config_draft_scope_race] PASS cases=${cases}`);
