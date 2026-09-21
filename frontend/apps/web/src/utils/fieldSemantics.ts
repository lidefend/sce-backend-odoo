import type { FieldDescriptor } from '@sc/schema';

/**
 * 字段语义单一权威。
 *
 * 集合（列表）与记录／表单必须消费同一份字段类型归一、空值口径与取值格式化规则；
 * 任何页面不得自行重新分支字段类型或重新定义空值、布尔、日期、附件检测口径。
 * 本模块只承载平台通用表达，不含行业、客户或低代码配置语义。
 */

export type CanonicalFieldType =
  | 'boolean'
  | 'integer'
  | 'float'
  | 'monetary'
  | 'selection'
  | 'many2one'
  | 'one2many'
  | 'many2many'
  | 'date'
  | 'datetime'
  | 'char'
  | 'text'
  | 'html'
  | 'binary'
  | 'unknown';

const CANONICAL_FIELD_TYPES: ReadonlySet<string> = new Set([
  'boolean',
  'integer',
  'float',
  'monetary',
  'selection',
  'many2one',
  'one2many',
  'many2many',
  'date',
  'datetime',
  'char',
  'text',
  'html',
  'binary',
]);

export const FIELD_VALUE_EMPTY_TEXT = '--';
export const FIELD_VALUE_TRUE_TEXT = '是';
export const FIELD_VALUE_FALSE_TEXT = '否';

/**
 * 数值列在集合视图缺少取值时的呈现口径。这是既有的集合密度策略，在此登记为有意声明，
 * 不代表记录／表单路径应采用同一取值；改口径需要产品决定，不在前端自行猜测。
 */
export const COLLECTION_NUMERIC_EMPTY_TEXT = '0';

export const ATTACHMENT_REFERENCE_URL_SOURCE = '(?:legacy-file-id|legacy-file|https?|file):\\/\\/|\\/web\\/content\\/';

const ATTACHMENT_REFERENCE_PATTERN = new RegExp(`\\|\\s*(?:${ATTACHMENT_REFERENCE_URL_SOURCE})`, 'i');

const TEMPORAL_PATTERN = /^(\d{4}-\d{2}-\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?)?(?:Z|[+-]\d{2}:?\d{2})?$/;

export type FieldTypeSource =
  | Pick<FieldDescriptor, 'ttype' | 'type'>
  | { ttype?: unknown; type?: unknown }
  | string
  | null
  | undefined;

export function normalizeFieldType(source: FieldTypeSource): CanonicalFieldType {
  const raw = typeof source === 'string'
    ? source
    : String(
      (source as { ttype?: unknown } | null | undefined)?.ttype
      ?? (source as { type?: unknown } | null | undefined)?.type
      ?? '',
    );
  const normalized = raw.trim().toLowerCase();
  return (CANONICAL_FIELD_TYPES.has(normalized) ? normalized : 'unknown') as CanonicalFieldType;
}

export function isNumericFieldType(type: string): boolean {
  return type === 'integer' || type === 'float' || type === 'monetary';
}

export function isTemporalFieldType(type: string): boolean {
  return type === 'date' || type === 'datetime';
}

export function isBooleanFieldType(type: string): boolean {
  return type === 'boolean';
}

export function isSelectionFieldType(type: string): boolean {
  return type === 'selection';
}

export function isScalarRelationFieldType(type: string): boolean {
  return type === 'many2one';
}

export function isRelationCollectionFieldType(type: string): boolean {
  return type === 'one2many' || type === 'many2many';
}

export function isEmptyFieldValue(value: unknown): boolean {
  return value === null || value === undefined || value === '';
}

export function numericFieldValue(value: unknown): number | null {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  if (typeof value !== 'string') return null;
  const normalized = value.replace(/,/g, '').trim();
  if (!normalized) return null;
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

export function formatNumericFieldValue(
  value: unknown,
  type: string,
  options?: { locale?: string },
): string | null {
  const parsed = numericFieldValue(value);
  if (parsed === null) return null;
  const fractionDigits = type === 'integer' ? 0 : 2;
  return parsed.toLocaleString(options?.locale || 'zh-CN', {
    maximumFractionDigits: fractionDigits,
    minimumFractionDigits: fractionDigits,
  });
}

/**
 * 日期／时间取值的统一解析与呈现。集合按 compact 保持列表密度，记录／表单按 full 保留秒，
 * 两者共用同一解析规则，差异是声明式的呈现档位而不是各写一套。
 */
export type TemporalDisplayProfile = 'compact' | 'full';

export function formatTemporalFieldValue(
  value: unknown,
  profile: TemporalDisplayProfile = 'compact',
): string {
  const text = String(value ?? '').trim();
  if (!text) return '';
  const match = text.match(TEMPORAL_PATTERN);
  if (!match) return '';
  const [, date, hour = '00', minute = '00', second = '00'] = match;
  if (`${hour}:${minute}:${second}` === '00:00:00') return date;
  return profile === 'full' ? `${date} ${hour}:${minute}:${second}` : `${date} ${hour}:${minute}`;
}

export function containsAttachmentReference(value: unknown): boolean {
  return ATTACHMENT_REFERENCE_PATTERN.test(String(value ?? ''));
}

export function containsAttachmentReferenceIn(value: unknown): boolean {
  if (Array.isArray(value)) return value.some((item) => containsAttachmentReference(item));
  return containsAttachmentReference(value);
}
