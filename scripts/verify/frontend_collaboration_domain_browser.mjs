import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';

const target = JSON.parse(process.env.FRONTEND_COLLABORATION_DOMAIN_TARGET || '{}');
const frontendUrl = process.env.FRONTEND_URL || '';
const database = process.env.DB_NAME || '';
const password = process.env.E2E_PASSWORD || '';
const outputDir = path.resolve('artifacts/playwright/phase10-collaboration-domain');

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
    if (response.url().includes('/api/')) evidence.network.push({ status: response.status(), url: response.url() });
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
    if (findKey(requestBody, 'intent') === 'ui.contract.v2') {
      evidence.contractRequests.push({
        actionId: requestBody?.params?.action_id,
        menuId: requestBody?.params?.menu_id,
        operation: requestBody?.params?.op,
      });
      try { evidence.contracts.push(await response.json()); } catch {}
    }
  });
}

check(frontendUrl && database && password, 'collaboration browser identity is incomplete');
check(target?.user?.login && target?.security_user?.login, 'collaboration users are missing', target);
check(Number(target?.action?.id) > 0 && Number(target?.menu?.id) > 0, 'collaboration entry is missing', target);
fs.mkdirSync(outputDir, { recursive: true });

const browser = await launchChromium({ headless: true });
const report = {
  schemaVersion: 'frontend_collaboration_domain_browser.v1',
  head: process.env.CANDIDATE_HEAD || '',
  target: { user: target.user, securityUser: target.security_user, action: target.action, menu: target.menu },
  primary: { errors: [], mutations: [], contracts: [], contractRequests: [], network: [] },
  security: { errors: [], mutations: [], contracts: [], contractRequests: [], network: [] },
  pass: false,
};

try {
  const primaryContext = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
  const page = await primaryContext.newPage();
  observe(page, report.primary);
  await login(page, target.user.login);
  const actionId = Number(target.action.id);
  const menuId = Number(target.menu.id);
  await page.goto(`${frontendUrl}/a/${actionId}?menu_id=${menuId}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const list = page.locator('[data-product-page-mode="list"]:visible').first();
  await list.waitFor({ timeout: 45000 });
  await page.waitForFunction(() => {
    const surface = document.querySelector('[data-product-page-mode="list"]');
    return Boolean(surface) && !String(surface.textContent || '').includes('正在载入数据');
  }, undefined, { timeout: 45000 });
  const listContract = report.primary.contracts.filter((body) => findKey(body, 'viewType') === 'list').at(-1);
  const listContractRequest = report.primary.contractRequests.at(-1);
  report.primary.result = {
    url: page.url(), model: findKey(listContract, 'model'),
    actionId: listContractRequest?.actionId, menuId: listContractRequest?.menuId,
    h1: await list.locator('h1:visible').count(),
    headers: await list.locator('[data-product-page-header]:visible').count(),
    tables: await list.locator('table:visible').count(),
    emptyStates: await list.locator('[data-semantic-component="ScEmptyState"]:visible').count(),
    text: (await list.innerText()).slice(0, 2000),
  };
  check(listContract, 'collaboration list contract was not observed');
  check(report.primary.result.model === 'mail.notification', 'collaboration model identity drifted', report.primary.result);
  check(String(report.primary.result.actionId) === String(actionId), 'collaboration action identity drifted', report.primary.result);
  check(String(report.primary.result.menuId) === String(menuId), 'collaboration menu identity drifted', report.primary.result);
  check(report.primary.result.h1 === 1 && report.primary.result.headers === 1,
    'collaboration list page identity is not unique', report.primary.result);
  check(report.primary.result.tables === 1 || report.primary.result.emptyStates === 1,
    'collaboration list has neither table nor professional empty state', report.primary.result);
  check(report.primary.errors.length === 0 && report.primary.mutations.length === 0,
    'collaboration primary journey is not read-only clean', report.primary);
  await page.screenshot({ path: path.join(outputDir, 'message-notification-list.png'), fullPage: true });
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
    businessLists: await securityPage.locator('[data-product-page-mode="list"]').count(),
  };
  check(report.security.result.denialVisible && report.security.result.businessLists === 0,
    'unauthorized collaboration entry did not fail closed', report.security.result);
  check(report.security.errors.length === 0 && report.security.mutations.length === 0,
    'collaboration security journey is not clean', report.security);
  await securityPage.screenshot({ path: path.join(outputDir, 'message-notification-finance-role-denied.png'), fullPage: true });
  await securityContext.close();
  report.pass = true;
} finally {
  fs.writeFileSync(path.join(outputDir, 'summary.json'), `${JSON.stringify(report, null, 2)}\n`);
  await browser.close();
}

console.log(JSON.stringify({ pass: report.pass, primary: report.primary.result, security: report.security.result }));
