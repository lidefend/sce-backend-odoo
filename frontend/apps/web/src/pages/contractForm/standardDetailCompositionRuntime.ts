/**
 * Which readonly record surfaces render their facts through the official detail
 * composition, decided once per page and read by the sections that render them.
 *
 * It is the readonly counterpart of `standardFormCompositionRuntime`: the page
 * resolves the decision from its own model and render profile, provides it, and
 * every section asks the same instance instead of deciding for itself. A page
 * that provides nothing (no official detail pilot) keeps the composition it had.
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

export type StandardDetailCompositionRuntime = {
  decision: ComputedRef<StandardDetailCompositionDecision>;
  adopted: ComputedRef<boolean>;
};

export const StandardDetailCompositionKey: InjectionKey<StandardDetailCompositionRuntime> =
  Symbol('sc:standard-detail-composition');

export function createStandardDetailCompositionRuntime(
  model: () => string,
  renderProfile: () => string,
): StandardDetailCompositionRuntime {
  const decision = computed(() => resolveStandardDetailComposition({
    model: model(),
    renderProfile: renderProfile(),
  }));
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
