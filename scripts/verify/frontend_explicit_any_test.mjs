import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import { execFileSync } from 'node:child_process';
import { countExplicitAny } from './frontend_explicit_any.mjs';

test('comments, strings and property names do not invent types', () => {
  assert.equal(countExplicitAny('a.ts', '// any\n/* eslint no-explicit-any */\nconst text = "any"; const value = {any: 1};'), 0);
});
test('explicit generics, callbacks, assertions and unions count', () => {
  assert.equal(countExplicitAny('a.ts', 'type A = Record<string, any>; type F = (...args: any[]) => any; const x = value as any; type U = string | any;'), 5);
});
test('Vue setup and classic scripts count but style and template text do not', () => {
  assert.equal(countExplicitAny('a.vue', '<script lang="ts">type A = any;</script><script setup lang="ts">const x = null as any;</script><template><div>any</div></template><style>/* any */ .any {color:red}</style>'), 2);
});
test('Vue interpolation and binding type assertions cannot bypass scanning', () => {
  assert.equal(countExplicitAny('a.vue', '<template><div :value="value as any">{{ value as any }}</div></template>'), 2);
});
test('invalid Vue input fails closed', () => {
  assert.throws(() => countExplicitAny('a.vue', '<script>one</script><script>two</script>'), /Cannot parse/);
});

test('migrated baseline only tightens allowances from the immutable original source', () => {
  const path = 'scripts/verify/baselines/frontend_no_new_any.json';
  const baseline = JSON.parse(fs.readFileSync(new URL('./baselines/frontend_no_new_any.json', import.meta.url), 'utf8'));
  const commit = 'ea0170d2652188083146c5423ed9dcbb20a170d7';
  assert.equal(baseline.source_commit, commit);
  assert.equal(baseline.metric, 'typescript-any-keyword-v1');
  const original = JSON.parse(execFileSync('git', ['show', `${commit}:${path}`], { encoding: 'utf8' }));
  assert.deepEqual(Object.keys(baseline.files).sort(), Object.keys(original.files).sort());
  for (const [file, allowance] of Object.entries(original.files)) {
    const actual = allowance === 0 ? 0 : countExplicitAny(file, execFileSync('git', ['show', `${commit}:${file}`], { encoding: 'utf8' }));
    assert.equal(baseline.files[file], Math.min(allowance, actual), file);
  }
  const file = 'frontend/apps/web/src/app/action_runtime/useActionViewActionPresentationRuntime.ts';
  assert.equal(baseline.files[file], 0);
  assert.ok(countExplicitAny(file, '// any\ntype Added = any;') > baseline.files[file]);
});
