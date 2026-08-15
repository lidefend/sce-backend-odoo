export type ContractRenderProfile = 'create' | 'edit' | 'readonly';

export function contractLoadProfileOptions(profile: ContractRenderProfile): {
  renderProfile: ContractRenderProfile;
} {
  return { renderProfile: profile };
}

export function resolveContractRenderProfile(input: {
  routeName: unknown;
  contractProfile?: unknown;
  canSave: boolean;
  recordId: number | null;
}): ContractRenderProfile {
  if (String(input.routeName || '').trim() === 'record') return 'readonly';

  const contractProfile = String(input.contractProfile || '').trim().toLowerCase();
  if (contractProfile === 'readonly' || contractProfile === 'edit' || contractProfile === 'create') {
    return contractProfile;
  }
  if (!input.canSave) return 'readonly';
  return input.recordId ? 'edit' : 'create';
}
