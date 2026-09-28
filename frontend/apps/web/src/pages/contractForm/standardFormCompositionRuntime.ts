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
import { resolveStandardFormComposition } from '../../app/presentation/standardFormComposition';

export type StandardFormSectionValidator = {
  sectionId: string;
  validate: () => Promise<string[]>;
};

export type StandardFormValidationOutcome = {
  /** False when a section could not be validated at all; the caller fails closed. */
  ok: boolean;
  fieldNames: string[];
};

export type StandardFormCompositionRuntime = {
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
 */
export function createStandardFormValidationRegistry(
  model: () => string,
): StandardFormCompositionRuntime {
  const adopted = computed(() => resolveStandardFormComposition({ model: model() }).adopted);
  const validators = new Map<string, StandardFormSectionValidator>();
  const runtime: StandardFormCompositionRuntime = {
    adopted,
    register: (validator) => {
      validators.set(validator.sectionId, validator);
    },
    unregister: (sectionId) => {
      validators.delete(sectionId);
    },
    validateAdoptedFields: async () => {
      if (!adopted.value) return { ok: true, fieldNames: [] };
      const fieldNames: string[] = [];
      for (const validator of [...validators.values()]) {
        try {
          fieldNames.push(...(await validator.validate()));
        } catch {
          // A section that cannot answer must not let the save through.
          return { ok: false, fieldNames: [] };
        }
      }
      return { ok: true, fieldNames: [...new Set(fieldNames)] };
    },
  };
  return runtime;
}

export function createStandardFormCompositionRuntime(
  model: () => string,
): StandardFormCompositionRuntime {
  const runtime = createStandardFormValidationRegistry(model);
  provide(StandardFormCompositionKey, runtime);
  return runtime;
}

export function useOptionalStandardFormComposition(): StandardFormCompositionRuntime | null {
  return inject(StandardFormCompositionKey, null);
}
