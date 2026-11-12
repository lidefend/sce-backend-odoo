function positiveInteger(value: unknown): number {
  const parsed = Number(value || 0);
  return Number.isFinite(parsed) && parsed > 0 ? Math.trunc(parsed) : 0;
}

export function mergeUploadedAttachmentIds(
  currentIds: readonly unknown[],
  uploadedIds: readonly unknown[],
): number[] {
  const merged: number[] = [];
  const seen = new Set<number>();
  for (const value of [...currentIds, ...uploadedIds]) {
    const id = positiveInteger(value);
    if (id <= 0 || seen.has(id)) continue;
    seen.add(id);
    merged.push(id);
  }
  return merged;
}
