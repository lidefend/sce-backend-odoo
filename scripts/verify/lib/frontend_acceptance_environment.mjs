import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const ENVIRONMENT_FILE = path.join(ROOT, 'config/frontend/acceptance_environments_v1.json');
const TOOL_FILE = path.join(ROOT, 'config/frontend/acceptance_tool_matrix_v1.json');
const LOOPBACK = new Set(['127.0.0.1', 'localhost', '::1']);
const WEAK_SECRETS = new Set(['123456', 'demo', 'activity-tabs-acceptance-password']);
const OPERATION_ALIASES = Object.freeze({ read: 'readonly', fixture: 'isolated-write' });

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function text(value) {
  return String(value ?? '').trim();
}

function requiredText(value, label) {
  const result = text(value);
  if (!result) throw new Error(`${label} is required`);
  return result;
}

function normalizeOperation(value) {
  const operation = text(value || 'readonly');
  return OPERATION_ALIASES[operation] || operation;
}

function parseBoolean(value, fallback = false) {
  if (value === undefined || value === null || value === '') return fallback;
  if (['1', 'true', 'yes', 'on'].includes(text(value).toLowerCase())) return true;
  if (['0', 'false', 'no', 'off'].includes(text(value).toLowerCase())) return false;
  throw new Error(`invalid boolean value: ${value}`);
}

function parseArgs(argv = []) {
  const result = {};
  const mapping = {
    '--profile': 'profile', '--frontend-url': 'frontendUrl', '--api-url': 'apiUrl', '--db': 'database',
    '--login': 'login', '--role': 'role', '--target-mode': 'targetMode', '--operation': 'operation',
    '--expected-sha': 'expectedSha', '--artifact-root': 'artifactRoot', '--port': 'port',
  };
  for (let index = 0; index < argv.length; index += 1) {
    const key = argv[index];
    if (key === '--manage-service') { result.manageService = true; continue; }
    if (key === '--no-manage-service') { result.manageService = false; continue; }
    if (!mapping[key]) throw new Error(`unknown acceptance option: ${key}`);
    if (index + 1 >= argv.length) throw new Error(`${key} requires a value`);
    result[mapping[key]] = argv[index += 1];
  }
  return result;
}

function resolveAliases(env, names, label) {
  const entries = names.map((name) => [name, text(env[name])]).filter(([, value]) => value);
  const distinct = new Set(entries.map(([, value]) => value.replace(/\/$/, '')));
  if (distinct.size > 1) throw new Error(`${label} aliases conflict: ${entries.map(([name]) => name).join(', ')}`);
  return entries[0]?.[1] || '';
}

function assertHttpUrl(value, label) {
  let parsed;
  try { parsed = new URL(requiredText(value, label)); } catch { throw new Error(`${label} must be an absolute URL`); }
  if (!['http:', 'https:'].includes(parsed.protocol)) throw new Error(`${label} must use http or https`);
  if (parsed.username || parsed.password) throw new Error(`${label} must not contain credentials`);
  parsed.hash = '';
  return parsed.toString().replace(/\/$/, '');
}

function resolveAbsolutePath(value, label, { allowOutsideRepo = false } = {}) {
  const resolved = path.resolve(ROOT, requiredText(value, label));
  const relative = path.relative(ROOT, resolved);
  if (!allowOutsideRepo && (!relative || relative.startsWith('..') || path.isAbsolute(relative))) {
    throw new Error(`${label} escapes repository: ${resolved}`);
  }
  return resolved;
}

function parseRoleBindings(profile, env) {
  if (!profile.role_bindings_env) return Object.freeze({ ...(profile.role_bindings || {}) });
  const raw = text(env[profile.role_bindings_env]);
  if (!raw) return Object.freeze({});
  let parsed;
  try { parsed = JSON.parse(raw); } catch { throw new Error(`${profile.role_bindings_env} must contain JSON`); }
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error(`${profile.role_bindings_env} must contain an object`);
  return Object.freeze({ ...parsed });
}

function validateStorageState(env, { baseUrl, database, profileName, role, expectedSha }) {
  const storageStatePath = text(env.SC_ACCEPTANCE_STORAGE_STATE);
  if (!storageStatePath) return '';
  const absolute = path.resolve(ROOT, storageStatePath);
  const stat = fs.statSync(absolute);
  if ((stat.mode & 0o077) !== 0) throw new Error(`acceptance storage state must have mode 0600`);
  const metadataPath = `${absolute}.meta.json`;
  const metadata = readJson(metadataPath);
  const expected = { origin: baseUrl, database, profile: profileName, role };
  for (const [key, value] of Object.entries(expected)) {
    if (text(metadata[key]) !== text(value)) throw new Error(`acceptance storage state ${key} mismatch`);
  }
  if (expectedSha && text(metadata.source_sha) !== expectedSha) throw new Error(`acceptance storage state source SHA mismatch`);
  const expiresAt = Date.parse(text(metadata.expires_at));
  if (!Number.isFinite(expiresAt) || expiresAt <= Date.now()) throw new Error(`acceptance storage state is expired`);
  return absolute;
}

