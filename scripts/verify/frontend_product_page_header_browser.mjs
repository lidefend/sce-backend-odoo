#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';
import { resolveAcceptanceEnvironment } from './lib/frontend_acceptance_environment.mjs';

const acceptance = resolveAcceptanceEnvironment({ tool: 'geometry-scroll-audit', operation: 'readonly' });
const targets = JSON.parse(process.env.PRODUCT_PAGE_HEADER_TARGETS_JSON || '[]');
const output = path.resolve(process.env.PRODUCT_PAGE_HEADER_OUTPUT || 'artifacts/frontend-product-page-header/summary.json');

function check(value, message) { if (!value) throw new Error(message); }
function requestBody(request) { try { return request.postDataJSON() || {}; } catch { return {}; } }
function isMutation(request) {
  if (request.method() !== 'POST') return false;
  const body = requestBody(request);
  const intent = String(body.intent || body.params?.intent || '');
  if (['execute_button', 'api.data.create', 'api.data.write', 'api.data.unlink'].includes(intent)) return true;
  return intent === 'api.data' && ['create', 'write', 'unlink'].includes(String(body.params?.op || body.params?.payload?.op || ''));
}

check(Array.isArray(targets) && targets.length > 0 && targets.length <= 3, 'one to three governed targets are required');
check(acceptance.login && acceptance.password, 'governed acceptance credentials are required');
fs.mkdirSync(path.dirname(output), { recursive: true });

const browser = await launchChromium({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();
const evidence = { console: [], pageerror: [], http: [], mutations: [], targets: [] };
page.on('console', (message) => { if (message.type() === 'error' && !/favicon|ResizeObserver/i.test(message.text())) evidence.console.push(message.text()); });
page.on('pageerror', (error) => evidence.pageerror.push(error.message));
page.on('response', (response) => { if (response.status() >= 500) evidence.http.push({ status: response.status(), url: response.url() }); });
await page.route('**/*', async (route) => {
  if (isMutation(route.request())) {
    evidence.mutations.push({ url: route.request().url(), body: requestBody(route.request()) });
    await route.abort('blockedbyclient');
    return;
  }
  await route.continue();
});

await page.goto(`${acceptance.baseUrl}/login`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
await page.locator('#login-username, input[autocomplete="username"]').first().fill(acceptance.login);
await page.locator('#login-password, input[autocomplete="current-password"]').first().fill(acceptance.password);
const database = page.locator('input').nth(2);
if (await database.isEnabled().catch(() => false)) await database.fill(acceptance.database);
await page.getByRole('button', { name: /^登录$/ }).click();
await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45_000 });

for (const target of targets) {
  check(typeof target.route === 'string' && target.route.startsWith('/'), 'target route is invalid');
  await page.goto(`${acceptance.baseUrl}${target.route}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  const header = page.locator('[data-product-page-header]');
  await header.waitFor({ state: 'visible', timeout: 45_000 });
  await page.waitForFunction(() => !/正在载入|正在加载|正在初始化/.test(document.body.innerText || ''), null, { timeout: 45_000 });
  const snapshot = await page.evaluate(() => {
    const visible = (node) => node instanceof HTMLElement && node.getClientRects().length > 0 && getComputedStyle(node).visibility !== 'hidden';
    const headerNode = document.querySelector('[data-product-page-header]');
    const primary = [...document.querySelectorAll('[data-product-primary-action]')].filter(visible);
    const enabledPrimary = primary.filter((node) => !(node instanceof HTMLButtonElement) || !node.disabled);
    const save = [...document.querySelectorAll('[data-action-ref="form.save"], [data-action-method="save"], [data-action-method="write"]')].filter(visible);
    return {
      url: location.href,
      headerCount: document.querySelectorAll('[data-product-page-header]').length,
      h1Count: document.querySelectorAll('h1').length,
      presentationMode: headerNode?.getAttribute('data-presentation-mode') || '',
      renderProfile: headerNode?.getAttribute('data-render-profile') || '',
      dirtyState: headerNode?.getAttribute('data-dirty-state') || '',
      primaryCount: primary.length,
      enabledPrimaryCount: enabledPrimary.length,
      saveCount: save.length,
      editTransitionCount: [...document.querySelectorAll('[data-form-mode-action="edit"]')].filter(visible).length,
      bodyActionBarCount: [...document.querySelectorAll('.sc-form-driver-host [data-canonical-action-bar]')].filter(visible).length,
      overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    };
  });
  check(snapshot.headerCount === 1, `${target.key}: page header count ${snapshot.headerCount}`);
  check(snapshot.h1Count === 1, `${target.key}: h1 count ${snapshot.h1Count}`);
  check(snapshot.presentationMode === target.presentationMode, `${target.key}: presentation mode ${snapshot.presentationMode}`);
  check(snapshot.renderProfile === target.renderProfile, `${target.key}: render profile ${snapshot.renderProfile}`);
  check(snapshot.primaryCount <= 1, `${target.key}: multiple primary actions`);
  check(snapshot.bodyActionBarCount === 0, `${target.key}: parallel body action bar remains`);
  if (target.renderProfile === 'edit') {
    check(snapshot.saveCount === 1 && snapshot.primaryCount === 1 && snapshot.enabledPrimaryCount === 1, `${target.key}: edit save action is not uniquely available`);
    check(snapshot.editTransitionCount === 0, `${target.key}: edit transition button remains`);
  }
  if (target.renderProfile === 'readonly') check(snapshot.saveCount === 0, `${target.key}: readonly exposes save`);
  await page.setViewportSize({ width: 390, height: 844 });
  const mobileOverflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  check(!mobileOverflow, `${target.key}: 390px overflow`);
  await page.setViewportSize({ width: 1440, height: 900 });
  evidence.targets.push({ key: target.key, ...snapshot, mobileOverflow });
}

check(evidence.console.length === 0, `console errors: ${JSON.stringify(evidence.console)}`);
check(evidence.pageerror.length === 0, `page errors: ${JSON.stringify(evidence.pageerror)}`);
check(evidence.http.length === 0, `http 5xx: ${JSON.stringify(evidence.http)}`);
check(evidence.mutations.length === 0, `business mutations: ${JSON.stringify(evidence.mutations)}`);
fs.writeFileSync(output, `${JSON.stringify({ ...evidence, mutationCount: 0 }, null, 2)}\n`);
await browser.close();
console.log(`[frontend_product_page_header_browser] PASS targets=${evidence.targets.length} mutations=0 errors=0`);
