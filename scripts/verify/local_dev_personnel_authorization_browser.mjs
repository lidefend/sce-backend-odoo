#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { launchChromium } from './playwright_runtime.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const EXPECTED_FRONTEND = 'http://127.0.0.1:5176';
const EXPECTED_DB = 'sc_dev_demo';
const EXPECTED_ENV = 'dev';
const EXPECTED_DBFILTER = '^sc_dev_demo$';
const NAMESPACE = 'codex_p4_personnel_authorization';
const BATCH_RE = /^[a-z0-9][a-z0-9-]{2,31}$/;
const FRONTEND_URL = String(process.env.FRONTEND_URL || '');
const DB_NAME = String(process.env.DB_NAME || '');
const BATCH = String(process.env.P4_PERSONNEL_AUTH_BATCH || '');
const PRODUCT_SHA = String(process.env.PRODUCT_CANDIDATE_SHA || '');
const TOOL_SHA = String(process.env.P4_TOOL_CANDIDATE_SHA || '');
const PERSON_ID = positiveId('PERSON_ID');
const PROJECT_ID = positiveId('PROJECT_ID');
const PASSWORD = String(process.env.E2E_PASSWORD || '');
const OUT = path.resolve(process.env.ARTIFACT_DIR || `artifacts/p4-personnel-authorization/${BATCH}`);
const NOTE = `P4 页面授权验收 ${BATCH}`;

