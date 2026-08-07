import { resolveLocalizedDisplayValue } from '../../utils/display.ts';

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
  money: [128, 148],
  date: [108, 140],
  actions: [80, 112],
};

export function listColumnAdaptiveFloor(role: ListColumnLayoutRole) {
  const floors: Record<ListColumnLayoutRole, number> = {
    identity: 136, description: 176, relation: 120, text: 96,
    status: 80, money: 128, date: 108, actions: 80,
  };
  return floors[role];
}

export function resolveListColumnBudgetWidth(input: {
  customWidth?: number;
  derivedWidth: number;
  role: ListColumnLayoutRole;
}) {
  const customWidth = Number(input.customWidth || 0);
  if (Number.isFinite(customWidth) && customWidth > 0) return customWidth;
  return Math.max(listColumnAdaptiveFloor(input.role), Number(input.derivedWidth || 0));
}

export function rankListBusinessColumn(input: ColumnPriorityInput) {
  if (input.primary) return 0;
  const roleOrder: Record<ListColumnLayoutRole, number> = {
    identity: 10,
    status: 20,
    date: 30,
    money: 40,
    relation: 50,
    description: 60,
    text: 70,
    actions: 80,
  };
  return roleOrder[input.role];
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
  if (input.role === 'money') return Math.min(maximum, Math.max(minimum, 128, headerWidth));
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
