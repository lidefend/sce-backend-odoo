/** Official detail reference: Tencent/tdesign-vue-next-starter@aeed57076217f7777158b905f353d73585bad1c4.
 * A readonly record has one composition, with explicit collection/attachment
 * extensions. Section capabilities decide whether descriptions can carry facts.
 *
 * The project renders readonly records through exactly one surface: the record
 * page in its readonly render profile.  There is no second detail renderer that
 * a "not adopted" answer could fall back to, so the decision carries a single
 * composition value and claiming a legacy one would misreport the shipped
 * state.  What the decision really carries is whether the effective contract
 * declared the readonly-record responsibility that this surface owns, and the
 * contract's own page-type reason for the answer.
 *
 * Its input is the contract-derived page-type decision from
 * `standardPageType.ts` (`pageInfo.viewType` together with the page's effective
 * render profile), so an edit form is never treated as a readonly record and a
 * record the contract declares readonly is a detail even when the route asked
 * for the edit form.
 */
import type { StandardPageTypeDecision, StandardPageTypeReason } from './standardPageType';

export type StandardDetailCompositionId = 'official-standard-detail';

export type StandardDetailCompositionReason = StandardPageTypeReason;

export type StandardDetailCompositionDecision = {
  composition: StandardDetailCompositionId;
  adopted: boolean;
  reason: StandardDetailCompositionReason;
};

export function resolveStandardDetailComposition(
  decision: StandardPageTypeDecision,
): StandardDetailCompositionDecision {
  // The reason is the contract's own page-type reason, passed through instead
  // of collapsed into one label: "the contract declared an editable record",
  // "the contract declared conflicting views" and "the contract did not
  // classify this page" are three different answers, and a caller has to act
  // on the difference.  The single composition value names the surface that
  // renders the page either way; adoption, not a renderer identity, is what
  // the answer carries.
  return {
    composition: 'official-standard-detail',
    adopted: decision?.pageType === 'record-detail',
    reason: decision?.reason ?? 'contract-view-not-classified',
  };
}

export function resolveStandardDetailSection(input: {
  adopted: boolean;
  configurationMode: boolean;
  readonlyFacts: boolean;
  fields: readonly { type: string; dedicatedControl: boolean }[];
}): { adopted: boolean; reason: string } {
  if (!input.adopted) return { adopted: false, reason: 'outside-standard-detail' };
  if (input.configurationMode) return { adopted: false, reason: 'configuration-editor' };
  if (!input.readonlyFacts) return { adopted: false, reason: 'editable-section' };
  if (!input.fields.length) return { adopted: false, reason: 'empty-section' };
  if (input.fields.some((field) => ['one2many', 'many2many'].includes(field.type))) return { adopted: false, reason: 'relation-collection-extension' };
  if (input.fields.some((field) => field.type === 'binary')) return { adopted: false, reason: 'attachment-extension' };
  if (input.fields.some((field) => field.dedicatedControl)) return { adopted: false, reason: 'dedicated-control-extension' };
  const factTypes = ['char', 'text', 'selection', 'many2one', 'boolean', 'date', 'datetime', 'integer', 'float', 'monetary', 'html'];
  if (input.fields.some((field) => !factTypes.includes(field.type))) return { adopted: false, reason: 'unsupported-fact-type' };
  return { adopted: true, reason: 'standard-readonly-facts' };
}
