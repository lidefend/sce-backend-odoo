import { resolveNativeOperand } from './nativeModifierContext';
import { comparePythonModifier } from './nativeModifierComparison';
import { contractGapError } from './contract/contractGap';

export type FieldRuntimeState = {
  invisible: boolean;
  readonly: boolean;
  required: boolean;
};

type DomainLeaf = [string, string, unknown];

function toScalar(value: unknown) {
  if (Array.isArray(value) && value.length && typeof value[0] === 'number') {
    return value[0];
  }
  return value;
}

function compare(actual: unknown, op: string, expected: unknown): boolean {
  const left = toScalar(actual);
  const right = toScalar(expected);
  const key = String(op || '').trim().toLowerCase();

  if (key === '=' || key === '==') return String(left ?? '') === String(right ?? '');
  if (key === '!=' || key === '<>') return String(left ?? '') !== String(right ?? '');
  if (key === 'in') return Array.isArray(expected) && expected.map((x) => String(x ?? '')).includes(String(left ?? ''));
  if (key === 'not in') return Array.isArray(expected) && !expected.map((x) => String(x ?? '')).includes(String(left ?? ''));
  if (key === '>') return Number(left) > Number(right);
  if (key === '>=') return Number(left) >= Number(right);
  if (key === '<') return Number(left) < Number(right);
  if (key === '<=') return Number(left) <= Number(right);
  if (key === 'like' || key === 'ilike') return String(left ?? '').toLowerCase().includes(String(right ?? '').toLowerCase());
  return false;
}

export function compareNativeModifierValue(actual: unknown, operator: string, expected: unknown) {
  return compare(actual, operator, expected);
}

export function isStaticTruthyModifier(value: unknown) {
  if (value === true || value === 1) return true;
  if (typeof value !== 'string') return false;
  return ['1', 'true', 'True'].includes(value.trim());
}

/**
 * The single rule that decides which value set a declared modifier field is
 * evaluated against.
 *
 * A live form value wins only when the form actually owns the key and carries a
 * defined value; otherwise the contract snapshot answers.  Two consumers
 * resolving the same declared fact from different unions can disagree about it,
 * and a declared condition that resolves one way in the renderer and another
 * way in the executor silently inverts a button's visibility.  Every consumer
 * of a declared modifier therefore resolves its field references through this
 * function instead of re-deriving a union of its own.
 */
export function resolveDeclaredModifierFieldValue(
  snapshot: Record<string, unknown> | null | undefined,
  live: Record<string, unknown> | null | undefined,
  field: string,
): unknown {
  const name = String(field || '').trim();
  if (!name) return undefined;
  if (name === '$native.context') return snapshot?.[name];
  if (live && Object.prototype.hasOwnProperty.call(live, name) && live[name] !== undefined) {
    return live[name];
  }
  return snapshot ? snapshot[name] : undefined;
}

function modifierGap(reason: string): never {
  throw contractGapError({
    kind: 'contract_defect', missing: `native_modifier.${reason}`,
    requiredDeclarationLayer: 'P0:smart_core:utils/native_modifier',
  }, `原生条件契约不可求值：${reason}`);
}

function nativeTruthy(value: unknown): boolean {
  if (Array.isArray(value)) return value.length > 0;
  if (value && typeof value === 'object') return Object.keys(value).length > 0;
  return Boolean(value);
}

