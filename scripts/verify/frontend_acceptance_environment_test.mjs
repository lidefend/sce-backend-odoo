#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {
  assertNoHardcodedNumericRouteFallback,
  redactedEnvironmentEvidence,
  resolveAcceptanceEnvironment,
  verifyServedIdentity,
} from './lib/frontend_acceptance_environment.mjs';
import { acquireAcceptanceLease, reserveDynamicPort, startOwnedProcess } from './lib/frontend_acceptance_lease.mjs';

const SHA = 'a'.repeat(40);
const localEnv = { SC_ACCEPTANCE_PROFILE: 'local', SC_ACCEPTANCE_FIXTURE_PASSWORD: 'local-secret' };
const local = resolveAcceptanceEnvironment({ tool: 'geometry-scroll-audit', env: localEnv });
assert.equal(local.database, 'sc_frontend_acceptance');
assert.equal(local.operation, 'readonly');
assert(Object.isFrozen(local.target));
assert(!JSON.stringify(redactedEnvironmentEvidence(local)).includes('local-secret'));

let launchCalls = 0;
let networkCalls = 0;
const beforeLaunch = (fn, pattern) => {
  const launchBefore = launchCalls;
  const networkBefore = networkCalls;
  assert.throws(fn, pattern);
  assert.equal(launchCalls, launchBefore);
  assert.equal(networkCalls, networkBefore);
};
beforeLaunch(() => resolveAcceptanceEnvironment({ tool: 'missing', env: localEnv }), /unknown acceptance tool/);
beforeLaunch(() => resolveAcceptanceEnvironment({ tool: 'geometry-scroll-audit', env: { ...localEnv, DB_NAME: 'one', E2E_DB: 'two' } }), /aliases conflict/);
beforeLaunch(() => resolveAcceptanceEnvironment({ tool: 'geometry-scroll-audit', env: { ...localEnv, SC_ACCEPTANCE_FRONTEND_URL: 'https:\/\/example.com' } }), /managed profile.*loopback/);
beforeLaunch(() => resolveAcceptanceEnvironment({ tool: 'geometry-scroll-audit', env: { ...localEnv, SC_ACCEPTANCE_ARTIFACT_ROOT: '../../escape' } }), /escapes repository/);
beforeLaunch(() => resolveAcceptanceEnvironment({ tool: 'geometry-scroll-audit', operation: 'isolated-write', env: { SC_ACCEPTANCE_PROFILE: 'daily', SC_ACCEPTANCE_FRONTEND_URL: 'https:\/\/daily.example.test', SC_ACCEPTANCE_EXPECTED_SHA: SHA } }), /forbidden/);
beforeLaunch(() => resolveAcceptanceEnvironment({ tool: 'daily-release-probe', env: { SC_ACCEPTANCE_PROFILE: 'daily', SC_ACCEPTANCE_EXPECTED_SHA: SHA } }), /must be supplied explicitly/);
beforeLaunch(() => resolveAcceptanceEnvironment({ tool: 'daily-release-probe', env: { SC_ACCEPTANCE_PROFILE: 'daily', SC_ACCEPTANCE_FRONTEND_URL: 'https:\/\/daily.example.test', SC_ACCEPTANCE_EXPECTED_SHA: SHA, ACCEPTANCE_PASSWORD: '123456' } }), /default credential/);
beforeLaunch(() => resolveAcceptanceEnvironment({ tool: 'production-safe-smoke', env: { SC_ACCEPTANCE_PROFILE: 'production', SC_ACCEPTANCE_FRONTEND_URL: 'https:\/\/prod.example.test', SC_ACCEPTANCE_DATABASE: 'tenant_prod' } }), /expected SHA/);
beforeLaunch(() => resolveAcceptanceEnvironment({ tool: 'geometry-scroll-audit', env: { SC_ACCEPTANCE_PROFILE: 'production', SC_ACCEPTANCE_FRONTEND_URL: 'https:\/\/prod.example.test', SC_ACCEPTANCE_DATABASE: 'tenant_prod', SC_ACCEPTANCE_EXPECTED_SHA: SHA } }), /forbidden for profile production/);
beforeLaunch(() => assertNoHardcodedNumericRouteFallback("page.goto('/a/786')"), /hardcoded numeric route/);

