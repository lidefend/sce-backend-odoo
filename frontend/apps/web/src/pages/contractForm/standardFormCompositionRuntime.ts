/**
 * Which form sections render through the official composition, and the collected
 * result of their generic validation.
 *
 * The decision is presentation scope only; the registry exists so the save chain
 * can ask the adopted sections one question before it writes. Sections register
 * themselves, so a surface that is not adopted contributes nothing and the
 * page-level save path needs no per-surface wiring.
 *
 * Section validators report business field codes, never page positions. The
 * caller turns them into the same business errors the rest of the save chain
 * produces, so there stays exactly one error store, one message and one focus
 * entry for both adopted and unadopted sections.
 */
import { computed, inject, provide, type ComputedRef, type InjectionKey } from 'vue';
import {
  resolveStandardFormComposition,
  type StandardFormCompositionDecision,
} from '../../app/presentation/standardFormComposition';
import type { StandardPageTypeDecision } from '../../app/presentation/standardPageType';

export type StandardFormSectionValidator = {
  sectionId: string;
  /**
   * Business field codes this section actually evaluates rules for, i.e. the
   * positions it renders through the official engine. Reported so the save
   * chain can tell "the engine owns this rule" from "no rule covers it": only
   * the first may be excluded from the page-level generic precheck.
   */
  ruleFieldNames: () => string[];
  validate: () => Promise<string[]>;
};

export type StandardFormValidationOutcome = {
  /** False when a section could not be validated at all; the caller fails closed. */
  ok: boolean;
  fieldNames: string[];
  /** Field codes the official engine really evaluated during this run. */
  coveredFieldNames: string[];
};

export type StandardFormCompositionRuntime = {
  /** The composition this surface renders, and why. */
  decision: ComputedRef<StandardFormCompositionDecision>;
  adopted: ComputedRef<boolean>;
  register: (validator: StandardFormSectionValidator) => void;
  unregister: (sectionId: string) => void;
  validateAdoptedFields: () => Promise<StandardFormValidationOutcome>;
};

export const StandardFormCompositionKey: InjectionKey<StandardFormCompositionRuntime> =
  Symbol('sc:standard-form-composition');

/**
 * The registry itself, free of component context so the save-chain contract can
 * be exercised without mounting a page.
 *
 * `contractPageType` is the page's own contract-derived responsibility (see
 * `standardPageType.ts`); it is a thunk so the surface follows the contract when
 * the bound record, the route or the effective render profile changes.
 */
export function createStandardFormValidationRegistry(
  contractPageType: () => StandardPageTypeDecision,
): StandardFormCompositionRuntime {
  const decision = computed(() => resolveStandardFormComposition(contractPageType()));
  const adopted = computed(() => decision.value.adopted);
  const validators = new Map<string, StandardFormSectionValidator>();
  const runtime: StandardFormCompositionRuntime = {
    decision,
    adopted,
    register: (validator) => {
      validators.set(validator.sectionId, validator);
    },
    unregister: (sectionId) => {
      validators.delete(sectionId);
    },
    validateAdoptedFields: async () => {
      if (!adopted.value) return { ok: true, fieldNames: [], coveredFieldNames: [] };
      const fieldNames: string[] = [];
      const coveredFieldNames: string[] = [];
      for (const validator of [...validators.values()]) {
        try {
          coveredFieldNames.push(...validator.ruleFieldNames());
          fieldNames.push(...(await validator.validate()));
        } catch {
          // A section that cannot answer must not let the save through.
          return { ok: false, fieldNames: [], coveredFieldNames: [] };
        }
      }
      return {
        ok: true,
        fieldNames: [...new Set(fieldNames)],
        coveredFieldNames: [...new Set(coveredFieldNames)],
      };
    },
  };
  return runtime;
}

export function createStandardFormCompositionRuntime(
  contractPageType: () => StandardPageTypeDecision,
): StandardFormCompositionRuntime {
  const runtime = createStandardFormValidationRegistry(contractPageType);
  provide(StandardFormCompositionKey, runtime);
  return runtime;
}

export function useOptionalStandardFormComposition(): StandardFormCompositionRuntime | null {
  return inject(StandardFormCompositionKey, null);
}
