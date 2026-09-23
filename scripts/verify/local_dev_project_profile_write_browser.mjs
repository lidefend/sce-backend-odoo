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
  return {
    ...authority,
    batch,
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
const WRITE_AUTHORITY = WRITE_MODE ? loadWriteAuthority(PROJECT_ID) : null;
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
    if (RELATION_ONLY) {
      await verifyCustomerRelation(page, report, beforeFacts);
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
