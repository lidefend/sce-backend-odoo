/**
 * Which standard query lists render through the official list composition.
 *
 * Presentation scope only. This decides *how* an already-authorized list is
 * composed; it never decides which columns exist, which records are readable,
 * which actions are allowed, or who may read the page. Adoption is therefore
 * never derived from field names, column labels, semantic roles, action IDs,
 * menu IDs, roles, or renderer selection, and it is never an authorization
 * input.
 *
 * The official source is the reference list page `src/pages/list/base/index.vue`
 * of `Tencent/tdesign-vue-next-starter`
 * (`aeed57076217f7777158b905f353d73585bad1c4`); it is a reference baseline, not
 * a dependency upgrade. The pilot list is intentionally explicit: a list is
 * adopted because it has been verified against the official composition, not
 * because it resembles one.
 */

export type StandardListCompositionId = 'official-standard-list' | 'legacy-list-surface';

export type StandardListCompositionReason =
  | 'pilot-model-adopted'
  | 'outside-pilot-scope';

export type StandardListCompositionDecision = {
  composition: StandardListCompositionId;
  adopted: boolean;
  reason: StandardListCompositionReason;
};

/**
 * Models whose standard query list is served by the official composition.
 *
 * Every entry is a surface this project has verified against the official
 * composition. The list is what makes a second model a *reuse* rather than a
 * second implementation: the list surface never names a model, so a business
 * model joins by being listed here and by carrying a contract the collection
 * renderer already understands.
 */
export const STANDARD_LIST_COMPOSITION_PILOT_MODELS: readonly string[] = Object.freeze([
  'project.project',
  'sc.general.contract',
]);

export function resolveStandardListComposition(input: { model?: unknown }): StandardListCompositionDecision {
  const model = String(input?.model ?? '').trim();
  if (model && STANDARD_LIST_COMPOSITION_PILOT_MODELS.includes(model)) {
    return { composition: 'official-standard-list', adopted: true, reason: 'pilot-model-adopted' };
  }
  return { composition: 'legacy-list-surface', adopted: false, reason: 'outside-pilot-scope' };
}
