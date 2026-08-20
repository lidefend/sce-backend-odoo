import { exportActionViewRecords } from './actionViewDataRuntime';

type ColumnOption = {
  name: string;
  label?: string;
  defaultVisible?: boolean;
  valueField?: string;
  exportField?: string;
};

type ExportField = { field: string; label: string };

export function resolveSelectionActions(
  actions: string[],
  deleteMode: string,
  activeField: string,
  text: (key: string, fallback: string) => string,
) {
  return actions
    .filter((action) => ['export', 'archive', 'activate', 'delete'].includes(action))
    .map((action) => ({
      key: `batch:${action}`,
      label: action === 'export'
        ? text('batch_label_export', '导出所选')
        : action === 'delete'
          ? text('batch_label_delete', '批量删除')
          : text(action === 'activate' ? 'batch_label_activate' : 'batch_label_archive', action === 'activate' ? '批量激活' : '批量归档'),
      enabled: action === 'export' || (action === 'delete' ? deleteMode === 'unlink' : Boolean(activeField)),
      hint: '',
    }));
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
