export type ContractRenderProfile = 'create' | 'edit' | 'readonly';

export function contractLoadProfileOptions(profile: ContractRenderProfile): {
  renderProfile: ContractRenderProfile;
} {
  return { renderProfile: profile };
}

export function resolveRequestedContractRenderProfile(input: {
  routeName: unknown;
  recordId: number | null;
}): ContractRenderProfile {
  const routeName = String(input.routeName || '').trim();
  if (routeName === 'record') return 'readonly';
  if (routeName === 'model-form') return input.recordId ? 'edit' : 'create';
  return input.recordId ? 'edit' : 'create';
}

export function resolveEffectiveContractRenderProfile(input: {
  backendProfile?: unknown;
  normalizedReady: boolean;
  requestedProfile: ContractRenderProfile;
}): ContractRenderProfile {
  const backendProfile = String(input.backendProfile || '').trim().toLowerCase();
  if (backendProfile === 'readonly' || backendProfile === 'edit' || backendProfile === 'create') {
    return backendProfile;
  }
  return input.normalizedReady ? 'readonly' : input.requestedProfile;
}
