/**
 * Which readonly record surfaces render through the official detail composition.
 *
 * Presentation scope only. This decides *how* an already-authorized readonly
 * record is composed; it never decides which fields exist, which values may be
 * shown, or who may read the record. Adoption is therefore never derived from
 * field names, labels, semantic roles, action IDs, menu IDs, roles, or renderer
 * selection, and it is never an authorization input.
 *
 * The official source is the reference detail page `src/pages/detail/base/index.vue`
 * of `Tencent/tdesign-vue-next-starter`
 * (`aeed57076217f7777158b905f353d73585bad1c4`); it is a reference baseline, not
 * a dependency upgrade. Its `t-descriptions` label/value composition is the
 * official readonly presentation; its sample data is not, so this project
 * grounds every item in the record's own contract field facts.
 *
 * Only the `readonly` render profile is in scope. An editable surface keeps its
 * previous composition, because the official detail page has no editing state.
 */

export type StandardDetailCompositionId = 'official-standard-detail' | 'legacy-detail-surface';

export type StandardDetailCompositionReason =
  | 'pilot-model-adopted'
  | 'outside-pilot-scope'
  | 'not-a-readonly-profile';

export type StandardDetailCompositionDecision = {
  composition: StandardDetailCompositionId;
  adopted: boolean;
  reason: StandardDetailCompositionReason;
};

/**
 * Models whose standard readonly record is served by the official detail
 * composition.
 *
 * Every entry is a surface this project has verified against the official
 * composition. The detail surface never names a model, so a business model
 * joins by being listed here and by carrying a contract the detail renderer
 * already understands.
 */
export const STANDARD_DETAIL_COMPOSITION_PILOT_MODELS: readonly string[] = Object.freeze([
  'sc.general.contract',
]);

export function resolveStandardDetailComposition(input: {
  model?: unknown;
  renderProfile?: unknown;
}): StandardDetailCompositionDecision {
  const model = String(input?.model ?? '').trim();
  const renderProfile = String(input?.renderProfile ?? '').trim();
  if (renderProfile !== 'readonly') {
    return { composition: 'legacy-detail-surface', adopted: false, reason: 'not-a-readonly-profile' };
  }
  if (model && STANDARD_DETAIL_COMPOSITION_PILOT_MODELS.includes(model)) {
    return { composition: 'official-standard-detail', adopted: true, reason: 'pilot-model-adopted' };
  }
  return { composition: 'legacy-detail-surface', adopted: false, reason: 'outside-pilot-scope' };
}
