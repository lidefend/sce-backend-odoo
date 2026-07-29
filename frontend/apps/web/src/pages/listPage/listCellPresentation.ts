export type ListStatusTone = 'neutral' | 'info' | 'success' | 'warning' | 'danger';

export type ColumnSemanticInput = {
  field: string;
  label: string;
  type?: string;
  cellRole?: string;
};

type CellPresentationInput = {
  raw: unknown;
  column: ColumnSemanticInput;
  selectionText?: string;
  numericText?: string;
  attachmentText?: string;
  emptyText?: string;
  trueText?: string;
  falseText?: string;
  numeric?: boolean;
  toneByValue?: Record<string, ListStatusTone | string>;
};

function normalized(input: unknown) {
  return String(input ?? '').trim();
}

export function isListTemporalColumn(input: ColumnSemanticInput) {
  const type = normalized(input.type).toLowerCase();
  const role = normalized(input.cellRole).toLowerCase();
  const field = normalized(input.field).toLowerCase();
  const label = normalized(input.label);
  return ['date', 'datetime'].includes(type)
    || ['date', 'datetime'].includes(role)
    || /(?:^|_)(?:date|datetime|time|at)(?:_|$)/.test(field)
    || /(?:日期|时间)$/.test(label);
}

export function formatListTemporalValue(value: unknown, input: ColumnSemanticInput) {
  const text = normalized(value);
  if (!text || !isListTemporalColumn(input)) return '';
  const match = text.match(/^(\d{4}-\d{2}-\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?)?(?:Z|[+-]\d{2}:?\d{2})?$/);
  if (!match) return '';
  const [, date, hour = '00', minute = '00', second = '00'] = match;
  if (`${hour}:${minute}:${second}` === '00:00:00') return date;
  return `${date} ${hour}:${minute}`;
}

export function isListStatusColumn(input: ColumnSemanticInput) {
  const role = normalized(input.cellRole).toLowerCase();
  const field = normalized(input.field).toLowerCase();
  const label = normalized(input.label);
  return role === 'status'
    || /(?:^|_)(?:status|state)(?:_|$)/.test(field)
    || /(?:状态|审批结果)$/.test(label);
}

export function resolveListStatusTone(value: unknown, label: unknown): ListStatusTone {
  const text = `${normalized(value)} ${normalized(label)}`.toLowerCase();
  if (/(?:驳回|拒绝|退回|失败|异常|reject|denied|fail|error)/.test(text)) return 'danger';
  if (/(?:待审|待批|审批中|审核中|待提交|已提交|submit|pending|waiting|review)/.test(text)) return 'warning';
  if (/(?:审核通过|审批通过|已批准|已完成|已生效|通过|完成|approved|validated|success|done)/.test(text)) return 'success';
  if (/(?:处理中|执行中|进行中|running|progress|processing)/.test(text)) return 'info';
  return 'neutral';
}

export function isListBusinessIdentifierColumn(input: ColumnSemanticInput) {
  const role = normalized(input.cellRole).toLowerCase();
  const field = normalized(input.field).toLowerCase();
  const label = normalized(input.label);
  if (role === 'identity') return true;
  return /(?:^|_)(?:document_no|number|code|name)(?:_|$)/.test(field)
    || /(?:单据|合同|项目|申请|结算|发票|订单|计划).*(?:编号|单号)$/.test(label);
}

export function presentListCell(input: CellPresentationInput) {
  const {
    raw,
    column,
    selectionText = '',
    numericText = '',
    attachmentText = '',
    emptyText = '--',
    trueText = '是',
    falseText = '否',
    numeric = false,
    toneByValue = {},
  } = input;
  const temporalText = formatListTemporalValue(raw, column);
  const fieldType = normalized(column.type).toLowerCase();
  const rawText = typeof raw === 'string' ? raw : '';
  const missing = raw === null || raw === undefined || raw === '';
  let text: string;
  if (selectionText) text = selectionText;
  else if (missing) text = numeric ? '0' : emptyText;
  else if ((raw === false || rawText.trim() === '--') && numeric) text = '0';
  else if (typeof raw === 'boolean') text = fieldType === 'boolean' ? (raw ? trueText : falseText) : emptyText;
  else text = attachmentText || temporalText || numericText || String(raw);
  const toneKey = normalized(raw);
  const tone = isListStatusColumn(column)
    ? (toneByValue[toneKey] || resolveListStatusTone(toneKey, text))
    : 'neutral';
  return { text, tone };
}
