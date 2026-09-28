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