function deny(message) { throw new Error(`[DENY] ${message}`); }
function check(value, message, details) {
  if (!value) throw new Error(`${message}${details === undefined ? '' : ` ${JSON.stringify(details)}`}`);
}
function positiveId(name) {
  const raw = String(process.env[name] || '');
  if (!/^[1-9][0-9]*$/.test(raw)) deny(`${name} must be an explicit positive integer`);
  const value = Number(raw);
  if (!Number.isSafeInteger(value)) deny(`${name} is outside the safe integer range`);
  return value;
}
function expectedXmlid(kind) {
  return `${NAMESPACE}.${kind}_${BATCH.replaceAll('-', '_')}`;
}
function validateStaticIdentity() {
  if (FRONTEND_URL !== EXPECTED_FRONTEND) deny(`FRONTEND_URL must be ${EXPECTED_FRONTEND}`);
  if (DB_NAME !== EXPECTED_DB || process.env.SC_ENVIRONMENT !== EXPECTED_ENV || process.env.ODOO_DBFILTER !== EXPECTED_DBFILTER) {
    deny('runner requires sc-local-dev / sc_dev_demo identity');
  }
  if (!BATCH_RE.test(BATCH)) deny('P4_PERSONNEL_AUTH_BATCH is invalid');
  if (!/^[0-9a-f]{40}$/.test(PRODUCT_SHA) || !/^[0-9a-f]{40}$/.test(TOOL_SHA)) deny('product and tool SHA must be full immutable SHAs');
  if (!PASSWORD) deny('governed operator credential is missing');
  const actual = spawnSync('git', ['-C', ROOT, 'rev-parse', 'HEAD'], { encoding: 'utf8' });
  if (actual.status !== 0 || String(actual.stdout).trim() !== TOOL_SHA) deny('tool SHA does not match the runner worktree');
  let served = '';
  try { served = String(JSON.parse(fs.readFileSync('/tmp/sc-local-dev-candidate-frontend.pid', 'utf8')).head || ''); }
  catch { deny('candidate frontend identity is unavailable'); }
  if (served !== PRODUCT_SHA) deny('served product SHA does not match PRODUCT_CANDIDATE_SHA');
}
function inspectAuthority() {
  const entry = path.join(ROOT, 'scripts/verify/local_dev_personnel_authorization_fixture.sh');
  const result = spawnSync('bash', [entry], {
    cwd: ROOT,
    encoding: 'utf8',
    maxBuffer: 4 * 1024 * 1024,
    env: {
      ...process.env,
      P4_PERSONNEL_AUTH_MODE: 'inspect',
      P4_PERSONNEL_AUTH_CONFIRM: 'INSPECT',
      CANDIDATE_GIT_HEAD: TOOL_SHA,
    },
  });
  if (result.error || result.status !== 0) deny(`governed authority read failed (exit=${result.status ?? 'spawn-error'})`);
  const prefix = 'LOCAL_DEV_PERSONNEL_AUTH_FIXTURE_JSON=';
  const rows = String(result.stdout || '').split(/\r?\n/).filter((line) => line.startsWith(prefix));
  if (rows.length !== 1) deny('governed authority read returned no unique result');
  let facts;
  try { facts = JSON.parse(rows[0].slice(prefix.length)); }
  catch { deny('governed authority result is invalid JSON'); }
  validateAuthority(facts);
  return facts;
}
function validateAuthority(facts) {
  if (facts.mode !== 'inspect' || facts.complete_batch !== true) deny('authority is not a complete batch inspect');
  if (facts.database !== EXPECTED_DB || facts.environment !== EXPECTED_ENV || facts.dbfilter !== EXPECTED_DBFILTER) deny('authority environment identity mismatch');
  if (facts.candidate_sha !== TOOL_SHA || facts.batch !== BATCH || facts.namespace !== NAMESPACE) deny('authority candidate or batch identity mismatch');
  if (Number(facts.person?.id) !== PERSON_ID || facts.person?.xmlid !== expectedXmlid('person')) deny('authority person identity mismatch');
  if (Number(facts.project?.id) !== PROJECT_ID || facts.project?.xmlid !== expectedXmlid('project')) deny('authority project identity mismatch');
  if (Number(facts.person?.company_id) !== Number(facts.project?.company_id)) deny('authority company scope mismatch');
  if (facts.person?.share !== false || facts.person?.managed !== true || (facts.person?.administrator_group_ids || []).length) deny('target person is not a non-privileged managed user');
  if (facts.operator?.login !== 'sc_test_admin' || Number(facts.operator?.company_id) !== Number(facts.person?.company_id)) deny('operator identity mismatch');
  if (facts.assignment?.id) {
    if (Number(facts.assignment.user_id) !== PERSON_ID || Number(facts.assignment.project_id) !== PROJECT_ID || Number(facts.assignment.company_id) !== Number(facts.person.company_id)) {
      deny('assignment escaped the owned person/project/company scope');
    }
  }
}
function responseBodyPromise(page, predicate, timeout = 30000) {
  return page.waitForResponse((response) => {
    if (!response.url().includes('/api/v1/intent')) return false;
    try { return predicate(JSON.parse(response.request().postData() || '{}')); }
    catch { return false; }
  }, { timeout });
}
async function successful(response, label) {
  const body = await response.json().catch(() => ({}));
  check(response.ok() && body?.ok === true, `${label} failed`, { http: response.status(), error: body?.error });
  return body;
}
async function login(page, authority) {
  await page.goto(`${FRONTEND_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const fields = page.locator('input');
  await fields.nth(0).fill(authority.operator.login);
  await fields.nth(1).fill(PASSWORD);
  if (await fields.nth(2).isEnabled().catch(() => false)) await fields.nth(2).fill(DB_NAME);
  const loginResponse = responseBodyPromise(page, (body) => body.intent === 'login');
  const initResponse = responseBodyPromise(page, (body) => body.intent === 'system.init');
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => url.pathname !== '/login', { timeout: 30000 });
  const loginBody = await successful(await loginResponse, 'login');
  const initBody = await successful(await initResponse, 'system.init');
  const user = initBody?.data?.user || {};
  check(Number(user.id) === Number(authority.operator.id), 'runtime operator user mismatch', user);
  check(Number(user.company_id) === Number(authority.operator.company_id), 'runtime operator company mismatch', user);
  return {
    login_ok: loginBody?.ok === true,
    user_id: Number(user.id),
    login: String(user.login || ''),
    company_id: Number(user.company_id),
  };
}
async function openOwnedForm(page, entry, personName) {
  await page.goto(`${FRONTEND_URL}/a/${entry.action_id}?menu_id=${entry.menu_id}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const list = page.locator('[data-product-page-mode="list"]:visible').first();
  await list.waitFor({ timeout: 45000 });
  await page.waitForFunction(() => {
    const surface = document.querySelector('[data-product-page-mode="list"]');
    return Boolean(surface) && !/正在载入数据|正在加载列表/.test(surface.textContent || '');
  }, null, { timeout: 45000 });
  const recordButton = page.getByRole('button', { name: personName, exact: true }).first();
  await recordButton.waitFor({ timeout: 30000 });
  await recordButton.click();
  await page.waitForURL((url) => url.pathname === `/f/res.users/${PERSON_ID}`, { timeout: 30000 });
  const form = page.locator(`[data-semantic-component="ContractFormPage"][data-form-record="${PERSON_ID}"]`).first();
  await form.waitFor({ timeout: 45000 });
  await form.locator('[data-field-name]').first().waitFor({ timeout: 30000 });
  return form;
}
function writeRecorder(page) {
  const writes = [];
  const pending = new Map();
  page.on('request', (request) => {
    if (request.method() !== 'POST' || !request.url().includes('/api/v1/intent')) return;
    let body;
    try { body = JSON.parse(request.postData() || '{}'); } catch { return; }
    if (body?.intent !== 'api.data' || body?.params?.op !== 'write' || body?.params?.model !== 'res.users' || Number(body?.params?.ids?.[0]) !== PERSON_ID) return;
    const vals = body.params?.vals && typeof body.params.vals === 'object' ? body.params.vals : {};
    const assignmentCommands = Array.isArray(vals.sc_project_member_assignment_ids)
      ? vals.sc_project_member_assignment_ids.map((command) => ({
        operation: Number(command?.[0]),
        record_id: Number(command?.[1]) || 0,
        field_names: command?.[2] && typeof command[2] === 'object' ? Object.keys(command[2]).sort() : [],
      }))
      : [];
    const entry = {
      at: new Date().toISOString(),
      request: {
        intent: body.intent,
        op: body.params.op,
        model: body.params.model,
        ids: body.params.ids,
        field_names: Object.keys(vals).sort(),
        assignment_commands: assignmentCommands,
      },
      outcome: 'pending',
    };
    writes.push(entry);
    pending.set(request, entry);
  });
  page.on('response', async (response) => {
    const entry = pending.get(response.request());
    if (!entry) return;
    const body = await response.json().catch(() => ({}));
    entry.response = { http_status: response.status(), business_ok: body?.ok === true, error: body?.error || null };
    entry.outcome = response.ok() && body?.ok === true ? 'business_success' : 'failure';
    pending.delete(response.request());
  });
  page.on('requestfailed', (request) => {
    const entry = pending.get(request);
    if (entry) { entry.outcome = 'network_failure'; entry.error = request.failure()?.errorText || 'unknown'; pending.delete(request); }
  });
  return writes;
}
async function waitWrite(writes, index) {
  const deadline = Date.now() + 30000;
  while (Date.now() < deadline) {
    if (writes[index] && writes[index].outcome !== 'pending') return writes[index];
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
  throw new Error(`write outcome timeout at index ${index}`);
}
async function save(page, writes, index) {
  const button = page.getByRole('button', { name: /^保存修改$/, exact: true }).first();
  await button.waitFor({ timeout: 15000 });
  await button.click();
  const write = await waitWrite(writes, index);
  check(write.outcome === 'business_success', 'browser write did not succeed', write);
  await page.getByText(/保存成功/).waitFor({ timeout: 20000 });
  await page.waitForFunction(() => !(document.body.innerText || '').includes('正在处理'), null, { timeout: 20000 });
  return write;
}
async function authorizationSurface(form) {
  const tab = form.getByText('授权维护（兼容入口）', { exact: true }).first();
  await tab.waitFor({ timeout: 15000 });
  await tab.click();
  const root = form.locator('[data-field-name="sc_project_member_assignment_ids"]').first();
  await root.waitFor({ timeout: 15000 });
  return root;
}
async function selectProject(page, root, projectName) {
  const editor = root.locator('[data-validation-target*="project_id"]:visible').first();
  await editor.waitFor({ timeout: 15000 });
  const input = editor.locator('input:visible').first();
  const enableDeadline = Date.now() + 20000;
  while (await input.isDisabled() && Date.now() < enableDeadline) await page.waitForTimeout(100);
  check(!(await input.isDisabled()), 'new assignment project selector is disabled', {
    editor: (await editor.evaluate((element) => element.outerHTML)).slice(0, 3000),
    visible_project_editors: await root.locator('[data-validation-target*="project_id"]:visible').count(),
  });
  await input.click();
  await input.fill(projectName);
  const option = page.locator('.t-select-option:visible, [role="option"]:visible').filter({ hasText: projectName }).first();
  await option.waitFor({ timeout: 20000 });
  await option.click();
  check((await input.inputValue()).includes(projectName), 'project selection did not persist in the control');
}
async function setNote(root, note) {
  const editor = root.locator('[data-validation-target*="note"]:visible').first();
  const input = editor.locator('input:visible, textarea:visible').first();
  await input.fill(note);
}
async function setSelection(page, root, columnName, optionLabel) {
  const editor = root.locator(`[data-validation-target*="${columnName}"]:visible`).first();
  const input = editor.locator('input:visible').first();
  await input.click();
  const option = page.locator('.t-select-option:visible, [role="option"]:visible').filter({ hasText: optionLabel }).first();
  await option.waitFor({ timeout: 15000 });
  await option.click();
  check((await input.inputValue()).includes(optionLabel), `${columnName} selection did not persist`);
}
async function setActive(root, desired) {
  const editor = root.locator('[data-validation-target*="active"]:visible').first();
  const checkbox = editor.locator('[data-semantic-component="ScCheckbox"]:visible').first();
  await checkbox.waitFor({ timeout: 15000 });
  const checked = (await checkbox.getAttribute('data-checked')) === 'true';
  if (checked !== desired) await checkbox.click();
}
async function existingProjectReadonly(root, projectName) {
  const editor = root.locator('[data-validation-target*="project_id"]:visible').first();
  const input = editor.locator('input:visible').first();
  await input.waitFor({ timeout: 15000 });
  return { value: await input.inputValue(), disabled: await input.isDisabled(), matches: (await input.inputValue()).includes(projectName) };
}
async function existingAssignmentState(root, projectName, expectedActive) {
  const project = await existingProjectReadonly(root, projectName);
  const editor = root.locator('[data-validation-target*="active"]:visible').first();
  const checkbox = editor.locator('[data-semantic-component="ScCheckbox"]:visible').first();
  await checkbox.waitFor({ timeout: 15000 });
  const active = (await checkbox.getAttribute('data-checked')) === 'true';
  return { ...project, active, expected_active: expectedActive, state_matches: active === expectedActive };
}
function diagnosticParams(request) {
  const params = request?.params && typeof request.params === 'object' ? request.params : {};
  return {
    op: String(params.op || ''),
    model: String(params.model || params.res_model || ''),
    ids: Array.isArray(params.ids) ? params.ids.map(Number) : [],
    action_id: Number(params.action_id || 0) || null,
    menu_id: Number(params.menu_id || 0) || null,
    record_id: Number(params.record_id || params.res_id || 0) || null,
  };
}

validateStaticIdentity();
const initial = inspectAuthority();
check(initial.person.active === true && initial.project.active === true, 'batch is not active before journey');
const resumeOwnedCreate = Boolean(initial.assignment.id);
const resumeInactive = resumeOwnedCreate && initial.assignment.active === false;
if (resumeOwnedCreate) {
  check(initial.assignment.source === 'manual' && initial.assignment.note === NOTE
    && initial.assignment.person_is_follower === !resumeInactive,
  'preserved assignment is not the exact successful create state', initial.assignment);
}
fs.mkdirSync(OUT, { recursive: true });
const report = {
  schema_version: 'local_dev_personnel_authorization_journey.v1',
  product_sha: PRODUCT_SHA,
  tool_sha: TOOL_SHA,
  database: DB_NAME,
  batch: BATCH,
  person_id: PERSON_ID,
  project_id: PROJECT_ID,
  initial,
  stages: [],
  writes: [],
  errors: [],
  http_failures: [],
  relation_contracts: [],
  pass: false,
};
const browser = await launchChromium({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
const page = await context.newPage();
page.on('pageerror', (error) => report.errors.push({ type: 'pageerror', message: String(error.message || error) }));
page.on('console', (message) => { if (message.type() === 'error' && !message.text().includes('favicon')) report.errors.push({ type: 'console', message: message.text().slice(0, 1000) }); });
page.on('response', async (response) => {
  if (!response.url().includes('/api/v1/intent')) return;
  let request = {};
  try { request = JSON.parse(response.request().postData() || '{}'); } catch { /* no request body */ }
  const params = diagnosticParams(request);
  const body = await response.json().catch(() => ({}));
  if (request?.intent === 'ui.contract.v2' && String(params?.model || params?.res_model || '') === 'sc.project.member.assignment') {
    const fields = body?.data?.fields || body?.data?.contract?.fields || {};
    report.relation_contracts.push({ status: response.status(), ok: body?.ok === true, params, project_id: fields?.project_id || null, field_names: Object.keys(fields) });
  }
  if (response.status() >= 400) report.http_failures.push({ status: response.status(), intent: request?.intent, params, error: body?.error || body?.message || null });
});
const writes = writeRecorder(page);
report.writes = writes;
try {
  report.runtime_identity = await login(page, initial);
  const form = await openOwnedForm(page, initial.entries.personnel, initial.person.name);
  let writeIndex = 0;
  let afterCreate = initial;
  if (!resumeOwnedCreate) {
    const root = await authorizationSurface(form);
    await root.getByRole('button', { name: /^添加项目成员授权$/ }).click();
    await selectProject(page, root, initial.project.name);
    await setSelection(page, root, 'source', '正式维护');
    await setActive(root, true);
    await setNote(root, NOTE);
    await save(page, writes, writeIndex++);
    afterCreate = inspectAuthority();
    check(afterCreate.assignment.id && afterCreate.assignment.active === true && afterCreate.assignment.note === NOTE, 'authoritative create readback mismatch', afterCreate.assignment);
    check(afterCreate.assignment.person_is_follower === true, 'active assignment did not establish the owned follower', afterCreate.assignment);
    await page.reload({ waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.locator(`[data-semantic-component="ContractFormPage"][data-form-record="${PERSON_ID}"]`).first().waitFor({ timeout: 45000 });
  }
  const readonlyAfterCreate = await existingProjectReadonly(await authorizationSurface(page.locator(`[data-semantic-component="ContractFormPage"][data-form-record="${PERSON_ID}"]`).first()), initial.project.name);
  check(readonlyAfterCreate.disabled && readonlyAfterCreate.matches, 'persisted assignment project remains editable or changed', readonlyAfterCreate);
  report.stages.push({ name: 'create_and_readback', status: 'PASS', evidence_source: resumeOwnedCreate ? 'preserved_owned_batch_authority' : 'current_browser_write', assignment: afterCreate.assignment, project_readonly: readonlyAfterCreate });
  await page.screenshot({ path: path.join(OUT, '01-created.png'), fullPage: true });

  const currentForm = page.locator(`[data-semantic-component="ContractFormPage"][data-form-record="${PERSON_ID}"]`).first();
  let afterDeactivate = initial;
  if (!resumeInactive) {
    const createdRoot = await authorizationSurface(currentForm);
    await setActive(createdRoot, false);
    await save(page, writes, writeIndex++);
    afterDeactivate = inspectAuthority();
    check(afterDeactivate.assignment.active === false && afterDeactivate.assignment.person_is_follower === false, 'authoritative deactivate readback mismatch', afterDeactivate.assignment);
  }
  report.stages.push({ name: 'deactivate_and_readback', status: 'PASS', evidence_source: resumeInactive ? 'preserved_owned_batch_authority' : 'current_browser_write', assignment: afterDeactivate.assignment });
  await page.screenshot({ path: path.join(OUT, '02-deactivated.png'), fullPage: true });

  const inactivePersonnel = await existingAssignmentState(await authorizationSurface(currentForm), initial.project.name, false);
  check(inactivePersonnel.matches && inactivePersonnel.disabled && inactivePersonnel.state_matches, 'personnel entry does not show the inactive immutable assignment', inactivePersonnel);
  report.stages.push({ name: 'inactive_visible_personnel', status: 'PASS', assignment: inactivePersonnel });

  const inactivePermissionForm = await openOwnedForm(page, initial.entries.data_permission, initial.person.name);
  const inactivePermissionRoot = inactivePermissionForm.locator('[data-field-name="sc_project_member_assignment_ids"]').first();
  await inactivePermissionRoot.waitFor({ timeout: 15000 });
  const inactivePermission = await existingAssignmentState(inactivePermissionRoot, initial.project.name, false);
  check(inactivePermission.matches && inactivePermission.disabled && inactivePermission.state_matches, 'data-permission entry does not show the inactive immutable assignment', inactivePermission);
  report.stages.push({ name: 'inactive_visible_data_permission', status: 'PASS', assignment: inactivePermission });
  await page.screenshot({ path: path.join(OUT, '02b-inactive-data-permission.png'), fullPage: true });

  const reactivationForm = await openOwnedForm(page, initial.entries.personnel, initial.person.name);
  const inactiveRoot = await authorizationSurface(reactivationForm);
  await setActive(inactiveRoot, true);
  await save(page, writes, writeIndex++);
  const afterReactivate = inspectAuthority();
  check(afterReactivate.assignment.active === true && afterReactivate.assignment.person_is_follower === true, 'authoritative reactivate readback mismatch', afterReactivate.assignment);
  report.stages.push({ name: 'reactivate_and_readback', status: 'PASS', assignment: afterReactivate.assignment });

  await page.reload({ waitUntil: 'domcontentloaded', timeout: 45000 });
  const refreshedForm = page.locator(`[data-semantic-component="ContractFormPage"][data-form-record="${PERSON_ID}"]`).first();
  await refreshedForm.waitFor({ timeout: 45000 });
  const refreshedReadonly = await existingProjectReadonly(await authorizationSurface(refreshedForm), initial.project.name);
  check(refreshedReadonly.disabled && refreshedReadonly.matches, 'refresh lost assignment identity or project immutability', refreshedReadonly);
  report.stages.push({ name: 'refresh_consistency', status: 'PASS', project_readonly: refreshedReadonly });
  await page.screenshot({ path: path.join(OUT, '03-reactivated-refreshed.png'), fullPage: true });

  const permissionForm = await openOwnedForm(page, initial.entries.data_permission, initial.person.name);
  const permissionRoot = permissionForm.locator('[data-field-name="sc_project_member_assignment_ids"]').first();
  await permissionRoot.waitFor({ timeout: 15000 });
  const sameFact = await existingProjectReadonly(permissionRoot, initial.project.name);
  check(sameFact.matches && sameFact.disabled, 'data-permission entry does not show the same immutable assignment fact', sameFact);
  report.stages.push({ name: 'second_entry_same_fact', status: 'PASS', project_readonly: sameFact });
  await page.screenshot({ path: path.join(OUT, '04-data-permission-same-fact.png'), fullPage: true });

  const finalPersonnelForm = await openOwnedForm(page, initial.entries.personnel, initial.person.name);
  const finalRoot = await authorizationSurface(finalPersonnelForm);
  await setActive(finalRoot, false);
  await save(page, writes, writeIndex++);
  const finalInactive = inspectAuthority();
  check(finalInactive.assignment.active === false && finalInactive.assignment.person_is_follower === false, 'final inactive authority or follower release mismatch', finalInactive.assignment);
  report.stages.push({ name: 'final_deactivate_and_preserve', status: 'PASS', assignment: finalInactive.assignment });
  await page.screenshot({ path: path.join(OUT, '05-final-inactive.png'), fullPage: true });

  const expectedWrites = resumeInactive ? 2 : resumeOwnedCreate ? 3 : 4;
  check(writes.length === expectedWrites && writes.every((item) => item.outcome === 'business_success'), 'unexpected browser write count or outcome', writes);
  check(report.errors.length === 0, 'browser reported console/page errors', report.errors);
  report.final_authority = finalInactive;
  report.pass = true;
} catch (error) {
  report.failure = String(error?.stack || error);
  await page.screenshot({ path: path.join(OUT, 'failure-scene.png'), fullPage: true }).catch(() => {});
  report.failure_authority = (() => { try { return inspectAuthority(); } catch (authorityError) { return { error: String(authorityError) }; } })();
  throw error;
} finally {
  fs.writeFileSync(path.join(OUT, 'summary.json'), `${JSON.stringify(report, null, 2)}\n`);
  await browser.close();
}
console.log(JSON.stringify({ pass: report.pass, batch: BATCH, person_id: PERSON_ID, project_id: PROJECT_ID, stages: report.stages.map((row) => row.name), writes: writes.length, artifact_dir: OUT }));
