/**
 * The generic field rules the official form engine evaluates for a contract
 * section, and the reading of that engine's result.
 *
 * The engine owns *when* rules run, how results are collected, and how they are
 * presented. It does not own what "empty" means: every rule delegates to the
 * same `isRequiredFieldEmptyByType` the pre-existing save precheck uses, so an
 * adopted section and an unadopted one can never disagree about the same value.
 * A rule is therefore only a declaration of *which* fields take part in generic
 * validation, not a second definition of the business rule.
 *
 * Read-only positions never produce a rule: an error that cannot be corrected
 * here belongs to a position the user can edit, and the page-level error
 * resolution decides where to send them.
 */
import { isRequiredFieldEmptyByType } from '../../pages/contractForm/valueUtils';
import type { FormSectionFieldSchema } from './formSection.types';

export type ContractFormFieldRule = {
  validator: () => boolean;
  message: string;
};

/** The draft value an adopted control is currently showing. */
export function adoptedValidationValue(field: FormSectionFieldSchema): unknown {
  return field.inputValue === undefined ? field.value : field.inputValue;
}

export function requiredFieldMessage(label: string): string {
  return `${String(label || '').trim()}不能为空`;
}

export function contractFormFieldRules(field: FormSectionFieldSchema): ContractFormFieldRule[] {
  const name = String(field.name || '').trim();
  if (!name || !field.required || field.readonly) return [];
  const label = String(field.label || name).trim();
  return [{
    // The engine passes the value it can see; the answer comes from the shared
    // emptiness authority instead, so both paths answer the same way.
    validator: () => !isRequiredFieldEmptyByType(adoptedValidationValue(field), String(field.type || '')),
    message: requiredFieldMessage(label),
  }];
}

export function buildContractFormRules(
  fields: readonly FormSectionFieldSchema[],
): Record<string, ContractFormFieldRule[]> {
  const rules: Record<string, ContractFormFieldRule[]> = {};
  fields.forEach((field) => {
    const name = String(field.name || '').trim();
    if (!name) return;
    const fieldRules = contractFormFieldRules(field);
    if (fieldRules.length) rules[name] = fieldRules;
  });
  return rules;
}

/**
 * Field names the engine rejected.
 *
 * The engine resolves with `true` when everything passed, and with an object
 * holding only the rejected names otherwise. A shape this reader does not
 * recognise is reported as "nothing failed" by the caller's own fail-closed
 * check rather than guessed at here.
 */
export function failedAdoptedFieldNames(result: unknown): string[] {
  if (!result || result === true) return [];
  if (typeof result !== 'object' || Array.isArray(result)) return [];
  return Object.keys(result as Record<string, unknown>).map((key) => key.trim()).filter(Boolean);
}
