/** Standard contract record pages share one form composition, including their
 * relation and master/detail extensions. Adoption never grants write access.
 * Dedicated worksheets and pages without this responsibility keep their own
 * renderer; field-engine capability decisions remain in the existing adapter.
 */
export type StandardFormCompositionId = 'official-standard-form' | 'legacy-form-section';
export type StandardFormCompositionReason = 'standard-page-type' | 'specialized-page-type';
export type StandardFormCompositionDecision = {
  composition: StandardFormCompositionId;
  adopted: boolean;
  reason: StandardFormCompositionReason;
};
export function resolveStandardFormComposition(input: { pageType?: unknown }): StandardFormCompositionDecision {
  return input.pageType === 'contract-record-form'
    ? { composition: 'official-standard-form', adopted: true, reason: 'standard-page-type' }
    : { composition: 'legacy-form-section', adopted: false, reason: 'specialized-page-type' };
}
