/** Standard contract record pages share one form composition, including their
 * relation and master/detail extensions. Adoption never grants write access.
 * Dedicated worksheets and pages without this responsibility keep their own
 * renderer; field-engine capability decisions remain in the existing adapter.
 *
 * The page type is an input, never a guess: it comes from
 * `standardPageType.ts`, which reads `pageInfo.viewType` plus the page's
 * effective render profile. A surface the contract did not declare as a record
 * form keeps `legacy-form-section`, which is a real second renderer here: the
 * sections render bare, without the official engine rules and without the
 * adopted-detail facts layout.
 */
import type { StandardPageType, StandardPageTypeReason } from './standardPageType';

export type StandardFormCompositionId = 'official-standard-form' | 'legacy-form-section';

export type StandardFormCompositionReason = StandardPageTypeReason;

export type StandardFormCompositionDecision = {
  composition: StandardFormCompositionId;
  adopted: boolean;
  reason: StandardFormCompositionReason;
};

export function resolveStandardFormComposition(input: {
  pageType?: StandardPageType;
  reason?: StandardPageTypeReason;
}): StandardFormCompositionDecision {
  // A page the contract did not declare as a record form keeps the bare section
  // renderer it names, and the reason it reports is the contract's own
  // classification, passed through instead of collapsed: a readonly record
  // ("contract-readonly-record-view") and a page the contract never classified
  // ("contract-view-not-classified") are different answers, and publishing the
  // second for the first would claim the contract said nothing when it did.
  return input?.pageType === 'record-form'
    ? { composition: 'official-standard-form', adopted: true, reason: 'contract-record-view' }
    : { composition: 'legacy-form-section', adopted: false, reason: input?.reason ?? 'contract-view-not-classified' };
}
