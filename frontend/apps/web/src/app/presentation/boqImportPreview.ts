/**
 * BOQ 导入批次只读预检快照投影 Model（G3.2）。
 *
 * 数据契约：contracts/domain/boq.yaml v1（只读域，safe_degradation 语义）。
 * 消费 intent：project.boq.import.preview.fetch（只读，MACHINE_ACCESS=read）。
 *
 * 视图状态机：
 *  - ready           ：快照齐备，投影统计卡与诊断行
 *  - missing_payload ：ok=true 但 preview_payload 为空快照（后端降级语义），
 *                      渲染空态，不白屏
 *  - error           ：ok=false（MISSING_PARAMS / BATCH_NOT_FOUND），
 *                      透传结构化错误与 suggested_action
 *  - degraded_shape  ：ok=true 但 batch 序列化形状异常，防御性降级
 *
 * 只读投影边界：本 Model 不产生任何写 intent；导入入口沿用既有向导
 * （digest 绑定 + [SC_GUARD:*] 错误透传），不在此复制。
 */
import type {
  BoqImportPreviewBatch,
  BoqImportPreviewIntentData,
  BoqImportPreviewPayload,
} from '../../api/boqImportPreview';

export const BOQ_IMPORT_PREVIEW_VIEW_READONLY = true;
export const BOQ_IMPORT_PREVIEW_STATE_READY = 'ready';
export const BOQ_IMPORT_PREVIEW_STATE_MISSING_PAYLOAD = 'missing_payload';
export const BOQ_IMPORT_PREVIEW_STATE_ERROR = 'error';
export const BOQ_IMPORT_PREVIEW_STATE_DEGRADED_SHAPE = 'degraded_shape';

export const BOQ_IMPORT_PREVIEW_MISSING_PAYLOAD_MESSAGE =
  '该导入批次没有可展示的预检快照（快照缺失或类型异常），可重新导入生成快照。';
export const BOQ_IMPORT_PREVIEW_DEGRADED_SHAPE_MESSAGE =
  '导入批次数据形状异常，已降级为只读摘要展示。';

export type BoqPreviewViewState =
  | typeof BOQ_IMPORT_PREVIEW_STATE_READY
  | typeof BOQ_IMPORT_PREVIEW_STATE_MISSING_PAYLOAD
  | typeof BOQ_IMPORT_PREVIEW_STATE_ERROR
  | typeof BOQ_IMPORT_PREVIEW_STATE_DEGRADED_SHAPE;

export type BoqPreviewStatCard = {
  key: string;
  label: string;
  value: string;
  emphasis: 'default' | 'warning' | 'danger';
};

export type BoqPreviewBatchSummary = {
  id: number;
  name: string;
  state: string;
  filename: string;
  fileDigest: string;
  importedAtLabel: string | null;
};

export type BoqImportPreviewViewModel = {
  viewState: BoqPreviewViewState;
  readonly: typeof BOQ_IMPORT_PREVIEW_VIEW_READONLY;
  previewSchema: string;
  batch: BoqPreviewBatchSummary | null;
  stats: BoqPreviewStatCard[];
  diagnostics: string[];
  errorCode: string | null;
  errorMessage: string | null;
  suggestedAction: string | null;
  stateMessage: string;
};

function toNumber(value: unknown): number {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return 0;
}

function toText(value: unknown): string {
  return typeof value === 'string' ? value : '';
}

/** 金额千分位格式化（无货币断言，展示层仅做分组） */
export function formatBoqPreviewAmount(value: number | null | undefined): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '—';
  return value.toLocaleString('zh-CN', { maximumFractionDigits: 2 });
}

function formatImportedAt(value: unknown): string | null {
  if (typeof value !== 'string' || !value.trim()) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString('zh-CN', { hour12: false });
}

function normalizePreviewPayload(raw: unknown): BoqImportPreviewPayload {
  if (raw && typeof raw === 'object' && !Array.isArray(raw)) {
    return raw as BoqImportPreviewPayload;
  }
  return {};
}

function normalizeBatch(raw: unknown): BoqImportPreviewBatch | null {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
  const record = raw as Record<string, unknown>;
  if (toNumber(record.id) <= 0) return null;
  return {
    id: toNumber(record.id),
    name: toText(record.name),
    project_id: typeof record.project_id === 'number' ? record.project_id : false,
    version_id: typeof record.version_id === 'number' ? record.version_id : false,
    state: toText(record.state),
    filename: toText(record.filename),
    file_digest: toText(record.file_digest),
    parser_schema: toText(record.parser_schema),
    row_count: toNumber(record.row_count),
    item_count: toNumber(record.item_count),
    skipped_count: toNumber(record.skipped_count),
    warning_count: toNumber(record.warning_count),
    imported_at:
      typeof record.imported_at === 'string' && record.imported_at ? record.imported_at : false,
    imported_by: typeof record.imported_by === 'number' ? record.imported_by : false,
    preview_payload: normalizePreviewPayload(record.preview_payload),
  };
}

function hasSnapshotContent(payload: BoqImportPreviewPayload): boolean {
  const keys = [
    'row_count',
    'item_count',
    'summary_count',
    'heading_count',
    'calculation_detail_count',
    'skipped_count',
    'warning_count',
    'analysis_count',
    'norm_line_count',
    'resource_line_count',
    'summary_component_count',
  ] as const;
  return keys.some((key) => toNumber(payload[key]) > 0) || Boolean(payload.amount);
}

