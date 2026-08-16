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
  const routeName = String(input.routeName || '').trim();
  if (routeName === 'record') return 'readonly';
  // The current route/record identity is authoritative. In particular, a
  // contract loaded for /f/:model/new must not keep the page in create mode
  // after saving navigates to /f/:model/:id.
  if (routeName === 'model-form') return input.recordId ? 'edit' : 'create';

  const contractProfile = String(input.contractProfile || '').trim().toLowerCase();
  if (contractProfile === 'readonly' || contractProfile === 'edit' || contractProfile === 'create') {
    return contractProfile;
  }
  if (!input.canSave) return 'readonly';
  return input.recordId ? 'edit' : 'create';
}