const dailyEnv = { SC_ACCEPTANCE_PROFILE: 'daily', SC_ACCEPTANCE_FRONTEND_URL: 'https://daily.example.test',
  SC_ACCEPTANCE_EXPECTED_SHA: SHA, ACCEPTANCE_LOGIN: 'synthetic-reader', ACCEPTANCE_PASSWORD: 'demo',
  SC_ACCEPTANCE_RUN_ID: 'explicit-readonly-run' };
const dailyConfirmation = { schema: 'daily-readonly-credential-confirmation.v1', profile: 'daily', operation: 'readonly',
  tool: 'daily-release-probe', baseUrl: dailyEnv.SC_ACCEPTANCE_FRONTEND_URL, apiUrl: dailyEnv.SC_ACCEPTANCE_FRONTEND_URL,
  database: 'sc_demo', login: dailyEnv.ACCEPTANCE_LOGIN, expectedSha: SHA, runId: dailyEnv.SC_ACCEPTANCE_RUN_ID,
  expiresAt: new Date(Date.now() + 60_000).toISOString() };
const confirmEnv = (confirmation = dailyConfirmation, changes = {}) => ({ ...dailyEnv,
  SC_ACCEPTANCE_DAILY_CREDENTIAL_CONFIRMATION: JSON.stringify(confirmation), ...changes });
const confirmed = resolveAcceptanceEnvironment({ tool: 'daily-release-probe', env: confirmEnv() });
assert.equal(confirmed.safety.dailyCredentialConfirmed, true);
assert(!JSON.stringify(redactedEnvironmentEvidence(confirmed)).includes('"password":'));
for (const [key, value] of Object.entries({ tool: 'other-tool', baseUrl: 'https://wrong.example.test', apiUrl: 'https://wrong.example.test',
  database: 'other', login: 'other-reader', expectedSha: 'b'.repeat(40), runId: 'different-run', operation: 'isolated-write' })) {
  beforeLaunch(() => resolveAcceptanceEnvironment({ tool: 'daily-release-probe', env: confirmEnv({ ...dailyConfirmation, [key]: value }) }), /identity mismatch/);
}
for (const expiresAt of [new Date(0).toISOString(), new Date(Date.now() + 30 * 60_000).toISOString(), 'invalid']) {
  beforeLaunch(() => resolveAcceptanceEnvironment({ tool: 'daily-release-probe', env: confirmEnv({ ...dailyConfirmation, expiresAt }) }), /expire/);
}
beforeLaunch(() => resolveAcceptanceEnvironment({ tool: 'daily-release-probe', env: confirmEnv(dailyConfirmation, { SC_ACCEPTANCE_RUN_ID: '' }) }), /identity mismatch/);
beforeLaunch(() => resolveAcceptanceEnvironment({ tool: 'production-safe-smoke', env: confirmEnv(dailyConfirmation, { SC_ACCEPTANCE_PROFILE: 'production', SC_ACCEPTANCE_DATABASE: 'tenant_prod' }) }), /identity mismatch/);
beforeLaunch(() => resolveAcceptanceEnvironment({ tool: 'daily-release-probe', env: confirmEnv({ ...dailyConfirmation, password: 'forbidden-extra-field' }) }), /identity mismatch/);
console.log('[daily_credential_confirmation] PASS cases=15 scope=readonly_exact_run_identity');

const production = resolveAcceptanceEnvironment({ tool: 'production-safe-smoke', env: {
  SC_ACCEPTANCE_PROFILE: 'production', SC_ACCEPTANCE_FRONTEND_URL: 'https://prod.example.test',
  SC_ACCEPTANCE_DATABASE: 'tenant_prod', SC_ACCEPTANCE_EXPECTED_SHA: SHA,
} });
assert.equal(production.operation, 'production-safe-smoke');
assert.equal(production.target.manageService, false);

const identity = await verifyServedIdentity(production, SHA, async () => {
  networkCalls += 1;
  return { ok: true, json: async () => ({ git_sha: SHA, database: 'tenant_prod', environment: 'prod', frontend_build_sha256: 'f'.repeat(64) }) };
});
assert.equal(identity.servedSha, SHA);
await assert.rejects(() => verifyServedIdentity(production, SHA, async () => ({ ok: true, json: async () => ({ git_sha: 'b'.repeat(40) }) })), /does not match/);

