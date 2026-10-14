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
 * defect, not a styling choice.  It stops the render (``ContractGapError``) so
 * the missing declaration is visible at the declaration layer instead of being
 * silently coerced to full width, a one-unit field or any other plausible
 * width.
 *
 * All exports are functions rather than a bound constant because this module
 * sits inside the collaboration authority's reviewed import closure, whose
 * members may hold nothing that is evaluated while they load.
 */
import { contractGapError } from '../../app/contract/contractGap';

/**
 * The declaration layer that owes a layout span.
 *
 * A function rather than a bound constant: this module sits inside the
 * collaboration authority's reviewed import closure, whose members may hold
 * nothing that is evaluated while they load.
 */
function layoutSpanDeclarationLayer(): string {
  return 'P0:smart_core:page_assembler:layout';
}
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

/**
 * Consume a declared layout span, or stop.
 *
 * The declaration layer publishes ``span`` for every layout node the renderer
 * places; the projection and the decoder both guarantee it.  A value that is
 * missing, or that is present but not a real 1..24 grid unit, is therefore a
 * contract defect: the renderer must not invent a width for it.  It raises the
 * one contract-gap primitive so the gap is closed at the declaration layer
 * rather than hidden behind a default.
 */
export function requireDeclaredLayoutSpan(
  value: unknown,
  spec?: { missing?: string; requiredDeclarationLayer?: string },
): number {
  if (!isDeclaredLayoutSpan(value)) {
    const missing = spec?.missing ?? 'layout.span';
    throw contractGapError(
      {
        kind: 'contract_defect',
        missing,
        requiredDeclarationLayer: spec?.requiredDeclarationLayer ?? layoutSpanDeclarationLayer(),
      },
      `契约缺少合法布局跨度 ${missing}：前端不停机兜底，等待声明层补齐`,
    );
  }
  return value as number;
}

export function declaredLayoutSpan(value: unknown): number {
  return requireDeclaredLayoutSpan(value);
}

/**
 * The declared width band on the folded face.
 *
 * The component vocabulary names a folded width ``full`` (owns the row) or
 * ``half`` (shares it).  The band is the fold of the ONE declared layout unit,
 * not a second width vocabulary: every renderer grid publishes it for the same
 * declared span, so one contract cannot fold two ways.  Deriving it in a
 * renderer (`span > 12`) left the threshold owned by nobody.
 */
export function declaredLayoutBand(value: unknown): 'full' | 'half' {
  return declaredLayoutSpan(value) > layoutGridUnits() / 2 ? 'full' : 'half';
}

/**
 * The one declared fold of the 24-unit grid.
 *
 * Below ``single`` the container owns one column, so every declared child takes
 * the whole row; up to ``mediumMax`` the grid folds to two tracks and a child
 * follows its band; above that the declared span is the placement.  The
 * frontend owns these breakpoints, the contract owns what folds: they are
 * declared once here and the renderer stylesheets must implement exactly these
 * numbers (`frontend_form_canvas_wide_grid_guard` locks the match), so no grid
 * can fold on a threshold of its own.
 */
export function declaredLayoutFoldBreakpoints(): { single: number; mediumMax: number } {
  return { single: 479, mediumMax: 959 };
}

/** Container field grids are explicit backend declarations, not component defaults. */
export function requireDeclaredLayoutColumns(value: unknown): number {
  const columns = requireDeclaredLayoutSpan(value, { missing: 'layout.columns' });
  if (layoutGridUnits() % columns) {
    throw contractGapError({ kind: 'contract_defect', missing: 'layout.columns.equalTracks', requiredDeclarationLayer: layoutSpanDeclarationLayer() }, '契约列数不能精确映射到24单位网格');
  }
  return columns;
}

/** Registered singleton mapping: outer declared field node owns parent placement;
 * its internal control fills that cell. Never selected from visible field count. */
export function containedFieldLayout(): { columns: number; span: number } {
  return { columns: 1, span: layoutGridUnits() };
}
