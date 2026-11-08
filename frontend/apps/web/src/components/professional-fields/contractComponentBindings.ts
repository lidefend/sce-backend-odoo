import type { FormSectionFieldSchema } from '../template/formSection.types';

export type ContractBaseControlKind =
  | 'text'
  | 'multiline'
  | 'html'
  | 'number'
  | 'selection'
  | 'boolean'
  | 'date'
  | 'datetime';

export type ContractBaseImplementationId =
  | 'ScInput'
  | 'ScTextarea'
  | 'RestrictedHtmlEditor'
  | 'ScNumberInput'
  | 'ScSelect'
  | 'ScCheckbox'
  | 'ScDateField';

export type ContractBaseComponentBinding = {
  bindingId: string;
  componentKey: string;
  fieldTypes: readonly string[];
  controlKind: ContractBaseControlKind;
  implementation: ContractBaseImplementationId;
};

function binding(
  componentKey: string,
  fieldTypes: readonly string[],
  controlKind: ContractBaseControlKind,
  implementation: ContractBaseImplementationId,
): ContractBaseComponentBinding {
  return Object.freeze({
    bindingId: `${componentKey}:${fieldTypes.join('|')}`,
    componentKey,
    fieldTypes: Object.freeze([...fieldTypes]),
    controlKind,
    implementation,
  });
}

/**
 * The V1 base-field implementation map.
 *
 * Keys are stable Contract component identities. ``fieldType`` is the declared
 * Contract variant that disambiguates identities such as sc.input.textarea,
 * whose editable text and HTML implementations intentionally differ. This is
 * not a second component vocabulary: every key is checked against the generated
 * Contract carrier by the focused binding test and guard.
 */
export const CONTRACT_BASE_COMPONENT_BINDINGS: readonly ContractBaseComponentBinding[] = Object.freeze([
  binding('sc.input.text', ['char'], 'text', 'ScInput'),
  binding('sc.input.textarea', ['text'], 'multiline', 'ScTextarea'),
  binding('sc.input.textarea', ['html'], 'html', 'RestrictedHtmlEditor'),
  binding('sc.input.number', ['integer', 'float'], 'number', 'ScNumberInput'),
  binding('sc.select.remote', ['selection'], 'selection', 'ScSelect'),
  binding('sc.input.boolean', ['boolean'], 'boolean', 'ScCheckbox'),
  binding('sc.input.date', ['date'], 'date', 'ScDateField'),
  binding('sc.input.datetime', ['datetime'], 'datetime', 'ScDateField'),

  // These declared component identities still resolve through the shared base
  // field family. Their concrete control remains the Contract field-type
  // variant; no model, field-name or page-name inference is involved.
  binding('sc.auth.credential_entry', ['char'], 'text', 'ScInput'),
  binding('sc.auth.secret_confirmation', ['char'], 'text', 'ScInput'),
  binding('sc.auth.challenge_status', ['char'], 'text', 'ScInput'),
  binding('sc.auth.challenge_status', ['text'], 'multiline', 'ScTextarea'),
  binding('sc.auth.challenge_status', ['selection'], 'selection', 'ScSelect'),
  binding('sc.display.text', ['char'], 'text', 'ScInput'),
  binding('sc.display.text', ['text'], 'multiline', 'ScTextarea'),
  binding('sc.display.text', ['html'], 'html', 'RestrictedHtmlEditor'),
  binding('sc.display.text', ['integer', 'float'], 'number', 'ScNumberInput'),
  binding('sc.display.text', ['selection'], 'selection', 'ScSelect'),
  binding('sc.display.text', ['boolean'], 'boolean', 'ScCheckbox'),
  binding('sc.display.text', ['date'], 'date', 'ScDateField'),
  binding('sc.display.text', ['datetime'], 'datetime', 'ScDateField'),
]);

function normalizedIdentity(value: unknown): string {
  return String(value || '').trim();
}

export function resolveContractBaseComponentBinding(
  field: Pick<FormSectionFieldSchema, 'componentKey' | 'type'>,
): ContractBaseComponentBinding | null {
  const componentKey = normalizedIdentity(field.componentKey);
  const fieldType = normalizedIdentity(field.type).toLowerCase();
  if (!componentKey || !fieldType) return null;
  return CONTRACT_BASE_COMPONENT_BINDINGS.find((candidate) => (
    candidate.componentKey === componentKey
    && candidate.fieldTypes.includes(fieldType)
  )) || null;
}

export function contractBaseComponentBindingKeys(): string[] {
  return [...new Set(CONTRACT_BASE_COMPONENT_BINDINGS.map((entry) => entry.componentKey))];
}
