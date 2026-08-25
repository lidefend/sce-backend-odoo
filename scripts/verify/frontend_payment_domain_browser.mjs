import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';

const target = JSON.parse(process.env.FRONTEND_PAYMENT_DOMAIN_TARGET || '{}');
const frontendUrl = process.env.FRONTEND_URL || '';
const database = process.env.DB_NAME || '';
const password = process.env.E2E_PASSWORD || '';
const outputDir = path.resolve('artifacts/playwright/phase10-payment-domain');

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
}

function observe(page, evidence) {
  page.on('console', (message) => {
    if (message.type() === 'error' && !message.text().includes('favicon')) evidence.errors.push(message.text());
  });
  page.on('pageerror', (error) => evidence.errors.push(error.message));
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
    if (requestBody?.intent !== 'ui.contract.v2') return;
    try { evidence.contracts.push(await response.json()); } catch {}
  });
}

check(frontendUrl && database && password, 'payment domain browser identity is incomplete');
check(target?.user?.login && target?.security_user?.login, 'payment domain users are missing', target);
check(Number(target?.action?.id) > 0 && Number(target?.menu?.id) > 0, 'payment domain entry is missing', target);
check(Number(target?.record?.id) > 0, 'payment domain record is missing', target);
fs.mkdirSync(outputDir, { recursive: true });

const browser = await launchChromium({ headless: true });
const report = {
  schemaVersion: 'frontend_payment_domain_browser.v1',
  head: process.env.CANDIDATE_HEAD || '',
  target: { user: target.user, securityUser: target.security_user, action: target.action, menu: target.menu, record: target.record },
  primary: { errors: [], mutations: [], contracts: [] },
  security: { errors: [], mutations: [], contracts: [] },
  pass: false,
};

