import { strict as assert } from 'node:assert';
import {
  BOQ_IMPORT_PREVIEW_STATE_DEGRADED_SHAPE,
  BOQ_IMPORT_PREVIEW_STATE_ERROR,
  BOQ_IMPORT_PREVIEW_STATE_MISSING_PAYLOAD,
  BOQ_IMPORT_PREVIEW_STATE_READY,
  BOQ_IMPORT_PREVIEW_VIEW_READONLY,
  formatBoqPreviewAmount,
  projectBoqImportPreview,
  resolveBoqBlockProjectId,
  type BoqImportPreviewIntentData,
} from '../src/app/presentation/boqImportPreview';

const READY_RAW: BoqImportPreviewIntentData = {
  ok: true,
  data: {
    batch: {
      id: 12,
      name: 'V2026-09 · 清单导入',
      project_id: 3,
      version_id: 7,
      state: 'done',
      filename: 'boq.xlsx',
      file_digest: 'abc123',
      parser_schema: 'sc.boq.parser.generic',
      row_count: 210,
      item_count: 180,
      skipped_count: 5,
      warning_count: 2,
      imported_at: '2026-09-03T10:00:00',
      imported_by: 2,
      preview_payload: {
        schema: 'sc.boq.import.preview.v1',
        row_count: 210,
        item_count: 180,
        summary_count: 9,
        heading_count: 14,
        calculation_detail_count: 0,
        skipped_count: 5,
        warning_count: 2,
        amount: 1234567.89,
        source_diagnostics: ['第 12 行单位缺失', '', '  ', '第 55 行金额非数字'],
        analysis_count: 6,
        norm_line_count: 40,
        resource_line_count: 52,
        summary_component_count: 9,
      },
    },
    preview_schema: 'sc.boq.import.preview.v1',
    safe_degradation: {
      missing_payload_policy: 'preview_payload 非对象时以空快照降级，前端须可渲染空态',
    },
  },
};

// ── ready 投影 ──────────────────────────────────────────────
const ready = projectBoqImportPreview(READY_RAW);
assert.equal(ready.viewState, BOQ_IMPORT_PREVIEW_STATE_READY);
assert.equal(ready.readonly, BOQ_IMPORT_PREVIEW_VIEW_READONLY);
assert.equal(ready.previewSchema, 'sc.boq.import.preview.v1');
assert.equal(ready.batch?.id, 12);
assert.equal(ready.batch?.name, 'V2026-09 · 清单导入');
assert.equal(ready.batch?.filename, 'boq.xlsx');
assert.equal(ready.batch?.fileDigest, 'abc123');
assert.ok(ready.batch?.importedAtLabel);
assert.equal(ready.errorCode, null);
assert.equal(ready.stateMessage, '');

const statsByKey = new Map(ready.stats.map((stat) => [stat.key, stat]));
assert.equal(statsByKey.get('row_count')?.value, '210');
assert.equal(statsByKey.get('item_count')?.value, '180');
assert.equal(statsByKey.get('skipped_count')?.value, '5');
assert.equal(statsByKey.get('skipped_count')?.emphasis, 'warning');
assert.equal(statsByKey.get('warning_count')?.emphasis, 'warning');
assert.equal(statsByKey.get('amount')?.value, '1,234,567.89');
assert.equal(statsByKey.get('analysis_count')?.value, '6');
assert.equal(statsByKey.get('analysis_count')?.emphasis, 'default');

// 诊断行过滤空串与空白
assert.deepEqual(ready.diagnostics, ['第 12 行单位缺失', '第 55 行金额非数字']);

// ── 直传形状（intentRequest 已解包信封，batch 挂顶层）───────
const directReady = projectBoqImportPreview(READY_RAW.data);
assert.equal(directReady.viewState, BOQ_IMPORT_PREVIEW_STATE_READY);
assert.equal(directReady.batch?.id, 12);
assert.equal(directReady.previewSchema, 'sc.boq.import.preview.v1');
assert.equal(directReady.errorCode, null);
assert.equal(directReady.stateMessage, '');

// 直传形状 batch 缺失 → 防御性降级（不白屏）
const directDegraded = projectBoqImportPreview({ preview_schema: 'sc.boq.import.preview.v1' });
assert.equal(directDegraded.viewState, BOQ_IMPORT_PREVIEW_STATE_DEGRADED_SHAPE);
assert.equal(directDegraded.previewSchema, 'sc.boq.import.preview.v1');

