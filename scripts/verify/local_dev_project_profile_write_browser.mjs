#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { assertRuntimeWriterIdentity } from './local_dev_project_profile_write_identity.mjs';

const EXPECTED_DB = 'sc_dev_demo';
const EXPECTED_ENVIRONMENT = 'dev';
const EXPECTED_DBFILTER = '^sc_dev_demo$';
const EXPECTED_FRONTEND_URL = 'http://127.0.0.1:5176';
const FIXTURE_NAMESPACE = 'codex_p4_project_profile_write';
const BATCH_PATTERN = /^[a-z0-9][a-z0-9-]{2,31}$/;
const SCRIPT_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const FRONTEND_URL = process.env.FRONTEND_URL || EXPECTED_FRONTEND_URL;
const DB_NAME = process.env.DB_NAME || EXPECTED_DB;
const READ_ONLY = process.env.READ_ONLY === '1';
const PREFLIGHT_ONLY = process.env.PREFLIGHT_ONLY === '1';
const NETWORK_FAILURE_RECOVERY = process.env.NETWORK_FAILURE_RECOVERY === '1';
const PERMISSION_ONLY = process.env.PERMISSION_ONLY === '1';
const RELATION_ONLY = process.env.RELATION_ONLY === '1';
const RELATION_WRITE_ONLY = process.env.RELATION_WRITE_ONLY === '1';
const M2M_ONLY = process.env.M2M_ONLY === '1';
const VALIDATE_ONLY = process.env.P4_RUNNER_VALIDATE_ONLY === '1';
const PM_LOGIN = process.env.PM_LOGIN || 'demo_role_project_manager';

function deny(message) { throw new Error(`[DENY] ${message}`); }
function requiredPositiveInteger(name) {
  const raw = String(process.env[name] ?? '').trim();
  if (!/^[1-9][0-9]*$/.test(raw)) deny(`${name} must be an explicit positive integer`);
  const value = Number(raw);
  if (!Number.isSafeInteger(value)) deny(`${name} exceeds the safe integer range`);
  return value;
}
function requiredJson(name) {
  const raw = String(process.env[name] ?? '').trim();
  if (!raw) deny(`${name} is required for write mode`);
  try { return JSON.parse(raw); }
  catch { deny(`${name} is not valid JSON`); }
}
function positiveIds(values, label) {
  if (!Array.isArray(values) || !values.length) deny(`${label} must contain owned positive IDs`);
  const ids = values.map((value) => Number(value));
  if (ids.some((value) => !Number.isSafeInteger(value) || value <= 0) || new Set(ids).size !== ids.length) {
    deny(`${label} contains invalid or duplicate IDs`);
  }
  return ids.sort((left, right) => left - right);
}
function expectedProjectXmlid(batch) {
  return `${FIXTURE_NAMESPACE}.project_${batch.replaceAll('-', '_')}`;
}
function expectedResponsibilityXmlids(batch) {
  const suffix = batch.replaceAll('-', '_');
  return [
    `${FIXTURE_NAMESPACE}.responsibility_${suffix}_manager`,
    `${FIXTURE_NAMESPACE}.responsibility_${suffix}_cost`,
  ].sort();
}
function validateProductCandidate() {
  const expected = String(process.env.PRODUCT_CANDIDATE_SHA ?? '').trim();
  if (!/^[0-9a-f]{40}$/.test(expected)) deny('PRODUCT_CANDIDATE_SHA must be a full immutable SHA');
  let served;
  if (VALIDATE_ONLY) {
    served = String(process.env.P4_RUNNER_SERVED_PRODUCT_SHA ?? '').trim();
  } else {
    try {
      const pid = JSON.parse(fs.readFileSync('/tmp/sc-local-dev-candidate-frontend.pid', 'utf8'));
      served = String(pid?.head ?? '').trim();
    } catch {
      deny('candidate pidfile is missing or invalid');
    }
  }
  if (served !== expected) deny('product candidate SHA mismatch');
}
function readGovernedAuthority(batch, toolSha) {
  if (VALIDATE_ONLY) return requiredJson('P4_PROJECT_PROFILE_AUTHORITY_JSON');
  const rootDir = String(process.env.ROOT_DIR ?? '').trim();
  const envFile = String(process.env.ENV_FILE ?? '').trim();
  if (!path.isAbsolute(rootDir) || !path.isAbsolute(envFile)) deny('ROOT_DIR and ENV_FILE must be absolute for governed authority read');
  if (path.resolve(rootDir) !== SCRIPT_ROOT) deny('ROOT_DIR does not match the runner worktree');
  const fixtureEntry = path.join(rootDir, 'scripts/verify/local_dev_project_profile_write_fixture.sh');
  const result = spawnSync('bash', [fixtureEntry], {
    cwd: rootDir,
    encoding: 'utf8',
    maxBuffer: 4 * 1024 * 1024,
    env: {
      ...process.env,
      P4_PROJECT_PROFILE_MODE: 'inspect',
      P4_PROJECT_PROFILE_BATCH: batch,
      P4_PROJECT_PROFILE_CONFIRM: 'INSPECT',
      CANDIDATE_GIT_HEAD: toolSha,
    },
  });
  if (result.error || result.status !== 0) deny(`governed authority read failed before browser startup (exit=${result.status ?? 'spawn-error'})`);
  const prefix = 'LOCAL_DEV_PROJECT_PROFILE_WRITE_FIXTURE_JSON=';
  const rows = String(result.stdout || '').split(/\r?\n/).filter((line) => line.startsWith(prefix));
  if (rows.length !== 1) deny('governed authority read did not return exactly one result');
  try { return JSON.parse(rows[0].slice(prefix.length)); }
  catch { deny('governed authority result is not valid JSON'); }
}
function loadWriteAuthority(projectId) {
  const batch = String(process.env.P4_PROJECT_PROFILE_BATCH ?? '').trim();
  if (!BATCH_PATTERN.test(batch)) deny('P4_PROJECT_PROFILE_BATCH must be explicit and match the governed batch format');
  const toolSha = String(process.env.P4_TOOL_CANDIDATE_SHA ?? '').trim();
  if (!/^[0-9a-f]{40}$/.test(toolSha)) deny('P4_TOOL_CANDIDATE_SHA must be a full immutable SHA');
  if (!VALIDATE_ONLY) {
    const actualHead = spawnSync('git', ['-C', SCRIPT_ROOT, 'rev-parse', 'HEAD'], { encoding: 'utf8' });
    if (actualHead.status !== 0 || String(actualHead.stdout || '').trim() !== toolSha) deny('P4 tool candidate SHA does not match the runner worktree');
  }
  if (DB_NAME !== EXPECTED_DB) deny(`write mode requires DB_NAME=${EXPECTED_DB}`);
  if (String(process.env.SC_ENVIRONMENT ?? '') !== EXPECTED_ENVIRONMENT) deny(`write mode requires SC_ENVIRONMENT=${EXPECTED_ENVIRONMENT}`);
  if (String(process.env.ODOO_DBFILTER ?? '') !== EXPECTED_DBFILTER) deny(`write mode requires ODOO_DBFILTER=${EXPECTED_DBFILTER}`);

  const authority = readGovernedAuthority(batch, toolSha);
  if (authority.mode !== 'inspect' || authority.existing_batch !== true) deny('authority must be a successful inspect of an existing batch');
  if (authority.database !== DB_NAME || authority.environment !== EXPECTED_ENVIRONMENT || authority.dbfilter !== EXPECTED_DBFILTER) {
    deny('authority environment/database identity mismatch');
  }
  if (authority.candidate_sha !== toolSha) deny('authority tool candidate SHA mismatch');
  if (authority.batch !== batch || authority.namespace !== FIXTURE_NAMESPACE) deny('authority batch or namespace mismatch');
  const project = authority.project || {};
  if (Number(project.id) !== projectId) deny('authority target project ID mismatch');
  if (project.xmlid !== expectedProjectXmlid(batch)) deny('authority project XMLID mismatch');
  if (project.ownership_marker !== `CODEX-P4-${batch.toUpperCase()}`) deny('authority project ownership marker mismatch');
  const projectCompanyId = Number(project.company_id);
  if (!Number.isSafeInteger(projectCompanyId) || projectCompanyId <= 0) deny('authority project company identity is missing or invalid');

  const managerCandidates = Array.isArray(authority.role_candidates?.project_manager)
    ? authority.role_candidates.project_manager
    : [];
  const writer = managerCandidates.find((row) => String(row?.login || '') === PM_LOGIN);
  if (!writer) deny('configured PM_LOGIN is not an authority project_manager candidate');
  if (Number(writer.company_id) !== projectCompanyId) deny('configured project manager company does not own the target project');
  const managerAccess = Array.isArray(authority.effective_project_access?.project_manager)
    ? authority.effective_project_access.project_manager
    : [];
  const writerAccess = managerAccess.find((row) => String(row?.login || '') === PM_LOGIN);
  if (!writerAccess || !['acl_read', 'acl_write', 'record_read', 'record_write'].every((key) => writerAccess[key] === true)) {
    deny('configured project manager lacks governed read/write authority for the target project');
  }

  const projectResponsibilityIds = positiveIds(project.responsibility_ids, 'authority project responsibility_ids');
  const responsibilities = Array.isArray(authority.responsibilities) ? authority.responsibilities : [];
  if (responsibilities.length !== 2) deny('authority must resolve exactly two batch-owned responsibility rows');
  const responsibilityIds = positiveIds(responsibilities.map((row) => row?.id), 'authority responsibility rows');
  if (JSON.stringify(projectResponsibilityIds) !== JSON.stringify(responsibilityIds)) deny('authority responsibility scope mismatch');
  if (responsibilities.some((row) => Number(row?.project_id) !== projectId)) deny('authority responsibility belongs to another project');
  const xmlids = responsibilities.map((row) => String(row?.xmlid || '')).sort();
  if (JSON.stringify(xmlids) !== JSON.stringify(expectedResponsibilityXmlids(batch))) deny('authority responsibility XMLID mismatch');
  const tags = Array.isArray(authority.tags) ? authority.tags : [];
  if (M2M_ONLY) {
    const marker = `CODEX-P4-${batch.toUpperCase()}-TAG-`;
    if (tags.length !== 3) deny('authority must resolve the three batch-owned many2many tag candidates');
    const tagNames = tags.map((row) => String(row?.name || '')).sort();
    if (new Set(tagNames).size !== 3 || tagNames.some((name) => !name.startsWith(marker))) {
      deny('authority many2many tag candidates lost their batch marker');
    }
    if (tags.some((row) => !Number.isSafeInteger(Number(row?.id)) || Number(row?.id) <= 0)) {
      deny('authority many2many tag candidate identity is invalid');
    }
    // The candidates are carried by a batch-owned project while the acceptance
    // target keeps an empty relation. The governed company scope no longer
    // derives a boundary from ``project_ids.company_id`` for the shared project
    // dictionaries, so the carrier is now only the stable batch-owned identity
    // the tool asserts, and it must stay a different record from the target.
    const carrier = authority.candidate_carrier || null;
    if (!carrier) deny('authority must resolve the batch-owned many2many tag carrier');
    const expectedCarrierXmlid = `${FIXTURE_NAMESPACE}.project_${batch.replaceAll('-', '_')}_tag_carrier`;
    if (String(carrier.xmlid || '') !== expectedCarrierXmlid) deny('authority many2many tag carrier XMLID mismatch');
    if (String(carrier.ownership_marker || '') !== `CODEX-P4-${batch.toUpperCase()}-TAG-CARRIER`) {
      deny('authority many2many tag carrier marker mismatch');
    }
    const carrierId = Number(carrier.id);
    if (!Number.isSafeInteger(carrierId) || carrierId <= 0) deny('authority many2many tag carrier identity is invalid');
    if (carrierId === projectId) deny('authority many2many tag carrier must not be the acceptance target');
    const carrierTagIds = positiveIds(carrier.tag_ids, 'authority many2many tag carrier tag_ids');
    const tagIds = positiveIds(tags.map((row) => row?.id), 'authority many2many tag rows');
    if (JSON.stringify(carrierTagIds) !== JSON.stringify(tagIds)) {
      deny('authority many2many tag carrier does not hold the batch candidates');
    }
  }
  return {
    ...authority,
    batch,
    tags,
    carrier: authority.candidate_carrier || null,
    project: { ...project, company_id: projectCompanyId, responsibility_ids: responsibilityIds },
    writer: {
      id: Number(writer.id),
      login: String(writer.login),
      company_id: Number(writer.company_id),
      role_code: String(writer.role_code || ''),
    },
  };
}
function assertOwnedProjectFacts(authority, facts) {
  const project = facts?.project || {};
  if (Number(project.id) !== Number(authority.project.id)) deny('authoritative project read returned the wrong target');
  if (String(project.project_code || '') !== String(authority.project.ownership_marker || '')) deny('authoritative project marker mismatch');
  const factIds = positiveIds(project.responsibility_ids, 'authoritative project responsibility_ids');
  if (JSON.stringify(factIds) !== JSON.stringify(authority.project.responsibility_ids)) deny('authoritative project has out-of-scope responsibility rows');
  const rows = Array.isArray(facts?.responsibilities) ? facts.responsibilities : [];
  const rowIds = positiveIds(rows.map((row) => row?.id), 'authoritative responsibility rows');
  if (JSON.stringify(rowIds) !== JSON.stringify(authority.project.responsibility_ids)) deny('authoritative responsibility read is incomplete or out of scope');
  if (rows.some((row) => Number(row?.project_id) !== Number(authority.project.id))) deny('authoritative responsibility row belongs to another project');
}

const PROJECT_ID = requiredPositiveInteger('PROJECT_ID');
if (FRONTEND_URL !== EXPECTED_FRONTEND_URL) deny(`FRONTEND_URL must be exactly ${EXPECTED_FRONTEND_URL}`);
validateProductCandidate();
if ((READ_ONLY || PREFLIGHT_ONLY) && NETWORK_FAILURE_RECOVERY) deny('read-only preflight cannot enable failure injection or retry');
const WRITE_MODE = !READ_ONLY && !PREFLIGHT_ONLY;
if (PERMISSION_ONLY && (!WRITE_MODE || NETWORK_FAILURE_RECOVERY)) deny('permission checks require dedicated write authority and no recovery injection');
if (RELATION_ONLY && (!WRITE_MODE || NETWORK_FAILURE_RECOVERY || PERMISSION_ONLY)) deny('relation checks require dedicated authority and an exclusive mode');
if (RELATION_WRITE_ONLY && (!WRITE_MODE || RELATION_ONLY || NETWORK_FAILURE_RECOVERY || PERMISSION_ONLY)) deny('relation write checks require dedicated authority and an exclusive mode');
if (M2M_ONLY && (!WRITE_MODE || RELATION_ONLY || RELATION_WRITE_ONLY || PERMISSION_ONLY || NETWORK_FAILURE_RECOVERY)) {
  deny('many2many checks require dedicated authority and an exclusive mode');
}
const WRITE_AUTHORITY = WRITE_MODE ? loadWriteAuthority(PROJECT_ID) : null;
if (RELATION_WRITE_ONLY && !WRITE_AUTHORITY?.write_scope?.includes('partner_id')) deny('relation write scope must explicitly include partner_id');
const configuredProjectName = String(process.env.PROJECT_NAME ?? '').trim();
if (WRITE_MODE && configuredProjectName && configuredProjectName !== WRITE_AUTHORITY.project.name) deny('PROJECT_NAME does not match governed authority');
const PROJECT_NAME = WRITE_MODE ? WRITE_AUTHORITY.project.name : configuredProjectName;

if (VALIDATE_ONLY) {
  const factsRaw = String(process.env.P4_RUNNER_FACTS_JSON ?? '').trim();
  if (WRITE_MODE && factsRaw) {
    let facts;
    try { facts = JSON.parse(factsRaw); } catch { deny('P4_RUNNER_FACTS_JSON is not valid JSON'); }
    assertOwnedProjectFacts(WRITE_AUTHORITY, facts);
  }
  console.log(JSON.stringify({ status: 'GUARD_VALIDATION_ONLY', validated_only: true, project_id: PROJECT_ID, write_mode: WRITE_MODE }));
  process.exit(0);
}

