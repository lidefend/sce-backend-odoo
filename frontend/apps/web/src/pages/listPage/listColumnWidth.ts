import { resolveLocalizedDisplayValue } from '../../utils/display';

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

type ColumnPriorityInput = {
  field: string;
  label: string;
  type?: string;
  role: ListColumnLayoutRole;
  primary?: boolean;
};

const limits: Record<ListColumnLayoutRole, [number, number]> = {
  identity: [136, 260],
  description: [176, 300],
  relation: [132, 232],
  text: [96, 192],
  status: [80, 120],
  money: [104, 148],
  date: [108, 140],
  actions: [80, 112],
};

export function listColumnAdaptiveFloor(role: ListColumnLayoutRole) {
  const floors: Record<ListColumnLayoutRole, number> = {
    identity: 136, description: 156, relation: 120, text: 96,
    status: 80, money: 104, date: 108, actions: 80,
  };
  return floors[role];
}

export function rankListBusinessColumn(input: ColumnPriorityInput) {
  const name = String(input.field || '').toLowerCase();
  const label = String(input.label || '');
  const type = String(input.type || '').toLowerCase();
  if (input.primary || /登记单号|登记编号/.test(label)) return 0;
  if (/contract.*(_no|number|code)/i.test(name) || /合同编号/.test(label)) return 1;
  if (/contract.*(name|title)/i.test(name) || /合同名称/.test(label)) return 2;
  if (input.role === 'status' || /^(status|state)$/i.test(name)) return 3;
  if (/合同日期/.test(label) || /contract.*date/i.test(name)) return 4;
  if (/合同金额/.test(label) || /^(amount_total|contract_amount)$/i.test(name)) return 5;
  if (/关联项目|项目/.test(label) || /project/i.test(name)) return 6;
  if (type === 'date' || type === 'datetime') return 10;
  if (input.role === 'money' || ['integer', 'float', 'monetary'].includes(type)) return 11;
  if (input.role === 'relation' || ['many2one', 'reference'].includes(type)) return 12;
  if (/((^|_)(name|title|subject)($|_))|名称|主题/i.test(`${name} ${label}`)) return 13;
  return 20;
}

function textWidth(value: unknown) {
  return Array.from(String(value ?? '').trim()).reduce((width, character) => {
    if (/[\u2e80-\u9fff\uff00-\uffef]/u.test(character)) return width + 13;
    if (/[A-Z0-9]/.test(character)) return width + 8;
    if (/\s/.test(character)) return width + 4;
    return width + 7;
  }, 0);
}

function displayValue(value: unknown) {
  const raw = Array.isArray(value) ? (value.length > 1 ? value[1] : value[0]) : value;
  return resolveLocalizedDisplayValue(raw, { emptyText: '' });
}

function percentile(values: number[], ratio: number) {
  if (!values.length) return 0;
  const sorted = [...values].sort((left, right) => left - right);
  return sorted[Math.min(sorted.length - 1, Math.floor((sorted.length - 1) * ratio))] || 0;
}

export function deriveListColumnWidth(input: ColumnWidthInput) {
  const type = String(input.type || '').trim().toLowerCase();
  const [minimum, maximum] = limits[input.role];
  const headerWidth = textWidth(input.label) + 52;
  if (input.role === 'date') {
    return Math.min(maximum, Math.max(minimum, type === 'datetime' ? 140 : 112, headerWidth));
  }
  if (input.role === 'money') return Math.min(maximum, Math.max(minimum, 120, headerWidth));
  if (input.role === 'actions') return Math.min(maximum, Math.max(minimum, headerWidth));

  const candidates = [...(input.values || []).slice(0, 30), ...(input.selectionLabels || [])]
    .map(displayValue)
    .filter((value) => value !== null && value !== undefined && value !== '' && value !== '--')
    .map((value) => textWidth(value) + 24);
  const sampledWidth = percentile(candidates, 0.8);
  const contentWidth = ['identity', 'description', 'relation'].includes(input.role)
    ? Math.ceil(sampledWidth * 0.88)
    : sampledWidth;
  return Math.min(maximum, Math.max(minimum, headerWidth, contentWidth));
}
