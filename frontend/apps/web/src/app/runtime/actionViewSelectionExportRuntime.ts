import { exportActionViewRecords } from './actionViewDataRuntime';

type ColumnOption = {
  name: string;
  label?: string;
  defaultVisible?: boolean;
  valueField?: string;
  exportField?: string;
};

type ExportField = { field: string; label: string };

/**
 * The batch declaration the contract publishes for this surface
 * (`actionContract.surfacePolicies.batch_policy`).  The client reads which
 * actions are available and how each one executes; it never decides either.
 */
export type BatchExecutionDeclaration = {
  /** `execution_intents`: the intent each declared action executes through. */
  intents: Record<string, string>;
  /** `delete_mode`: whether deletion is declared as a hard unlink. */
  deleteMode: string;
  /** `active_field`: the declared active flag an archive/activate writes. */
  activeField: string;
};

/**
 * What this client build can actually run, keyed by the *declared intent*.  This
 * is a client capability table, so it names executors rather than business
 * actions: a contract that declares a new batch action reaches the client
 * through its intent, and one whose intent this build cannot execute is
 * reported unresolved instead of being guessed at or silently dropped.
 */
export const DECLARED_BATCH_EXECUTORS: Record<string, string> = Object.freeze({
  'api.data': 'export_csv',
  'api.data.batch': 'batch_write',
  'api.data.unlink': 'unlink',
});

const BATCH_ACTION_LABELS: Record<string, [string, string]> = Object.freeze({
  export: ['batch_label_export', '导出所选'],
  delete: ['batch_label_delete', '批量删除'],
  activate: ['batch_label_activate', '批量激活'],
  archive: ['batch_label_archive', '批量归档'],
});

/**
 * Turns the declared batch policy into the selection actions this surface may
 * offer.  Every entry the contract declares is kept — hiding one would be the
 * client overruling the contract — and an entry this build cannot execute is
 * offered disabled with the reason it is unresolved.
 */
export function resolveSelectionActions(
  actions: string[],
  declaration: BatchExecutionDeclaration,
  text: (key: string, fallback: string) => string,
) {
  const intents = declaration?.intents || {};
  return actions.map((action) => {
    const intent = String(intents[action] || '').trim();
    const executor = String(DECLARED_BATCH_EXECUTORS[intent] || '').trim();
    const executionDeclared = Boolean(intent && executor);
    const [labelKey, labelFallback] = BATCH_ACTION_LABELS[action] || ['', ''];
    const label = labelKey ? text(labelKey, labelFallback) : action;
    const enabled = executionDeclared
      && (executor === 'export_csv'
        || (executor === 'unlink'
          ? String(declaration.deleteMode || '').trim() === 'unlink'
          : Boolean(String(declaration.activeField || '').trim())));
    return {
      key: `batch:${action}`,
      label,
      enabled,
      hint: enabled
        ? ''
        : executionDeclared
          ? text('batch_hint_unavailable', '当前状态下该操作不可用')
          : text('batch_hint_execution_unresolved', '该批量操作未声明执行方式，暂不可用'),
    };
  });
}

function visibleExportFields(
  columns: string[],
  options: ColumnOption[],
  visibility: Record<string, boolean>,
  labels: Record<string, string>,
): ExportField[] {
  const optionByName = new Map(options.map((option) => [option.name, option]));
  const seenFields = new Set<string>();
  return columns.reduce<ExportField[]>((rows, key) => {
    const option = optionByName.get(key);
    const field = String(option?.exportField || option?.valueField || key).trim();
    const visible = typeof visibility[key] === 'boolean'
      ? visibility[key]
      : option?.defaultVisible !== false;
    if (!visible || !field || field === 'id' || field.includes('@@') || seenFields.has(field)) return rows;
    seenFields.add(field);
    rows.push({ field, label: String(option?.label || labels[key] || labels[field] || field).trim() || field });
    return rows;
  }, []);
}

function downloadBase64(filename: string, mimeType: string, contentB64: string): void {
  if (!contentB64) return;
  const binary = atob(contentB64);
  const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
  const url = URL.createObjectURL(new Blob([bytes], { type: mimeType || 'text/csv' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = filename || 'export.csv';
  link.click();
  URL.revokeObjectURL(url);
}

export async function executeActionViewSelectionExport(options: {
  model: string;
  ids: number[];
  columns: string[];
  columnOptions: ColumnOption[];
  visibility: Record<string, boolean>;
  columnLabels: Record<string, string>;
  context: Record<string, unknown>;
  setBusy: (busy: boolean) => void;
  onSuccess: (count: number) => void;
  onFailure: () => void;
}): Promise<void> {
  options.setBusy(true);
  try {
    const exportFields = visibleExportFields(
      options.columns,
      options.columnOptions,
      options.visibility,
      options.columnLabels,
    );
    const fields = exportFields.map((item) => item.field);
    const result = await exportActionViewRecords({
      model: options.model,
      ids: options.ids,
      fields,
      columnLabels: Object.fromEntries(exportFields.map((item) => [item.field, item.label])),
      context: options.context,
    });
    downloadBase64(result.file_name, result.mime_type, result.content_b64);
    options.onSuccess(Number(result.count || 0));
  } catch {
    options.onFailure();
  } finally {
    options.setBusy(false);
  }
}