const requireBase = path.join(process.cwd(), 'frontend/apps/web/package.json');
const { chromium } = createRequire(requireBase)('playwright');
const PASSWORD = process.env.E2E_PASSWORD || process.env.SC_DEMO_USER_PASSWORD || '';
const ACTION_ID = Number(process.env.ACTION_ID || 861);
const MENU_ID = Number(process.env.MENU_ID || 681);
const MEMBER_LOGIN = process.env.MEMBER_LOGIN || 'demo_role_project_a_member';
const READ_LOGIN = process.env.READ_LOGIN || 'demo_role_project_read';
const PREFLIGHT_LOGIN = process.env.PREFLIGHT_LOGIN || '';
const OUT = path.resolve(process.env.ARTIFACT_DIR || `artifacts/p4-project-profile-write/${Date.now()}`);
const originalName = WRITE_AUTHORITY?.project?.name || 'Codex P4 项目资料只读预检';

if (!PASSWORD) throw new Error('E2E_PASSWORD or SC_DEMO_USER_PASSWORD is required');
fs.mkdirSync(OUT, { recursive: true });

function normalize(value) { return String(value ?? '').replace(/\s+/g, ' ').trim(); }
function sameJson(left, right) { return JSON.stringify(left) === JSON.stringify(right); }
function recordWriteRequests(page) {
  const writes = [];
  const pending = new Map();
  page.on('request', (request) => {
    if (request.method() !== 'POST' || !request.url().includes('/api/v1/intent')) return;
    let body = {};
    try { body = JSON.parse(request.postData() || '{}'); } catch { return; }
    const isWrite = (body?.intent === 'api.data' && body?.params?.op === 'write') || body?.intent === 'api.data.write';
    if (!isWrite || body?.params?.model !== 'project.project' || !body?.params?.ids?.map(Number).includes(PROJECT_ID)) return;
    const entry = { body, at: Date.now(), outcome: 'pending' };
    writes.push(entry);
    pending.set(request, entry);
  });
  page.on('response', async (response) => {
    const entry = pending.get(response.request());
    if (!entry) return;
    entry.http_status = response.status();
    try {
      const body = await response.json();
      entry.business_ok = body?.ok === true;
      entry.response_error = body?.error || undefined;
    } catch {
      entry.business_ok = false;
      entry.response_error = 'non_json_response';
    }
    entry.outcome = response.ok() && entry.business_ok ? 'business_success' : 'response_failure';
    pending.delete(response.request());
  });
  page.on('requestfailed', (request) => {
    const entry = pending.get(request);
    if (!entry) return;
    entry.outcome = 'network_blocked';
    entry.network_error = request.failure()?.errorText || 'unknown';
    pending.delete(request);
  });
  return writes;
}
function recordDiagnostics(page) {
  const requests = [];
  const pending = new Map();
  page.on('request', (request) => {
    if (!request.url().includes('/api/v1/intent')) return;
    let body = {};
    try { body = JSON.parse(request.postData() || '{}'); } catch { /* non-json request */ }
    const params = { ...(body?.params || {}) };
    delete params.password;
    delete params.passwd;
    pending.set(request, { intent: body?.intent, params });
  });
  page.on('response', async (response) => {
    if (!response.url().includes('/api/v1/intent')) return;
    const entry = { url: response.url(), status: response.status(), ok: response.ok(), ...(pending.get(response.request()) || {}) };
    try {
      const body = await response.json();
      entry.intent = body?.intent || body?.meta?.intent;
      entry.business_ok = body?.ok;
      entry.error = body?.error || undefined;
      entry.data_keys = body?.data && typeof body.data === 'object' ? Object.keys(body.data) : [];
      if (body?.data?.records) entry.record_count = body.data.records.length;
    } catch { /* non-json response */ }
    requests.push(entry);
    pending.delete(response.request());
  });
  page.on('pageerror', (error) => requests.push({ type: 'pageerror', message: String(error.message || error) }));
  page.on('console', (message) => {
    if (message.type() === 'error' || message.type() === 'warning' || (message.type() === 'info' && message.text().startsWith('[save-trace]'))) requests.push({ type: 'console', level: message.type(), text: message.text().slice(0, 1000) });
  });
  page.on('requestfailed', (request) => requests.push({ type: 'requestfailed', url: request.url(), failure: request.failure()?.errorText || 'unknown' }));
  return requests;
}
function intentResponsePromise(page, expectedIntent) {
  return page.waitForResponse((response) => {
    if (!response.url().includes('/api/v1/intent')) return false;
    try {
      const request = JSON.parse(response.request().postData() || '{}');
      return request?.intent === expectedIntent;
    } catch {
      return false;
    }
  }, { timeout: 30000 });
}
async function successfulIntentData(response, label) {
  const body = await response.json().catch(() => ({}));
  if (!response.ok() || body?.ok !== true || !body?.data || typeof body.data !== 'object') {
    throw new Error(`${label}_failed:${JSON.stringify({ http_status: response.status(), business_ok: body?.ok === true, code: body?.error?.code || body?.code || '' })}`);
  }
  return body.data;
}
async function login(page, login) {
  await page.goto(`${FRONTEND_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const inputs = page.locator('input');
  await inputs.nth(0).fill(login);
  await inputs.nth(1).fill(PASSWORD);
  if (await inputs.nth(2).isEnabled().catch(() => false)) await inputs.nth(2).fill(DB_NAME);
  const loginResponse = intentResponsePromise(page, 'login');
  const initResponse = intentResponsePromise(page, 'system.init');
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 30000 });
  return {
    login: await successfulIntentData(await loginResponse, 'login'),
    init: await successfulIntentData(await initResponse, 'system_init'),
  };
}
async function token(page) { return page.evaluate((db) => sessionStorage.getItem(`sc_auth_token:${db}`) || '', DB_NAME); }
async function intent(page, name, params, allowError = false) {
  const bearer = await token(page);
  return page.evaluate(async ({ db, bearer, name, params, allowError }) => {
    const response = await fetch(`/api/v1/intent?db=${encodeURIComponent(db)}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: bearer ? `Bearer ${bearer}` : '' },
      body: JSON.stringify({ intent: name, params }),
    });
    const body = await response.json().catch(() => ({}));
    if (!allowError && (!response.ok || body.ok === false)) throw new Error(JSON.stringify(body.error || body));
    return { status: response.status, ok: body.ok === true, data: body.data || {}, error: body.error || {} };
  }, { db: DB_NAME, bearer, name, params, allowError });
}
async function readProject(page) {
  const result = await intent(page, 'api.data', {
    op: 'read', model: 'project.project', ids: [PROJECT_ID],
    fields: ['id', 'name', 'project_code', 'partner_id', 'date_start', 'date', 'description', 'lifecycle_state', 'responsibility_ids'], context: {},
  });
  return result.data.records?.[0] || null;
}
function many2oneId(value) {
  const raw = Array.isArray(value) ? value[0] : value;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}
