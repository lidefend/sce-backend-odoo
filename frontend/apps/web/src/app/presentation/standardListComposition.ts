/** Official list reference: Tencent/tdesign-vue-next-starter@aeed57076217f7777158b905f353d73585bad1c4.
 *
 * The project renders collections through exactly one surface, so the decision
 * below has a single composition value: there is no second list renderer that a
 * "not adopted" answer could fall back to, and claiming one would misreport the
 * shipped state.  What the decision really carries is whether the effective
 * contract declared the collection responsibility that this surface owns.
 *
 * The page type is an input, never a guess: it comes from
 * `standardPageType.ts`, which reads `pageInfo.viewType`.  Business
 * capabilities, server query state and authorization remain with the effective
 * contract; this policy only names which of the project's own compositions
 * frames an already-authorized page.
 */
import type { StandardPageTypeDecision, StandardPageTypeReason } from './standardPageType';

export type StandardListCompositionId = 'official-standard-list';

export type StandardListCompositionReason = StandardPageTypeReason;

export type StandardListCompositionDecision = {
  composition: StandardListCompositionId;
  adopted: boolean;
  reason: StandardListCompositionReason;
};

export function resolveStandardListComposition(
  decision: StandardPageTypeDecision,
): StandardListCompositionDecision {
  return decision?.pageType === 'query-list'
    ? { composition: 'official-standard-list', adopted: true, reason: decision.reason }
    : {
      composition: 'official-standard-list',
      adopted: false,
      // The contract's own classification, passed through: a page the contract
      // declared as a record form or a readonly record is not the same answer
      // as a page it never classified, and publishing the second for the first
      // would misreport what the contract said.
      reason: decision?.reason ?? 'contract-view-not-classified',
    };
}