export function evaluateNativeModifierValue(value: unknown, resolveFieldValue: (field: string) => unknown): boolean {
  if (typeof value === 'boolean') return value;
  // An absent optional modifier is not an expression with a missing dependency.
  if (value === undefined || value === null || value === '' || value === 0 || value === '0' || value === 'false' || value === 'False') return false;
  if (isStaticTruthyModifier(value)) return true;
  if (typeof value !== 'object' || Array.isArray(value)) return modifierGap('unsupported_expression');
  const row = value as Record<string, unknown>;
  const kind = String(row.kind || '').trim();
  if (kind === 'value_truthy' || kind === 'value_compare') {
    if (row.semantics !== 'python') return modifierGap('comparison_semantics');
    if (kind === 'value_truthy') return nativeTruthy(resolveNativeOperand(row.value_expr, resolveFieldValue));
    if (typeof row.operator !== 'string') return modifierGap('operator');
    const left = resolveNativeOperand(row.left, resolveFieldValue);
    const right = resolveNativeOperand(row.right, resolveFieldValue);
    return comparePythonModifier(left, String(row.operator || ''), right);
  }
  if (kind === 'static') {
    if (typeof row.value !== 'boolean') return modifierGap('static.value');
    return row.value;
  }
  if (kind === 'not') {
    if (!Object.prototype.hasOwnProperty.call(row, 'expr') || row.expr == null || row.expr === '') return modifierGap('not.expr');
    return !evaluateNativeModifierValue(row.expr, resolveFieldValue);
  }
  if (kind === 'all' || kind === 'any') {
    if (!Array.isArray(row.exprs) || !row.exprs.length || row.exprs.some((expr) => expr == null || expr === '')) return modifierGap(`${kind}.exprs`);
    // Resolve every declared branch before reducing: short-circuiting must not hide a contract defect.
    const verdicts = row.exprs.map((expr) => evaluateNativeModifierValue(expr, resolveFieldValue));
    return kind === 'all' ? verdicts.every(Boolean) : verdicts.some(Boolean);
  }
  if (kind !== 'field_truthy' && kind !== 'field_compare') return modifierGap('unsupported_kind');
  const field = String(row.field || '').trim();
  if (!field) return modifierGap('field');
  const resolve = (name: string) => {
    const actual = resolveFieldValue(name);
    if (actual === undefined) return modifierGap(`dependency.${name}`);
    return actual;
  };
  if (kind === 'field_truthy') return nativeTruthy(resolve(field));
  if (typeof row.operator !== 'string') return modifierGap('operator');
  const operator = row.operator.trim();
  if (!['=', '==', '!=', '<>', '>', '>=', '<', '<=', 'in', 'not in', 'like', 'ilike'].includes(operator)) return modifierGap('operator');
  const valueField = String(row.value_field || row.valueField || '').trim();
  if (!valueField && !Object.prototype.hasOwnProperty.call(row, 'value')) return modifierGap('value');
  const expected = valueField ? resolve(valueField) : row.value;
  if (row.semantics === 'python') return comparePythonModifier(resolve(field), operator, expected);
  if (row.semantics !== undefined) return modifierGap('comparison_semantics');
  return compareNativeModifierValue(resolve(field), operator, expected);
}

function evalLeaf(expr: unknown, values: Record<string, unknown>): boolean {
  if (!Array.isArray(expr) || expr.length < 3) return false;
  const leaf = expr as DomainLeaf;
  const field = String(leaf[0] || '').trim();
  if (!field) return false;
  return compare(values[field], String(leaf[1] || ''), leaf[2]);
}

function evalDomain(expr: unknown, values: Record<string, unknown>): boolean {
  if (typeof expr === 'boolean') return expr;
  if (!Array.isArray(expr)) return false;
  if (!expr.length) return false;

  const head = expr[0];
  if (head === '|') {
    return evalDomain(expr[1], values) || evalDomain(expr[2], values);
  }
  if (head === '&') {
    return evalDomain(expr[1], values) && evalDomain(expr[2], values);
  }
  if (head === '!') {
    return !evalDomain(expr[1], values);
  }

  if (Array.isArray(head) && head.length >= 3) {
    return (expr as unknown[]).every((item) => evalLeaf(item, values));
  }

  return evalLeaf(expr, values);
}

function evalModifierBucket(bucket: unknown, values: Record<string, unknown>): boolean {
  if (typeof bucket === 'boolean') return bucket;
  if (!Array.isArray(bucket)) return false;
  if (!bucket.length) return false;

  return bucket.some((entry) => {
    if (typeof entry === 'boolean') return entry;
    if (!entry || typeof entry !== 'object') return evalDomain(entry, values);
    const row = entry as Record<string, unknown>;
    if (typeof row.parsed === 'boolean') return row.parsed;
    if (row.parsed !== undefined) return evalDomain(row.parsed, values);
    if (row.raw !== undefined) return evalDomain(row.raw, values);
    return evalDomain(entry, values);
  });
}

export function buildRuntimeFieldStates(params: {
  fieldNames: string[];
  fieldModifiers?: Record<string, Record<string, unknown>>;
  modifierPatch?: Record<string, Record<string, unknown>>;
  values: Record<string, unknown>;
}) {
  const modifiers = params.fieldModifiers || {};
  const patch = params.modifierPatch || {};
  const values = params.values || {};
  const states: Record<string, FieldRuntimeState> = {};

  for (const name of params.fieldNames) {
    const base = modifiers[name] || {};
    const extra = patch[name] || {};
    const merged = { ...base, ...extra };
    states[name] = {
      invisible: evalModifierBucket(merged.invisible, values),
      readonly: evalModifierBucket(merged.readonly, values),
      required: evalModifierBucket(merged.required, values),
    };
  }

  return states;
}
