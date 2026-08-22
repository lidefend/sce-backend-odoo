export interface RuntimeFieldState {
  invisible: boolean;
  readonly: boolean;
  required: boolean;
}

type Dict = Record<string, unknown>;

function scalar(value: unknown) {
  if (Array.isArray(value) && value.length && typeof value[0] === 'number') return value[0];
  return value;
}

function comparable(value: unknown): unknown[] {
  if (Array.isArray(value)) return value.map((item) => scalar(item));
  return [scalar(value)];
}

function compare(actual: unknown, operator: unknown, expected: unknown) {
  const left = scalar(actual);
  const right = scalar(expected);
  const op = String(operator || '')
    .trim()
    .toLowerCase();
  if (op === '=' || op === '==') return String(left ?? '') === String(right ?? '');
  if (op === '!=' || op === '<>') return String(left ?? '') !== String(right ?? '');
  if (op === 'in') {
    return (
      Array.isArray(expected) && comparable(actual).some((item) => expected.map(String).includes(String(item ?? '')))
    );
  }
  if (op === 'not in') {
    return (
      Array.isArray(expected) && comparable(actual).every((item) => !expected.map(String).includes(String(item ?? '')))
    );
  }
  if (op === '>') return Number(left) > Number(right);
  if (op === '>=') return Number(left) >= Number(right);
  if (op === '<') return Number(left) < Number(right);
  if (op === '<=') return Number(left) <= Number(right);
  if (op === 'like' || op === 'ilike') {
    return String(left ?? '')
      .toLowerCase()
      .includes(String(right ?? '').toLowerCase());
  }
  return false;
}

function evaluateDomain(expression: unknown, values: Dict): boolean {
  if (typeof expression === 'boolean') return expression;
  if (!Array.isArray(expression) || !expression.length) return false;
  if (expression[0] === '|') return evaluateDomain(expression[1], values) || evaluateDomain(expression[2], values);
  if (expression[0] === '&') return evaluateDomain(expression[1], values) && evaluateDomain(expression[2], values);
  if (expression[0] === '!') return !evaluateDomain(expression[1], values);
  if (Array.isArray(expression[0])) return expression.every((item) => evaluateDomain(item, values));
  if (expression.length >= 3) return compare(values[String(expression[0] || '')], expression[1], expression[2]);
  return false;
}

function resolveValue(value: unknown, values: Dict, context: Dict): unknown {
  if (typeof value !== 'string') return value;
  const token = value.trim();
  if (token.startsWith('$')) return values[token.slice(1)];
  if (token.startsWith('context.')) return context[token.slice('context.'.length)];
  if (token.startsWith('parent.')) return values[token.slice('parent.'.length)];
  return value;
}

export function resolveRuntimeDomain(domain: unknown, values: Dict, context: Dict = {}): unknown[] {
  if (!Array.isArray(domain)) return [];
  return domain.map((item) => {
    if (!Array.isArray(item)) return item;
    if (typeof item[0] === 'string' && !['|', '&', '!'].includes(item[0])) {
      return [
        item[0],
        item[1],
        Array.isArray(item[2])
          ? item[2].map((value) => resolveValue(value, values, context))
          : resolveValue(item[2], values, context),
      ];
    }
    return resolveRuntimeDomain(item, values, context);
  });
}

function evaluateModifier(expression: unknown, values: Dict): boolean {
  if (typeof expression === 'boolean') return expression;
  if (!expression) return false;
  if (Array.isArray(expression)) return evaluateDomain(expression, values);
  if (typeof expression !== 'object') return false;
  const row = expression as Dict;
  if (typeof row.parsed === 'boolean') return row.parsed;
  if (row.kind === 'field_compare') return compare(values[String(row.field || '')], row.operator, row.value);
  if (row.parsed !== undefined) return evaluateDomain(row.parsed, values);
  if (row.raw !== undefined && Array.isArray(row.raw)) return evaluateDomain(row.raw, values);
  return false;
}

export function runtimeFieldState(modifiers: Dict, patch: Dict, values: Dict): RuntimeFieldState {
  const merged = { ...modifiers, ...patch };
  return {
    invisible: evaluateModifier(merged.invisible, values),
    readonly: evaluateModifier(merged.readonly, values),
    required: evaluateModifier(merged.required, values),
  };
}
