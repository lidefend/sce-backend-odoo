import assert from 'node:assert/strict';
import { effectScope, ref } from 'vue';
import { ApiError } from '../src/api/client';
import { useActionViewSelectionActionRuntime } from '../src/app/action_runtime/useActionViewSelectionActionRuntime';

import test from 'node:test';

test('action_view_selection_feedback_test', async () => {
  const failure = new ApiError('导出服务暂时不可用，请稍后重试', 500, 'trace-export-500', {
    reasonCode: 'EXPORT_SERVICE_UNAVAILABLE',
    retryable: true,
  });
  const batchBusy = ref(false);
  const batchMessage = ref('');
  let exportCalls = 0;
  let releaseExport!: () => void;
  const released = new Promise<void>((resolve) => { releaseExport = resolve; });

  const scope = effectScope();
  const runtime = scope.run(() => useActionViewSelectionActionRuntime({
    capabilities: ref({ enabled: true, actions: [] }),
    allowedBatchActions: ref(['export']),
    batchPolicy: ref({ available_actions: ['export'] }),
    activeField: ref(''),
    selectedIds: ref([1]),
    batchBusy,
    batchMessage,
    batchConfirmationRef: ref(null),
    columns: ref(['name']),
    listColumnOptions: ref([{ name: 'name', label: '名称', defaultVisible: true }]),
    listColumnVisibility: ref({}),
    contractColumnLabels: ref({ name: '名称' }),
    contractActions: ref([]),
    text: (_key, fallback) => fallback,
    resolveTargetModel: () => 'project.project',
    resolveEffectiveRequestContext: () => ({}),
    buildIfMatchMap: () => ({}),
    buildIdempotencyKey: () => 'export-key',
    clearSelection: () => {},
    reload: async () => undefined,
    runDeclaredAction: () => {},
    executeExport: async (options) => {
      exportCalls += 1;
      options.setBusy(true);
      await released;
      options.onFailure(failure);
      options.setBusy(false);
    },
  }));
  assert.ok(runtime);

  runtime.handleSelectionAction('batch:export');
  runtime.handleSelectionAction('batch:export');
  assert.equal(exportCalls, 1, 'an in-flight export cannot be submitted twice');
  releaseExport();
  await released;
  await Promise.resolve();
  await Promise.resolve();

  assert.equal(batchBusy.value, false, 'export failure releases the busy state for retry');
  assert.match(batchMessage.value, /导出服务暂时不可用/);
  assert.match(batchMessage.value, /EXPORT_SERVICE_UNAVAILABLE/);
  assert.match(batchMessage.value, /trace-export-500/);
  assert.match(batchMessage.value, /原因：EXPORT_SERVICE_UNAVAILABLE/);
  assert.match(batchMessage.value, /追踪 ID：trace-export-500/);
});
