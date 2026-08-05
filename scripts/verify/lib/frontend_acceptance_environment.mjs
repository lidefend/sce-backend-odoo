import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const ENVIRONMENT_FILE = path.join(ROOT, 'config/frontend/acceptance_environments_v1.json');
const TOOL_FILE = path.join(ROOT, 'config/frontend/acceptance_tool_matrix_v1.json');

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function requiredText(value, label) {
  const text = String(value || '').trim();
  if (!text) throw new Error(`${label} is required`);
  return text;
}

function assertHttpUrl(value, label) {
  const parsed = new URL(requiredText(value, label));
  if (!['http:', 'https:'].includes(parsed.protocol)) throw new Error(`${label} must use http or https`);
  parsed.hash = '';
  return parsed.toString().replace(/\/$/, '');
}

function insideRoot(candidate) {
  const relative = path.relative(ROOT, candidate);
  return relative && !relative.startsWith('..') && !path.isAbsolute(relative);
}

export function resolveAcceptanceEnvironment({ tool, operation = 'read', env = process.env } = {}) {
  const environments = readJson(ENVIRONMENT_FILE);
  const matrix = readJson(TOOL_FILE);
  const profileName = String(env.SC_ACCEPTANCE_PROFILE || environments.default_profile || '').trim();
  const profile = environments.profiles?.[profileName];
  if (!profile) throw new Error(`unknown acceptance profile: ${profileName || '(empty)'}`);
  const toolPolicy = matrix.tools?.[tool];
  if (!toolPolicy) throw new Error(`unknown acceptance tool: ${tool || '(empty)'}`);
  if (!toolPolicy.profiles.includes(profileName)) throw new Error(`${tool} is forbidden for profile ${profileName}`);
  if (!toolPolicy.operations.includes(operation) || !profile.allowed_operations.includes(operation)) {
    throw new Error(`${tool}/${operation} is forbidden for profile ${profileName}`);
  }
  if (profile.service_mode === 'external' && operation === 'managed-service') {
    throw new Error(`external profile ${profileName} cannot manage services`);
  }
  const configuredUrl = profile.base_url_env ? env[profile.base_url_env] : profile.base_url;
  const configuredDatabase = profile.database_env ? env[profile.database_env] : profile.database;
  const overrideUrl = String(env.FRONTEND_URL || env.ACCEPTANCE_BASE_URL || '').trim();
  const overrideDatabase = String(env.DB_NAME || '').trim();
  const baseUrl = assertHttpUrl(overrideUrl || configuredUrl, `${profileName}.base_url`);
  const database = requiredText(overrideDatabase || configuredDatabase, `${profileName}.database`);
  if (profile.service_mode === 'external') {
    if (overrideUrl && profile.base_url && assertHttpUrl(profile.base_url, `${profileName}.base_url`) !== baseUrl) {
      throw new Error(`URL override conflicts with governed ${profileName} endpoint`);
    }
    if (overrideDatabase && profile.database && profile.database !== database) {
      throw new Error(`database override conflicts with governed ${profileName} alias`);
    }
  }
  if (profile.service_mode === 'managed' && !['127.0.0.1', 'localhost', '::1'].includes(new URL(baseUrl).hostname)) {
    throw new Error(`managed profile ${profileName} must use a loopback URL`);
  }
  const artifactRoot = path.resolve(ROOT, String(env.SC_ACCEPTANCE_ARTIFACT_ROOT || profile.artifact_root));
  if (!insideRoot(artifactRoot)) throw new Error(`acceptance artifact root escapes repository: ${artifactRoot}`);
  const loginEnv = profile.credential_env?.login;
  const passwordEnv = profile.credential_env?.password;
  let roleBindings = profile.role_bindings || {};
  if (profile.role_bindings_env) {
    const raw = String(env[profile.role_bindings_env] || '').trim();
    if (raw) {
      roleBindings = JSON.parse(raw);
      if (!roleBindings || typeof roleBindings !== 'object' || Array.isArray(roleBindings)) throw new Error(`${profile.role_bindings_env} must contain an object`);
    }
  }
  return Object.freeze({
    root: ROOT,
    profile: profileName,
    environment: profile.environment,
    serviceMode: profile.service_mode,
    operation,
    baseUrl,
    database,
    artifactRoot,
    runtimeIdentityPath: profile.runtime_identity_path || '',
    login: loginEnv ? String(env[loginEnv] || '') : '',
    password: passwordEnv ? String(env[passwordEnv] || '') : '',
    roleBindings: Object.freeze({ ...roleBindings }),
  });
}

export function assertNoHardcodedNumericRouteFallback(source, label = 'acceptance source') {
  if (/['"`]\/(?:a|m|r)\/\d+/.test(String(source))) {
    throw new Error(`${label} contains a hardcoded numeric route fallback`);
  }
}

export async function verifyServedIdentity(environment, expectedSha, fetchImpl = fetch) {
  if (!environment.runtimeIdentityPath) return { skipped: true };
  const response = await fetchImpl(`${environment.baseUrl}${environment.runtimeIdentityPath}`, { redirect: 'error' });
  if (!response.ok) throw new Error(`runtime identity probe failed: HTTP ${response.status}`);
  const payload = await response.json();
  const servedSha = requiredText(payload.git_sha || payload.sha || payload.source_revision, 'served runtime SHA');
  if (expectedSha && servedSha !== expectedSha) throw new Error(`served SHA ${servedSha} does not match ${expectedSha}`);
  return { skipped: false, servedSha };
}
