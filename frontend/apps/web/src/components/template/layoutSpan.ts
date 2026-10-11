/**
 * The one renderer-facing layout unit.
 *
 * The contract projection resolves every declared width — the native arch
 * ``col`` / ``col-*`` and the low-code ``columns`` / ``field_size`` — into a
 * single ``span`` on a 24-unit grid.  The renderer places a declared child by
 * that number only.  It must never re-derive a width from a class name, a
 * column enum or a field type: that is the contract defect this module exists
 * to prevent (a declared ``col="4"`` group degrading to two columns and the
 * renderer inventing a 112px single column).
 *
 * A node that reaches the renderer without a declared span is a contract
 * defect, not a styling choice.  It fails closed to the full grid width so the
 * missing declaration is visible instead of being silently mis-rendered.
 *
 * Both exports are functions rather than a bound constant because this module
 * sits inside the collaboration authority's reviewed import closure, whose
 * members may hold nothing that is evaluated while they load.
 */
export function layoutGridUnits(): number {
  return 24;
}

/**
 * Whether a contract value is a declared layout span at all.
 *
 * Only a real 1..24 grid unit counts.  A boolean, a numeric string or an
 * out-of-range number is a contract defect: it must stay visible as a missing
 * declaration rather than being coerced into a plausible width (`true` used to
 * become a one-unit field, and a string was silently accepted).
 */
export function isDeclaredLayoutSpan(value: unknown): boolean {
  return typeof value === 'number'
    && Number.isInteger(value)
    && value >= 1
    && value <= layoutGridUnits();
}

export function declaredLayoutSpan(value: unknown): number {
  return isDeclaredLayoutSpan(value) ? (value as number) : layoutGridUnits();
}
