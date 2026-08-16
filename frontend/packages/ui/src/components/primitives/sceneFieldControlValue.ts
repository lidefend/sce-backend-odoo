export function normalizeSceneFieldControlValue(value: unknown, fieldKind = ''): string {
  const scalar = Array.isArray(value) ? value[0] : value;
  if (scalar === false || scalar === null || scalar === undefined) return '';
  const normalized = String(scalar);
  return fieldKind === 'date' && normalized.trim().toLowerCase() === 'false' ? '' : normalized;
}
