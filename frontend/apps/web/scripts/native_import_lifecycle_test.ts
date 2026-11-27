import { strict as assert } from 'node:assert';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { createNativeImportRequestOwner } from '../src/app/action_runtime/nativeImportLifecycle';

let epoch = 3;
const controllers: AbortController[] = [];
const owner = createNativeImportRequestOwner({
  currentEpoch: () => epoch,
  isCurrentEpoch: (candidate) => candidate === epoch,
  createAbortController: () => {
    const controller = new AbortController();
    controllers.push(controller);
    return controller;
  },
});

const first = owner.begin('project.project:company:1');
assert.equal(owner.isCurrent(first), true);
assert.equal(first.epoch, 3);

const second = owner.begin('project.project:company:1');
assert.equal(owner.isCurrent(first), false, 'a superseded request ticket must be stale');
assert.equal(controllers[0]?.signal.aborted, true, 'a superseded request must abort');
assert.equal(controllers[0]?.signal.reason, 'superseded');
assert.equal(owner.isCurrent(second), true);

owner.invalidate('closed');
assert.equal(owner.isCurrent(second), false, 'closing must invalidate the active ticket');
assert.equal(controllers[1]?.signal.aborted, true);
assert.equal(controllers[1]?.signal.reason, 'closed');

let lateMutation = '';
const lateTicket = owner.begin('project.project:company:1');
const lateResult = Promise.resolve('stale inspect result').then((value) => {
  if (owner.isCurrent(lateTicket)) lateMutation = value;
});
owner.invalidate('closed');
await lateResult;
assert.equal(lateMutation, '', 'a late result from an invalidated import chain must not mutate UI state');

const third = owner.begin('project.project:company:1');
epoch += 1;
assert.equal(
  owner.isCurrent(third),
  false,
  'a company/context epoch change must make an old callback stale even before its late promise settles',
);

const fourth = owner.begin('project.project:company:2');
owner.dispose();
assert.equal(owner.isCurrent(fourth), false, 'unmount must invalidate the active ticket');
assert.equal(controllers.at(-1)?.signal.aborted, true);
assert.equal(controllers.at(-1)?.signal.reason, 'unmounted');
assert.throws(() => owner.begin('project.project:company:2'), /disposed/);

const wizard = readFileSync(
  resolve(process.cwd(), 'frontend/apps/web/src/components/business/NativeImportWizard.vue'),
  'utf8',
);
for (const expected of [
  'createNativeImportRequestOwner',
  'onBeforeUnmount',
  'onContextEpochChange',
  'lifecycle.isCurrent(token)',
  'signal: token.signal',
  'executing.value',
]) {
  assert.ok(wizard.includes(expected), `wizard lifecycle wiring must retain ${expected}`);
}

const dataApi = readFileSync(resolve(process.cwd(), 'frontend/apps/web/src/api/data.ts'), 'utf8');
assert.ok(
  dataApi.includes('signal?: AbortSignal') && dataApi.includes('{ signal: params.signal }'),
  'record import/export requests must forward the lifecycle abort signal',
);
const capabilityRuntime = readFileSync(
  resolve(process.cwd(), 'frontend/apps/web/src/app/runtime/actionViewCollectionCapabilityRuntime.ts'),
  'utf8',
);
for (const removedFlow of ['pickImportFile', 'executeActionViewCollectionImport', 'CollectionImportSummary']) {
  assert.equal(
    capabilityRuntime.includes(removedFlow),
    false,
    `the obsolete direct import flow must not remain: ${removedFlow}`,
  );
}

console.info('[native-import-lifecycle-test] PASS lifecycle owner, wizard wiring and old-flow removal');
