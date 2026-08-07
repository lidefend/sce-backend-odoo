export type ProjectionMetricItem = {
  key: string;
  label: string;
  value: string;
  tone: string;
};

export function mapProjectionMetricItems(rowsRaw: unknown, keyPrefix: string): ProjectionMetricItem[] {
  const rows = Array.isArray(rowsRaw) ? (rowsRaw as Array<Record<string, unknown>>) : [];
  return rows
    .map((row, index) => ({
      key: String(row.key || `${keyPrefix}_${index + 1}`),
      label: String(row.label || row.key || ''),
      value: String(row.value ?? ''),
      tone: String(row.tone || 'neutral'),
    }))
    .filter((item) => item.label);
}