function buildStats(payload: BoqImportPreviewPayload): BoqPreviewStatCard[] {
  const skipped = toNumber(payload.skipped_count);
  const warnings = toNumber(payload.warning_count);
  const stats: BoqPreviewStatCard[] = [
    {
      key: 'row_count',
      label: '解析总行数',
      value: String(toNumber(payload.row_count)),
      emphasis: 'default',
    },
    {
      key: 'item_count',
      label: '明细项',
      value: String(toNumber(payload.item_count)),
      emphasis: 'default',
    },
    {
      key: 'skipped_count',
      label: '跳过行',
      value: String(skipped),
      emphasis: skipped > 0 ? 'warning' : 'default',
    },
    {
      key: 'warning_count',
      label: '警告行',
      value: String(warnings),
      emphasis: warnings > 0 ? 'warning' : 'default',
    },
    {
      key: 'amount',
      label: '清单金额',
      value: formatBoqPreviewAmount(payload.amount ?? null),
      emphasis: 'default',
    },
  ];
  const analysisCount = toNumber(payload.analysis_count);
  if (analysisCount > 0) {
    stats.push({
      key: 'analysis_count',
      label: '综合单价分析',
      value: String(analysisCount),
      emphasis: 'default',
    });
  }
  return stats;
}

function buildDiagnostics(payload: BoqImportPreviewPayload): string[] {
  const raw = payload.source_diagnostics;
  if (!Array.isArray(raw)) return [];
  return raw
    .filter((line): line is string => typeof line === 'string')
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
}

function errorViewModel(
  raw: BoqImportPreviewIntentData | null | undefined,
  fallbackMessage: string,
): BoqImportPreviewViewModel {
  const error = raw?.error;
  return {
    viewState: BOQ_IMPORT_PREVIEW_STATE_ERROR,
    readonly: BOQ_IMPORT_PREVIEW_VIEW_READONLY,
    previewSchema: 'sc.boq.import.preview.v1',
    batch: null,
    stats: [],
    diagnostics: [],
    errorCode: toText(error?.code) || 'BOQ_PREVIEW_UNAVAILABLE',
    errorMessage: toText(error?.message) || fallbackMessage,
    suggestedAction: toText(error?.suggested_action) || null,
    stateMessage: toText(error?.message) || fallbackMessage,
  };
}

/**
 * 将 intent 结构化返回投影为只读视图模型。
 * 纯函数：无网络/会话依赖，可被 esbuild 单测直接覆盖。
 */
export function projectBoqImportPreview(
  raw: BoqImportPreviewIntentData | null | undefined,
): BoqImportPreviewViewModel {
  if (!raw || typeof raw !== 'object' || !raw.ok) {
    return errorViewModel(raw, '未能获取清单导入批次预检快照。');
  }

  const batch = normalizeBatch(raw.data?.batch);
  if (!batch) {
    // ok=true 但 batch 形状异常：防御性降级，不白屏。
    return {
      viewState: BOQ_IMPORT_PREVIEW_STATE_DEGRADED_SHAPE,
      readonly: BOQ_IMPORT_PREVIEW_VIEW_READONLY,
      previewSchema: toText(raw.data?.preview_schema) || 'sc.boq.import.preview.v1',
      batch: null,
      stats: [],
      diagnostics: [],
      errorCode: 'BOQ_PREVIEW_DEGRADED_SHAPE',
      errorMessage: BOQ_IMPORT_PREVIEW_DEGRADED_SHAPE_MESSAGE,
      suggestedAction: 'retry',
      stateMessage: BOQ_IMPORT_PREVIEW_DEGRADED_SHAPE_MESSAGE,
    };
  }

  const payload = batch.preview_payload;
  if (!hasSnapshotContent(payload)) {
    // 契约 safe_degradation.missing_payload：空快照空态渲染。
    return {
      viewState: BOQ_IMPORT_PREVIEW_STATE_MISSING_PAYLOAD,
      readonly: BOQ_IMPORT_PREVIEW_VIEW_READONLY,
      previewSchema: toText(raw.data?.preview_schema) || 'sc.boq.import.preview.v1',
      batch: {
        id: batch.id,
        name: batch.name,
        state: batch.state,
        filename: batch.filename,
        fileDigest: batch.file_digest,
        importedAtLabel: formatImportedAt(batch.imported_at),
      },
      stats: [],
      diagnostics: [],
      errorCode: null,
      errorMessage: null,
      suggestedAction: null,
      stateMessage: BOQ_IMPORT_PREVIEW_MISSING_PAYLOAD_MESSAGE,
    };
  }

  return {
    viewState: BOQ_IMPORT_PREVIEW_STATE_READY,
    readonly: BOQ_IMPORT_PREVIEW_VIEW_READONLY,
    previewSchema: toText(raw.data?.preview_schema) || 'sc.boq.import.preview.v1',
    batch: {
      id: batch.id,
      name: batch.name,
      state: batch.state,
      filename: batch.filename,
      fileDigest: batch.file_digest,
      importedAtLabel: formatImportedAt(batch.imported_at),
    },
    stats: buildStats(payload),
    diagnostics: buildDiagnostics(payload),
    errorCode: null,
    errorMessage: null,
    suggestedAction: null,
    stateMessage: '',
  };
}
