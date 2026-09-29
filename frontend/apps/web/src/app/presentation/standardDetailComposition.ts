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
 *
 * Page adoption and section eligibility are two separate questions and stay
 * separate: `resolveStandardDetailFactLayout` answers the first from this
 * decision alone, `resolveStandardDetailSection` answers the second from the
 * section's own fields. Folding them into the form composition's adoption would
 * make the facts layout unreachable, because a page is never both a record form
 * and a record detail.
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

/**
 * Whether a section renders its readonly facts through the adopted detail
 * composition.
 *
 * The page-level term is the *detail* decision and nothing else. The record
 * form composition is the other half of the same classification
 * (`record-form` versus `record-detail`), so a contract never declares one page
 * as both; requiring the form composition to be adopted here as well would make
 * the facts layout unreachable on every page, including the readonly record it
 * exists for. Sections on an editable record form already fail this gate
 * because the contract classified the page as a record form, not a record
 * detail — no second conjunction is needed to keep them on their controls.
 */
export function resolveStandardDetailFactLayout(
  decision: StandardDetailCompositionDecision | null | undefined,
  section: {
    configurationMode: boolean;
    readonlyFacts: boolean;
    fields: readonly { type: string; dedicatedControl: boolean }[];
  },
): { adopted: boolean; reason: string } {
  return resolveStandardDetailSection({ adopted: decision?.adopted === true, ...section });
}

/**
 * The section-level half of the same question: does *this* section qualify to
 * present its fields as facts. `adopted` is the page-level detail adoption
 * supplied by the caller (see `resolveStandardDetailFactLayout`), never the
 * form composition's adoption.
 */
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
