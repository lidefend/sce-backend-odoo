import { config } from '../config';
import { resolveConfiguredDb } from './dbContext';

interface ActivationStartResponse {
  ok: boolean;
  message?: string;
  activation_context?: string;
  expires_in_seconds?: string;
}

interface ActivationCompleteResponse {
  ok: boolean;
  message?: string;
}

async function activationRequest<T>(path: string, body?: Record<string, string>): Promise<T> {
  const headers = new Headers({
    Accept: 'application/json',
    'Content-Type': 'application/json',
    'X-Tenant': config.tenant,
  });
  const db = resolveConfiguredDb(String(config.odooDb || '').trim());
  if (db) headers.set('X-Odoo-DB', db);
  const response = await fetch(`${config.apiBaseUrl}${path}`, {
    method: body ? 'POST' : 'GET',
    headers,
    body: body ? JSON.stringify(body) : undefined,
    cache: 'no-store',
    credentials: 'omit',
    referrerPolicy: 'no-referrer',
  });
  const payload = await response.json().catch(() => ({ ok: false })) as T & { message?: string };
  if (!response.ok) throw new Error(payload.message || '请求未完成');
  return payload;
}

export function beginAccountActivation(activationCode: string) {
  return activationRequest<ActivationStartResponse>('/api/v1/auth/activation/start', {
    activation_code: activationCode,
  });
}

export function completeAccountActivation(activationContext: string, password: string, confirmPassword: string) {
  return activationRequest<ActivationCompleteResponse>('/api/v1/auth/activation/complete', {
    activation_context: activationContext,
    password,
    confirm_password: confirmPassword,
  });
}

export function getPasswordRecoveryStatus() {
  return activationRequest<{ ok: boolean; self_service_enabled: boolean; message: string }>(
    '/api/v1/auth/password-recovery/status',
  );
}
