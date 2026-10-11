import { extractX2ManyIds } from '../../app/x2manyCommands';
import type { FieldDescriptor } from '@sc/schema';
import { layoutGridUnits } from '../../components/template/layoutSpan';
import type { LowCodeFieldSize, RelationOption } from './types';

export function normalizeLowCodeColumns(value: unknown, fallback: 1 | 2 | 3 = 2): 1 | 2 | 3 {
  const columns = Number(value);
  if (columns === 1 || columns === 2 || columns === 3) return columns;
  return fallback;
}

export function normalizeLowCodeColumnsOrNull(value: unknown): 1 | 2 | 3 | null {
  const columns = Number(value);
  return columns === 1 || columns === 2 || columns === 3 ? columns : null;
}

export function normalizeLowCodeFieldSize(value: unknown): LowCodeFieldSize {
  const normalized = String(value || '').trim().toLowerCase();
  if (['compact', 'wide', 'full', 'large'].includes(normalized)) return normalized as LowCodeFieldSize;
  return 'normal';
}

/**
 * The declared low-code size facets in the renderer's one unit.  It mirrors the
 * projection's ``LAYOUT_FIELD_SIZE_UNITS``: one declaration, one width.  It is
 * built by a function rather than bound at load time because this module sits
 * inside the collaboration authority's reviewed import closure.
 */
function declaredFieldSizeSpans(): Map<string, number> {
  return new Map([
    ['compact', 8],
    ['normal', 12],
    ['half', 12],
    ['wide', 16],
    ['full', 24],
    ['large', 24],
  ]);
}

/**
 * The declared low-code size facet as the one renderer layout unit.  This is a
 * declared facet (``field_size``), not a width the renderer invented from a
 * class name or a field type.
 */
export function lowCodeFieldSizeUnits(size: LowCodeFieldSize) {
  return declaredFieldSizeSpans().get(String(size || '').trim().toLowerCase()) ?? layoutGridUnits();
}

/**
 * The declared facet as a span, or ``null`` when the node declares no facet the
 * projection would recognise.  An unrecognised declaration is not reinterpreted
 * as the editor's default ``normal`` width, so the caller fails closed instead
 * of inventing a plausible width.
 */
export function declaredFieldSizeSpan(value: unknown): number | null {
  return declaredFieldSizeSpans().get(String(value || '').trim().toLowerCase()) ?? null;
}

export function lowCodeFieldSizeClass(size: LowCodeFieldSize) {
  if (size === 'compact') return 'field--compact';
  if (size === 'wide') return 'field--wide';
  if (size === 'full') return 'field--full';
  if (size === 'large') return 'field--full field--large';
  return '';
}

export function viewTypeDisplayLabel(value: unknown) {
  const normalized = String(value || '').trim().toLowerCase();
  const labels: Record<string, string> = {
    form: '表单',
    tree: '列表',
    list: '列表',
    kanban: '看板',
    search: '搜索',
    calendar: '日历',
    pivot: '透视',
    graph: '图表',
  };
  if (!normalized || normalized === '-') return '未配置';
  return labels[normalized] || normalized.replace(/[_-]+/g, ' ');
}

export function fieldType(descriptor?: FieldDescriptor | null) {
  return String(descriptor?.ttype || descriptor?.type || '').trim().toLowerCase();
}

export function fieldInputType(ttype?: string): 'text' | 'number' | 'date' | 'datetime-local' {
  const type = String(ttype || '').toLowerCase();
  if (type === 'integer' || type === 'float' || type === 'monetary') return 'number';
  if (type === 'date') return 'date';
  if (type === 'datetime') return 'datetime-local';
  return 'text';
}

export function toDateInputValue(value: unknown) {
  if (value === false || value === null || value === undefined) return '';
  const raw = String(value ?? '').trim();
  if (!raw || raw.toLowerCase() === 'false') return '';
  if (raw.length >= 10) return raw.slice(0, 10);
  return raw;
}

export function toDatetimeInputValue(value: unknown) {
  if (value === false || value === null || value === undefined) return '';
  const raw = String(value ?? '').trim();
  if (!raw || raw.toLowerCase() === 'false') return '';
  const normalized = raw.replace(' ', 'T');
  return normalized.length >= 16 ? normalized.slice(0, 16) : normalized;
}

export function fromDatetimeInputValue(value: unknown) {
  const raw = String(value ?? '').trim();
  if (!raw) return false;
  const normalized = raw.replace('T', ' ');
  return normalized.length === 16 ? `${normalized}:00` : normalized;
}

export function normalizeRelationIds(value: unknown): number[] {
  return extractX2ManyIds(value);
}

export function cleanRelationDisplayLabel(value: unknown, id: number) {
  const label = String(value || '').trim();
  if (!label || label === 'display_name' || label === 'name') return `#${id}`;
  return label;
}

export function parseMany2oneDisplay(value: unknown): RelationOption | null {
  if (Array.isArray(value)) {
    const id = Number(value[0]);
    if (!Number.isFinite(id) || id <= 0) return null;
    const label = cleanRelationDisplayLabel(value[1], id);
    return { id: Math.trunc(id), label };
  }
  if (value && typeof value === 'object') {
    const row = value as Record<string, unknown>;
    const id = Number(row.id);
    if (!Number.isFinite(id) || id <= 0) return null;
    const label = cleanRelationDisplayLabel(row.display_name || row.name, id);
    return { id: Math.trunc(id), label };
  }
  return null;
}

export function sanitizeUiErrorMessage(raw: unknown, fallback: string) {
  const text = String(raw || '').trim();
  if (!text) return fallback;
  const lower = text.toLowerCase();
  if (
    lower.includes('failed to fetch')
    || lower.includes('network request failed')
    || lower.includes('networkerror')
  ) {
    return '网络异常，请检查连接后重试。';
  }
  if (
    lower.includes('duplicate key value')
    || lower.includes('unique constraint')
    || lower.includes('already exists')
    || text.includes('唯一')
    || text.includes('已存在')
  ) {
    return fallback || text;
  }
  if (lower.includes('psycopg2') || lower.includes('traceback') || lower.includes('sql')) {
    return fallback;
  }
  if (text.startsWith('{') && text.includes('"ok"') && text.includes('"data"')) {
    if (text.includes('"ok": true') || text.includes('"records"')) {
      return fallback;
    }
  }
  return text;
}