async function readProjectFacts(page) {
  const project = await readProject(page);
  const responsibilityIds = (project?.responsibility_ids || []).map(Number).filter(Number.isFinite);
  let responsibilities = [];
  if (responsibilityIds.length) {
    const result = await intent(page, 'api.data', {
      op: 'read', model: 'project.responsibility', ids: responsibilityIds,
      fields: ['id', 'project_id', 'role_key', 'user_id', 'note'], context: {},
    });
    responsibilities = (result.data.records || []).map((row) => ({
      id: Number(row.id),
      project_id: many2oneId(row.project_id),
      role_key: String(row.role_key || ''),
      user_id: many2oneId(row.user_id),
      note: String(row.note || ''),
    })).sort((left, right) => left.id - right.id);
  }
  return {
    project: {
      id: Number(project?.id),
      name: String(project?.name || ''),
      project_code: String(project?.project_code || ''),
      partner_id: many2oneId(project?.partner_id),
      date_start: project?.date_start || false,
      date: project?.date || false,
      description: project?.description || false,
      lifecycle_state: project?.lifecycle_state || false,
      responsibility_ids: responsibilityIds.slice().sort((left, right) => left - right),
    },
    responsibilities,
  };
}
async function captureDraftSnapshot(page) {
  return page.evaluate(() => {
    const normalizeText = (value) => String(value ?? '').replace(/\s+/g, ' ').trim();
    const controls = (root) => [...(root?.querySelectorAll('input, textarea, select, [contenteditable="true"]') || [])]
      .filter((control) => {
        const style = window.getComputedStyle(control);
        return style.display !== 'none' && style.visibility !== 'hidden';
      })
      .map((control) => ({
        tag: control.tagName.toLowerCase(),
        type: control.getAttribute('type') || '',
        placeholder: control.getAttribute('placeholder') || '',
        value: control.getAttribute('contenteditable') === 'true'
          ? normalizeText(control.textContent || '')
          : String(control.value ?? ''),
      }));
    const fieldControls = (name) => controls(document.querySelector(`[data-field-name="${name}"]`));
    const responsibility = document.querySelector('[data-field-name="responsibility_ids"]');
    const rows = [...(responsibility?.querySelectorAll('tbody tr') || [])].map((row, index) => ({
      index,
      state: normalizeText(row.querySelector('.o2m-state-badge')?.textContent || ''),
      controls: controls(row),
    }));
    return {
      fields: {
        name: fieldControls('name'),
        date_start: fieldControls('date_start'),
        date: fieldControls('date'),
        description: fieldControls('description'),
      },
      responsibility: {
        summary: normalizeText(responsibility?.querySelector('[data-detail-collection-summary]')?.textContent || ''),
        row_count: rows.length,
        rows,
      },
    };
  });
}
function responsibilityOperations(writes, index) {
  return writes[index]?.body?.params?.vals?.responsibility_ids || [];
}
function hasCompleteResponsibilityOperations(operations) {
  const commands = operations.map((operation) => Number(operation?.[0]));
  return [0, 1, 2].every((command) => commands.includes(command));
}
function relationOperationsApplied(initialFacts, finalFacts, operations) {
  const initialRows = new Map(initialFacts.responsibilities.map((row) => [row.id, row]));
  const finalRows = new Map(finalFacts.responsibilities.map((row) => [row.id, row]));
  return operations.every((operation) => {
    const command = Number(operation?.[0]);
    const id = Number(operation?.[1]);
    const vals = operation?.[2] || {};
    if (command === 2) return initialRows.has(id) && !finalRows.has(id);
    if (command === 1) {
      const row = finalRows.get(id);
      return Boolean(row) && Object.entries(vals).every(([name, value]) => {
        if (name === 'user_id') return row.user_id === Number(value);
        return String(row[name] ?? '') === String(value ?? '');
      });
    }
    if (command === 0) {
      return finalFacts.responsibilities.some((row) => Object.entries(vals).every(([name, value]) => {
        if (name === 'user_id') return row.user_id === Number(value);
        return String(row[name] ?? '') === String(value ?? '');
      }));
    }
    return true;
  });
}
async function waitForWriteOutcome(page, writes, index, timeout = 20000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    if (writes[index] && writes[index].outcome !== 'pending') return writes[index];
    await page.waitForTimeout(50);
  }
  throw new Error(`write_outcome_timeout:${index}`);
}
// The many2many check starts draft-only: it drives the official relation control
// through mouse, keyboard, blur, Escape, clear, consecutive searches and a narrow
// viewport while recording mutation requests and the authoritative relation queries.
// It then closes the business loop on the same governed objects: a form save that
// commits the relation, a discard that must not write, a failed save that keeps the
// draft and a retry that has to match an authoritative readback. Only the save
// scenarios may write, and each one asserts its own request count.
function recordMutationRequests(page) {
  const mutations = [];
  page.on('request', (request) => {
    if (!request.url().includes('/api/v1/intent')) return;
    let body = {};
    try { body = JSON.parse(request.postData() || '{}'); } catch { return; }
    const op = String(body?.params?.op || '');
    const isDataWrite = body?.intent === 'api.data' && ['write', 'create', 'unlink'].includes(op);
    if (!isDataWrite && body?.intent !== 'api.data.write') return;
    mutations.push({ intent: body?.intent, model: body?.params?.model || null, op: op || null, fields: Object.keys(body?.params?.vals || {}).sort() });
  });
  return mutations;
}
function recordRelationQueries(page, model) {
  const entries = [];
  const byRequest = new Map();
  const waiters = [];
  page.on('request', (request) => {
    if (!request.url().includes('/api/v1/intent')) return;
    let body = {};
    try { body = JSON.parse(request.postData() || '{}'); } catch { return; }
    if (body?.intent !== 'api.data' || body?.params?.op !== 'list' || body?.params?.model !== model) return;
    const entry = { search_term: body?.params?.search_term ?? null, limit: body?.params?.limit ?? null, status: null };
    entries.push(entry);
    byRequest.set(request, entry);
    waiters.splice(0).forEach((resolve) => resolve(entry));
  });
  page.on('response', (response) => {
    const entry = byRequest.get(response.request());
    if (!entry) return;
    entry.status = response.status();
    entry.ok = response.ok();
    byRequest.delete(response.request());
  });
  return {
    entries,
    next(timeoutMs = 20000) {
      return new Promise((resolve) => {
        const timer = setTimeout(() => resolve(null), timeoutMs);
        waiters.push((entry) => { clearTimeout(timer); resolve(entry); });
      });
    },
  };
}
async function readRelationCandidates(page, model, searchTerm) {
  const result = await intent(page, 'api.data', {
    op: 'list', model, fields: ['name'], limit: 80,
    search_term: searchTerm || undefined, context: {},
  });
  return (result.data.records || []).map((row) => normalize(row.name));
}
async function readProjectTagIds(page) {
  const result = await intent(page, 'api.data', {
    op: 'read', model: 'project.project', ids: [PROJECT_ID], fields: ['id', 'tag_ids'], context: {},
  });
  const raw = result.data.records?.[0]?.tag_ids;
  if (!raw || raw === false) return [];
  return (Array.isArray(raw) ? raw : [raw]).map(Number).filter(Number.isFinite).sort((left, right) => left - right);
}
async function verifyMany2manyTagSelect(browser, page, report, beforeFacts) {
  const expectedTags = WRITE_AUTHORITY.tags || [];
  const expectedNames = expectedTags.map((row) => normalize(row.name)).sort();
  const mutations = recordMutationRequests(page);
  const relationQueries = recordRelationQueries(page, 'project.tags');
  const writes = recordWriteRequests(page);
  report.writes = writes;
  const carrier = WRITE_AUTHORITY?.carrier;
  if (!carrier || Number(carrier.id) === PROJECT_ID) throw new Error('m2m_carrier_precondition_failed');
  const beforeTagIds = await readProjectTagIds(page);
  if (beforeTagIds.length) throw new Error(`m2m_precondition_failed:${JSON.stringify(beforeTagIds)}`);

  const fieldRoot = page.locator('[data-field-name="tag_ids"]').first();
  await fieldRoot.waitFor({ timeout: 30000 });
  const input = fieldRoot.locator('input').first();
  await input.waitFor({ timeout: 30000 });
  const panel = page.locator('.t-select__dropdown:visible');
  const optionRows = panel.locator('li.t-select-option');
  const selectedChips = () => fieldRoot.locator('.t-tag');
  const optionLabels = async () => (await optionRows.allInnerTexts()).map(normalize).filter(Boolean);
  const selectableLabels = async () => (await optionLabels()).filter((label) => !label.startsWith('创建'));
  const draftClean = () => page.getByText('尚未修改', { exact: true }).isVisible();
  const draftDirty = async () => !(await draftClean());
  const dirtyIndicatorShown = async () => (await page.getByText('有未保存修改', { exact: true }).count()) > 0;
  // A control that already holds chips collapses the official TagInput input to
  // a sliver until it is focused, so a freshly loaded control has no clickable
  // input box and the interaction has to start from the control itself. The
  // official arrow (``.t-input__suffix``, always the dropdown icon and never a
  // clear affordance) is that control's own toggle, so it opens the panel from
  // any state; clicking the wrapper instead can land on a chip's close icon.
  const relationToggle = fieldRoot.locator('.t-input__suffix').first();
  const focusControl = async () => {
    if (await relationToggle.count()) await relationToggle.click();
    else await input.click();
    await input.waitFor({ state: 'visible', timeout: 15000 });
  };
  const openPanel = async () => {
    if (!(await panel.count())) await focusControl();
    await panel.waitFor({ state: 'visible', timeout: 15000 });
  };
  const closePanel = async () => {
    await input.press('Escape');
    await panel.waitFor({ state: 'hidden', timeout: 15000 }).catch(() => {});
  };
  // The official panel is portalled outside the field root, so every panel
  // assertion has to look at the visible dropdown, not at the field subtree.
  const waitForCandidates = (total) => page.waitForFunction(
    (expected) => document.querySelectorAll('.t-select__dropdown .t-select-option').length >= expected,
    total, { timeout: 20000 },
  );
  const waitForVisibleLabel = async (label) => {
    const deadline = Date.now() + 20000;
    while (Date.now() < deadline) {
      const labels = await optionLabels();
      if (labels.some((value) => value.includes(label))) return;
      await page.waitForTimeout(100);
    }
    throw new Error(`m2m_option_label_not_visible:${label}`);
  };
  const searchFor = async (keyword) => {
    const pending = relationQueries.next();
    await input.fill(keyword);
    const entry = await pending;
    if (!entry) throw new Error(`m2m_relation_query_missing:${keyword}`);
    await page.waitForTimeout(250);
    return entry;
  };

  // 1. The panel offers every batch-owned candidate without any keyword, and
  //    opening it changes neither the draft nor the backend.
  await openPanel();
  await waitForCandidates(expectedTags.length);
  const unfiltered = await selectableLabels();
  const candidatesLoaded = JSON.stringify(unfiltered.slice().sort()) === JSON.stringify(expectedNames)
    && await draftClean() && mutations.length === 0;
  report.scenarios.push({ name: 'm2m_candidates_loaded_without_keyword', status: candidatesLoaded ? 'PASS' : 'FAIL', candidates: unfiltered, draft_clean: await draftClean(), mutation_requests: mutations.length });
  if (!candidatesLoaded) throw new Error(`m2m_candidates_not_authoritative:${JSON.stringify({ unfiltered, expectedNames })}`);

  // 1b. Searching is not a field change: while a keyword is typed and no
  //     option has been picked, the relation value stays empty and no write is
  //     sent. The header dirty indicator is recorded next to it because a
  //     search-only keyword currently still raises it (recorded deviation).
  await searchFor('BETA');
  const searchOnlyTagIds = await readProjectTagIds(page);
  const searchOnlyChips = await selectedChips().count();
  const searchOnlyKeptValue = JSON.stringify(searchOnlyTagIds) === JSON.stringify(beforeTagIds)
    && searchOnlyChips === 0
    && mutations.length === 0;
  report.scenarios.push({
    name: 'm2m_search_only_keeps_the_relation_value',
    status: searchOnlyKeptValue ? 'PASS' : 'FAIL',
    chips: searchOnlyChips,
    relation_ids: searchOnlyTagIds,
    keyword_dirty_indicator: await dirtyIndicatorShown(),
    recorded_deviation: 'the form header reports unsaved changes while only a search keyword is present',
    mutation_requests: mutations.length,
  });
  if (!searchOnlyKeptValue) {
    throw new Error(`m2m_search_modified_the_relation:${JSON.stringify({ searchOnlyTagIds, searchOnlyChips })}`);
  }

  // 2. A blur closes the official panel, and the runtime keyword follows the
  //    official close: reopening shows the unfiltered candidates again.
  const emptyQuery = await searchFor('zzz-no-such-tag');
  await page.locator('[data-field-name="name"] input').first().click();
  await panel.waitFor({ state: 'hidden', timeout: 15000 });
  const blurredDraftClean = await draftClean();
  await openPanel();
  await waitForCandidates(expectedTags.length);
  const afterBlurLabels = await selectableLabels();
  const blurReset = blurredDraftClean
    && JSON.stringify(afterBlurLabels.slice().sort()) === JSON.stringify(expectedNames)
    && mutations.length === 0;
  report.scenarios.push({ name: 'm2m_blur_resets_keyword_and_draft', status: blurReset ? 'PASS' : 'FAIL', query: emptyQuery.search_term, candidates_after_blur: afterBlurLabels, draft_clean: blurredDraftClean, mutation_requests: mutations.length });
  if (!blurReset) throw new Error(`m2m_blur_left_a_stale_keyword:${JSON.stringify({ afterBlurLabels })}`);

  // 3. Escape closes the official panel; the visible input is empty and the
  //    reopened candidates are the unfiltered set, not the abandoned keyword.
  await searchFor('zzz-no-such-tag');
  await closePanel();
  const inputTextAfterEscape = normalize(await input.inputValue());
  const escapeDraftClean = await draftClean();
  await openPanel();
  await waitForCandidates(expectedTags.length);
  const afterEscapeLabels = await selectableLabels();
  const escapeReset = inputTextAfterEscape === ''
    && escapeDraftClean
    && JSON.stringify(afterEscapeLabels.slice().sort()) === JSON.stringify(expectedNames)
    && mutations.length === 0;
  report.scenarios.push({ name: 'm2m_escape_resets_keyword_and_draft', status: escapeReset ? 'PASS' : 'FAIL', input_after_escape: inputTextAfterEscape, candidates_after_escape: afterEscapeLabels, draft_clean: escapeDraftClean, mutation_requests: mutations.length });
  if (!escapeReset) throw new Error(`m2m_escape_left_a_stale_keyword:${JSON.stringify({ inputTextAfterEscape, afterEscapeLabels })}`);
  await closePanel();

  // 4. Consecutive searches: each keyword is requested on its own and the list
  //    that stays visible is the authoritative answer for the last keyword.
  const alphaName = expectedNames.find((name) => name.endsWith('-ALPHA'));
  const alphaKeyword = 'ALPHA';
  const alphaQuery = await searchFor(alphaKeyword);
  const alphaAuthority = (await readRelationCandidates(page, 'project.tags', alphaKeyword)).map(normalize).sort();
  const alphaVisible = (await selectableLabels()).slice().sort();
  const betaName = expectedNames.find((name) => name.endsWith('-BETA'));
  const betaKeyword = 'BETA';
  const betaQuery = await searchFor(betaKeyword);
  const betaAuthority = (await readRelationCandidates(page, 'project.tags', betaKeyword)).map(normalize).sort();
  await waitForVisibleLabel(betaKeyword);
  const betaVisible = (await selectableLabels()).slice().sort();
  const sequentialSearches = alphaQuery.search_term === alphaKeyword
    && betaQuery.search_term === betaKeyword
    && JSON.stringify(alphaVisible) === JSON.stringify(alphaAuthority)
    && JSON.stringify(betaVisible) === JSON.stringify(betaAuthority)
    && betaAuthority.length === 1 && betaAuthority[0] === betaName
    && mutations.length === 0;
  report.scenarios.push({
    name: 'm2m_consecutive_searches_last_is_authoritative',
    status: sequentialSearches ? 'PASS' : 'FAIL',
    queries: relationQueries.entries.map((entry) => entry.search_term),
    alpha: { keyword: alphaKeyword, authority: alphaAuthority, visible: alphaVisible },
    beta: { keyword: betaKeyword, authority: betaAuthority, visible: betaVisible },
    mutation_requests: mutations.length,
  });
  if (!sequentialSearches) throw new Error(`m2m_consecutive_search_not_authoritative:${JSON.stringify({ alphaAuthority, alphaVisible, betaAuthority, betaVisible })}`);

  // 5. Mouse selection: the official check clears the search state (the panel
  //    returns to the full candidate list) and only the draft changes.
  await optionRows.filter({ hasText: betaKeyword }).first().click();
  await page.waitForFunction((label) => [...document.querySelectorAll('[data-field-name="tag_ids"] .t-tag')].some((node) => (node.textContent || '').includes(label)), betaKeyword, { timeout: 15000 });
  await waitForCandidates(expectedTags.length);
  const afterMouseSelect = (await selectableLabels()).slice().sort();
  const chipsAfterMouseSelect = (await selectedChips().allInnerTexts()).map(normalize);
  const mouseSelect = chipsAfterMouseSelect.some((label) => label.includes(betaKeyword))
    && JSON.stringify(afterMouseSelect) === JSON.stringify(expectedNames)
    && await draftDirty()
    && mutations.length === 0;
  report.scenarios.push({ name: 'm2m_mouse_select_draft_only', status: mouseSelect ? 'PASS' : 'FAIL', chips: chipsAfterMouseSelect, candidates_after_check: afterMouseSelect, draft_dirty: await draftDirty(), mutation_requests: mutations.length });
  if (!mouseSelect) throw new Error(`m2m_mouse_select_not_proven:${JSON.stringify({ chipsAfterMouseSelect, afterMouseSelect })}`);
  await closePanel();

  // 6. Keyboard selection stays with the official list: Arrow + Enter commits the
  //    row the official panel highlights, and only the draft changes.
  const keyboardTarget = expectedNames.find((name) => name.endsWith('-GAMMA'));
  const hoveredRowLabel = async () => normalize(await page.evaluate(() => {
    const row = [...document.querySelectorAll('.t-select__dropdown .t-select-option')]
      .find((node) => String(node.className).includes('hover'));
    return row ? row.textContent : '';
  }));
  await openPanel();
  await waitForCandidates(expectedTags.length);
  let hovered = '';
  for (let press = 0; press <= expectedTags.length; press += 1) {
    hovered = await hoveredRowLabel();
    if (hovered.includes(keyboardTarget)) break;
    await input.press('ArrowDown');
    await page.waitForTimeout(150);
  }
  hovered = await hoveredRowLabel();
  await input.press('Enter');
  await page.waitForFunction((label) => [...document.querySelectorAll('[data-field-name="tag_ids"] .t-tag')].some((node) => (node.textContent || '').includes(label)), keyboardTarget, { timeout: 15000 });
  const chipsAfterKeyboard = (await selectedChips().allInnerTexts()).map(normalize);
  const keyboardSelect = hovered.includes(keyboardTarget)
    && chipsAfterKeyboard.some((label) => normalize(label) === hovered)
    && await draftDirty()
    && mutations.length === 0;
  report.scenarios.push({ name: 'm2m_keyboard_select_draft_only', status: keyboardSelect ? 'PASS' : 'FAIL', hovered_option: hovered, chips: chipsAfterKeyboard, draft_dirty: await draftDirty(), mutation_requests: mutations.length });
  if (!keyboardSelect) throw new Error(`m2m_keyboard_select_not_proven:${JSON.stringify({ hovered, chipsAfterKeyboard })}`);
  await closePanel();

  // 6b. Keyboard selection with a live search keyword: Enter must commit the
  //     option the official panel highlights. The keyword is a search term, not
  //     a tag, so the control suppresses TagInput's tag append through the
  //     official `tagInputProps.max` channel (see the component note
  //     official-enter-keyword); without it the append stops the keydown before
  //     the official keyboard handler. The target is the one batch candidate the
  //     previous step did not check, because the official multiple path answers
  //     Enter with check|uncheck (es/select/hooks/useKeyboardControl.mjs Enter ->
  //     getNewMultipleValue). Only the draft may change here.
  const keywordTarget = expectedNames.find((name) => name.endsWith('-ALPHA'));
  const keywordSearchTerm = 'ALPHA';
  await openPanel();
  const keywordQuery = await searchFor(keywordSearchTerm);
  await waitForVisibleLabel(keywordSearchTerm);
  const chipsBeforeGap = (await selectedChips().allInnerTexts()).map(normalize);
  const tagIdsBeforeGap = await readProjectTagIds(page);
  if (chipsBeforeGap.includes(normalize(keywordTarget))) {
    throw new Error(`m2m_keyword_enter_target_already_checked:${JSON.stringify(chipsBeforeGap)}`);
  }
  await input.press('ArrowDown');
  await page.waitForTimeout(200);
  const hoveredWithKeyword = await hoveredRowLabel();
  await input.press('Enter');
  await page.waitForFunction((label) => [...document.querySelectorAll('[data-field-name="tag_ids"] .t-tag')].some((node) => (node.textContent || '').includes(label)), hoveredWithKeyword, { timeout: 15000 });
  const chipsAfterGap = (await selectedChips().allInnerTexts()).map(normalize);
  const tagIdsAfterGap = await readProjectTagIds(page);
  const keywordNotATag = !chipsAfterGap.includes(keywordSearchTerm);
  // The relation value is draft-only until save, so the authoritative tag_ids
  // must stay exactly as read before the keyboard commit.
  const relationIdsUnchanged = JSON.stringify(tagIdsAfterGap) === JSON.stringify(tagIdsBeforeGap);
  const keyboardEnterWithKeyword = keywordQuery.search_term === keywordSearchTerm
    && hoveredWithKeyword === normalize(keywordTarget)
    && chipsAfterGap.length === chipsBeforeGap.length + 1
    && chipsAfterGap.includes(normalize(keywordTarget))
    && relationIdsUnchanged
    && keywordNotATag
    && normalize(await input.inputValue()) === ''
    && await draftDirty()
    && mutations.length === 0;
  report.scenarios.push({
    name: 'm2m_keyboard_enter_with_keyword_selects_highlighted',
    status: keyboardEnterWithKeyword ? 'PASS' : 'FAIL',
    keyword: keywordSearchTerm,
    search_term: keywordQuery.search_term,
    hovered_option: hoveredWithKeyword,
    expected_option: normalize(keywordTarget),
    chips_before: chipsBeforeGap,
    chips_after: chipsAfterGap,
    relation_ids_before: tagIdsBeforeGap,
    relation_ids_after: tagIdsAfterGap,
    relation_ids_unchanged: relationIdsUnchanged,
    keyword_after_enter: normalize(await input.inputValue()),
    keyword_became_a_tag: !keywordNotATag,
    official_channel: 'tagInputProps.max suppresses the TagInput tag append so the official Enter branch commits the highlighted option',
    mutation_requests: mutations.length,
  });
  if (!keyboardEnterWithKeyword) {
    throw new Error(`m2m_keyword_enter_did_not_select:${JSON.stringify({ hoveredWithKeyword, expected: normalize(keywordTarget), chipsBeforeGap, chipsAfterGap, tagIdsBeforeGap, tagIdsAfterGap })}`);
  }
  await closePanel();

  // 6c. Duplicate selection: the same record must never appear twice. Repeating
  //     the checked option through the official multiple path resolves to
  //     "uncheck", so the chips stay unique; whichever way it resolves, no write
  //     is sent before saving.
  await openPanel();
  const duplicateQuery = await searchFor(keywordSearchTerm);
  await waitForVisibleLabel(keywordSearchTerm);
  const chipsBeforeDuplicate = (await selectedChips().allInnerTexts()).map(normalize);
  await input.press('ArrowDown');
  await page.waitForTimeout(200);
  const duplicateHovered = await hoveredRowLabel();
  await input.press('Enter');
  await page.waitForTimeout(700);
  const chipsAfterDuplicate = (await selectedChips().allInnerTexts()).map(normalize);
  const labelCounts = new Map();
  chipsAfterDuplicate.forEach((label) => labelCounts.set(label, (labelCounts.get(label) || 0) + 1));
  const noDuplicateChip = [...labelCounts.values()].every((count) => count === 1);
  const duplicateTarget = normalize(keywordTarget);
  const keptChecked = chipsAfterDuplicate.length === chipsBeforeDuplicate.length
    && chipsAfterDuplicate.includes(duplicateTarget);
  const toggledOff = chipsAfterDuplicate.length === chipsBeforeDuplicate.length - 1
    && !chipsAfterDuplicate.includes(duplicateTarget);
  const duplicateSelection = duplicateQuery.search_term === keywordSearchTerm
    && duplicateHovered === duplicateTarget
    && noDuplicateChip
    && (keptChecked || toggledOff)
    && mutations.length === 0;
  report.scenarios.push({
    name: 'm2m_duplicate_selection_never_duplicates_a_record',
    status: duplicateSelection ? 'PASS' : 'FAIL',
    keyword: keywordSearchTerm,
    search_term: duplicateQuery.search_term,
    hovered_option: duplicateHovered,
    chips_before: chipsBeforeDuplicate,
    chips_after: chipsAfterDuplicate,
    official_resolution: toggledOff ? 'unchecked-on-repeat' : 'kept-checked',
    official_evidence: 'es/select/hooks/useKeyboardControl.mjs Enter -> getNewMultipleValue -> check|uncheck',
    mutation_requests: mutations.length,
  });
  if (!duplicateSelection) {
    throw new Error(`m2m_duplicate_selection_failed:${JSON.stringify({ duplicateHovered, chipsBeforeDuplicate, chipsAfterDuplicate })}`);
  }
  await page.screenshot({ path: path.join(OUT, 'm2m-keyboard-enter-with-keyword.png'), fullPage: true });
  await closePanel();
  while (await selectedChips().count()) {
    const before = await selectedChips().count();
    await selectedChips().first().locator('.t-icon-close, .t-tag__icon-close').first().click();
    await page.waitForFunction((remaining) => document.querySelectorAll('[data-field-name="tag_ids"] .t-tag').length < remaining, before, { timeout: 15000 }).catch(() => {});
    if (await selectedChips().count() >= before) break;
  }
  const chipsAfterClear = await selectedChips().count();
  const clearProven = chipsAfterClear === 0 && await draftClean() && mutations.length === 0;
  report.scenarios.push({ name: 'm2m_explicit_clear_restores_clean_draft', status: clearProven ? 'PASS' : 'FAIL', chips_after_clear: chipsAfterClear, draft_clean: await draftClean(), mutation_requests: mutations.length });
  if (!clearProven) throw new Error(`m2m_clear_not_proven:${JSON.stringify({ chipsAfterClear, draftClean: await draftClean() })}`);

  // 7. Narrow viewport: one panel, operable options, no horizontal overflow.
  await page.setViewportSize({ width: 390, height: 844 });
  await openPanel();
  await page.waitForFunction((total) => {
    const options = [...document.querySelectorAll('.t-select__dropdown .t-select-option')];
    if (options.length < total) return false;
    return document.documentElement.scrollWidth <= window.innerWidth;
  }, expectedTags.length, { timeout: 20000 });
  const narrow = await page.evaluate(() => {
    const panels = [...document.querySelectorAll('.t-select__dropdown')].filter((node) => node.getBoundingClientRect().width > 0);
    const option = panels[0]?.querySelector('li.t-select-option');
    if (!option) return { panels: panels.length, operable: false, overflow: true };
    const box = option.getBoundingClientRect();
    return {
      panels: panels.length,
      operable: option.contains(document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2)),
      overflow: document.documentElement.scrollWidth > window.innerWidth,
    };
  });
  await page.screenshot({ path: path.join(OUT, 'm2m-narrow-390.png'), fullPage: true });
  await closePanel();
  const narrowPassed = narrow.panels === 1 && narrow.operable && !narrow.overflow && await draftClean() && mutations.length === 0;
  report.scenarios.push({ name: 'm2m_narrow_viewport_single_panel', status: narrowPassed ? 'PASS' : 'FAIL', viewport: 390, panels: narrow.panels, option_operable: narrow.operable, horizontal_overflow: narrow.overflow, draft_clean: await draftClean(), mutation_requests: mutations.length });
  if (!narrowPassed) throw new Error(`m2m_narrow_viewport_not_proven:${JSON.stringify(narrow)}`);
  await page.setViewportSize({ width: 1440, height: 1000 });

  // 8. The whole journey stayed client-side: no mutation request reached the
  //    backend and the authoritative project facts are unchanged.
  const afterTagIds = await readProjectTagIds(page);
  const backendUnchanged = sameJson(beforeFacts, await readProjectFacts(page)) && sameJson(beforeTagIds, afterTagIds);
  report.scenarios.push({ name: 'm2m_journey_stayed_draft_only', status: backendUnchanged && mutations.length === 0 ? 'PASS' : 'FAIL', mutation_requests: mutations.length, authoritative_unchanged: backendUnchanged, relation_queries: relationQueries.entries });
  if (!backendUnchanged || mutations.length) throw new Error(`m2m_journey_wrote_state:${JSON.stringify({ mutations, beforeTagIds, afterTagIds })}`);

  // -------------------------------------------------------------------------
  // Write closure. The scenarios above stay draft-only on purpose; the ones
  // below close the business loop on the same governed objects. Every
  // expectation is bound to the authoritative readback, never to the DOM alone:
  // the control may only claim a saved relation after the backend confirms it.
  const chipLabels = async () => (await selectedChips().allInnerTexts()).map(normalize);
  const chipSetMatches = (labels, expected) => labels.length === expected.length
    && expected.every((label) => labels.some((value) => value === label || value.includes(label)));
  const alphaTag = expectedTags.find((row) => normalize(row.name).endsWith('-ALPHA'));
  const betaTag = expectedTags.find((row) => normalize(row.name).endsWith('-BETA'));
  const gammaTag = expectedTags.find((row) => normalize(row.name).endsWith('-GAMMA'));
  if (!alphaTag || !betaTag || !gammaTag) throw new Error('m2m_write_candidate_missing');
  const alphaId = Number(alphaTag.id);
  const alphaLabel = normalize(alphaTag.name);
  const betaLabel = normalize(betaTag.name);
  const gammaLabel = normalize(gammaTag.name);
  const tagCommandValues = (index) => writes[index]?.body?.params?.vals?.tag_ids ?? null;
  // Replay the submitted relation commands on top of the authoritative set that
  // was read before the save. The result must equal what the backend then
  // reports, whichever command shape the generic relation adapter sends.
  const applyTagCommands = (current, commands) => {
    const next = new Set(current);
    for (const command of commands || []) {
      const code = Number(command?.[0]);
      if (code === 6) { next.clear(); (command[2] || []).forEach((id) => next.add(Number(id))); }
      else if (code === 4) next.add(Number(command[1]));
      else if (code === 3 || code === 2) next.delete(Number(command[1]));
    }
    return [...next].sort((left, right) => left - right);
  };
  const clickOptionWithLabel = async (label) => {
    await openPanel();
    await input.fill('');
    await waitForCandidates(expectedTags.length);
    const labels = await optionLabels();
    const index = labels.findIndex((value) => value === label);
    if (index < 0) throw new Error(`m2m_option_label_missing:${label}`);
    await optionRows.nth(index).click();
    await page.waitForFunction((expected) => [...document.querySelectorAll('[data-field-name="tag_ids"] .t-tag')]
      .some((node) => (node.textContent || '').includes(expected)), label, { timeout: 15000 });
  };

  // 9. Selection plus save: the draft commits through one project.project write,
  //    the authoritative readback equals the submitted commands and the reloaded
  //    form shows the same relation.
  const preWriteTagIds = await readProjectTagIds(page);
  if (preWriteTagIds.length) throw new Error(`m2m_write_precondition_failed:${JSON.stringify(preWriteTagIds)}`);
  await clickOptionWithLabel(alphaLabel);
  const chipsBeforeSave = await chipLabels();
  const draftTagIds = await readProjectTagIds(page);
  const draftOnly = chipSetMatches(chipsBeforeSave, [alphaLabel]) && !draftTagIds.length
    && writes.length === 0 && mutations.length === 0 && await dirty(page);
  report.scenarios.push({ name: 'm2m_selection_stays_draft_until_save', status: draftOnly ? 'PASS' : 'FAIL', chips: chipsBeforeSave, relation_ids: draftTagIds, write_requests: writes.length, mutation_requests: mutations.length });
  if (!draftOnly) throw new Error(`m2m_write_draft_phase_failed:${JSON.stringify({ chipsBeforeSave, draftTagIds, writes: writes.length })}`);
  await closePanel();
  await save(page);
  const saveWrite = await waitForWriteOutcome(page, writes, 0);
  await page.waitForFunction(() => !document.body.innerText.includes('正在处理'), null, { timeout: 20000 });
  const cleanAfterSave = await draftClean();
  const savedTagIds = await readProjectTagIds(page);
  const savedFacts = await readProjectFacts(page);
  await page.reload({ waitUntil: 'domcontentloaded' });
  await field(page, 'tag_ids').waitFor({ timeout: 30000 });
  const refreshedTagIds = await readProjectTagIds(page);
  const refreshedChips = await chipLabels();
  const submittedTagIds = applyTagCommands(preWriteTagIds, tagCommandValues(0));
  const savedPassed = writes.length === 1 && saveWrite.outcome === 'business_success'
    && Object.prototype.hasOwnProperty.call(writes[0].body.params.vals || {}, 'tag_ids')
    && sameJson(submittedTagIds, [alphaId])
    && sameJson(submittedTagIds, savedTagIds)
    && sameJson(savedTagIds, refreshedTagIds)
    && chipSetMatches(refreshedChips, [alphaLabel])
    && cleanAfterSave
    && sameJson(beforeFacts, savedFacts);
  report.scenarios.push({
    name: 'm2m_selection_saves_and_reads_back', status: savedPassed ? 'PASS' : 'FAIL',
    selected_id: alphaId, selected_label: alphaLabel,
    write_requests: writes.length, requested_commands: tagCommandValues(0), requested_tag_ids: submittedTagIds,
    write_response: { outcome: saveWrite.outcome, http_status: saveWrite.http_status, business_ok: saveWrite.business_ok, error: saveWrite.response_error },
    authoritative_tag_ids: savedTagIds, refreshed_tag_ids: refreshedTagIds, refreshed_chips: refreshedChips,
    draft_clean_after_save: cleanAfterSave, unrelated_facts_unchanged: sameJson(beforeFacts, savedFacts),
  });
  if (!savedPassed) throw new Error(`m2m_save_readback_not_proven:${JSON.stringify({ writeRequests: writes.length, outcome: saveWrite.outcome, submittedTagIds, savedTagIds, refreshedTagIds, refreshedChips, cleanAfterSave })}`);

  // 10. Cancel: the form's own discard action reverts a dirty relation draft and
  //     must not produce any write.
  const writesBeforeDiscard = writes.length;
  const mutationsBeforeDiscard = mutations.length;
  await clickOptionWithLabel(betaLabel);
  const chipsBeforeDiscard = await chipLabels();
  const dirtyBeforeDiscard = await dirty(page);
  await closePanel();
  const discardAction = page.getByRole('button', { name: '放弃', exact: true }).first();
  await discardAction.waitFor({ timeout: 15000 });
  await discardAction.click();
  await page.waitForFunction((label) => {
    const chips = [...document.querySelectorAll('[data-field-name="tag_ids"] .t-tag')].map((node) => (node.textContent || '').trim());
    return chips.length === 1 && chips[0].includes(label);
  }, alphaLabel, { timeout: 20000 });
  const chipsAfterDiscard = await chipLabels();
  const cleanAfterDiscard = await draftClean();
  const authoritativeAfterDiscard = await readProjectTagIds(page);
  const discardPassed = chipSetMatches(chipsBeforeDiscard, [alphaLabel, betaLabel]) && dirtyBeforeDiscard
    && chipSetMatches(chipsAfterDiscard, [alphaLabel])
    && cleanAfterDiscard
    && writes.length === writesBeforeDiscard && mutations.length === mutationsBeforeDiscard
    && sameJson(authoritativeAfterDiscard, [alphaId]);
  report.scenarios.push({
    name: 'm2m_cancel_discards_draft_without_a_write', status: discardPassed ? 'PASS' : 'FAIL',
    discard_action: '放弃', superseded_chip: betaLabel,
    chips_before_discard: chipsBeforeDiscard, chips_after_discard: chipsAfterDiscard,
    draft_dirty_before_discard: dirtyBeforeDiscard, draft_clean_after_discard: cleanAfterDiscard,
    write_requests: writes.length, mutation_requests: mutations.length,
    authoritative_tag_ids: authoritativeAfterDiscard,
  });
  if (!discardPassed) throw new Error(`m2m_cancel_not_proven:${JSON.stringify({ chipsBeforeDiscard, chipsAfterDiscard, dirtyBeforeDiscard, cleanAfterDiscard, writes: writes.length, authoritativeAfterDiscard })}`);

  // 11. A failed save keeps the draft and changes nothing; the retry sends the
  //     same commands and the authoritative readback then matches the form.
  const writesBeforeFailure = writes.length;
  const mutationsBeforeFailure = mutations.length;
  await clickOptionWithLabel(gammaLabel);
  const chipsBeforeFailure = await chipLabels();
  let blocked = false;
  await page.route('**/api/v1/intent*', async (route) => {
    let body = {};
    try { body = JSON.parse(route.request().postData() || '{}'); } catch { return route.continue(); }
    const isProjectWrite = body?.intent === 'api.data' && body?.params?.op === 'write'
      && body?.params?.model === 'project.project' && sameJson(body?.params?.ids, [PROJECT_ID]);
    const isTagWrite = isProjectWrite && Object.prototype.hasOwnProperty.call(body?.params?.vals || {}, 'tag_ids');
    if (!isTagWrite) return route.continue();
    if (!blocked) { blocked = true; return route.abort('failed'); }
    return route.continue();
  });
  await closePanel();
  const saveButton = page.getByRole('button', { name: /^保存(?:修改)?$/, exact: true }).first();
  await saveButton.click();
  const failedWrite = await waitForWriteOutcome(page, writes, writesBeforeFailure);
  const errorFeedback = page.locator('.submission-feedback--error:visible, [data-semantic-component="ProductFormErrorSummary"]:visible').first();
  await errorFeedback.waitFor({ state: 'visible', timeout: 20000 });
  await page.waitForFunction(() => !document.body.innerText.includes('正在处理'), null, { timeout: 20000 });
  const feedbackText = normalize(await errorFeedback.innerText());
  const messageVisible = /保存失败|请求失败|网络异常|操作未完成|请稍后重试/.test(feedbackText);
  await errorFeedback.screenshot({ path: path.join(OUT, 'm2m-save-failure-feedback.png') });
  const chipsAfterFailure = await chipLabels();
  const dirtyAfterFailure = await dirty(page);
  const saveEnabledAfterFailure = !(await saveButton.isDisabled());
  const authoritativeAfterFailure = await readProjectTagIds(page);
  const failurePassed = blocked && failedWrite.outcome === 'network_blocked' && messageVisible
    && chipSetMatches(chipsAfterFailure, [alphaLabel, gammaLabel])
    && dirtyAfterFailure && saveEnabledAfterFailure
    && writes.length === writesBeforeFailure + 1 && mutations.length === mutationsBeforeFailure + 1
    && sameJson(authoritativeAfterFailure, [alphaId]);
  report.scenarios.push({
    name: 'm2m_save_failure_preserves_draft', status: failurePassed ? 'PASS' : 'FAIL',
    blocked, failed_message: messageVisible, feedback: feedbackText, write_outcome: failedWrite.outcome,
    chips_after_failure: chipsAfterFailure, draft_dirty: dirtyAfterFailure, save_enabled: saveEnabledAfterFailure,
    authoritative_tag_ids: authoritativeAfterFailure, write_requests: writes.length, mutation_requests: mutations.length,
  });
  if (!failurePassed) throw new Error(`m2m_save_failure_not_proven:${JSON.stringify({ blocked, outcome: failedWrite.outcome, messageVisible, chipsAfterFailure, dirtyAfterFailure, saveEnabledAfterFailure, authoritativeAfterFailure, writes: writes.length })}`);
  // The injection handler stays installed: after the single blocked attempt it
  // passes the relation write through, so the retry below is a real submission.
  await save(page);
  const retryWrite = await waitForWriteOutcome(page, writes, writesBeforeFailure + 1);
  await page.waitForFunction(() => !document.body.innerText.includes('正在处理'), null, { timeout: 20000 });
  const samePayloadRetried = sameJson(writes[writesBeforeFailure]?.body?.params?.vals, writes[writesBeforeFailure + 1]?.body?.params?.vals);
  const authoritativeAfterRetry = await readProjectTagIds(page);
  await page.reload({ waitUntil: 'domcontentloaded' });
  await field(page, 'tag_ids').waitFor({ timeout: 30000 });
  const refreshedAfterRetry = await readProjectTagIds(page);
  const refreshedChipsAfterRetry = await chipLabels();
  const expectedAfterRetry = applyTagCommands([alphaId], tagCommandValues(writesBeforeFailure + 1));
  const retryPassed = retryWrite.outcome === 'business_success' && samePayloadRetried
    && writes.length === writesBeforeFailure + 2
    && sameJson(expectedAfterRetry, authoritativeAfterRetry)
    && sameJson(authoritativeAfterRetry, refreshedAfterRetry)
    && chipSetMatches(refreshedChipsAfterRetry, [alphaLabel, gammaLabel])
    && sameJson(beforeFacts, await readProjectFacts(page));
  report.scenarios.push({
    name: 'm2m_save_retry_persists_and_matches_ui', status: retryPassed ? 'PASS' : 'FAIL',
    write_attempts: writes.length, backend_successful_submissions: writes.filter((row) => row.outcome === 'business_success').length,
    retry_response: { outcome: retryWrite.outcome, http_status: retryWrite.http_status, business_ok: retryWrite.business_ok, error: retryWrite.response_error },
    same_payload_retried: samePayloadRetried, requested_tag_ids: expectedAfterRetry,
    authoritative_tag_ids: authoritativeAfterRetry, refreshed_tag_ids: refreshedAfterRetry, refreshed_chips: refreshedChipsAfterRetry,
  });
  if (!retryPassed) throw new Error(`m2m_save_retry_not_proven:${JSON.stringify({ outcome: retryWrite.outcome, samePayloadRetried, authoritativeAfterRetry, refreshedAfterRetry, refreshedChipsAfterRetry })}`);

  // 12. The governed read-only principal must not be able to modify the
  //     relation: the direct tag write is denied and the form route itself is
  //     refused, so that role has no editable relation entry at all.
  const reader = (WRITE_AUTHORITY.role_candidates?.project_read_only || []).find((row) => row.login === READ_LOGIN);
  const readerAccess = (WRITE_AUTHORITY.effective_project_access?.project_read_only || []).find((row) => row.login === READ_LOGIN);
  if (!reader || !readerAccess || readerAccess.acl_write !== false || !readerAccess.record_read) {
    deny('m2m read-only principal must be a governed reader with denied write ACL');
  }
  const readonlyContext = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: 'zh-CN' });
  const readonlyPage = await readonlyContext.newPage();
  report.roles.readonly = { login: READ_LOGIN, diagnostics: recordDiagnostics(readonlyPage) };
  let readonlyPassed = false;
  try {
    const identity = await login(readonlyPage, READ_LOGIN);
    if (Number(identity.init?.user?.id) !== Number(reader.id)) deny('m2m read-only runtime identity mismatch');
    const readerProject = await readProject(readonlyPage);
    if (readerProject?.id !== PROJECT_ID) deny('m2m read-only principal cannot read the dedicated project');
    const currentTagIds = await readProjectTagIds(page);
    // Same-value write: if enforcement were broken this would still be a no-op,
    // so the probe never becomes a business change of its own.
    const denied = await intent(readonlyPage, 'api.data', {
      op: 'write', model: 'project.project', ids: [PROJECT_ID], vals: { tag_ids: [[6, 0, currentTagIds]] }, context: {},
    }, true);
    const reasonCode = String(denied.error?.code || '');
    const aclDenied = denied.ok === false && /ACCESS|FORBIDDEN|PERMISSION|DENIED/i.test(reasonCode);
    const writerReadback = await readProjectTagIds(page);
    const targetUrl = new URL(page.url());
    await readonlyPage.goto(targetUrl.href, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await readonlyPage.waitForURL((url) => url.pathname === '/access-denied'
      && url.searchParams.get('reason') === 'NAVIGATION_AUTHORITY_DENIED', { timeout: 30000 });
    const denialTextVisible = await readonlyPage.getByText(/无权限|没有权限|访问受限|权限不足/).first()
      .isVisible({ timeout: 10000 }).catch(() => false);
    const enabledRelationEdits = await readonlyPage.evaluate(() => {
      const root = document.querySelector('[data-field-name="tag_ids"]');
      if (!root) return 0;
      return [...root.querySelectorAll('button:not([disabled]), input:not([disabled]), [role="button"]')]
        .filter((node) => node.getClientRects().length).length;
    });
    await readonlyPage.screenshot({ path: path.join(OUT, 'm2m-readonly-denial.png'), fullPage: true });
    const unchanged = sameJson(writerReadback, currentTagIds);
    readonlyPassed = aclDenied && unchanged && denialTextVisible && enabledRelationEdits === 0;
    report.scenarios.push({
      name: 'm2m_readonly_principal_cannot_modify', status: readonlyPassed ? 'PASS' : 'FAIL',
      principal_id: reader.id, company_id: reader.company_id, role_code: String(identity.init?.role_surface?.role_code || ''),
      direct_write: { ok: denied.ok, http_status: denied.status, reason_code: reasonCode },
      authoritative_unchanged: unchanged, authoritative_tag_ids: writerReadback,
      navigation_reason: 'NAVIGATION_AUTHORITY_DENIED', denial_text_visible: denialTextVisible,
      url: readonlyPage.url(), enabled_relation_edits: enabledRelationEdits,
    });
  } finally {
    await readonlyContext.close();
  }
  if (!readonlyPassed) throw new Error('m2m_readonly_modification_not_denied');

  // 13. Write ledger for the closure: one committed save, one blocked attempt,
  //     one committed retry, and no relation write from the cancel or the
  //     read-only probe. The fixture cleanup then removes the objects and the
  //     batch is read back empty.
  const ledger = {
    write_attempts: writes.length,
    business_success: writes.filter((row) => row.outcome === 'business_success').length,
    network_blocked: writes.filter((row) => row.outcome === 'network_blocked').length,
    outcomes: writes.map((row) => row.outcome),
    mutation_requests: mutations.length,
    authoritative_tag_ids: await readProjectTagIds(page),
  };
  const ledgerPassed = ledger.write_attempts === 3 && ledger.business_success === 2 && ledger.network_blocked === 1;
  report.scenarios.push({ name: 'm2m_write_closure_request_ledger', status: ledgerPassed ? 'PASS' : 'FAIL', ...ledger });
  if (!ledgerPassed) throw new Error(`m2m_write_ledger_unexpected:${JSON.stringify(ledger)}`);

  // 14. Explicit create: a relation name with no exact match is offered through
  //     the official create row, and committing it creates the dictionary record
  //     and selects it. The created tag must then be authoritative in the same
  //     relation query, because the governed company scope no longer infers a
  //     company boundary from ``project_ids`` for the shared project dictionaries.
  //     Before that fix a tag no project carried yet stayed invisible, so this
  //     panel kept offering 创建「…」 for a name that already existed.
  const createdTagName = `CODEX-P4-${String(WRITE_AUTHORITY?.batch || '').toUpperCase()}-TAG-UI-${Date.now()}`;
  const tagIdsBeforeCreate = await readProjectTagIds(page);
  const writesBeforeCreate = writes.length;
  const createRequests = [];
  const onCreateResponse = async (response) => {
    if (!response.url().includes('/api/v1/intent')) return;
    let body = {};
    try { body = JSON.parse(response.request().postData() || '{}'); } catch { return; }
    const params = body?.params || {};
    if (body?.intent !== 'api.data' || params.op !== 'create' || params.model !== 'project.tags') return;
    let payload = {};
    try { payload = await response.json(); } catch { payload = {}; }
    createRequests.push({
      vals: params.vals || {},
      http_status: response.status(),
      ok: payload?.ok === true,
      id: Number(payload?.data?.id || payload?.data?.record?.id || 0) || 0,
      error: payload?.error || undefined,
    });
  };
  page.on('response', onCreateResponse);
  let createdTagId = 0;
  try {
    await openPanel();
    // Drive the keyword through the same path the other scenarios use, so the
    // official search signal and the governed relation query are both observed
    // instead of inferred from the rendered options.
    const createSearch = await searchFor(createdTagName);
    const createRow = optionRows.filter({ hasText: '创建' }).first();
    const createRowDeadline = Date.now() + 10000;
    while (Date.now() < createRowDeadline && !(await createRow.count())) await page.waitForTimeout(100);
    const optionsBeforeCreate = await optionLabels();
    const createRowOffered = (await createRow.count()) === 1
      && normalize(await createRow.innerText()).includes(createdTagName);
    report.scenarios.push({ name: 'm2m_create_option_is_offered_for_an_unknown_name', status: createRowOffered ? 'PASS' : 'FAIL', keyword: createdTagName, search_term: createSearch?.search_term ?? null, search_status: createSearch?.status ?? null, options: optionsBeforeCreate, mutation_requests: mutations.length });
    if (!createRowOffered) throw new Error(`m2m_create_option_missing:${JSON.stringify({ search_term: createSearch?.search_term ?? null, optionsBeforeCreate })}`);
    await createRow.click();
    const createDeadline = Date.now() + 20000;
    while (Date.now() < createDeadline && !createRequests.length) await page.waitForTimeout(100);
    const createResponse = createRequests[0] || null;
    createdTagId = Number(createResponse?.id || 0);
    await page.waitForFunction((label) => [...document.querySelectorAll('[data-field-name="tag_ids"] .t-tag')].some((node) => (node.textContent || '').includes(label)), createdTagName, { timeout: 20000 });
    const chipsAfterCreate = await chipLabels();
    const authoritativeAfterCreate = await readProjectTagIds(page);
    const createDraftOnly = createResponse?.ok === true && String(createResponse?.vals?.name || '') === createdTagName
      && createdTagId > 0 && writes.length === writesBeforeCreate
      && chipSetMatches(chipsAfterCreate, [alphaLabel, gammaLabel, createdTagName])
      && sameJson(authoritativeAfterCreate, tagIdsBeforeCreate);
    report.scenarios.push({ name: 'm2m_create_option_creates_and_selects_the_record', status: createDraftOnly ? 'PASS' : 'FAIL', keyword: createdTagName, created_id: createdTagId, create_request: createResponse, chips: chipsAfterCreate, authoritative_tag_ids_before_save: authoritativeAfterCreate, write_requests: writes.length, mutation_requests: mutations.length });
    if (!createDraftOnly) throw new Error(`m2m_create_option_did_not_create:${JSON.stringify({ createResponse, chipsAfterCreate, authoritativeAfterCreate })}`);

    // The created record is now authoritative for the same governed query: the
    // official panel returns the tag itself, so it stops offering 创建 for that
    // name. The option text has to equal the tag name exactly, which the create
    // row can never satisfy.
    await input.fill('');
    await waitForCandidates(expectedTags.length);
    const recallSearch = await searchFor(createdTagName);
    await page.waitForFunction((name) => [...document.querySelectorAll('.t-select__dropdown .t-select-option')].some((node) => (node.textContent || '').trim() === name), createdTagName, { timeout: 20000 });
    const optionsAfterCreate = await optionLabels();
    const createRowsAfterCreate = await optionRows.filter({ hasText: '创建' }).count();
    const createdTagVisible = optionsAfterCreate.filter((value) => value === createdTagName).length === 1
      && createRowsAfterCreate === 0;
    report.scenarios.push({ name: 'm2m_created_tag_is_authoritative_in_the_relation_query', status: createdTagVisible ? 'PASS' : 'FAIL', keyword: createdTagName, search_term: recallSearch?.search_term ?? null, options: optionsAfterCreate, create_row_count: createRowsAfterCreate });
    if (!createdTagVisible) throw new Error(`m2m_created_tag_not_visible:${JSON.stringify({ optionsAfterCreate, createRowsAfterCreate })}`);
    await page.screenshot({ path: path.join(OUT, 'm2m-created-tag-visible.png'), fullPage: true });

    // Selection, save and reload close the loop for the created record. The
    // create step already checked it, and the official multiple path toggles on
    // a repeat selection (see the duplicate-selection scenario), so the created
    // record must not be clicked a second time; only the panel is closed and the
    // draft the create produced is submitted.
    const dirtyAfterCreate = await dirty(page);
    await closePanel();
    const chipsBeforeCreatedSave = await chipLabels();
    const authoritativeBeforeCreatedSave = await readProjectTagIds(page);
    const writesBeforeCreatedSave = writes.length;
    await save(page);
    const createdSave = await waitForWriteOutcome(page, writes, writesBeforeCreatedSave);
    await page.waitForFunction(() => !document.body.innerText.includes('正在处理'), null, { timeout: 20000 });
    const expectedCreatedTagIds = applyTagCommands(authoritativeBeforeCreatedSave, tagCommandValues(writesBeforeCreatedSave));
    const authoritativeAfterCreatedSave = await readProjectTagIds(page);
    await page.reload({ waitUntil: 'domcontentloaded' });
    await field(page, 'tag_ids').waitFor({ timeout: 30000 });
    const refreshedCreatedTagIds = await readProjectTagIds(page);
    const refreshedCreatedChips = await chipLabels();
    const createdSavePassed = createdSave.outcome === 'business_success'
      && dirtyAfterCreate
      && chipSetMatches(chipsBeforeCreatedSave, [alphaLabel, gammaLabel, createdTagName])
      && expectedCreatedTagIds.includes(createdTagId)
      && sameJson(expectedCreatedTagIds, authoritativeAfterCreatedSave)
      && sameJson(authoritativeAfterCreatedSave, refreshedCreatedTagIds)
      && refreshedCreatedChips.some((label) => label.includes(createdTagName));
    report.scenarios.push({ name: 'm2m_created_tag_saves_and_reads_back', status: createdSavePassed ? 'PASS' : 'FAIL', created_id: createdTagId, created_label: createdTagName, draft_dirty_after_create: dirtyAfterCreate, chips_before_created_save: chipsBeforeCreatedSave, requested_tag_ids: expectedCreatedTagIds, authoritative_tag_ids: authoritativeAfterCreatedSave, refreshed_tag_ids: refreshedCreatedTagIds, refreshed_chips: refreshedCreatedChips, write_response: { outcome: createdSave.outcome, http_status: createdSave.http_status, business_ok: createdSave.business_ok } });
    if (!createdSavePassed) throw new Error(`m2m_created_tag_save_readback_not_proven:${JSON.stringify({ expectedCreatedTagIds, authoritativeAfterCreatedSave, refreshedCreatedTagIds, refreshedCreatedChips })}`);
  } finally {
    page.off('response', onCreateResponse);
  }
}

