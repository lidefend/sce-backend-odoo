/**
 * Which readonly record surfaces render their facts through the official detail
 * composition, decided once per page and read by the sections that render them.
 *
 * It is the readonly counterpart of `standardFormCompositionRuntime`: the page
 * resolves its own contract-derived responsibility once (see
 * `standardPageType.ts`), provides it, and every section asks the same instance
 * instead of deciding for itself. A page that provides nothing keeps the
 * composition it had.
 *
 * The decision is presentation scope only. It never decides which fields exist,
 * which values may be shown, or who may read the record; those stay with the
 * contract and the backend.
 */
import { computed, inject, provide, type ComputedRef, type InjectionKey } from 'vue';
import {
  resolveStandardDetailComposition,
  type StandardDetailCompositionDecision,
} from '../../app/presentation/standardDetailComposition';
import type { StandardPageTypeDecision } from '../../app/presentation/standardPageType';

export type StandardDetailCompositionRuntime = {
  decision: ComputedRef<StandardDetailCompositionDecision>;
  adopted: ComputedRef<boolean>;
};

export const StandardDetailCompositionKey: InjectionKey<StandardDetailCompositionRuntime> =
  Symbol('sc:standard-detail-composition');

export function createStandardDetailCompositionRuntime(
  contractPageType: () => StandardPageTypeDecision,
): StandardDetailCompositionRuntime {
  const decision = computed(() => resolveStandardDetailComposition(contractPageType()));
  const runtime: StandardDetailCompositionRuntime = {
    decision,
    adopted: computed(() => decision.value.adopted),
  };
  provide(StandardDetailCompositionKey, runtime);
  return runtime;
}

export function useOptionalStandardDetailComposition(): StandardDetailCompositionRuntime | null {
  return inject(StandardDetailCompositionKey, null);
}
