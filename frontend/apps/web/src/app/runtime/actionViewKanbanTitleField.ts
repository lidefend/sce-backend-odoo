import { contractGapError } from '../contract/contractGap';

export function resolveDeclaredKanbanTitleField(titleFieldHint: string, kanbanFields: string[]): string {
  const hint = String(titleFieldHint || '').trim();
  const fields = Array.isArray(kanbanFields) ? kanbanFields.map((field) => String(field || '').trim()).filter(Boolean) : [];
  if (!fields.length) return '';
  if (!hint) throw contractGapError({
    kind: 'contract_defect',
    missing: 'list_profile.primary_field',
    requiredDeclarationLayer: 'P0:smart_core:contract_governance_list_surface.primary_field',
  }, 'Kanban profile requires a declared title field');
  if (!fields.includes(hint)) throw contractGapError({
    kind: 'contract_defect',
    missing: 'list_profile.primary_field',
    requiredDeclarationLayer: 'P0:smart_core:contract_governance_list_surface.primary_field',
  }, `Kanban title field ${hint} is not in the declared field set`);
  return hint;
}