async function openProject(page) {
  // Reuse the verified formal navigation chain; do not hand-splice a form route.
  await page.goto(`${FRONTEND_URL}/s/workspace.home`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.locator('li[data-navigation-label="项目中心"] > .t-menu__item').click();
  await page.locator('li[data-navigation-label="项目创建"] > .t-menu__item').click();
  await page.locator('li[data-navigation-node][data-navigation-menu-id="681"]').click();
  await page.waitForFunction(() => !/正在载入数据|正在加载列表/.test(document.body.innerText || ''), null, { timeout: 30000 });
  if (PROJECT_NAME) await page.getByRole('button', { name: PROJECT_NAME, exact: true }).waitFor({ timeout: 30000 });
  let formContractSeen = false;
  const formContract = new Promise((resolve) => {
    const timer = setTimeout(() => resolve(false), 30000);
    page.on('response', async (response) => {
      if (!response.url().includes('/api/v1/intent')) return;
      try {
        const body = await response.json();
        const data = body?.data || {};
        if (body?.ok === true && data?.pageInfo?.viewType === 'form' && data?.layoutContract) {
          formContractSeen = true; clearTimeout(timer); resolve(true);
        }
      } catch { /* diagnostic listener only */ }
    });
  });
  const target = page.locator(`[data-record-id="${PROJECT_ID}"], [data-id="${PROJECT_ID}"]`).first();
  if (await target.count()) await target.click();
  else {
    const rows = PROJECT_NAME ? page.getByRole('button', { name: PROJECT_NAME, exact: true }) : page.locator('[data-semantic-component="ListPage"] button').filter({ hasText: /项目/ });
    const count = await rows.count();
    if (!count) throw new Error(`target_record_not_found:${PROJECT_ID}`);
    await rows.first().click();
  }
  await page.waitForURL((url) => url.pathname.startsWith('/f/project.project/'), { timeout: 30000 });
  if (!(await formContract)) throw new Error(`form_contract_not_ready:${JSON.stringify({ url: page.url(), formContractSeen })}`);
  await page.waitForFunction(() => {
    const text = document.body.innerText || '';
    const fields = document.querySelectorAll('[data-field-name]').length;
    const explicitError = /错误|无权限|不存在|登录|加载失败/.test(text);
    const loading = /正在加载页面|正在加载表单|加载中/.test(text);
    const save = [...document.querySelectorAll('button')].some((button) => /保存/.test(button.textContent || '') && !button.disabled);
    return fields > 0 && save || explicitError;
  }, null, { timeout: 30000 });
  const state = await page.evaluate(() => ({ url: location.href, title: document.title, text: (document.body.innerText || '').slice(0, 1200), fields: [...document.querySelectorAll('[data-field-name]')].map((el) => el.getAttribute('data-field-name')).slice(0, 80) }));
  if (!new URL(state.url).pathname.startsWith('/f/project.project/')) throw new Error(`route_mismatch:${JSON.stringify(state)}`);
  if (new URL(state.url).pathname === '/login' || new URL(state.url).pathname.startsWith('/login/')) throw new Error(`login_redirect:${JSON.stringify(state)}`);
  if (/403|404|无权限|不存在|错误/.test(state.text)) throw new Error(`page_error:${JSON.stringify(state)}`);
  return state;
}
function field(page, name) { return page.locator(`[data-field-name="${name}"]`).first(); }
async function fillField(page, name, value) {
  const root = field(page, name);
  const control = root.locator('input, textarea, [contenteditable="true"]').first();
  await control.waitFor({ timeout: 12000 });
  if (await control.getAttribute('contenteditable') === 'true') await control.fill(value);
  else await control.fill(value);
}
async function chooseDate(page, index, day) {
  const input = page.locator('[data-field-name="date_start"] input').nth(index);
  await input.click();
  const popup = page.locator('.t-popup__content:visible .t-date-picker__panel').last();
  await popup.waitFor({ state: 'visible', timeout: 12000 });
  await popup.locator('td:not(.t-is-disabled) .t-date-picker__cell-inner').filter({ hasText: new RegExp(`^${day}$`) }).first().click();
}
async function save(page) {
  const button = page.getByRole('button', { name: /^保存(?:修改)?$/, exact: true }).first();
  await button.waitFor({ timeout: 12000 });
  await button.click();
  try { await page.getByText(/保存成功/).waitFor({ timeout: 20000 }); }
  catch (error) { const body = await page.locator('body').innerText().catch(() => ''); if (/请检查以下内容|角色不能为空|责任人不能为空/.test(body)) throw new Error('validation_rejected:responsibility_required'); throw error; }
}
async function saveWithFailureRecovery(page, writes, report, draftBeforeFailure) {
  let blocked = false;
  let resolveBlocked;
  const blockedRequest = new Promise((resolve) => { resolveBlocked = resolve; });
  await page.route('**/api/v1/intent*', async (route) => {
    try { const body = JSON.parse(route.request().postData() || '{}'); if (!blocked && body.intent === 'api.data' && body.params?.op === 'write' && Number(body.params?.ids?.[0]) === PROJECT_ID) { blocked = true; resolveBlocked(true); await route.abort('failed'); return; } } catch {}
    await route.continue();
  });
  const button = page.getByRole('button', { name: /^保存(?:修改)?$/, exact: true }).first();
  await button.click();
  await Promise.race([blockedRequest, new Promise((_, reject) => setTimeout(() => reject(new Error('save_request_not_blocked')), 20000))]);
  const firstWrite = await waitForWriteOutcome(page, writes, 0);
  const feedback = page.locator('.submission-feedback--error:visible, [data-semantic-component="ProductFormErrorSummary"]:visible').first();
  await feedback.waitFor({ state: 'visible', timeout: 20000 });
  await page.waitForFunction(() => !document.body.innerText.includes('正在处理'), null, { timeout: 20000 });
  const failedState = await page.evaluate(() => ({ text: document.body.innerText, processing: document.body.innerText.includes('正在处理') }));
  const saveDisabled = await button.isDisabled();
  const feedbackText = normalize(await feedback.innerText());
  const feedbackBox = await feedback.boundingBox();
  const feedbackVisible = await feedback.isVisible() && Boolean(feedbackBox?.width && feedbackBox?.height);
  await feedback.screenshot({ path: path.join(OUT, 'failure-feedback-visible.png') });
  await page.screenshot({ path: path.join(OUT, 'failure-before-retry.png'), fullPage: true });
  const draftAfterFailure = await captureDraftSnapshot(page);
  const factsAfterFailure = await readProjectFacts(page);
  const failedMessageVisible = feedbackVisible && /保存失败|请求失败|网络异常|操作未完成|请稍后重试/.test(feedbackText);
  const draftPreserved = sameJson(draftBeforeFailure, draftAfterFailure);
  const backendUnchanged = sameJson(report.preflight.authoritative_facts, factsAfterFailure);
  const operations = responsibilityOperations(writes, 0);
  const operationsComplete = hasCompleteResponsibilityOperations(operations);
  const failurePassed = blocked && firstWrite.outcome === 'network_blocked' && failedMessageVisible
    && !failedState.processing && !saveDisabled && draftPreserved && backendUnchanged && operationsComplete;
  report.scenarios.push({
    name: 'failure_attempt', status: failurePassed ? 'PASS' : 'FAIL', blocked,
    failed_message: failedMessageVisible,
    feedback: { visible: feedbackVisible, text: feedbackText, locator: 'ProductFormErrorSummary', element_screenshot: 'failure-feedback-visible.png', page_screenshot: 'failure-before-retry.png' },
    busy_released: !failedState.processing, save_disabled: saveDisabled,
    draft_preserved: draftPreserved, draft_before_failure: draftBeforeFailure, draft_after_failure: draftAfterFailure,
    backend_unchanged: backendUnchanged, authoritative_after_failure: factsAfterFailure,
    responsibility_operations_complete: operationsComplete, responsibility_operations: operations,
    write_outcome: firstWrite.outcome,
  });
  if (!failurePassed) throw new Error(`failure_recovery_evidence_incomplete:${JSON.stringify({ blocked, writeOutcome: firstWrite.outcome, failedMessageVisible, processing: failedState.processing, saveDisabled, draftPreserved, backendUnchanged, operationsComplete })}`);
  await page.unroute('**/api/v1/intent*');
  await button.click();
  await page.getByText(/保存成功/).waitFor({ timeout: 20000 });
  const retryWrite = await waitForWriteOutcome(page, writes, 1);
  await page.waitForFunction(() => !document.body.innerText.includes('正在处理'), null, { timeout: 20000 });
  const afterRetry = await readProjectFacts(page);
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.locator('[data-field-name]').first().waitFor({ timeout: 30000 });
  const refreshed = await readProjectFacts(page);
  const samePayload = sameJson(writes[0]?.body?.params?.vals, writes[1]?.body?.params?.vals);
  const refreshConsistent = sameJson(afterRetry, refreshed);
  const changedFromInitial = !sameJson(report.preflight.authoritative_facts, afterRetry);
  const operationsApplied = relationOperationsApplied(report.preflight.authoritative_facts, afterRetry, responsibilityOperations(writes, 1));
  const retryPassed = writes.length === 2 && retryWrite.outcome === 'business_success' && samePayload
    && changedFromInitial && refreshConsistent && operationsApplied
    && afterRetry.project.lifecycle_state === report.preflight.authoritative_facts.project.lifecycle_state;
  report.scenarios.push({
    name: 'retry_success', status: retryPassed ? 'PASS' : 'FAIL', write_attempts: writes.length,
    browser_attempts: { blocked: 1, allowed: 1 }, backend_successful_submissions: retryWrite.business_ok === true ? 1 : 0,
    retry_response: { outcome: retryWrite.outcome, http_status: retryWrite.http_status, business_ok: retryWrite.business_ok, error: retryWrite.response_error },
    same_payload_retried: samePayload, responsibility_operations_applied: operationsApplied,
    lifecycle_unchanged: afterRetry.project.lifecycle_state === report.preflight.authoritative_facts.project.lifecycle_state,
    authoritative_after_retry: afterRetry, refreshed, refresh_consistent: refreshConsistent,
  });
  if (!retryPassed) throw new Error(`retry_evidence_incomplete:${JSON.stringify({ writes: writes.length, outcome: retryWrite.outcome, samePayload, changedFromInitial, refreshConsistent, operationsApplied })}`);
}
async function dirty(page) { return /未保存|已修改\s*\d+\s*项/.test(normalize(await page.locator('.record-header-context:visible').innerText().catch(() => ''))); }
async function verifyCustomerRelation(page, report, beforeFacts) {
  const input = field(page, 'partner_id').locator('input').first();
  const mutations = [];
  page.on('request', (request) => {
    let body; try { body = request.postDataJSON(); } catch { return; }
    if (body?.intent === 'api.data' && ['write', 'create', 'unlink'].includes(body.params?.op)) {
      mutations.push({ model: body.params.model, op: body.params.op });
    }
  });
  await input.fill('AB');
  await field(page, 'name').locator('input').first().click();
  const unchangedDraft = await page.getByText('尚未修改', { exact: true }).isVisible();
  if (!unchangedDraft || mutations.length) throw new Error('query_blur_mutated_relation');
  report.scenarios.push({ name: 'customer_query_blur_preserves_draft', status: 'PASS', mutation_requests: 0 });

  await input.click();
  const popup = page.locator('.many2one-option-panel:visible');
  await popup.waitFor({ state: 'visible' });
  const more = popup.getByRole('button', { name: /搜索更多/ });
  const unobscured = await more.evaluate((element) => {
    const box = element.getBoundingClientRect();
    return element.contains(document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2));
  });
  if (!unobscured) throw new Error('relation_option_obscured');
  await page.screenshot({ path: path.join(OUT, 'customer-popup.png'), fullPage: true });
  const response = page.waitForResponse((res) => {
    let body; try { body = res.request().postDataJSON(); } catch { return false; }
    return body?.intent === 'api.data' && body.params?.model === 'res.partner'
      && body.params?.op === 'list' && body.params?.fields?.includes('email');
  });
  await more.click();
  const searched = await response;
  if (!searched.ok()) throw new Error(`customer_search_failed:${searched.status()}`);
  const dialog = page.locator('.relation-dialog:visible');
  await dialog.waitFor({ state: 'visible' });
  await page.waitForFunction(() => !document.querySelector('.relation-dialog [aria-busy="true"]'));
  if (await dialog.getByRole('alert').count()) throw new Error('customer_search_error_visible');
  await dialog.getByRole('button', { name: '取消', exact: true }).click();
  await dialog.waitFor({ state: 'hidden' });
  await page.waitForFunction(() => document.querySelector('[data-field-name="partner_id"]')?.contains(document.activeElement));
  if (await popup.count()) throw new Error('customer_cancel_reopened_dropdown');
  if (!(await page.getByText('尚未修改', { exact: true }).isVisible()) || mutations.length) throw new Error('customer_cancel_mutated_relation');
  report.scenarios.push({ name: 'customer_search_cancel_and_overlay', status: 'PASS', search_http_status: searched.status(), option_unobscured: unobscured, focus_restored: true, dropdown_reopened: false });

  await page.setViewportSize({ width: 390, height: 844 });
  await input.click();
  await popup.waitFor({ state: 'visible' });
  // Popup positioning follows viewport updates asynchronously; assert the settled layout.
  await page.waitForFunction(() => {
    const panel = [...document.querySelectorAll('.many2one-option-panel')].find(e => e.getBoundingClientRect().width > 0);
    const button = panel?.querySelector('button');
    if (!button) return false;
    const box = button.getBoundingClientRect();
    return button.contains(document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2))
      && document.documentElement.scrollWidth <= innerWidth;
  });
  const narrow = await more.evaluate((element) => {
    const box = element.getBoundingClientRect();
    return { visible: element.contains(document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2)), overflow: document.documentElement.scrollWidth > innerWidth };
  });
  await page.screenshot({ path: path.join(OUT, 'customer-popup-390.png'), fullPage: true });
  await input.press('Escape');
  await popup.waitFor({ state: 'hidden' });
  if (!narrow.visible || narrow.overflow || await popup.count() || mutations.length) throw new Error('customer_narrow_popup_or_escape_failed');
  const unchanged = sameJson(beforeFacts, await readProjectFacts(page));
  if (!unchanged) throw new Error('customer_relation_probe_changed_backend');
  report.scenarios.push({ name: 'customer_narrow_escape_no_write', status: 'PASS', viewport: 390, option_unobscured: true, authoritative_unchanged: true, mutation_requests: mutations.length });

  // The remaining relation paths run through the official component only: the
  // documented keys, the panel's own actions and the official input. No business
  // state is written, so every assertion below binds the draft and the backend.
  const panelOptionIds = () => page.evaluate(() => [...document.querySelectorAll('.many2one-option-panel li.t-select-option[data-relation-option-value]')]
    .map((node) => node.getAttribute('data-relation-option-value')));
  const optionRowsOf = (scope) => scope.locator('li.t-select-option[data-relation-option-value]');
  const panelRowCount = () => optionRowsOf(popup).count();
  const headerState = async () => normalize(await page.locator('.record-header-context:visible').innerText().catch(() => ''));
  const waitUntil = async (predicate, timeoutMs = 15000) => {
    const deadline = Date.now() + timeoutMs;
    for (;;) {
      if (await predicate()) return true;
      if (Date.now() > deadline) return false;
      await page.waitForTimeout(120);
    }
  };
  const waitForPanelRows = (minimum, timeoutMs = 20000) => waitUntil(async () => (await panelRowCount()) >= minimum, timeoutMs);

  // Keyboard selection: press ArrowDown onto an option that is not the current
  // value and commit it with Enter. The official component owns navigation.
  await page.setViewportSize({ width: 1440, height: 900 });
  await input.click();
  await popup.waitFor({ state: 'visible' });
  if (!(await waitForPanelRows(1))) throw new Error('customer_keyboard_panel_empty');
  const selectedRowValue = async () => {
    const selected = popup.locator('li.t-select-option[aria-selected="true"]').first();
    return (await selected.count()) ? String(await selected.getAttribute('data-relation-option-value')) : '';
  };
  const valueBeforeKeyboard = await selectedRowValue();
  const rowTotal = await panelRowCount();
  let targetIndex = -1;
  for (let index = 0; index < rowTotal; index += 1) {
    const candidate = String(await optionRowsOf(popup).nth(index).getAttribute('data-relation-option-value'));
    if (candidate && candidate !== valueBeforeKeyboard) { targetIndex = index; break; }
  }
  if (targetIndex < 0) throw new Error(`customer_keyboard_target_missing:${JSON.stringify({ valueBeforeKeyboard, rowTotal })}`);
  const keyboardId = Number(await optionRowsOf(popup).nth(targetIndex).getAttribute('data-relation-option-value'));
  const keyboardLabel = normalize(await optionRowsOf(popup).nth(targetIndex).innerText());
  for (let index = 0; index <= targetIndex; index += 1) await input.press('ArrowDown');
  await input.press('Enter');
  await popup.waitFor({ state: 'hidden' });
  const keyboardDirty = await waitUntil(() => dirty(page), 6000);
  const keyboardValue = normalize(await input.inputValue());
  const keyboardFacts = await readProjectFacts(page);
  const keyboardUnchanged = sameJson(beforeFacts, keyboardFacts);
  const keyboardPassed = Number.isSafeInteger(keyboardId) && keyboardId > 0 && keyboardLabel.length > 0
    && keyboardValue === keyboardLabel && keyboardDirty && keyboardUnchanged && !mutations.length;
  report.scenarios.push({
    name: 'customer_keyboard_selection_updates_draft', status: keyboardPassed ? 'PASS' : 'FAIL',
    selected_id: keyboardId, selected_label: keyboardLabel, input_value: keyboardValue,
    superseded_value: valueBeforeKeyboard, draft_dirty: keyboardDirty,
    authoritative_unchanged: keyboardUnchanged, mutation_requests: mutations.length,
  });
  if (!keyboardPassed) throw new Error(`customer_keyboard_selection_not_in_draft:${JSON.stringify({ keyboardId, keyboardLabel, keyboardValue, keyboardDirty, keyboardUnchanged })}`);

  // Explicit clear through the panel action: the value must actually empty, and
  // clearing must not reach the backend until the form is submitted.
  await input.click();
  await popup.waitFor({ state: 'visible' });
  await popup.getByRole('button', { name: /清除选择/ }).first().click();
  await popup.waitFor({ state: 'hidden' });
  const clearedValue = normalize(await input.inputValue());
  await input.click();
  await popup.waitFor({ state: 'visible' });
  const clearedSelectedRows = await popup.locator('li.t-select-option[aria-selected="true"]').count();
  const clearedFacts = await readProjectFacts(page);
  const clearedUnchanged = sameJson(beforeFacts, clearedFacts);
  const clearedPassed = clearedValue === '' && clearedSelectedRows === 0 && clearedUnchanged && !mutations.length;
  report.scenarios.push({
    name: 'customer_explicit_clear_empties_value', status: clearedPassed ? 'PASS' : 'FAIL',
    input_value: clearedValue, selected_option_rows: clearedSelectedRows,
    authoritative_unchanged: clearedUnchanged, mutation_requests: mutations.length,
  });
  if (!clearedPassed) throw new Error(`customer_clear_not_applied:${JSON.stringify({ clearedValue, clearedSelectedRows, clearedUnchanged })}`);

  // Zero-result search and recovery: a keyword without matches must show no
  // candidate, must not touch the draft or the backend, and must recover.
  const zeroKeyword = 'zzz-no-such-customer-9f3d1';
  const headerBeforeQuery = await headerState();
  await input.fill(zeroKeyword);
  await page.waitForTimeout(1200);
  const zeroRows = await panelRowCount();
  const zeroSelectedRows = await popup.locator('li.t-select-option[aria-selected="true"]').count();
  const zeroEmptyState = await popup.locator('.t-select__empty').isVisible().catch(() => false);
  await input.fill('UM');
  if (!(await waitForPanelRows(1))) throw new Error('customer_query_recovery_failed');
  const recoveredRows = await panelRowCount();
  const headerAfterQuery = await headerState();
  const recoveredFacts = await readProjectFacts(page);
  const recoveryPassed = zeroRows === 0 && zeroSelectedRows === 0 && zeroEmptyState && recoveredRows > 0
    && headerBeforeQuery === headerAfterQuery && sameJson(beforeFacts, recoveredFacts) && !mutations.length;
  report.scenarios.push({
    name: 'customer_zero_result_and_query_recovery', status: recoveryPassed ? 'PASS' : 'FAIL',
    keyword: zeroKeyword, zero_result_rows: zeroRows, zero_result_selected_rows: zeroSelectedRows,
    empty_state_visible: zeroEmptyState, draft_state_unchanged_by_search: headerBeforeQuery === headerAfterQuery,
    recovered_rows: recoveredRows, authoritative_unchanged: sameJson(beforeFacts, recoveredFacts), mutation_requests: mutations.length,
  });
  if (!recoveryPassed) throw new Error(`customer_zero_result_or_recovery_failed:${JSON.stringify({ zeroRows, zeroSelectedRows, zeroEmptyState, recoveredRows, headerBeforeQuery, headerAfterQuery })}`);

  // Leaving the search must not promote the typed keyword into the field value:
  // Escape closes the panel and the control falls back to the committed value.
  await input.press('Escape');
  await popup.waitFor({ state: 'hidden' });
  const valueAfterSearchEscape = normalize(await input.inputValue());
  if (valueAfterSearchEscape !== '') throw new Error(`customer_search_keyword_became_value:${JSON.stringify({ valueAfterSearchEscape })}`);

  // Query failure: a failed candidate search must stay contained. Nothing is
  // written, the draft is untouched, and the next search recovers.
  let failedSearches = 0;
  const failRelationList = async (route) => {
    let body; try { body = route.request().postDataJSON(); } catch { body = null; }
    const isRelationList = body?.intent === 'api.data' && body.params?.model === 'res.partner' && body.params?.op === 'list';
    if (!isRelationList) return route.continue().catch(() => {});
    failedSearches += 1;
    return route.abort('failed').catch(() => {});
  };
  await page.route('**/api/v1/intent*', failRelationList);
  await input.click();
  await popup.waitFor({ state: 'visible' });
  const headerBeforeFailure = await headerState();
  await input.fill('UM-P3');
  await page.waitForTimeout(1400);
  const rowsDuringFailure = await panelRowCount();
  const selectedDuringFailure = await popup.locator('li.t-select-option[aria-selected="true"]').count();
  await page.unroute('**/api/v1/intent*');
  const headerAfterFailure = await headerState();
  await input.fill('UM');
  if (!(await waitForPanelRows(1))) throw new Error('customer_query_failure_recovery_failed');
  const recoveredAfterFailure = await panelRowCount();
  const failureFacts = await readProjectFacts(page);
  const failurePassed = failedSearches > 0 && selectedDuringFailure === 0
    && headerBeforeFailure === headerAfterFailure && recoveredAfterFailure > 0
    && sameJson(beforeFacts, failureFacts) && !mutations.length;
  report.scenarios.push({
    name: 'customer_query_failure_then_recovery', status: failurePassed ? 'PASS' : 'FAIL',
    failed_relation_searches: failedSearches, rows_during_failure: rowsDuringFailure,
    selected_rows_during_failure: selectedDuringFailure, draft_state_unchanged: headerBeforeFailure === headerAfterFailure,
    recovered_rows: recoveredAfterFailure, authoritative_unchanged: sameJson(beforeFacts, failureFacts), mutation_requests: mutations.length,
  });
  if (!failurePassed) throw new Error(`customer_query_failure_not_contained:${JSON.stringify({ failedSearches, rowsDuringFailure, selectedDuringFailure, recoveredAfterFailure, headerBeforeFailure, headerAfterFailure })}`);

  // Rapid consecutive searches: the earlier candidate search is held open while
  // the next keyword is typed. Each keyword owns its request now, so the later
  // keyword must answer for itself, and the late earlier response must neither
  // repaint the panel nor become selectable. No third input may be required.
  // The held-open first keyword resolves to a single partner through the
  // record-id search branch; the latest keyword resolves to the whole match
  // set. Different result sets are what make "the earlier response did not
  // repaint the panel" observable rather than vacuous.
  const lateKeyword = '6390';
  const latestKeyword = 'UM';
  const sameIdSet = (left, right) => Array.isArray(left) && Array.isArray(right)
    && left.length === right.length && [...left].sort().join('|') === [...right].sort().join('|');
  const referenceIdsFor = async (keyword) => {
    await input.fill(keyword);
    if (!(await waitUntil(() => panelRowCount().then((count) => count > 0), 20000))) return null;
    return panelOptionIds();
  };
  // Each keyword's authoritative rows, captured with no route installed, so the
  // concurrency assertions compare against the server's own answer.
  const referenceLateIds = await referenceIdsFor(lateKeyword);
  const referenceLatestIds = await referenceIdsFor(latestKeyword);
  if (!referenceLatestIds?.length || !referenceLateIds?.length) {
    throw new Error(`customer_stale_reference_missing:${JSON.stringify({ referenceLateIds, referenceLatestIds })}`);
  }
  if (sameIdSet(referenceLateIds, referenceLatestIds)) {
    throw new Error(`customer_stale_keywords_not_distinguishable:${JSON.stringify({ referenceLateIds, referenceLatestIds })}`);
  }
  let relationSearches = 0;
  const relationSearchTerms = [];
  let staleForwardedAt = 0;
  const searchStart = Date.now();
  const elapsed = () => Date.now() - searchStart;
  const optionState = async () => ({
    store_size: Number(await page.locator('.many2one-widget-shell .sc-relation-field').first()
      .getAttribute('data-option-count').catch(() => '0')) || 0,
    rows: await panelRowCount(),
    ids: await panelOptionIds(),
    empty_visible: await popup.locator('.t-select__empty').isVisible().catch(() => false),
  });
  const delayFirstRelationSearch = async (route) => {
    let body; try { body = route.request().postDataJSON(); } catch { body = null; }
    const isRelationList = body?.intent === 'api.data' && body.params?.model === 'res.partner' && body.params?.op === 'list';
    if (!isRelationList) return route.continue().catch(() => {});
    const requestIndex = (relationSearches += 1);
    relationSearchTerms.push(String(body.params.search_term ?? ''));
    if (requestIndex === 1) {
      // Hold the first keyword open long enough for the next keyword to issue,
      // settle and be observed before this response is allowed to land.
      await new Promise((resolve) => setTimeout(resolve, 2500));
      staleForwardedAt = elapsed();
    }
    return route.continue().catch(() => {});
  };
  const headerBeforeStale = await headerState();
  await page.route('**/api/v1/intent*', delayFirstRelationSearch);
  await input.fill(lateKeyword);
  const slowSearchIssued = await waitUntil(() => relationSearches >= 1, 8000);
  const secondKeywordAt = elapsed();
  await input.fill(latestKeyword);
  // The newer keyword must settle with its own authoritative rows, with no
  // further input, even while the earlier request is still in flight.
  const latestSettled = await waitUntil(async () => sameIdSet(await panelOptionIds(), referenceLatestIds), 20000);
  const stateAfterSecondKeyword = await optionState();
  // The late earlier response must leave the newer keyword's rows in place.
  const waited = await waitUntil(() => staleForwardedAt > 0 && elapsed() > staleForwardedAt + 1500, 20000);
  const stateAfterStaleResponse = await optionState();
  const staleSettledAt = elapsed();
  const staleSelectedRows = await popup.locator('li.t-select-option[aria-selected="true"]').count();
  await page.unroute('**/api/v1/intent*');
  const headerAfterStale = await headerState();
  const staleFacts = await readProjectFacts(page);
  const stalePassed = slowSearchIssued && relationSearches === 2
    && relationSearchTerms[0] === lateKeyword && relationSearchTerms[1] === latestKeyword
    && secondKeywordAt > 0 && latestSettled
    && stateAfterSecondKeyword.ids.length > 0 && sameIdSet(stateAfterSecondKeyword.ids, referenceLatestIds)
    && waited && sameIdSet(stateAfterStaleResponse.ids, referenceLatestIds)
    && !sameIdSet(stateAfterStaleResponse.ids, referenceLateIds)
    && staleSelectedRows === 0
    && headerAfterStale === headerBeforeStale && sameJson(beforeFacts, staleFacts) && !mutations.length;
  report.scenarios.push({
    name: 'customer_stale_search_does_not_repaint', status: stalePassed ? 'PASS' : 'FAIL',
    slow_search_issued: slowSearchIssued, relation_searches: relationSearches,
    relation_search_terms: relationSearchTerms, third_input_required: false,
    reference_late_ids: referenceLateIds, reference_latest_ids: referenceLatestIds,
    second_keyword_at_ms: secondKeywordAt, stale_response_forwarded_at_ms: staleForwardedAt,
    stale_response_settled_at_ms: staleSettledAt, waited_past_stale_response: waited,
    latest_keyword_settled_without_extra_input: latestSettled,
    state_after_second_keyword: stateAfterSecondKeyword, state_after_stale_response: stateAfterStaleResponse,
    selected_rows_after_stale_response: staleSelectedRows,
    draft_state_unchanged: headerAfterStale === headerBeforeStale,
    authoritative_unchanged: sameJson(beforeFacts, staleFacts), mutation_requests: mutations.length,
  });
  if (!stalePassed) throw new Error(`customer_stale_search_overwrote_result:${JSON.stringify({ relationSearches, relationSearchTerms, secondKeywordAt, staleForwardedAt, waited, latestSettled, stateAfterSecondKeyword, stateAfterStaleResponse, referenceLateIds, referenceLatestIds, staleSelectedRows })}`);

  await input.press('Escape');
  await popup.waitFor({ state: 'hidden' });
  const finalValue = normalize(await input.inputValue());
  if (finalValue !== '') throw new Error(`customer_probe_left_value_dirty:${JSON.stringify({ finalValue })}`);
}

