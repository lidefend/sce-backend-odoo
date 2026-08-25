import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';

const baseUrl = String(process.env.FRONTEND_URL || '').replace(/\/$/, '');
const database = String(process.env.DB_NAME || '');
const login = String(process.env.E2E_LOGIN || '');
const password = String(process.env.E2E_PASSWORD || '');
const head = String(process.env.CANDIDATE_GIT_HEAD || '');
const routes = JSON.parse(process.env.CANDIDATE_VISUAL_ROUTES_JSON || '[]');
const outputDir = path.resolve('artifacts/playwright/local-dev-candidate-visual-smoke');

if (!baseUrl || !database || !login || !password || !/^[0-9a-f]{40}$/.test(head)) throw new Error('candidate visual identity is incomplete');
if (!Array.isArray(routes) || routes.length === 0 || routes.some((item) => !item || typeof item.name !== 'string' || !String(item.path || '').startsWith('/'))) {
  throw new Error('candidate visual routes must be a non-empty name/path array');
}

fs.mkdirSync(outputDir, { recursive: true });
const report = { head, baseUrl, database, login, mutationCount: 0, routes: [] };
const browser = await launchChromium({ headless: true });

async function loginPage(page) {
  await page.goto(`${baseUrl}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const inputs = page.locator('input');
  await inputs.nth(0).fill(login);
  await inputs.nth(1).fill(password);
  if (await inputs.nth(2).count() && !(await inputs.nth(2).isDisabled())) await inputs.nth(2).fill(database);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45000 });
  await page.locator('.layout-shell').waitFor({ timeout: 45000 });
}

async function waitForStableProductSurface(page) {
  await page.waitForFunction(() => {
    const pendingForm = document.querySelector('[data-workspace-primary-content][aria-busy="true"]');
    const pendingCollection = document.querySelector('.product-loading-shell[aria-busy="true"]');
    return !pendingForm && !pendingCollection;
  }, undefined, { timeout: 45000 });
  await page.evaluate(() => new Promise((resolve) => {
    requestAnimationFrame(() => requestAnimationFrame(resolve));
  }));
}

try {
  for (const viewport of [{ name: 'desktop', width: 1440, height: 960 }, { name: 'mobile', width: 390, height: 844 }]) {
    const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height }, locale: 'zh-CN' });
    const page = await context.newPage();
    const errors = [];
    page.on('console', (message) => { if (message.type() === 'error' && !message.text().includes('favicon')) errors.push(`console:${message.text()}`); });
    page.on('pageerror', (error) => errors.push(`page:${error.message}`));
    page.on('response', (response) => { if (response.status() >= 400 && response.url().includes('/api/')) errors.push(`http:${response.status()}:${response.url()}`); });
    page.on('request', (request) => {
      if (request.method() !== 'POST') return;
      let body = {};
      try { body = JSON.parse(request.postData() || '{}'); } catch {}
      const intent = String(body.intent || '');
      const method = String(body?.params?.method || body.method || '');
      if (/(^|\.)(create|write|unlink|execute_button|upload)(\.|$)/.test(intent) || /^(create|write|unlink|web_save|action_)/.test(method)) report.mutationCount += 1;
    });
    await loginPage(page);
    if (viewport.name === 'desktop') {
      const companyTrigger = page.getByRole('button', { name: '公司空间：切换公司' });
      await companyTrigger.click();
      const companySearchRoot = page.locator('[data-semantic-component="ScInput"][data-semantic-layer="primitive"][aria-label="搜索公司"]');
      const companySearch = page.locator('input[data-semantic-component="ScInput"][data-semantic-layer="primitive"][aria-label="搜索公司"], [data-semantic-component="ScInput"][data-semantic-layer="primitive"][aria-label="搜索公司"] input');
      await companySearch.waitFor({ state: 'visible', timeout: 15000 });
      await companySearch.fill('__primitive_adapter_probe__');
      const inputContract = {
        rootCount: await companySearchRoot.count(),
        inputCount: await companySearch.count(),
        value: await companySearch.inputValue(),
      };
      report.routes.push({ viewport: viewport.name, primitiveInputContract: inputContract });
      await companySearch.fill('');
    }
    for (const target of routes) {
      await page.goto(`${baseUrl}${target.path}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
      await page.locator('.layout-shell').waitFor({ timeout: 45000 });
      await page.locator('[data-product-page-mode], main').first().waitFor({ timeout: 45000 });
      await waitForStableProductSurface(page);
      const result = await page.evaluate(() => {
        const root = document.documentElement;
        const style = getComputedStyle(root);
        return {
          h1: document.querySelectorAll('h1').length,
          pageHeaders: document.querySelectorAll('.template-page-header, [data-product-page-header]').length,
          primaryActions: document.querySelectorAll('[data-primary-action]:not([hidden]), .sc-btn-primary:not([hidden])').length,
          overflow: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - window.innerWidth,
          tokenLoaded: Boolean(style.getPropertyValue('--sc-semantic-surface-interactive').trim()),
        };
      });
      report.routes.push({ name: target.name, path: target.path, viewport: viewport.name, finalUrl: page.url(), ...result });
      await page.screenshot({ path: path.join(outputDir, `${viewport.name}-${target.name.replace(/[^a-zA-Z0-9_-]/g, '_')}.png`), fullPage: false });
    }
    report.routes.push({ viewport: viewport.name, errors });
    await context.close();
  }
} finally {
  await browser.close();
}

const errors = report.routes.flatMap((item) => item.errors || []);
const failures = report.routes.filter((item) => item.path && (!item.tokenLoaded || item.h1 !== 1 || item.overflow > 0));
const primitiveInput = report.routes.find((item) => item.primitiveInputContract)?.primitiveInputContract;
if (!primitiveInput || primitiveInput.rootCount !== 1 || primitiveInput.inputCount !== 1 || primitiveInput.value !== '__primitive_adapter_probe__') {
  failures.push({ primitiveInputContract: primitiveInput || null });
}
report.pass = errors.length === 0 && report.mutationCount === 0 && failures.length === 0;
report.errors = errors;
report.failures = failures;
fs.writeFileSync(path.join(outputDir, 'summary.json'), `${JSON.stringify(report, null, 2)}\n`);
console.log(JSON.stringify({ pass: report.pass, mutationCount: report.mutationCount, errors, failures }, null, 2));
if (!report.pass) process.exit(1);