function deepFreeze(value) {
  if (!value || typeof value !== 'object' || Object.isFrozen(value)) return value;
  Object.freeze(value);
  for (const child of Object.values(value)) deepFreeze(child);
  return value;
}

export function resolveRepoRoot() { return ROOT; }

export function resolveAcceptanceEnvironment({ tool, operation, env = process.env, argv = [] } = {}) {
  const cli = parseArgs(argv);
  const environments = readJson(ENVIRONMENT_FILE);
  const matrix = readJson(TOOL_FILE);
  const profileName = text(cli.profile || env.SC_ACCEPTANCE_PROFILE || environments.default_profile);
  const profile = environments.profiles?.[profileName];
  if (!profile) throw new Error(`unknown acceptance profile: ${profileName || '(empty)'}`);
  const toolPolicy = matrix.tools?.[tool];
  if (!toolPolicy) throw new Error(`unknown acceptance tool: ${tool || '(empty)'}`);
  if (!toolPolicy.profiles.includes(profileName)) throw new Error(`${tool} is forbidden for profile ${profileName}`);

  const requestedOperation = normalizeOperation(cli.operation || operation || env.SC_ACCEPTANCE_OPERATION || (tool === 'form-system-audit' ? 'isolated-write' : profileName === 'production' ? 'production-safe-smoke' : 'readonly'));
  if (!toolPolicy.operations.includes(requestedOperation) || !profile.allowed_operations.includes(requestedOperation)) {
    throw new Error(`${tool}/${requestedOperation} is forbidden for profile ${profileName}`);
  }
  const targetMode = text(cli.targetMode || env.SC_ACCEPTANCE_TARGET_MODE || profile.target_mode);
  if (!['managed', 'external'].includes(targetMode)) throw new Error(`invalid target mode: ${targetMode}`);
  const manageService = parseBoolean(cli.manageService ?? env.SC_ACCEPTANCE_MANAGE_SERVICE, targetMode === 'managed');
  if (targetMode === 'external' && manageService) throw new Error(`external profile ${profileName} cannot manage services`);

  const legacyUrl = resolveAliases(env, ['SC_ACCEPTANCE_FRONTEND_URL', 'FRONTEND_URL', 'ACCEPTANCE_BASE_URL', 'BASE_URL'], 'frontend URL');
  const configuredUrl = cli.frontendUrl || legacyUrl || profile.base_url || '';
  if (profile.base_url_required && !cli.frontendUrl && !legacyUrl) throw new Error(`${profileName}.frontend URL must be supplied explicitly`);
  const baseUrl = assertHttpUrl(configuredUrl, `${profileName}.frontend_url`);
  const apiUrl = assertHttpUrl(cli.apiUrl || env.SC_ACCEPTANCE_API_URL || baseUrl, `${profileName}.api_url`);
  if (targetMode === 'managed' && (!LOOPBACK.has(new URL(baseUrl).hostname) || !LOOPBACK.has(new URL(apiUrl).hostname))) {
    throw new Error(`managed profile ${profileName} must use loopback URLs`);
  }

  const legacyDb = resolveAliases(env, ['SC_ACCEPTANCE_DATABASE', 'DB_NAME', 'E2E_DB', 'DB'], 'database');
  const configuredDb = cli.database || legacyDb || profile.database || '';
  if (profile.database_required && !cli.database && !legacyDb) throw new Error(`${profileName}.database must be supplied explicitly`);
  const database = requiredText(configuredDb, `${profileName}.database`);
  if (profile.database && legacyDb && profile.database !== database && profileName !== 'local' && profileName !== 'test') {
    throw new Error(`database override conflicts with governed ${profileName} database`);
  }

  const writeOperation = ['simulated-write', 'isolated-write'].includes(requestedOperation);
  if (writeOperation && profile.fixture_required_for_write && database !== 'sc_frontend_acceptance') {
    throw new Error(`${requestedOperation} requires the isolated frontend acceptance database`);
  }
  if (['daily', 'production'].includes(profileName) && writeOperation) throw new Error(`${profileName} forbids write-capable acceptance`);

  const expectedSha = text(cli.expectedSha || env.SC_ACCEPTANCE_EXPECTED_SHA || env.GIT_SHA);
  if (profile.expected_sha_required && !/^[0-9a-f]{40}$/.test(expectedSha)) throw new Error(`${profileName}.expected SHA must be a full 40-character commit`);
  if (expectedSha && !/^[0-9a-f]{40}$/.test(expectedSha)) throw new Error(`expected SHA must be a full 40-character commit`);

  const credential = profile.credential_env || {};
  const login = text(cli.login || env.SC_ACCEPTANCE_LOGIN || (credential.login ? env[credential.login] : ''));
  const password = text(credential.password ? env[credential.password] : '');
  if (['daily', 'production'].includes(profileName) && password && WEAK_SECRETS.has(password)) throw new Error(`${profileName} refuses a known default credential`);
  const roleBindings = parseRoleBindings(profile, env);
  const role = text(cli.role || env.SC_ACCEPTANCE_ROLE);
  const storageStatePath = validateStorageState(env, { baseUrl, database, profileName, role, expectedSha });

  const artifactBase = resolveAbsolutePath(cli.artifactRoot || env.SC_ACCEPTANCE_ARTIFACT_ROOT || '.runtime/acceptance', 'artifact root');
  const runId = text(env.SC_ACCEPTANCE_RUN_ID) || `${new Date().toISOString().replace(/[^0-9TZ]/g, '')}-${process.pid}-${crypto.randomBytes(4).toString('hex')}`;
  if (!/^[A-Za-z0-9._-]+$/.test(runId)) throw new Error(`invalid acceptance run id`);
  const shaSegment = expectedSha || 'unbound';
  const runArtifactRoot = path.join(artifactBase, profileName, shaSegment, tool, runId);
  const leaseRoot = path.join(text(env.XDG_RUNTIME_DIR) || os.tmpdir(), 'sce-frontend-acceptance', 'leases');

  return deepFreeze({
    schema: 'frontend_acceptance_environment.v1', root: ROOT, tool, profile: profileName,
    environment: profile.environment, operation: requestedOperation,
    runner: { kind: text(env.CI) ? 'ci' : 'host', repoRoot: ROOT },
    target: { mode: targetMode, manageService, baseUrl, apiUrl, identityPath: profile.runtime_identity_path || '', identityRequired: Boolean(profile.target_identity_required || toolPolicy.target_identity_required) },
    data: { database, fixture: database === 'sc_frontend_acceptance' },
    auth: { login, password, role, secretEnvKey: credential.password || '', roleBindings, storageStatePath },
    safety: { operation: requestedOperation, writeCapable: writeOperation, redactionRequired: Boolean(profile.redaction_required) },
    provenance: { expectedSha, configFiles: [ENVIRONMENT_FILE, TOOL_FILE], precedence: 'CLI>SC_ACCEPTANCE_*>legacy-env>profile>safe-default' },
    artifacts: { root: artifactBase, runId, runRoot: runArtifactRoot },
    concurrency: { leaseRoot, targetKey: crypto.createHash('sha256').update(`${baseUrl}|${apiUrl}|${database}`).digest('hex') },
    profilePolicy: profile,
    // Compatibility projections for the first migration batch.
    baseUrl, apiUrl, database, artifactRoot: artifactBase, runArtifactRoot,
    runtimeIdentityPath: profile.runtime_identity_path || '', login, password, roleBindings,
  });
}