async function verifyCustomerRelationWrite(page, report, beforeFacts) {
  const mutations = [];
  const writes = recordWriteRequests(page);
  report.writes = writes;
  page.on('request', request => {
    let body; try { body = request.postDataJSON(); } catch { return; }
    if ((body?.intent === 'api.data' && ['write', 'create', 'unlink'].includes(body.params?.op)) || body?.intent === 'api.data.write') mutations.push(body);
  });
  const input = field(page, 'partner_id').locator('input').first();
  await input.fill('');
  await input.click();
  // The candidate panel now belongs to the official Select popup: option rows
  // carry the projected option identity instead of a self-built row dataset.
  const optionPanel = page.locator('.many2one-option-panel:visible');
  await optionPanel.waitFor();
  const optionRows = optionPanel.locator('li.t-select-option[data-relation-option-value]');
  await optionRows.first().waitFor();
  await page.waitForFunction(() => [...document.querySelectorAll('.many2one-option-panel li.t-select-option[data-relation-option-value]')]
    .some((node) => Number(node.getAttribute('data-relation-option-value')) > 0), null, { timeout: 15000 });
  // The record may already carry a customer, so the scenario must select a
  // different record: re-picking the current value is not a modification and
  // would not prove that an explicit selection reaches the backend.
  const selectedRow = optionPanel.locator('li.t-select-option[aria-selected="true"]').first();
  const currentId = (await selectedRow.count()) ? String(await selectedRow.getAttribute('data-relation-option-value')) : '';
  const rowTotal = await optionRows.count();
  let optionIndex = -1;
  for (let index = 0; index < rowTotal; index += 1) {
    const candidate = String(await optionRows.nth(index).getAttribute('data-relation-option-value'));
    if (candidate && candidate !== currentId) { optionIndex = index; break; }
  }
  if (optionIndex < 0) throw new Error(`customer_write_target_missing:${JSON.stringify({ currentId, rowTotal })}`);
  const option = optionRows.nth(optionIndex);
  const selectedId = Number(await option.getAttribute('data-relation-option-value'));
  if (!Number.isSafeInteger(selectedId) || selectedId <= 0) throw new Error('customer_option_has_no_option_identity');
  const label = normalize(await option.innerText());
  let blocked = false;
  await page.route('**/api/v1/intent*', async route => {
    const body = route.request().postDataJSON();
    const mutation = (body?.intent === 'api.data' && ['write', 'create', 'unlink'].includes(body.params?.op)) || body?.intent === 'api.data.write';
    if (mutation) {
      const expected = body.intent === 'api.data' && body.params?.op === 'write'
        && body.params.model === 'project.project' && sameJson(body.params.ids, [PROJECT_ID])
        && sameJson(Object.keys(body.params.vals || {}), ['partner_id']) && body.params.vals.partner_id === selectedId;
      if (!expected) return route.abort('blockedbyclient');
      if (!blocked) { blocked = true; return route.abort('failed'); }
    }
    return route.continue();
  });
  await option.click();
  if (!await dirty(page) || normalize(await input.inputValue()) !== label) throw new Error('explicit_customer_selection_not_in_draft');
  if (mutations.length) throw new Error('customer_selection_mutated_before_save');
  const button = page.getByRole('button', { name: /^保存(?:修改)?$/, exact: true }).first();
  await button.click();
  const failedWrite = await waitForWriteOutcome(page, writes, 0);
  const error = page.locator('.submission-feedback--error:visible, [data-semantic-component="ProductFormErrorSummary"]:visible').first();
  await error.waitFor();
  const backendUnchanged = sameJson(beforeFacts, await readProjectFacts(page));
  const failurePassed = blocked && failedWrite.outcome === 'network_blocked'
    && writes[0]?.body?.params?.vals?.partner_id === selectedId
    && normalize(await input.inputValue()) === label && await dirty(page)
    && await input.isEditable() && !await button.isDisabled()
    && backendUnchanged;
  report.scenarios.push({ name: 'customer_selected_save_failure_preserves_draft', status: failurePassed ? 'PASS' : 'FAIL', selected_id: selectedId, superseded_id: currentId, backend_unchanged: backendUnchanged });
  if (!failurePassed) throw new Error('customer_failure_recovery_not_proven');
  await save(page);
  const retry = await waitForWriteOutcome(page, writes, 1);
  const after = await readProjectFacts(page);
  await page.reload({ waitUntil: 'domcontentloaded' });
  await field(page, 'partner_id').waitFor();
  const refreshed = await readProjectFacts(page);
  const refreshedLabel = normalize(await field(page, 'partner_id').locator('input').first().inputValue());
  const onlyExpectedWrites = mutations.length === 2 && mutations.every(body => body.intent === 'api.data'
    && body.params?.op === 'write' && body.params.model === 'project.project'
    && sameJson(body.params.ids, [PROJECT_ID]) && sameJson(Object.keys(body.params.vals || {}), ['partner_id'])
    && body.params.vals.partner_id === selectedId);
  const expected = { ...beforeFacts, project: { ...beforeFacts.project, partner_id: selectedId } };
  const passed = String(beforeFacts.project.partner_id ?? '') !== String(selectedId)
    && onlyExpectedWrites && refreshedLabel === label && writes.length === 2 && retry.outcome === 'business_success'
    && sameJson(writes[0].body.params.vals, writes[1].body.params.vals)
    && sameJson(expected, after) && sameJson(after, refreshed);
  report.scenarios.push({ name: 'customer_explicit_selection_retry_and_refresh', status: passed ? 'PASS' : 'FAIL', selected_id: selectedId, superseded_id: currentId, selected_id_source: 'clicked_option.data-relation-option-value', mutation_requests: mutations.length, only_expected_project_writes: onlyExpectedWrites, refreshed_ui_matches_selection: refreshedLabel === label, backend_successful_submissions: writes.filter(row => row.outcome === 'business_success').length, authoritative_after: after, refreshed });
  if (!passed) throw new Error('customer_selection_readback_not_proven');
}

