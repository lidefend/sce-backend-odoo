export type ListColumnLayoutRole =
  | 'identity'
  | 'description'
  | 'relation'
  | 'text'
  | 'status'
  | 'money'
  | 'date'
  | 'actions';

type ColumnWidthInput = {
  label: string;
  type?: string;
  role: ListColumnLayoutRole;
  values?: unknown[];
  selectionLabels?: string[];
};

const limits: Record<ListColumnLayoutRole, [number, number]> = {
  identity: [220, 320],
  description: [200, 320],
  relation: [160, 260],
  text: [112, 220],
  status: [88, 144],
  money: [112, 160],
  date: [112, 160],
  actions: [88, 120],
};

function textWidth(value: unknown) {
  return Array.from(String(value ?? '').trim()).reduce((width, character) => {
    if (/[\u2e80-\u9fff\uff00-\uffef]/u.test(character)) return width + 13;
    if (/[A-Z0-9]/.test(character)) return width + 8;
    if (/\s/.test(character)) return width + 4;
    return width + 7;
  }, 0);
}

function displayValue(value: unknown) {
  if (Array.isArray(value)) return value.length > 1 ? value[1] : value[0];
  return value;
}

function percentile(values: number[], ratio: number) {
  if (!values.length) return 0;
  const sorted = [...values].sort((left, right) => left - right);
  return sorted[Math.min(sorted.length - 1, Math.floor((sorted.length - 1) * ratio))] || 0;
}

export function deriveListColumnWidth(input: ColumnWidthInput) {
  const type = String(input.type || '').trim().toLowerCase();
  const [minimum, maximum] = limits[input.role];
  const headerWidth = textWidth(input.label) + 68;
  if (input.role === 'date') {
    return Math.min(maximum, Math.max(minimum, type === 'datetime' ? 152 : 120, headerWidth));
  }
  if (input.role === 'money') return Math.min(maximum, Math.max(minimum, 132, headerWidth));
  if (input.role === 'actions') return Math.min(maximum, Math.max(minimum, headerWidth));

  const candidates = [...(input.values || []).slice(0, 30), ...(input.selectionLabels || [])]
    .map(displayValue)
    .filter((value) => value !== null && value !== undefined && value !== '' && value !== '--')
    .map((value) => textWidth(value) + 24);
  const sampledWidth = percentile(candidates, 0.8);
  const contentWidth = ['identity', 'description', 'relation'].includes(input.role)
    ? Math.ceil(sampledWidth * 0.78)
    : sampledWidth;
  return Math.min(maximum, Math.max(minimum, headerWidth, contentWidth));
}
