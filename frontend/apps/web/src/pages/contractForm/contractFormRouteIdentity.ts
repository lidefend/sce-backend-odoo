function firstText(value: unknown): string {
  const item = Array.isArray(value) ? value[0] : value;
  return String(item ?? '').trim();
}

export function resolveContractFormRouteModel(options: {
  routeModel?: unknown;
  queryModel?: unknown;
  contractModel?: unknown;
}): string {
  return firstText(options.routeModel)
    || firstText(options.queryModel)
    || firstText(options.contractModel);
}

export function resolveContractFormRouteRecordId(options: {
  routeRecordId?: unknown;
  queryRecordId?: unknown;
}): number | null {
  const raw = firstText(options.routeRecordId) || firstText(options.queryRecordId);
  if (!raw || raw === 'new') return null;
  const parsed = Number(raw);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}
