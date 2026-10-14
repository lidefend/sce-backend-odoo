/**
 * Web-side choice of the position that receives focus for one business error.
 *
 * This is a display decision, not business ownership. Given the positions the
 * current page registered for one business goal, it decides which one the user
 * should be sent to. It is free of the DOM so the same rule is exercised by the
 * unit test and by the page, and so another client remains free to choose its
 * own position from the same business error.
 *
 * The rule never picks a position merely because it comes first in the
 * document: a read-only copy of the same field is not a place where the user can
 * correct the value. When no correction-capable position exists, the caller is
 * told to keep the error at form level instead of sending the user to a field
 * they cannot edit.
 */

export type ValidationPositionCandidate = {
  /** Page-local display key of the registered position (the business error key). */
  key: string;
  /** Local occurrence identity of the rendering position. */
  occurrenceKey: string;
  /** The position is rendered and reachable on screen. */
  visible: boolean;
  /** The position accepts a user correction: editable, enabled, edit profile. */
  correctable: boolean;
};

export type ValidationPositionReason =
  | 'source-occurrence'
  | 'correctable-position'
  | 'no-correctable-position';

export type ValidationPositionChoice = {
  position: ValidationPositionCandidate | null;
  outcome: 'position' | 'summary';
  reason: ValidationPositionReason;
};

export function selectValidationPosition(
  candidates: readonly ValidationPositionCandidate[],
  options: { sourceOccurrenceKey?: string } = {},
): ValidationPositionChoice {
  const usable = (candidates || []).filter((candidate) => candidate.visible && candidate.correctable);
  const source = String(options.sourceOccurrenceKey || '').trim();
  if (source) {
    const fromSource = usable.find((candidate) => candidate.occurrenceKey === source);
    if (fromSource) return { position: fromSource, outcome: 'position', reason: 'source-occurrence' };
  }
  if (usable.length) return { position: usable[0], outcome: 'position', reason: 'correctable-position' };
  return { position: null, outcome: 'summary', reason: 'no-correctable-position' };
}

/** True when the position is registered for exactly this display key. */
export function positionMatchesDisplayKey(candidate: ValidationPositionCandidate, key: string): boolean {
  const expected = String(key || '').trim();
  return Boolean(expected) && candidate.key === expected;
}

/**
 * Rank of one control as a *correction* site. Lower is better.
 *
 * Document order cannot decide this. A value container may place a control that
 * only *configures* the value — a currency picker, a unit toggle, a clear
 * button — before the control that actually holds it, so taking the first match
 * sent the user to a control they cannot type in. The tiers below state the
 * order explicitly: a value holder first, then a configurator, then nothing.
 *
 * This is a display decision, not business ownership, so it stays DOM-free and
 * is exercised by the unit test and by the page from the same rule.
 */
export type CorrectionControlDescriptor = {
  tagName?: string;
  type?: string | null;
  tabIndex?: number | null;
  contentEditable?: boolean | string | null;
};

export function correctionControlRank(control: CorrectionControlDescriptor): number {
  const tag = String(control.tagName || '').toLowerCase();
  const type = String(control.type || '').toLowerCase();
  if (tag === 'textarea') return 0;
  if (tag === 'select') return 1;
  if (tag === 'input') {
    if (type === 'hidden' || type === 'button' || type === 'submit' || type === 'reset') return 5;
    if (type === 'checkbox' || type === 'radio') return 2;
    return 0;
  }
  if (control.contentEditable === true || control.contentEditable === 'true') return 1;
  if (typeof control.tabIndex === 'number' && control.tabIndex >= 0) return 3;
  if (tag === 'button') return 4;
  return 5;
}

/**
 * The control the user should be sent to, preserving input order inside a tier.
 *
 * Returns `null` for an empty list so the caller decides its own fallback
 * instead of receiving an invented element.
 */
export function selectCorrectionControl<T extends CorrectionControlDescriptor>(
  controls: readonly T[],
): T | null {
  let best: T | null = null;
  let bestRank = Number.POSITIVE_INFINITY;
  for (const control of controls || []) {
    const rank = correctionControlRank(control);
    if (rank < bestRank) {
      best = control;
      bestRank = rank;
    }
  }
  return best;
}
