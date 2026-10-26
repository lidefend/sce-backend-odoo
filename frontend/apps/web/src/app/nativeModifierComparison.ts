import { contractGapError } from './contract/contractGap';

function invalid(): never {
  throw contractGapError({ kind: 'contract_defect', missing: 'native_modifier.python_comparison',
    requiredDeclarationLayer: 'P0:smart_core:utils/native_modifier' }, '原生 Python 比较的类型或操作符不受支持');
}

function jsonValue(value: unknown): boolean {
  if (value === null || typeof value === 'boolean') return true;
  if (typeof value === 'string') return Array.from(value).every((char) => {
    const point = char.codePointAt(0)!;
    return point < 0xD800 || point > 0xDFFF;
  });
  if (typeof value === 'number') return Number.isFinite(value) && Math.abs(value) <= Number.MAX_SAFE_INTEGER;
  if (Array.isArray(value)) return value.every(jsonValue);
  if (value && typeof value === 'object' && Object.getPrototypeOf(value) === Object.prototype) {
    return Object.entries(value).every(([key, item]) => jsonValue(key) && jsonValue(item));
  }
  return false;
}

function numeric(value: unknown): value is number | boolean {
  return typeof value === 'number' || typeof value === 'boolean';
}

function equal(left: unknown, right: unknown): boolean {
  if (numeric(left) && numeric(right)) return Number(left) === Number(right);
  if (Array.isArray(left) || Array.isArray(right)) {
    return Array.isArray(left) && Array.isArray(right) && left.length === right.length
      && left.every((value, index) => equal(value, right[index]));
  }
  if (left !== null && right !== null && typeof left === 'object' && typeof right === 'object') {
    const a = left as Record<string, unknown>;
    const b = right as Record<string, unknown>;
    return Object.keys(a).length === Object.keys(b).length
      && Object.keys(a).every((key) => Object.prototype.hasOwnProperty.call(b, key) && equal(a[key], b[key]));
  }
  return left === right;
}

function order(left: unknown, right: unknown): number {
  if (numeric(left) && numeric(right)) return Number(left) - Number(right);
  if (typeof left === 'string' && typeof right === 'string') {
    // Python compares Unicode code points; JS's default order uses UTF-16 units.
    return order(Array.from(left, (v) => v.codePointAt(0)), Array.from(right, (v) => v.codePointAt(0)));
  }
  if (Array.isArray(left) && Array.isArray(right)) {
    for (let i = 0; i < Math.min(left.length, right.length); i += 1) {
      if (!equal(left[i], right[i])) return order(left[i], right[i]);
    }
    return left.length - right.length;
  }
  return invalid();
}

export function comparePythonModifier(actual: unknown, operator: string, expected: unknown): boolean {
  if (!jsonValue(actual) || !jsonValue(expected)) return invalid();
  if (operator === '==') return equal(actual, expected);
  if (operator === '!=') return !equal(actual, expected);
  if (operator === 'in' || operator === 'not in') {
    let found: boolean;
    if (Array.isArray(expected)) found = expected.some((item) => equal(actual, item));
    else if (typeof expected === 'string' && typeof actual === 'string') found = expected.includes(actual);
    else if (expected && typeof expected === 'object' && !Array.isArray(expected)) {
      if (Array.isArray(actual) || actual !== null && typeof actual === 'object') return invalid();
      found = typeof actual === 'string' && Object.prototype.hasOwnProperty.call(expected, actual);
    } else return invalid();
    return operator === 'in' ? found : !found;
  }
  if (!['>', '>=', '<', '<='].includes(operator)) return invalid();
  const compared = order(actual, expected);
  if (operator === '>') return compared > 0;
  if (operator === '>=') return compared >= 0;
  if (operator === '<') return compared < 0;
  return compared <= 0;
}
