import { intentRequest } from './intents';

export type CredentialState = 'active' | 'revoked' | 'expired';

export interface AuthCredentialPolicy {
  credential_id: string;
  name: string;
  state: CredentialState;
  scope: string[];
  company_ids: number[];
  expires_at: string | false;
  last_used_at: string | false;
  usage_count: number;
  created_at: string | false;
  rotated_from_credential_id: string;
}

export interface OneTimeCredentialResult {
  credential: AuthCredentialPolicy;
  api_key: string;
  secret_display: 'once';
}

export async function listAuthCredentials(): Promise<AuthCredentialPolicy[]> {
  const result = await intentRequest<{ credentials?: AuthCredentialPolicy[]; secret_returned?: boolean }>({
    intent: 'auth.credential.list',
  });
  return Array.isArray(result.credentials) ? result.credentials : [];
}

export function createAuthCredential(params: {
  name: string;
  password: string;
  scope: string[];
  companyIds: number[];
  expiresAt?: string;
}): Promise<OneTimeCredentialResult> {
  return intentRequest<OneTimeCredentialResult>({
    intent: 'auth.credential.create',
    params: {
      name: params.name,
      scope: params.scope,
      company_ids: params.companyIds,
      expires_at: params.expiresAt || false,
      credential: { type: 'password', secret: params.password },
    },
  });
}

export function rotateAuthCredential(credentialId: string, password: string): Promise<OneTimeCredentialResult> {
  return intentRequest<OneTimeCredentialResult>({
    intent: 'auth.credential.rotate',
    params: {
      credential_id: credentialId,
      credential: { type: 'password', secret: password },
    },
  });
}

export function revokeAuthCredential(credentialId: string): Promise<{ credential: AuthCredentialPolicy; sessions_invalidated: boolean }> {
  return intentRequest<{ credential: AuthCredentialPolicy; sessions_invalidated: boolean }>({
    intent: 'auth.credential.revoke',
    params: { credential_id: credentialId },
  });
}
