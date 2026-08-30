import type { Dictionary } from "@/types/contracts";

export interface RuntimeFieldState {
  invisible: boolean;
  readonly: boolean;
  required: boolean;
}

function scalar(value: unknown) {
  return Array.isArray(value) && value.length && typeof value[0] === "number"
    ? value[0]
    : value;
}
function comparable(value: unknown) {
  return Array.isArray(value) ? value.map(scalar) : [scalar(value)];
}
function compare(actual: unknown, operator: unknown, expected: unknown) {
  const left = scalar(actual);
  const right = scalar(expected);
  const op = String(operator || "")
    .trim()
    .toLowerCase();
  if (op === "=" || op === "==")
    return String(left ?? "") === String(right ?? "");
  if (op === "!=" || op === "<>")
    return String(left ?? "") !== String(right ?? "");
  if (op === "in")
    return (
      Array.isArray(expected) &&
      comparable(actual).some((item) =>
        expected.map(String).includes(String(item ?? "")),
      )
    );
  if (op === "not in")
    return (
      Array.isArray(expected) &&
      comparable(actual).every(
        (item) => !expected.map(String).includes(String(item ?? "")),
      )
    );
  if (op === ">") return Number(left) > Number(right);
  if (op === ">=") return Number(left) >= Number(right);
  if (op === "<") return Number(left) < Number(right);
  if (op === "<=") return Number(left) <= Number(right);
  if (op === "like" || op === "ilike")
    return String(left ?? "")
      .toLowerCase()
      .includes(String(right ?? "").toLowerCase());
  return false;
}
function evaluateDomain(expression: unknown, values: Dictionary): boolean {
  if (typeof expression === "boolean") return expression;
  if (!Array.isArray(expression) || !expression.length) return false;
  if (expression[0] === "|")
    return (
      evaluateDomain(expression[1], values) ||
      evaluateDomain(expression[2], values)
    );
  if (expression[0] === "&")
    return (
      evaluateDomain(expression[1], values) &&
      evaluateDomain(expression[2], values)
    );
  if (expression[0] === "!") return !evaluateDomain(expression[1], values);
  if (Array.isArray(expression[0]))
    return expression.every((item) => evaluateDomain(item, values));
  return expression.length >= 3
    ? compare(values[String(expression[0] || "")], expression[1], expression[2])
    : false;
}
function evaluateModifier(expression: unknown, values: Dictionary): boolean {
  if (typeof expression === "boolean") return expression;
  if (!expression) return false;
  if (Array.isArray(expression)) return evaluateDomain(expression, values);
  if (typeof expression !== "object") return false;
  const row = expression as Dictionary;
  if (typeof row.parsed === "boolean") return row.parsed;
  if (row.kind === "static") return Boolean(row.value);
  if (row.kind === "field_compare")
    return compare(values[String(row.field || "")], row.operator, row.value);
  if (row.parsed !== undefined) return evaluateDomain(row.parsed, values);
  if (Array.isArray(row.raw)) return evaluateDomain(row.raw, values);
  return false;
}
export function runtimeFieldState(
  modifiers: Dictionary,
  patch: Dictionary,
  values: Dictionary,
): RuntimeFieldState {
  const merged = { ...modifiers, ...patch };
  return {
    invisible: evaluateModifier(merged.invisible, values),
    readonly: evaluateModifier(merged.readonly, values),
    required: evaluateModifier(merged.required, values),
  };
}
function resolveValue(value: unknown, values: Dictionary, context: Dictionary) {
  if (typeof value !== "string") return value;
  if (value.startsWith("$")) return values[value.slice(1)];
  if (value.startsWith("context.")) return context[value.slice(8)];
  if (value.startsWith("parent.")) return values[value.slice(7)];
  return value;
}
export function resolveRuntimeDomain(
  domain: unknown,
  values: Dictionary,
  context: Dictionary = {},
): unknown[] {
  const source = normalizeRuntimeDomain(domain);
  return source.map((item) => {
    if (!Array.isArray(item)) return item;
    if (typeof item[0] === "string" && !["|", "&", "!"].includes(item[0]))
      return [
        item[0],
        item[1],
        Array.isArray(item[2])
          ? item[2].map((value) => resolveValue(value, values, context))
          : resolveValue(item[2], values, context),
      ];
    return resolveRuntimeDomain(item, values, context);
  });
}

function relationId(value: unknown): number {
  const raw = Array.isArray(value)
    ? value[0]
    : value && typeof value === "object"
      ? (value as Dictionary).id
      : value;
  const id = Number(raw || 0);
  return Number.isInteger(id) && id > 0 ? id : 0;
}

function domainMentions(domain: unknown[], fieldName: string): boolean {
  return domain.some(
    (item) => Array.isArray(item) && String(item[0]) === fieldName,
  ) || JSON.stringify(domain).includes(`\"$${fieldName}\"`);
}

/** Resolve a relation domain against the current form and prevent stale cross-record options. */
export function resolveRelationDomain(
  domain: unknown,
  values: Dictionary,
  context: Dictionary = {},
  fieldCode = "",
): unknown[] {
  const source = normalizeRuntimeDomain(domain);
  const resolved = resolveRuntimeDomain(source, values, context);
  const projectId = relationId(values.project_id);
  const isProjectScoped = fieldCode === "boq_version_id" || domainMentions(source, "project_id");
  if (!isProjectScoped) return resolved;

  const withoutProjectAndState = resolved.filter(
    (item) =>
      !(
        Array.isArray(item) &&
        (String(item[0]) === "project_id" ||
          (fieldCode === "boq_version_id" && String(item[0]) === "state"))
      ),
  );
  return [
    ...withoutProjectAndState,
    ["project_id", "=", projectId || 0],
    ...(fieldCode === "boq_version_id" ? [["state", "=", "published"]] : []),
  ];
}

export function normalizeRuntimeDomain(domain: unknown): unknown[] {
  if (Array.isArray(domain)) return domain;
  if (typeof domain !== "string" || !domain.trim()) return [];
  const clauses: unknown[] = [];
  const pattern = /\(\s*['"]([^'"]+)['"]\s*,\s*['"]([^'"]+)['"]\s*,\s*([^\)]*)\)/g;
  for (const match of domain.matchAll(pattern)) {
    const rawValue = String(match[3] || "").trim();
    let value: unknown = rawValue;
    if ((rawValue.startsWith("'") && rawValue.endsWith("'")) || (rawValue.startsWith('"') && rawValue.endsWith('"'))) value = rawValue.slice(1, -1);
    else if (/^(true|false)$/i.test(rawValue)) value = rawValue.toLowerCase() === "true";
    else if (/^\d+(?:\.\d+)?$/.test(rawValue)) value = Number(rawValue);
    else if (/^[a-zA-Z_][\w.]*$/.test(rawValue)) value = `$${rawValue}`;
    clauses.push([match[1], match[2], value]);
  }
  return clauses;
}
