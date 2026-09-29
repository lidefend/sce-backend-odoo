/** Official list reference: Tencent/tdesign-vue-next-starter@aeed57076217f7777158b905f353d73585bad1c4.
 * Adoption follows the existing page responsibility. Business capabilities,
 * server query state and authorization remain with the effective contract.
 */
export type StandardListCompositionId = 'official-standard-list' | 'legacy-list-surface';
export type StandardListCompositionReason = 'standard-page-type' | 'specialized-page-type';
export type StandardListCompositionDecision = {
  composition: StandardListCompositionId;
  adopted: boolean;
  reason: StandardListCompositionReason;
};
export function resolveStandardListComposition(input: { pageType?: unknown }): StandardListCompositionDecision {
  return input.pageType === 'standard-query-list'
    ? { composition: 'official-standard-list', adopted: true, reason: 'standard-page-type' }
    : { composition: 'legacy-list-surface', adopted: false, reason: 'specialized-page-type' };
}
