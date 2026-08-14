#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';

const BASE_URL = process.env.FRONTEND_URL || 'http://127.0.0.1:5193';
const DB_NAME = process.env.DB_NAME || '';
const PASSWORD = process.env.SC_ACCEPTANCE_PFL035_PASSWORD || '';
const SOURCE_SHA = process.env.SOURCE_SHA || '';
const DIRTY_DIFF_SHA256 = process.env.DIRTY_DIFF_SHA256 || '';
const ACTION_ID = Number(process.env.ACTION_ID || 0);
const MENU_ID = Number(process.env.MENU_ID || 0);
const IDS = {
  approved: Number(process.env.APPROVED_REQUEST_ID || 0),
  draft: Number(process.env.DRAFT_REQUEST_ID || 0),
  receive: Number(process.env.RECEIVE_REQUEST_ID || 0),
  incomplete: Number(process.env.INCOMPLETE_REQUEST_ID || 0),
};
const LOGINS = {
  manager: process.env.FINANCE_MANAGER_LOGIN || '',
  user: process.env.FINANCE_USER_LOGIN || '',
  empty: process.env.EMPTY_FINANCE_LOGIN || '',
  forbidden: process.env.FORBIDDEN_LOGIN || '',
};
const COMPANY = process.env.COMPANY_NAME || '';
const OUTPUT_DIR = process.env.ARTIFACTS_DIR || 'artifacts/playwright/pfl035-payment-request-runtime/latest';

for (const [name, value] of Object.entries({ DB_NAME, PASSWORD, SOURCE_SHA, ACTION_ID, MENU_ID, COMPANY, ...IDS, ...LOGINS })) {
  if (!value) throw new Error(`missing required acceptance input: ${name}`);
}
fs.mkdirSync(OUTPUT_DIR, { recursive: true });

const result = {
  schema: 'pfl035.payment_request.runtime_acceptance.v1',
  pass: false,
  generated_at: new Date().toISOString(),
  source: { head_sha: SOURCE_SHA, dirty_diff_sha256: DIRTY_DIFF_SHA256 },
  runtime: {
    database: DB_NAME,
    frontend_url: BASE_URL,
    company: COMPANY,
    action: { xmlid: 'smart_construction_core.action_payment_request_user_payment_apply', id: ACTION_ID },
    menu: { xmlid: 'smart_construction_core.menu_sc_user_payment_apply_acceptance', id: MENU_ID },
  },
  roles: LOGINS,
  records: IDS,
  states: [],
  business_paths: [],
  screenshots: [],
  console_errors: [],
  failed_requests: [],
  unexpected_failed_requests: [],
  assertions: [],
  environment_noise: [
    'Odoo mail installation emitted docutils formatting warnings: unexpected indentation / block quote blank-line / title underline length.',
    'Node emitted DEP0169 for url.parse() while restoring the lockfile-pinned offline dependencies.',
  ],
};

function check(condition, assertion, facts = {}) {
  result.assertions.push({ assertion, pass: Boolean(condition), ...facts });
  if (!condition) throw new Error(assertion);
}

function clean(value) {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

function attachDiagnostics(page, role) {
  page.on('console', (message) => {
    if (message.type() !== 'error') return;
    const text = message.text();
    if (/favicon|ResizeObserver/i.test(text)) return;
    result.console_errors.push({ role, url: page.url(), text });
  });
  page.on('pageerror', (error) => {
    result.console_errors.push({ role, url: page.url(), text: error.message });
  });
  page.on('response', async (response) => {
    if (response.status() < 400) return;
    const request = response.request();
    let payload = {};
    try { payload = JSON.parse(request.postData() || '{}'); } catch {}
    const recordId = Number(payload?.params?.res_id || payload?.params?.record_id || 0);
    const expected = payload?.intent === 'execute_button'
      && [IDS.draft, IDS.receive, IDS.incomplete, IDS.approved].includes(recordId);
    const row = {
      role,
      status: response.status(),
      url: response.url(),
      method: request.method(),
      intent: String(payload?.intent || ''),
      record_id: recordId || null,
      expected,
    };
    result.failed_requests.push(row);
    if (!expected) result.unexpected_failed_requests.push(row);
  });
}

async function login(page, loginName, role) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const inputs = page.locator('input');
  await inputs.nth(0).fill(loginName);
  await inputs.nth(1).fill(PASSWORD);
  if (await inputs.nth(2).isEnabled()) {
    await inputs.nth(2).fill(DB_NAME);
  } else {
    check(await inputs.nth(2).inputValue() === DB_NAME, `${role}: locked database must equal acceptance database`);
  }
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45000 });
  await page.locator('.layout-shell').waitFor({ timeout: 45000 });
}

