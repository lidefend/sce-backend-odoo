export type SettlementApplyPreviewLine = Readonly<{
  remaining: number;
}>;

export function roundSettlementCurrencyAmount(value: number, rounding: number): number {
  const normalizedRounding = Number(rounding || 0);
  if (!(normalizedRounding > 0)) return value;
  const normalizedValue = Number(value || 0) / normalizedRounding;
  if (!Number.isFinite(normalizedValue) || normalizedValue === 0) return normalizedValue;
  const epsilon = 2 ** (Math.log2(Math.abs(normalizedValue)) - 52);
  const roundedUnits = Math.sign(normalizedValue)
    * Math.floor(Math.abs(normalizedValue) + epsilon + 0.5);
  return roundedUnits * normalizedRounding;
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
