import type { WorkspaceHomeObjectRow } from './sessionWorkspaceTypes';

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? value as Record<string, unknown> : {};
}

function asText(value: unknown): string {
  return String(value ?? '').trim();
}

export function projectWorkspaceHomeObjectRows(source: unknown[]): WorkspaceHomeObjectRow[] {
  return source.map((item, index) => {
    const row = asRecord(item);
    return {
      id: asText(row.id) || `home-object-${index + 1}`,
      key: asText(row.key) || asText(row.id) || `home-object-${index + 1}`,
      kind: asText(row.kind),
      kindLabel: asText(row.kind_label),
      title: asText(row.title),
      subtitle: asText(row.subtitle),
      state: asText(row.state),
      stateLabel: asText(row.state_label),
      amount: Number(row.amount || 0),
      amountDisplay: asText(row.amount_display),
      model: asText(row.model),
      recordId: Number(row.record_id || 0),
      route: asText(row.route),
      reason: asText(row.reason),
      authority: asText(row.authority),
    };
  }).filter((row) => Boolean(row.title));
}
