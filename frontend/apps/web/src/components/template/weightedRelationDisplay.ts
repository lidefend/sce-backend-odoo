import { contractGapError } from '../../app/contract/contractGap';

export type WeightedRelationRead = (params: {
  model: string; ids: number[]; fields: string[]; context: Record<string, unknown>;
}) => Promise<{ records?: Array<Record<string, unknown>> }>;

function gap(): never {
  throw contractGapError({ kind: 'contract_defect', missing: 'native_widget.weighted_relation',
    requiredDeclarationLayer: 'P0:smart_core:native_widget' }, '结构化关系显示声明或数据无效');
}

export async function weightedRelationDisplay(
  declaration: Record<string, unknown> | undefined,
  value: unknown,
  context: Record<string, unknown> | undefined,
  read: WeightedRelationRead,
): Promise<string> {
  const spec = declaration;
  if (!spec || spec.kind !== 'weighted_relation' || spec.version !== 1 || spec.mode !== 'readonly'
    || spec.key_encoding !== 'csv_ids' || typeof spec.relation_model !== 'string' || !spec.relation_model
    || typeof spec.label_field !== 'string' || !spec.label_field
    || typeof spec.value_unit !== 'string' || !spec.value_unit
    || typeof spec.empty_text !== 'string' || !spec.empty_text || !context) gap();
  if (value === null || value === undefined || value === false) return spec.empty_text as string;
  if (!value || typeof value !== 'object' || Array.isArray(value)) gap();
  const entries = Object.entries(value as Record<string, unknown>).map(([key, weight]) => {
    if (!/^[1-9]\d*(,[1-9]\d*)*$/.test(key) || typeof weight !== 'number' || !Number.isFinite(weight)) gap();
    const ids = key.split(',').map(Number);
    if (ids.some(id => !Number.isSafeInteger(id)) || new Set(ids).size !== ids.length) gap();
    return { ids, weight };
  });
  if (!entries.length) return spec.empty_text as string;
  const ids = [...new Set(entries.flatMap(entry => entry.ids))];
  const field = spec.label_field as string;
  const response = await read({ model: spec.relation_model as string, ids, fields: ['id', field], context });
  const labels = new Map<number, string>();
  for (const row of response.records || []) {
    if (typeof row.id !== 'number' || !ids.includes(row.id) || labels.has(row.id)
      || typeof row[field] !== 'string' || !(row[field] as string).trim()) gap();
    labels.set(row.id, (row[field] as string).trim());
  }
  // Missing or denied accounts never become raw IDs, partial labels, or a false empty state.
  if (labels.size !== ids.length) gap();
  return entries.map(entry => `${entry.ids.map(id => labels.get(id)).join(' / ')}：${entry.weight}${spec.value_unit}`).join('；');
}
