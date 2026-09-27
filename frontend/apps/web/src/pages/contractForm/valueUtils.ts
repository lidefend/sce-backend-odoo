import type { FieldDescriptor } from '@sc/schema';
import { buildX2ManyCommands } from '../../app/x2manyCommands';
import { fieldType, fromDatetimeInputValue, toDateInputValue } from './fieldUtils';

/**
 * Single source of truth for "is this required value missing".
 *
 * Both the scene precheck (`collectSceneValidationPrecheckErrors`, no type
 * available) and the save-time required validation (`collectRequiredFieldValidation`)
 * must answer the same way for the same value; otherwise one path blocks a save
 * the other one allows.
 *
 * - numeric `0` / `0.0` is a real value, never missing (falsy is not emptiness)
 * - a boolean field's `false` is a real value: an unchecked flag is not "unfilled"
 * - for non-boolean fields, Odoo's `false` empty sentinel is missing
 * - `null` / `undefined` / blank text / empty collection are missing
 */
export function isMissingRequiredValue(value: unknown, fieldType?: unknown) {
  const ttype = String(fieldType ?? '').trim().toLowerCase();
  if (ttype === 'boolean') return value !== true && value !== false;
  if (Array.isArray(value)) return value.length === 0;
  if (ttype === 'many2one') return !Number(value || 0);
  if (ttype === 'many2many' || ttype === 'one2many') return !Array.isArray(value) || value.length === 0;
  if (value === false || value === null || value === undefined) return true;
  if (typeof value === 'string') return value.trim() === '';
  if (typeof value === 'number') return !Number.isFinite(value);
  if (typeof value === 'object') return Object.keys(value as Record<string, unknown>).length === 0;
  return false;
}

export function normalizeComparable(value: unknown) {
  if (Array.isArray(value) && value.every((item) => typeof item === 'number')) {
    return JSON.stringify([...value].sort((a, b) => a - b));
  }
  if (Array.isArray(value)) return JSON.stringify(value);
  if (value && typeof value === 'object') return JSON.stringify(value);
  return String(value ?? '');
}

export function parseNumeric(text: unknown) {
  const raw = String(text ?? '').trim();
  if (!raw) return null;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}

/**
 * Type-aware name kept for existing consumers. It is intentionally a thin alias
 * so page-level validation and save-time validation cannot drift apart again.
 */
export function isRequiredFieldEmptyByType(value: unknown, fieldType: string) {
  return isMissingRequiredValue(value, fieldType);
}

export function normalizeRouteDefault(value: unknown) {
  const raw = Array.isArray(value) ? value[value.length - 1] : value;
  if (typeof raw !== 'string') return raw;
  const normalized = raw.trim();
  if (!normalized) return '';
  if (normalized === 'true') return true;
  if (normalized === 'false') return false;
  if (/^-?\d+(\.\d+)?$/.test(normalized)) return Number(normalized);
  return normalized;
}

export function resolveNavigationUrl(url: string, origin: string) {
  const raw = String(url || '').trim();
  if (!raw) return '';
  if (/^https?:\/\//i.test(raw)) return raw;
  if (raw.startsWith('/')) return `${origin}${raw}`;
  return raw;
}

export function normalizeContractFieldValue(params: {
  name: string;
  value: unknown;
  descriptor?: FieldDescriptor;
  originalValue: unknown;
  mode?: 'write' | 'onchange';
  buildOne2manyValue: (name: string, mode: 'write' | 'onchange') => unknown;
}) {
  const ttype = fieldType(params.descriptor);
  if (ttype === 'boolean') return Boolean(params.value);
  if (ttype === 'integer') {
    // An untouched numeric is `null`, not `false`: the payload builder omits it
    // so the server keeps the stored value / applies its own default instead of
    // silently writing 0. An explicit clear (`''`) still serializes as Odoo's
    // type-correct empty sentinel `false`.
    if (params.value === null || params.value === undefined) return null;
    const parsed = parseNumeric(params.value);
    return parsed === null ? false : Math.trunc(parsed);
  }
  if (ttype === 'float' || ttype === 'monetary') {
    if (params.value === null || params.value === undefined) return null;
    const parsed = parseNumeric(params.value);
    if (parsed === null) return false;
    if (ttype !== 'monetary') return parsed;
    const rawDigits = params.descriptor && typeof params.descriptor === 'object'
      ? (params.descriptor as Record<string, unknown>).digits
      : undefined;
    const scale = Array.isArray(rawDigits) && rawDigits.length === 2 ? Number(rawDigits[1]) : NaN;
    if (!Number.isInteger(scale) || scale < 0 || scale > 20) return parsed;
    const factor = 10 ** scale;
    return Math.round((parsed + Number.EPSILON) * factor) / factor;
  }
  if (ttype === 'many2one') {
    if (Array.isArray(params.value) && typeof params.value[0] === 'number') return params.value[0];
    if (typeof params.value === 'number') return params.value;
    const parsed = parseNumeric(params.value);
    return parsed === null ? false : Math.trunc(parsed);
  }
  if (ttype === 'many2many') {
    return buildX2ManyCommands({
      kind: 'many2many',
      current: params.value,
      original: params.originalValue,
      mode: params.mode || 'write',
    });
  }
  if (ttype === 'one2many') return params.buildOne2manyValue(params.name, params.mode || 'write');
  if (ttype === 'date') {
    const normalized = toDateInputValue(params.value);
    return normalized || false;
  }
  if (ttype === 'datetime') return fromDatetimeInputValue(params.value);
  if (ttype === 'char' || ttype === 'text' || ttype === 'html') return String(params.value ?? '');
  return params.value;
}
