import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';

const target = JSON.parse(process.env.FRONTEND_QUALITY_SAFETY_DOMAIN_TARGET || '{}');
const frontendUrl = process.env.FRONTEND_URL || '';
const database = process.env.DB_NAME || '';
const password = process.env.E2E_PASSWORD || '';
const outputDir = path.resolve('artifacts/playwright/phase10-quality-safety-domain');

function check(value, message, details) {
  if (!value) throw new Error(`${message}${details === undefined ? '' : ` ${JSON.stringify(details)}`}`);
}

function findKey(value, key) {
  if (!value || typeof value !== 'object') return undefined;
  if (Object.prototype.hasOwnProperty.call(value, key)) return value[key];
  for (const child of Object.values(value)) {
    const found = findKey(child, key);
    if (found !== undefined) return found;
  }
  return undefined;
}

async function login(page, loginName) {
  await page.goto(`${frontendUrl}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const inputs = page.locator('input');
  await inputs.nth(0).fill(loginName);
  await inputs.nth(1).fill(password);
  if (await inputs.nth(2).count() && !(await inputs.nth(2).isDisabled())) await inputs.nth(2).fill(database);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 30000 });
  await page.locator('[data-semantic-component="ProductAppShell"]:visible').first().waitFor({ timeout: 45000 });
}

function observe(page, evidence) {
  page.on('console', (message) => {
    if (message.type() === 'error' && !message.text().includes('favicon')) evidence.errors.push(message.text());
  });
  page.on('pageerror', (error) => evidence.errors.push(error.message));
  page.on('response', (response) => {
    if (response.status() >= 400) evidence.errors.push(`http ${response.status()} ${response.url()}`);
  });
  page.on('request', (request) => {
    if (request.method() !== 'POST') return;
    let body = {};
    try { body = JSON.parse(request.postData() || '{}'); } catch {}
    const intent = String(body?.intent || '');
    const method = String(body?.params?.method || body?.method || '');
    if (/(^|\.)(create|write|unlink|execute_button|upload)(\.|$)/.test(intent)
      || /^(create|write|unlink|web_save|action_)/.test(method)) {
      evidence.mutations.push({ intent, method, url: request.url() });
    }
  });
  page.on('response', async (response) => {
    if (!response.url().includes('/api/v1/intent')) return;
    let requestBody = {};
    try { requestBody = JSON.parse(response.request().postData() || '{}'); } catch {}
    if (requestBody?.intent === 'ui.contract.v2') {
      try { evidence.contracts.push(await response.json()); } catch {}
    }
  });
}

check(frontendUrl && database && password, 'quality-safety browser identity is incomplete');
check(target?.user?.login && target?.security_user?.login, 'quality-safety users are missing', target);
check(Number(target?.action?.id) > 0 && Number(target?.menu?.id) > 0, 'quality-safety entry is missing', target);
check(Number(target?.record?.id) > 0, 'quality-safety record is missing', target);
fs.mkdirSync(outputDir, { recursive: true });

const browser = await launchChromium({ headless: true });
const report = {
  schemaVersion: 'frontend_quality_safety_domain_browser.v1',
  head: process.env.CANDIDATE_HEAD || '',
  target: { user: target.user, securityUser: target.security_user, action: target.action, menu: target.menu, record: target.record },
  primary: { errors: [], mutations: [], contracts: [] },
  security: { errors: [], mutations: [], contracts: [] },
  pass: false,
};

try {
  const primaryContext = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
  const page = await primaryContext.newPage();
  observe(page, report.primary);
  await login(page, target.user.login);
  const actionId = Number(target.action.id);
  const menuId = Number(target.menu.id);
  const recordId = Number(target.record.id);
  await page.goto(`${frontendUrl}/a/${actionId}?menu_id=${menuId}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const list = page.locator('[data-product-page-mode="list"]:visible').first();
  await list.waitFor({ timeout: 45000 });
  const row = list.locator('tbody tr').filter({ hasText: String(target.record.name || '') }).first();
  await row.waitFor({ timeout: 45000 });
  const navigationSequence = [];
  page.on('framenavigated', (frame) => {
    if (frame === page.mainFrame()) navigationSequence.push(frame.url());
  });
  await row.click();
  await page.waitForURL((url) => (
    url.pathname === `/f/sc.safety.issue/${recordId}`
      && url.searchParams.get('action_id') === String(actionId)
      && url.searchParams.get('menu_id') === String(menuId)
  ), { timeout: 45000 });
  const form = page.locator('[data-product-page-mode="form"]:visible').first();
  await form.locator('.product-form-loading').waitFor({ state: 'detached', timeout: 45000 });
  const driverCount = await form.locator('[data-contract-form-driver]:visible').count();
  const driverErrors = await form.locator('[data-contract-form-driver-error]:visible').allTextContents();
  const renderError = await form.getAttribute('data-v2-shadow-error');
  check(driverCount === 1, 'quality-safety form driver is not ready', {
    driverCount,
    driverErrors,
    renderError,
    text: (await form.innerText()).slice(0, 2000),
  });
  const listContract = report.primary.contracts.filter((body) => findKey(body, 'viewType') === 'list').at(-1);
  const formContract = report.primary.contracts.filter((body) => findKey(body, 'viewType') === 'form').at(-1);
  const editableFields = await form.locator(
    '[data-field-state]:not([data-field-state="readonly"]) input:not([type="hidden"]):not(:disabled), '
      + '[data-field-state]:not([data-field-state="readonly"]) textarea:not(:disabled), '
      + '[data-field-state]:not([data-field-state="readonly"]) select:not(:disabled)',
  ).count();
  const saveActions = await page.locator('[data-action-ref="form.save"][data-action-enabled="true"]:visible').count();
  const editTransitions = await form.locator('[data-form-mode-action="edit"]:visible').count();
  const businessNavigationSequence = navigationSequence.filter((value) => {
    const pathname = new URL(value).pathname;
    return pathname.startsWith('/r/sc.safety.issue/') || pathname.startsWith('/f/sc.safety.issue/');
  });
  report.primary.result = {
    firstUrl: page.url(), businessNavigationSequence,
    modelRights: findKey(listContract, 'modelRights'),
    effectiveRecordCapabilities: findKey(formContract, 'effectiveRecordCapabilities'),
    effectiveRenderProfile: findKey(formContract, 'effectiveRenderProfile'),
    presentationMode: findKey(formContract, 'presentationMode'),
    editableFields, saveActions, editTransitions,
    h1: await form.locator('h1:visible').count(),
    headers: await form.locator('[data-product-page-header]:visible').count(),
  };
  check(listContract && formContract, 'quality-safety list/form contract pair was not observed');
  check(findKey(listContract, 'modelRights')?.write === true, 'quality-safety list write authority is not true', report.primary.result);
  check(findKey(formContract, 'effectiveRecordCapabilities')?.write === true, 'quality-safety record write authority is not true', report.primary.result);
  check(findKey(formContract, 'effectiveRenderProfile') === 'edit', 'quality-safety record did not resolve edit', report.primary.result);
  check(findKey(formContract, 'presentationMode') === 'task', 'quality-safety record did not resolve task presentation', report.primary.result);
  check(businessNavigationSequence.length > 0 && new URL(businessNavigationSequence[0]).pathname === `/f/sc.safety.issue/${recordId}`,
    'quality-safety entry did not use /f as its first business route', report.primary.result);
  check(!businessNavigationSequence.some((value) => new URL(value).pathname.startsWith('/r/sc.safety.issue/')),
    'quality-safety entry passed through readonly', report.primary.result);
  check(editableFields > 0 && saveActions === 1 && editTransitions === 0,
    'quality-safety edit surface is incomplete', report.primary.result);
  check(report.primary.result.h1 === 1 && report.primary.result.headers === 1,
    'quality-safety page identity is not unique', report.primary.result);
  check(report.primary.errors.length === 0 && report.primary.mutations.length === 0,
    'quality-safety primary journey is not read-only clean', report.primary);
  await page.screenshot({ path: path.join(outputDir, 'safety-issue-direct-edit.png'), fullPage: true });
  await primaryContext.close();

  const securityContext = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
  const securityPage = await securityContext.newPage();
  observe(securityPage, report.security);
  await login(securityPage, target.security_user.login);
  await securityPage.goto(`${frontendUrl}/a/${actionId}?menu_id=${menuId}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await securityPage.waitForURL((url) => url.pathname === '/access-denied', { timeout: 45000 });
  const denial = securityPage.locator('[data-semantic-component="ScErrorState"][role="alert"]:visible').first();
  await denial.waitFor({ timeout: 45000 });
  report.security.result = {
    url: securityPage.url(),
    denialVisible: (await denial.innerText()).includes('访问受限'),
    businessForms: await securityPage.locator('[data-product-page-mode="form"]').count(),
    saveActions: await securityPage.locator('[data-action-ref="form.save"]').count(),
  };
  check(report.security.result.denialVisible, 'unauthorized quality-safety entry did not fail closed', report.security.result);
  check(report.security.result.businessForms === 0 && report.security.result.saveActions === 0,
    'unauthorized quality-safety entry exposed business controls', report.security.result);
  check(report.security.errors.length === 0 && report.security.mutations.length === 0,
    'quality-safety security journey is not clean', report.security);
  await securityPage.screenshot({ path: path.join(outputDir, 'safety-entry-finance-role-denied.png'), fullPage: true });
  await securityContext.close();
  report.pass = true;
} finally {
  fs.writeFileSync(path.join(outputDir, 'summary.json'), `${JSON.stringify(report, null, 2)}\n`);
  await browser.close();
}

console.log(JSON.stringify({ pass: report.pass, primary: report.primary.result, security: report.security.result }));