async function verifyFieldValidation(page, report, beforeFacts) {
  const code = field(page, 'project_code');
  await code.waitFor({ state: 'visible', timeout: 10000 });
  const writableCode = await code.locator('input:not([disabled]):not([readonly]), textarea:not([disabled]):not([readonly]), [contenteditable="true"]').count();
  report.scenarios.push({ name: 'system_code_readonly', status: writableCode === 0 ? 'PASS' : 'FAIL', editable_controls: writableCode });
  if (writableCode) throw new Error('system_code_is_editable');
  const writes = recordWriteRequests(page);
  report.writes = writes;
  await fillField(page, 'name', '');
  await page.getByRole('button', { name: /^保存(?:修改)?$/, exact: true }).first().click();
  const feedback = page.locator('[data-semantic-component="ProductFormErrorSummary"]:visible, .submission-feedback--error:visible').first();
  await feedback.waitFor({ state: 'visible', timeout: 10000 });
  const invalid = await field(page, 'name').locator('[aria-invalid="true"]').count();
  const unchanged = sameJson(beforeFacts, await readProjectFacts(page));
  await page.screenshot({ path: path.join(OUT, 'required-field-error.png'), fullPage: true });
  await fillField(page, 'name', beforeFacts.project.name);
  const recovered = await field(page, 'name').locator('input').first().inputValue() === beforeFacts.project.name;
  const passed = invalid > 0 && unchanged && recovered && writes.length === 0;
  report.scenarios.push({ name: 'required_field_error_and_draft_recovery', status: passed ? 'PASS' : 'FAIL', invalid_controls: invalid, write_attempts: writes.length, authoritative_unchanged: unchanged, draft_editable_after_error: recovered });
  if (!passed) throw new Error('required_field_recovery_not_proven');
  const rejected = await intent(page, 'api.data', {
    op: 'write', model: 'project.project', ids: [PROJECT_ID],
    vals: { name: '', description: 'This rejected request must not persist' }, context: {},
  }, true);
  const serverUnchanged = sameJson(beforeFacts, await readProjectFacts(page));
  const serverRejected = !rejected.ok && rejected.status >= 400
    && JSON.stringify(rejected.error).includes('项目名称不能为空') && serverUnchanged;
  report.scenarios.push({ name: 'server_required_field_rejected_without_partial_write', status: serverRejected ? 'PASS' : 'FAIL', http_status: rejected.status, reason_code: rejected.error?.code, authoritative_unchanged: serverUnchanged });
  if (!serverRejected) throw new Error('server_required_field_rejection_not_proven');
  const validName = `${beforeFacts.project.name} · 已核验`;
  await fillField(page, 'name', validName);
  await save(page);
  const savedFacts = await readProjectFacts(page);
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.locator('[data-field-name="name"]').first().waitFor({ timeout: 30000 });
  const refreshedFacts = await readProjectFacts(page);
  const recoveredSave = savedFacts.project.name === validName
    && savedFacts.project.lifecycle_state === beforeFacts.project.lifecycle_state
    && sameJson(savedFacts, refreshedFacts);
  report.scenarios.push({ name: 'valid_save_after_field_error_and_refresh', status: recoveredSave ? 'PASS' : 'FAIL', authoritative_name: savedFacts.project.name, refresh_consistent: sameJson(savedFacts, refreshedFacts), lifecycle_unchanged: savedFacts.project.lifecycle_state === beforeFacts.project.lifecycle_state });
  if (!recoveredSave) throw new Error('valid_save_after_field_error_not_proven');
  return refreshedFacts;
}
async function verifyPermissionBoundary(browser, writerPage, report, beforeFacts) {
  const reader = WRITE_AUTHORITY.role_candidates.project_read_only.find((row) => row.login === READ_LOGIN);
  const access = WRITE_AUTHORITY.effective_project_access.project_read_only.find((row) => row.login === READ_LOGIN);
  if (!reader || reader.id === WRITE_AUTHORITY.writer.id || !access || access.acl_write !== false || !access.acl_read || !access.record_read) {
    deny('permission principal must be a distinct governed reader with denied write ACL');
  }
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: 'zh-CN' });
  const page = await context.newPage();
  report.roles.readonly = { login: READ_LOGIN, diagnostics: recordDiagnostics(page) };
  try {
    const identity = await login(page, READ_LOGIN);
    if (Number(identity.init?.user?.id) !== Number(reader.id) || Number(identity.init?.user?.company_id) !== Number(reader.company_id)) deny('reader runtime identity mismatch');
    const before = await readProject(page);
    if (before?.id !== PROJECT_ID) deny('reader cannot read exact dedicated project');
    // A direct, same-value request tests server enforcement without advancing a
    // lifecycle or changing business facts even if enforcement is broken.
    const rejected = await intent(page, 'api.data', {
      op: 'write', model: 'project.project', ids: [PROJECT_ID], vals: { name: before.name }, context: {},
    }, true);
    const code = String(rejected.error?.code || '');
    const unchanged = sameJson(beforeFacts, await readProjectFacts(writerPage));
    const passed = rejected.ok === false && /ACCESS|FORBIDDEN|PERMISSION|DENIED/i.test(code) && unchanged;
    report.scenarios.push({ name: 'readonly_direct_write_denied', status: passed ? 'PASS' : 'FAIL', principal_id: reader.id, company_id: reader.company_id, role_code: identity.init?.role_surface?.role_code, http_status: rejected.status, reason_code: code, authoritative_unchanged: unchanged });
    if (!passed) throw new Error(`readonly_write_denial_not_proven:${JSON.stringify({ code, ok: rejected.ok, unchanged })}`);
    // Deliberately revisit the writer's URL as a refusal counterexample.
    const targetUrl = new URL(writerPage.url());
    const targetRoute = targetUrl.pathname + targetUrl.search;
    await page.goto(targetUrl.href, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForURL((url) => url.pathname === '/access-denied'
      && url.searchParams.get('reason') === 'NAVIGATION_AUTHORITY_DENIED'
      && url.searchParams.get('from') === targetRoute, { timeout: 30000 });
    await page.getByText(/无权限|没有权限|访问受限|权限不足/).first().waitFor({ state: 'visible', timeout: 10000 });
    const enabledWrites = await page.getByRole('button', { name: /^(保存修改|保存|提交立项)$/ }).evaluateAll((buttons) => buttons.filter((button) => !button.disabled && button.getClientRects().length).length);
    report.scenarios.push({ name: 'readonly_write_actions_unavailable', status: enabledWrites === 0 ? 'PASS' : 'FAIL', enabled_write_actions: enabledWrites, target_route: targetRoute, reason_code: 'NAVIGATION_AUTHORITY_DENIED', url: page.url() });
    await page.screenshot({ path: path.join(OUT, 'readonly-denial.png'), fullPage: true });
    if (enabledWrites) throw new Error('readonly_write_action_enabled');
  } catch (error) {
    report.roles.readonly.failure_context = await page.evaluate(() => ({ url: location.href, text: (document.body.innerText || '').slice(0, 1500) })).catch(() => ({ url: page.url() }));
    await page.screenshot({ path: path.join(OUT, 'readonly-failure.png'), fullPage: true }).catch(() => {});
    throw error;
  } finally {
    await context.close();
  }
}
async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, locale: 'zh-CN' });
  const diagnostics = recordDiagnostics(page);
  const report = { database: DB_NAME, project_id: PROJECT_ID, action_id: ACTION_ID, menu_id: MENU_ID, read_only: READ_ONLY, scenarios: [], roles: {}, writes: [], diagnostics, errors: [] };
  try {
    const loginName = PREFLIGHT_LOGIN || (READ_ONLY ? READ_LOGIN : PM_LOGIN);
    const runtimeIdentity = await login(page, loginName);
    if (WRITE_MODE) assertRuntimeWriterIdentity(runtimeIdentity, WRITE_AUTHORITY);
    report.session_login = loginName;
    report.session_identity = {
      user_id: Number(runtimeIdentity.init?.user?.id || 0),
      company_id: Number(runtimeIdentity.init?.user?.company_id || 0),
      role_code: String(runtimeIdentity.init?.role_surface?.role_code || ''),
      governed_match: WRITE_MODE ? true : undefined,
    };
    const pageState = await openProject(page);
    const beforeFacts = await readProjectFacts(page);
    const before = beforeFacts.project;
    if (!before || before.id !== PROJECT_ID) throw new Error(`project ${PROJECT_ID} authoritative read failed`);
    if (WRITE_MODE) assertOwnedProjectFacts(WRITE_AUTHORITY, beforeFacts);
    report.preflight = { page_state: pageState, authoritative_read: before, authoritative_facts: beforeFacts };
    if (RELATION_WRITE_ONLY) {
      await verifyCustomerRelationWrite(page, report, beforeFacts);
      return;
    }
    if (RELATION_ONLY) {
      await verifyCustomerRelation(page, report, beforeFacts);
      return;
    }
    if (M2M_ONLY) {
      await verifyMany2manyTagSelect(browser, page, report, beforeFacts);
      return;
    }
    if (PERMISSION_ONLY) {
      const validatedFacts = await verifyFieldValidation(page, report, beforeFacts);
      await verifyPermissionBoundary(browser, page, report, validatedFacts);
      return;
    }
    if (PREFLIGHT_ONLY) {
      report.scenarios.push({ name: 'readonly_save_preflight', status: pageState.fields.length > 0 && before.id === PROJECT_ID ? 'PASS' : 'FAIL', save_controls: await page.locator('.template-page-header-actions button').allTextContents() });
      return;
    }
    if (READ_ONLY) {
      const editable = await page.locator('input:not([disabled]), textarea:not([disabled]), [contenteditable="true"]').count();
      const visibleFields = pageState.fields.length;
      const renderedText = normalize(pageState.text).length;
      report.scenarios.push({ name: 'readonly_preflight', status: visibleFields > 0 && renderedText > 0 && editable === 0 ? 'PASS' : 'FAIL', visible_fields: visibleFields, rendered_text_length: renderedText, editable_controls: editable });
      if (visibleFields === 0 || renderedText === 0) throw new Error(`form_not_rendered:${JSON.stringify({ visible_fields: visibleFields, rendered_text_length: renderedText })}`);
      await page.screenshot({ path: path.join(OUT, 'readonly-preflight.png'), fullPage: true });
      return;
    }
    const marker = `${originalName} · 真实保存 ${Date.now()}`;
    await fillField(page, 'name', marker);
    const dateRoot = field(page, 'date_start');
    const dateInputs = dateRoot.locator('input');
    if (await dateInputs.count() >= 2) {
      await chooseDate(page, 0, '15');
      await chooseDate(page, 1, '15');
    } else {
      await dateInputs.first().fill('2026-09-15');
      const end = field(page, 'date').locator('input').first();
      if (await end.count()) await end.fill('2026-10-15');
    }
    await fillField(page, 'description', 'P4 真实保存验收说明');
    const responsibility = field(page, 'responsibility_ids');
    const rows = responsibility.locator('tbody tr');
    const initialRows = await rows.count();
    if (initialRows < 2) throw new Error(`expected two responsibility rows, got ${initialRows}`);
    const firstNote = rows.nth(0).locator('input').last();
    if (await firstNote.count()) await firstNote.fill('P4 责任修改');
    await rows.nth(1).locator('.o2m-row-remove').click();
    await responsibility.locator('.o2m-create').click();
    const createdRow = responsibility.locator('tbody tr').last();
    const roleSelect = createdRow.locator('select').first();
    if (await roleSelect.count()) await roleSelect.selectOption('finance');
    else {
      const roleInput = createdRow.locator('input[placeholder="请选择角色"]').first();
      if (await roleInput.count()) { await roleInput.click(); await page.locator('.t-select-option').filter({ hasText: '项目经理' }).first().click(); }
      // Empty relation controls change their placeholder before the first query.
      // Bind the accessible field identity and require the real selection.
      const userInput = createdRow.getByRole('textbox', { name: '责任人', exact: true });
      await userInput.click();
      await page.locator('.t-select-option:visible').filter({ hasText: 'Demo-项目经理A' }).first().click();
    }
    const rowInputs = createdRow.locator('input');
    if (await rowInputs.count()) await rowInputs.last().fill('P4 责任新增');
    const roleValue = await createdRow.locator('input[placeholder="请选择角色"]').inputValue().catch(() => '');
    const userValue = await createdRow.getByRole('textbox', { name: '责任人', exact: true }).inputValue().catch(() => '');
    if (await roleSelect.count() === 0 && (!roleValue || !userValue)) throw new Error(`responsibility_selection_missing:${JSON.stringify({ role: Boolean(roleValue), user: Boolean(userValue) })}`);
    if (!await dirty(page)) throw new Error('draft did not become dirty');
    const draftBeforeFailure = NETWORK_FAILURE_RECOVERY ? await captureDraftSnapshot(page) : null;
    const writes = recordWriteRequests(page);
    if (NETWORK_FAILURE_RECOVERY) await saveWithFailureRecovery(page, writes, report, draftBeforeFailure);
    else await save(page);
    report.writes = writes;
    if (!NETWORK_FAILURE_RECOVERY) {
      await page.waitForTimeout(400);
      const after = await readProject(page);
      report.scenarios.push({ name: 'normal_save', status: after?.name === marker && after?.date_start === '2026-09-15' && after?.date === '2026-10-15' && writes.length === 1 ? 'PASS' : 'FAIL', before, after, write_count: writes.length, responsibility_rows_before: initialRows });
      await page.reload({ waitUntil: 'domcontentloaded' });
      await page.locator('.template-layout-shell').waitFor({ timeout: 30000 });
      const refreshed = await readProject(page);
      report.scenarios.push({ name: 'authoritative_refresh', status: refreshed?.name === marker && refreshed?.date_start === '2026-09-15' && refreshed?.date === '2026-10-15' ? 'PASS' : 'FAIL', refreshed });
    }
    await page.screenshot({ path: path.join(OUT, NETWORK_FAILURE_RECOVERY ? 'recovery-after-refresh.png' : 'normal-save.png'), fullPage: true });
  } catch (error) {
    report.failure_context = await page.evaluate(() => ({
      url: location.href, title: document.title,
      text: (document.body.innerText || '').slice(0, 1200),
      fields: [...document.querySelectorAll('[data-field-name]')].map(el => el.getAttribute('data-field-name')).slice(0, 80),
      viewport: {
        width: innerWidth, scrollWidth: document.documentElement.scrollWidth,
        overflow: [...document.querySelectorAll('body *')]
          .filter(el => el.getBoundingClientRect().right > innerWidth + 1 && getComputedStyle(el).visibility !== 'hidden')
          .map(el => ({ tag: el.tagName, cls: String(el.className), right: el.getBoundingClientRect().right,
            width: el.getBoundingClientRect().width, position: getComputedStyle(el).position, display: getComputedStyle(el).display }))
          .slice(0, 30),
      },
    })).catch(() => ({ url: page.url() }));
    await page.screenshot({ path: path.join(OUT, 'failure.png'), fullPage: true }).catch(() => {});
    report.errors.push(error instanceof Error ? error.stack || error.message : String(error));
  } finally {
    report.status = !report.errors.length && report.scenarios.every((row) => row.status === 'PASS') ? 'PASS' : 'FAIL';
    fs.writeFileSync(path.join(OUT, 'summary.json'), `${JSON.stringify(report, null, 2)}\n`);
    await browser.close();
  }
  console.log(JSON.stringify({ status: report.status, output: OUT, scenarios: report.scenarios, errors: report.errors }, null, 2));
  if (report.status !== 'PASS') process.exit(1);
}
await main();
