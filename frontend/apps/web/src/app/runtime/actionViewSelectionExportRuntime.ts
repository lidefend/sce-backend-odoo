import { exportActionViewRecords } from './actionViewDataRuntime';

type ColumnOption = { name: string; defaultVisible?: boolean };

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

function visibleExportFields(columns: string[], options: ColumnOption[], visibility: Record<string, boolean>): string[] {
  const optionByName = new Map(options.map((option) => [option.name, option]));
  return columns.filter((field, index, rows) => {
    if (!field || field === 'id' || rows.indexOf(field) !== index) return false;
    if (typeof visibility[field] === 'boolean') return visibility[field];
    return optionByName.get(field)?.defaultVisible !== false;
  });
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
    const fields = visibleExportFields(options.columns, options.columnOptions, options.visibility);
    const result = await exportActionViewRecords({
      model: options.model,
      ids: options.ids,
      fields,
      columnLabels: Object.fromEntries(fields.map((field) => [field, options.columnLabels[field] || field])),
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