try {
  const primaryContext = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
  const primaryPage = await primaryContext.newPage();
  observe(primaryPage, report.primary);
  await login(primaryPage, target.user.login);
  const actionId = Number(target.action.id);
  const menuId = Number(target.menu.id);
  const recordId = Number(target.record.id);
  await primaryPage.goto(`${frontendUrl}/a/${actionId}?menu_id=${menuId}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const list = primaryPage.locator('[data-product-page-mode="list"]').first();
  await list.waitFor({ timeout: 45000 });
  const row = list.locator('tbody tr').filter({ hasText: String(target.record.name || '') }).first();
  await row.waitFor({ timeout: 45000 });
  await row.click();
  await primaryPage.waitForURL((url) => (
    url.pathname === `/f/payment.request/${recordId}`
      && url.searchParams.get('action_id') === String(actionId)
      && url.searchParams.get('menu_id') === String(menuId)
  ), { timeout: 45000 });
  const form = primaryPage.locator('[data-product-page-mode="form"]:visible').first();
  const driver = form.locator('[data-contract-form-driver]:visible').first();
  await driver.waitFor({ timeout: 45000 });
  const formContract = report.primary.contracts.filter((body) => findKey(body, 'viewType') === 'form').at(-1);
  const editableFields = await form.locator(
    '[data-field-state="edit"] input:not([type="hidden"]):not(:disabled), '
      + '[data-field-state="edit"] textarea:not(:disabled), [data-field-state="edit"] select:not(:disabled)',
  ).count();
  const saveActions = await primaryPage.locator('[data-action-ref="form.save"][data-action-enabled="true"]:visible').count();
  const editTransitions = await form.locator('[data-form-mode-action="edit"]:visible').count();
  const h1 = await form.locator('h1:visible').count();
  const headers = await form.locator('[data-product-page-header]:visible').count();
  const actionNodes = await primaryPage.locator('[data-action-ref]').evaluateAll((nodes) => nodes.map((node) => ({
    actionRef: node.getAttribute('data-action-ref'),
    enabled: node.getAttribute('data-action-enabled'),
    disabled: node.hasAttribute('disabled'),
    text: String(node.textContent || '').trim(),
  })));
  const driverEvidence = {
    fields: await driver.getAttribute('data-render-model-fields'),
    actions: await driver.getAttribute('data-render-model-actions'),
    text: String(await driver.innerText()).replace(/\s+/g, ' ').trim(),
    fieldStates: await driver.locator('[data-field-state]').evaluateAll((nodes) => nodes.map((node) => ({
      field: node.getAttribute('data-field-name'), state: node.getAttribute('data-field-state'),
      inputCount: node.querySelectorAll('input, textarea, select').length,
    }))),
  };
  await primaryPage.screenshot({ path: path.join(outputDir, 'payment-first-edit-diagnostic.png'), fullPage: true });
  report.primary.result = {
    firstUrl: primaryPage.url(), modelRights: findKey(formContract, 'modelRights'),
    effectiveRecordCapabilities: findKey(formContract, 'effectiveRecordCapabilities'),
    effectiveRenderProfile: findKey(formContract, 'effectiveRenderProfile'),
    presentationMode: findKey(formContract, 'presentationMode'), editableFields, saveActions, editTransitions, h1, headers,
    actionNodes, driverEvidence,
  };
  check(formContract, 'payment form contract was not observed');
  check(findKey(formContract, 'modelRights')?.write === true, 'payment model write authority is not true', report.primary.result);
  check(findKey(formContract, 'effectiveRecordCapabilities')?.write === true, 'payment record is not writable', report.primary.result);
  check(findKey(formContract, 'effectiveRenderProfile') === 'edit', 'payment form did not resolve edit profile', report.primary.result);
  check(editableFields > 0, 'payment form has no editable business fields', report.primary.result);
  check(saveActions === 1, 'payment form must expose exactly one save action', report.primary.result);
  check(editTransitions === 0, 'payment form exposed a readonly-to-edit transition', report.primary.result);
  check(h1 === 1 && headers === 1, 'payment form page identity is not unique', report.primary.result);
  check(report.primary.errors.length === 0, 'payment primary journey has browser errors', report.primary.errors);
  check(report.primary.mutations.length === 0, 'payment primary journey mutated business data', report.primary.mutations);
  await primaryPage.screenshot({ path: path.join(outputDir, 'payment-first-edit.png'), fullPage: true });
  await primaryContext.close();

  const securityContext = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
  const securityPage = await securityContext.newPage();
  observe(securityPage, report.security);
  await login(securityPage, target.security_user.login);
  await securityPage.goto(`${frontendUrl}/a/${actionId}?menu_id=${menuId}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await securityPage.waitForFunction(() => document.body.innerText.includes('NAVIGATION_AUTHORITY_DENIED'), undefined, { timeout: 45000 });
  report.security.result = {
    url: securityPage.url(), denialVisible: (await securityPage.locator('body').innerText()).includes('NAVIGATION_AUTHORITY_DENIED'),
    businessForms: await securityPage.locator('[data-product-page-mode="form"]').count(),
    saveActions: await securityPage.locator('[data-action-ref="form.save"]').count(),
  };
  check(report.security.result.denialVisible, 'unauthorized payment entry did not fail closed', report.security.result);
  check(report.security.result.businessForms === 0 && report.security.result.saveActions === 0,
    'unauthorized payment entry exposed business form controls', report.security.result);
  check(report.security.errors.length === 0, 'payment security journey has browser errors', report.security.errors);
  check(report.security.mutations.length === 0, 'payment security journey mutated business data', report.security.mutations);
  await securityPage.screenshot({ path: path.join(outputDir, 'payment-entry-project-role-denied.png'), fullPage: true });
  await securityContext.close();
  report.pass = true;
} finally {
  fs.writeFileSync(path.join(outputDir, 'summary.json'), `${JSON.stringify(report, null, 2)}\n`);
  await browser.close();
}

console.log(JSON.stringify({ pass: report.pass, primary: report.primary.result, security: report.security.result }));