export function redactedEnvironmentEvidence(environment) {
  return {
    schema: environment.schema, tool: environment.tool, profile: environment.profile,
    operation: environment.operation, runner: environment.runner, target: environment.target,
    data: environment.data, auth: { login: environment.auth.login, role: environment.auth.role, secretEnvKey: environment.auth.secretEnvKey, passwordSupplied: Boolean(environment.auth.password) },
    safety: environment.safety, provenance: environment.provenance, artifacts: environment.artifacts,
    concurrency: environment.concurrency,
  };
}

export function assertNoHardcodedNumericRouteFallback(source, label = 'acceptance source') {
  if (/['"`]\/(?:a|m|r)\/\d+/.test(String(source))) throw new Error(`${label} contains a hardcoded numeric route fallback`);
}

export async function verifyServedIdentity(environment, expectedSha = environment.provenance.expectedSha, fetchImpl = fetch) {
  if (!environment.target.identityPath) {
    if (environment.target.identityRequired) throw new Error(`target identity endpoint is required`);
    return { skipped: true };
  }
  const response = await fetchImpl(`${environment.target.apiUrl}${environment.target.identityPath}`, { redirect: 'error' });
  if (!response.ok) throw new Error(`runtime identity probe failed: HTTP ${response.status}`);
  const raw = await response.json();
  const payload = raw?.data || raw?.result || raw;
  const servedSha = requiredText(payload.git_sha || payload.sha || payload.source_revision || payload.source_sha, 'served runtime SHA');
  const servedDatabase = text(payload.database || payload.db_name || payload.db);
  const servedProfile = text(payload.profile || payload.environment || payload.env);
  if (expectedSha && servedSha !== expectedSha) throw new Error(`served SHA ${servedSha} does not match ${expectedSha}`);
  if (servedDatabase && servedDatabase !== environment.database) throw new Error(`served database ${servedDatabase} does not match ${environment.database}`);
  if (servedProfile && ![environment.profile, environment.environment].includes(servedProfile)) throw new Error(`served profile ${servedProfile} does not match ${environment.profile}`);
  return { skipped: false, servedSha, servedDatabase, servedProfile, frontendBuildSha256: text(payload.frontend_build_sha256) };
}
