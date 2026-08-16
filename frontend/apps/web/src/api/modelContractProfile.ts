export type ModelContractRenderProfile = 'create' | 'edit' | 'readonly';

export function resolveModelContractRenderProfile(input: {
  viewType?: string | null;
  recordId?: number | null;
  renderProfile?: string | null;
}): ModelContractRenderProfile | '' {
  const explicit = String(input.renderProfile || '').trim().toLowerCase();
  if (explicit === 'create' || explicit === 'edit' || explicit === 'readonly') return explicit;
  const viewType = String(input.viewType || 'form').trim().toLowerCase();
  const recordId = Number(input.recordId || 0);
  return viewType === 'form' && !(Number.isFinite(recordId) && recordId > 0) ? 'create' : '';
}
