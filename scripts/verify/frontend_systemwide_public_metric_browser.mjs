import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';

const target = JSON.parse(process.env.FRONTEND_SYSTEMWIDE_PUBLIC_METRIC_TARGET || '{}');
const frontendUrl = process.env.FRONTEND_URL || '';
const database = process.env.DB_NAME || '';
const password = process.env.E2E_PASSWORD || '';
const outputDir = path.resolve('artifacts/playwright/systemwide-public-metric-acceptance');

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
function requestBody(request) {
  try { return JSON.parse(request.postData() || '{}'); } catch { return {}; }
}
function isMutation(request) {
  if (request.method() !== 'POST') return false;
  const body = requestBody(request);
  const intent = String(body.intent || body.params?.intent || '');
  const method = String(body.params?.method || body.method || '');
  return /(^|\.)(create|write|unlink|execute_button|upload)(\.|$)/.test(intent)
    || /^(create|write|unlink|web_save|action_)/.test(method);
}
async function login(page) {
  await page.goto(`${frontendUrl}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const inputs = page.locator('input');
  await inputs.nth(0).fill(target.user.login);
  await inputs.nth(1).fill(password);
  if (await inputs.nth(2).count() && !(await inputs.nth(2).isDisabled())) await inputs.nth(2).fill(database);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 30000 });
  await page.locator('[data-semantic-component="ProductAppShell"]:visible').first().waitFor({ timeout: 45000 });
}
check(frontendUrl && database && password, 'systemwide public-metric browser identity is incomplete');
check(target?.user?.login && Array.isArray(target.targets) && target.targets.length === 3,
  'systemwide public-metric target matrix is incomplete', target);
fs.mkdirSync(outputDir, { recursive: true });

const browser = await launchChromium({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
const page = await context.newPage();
const report = {
  schemaVersion: 'frontend_systemwide_public_metric_browser.v1',
  head: process.env.CANDIDATE_HEAD || '', target,
  errors: [], mutations: [], contracts: [], rows: [], pass: false,
};
page.on('console', (message) => {
  if (message.type() === 'error' && !/favicon|ResizeObserver/i.test(message.text())) report.errors.push(message.text());
});
page.on('pageerror', (error) => report.errors.push(error.message));
page.on('response', (response) => {
  if (response.status() >= 400) report.errors.push(`http ${response.status()} ${response.url()}`);
});
page.on('request', (request) => {
  if (isMutation(request)) report.mutations.push({ url: request.url(), body: requestBody(request) });
});
page.on('response', async (response) => {
  if (!response.url().includes('/api/v1/intent')) return;
  const body = requestBody(response.request());
  if (findKey(body, 'intent') !== 'ui.contract.v2') return;
  try {
    report.contracts.push({ request: body, response: await response.json() });
  } catch {}
});

try {
  await login(page);
  for (const spec of target.targets) {
    const contractStart = report.contracts.length;
    await page.goto(`${frontendUrl}${spec.route}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
    const pattern = page.locator(`[data-product-page-pattern="${spec.pagePattern}"]:visible`).first();
    await pattern.waitFor({ timeout: 45000 });
    await page.locator('[data-product-page-header]:visible').first().waitFor({ timeout: 45000 });
    await page.waitForFunction(() => !/正在载入|正在加载|正在初始化/.test(document.body.innerText || ''), null, { timeout: 45000 });

    const metrics = await page.evaluate(({ menuId }) => {
      const visible = (node) => node instanceof HTMLElement
        && node.getClientRects().length > 0 && getComputedStyle(node).visibility !== 'hidden';
      const patternNode = document.querySelector('[data-product-page-pattern]');
      const header = document.querySelector('[data-product-page-header]');
      const fieldNames = [...patternNode?.querySelectorAll('[data-field-name]') || []]
        .filter(visible).map((node) => String(node.getAttribute('data-field-name') || '')).filter(Boolean);
      const titles = [...patternNode?.querySelectorAll('[data-group-title]') || []]
        .filter(visible).map((node) => String(node.getAttribute('data-group-title') || '').replace(/\s+/g, ' ').trim()).filter(Boolean);
      const components = [...patternNode?.querySelectorAll('[data-component-key]') || []].filter(visible);
      const unresolved = components.filter((node) => !['ready', 'readable_fallback'].includes(node.getAttribute('data-component-readiness') || ''));
      const primary = [...document.querySelectorAll('[data-product-primary-action]')].filter(visible);
      const enabledPrimary = primary.filter((node) => !(node instanceof HTMLButtonElement) || !node.disabled);
      const fakeReadonly = [...patternNode?.querySelectorAll('input:disabled, textarea:disabled, select:disabled') || []]
        .filter(visible);
      const selectedNav = document.querySelectorAll(`#primary-sidebar [data-navigation-menu-id="${menuId}"][aria-current="page"]`).length;
      return {
        url: location.href,
        h1: document.querySelectorAll('h1').length,
        pageHeader: document.querySelectorAll('[data-product-page-header]').length,
        pattern: patternNode?.getAttribute('data-product-page-pattern') || '',
        presentationMode: header?.getAttribute('data-presentation-mode') || '',
        renderProfile: header?.getAttribute('data-render-profile') || '',
        selectedNavigationItem: selectedNav,
        primaryActions: primary.length,
        enabledPrimaryActions: enabledPrimary.length,
        saveActions: [...document.querySelectorAll('[data-action-ref="form.save"], [data-action-method="save"], [data-action-method="write"]')].filter(visible).length,
        editTransitions: [...document.querySelectorAll('[data-form-mode-action="edit"]')].filter(visible).length,
        fieldNames,
        duplicateFields: [...new Set(fieldNames.filter((value, index) => fieldNames.indexOf(value) !== index))],
        titles,
        duplicateTitles: [...new Set(titles.filter((value, index) => titles.indexOf(value) !== index))],
        disabledFakeReadonlyControls: fakeReadonly.length,
        disabledFakeReadonlyControlDetails: fakeReadonly.map((node) => ({
          tag: node.tagName.toLowerCase(), type: node.getAttribute('type') || '',
          value: String(node.value || ''), field: node.closest('[data-field-name]')?.getAttribute('data-field-name') || '',
          component: node.closest('[data-component-key]')?.getAttribute('data-component-key') || '',
          className: String(node.className || ''),
        })),
        registeredComponents: components.length,
        unregisteredComponents: unresolved.length,
        horizontalOverflow: Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth),
      };
    }, { menuId: spec.menuId });

    const candidateContracts = report.contracts.slice(contractStart);
    const formContract = candidateContracts.map((row) => row.response)
      .find((body) => findKey(body, 'model') === spec.model && findKey(body, 'viewType') === 'form');
    const listContract = candidateContracts.map((row) => row.response)
      .find((body) => findKey(body, 'model') === spec.model && findKey(body, 'viewType') === 'list');
    const contract = formContract || listContract;
    metrics.contractPresentationMode = formContract ? findKey(formContract, 'presentationMode') : 'collection';
    metrics.contractRenderProfile = formContract ? findKey(formContract, 'effectiveRenderProfile') : 'readonly';
    metrics.contractModel = findKey(contract, 'model');
    metrics.contractActionId = candidateContracts.map((row) => findKey(row.request, 'action_id')).find(Boolean);
    metrics.contractMenuId = candidateContracts.map((row) => findKey(row.request, 'menu_id')).find(Boolean);

    check(metrics.h1 === 1 && metrics.pageHeader === 1, `${spec.key}: page identity is not unique`, metrics);
    check(metrics.pattern === spec.pagePattern, `${spec.key}: page pattern drifted`, metrics);
    check(metrics.presentationMode === spec.presentationMode && metrics.renderProfile === spec.renderProfile,
      `${spec.key}: header authority drifted`, metrics);
    check(metrics.selectedNavigationItem === 1, `${spec.key}: selected navigation identity is not unique`, metrics);
    check(metrics.primaryActions <= 1, `${spec.key}: multiple primary actions`, metrics);
    check(metrics.duplicateFields.length === 0, `${spec.key}: duplicate fields`, metrics);
    check(metrics.duplicateTitles.length === 0, `${spec.key}: duplicate titles`, metrics);
    check(metrics.unregisteredComponents === 0, `${spec.key}: unregistered component reached DOM`, metrics);
    check(metrics.horizontalOverflow === 0, `${spec.key}: desktop horizontal overflow`, metrics);
    check(metrics.contractModel === spec.model, `${spec.key}: Contract model drifted`, metrics);
    check(String(metrics.contractActionId) === String(spec.actionId), `${spec.key}: Contract action drifted`, metrics);
    check(String(metrics.contractMenuId) === String(spec.menuId), `${spec.key}: Contract menu drifted`, metrics);
    if (spec.pagePattern !== 'collection') {
      check(metrics.contractPresentationMode === spec.presentationMode,
        `${spec.key}: presentation mode was not backend-declared`, metrics);
      check(metrics.contractRenderProfile === spec.renderProfile,
        `${spec.key}: render profile differs from backend authority`, metrics);
    }
    if (spec.renderProfile === 'edit') {
      check(metrics.saveActions === 1 && metrics.enabledPrimaryActions === 1,
        `${spec.key}: edit primary action is not uniquely usable`, metrics);
      check(metrics.editTransitions === 0, `${spec.key}: edit intermediate action remains`, metrics);
    } else {
      check(metrics.saveActions === 0, `${spec.key}: readonly surface exposes save`, metrics);
      check(metrics.disabledFakeReadonlyControls === 0,
        `${spec.key}: readonly facts use disabled fake controls`, metrics);
    }
    if (spec.route.startsWith('/r/')) {
      check(new URL(metrics.url).pathname.startsWith('/r/'), `${spec.key}: explicit readonly route was promoted`, metrics);
    }

    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForFunction(() => document.documentElement.clientWidth === 390, null, { timeout: 15000 });
    metrics.mobile390Overflow = await page.evaluate(() => Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth));
    check(metrics.mobile390Overflow === 0, `${spec.key}: 390px horizontal overflow`, metrics);
    await page.screenshot({ path: path.join(outputDir, `${spec.key}-390.png`), fullPage: true });
    await page.setViewportSize({ width: 1440, height: 960 });
    report.rows.push({ key: spec.key, ...metrics });
  }
  check(report.rows.some((row) => row.presentationMode === 'task'), 'task presentation evidence is absent');
  check(report.rows.some((row) => row.presentationMode === 'workspace'), 'workspace presentation evidence is absent');
  check(report.rows.reduce((sum, row) => sum + row.registeredComponents, 0) > 0,
    'registered component runtime evidence is absent', report.rows);
  check(report.errors.length === 0, 'browser errors occurred', report.errors);
  check(report.mutations.length === 0, 'readonly acceptance mutated business data', report.mutations);
  report.pass = true;
  fs.writeFileSync(path.join(outputDir, 'summary.json'), `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({ pass: true, rows: report.rows.length, errors: 0, mutations: 0 }));
} finally {
  await context.close();
  await browser.close();
}