const formalSources = [
  'scripts/verify/frontend_full_product_audit.mjs',
  'scripts/verify/frontend_form_system_audit.mjs',
  'scripts/verify/frontend_geometry_scroll_audit.mjs',
];
for (const relative of formalSources) {
  const source = await fs.readFile(new URL(`../../${relative}`, import.meta.url), 'utf8');
  assertNoHardcodedNumericRouteFallback(source, relative);
  assert.doesNotMatch(source, /http:\/\/1\.95\.85\.92|\bsc_demo\b/, `${relative} must not embed a daily target`);
  assert.doesNotMatch(source, /launchChromium\(/, `${relative} must use the governed browser launcher`);
  assert.doesNotMatch(source, /process\.cwd\(\)/, `${relative} must not depend on cwd`);
}

const temp = await fs.mkdtemp(path.join(os.tmpdir(), 'sc-acceptance-environment-'));
try {
  const storageState = path.join(temp, 'auth.json');
  await fs.writeFile(storageState, '{}\n', { mode: 0o600 });
  await fs.writeFile(`${storageState}.meta.json`, `${JSON.stringify({
    origin: local.baseUrl, database: local.database, profile: 'local', role: 'project_manager',
    source_sha: '', expires_at: new Date(Date.now() + 60_000).toISOString(),
  })}\n`, { mode: 0o600 });
  const withStorage = resolveAcceptanceEnvironment({ tool: 'geometry-scroll-audit', env: {
    ...localEnv, SC_ACCEPTANCE_ROLE: 'project_manager', SC_ACCEPTANCE_STORAGE_STATE: storageState,
  } });
  assert.equal(withStorage.auth.storageStatePath, storageState);
  await fs.chmod(storageState, 0o644);
  beforeLaunch(() => resolveAcceptanceEnvironment({ tool: 'geometry-scroll-audit', env: {
    ...localEnv, SC_ACCEPTANCE_ROLE: 'project_manager', SC_ACCEPTANCE_STORAGE_STATE: storageState,
  } }), /mode 0600/);
  await fs.chmod(storageState, 0o600);
  await fs.writeFile(`${storageState}.meta.json`, `${JSON.stringify({
    origin: local.baseUrl, database: 'wrong', profile: 'local', role: 'project_manager',
    expires_at: new Date(Date.now() + 60_000).toISOString(),
  })}\n`, { mode: 0o600 });
  beforeLaunch(() => resolveAcceptanceEnvironment({ tool: 'geometry-scroll-audit', env: {
    ...localEnv, SC_ACCEPTANCE_ROLE: 'project_manager', SC_ACCEPTANCE_STORAGE_STATE: storageState,
  } }), /database mismatch/);

  const makeEnvironment = (runId) => ({
    ...local,
    artifacts: { root: temp, runId, runRoot: path.join(temp, 'runs', runId) },
    concurrency: { leaseRoot: path.join(temp, 'leases'), targetKey: 'same-target' },
  });
  const sharedOne = await acquireAcceptanceLease({ environment: makeEnvironment('read-one'), mode: 'shared-read' });
  const sharedTwo = await acquireAcceptanceLease({ environment: makeEnvironment('read-two'), mode: 'shared-read' });
  assert.notEqual(sharedOne.artifactDir, sharedTwo.artifactDir);
  await assert.rejects(() => acquireAcceptanceLease({ environment: makeEnvironment('write-blocked'), mode: 'exclusive-write' }), /lease conflict/);
  await sharedOne.release();
  await sharedOne.release();
  await sharedTwo.release();
  const exclusive = await acquireAcceptanceLease({ environment: makeEnvironment('write-one'), mode: 'exclusive-write' });
  await assert.rejects(() => acquireAcceptanceLease({ environment: makeEnvironment('read-blocked'), mode: 'shared-read' }), /lease conflict/);
  await exclusive.release();

  const portOne = await reserveDynamicPort();
  const portTwo = await reserveDynamicPort();
  assert.notEqual(portOne.port, portTwo.port);
  await portOne.release();
  await portTwo.release();

  const serviceLease = await acquireAcceptanceLease({ environment: makeEnvironment('service-one'), mode: 'exclusive-service' });
  const service = await startOwnedProcess({
    command: process.execPath, args: ['-e', 'setInterval(() => {}, 1000)'], cwd: temp,
    logFile: path.join(serviceLease.artifactDir, 'service.log'), ready: async () => true, lease: serviceLease,
  });
  assert(service.pid > 0);
  await service.stop();
  await serviceLease.release();
} finally {
  await fs.rm(temp, { recursive: true, force: true });
}

console.log('[frontend_acceptance_environment_test] PASS');
