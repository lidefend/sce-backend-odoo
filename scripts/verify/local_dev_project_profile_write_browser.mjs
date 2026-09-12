#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const requireBase = path.join(process.cwd(), 'frontend/apps/web/package.json');
const { chromium } = createRequire(requireBase)('playwright');

const FRONTEND_URL = process.env.FRONTEND_URL || 'http://127.0.0.1:5176';
const DB_NAME = process.env.DB_NAME || 'sc_dev_demo';
const PASSWORD = process.env.E2E_PASSWORD || process.env.SC_DEMO_USER_PASSWORD || '';
const PROJECT_ID = Number(process.env.PROJECT_ID || 366);
const PROJECT_NAME = process.env.PROJECT_NAME || '';
const ACTION_ID = Number(process.env.ACTION_ID || 861);
const MENU_ID = Number(process.env.MENU_ID || 681);
const PM_LOGIN = process.env.PM_LOGIN || 'demo_role_project_manager';
const MEMBER_LOGIN = process.env.MEMBER_LOGIN || 'demo_role_project_a_member';
const READ_LOGIN = process.env.READ_LOGIN || 'demo_role_project_read';
const READ_ONLY = process.env.READ_ONLY === '1';
const PREFLIGHT_ONLY = process.env.PREFLIGHT_ONLY === '1';
const PREFLIGHT_LOGIN = process.env.PREFLIGHT_LOGIN || '';
const ROUTE_PATH = process.env.ROUTE_PATH || `/r/project.project/${PROJECT_ID}?menu_id=${MENU_ID}&action_id=${ACTION_ID}`;
const OUT = path.resolve(process.env.ARTIFACT_DIR || `artifacts/p4-project-profile-write/${Date.now()}`);
const originalName = `Codex P4 项目资料写入验收 profile-save-20260911`;

if (!PASSWORD) throw new Error('E2E_PASSWORD or SC_DEMO_USER_PASSWORD is required');
fs.mkdirSync(OUT, { recursive: true });

function normalize(value) { return String(value ?? '').replace(/\s+/g, ' ').trim(); }
function recordWriteRequests(page) {
  const writes = [];
  page.on('request', (request) => {
    if (request.method() !== 'POST' || !request.url().includes('/api/v1/intent')) return;
    let body = {};
    try { body = JSON.parse(request.postData() || '{}'); } catch { return; }
    if (body?.intent === 'api.data' && body?.params?.op === 'write') writes.push({ body, at: Date.now() });
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
    if (message.type() === 'error' || message.type() === 'warning') requests.push({ type: 'console', level: message.type(), text: message.text().slice(0, 1000) });
  });
  page.on('requestfailed', (request) => requests.push({ type: 'requestfailed', url: request.url(), failure: request.failure()?.errorText || 'unknown' }));
  return requests;
}
async function login(page, login) {
  await page.goto(`${FRONTEND_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const inputs = page.locator('input');
  await inputs.nth(0).fill(login);
  await inputs.nth(1).fill(PASSWORD);
  if (await inputs.nth(2).isEnabled().catch(() => false)) await inputs.nth(2).fill(DB_NAME);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 30000 });
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
    fields: ['id', 'name', 'date_start', 'date', 'description', 'lifecycle_state', 'responsibility_ids'], context: {},
  });
  return result.data.records?.[0] || null;
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
  await page.getByText(/保存成功/).waitFor({ timeout: 20000 });
}
async function dirty(page) { return /未保存|已修改\s*\d+\s*项/.test(normalize(await page.locator('.record-header-context:visible').innerText().catch(() => ''))); }
async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, locale: 'zh-CN' });
  const diagnostics = recordDiagnostics(page);
  const report = { database: DB_NAME, project_id: PROJECT_ID, action_id: ACTION_ID, menu_id: MENU_ID, read_only: READ_ONLY, scenarios: [], roles: {}, writes: [], diagnostics, errors: [] };
  try {
    const loginName = PREFLIGHT_LOGIN || (READ_ONLY ? READ_LOGIN : PM_LOGIN);
    await login(page, loginName);
    report.session_login = loginName;
    const pageState = await openProject(page);
    const before = await readProject(page);
    if (!before || before.id !== PROJECT_ID) throw new Error('project 366 authoritative read failed');
    report.preflight = { page_state: pageState, authoritative_read: { id: before.id, lifecycle_state: before.lifecycle_state, responsibility_ids: before.responsibility_ids } };
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
    const rowInputs = createdRow.locator('input');
    if (await rowInputs.count()) await rowInputs.last().fill('P4 责任新增');
    if (!await dirty(page)) throw new Error('draft did not become dirty');
    const writes = recordWriteRequests(page);
    await save(page);
    await page.waitForTimeout(400);
    const after = await readProject(page);
    report.writes = writes;
    report.scenarios.push({ name: 'normal_save', status: after?.name === marker && after?.date_start === '2026-09-15' && after?.date === '2026-10-15' && writes.length === 1 ? 'PASS' : 'FAIL', before, after, write_count: writes.length, responsibility_rows_before: initialRows });
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.locator('.template-layout-shell').waitFor({ timeout: 30000 });
    const refreshed = await readProject(page);
    report.scenarios.push({ name: 'authoritative_refresh', status: refreshed?.name === marker && refreshed?.date_start === '2026-09-15' && refreshed?.date === '2026-10-15' ? 'PASS' : 'FAIL', refreshed });
    await page.screenshot({ path: path.join(OUT, 'normal-save.png'), fullPage: true });
  } catch (error) {
    report.failure_context = await page.evaluate(() => ({ url: location.href, title: document.title, text: (document.body.innerText || '').slice(0, 1200), fields: [...document.querySelectorAll('[data-field-name]')].map((el) => el.getAttribute('data-field-name')).slice(0, 80) })).catch(() => ({ url: page.url() }));
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
