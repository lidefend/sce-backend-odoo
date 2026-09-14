export type SettlementApplyPreviewLine = Readonly<{
  remaining: number;
}>;

export function roundSettlementCurrencyAmount(value: number, rounding: number): number {
  const normalizedRounding = Number(rounding || 0);
  if (!(normalizedRounding > 0)) return value;
  return Math.round((value / normalizedRounding) + Number.EPSILON) * normalizedRounding;
}

export function ratioSettlementApplyTotal(
  lines: readonly SettlementApplyPreviewLine[],
  ratio: number,
  rounding: number,
): number {
  const normalizedRatio = Math.min(Math.max(Number(ratio) || 0, 0), 100);
  const total = lines.reduce((sum, line) => (
    sum + roundSettlementCurrencyAmount(
      (Number(line.remaining) || 0) * normalizedRatio / 100,
      rounding,
    )
  ), 0);
  return roundSettlementCurrencyAmount(total, rounding);
}
