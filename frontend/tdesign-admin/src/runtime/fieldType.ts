const FIELD_TYPE_ALIASES: Readonly<Record<string, string>> = Object.freeze({
  bigint: 'integer',
  bool: 'boolean',
  decimal: 'float',
  double: 'float',
  int: 'integer',
  jsonb: 'json',
  string: 'char',
  timestamp: 'datetime',
  varchar: 'char',
});

export function normalizeFieldType(value: unknown, fallback = 'char') {
  const raw = String(value || fallback)
    .trim()
    .toLowerCase();
  return FIELD_TYPE_ALIASES[raw] || raw || fallback;
}

export function isNumericFieldType(value: unknown) {
  return ['integer', 'float', 'monetary'].includes(normalizeFieldType(value));
}
