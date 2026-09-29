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
import type { StandardPageType } from './standardPageType';

export type StandardFormCompositionId = 'official-standard-form' | 'legacy-form-section';

export type StandardFormCompositionReason =
  | 'contract-record-view'
  | 'contract-view-conflict'
  | 'contract-view-not-classified';

export type StandardFormCompositionDecision = {
  composition: StandardFormCompositionId;
  adopted: boolean;
  reason: StandardFormCompositionReason;
};

export function resolveStandardFormComposition(input: {
  pageType?: StandardPageType;
}): StandardFormCompositionDecision {
  return input?.pageType === 'record-form'
    ? { composition: 'official-standard-form', adopted: true, reason: 'contract-record-view' }
    : { composition: 'legacy-form-section', adopted: false, reason: 'contract-view-not-classified' };
}