async function intent(page, intentName, params, traceSuffix = '') {
  const token = await page.evaluate((database) => sessionStorage.getItem(`sc_auth_token:${database}`) || '', DB_NAME);
  return page.evaluate(async ({ database, bearer, intentName: name, payload, traceSuffix: suffix }) => {
    const response = await fetch(`/api/v1/intent?db=${encodeURIComponent(database)}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: bearer ? `Bearer ${bearer}` : '',
        'X-Trace-Id': `pfl035-${suffix || name}-${Date.now()}`,
      },
      body: JSON.stringify({ intent: name, params: payload }),
    });
    const body = await response.json().catch(() => ({}));
    return { status: response.status, body, data: body?.data || body?.result || {} };
  }, { database: DB_NAME, bearer: token, intentName, payload: params, traceSuffix });
}

async function waitForStablePage(page, mode) {
  await page.locator('.layout-shell').waitFor({ timeout: 45000 });
  if (mode) await page.locator(`[data-product-page-mode="${mode}"]`).first().waitFor({ timeout: 45000 });
  await page.waitForFunction(() => !/正在加载列表|正在加载页面|正在加载记录|正在载入数据|加载中/.test(document.body?.innerText || ''), null, { timeout: 45000 });
  await page.waitForTimeout(400);
}

async function surface(page) {
  return page.evaluate(() => {
    const text = (node) => String(node?.textContent || '').replace(/\s+/g, ' ').trim();
    const root = document.documentElement;
    const selectedCompanies = [
      ...[...document.querySelectorAll('label.business-scope-field select')]
        .map((select) => select.selectedOptions?.[0]?.textContent?.trim() || ''),
      ...[...document.querySelectorAll('.topbar-scope-label')]
        .map((node) => node.textContent?.trim() || ''),
    ].filter(Boolean);
    return {
      url: window.location.href,
      viewport: { width: window.innerWidth, height: window.innerHeight },
      document_width: { client: root.clientWidth, scroll: root.scrollWidth, overflow: Math.max(0, root.scrollWidth - root.clientWidth) },
      product_modes: [...document.querySelectorAll('[data-product-page-mode]')].map((node) => node.getAttribute('data-product-page-mode')),
      headings: [...document.querySelectorAll('h1,h2,h3')].map(text).filter(Boolean).slice(0, 20),
      buttons: [...document.querySelectorAll('button')].filter((node) => node.offsetParent !== null).map(text).filter(Boolean).slice(0, 60),
      selected_companies: selectedCompanies,
      shell_context: text(document.querySelector('.sidebar .brand .subtitle')),
      body_sample: text(document.body).slice(0, 2000),
      table_rows: document.querySelectorAll('tbody tr').length,
      form_inputs: document.querySelectorAll('input:not([type="hidden"]), textarea, select').length,
    };
  });
}

async function shot(page, name) {
  const target = path.join(OUTPUT_DIR, `${name}.png`);
  await page.screenshot({ path: target, fullPage: true });
  result.screenshots.push({ name, path: target, url: page.url(), viewport: page.viewportSize() });
}

async function captureState(page, spec) {
  await page.goto(`${BASE_URL}${spec.route}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  if (spec.mode) await waitForStablePage(page, spec.mode);
  else await page.waitForTimeout(1000);
  const facts = await surface(page);
  await shot(page, spec.name);
  result.states.push({ name: spec.name, role: spec.role, expected_route: spec.route, ...facts });
  check(facts.document_width.overflow === 0, `${spec.name}: horizontal overflow must be zero`, facts.document_width);
  const actualPath = new URL(facts.url).pathname;
  const expectedPaths = Array.isArray(spec.expectedPath) ? spec.expectedPath : [spec.expectedPath];
  check(expectedPaths.includes(actualPath) || (spec.allowDenied && /access-denied/.test(actualPath)), `${spec.name}: fixed route mismatch`, { url: facts.url, expected_paths: expectedPaths });
  if (!spec.allowDenied) check(
    facts.selected_companies.includes(COMPANY) || facts.shell_context.includes(COMPANY),
    `${spec.name}: fixed company mismatch`,
    { selected: facts.selected_companies, shell_context: facts.shell_context },
  );
  return facts;
}

async function rejectPath(page, role, recordId, name, messagePattern) {
  const route = `/r/payment.request/${recordId}?action_id=${ACTION_ID}&menu_id=${MENU_ID}`;
  await page.goto(`${BASE_URL}${route}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await waitForStablePage(page, 'form');
  await shot(page, `reject-${name}`);
  const response = await intent(page, 'execute_button', {
    model: 'payment.request',
    res_id: recordId,
    button: { name: 'action_create_payment_execution', type: 'object' },
  }, `reject-${name}`);
  const message = clean(response.body?.error?.message || response.body?.message || response.data?.message);
  const pass = response.status >= 400 && messagePattern.test(message);
  result.business_paths.push({ name, role, record_id: recordId, expected: 'rejected', status: response.status, message, pass });
  check(pass, `${name}: authoritative rejection mismatch`, { status: response.status, message });
}

const browser = await launchChromium({ headless: true });
try {
  const managerContext = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
  const manager = await managerContext.newPage();
  attachDiagnostics(manager, 'finance_manager');
  await login(manager, LOGINS.manager, 'finance_manager');

  const init = await intent(manager, 'system.init', {}, 'identity');
  const initData = init.data || {};
  check(init.status === 200, 'system.init must succeed', { status: init.status });
  check(String(initData.source_revision || initData.git_sha || '') === SOURCE_SHA, 'served source revision must equal topic HEAD', { served: initData.source_revision || initData.git_sha });

  const listFacts = await captureState(manager, {
    name: 'list', role: 'finance_manager', route: `/m/${MENU_ID}?action_id=${ACTION_ID}`, expectedPath: [`/a/${ACTION_ID}`, `/m/${MENU_ID}`], mode: 'list',
  });
  check(
    listFacts.body_sample.includes('支付申请') || listFacts.body_sample.includes('付款申请'),
    'list: payment request identity missing',
  );
  check(listFacts.table_rows >= 1, 'list: expected business rows missing', { rows: listFacts.table_rows });

  const readonlyFacts = await captureState(manager, {
    name: 'readonly-detail', role: 'finance_manager', route: `/r/payment.request/${IDS.approved}?action_id=${ACTION_ID}&menu_id=${MENU_ID}`, expectedPath: `/r/payment.request/${IDS.approved}`, mode: 'form',
  });
  check(readonlyFacts.body_sample.includes('已批准'), 'readonly detail: approved state missing');

  await rejectPath(manager, 'finance_manager', IDS.draft, 'draft', /已批准状态/);
  await rejectPath(manager, 'finance_manager', IDS.receive, 'receive-request', /只有付款申请/);
  await rejectPath(manager, 'finance_manager', IDS.incomplete, 'incomplete-account', /户名.*开户行.*账号.*完整/);

  await manager.goto(`${BASE_URL}/r/payment.request/${IDS.approved}?action_id=${ACTION_ID}&menu_id=${MENU_ID}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await waitForStablePage(manager, 'form');
  const moreActions = manager.getByText('更多操作', { exact: true }).first();
  if (await moreActions.isVisible()) await moreActions.click();
  const generateButton = manager.getByRole('button', { name: '生成付款登记', exact: true }).first();
  await generateButton.waitFor({ state: 'visible', timeout: 30000 });
  await shot(manager, 'positive-approved-ready');
  await generateButton.click();
  await manager.waitForURL((url) => url.pathname !== `/r/payment.request/${IDS.approved}`, { timeout: 45000 });
  await waitForStablePage(manager, 'form');
  const executionCreateFacts = await surface(manager);
  const executionCreatePath = new URL(manager.url()).pathname;
  check(
    executionCreatePath === '/f/sc.payment.execution/new' || /^\/a\/\d+$/.test(executionCreatePath),
    'positive: authoritative execution entry target did not open',
    { url: manager.url() },
  );
  check(executionCreateFacts.body_sample.includes('付款'), 'positive: execution create form did not open');
  await shot(manager, 'positive-execution-create');
  await manager.getByRole('button', { name: /^保存$/ }).first().click();
  await manager.waitForURL((url) => /^\/[rf]\/sc\.payment\.execution\/\d+$/.test(url.pathname), { timeout: 45000 });
  await waitForStablePage(manager, 'form');
  await shot(manager, 'positive-execution-saved');
  const createdExecutionId = Number(new URL(manager.url()).pathname.split('/').pop());
  const executionList = await intent(manager, 'api.data', {
    op: 'list', model: 'sc.payment.execution', fields: ['id', 'payment_request_id', 'project_id', 'partner_id', 'contract_id', 'state'],
    domain: [['payment_request_id', '=', IDS.approved]], limit: 10,
  }, 'positive-verify');
  const executionRows = executionList.data?.records || [];
  const positivePass = executionList.status === 200 && executionRows.some((row) => Number(row.id) === createdExecutionId);
  result.business_paths.push({ name: 'approved-complete-generate-execution', role: 'finance_manager', record_id: IDS.approved, execution_id: createdExecutionId, status: executionList.status, rows: executionRows, pass: positivePass });
  check(positivePass, 'positive: saved execution must trace to approved request');

  await managerContext.close();

  const userContext = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
  const user = await userContext.newPage();
  attachDiagnostics(user, 'finance_user');
  await login(user, LOGINS.user, 'finance_user');
  const editFacts = await captureState(user, {
    name: 'create-edit', role: 'finance_user', route: `/f/payment.request/${IDS.draft}?action_id=${ACTION_ID}&menu_id=${MENU_ID}`, expectedPath: `/f/payment.request/${IDS.draft}`, mode: 'form',
  });
  check(editFacts.form_inputs > 0 && editFacts.body_sample.includes('编辑'), 'create/edit: editable form not exposed', { inputs: editFacts.form_inputs });
  await rejectPath(user, 'finance_user', IDS.approved, 'non-finance-manager', /没有生成付款登记.*权限/);
  await userContext.close();

  const emptyContext = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
  const empty = await emptyContext.newPage();
  attachDiagnostics(empty, 'empty_finance');
  await login(empty, LOGINS.empty, 'empty_finance');
  const emptyFacts = await captureState(empty, {
    name: 'empty', role: 'empty_finance', route: `/m/${MENU_ID}?action_id=${ACTION_ID}`, expectedPath: [`/a/${ACTION_ID}`, `/m/${MENU_ID}`], mode: 'list',
  });
  check(emptyFacts.table_rows === 0 && /暂无|没有.*数据|空/.test(emptyFacts.body_sample), 'empty: expected an explicit empty list state', { rows: emptyFacts.table_rows, sample: emptyFacts.body_sample });
  await emptyContext.close();

  const forbiddenContext = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
  const forbidden = await forbiddenContext.newPage();
  attachDiagnostics(forbidden, 'forbidden_user');
  await login(forbidden, LOGINS.forbidden, 'forbidden_user');
  const forbiddenFacts = await captureState(forbidden, {
    name: 'forbidden', role: 'forbidden_user', route: `/m/${MENU_ID}?action_id=${ACTION_ID}`, expectedPath: `/m/${MENU_ID}`, allowDenied: true,
  });
  check(/无权访问|没有权限|未授权/.test(forbiddenFacts.body_sample), 'forbidden: explicit permission state missing', { sample: forbiddenFacts.body_sample });
  await forbiddenContext.close();

  const mobileContext = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: 'zh-CN', isMobile: true });
  const mobile = await mobileContext.newPage();
  attachDiagnostics(mobile, 'finance_manager_mobile');
  await login(mobile, LOGINS.manager, 'finance_manager_mobile');
  const mobileFacts = await captureState(mobile, {
    name: '390px-mobile', role: 'finance_manager', route: `/r/payment.request/${IDS.approved}?action_id=${ACTION_ID}&menu_id=${MENU_ID}`, expectedPath: `/r/payment.request/${IDS.approved}`, mode: 'form',
  });
  check(mobileFacts.viewport.width === 390, 'mobile: viewport width must be 390', mobileFacts.viewport);
  await mobileContext.close();

  check(result.console_errors.length === 0, 'console business errors must be zero', { errors: result.console_errors });
  check(result.unexpected_failed_requests.length === 0, 'unexpected failed requests must be zero', { failures: result.unexpected_failed_requests });
  check(result.states.every((state) => state.document_width.overflow === 0), 'all states must have zero horizontal overflow');
  result.pass = true;
} catch (error) {
  result.error = error instanceof Error ? error.stack || error.message : String(error);
  throw error;
} finally {
  result.completed_at = new Date().toISOString();
  fs.writeFileSync(path.join(OUTPUT_DIR, 'acceptance.json'), JSON.stringify(result, null, 2));
  fs.writeFileSync(path.join(OUTPUT_DIR, 'acceptance.md'), [
    '# PFL-035 runtime acceptance',
    '',
    `- Result: ${result.pass ? 'PASS' : 'FAIL'}`,
    `- Source HEAD: ${SOURCE_SHA}`,
    `- Dirty diff SHA-256: ${DIRTY_DIFF_SHA256}`,
    `- Database: ${DB_NAME}`,
    `- Company: ${COMPANY}`,
    `- Fixed route: /m/${MENU_ID}?action_id=${ACTION_ID}`,
    `- States: ${result.states.map((row) => row.name).join(', ')}`,
    `- Business paths: ${result.business_paths.map((row) => `${row.name}:${row.pass ? 'PASS' : 'FAIL'}`).join(', ')}`,
    `- Console business errors: ${result.console_errors.length}`,
    `- Unexpected failed requests: ${result.unexpected_failed_requests.length}`,
    `- Environment noise: ${result.environment_noise.join(' | ')}`,
    '',
  ].join('\n'));
  await browser.close();
}

console.log(JSON.stringify({ pass: result.pass, artifacts: OUTPUT_DIR, states: result.states.length, business_paths: result.business_paths.length, console_errors: result.console_errors.length, unexpected_failed_requests: result.unexpected_failed_requests.length }));