// 调用方 catch 重建形状（fetch 异常路径，ok=false + error）
const fetchFailed = projectBoqImportPreview({
  ok: false,
  error: {
    code: 'BOQ_PREVIEW_FETCH_FAILED',
    message: '网络异常',
    suggested_action: 'retry',
  },
});
assert.equal(fetchFailed.viewState, BOQ_IMPORT_PREVIEW_STATE_ERROR);
assert.equal(fetchFailed.errorCode, 'BOQ_PREVIEW_FETCH_FAILED');

// ── 错误态：BATCH_NOT_FOUND（防枚举语义） ───────────────────
const notFound = projectBoqImportPreview({
  ok: false,
  error: {
    code: 'BATCH_NOT_FOUND',
    message: '未找到可访问的清单导入批次',
    suggested_action: 'check_params',
  },
  data: {},
});
assert.equal(notFound.viewState, BOQ_IMPORT_PREVIEW_STATE_ERROR);
assert.equal(notFound.errorCode, 'BATCH_NOT_FOUND');
assert.equal(notFound.errorMessage, '未找到可访问的清单导入批次');
assert.equal(notFound.suggestedAction, 'check_params');
assert.equal(notFound.batch, null);
assert.deepEqual(notFound.stats, []);

// ── 错误态：MISSING_PARAMS ──────────────────────────────────
const missingParams = projectBoqImportPreview({
  ok: false,
  error: {
    code: 'MISSING_PARAMS',
    message: '缺少参数：batch_id 或 project_id 至少提供一个',
    suggested_action: 'fix_input',
  },
  data: {},
});
assert.equal(missingParams.viewState, BOQ_IMPORT_PREVIEW_STATE_ERROR);
assert.equal(missingParams.errorCode, 'MISSING_PARAMS');
assert.equal(missingParams.suggestedAction, 'fix_input');

// ── 空态：missing_payload（空快照契约语义） ─────────────────
const emptyPayload = projectBoqImportPreview({
  ok: true,
  data: {
    batch: {
      id: 13,
      name: 'V0 · 空批次',
      project_id: 3,
      version_id: 8,
      state: 'done',
      filename: 'empty.xlsx',
      file_digest: 'def456',
      parser_schema: '',
      row_count: 0,
      item_count: 0,
      skipped_count: 0,
      warning_count: 0,
      imported_at: false,
      imported_by: 2,
      preview_payload: {},
    },
    preview_schema: 'sc.boq.import.preview.v1',
  },
});
assert.equal(emptyPayload.viewState, BOQ_IMPORT_PREVIEW_STATE_MISSING_PAYLOAD);
assert.equal(emptyPayload.batch?.id, 13);
assert.equal(emptyPayload.errorCode, null);
assert.ok(emptyPayload.stateMessage.includes('预检快照'));
assert.deepEqual(emptyPayload.stats, []);

// preview_payload 缺失（后端已降级为空快照）同样进入空态
const noPayloadKey = projectBoqImportPreview({
  ok: true,
  data: {
    batch: {
      id: 14,
      name: 'V0 · 无快照键',
      project_id: 3,
      version_id: 9,
      state: 'done',
      filename: 'x.xlsx',
      file_digest: '',
      parser_schema: '',
      row_count: 0,
      item_count: 0,
      skipped_count: 0,
      warning_count: 0,
      imported_at: false,
      imported_by: 2,
      preview_payload: {},
    },
  },
});
assert.equal(noPayloadKey.viewState, BOQ_IMPORT_PREVIEW_STATE_MISSING_PAYLOAD);

// ── 防御性降级：ok=true 但 batch 形状异常 ───────────────────
const degraded = projectBoqImportPreview({ ok: true, data: {} });
assert.equal(degraded.viewState, BOQ_IMPORT_PREVIEW_STATE_DEGRADED_SHAPE);
assert.equal(degraded.errorCode, 'BOQ_PREVIEW_DEGRADED_SHAPE');
assert.equal(degraded.batch, null);

const degradedNoId = projectBoqImportPreview({
  ok: true,
  data: { batch: { name: '缺 id' } as never },
});
assert.equal(degradedNoId.viewState, BOQ_IMPORT_PREVIEW_STATE_DEGRADED_SHAPE);

