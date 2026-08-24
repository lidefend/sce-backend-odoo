import type { CanonicalFormPresentationMode, CanonicalFormRenderMode } from '../../app/presentation/canonicalFormRenderModel';

export const PROFESSIONAL_BASE_FIELD_TYPES = Object.freeze([
  'char', 'text', 'html', 'integer', 'float', 'date', 'datetime', 'boolean', 'selection',
] as const);

export type ProfessionalBaseFieldType = typeof PROFESSIONAL_BASE_FIELD_TYPES[number];
export type ProfessionalBaseControlKind = 'text' | 'multiline' | 'number' | 'date' | 'datetime' | 'boolean' | 'selection';
export type ProfessionalFieldPresentationContext = CanonicalFormPresentationMode | 'unscoped';
export type ProfessionalFieldRenderContext = CanonicalFormRenderMode | 'unscoped';

const SPECIAL_WIDGETS = new Set(['radio', 'daterange']);

export function isProfessionalBaseFieldCandidate(fieldType: string, widget = ''): boolean {
  return PROFESSIONAL_BASE_FIELD_TYPES.includes(fieldType.trim().toLowerCase() as ProfessionalBaseFieldType)
    && !SPECIAL_WIDGETS.has(widget.trim().toLowerCase());
}

export function resolveProfessionalBaseFieldModel(input: {
  fieldType: string;
  widget?: string;
  presentationMode: ProfessionalFieldPresentationContext;
  renderProfile: ProfessionalFieldRenderContext;
  readonly?: boolean;
}): {
  fieldType: ProfessionalBaseFieldType;
  controlKind: ProfessionalBaseControlKind;
  presentationMode: ProfessionalFieldPresentationContext;
  renderProfile: ProfessionalFieldRenderContext;
  controlState: 'editable' | 'readonly';
} {
  const fieldType = input.fieldType.trim().toLowerCase() as ProfessionalBaseFieldType;
  if (!isProfessionalBaseFieldCandidate(fieldType, input.widget)) {
    throw new Error(`PROFESSIONAL_BASE_FIELD_UNSUPPORTED:${input.fieldType}:${input.widget || ''}`);
  }
  const controlKind: ProfessionalBaseControlKind = fieldType === 'text' || fieldType === 'html'
    ? 'multiline'
    : fieldType === 'integer' || fieldType === 'float'
      ? 'number'
      : fieldType === 'char'
        ? 'text'
        : fieldType;
  return Object.freeze({
    fieldType,
    controlKind,
    presentationMode: input.presentationMode,
    renderProfile: input.renderProfile,
    controlState: input.readonly || input.renderProfile === 'readonly' ? 'readonly' : 'editable',
  });
}
