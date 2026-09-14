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
  const amounts = ratioSettlementApplyAmounts(lines, ratio, rounding);
  return roundSettlementCurrencyAmount(
    amounts.reduce((sum, amount) => sum + amount, 0),
    rounding,
  );
}

export function ratioSettlementApplyAmounts(
  lines: readonly SettlementApplyPreviewLine[],
  ratio: number,
  rounding: number,
): readonly number[] {
  const normalizedRatio = Math.min(Math.max(Number(ratio) || 0, 0), 100);
  return Object.freeze(lines.map((line) => (
    roundSettlementCurrencyAmount(
      (Number(line.remaining) || 0) * normalizedRatio / 100,
      rounding,
    )
  )));
}