// ── 防御：raw 为 null / 畸形 ───────────────────────────────
const nullRaw = projectBoqImportPreview(null);
assert.equal(nullRaw.viewState, BOQ_IMPORT_PREVIEW_STATE_ERROR);
assert.equal(nullRaw.errorCode, 'BOQ_PREVIEW_UNAVAILABLE');

const malformed = projectBoqImportPreview({ ok: true } as BoqImportPreviewIntentData);
assert.equal(malformed.viewState, BOQ_IMPORT_PREVIEW_STATE_DEGRADED_SHAPE);

// ok=false 且 error 缺失 → 兜底错误
const noError = projectBoqImportPreview({ ok: false, data: {} });
assert.equal(noError.viewState, BOQ_IMPORT_PREVIEW_STATE_ERROR);
assert.equal(noError.errorCode, 'BOQ_PREVIEW_UNAVAILABLE');
assert.ok(noError.errorMessage.length > 0);

// ── 金额格式化 ──────────────────────────────────────────────
assert.equal(formatBoqPreviewAmount(0), '0');
assert.equal(formatBoqPreviewAmount(1234.5), '1,234.5');
assert.equal(formatBoqPreviewAmount(null), '—');
assert.equal(formatBoqPreviewAmount(undefined), '—');
assert.equal(formatBoqPreviewAmount(Number.NaN), '—');

// ── 非数字计数的字符串容错 ──────────────────────────────────
const stringyCounts = projectBoqImportPreview({
  ok: true,
  data: {
    batch: {
      id: 15,
      name: '字符串计数',
      project_id: 3,
      version_id: 10,
      state: 'done',
      filename: 's.xlsx',
      file_digest: '',
      parser_schema: '',
      row_count: '42',
      item_count: '40',
      skipped_count: 0,
      warning_count: 0,
      imported_at: 'not-a-date',
      imported_by: 2,
      preview_payload: { row_count: '42', item_count: '40' },
    },
  },
});
assert.equal(stringyCounts.viewState, BOQ_IMPORT_PREVIEW_STATE_READY);
const stringyStats = new Map(stringyCounts.stats.map((stat) => [stat.key, stat]));
assert.equal(stringyStats.get('row_count')?.value, '42');
assert.equal(stringyStats.get('item_count')?.value, '40');
// 非法日期原样透传，不产生 null 崩溃
assert.equal(stringyCounts.batch?.importedAtLabel, 'not-a-date');

// ── resolveBoqBlockProjectId：驾驶舱块项目上下文解析（G3.3）──
// dataset 投影（builder data.project_id）优先
assert.equal(resolveBoqBlockProjectId({ data: { project_id: 7 } }, null), 7);
// dataset 顶层 project_id 兜底
assert.equal(resolveBoqBlockProjectId({ project_id: 9 }, {}), 9);
// dataset 缺失时回落路由 query
assert.equal(resolveBoqBlockProjectId(null, { project_id: '12' }), 12);
assert.equal(resolveBoqBlockProjectId({}, { project_id: 15 }), 15);
// 两者均缺失 → 0（无项目上下文空态）
assert.equal(resolveBoqBlockProjectId(null, {}), 0);
assert.equal(resolveBoqBlockProjectId(undefined, undefined), 0);
// dataset 优先级高于路由
assert.equal(resolveBoqBlockProjectId({ data: { project_id: 3 } }, { project_id: 99 }), 3);
// 非法值防御：0/负数/NaN/对象
assert.equal(resolveBoqBlockProjectId({ data: { project_id: 0 } }, { project_id: 0 }), 0);
assert.equal(resolveBoqBlockProjectId({ data: { project_id: -5 } }, { project_id: -1 }), 0);
assert.equal(resolveBoqBlockProjectId({ data: { project_id: 'abc' } }, { project_id: {} }), 0);
// 浮点截断
assert.equal(resolveBoqBlockProjectId({ data: { project_id: 3.7 } }, null), 3);
// dataset 非对象防御
assert.equal(resolveBoqBlockProjectId('nope', { project_id: 4 }), 4);
assert.equal(resolveBoqBlockProjectId([], { project_id: 4 }), 4);

console.info('[boq-import-preview-model-test] all assertions passed');
