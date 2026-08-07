type Dict = Record<string, unknown>;

export function buildCollectionRouteQuery(current: Dict, patch: {
  viewMode?: string;
  listOffset?: number;
}): Dict {
  const next = { ...current };
  if (patch.viewMode) next.view_mode = patch.viewMode;
  if (typeof patch.listOffset === 'number' && patch.listOffset > 0) {
    next.list_offset = String(Math.trunc(patch.listOffset));
  } else if (typeof patch.listOffset === 'number') {
    delete next.list_offset;
  }
  return next;
}

export function groupCollectionRecords(records: Dict[], groupField: string): Array<{
  key: string;
  label: string;
  records: Dict[];
}> {
  if (!groupField) return [{ key: 'cards', label: '', records }];
  const lanes = new Map<string, { key: string; label: string; records: Dict[] }>();
  records.forEach((row) => {
    const raw = row[groupField];
    const key = Array.isArray(raw) ? String(raw[0] ?? '') : String(raw ?? '');
    const label = Array.isArray(raw) ? String(raw[1] ?? raw[0] ?? '') : String(raw ?? '');
    const laneKey = key || '__unset__';
    if (!lanes.has(laneKey)) lanes.set(laneKey, { key: laneKey, label: label || '未设置', records: [] });
    lanes.get(laneKey)?.records.push(row);
  });
  return Array.from(lanes.values());
}

export function resolveResponsiveCollectionPresentation(input: {
  explicitMode: string;
  compactViewport: boolean;
}): 'responsive_table_card' | 'explicit_card' | 'workflow_board' | 'table' {
  if (input.explicitMode === 'workflow_board') return 'workflow_board';
  if (input.explicitMode === 'card') return 'explicit_card';
  return input.compactViewport ? 'responsive_table_card' : 'table';
}
