/**
 * Which standard form surfaces render through the official form composition.
 *
 * Presentation scope only. This decides *how* an already-authorized standard
 * form is composed; it never decides what a field means, whether it is
 * writable, or who may read it. Adoption is therefore never derived from field
 * names, semantic roles, action IDs, menu IDs, roles, or renderer selection,
 * and it is never an authorization input.
 *
 * The pilot list is intentionally explicit: a surface is adopted because it has
 * been verified against the official composition, not because it resembles one.
 */

export type StandardFormCompositionId = 'official-standard-form' | 'legacy-form-section';

export type StandardFormCompositionReason =
  | 'pilot-model-adopted'
  | 'outside-pilot-scope';

export type StandardFormCompositionDecision = {
  composition: StandardFormCompositionId;
  adopted: boolean;
  reason: StandardFormCompositionReason;
};

/**
 * Models whose standard form is served by the official composition.
 *
 * Every entry is a surface this project has verified against the official
 * composition. The list is what makes a second model a *reuse* rather than a
 * second implementation: the call sites never name a model, so a surface joins
 * by being listed here and by carrying a contract the composition already
 * understands.
 */
export const STANDARD_FORM_COMPOSITION_PILOT_MODELS: readonly string[] = Object.freeze([
  'project.project',
  'sc.general.contract',
]);

export function resolveStandardFormComposition(input: { model?: unknown }): StandardFormCompositionDecision {
  const model = String(input?.model ?? '').trim();
  if (model && STANDARD_FORM_COMPOSITION_PILOT_MODELS.includes(model)) {
    return { composition: 'official-standard-form', adopted: true, reason: 'pilot-model-adopted' };
  }
  return { composition: 'legacy-form-section', adopted: false, reason: 'outside-pilot-scope' };
}
