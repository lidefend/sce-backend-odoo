#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { launchChromium } from './playwright_runtime.mjs';

const require = createRequire(import.meta.url);
const axeModule = require(require.resolve('@axe-core/playwright', {
  paths: [
    path.resolve('frontend/apps/web/node_modules'),
    path.resolve('frontend/node_modules'),
  ],
}));
const AxeBuilder = axeModule.default || axeModule;

const baseUrl = process.env.FRONTEND_URL || 'http://127.0.0.1:5175';
const database = process.env.DB_NAME || '';
const password = process.env.SC_ACCEPTANCE_FIXTURE_PASSWORD || '';
const outputDir = process.env.ARTIFACTS_DIR || 'artifacts/frontend-business-list-productization';
const targets = JSON.parse(process.env.FRONTEND_BUSINESS_LIST_TARGETS_JSON || '{}');

if (database !== 'sc_frontend_acceptance') {
  throw new Error(`BUSINESS_LIST_ACCEPTANCE_DATABASE_DENIED:${database || '<empty>'}`);
}
if (!password) throw new Error('BUSINESS_LIST_ACCEPTANCE_PASSWORD_REQUIRED');

const requestedKeys = new Set(
  String(process.env.FRONTEND_BUSINESS_LIST_TARGET_KEYS || '')
    .split(',')
    .map((value) => value.trim())
    .filter(Boolean),
);
const pages = [
  { key: 'payment', login: 'fixture_role_finance', target: targets.payment_request },
  { key: 'contract', login: 'fixture_role_pm', target: targets.contract },
  { key: 'project', login: 'fixture_role_pm', target: targets.project },
].filter((row) => requestedKeys.size === 0 || requestedKeys.has(row.key));
const viewports = [
  { width: 1440, height: 900, label: '1440x900' },
  { width: 1280, height: 800, label: '1280x800' },
  { width: 960, height: 768, label: '960x768' },
];

fs.mkdirSync(outputDir, { recursive: true });

function check(condition, reason) {
  if (!condition) throw new Error(reason);
}

async function login(page, loginName) {
  await page.goto(`${baseUrl}/login`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  const inputs = page.locator('input');
  await inputs.nth(0).fill(loginName);
  await inputs.nth(1).fill(password);
  if (await inputs.nth(2).isEnabled()) {
    await inputs.nth(2).fill(database);
  } else {
    check(await inputs.nth(2).inputValue() === database, 'LOGIN_DATABASE_MISMATCH');
  }
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45_000 });
  await page.locator('.layout-shell').waitFor({ timeout: 45_000 });
}

async function openTarget(page, target) {
  check(Number(target?.action_id) > 0, 'TARGET_ACTION_MISSING');
  const route = `/a/${target.action_id}?menu_id=${target.menu_id}&action_id=${target.action_id}`;
  await page.goto(`${baseUrl}${route}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  const list = page.locator('section.page[data-product-page-mode="list"]').first();
  await list.waitFor({ timeout: 45_000 });
  await page.waitForFunction(() => {
    const text = document.body.innerText || '';
    const settledSurface = document.querySelector(
      'table.flat-table, table.group-table, .desktop-record-table, .sc-empty-state, .sc-state-panel, [data-list-state="empty"], [data-list-state="error"]',
    );
    return Boolean(settledSurface) && !text.includes('正在加载列表...');
  }, undefined, { timeout: 45_000 });
  return route;
}

async function inspect(page, key, viewport) {
  const body = page.locator('body');
  const text = await body.innerText();
  const headers = await page.locator('table thead th').allTextContents();
  const title = (await page.locator('.product-list-header__title-row h2').first().textContent() || '').trim();
  const summary = (await page.locator('.product-list-header__result').first().textContent().catch(() => '') || '').trim();
  const toolbarCount = await page.locator('.action-toolbar').count();
  const tableCount = await page.locator('table.flat-table, table.group-table, .desktop-record-table').count();
  const documentOverflow = await page.evaluate(() => ({
    body: document.body.scrollWidth - document.body.clientWidth,
    document: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  }));
  const layout = await page.evaluate(() => {
    const measure = (selector) => {
      const node = document.querySelector(selector);
      if (!node) return null;
      const rect = node.getBoundingClientRect();
      return { top: Math.round(rect.top), bottom: Math.round(rect.bottom), height: Math.round(rect.height) };
    };
    return {
      header: measure('.product-list-header'),
      identity: measure('.product-list-header__identity'),
      toolbar: measure('.action-toolbar'),
      table: measure('.table.sc-product-main-surface'),
    };
  });
  check(title.length > 0, `${key}:LIST_TITLE_MISSING`);
  check(summary.length > 0, `${key}:RESULT_SUMMARY_MISSING`);
  check(toolbarCount === 1, `${key}:QUERY_TOOLBAR_COUNT_${toolbarCount}`);
  check(tableCount > 0 || /暂无|没有符合当前条件/.test(text), `${key}:LIST_SURFACE_MISSING`);
  check(documentOverflow.body <= 1 && documentOverflow.document <= 1, `${key}:DOCUMENT_HORIZONTAL_OVERFLOW`);

  const screenshot = path.join(outputDir, `${key}-after-${viewport.label}.png`);
  await page.screenshot({ path: screenshot, fullPage: true, animations: 'disabled' });
  return {
    key,
    viewport: viewport.label,
    title,
    summary,
    headers: headers.map((value) => value.trim()).filter(Boolean),
    document_overflow: documentOverflow,
    layout,
    screenshot,
  };
}

async function verifyFilteredEmpty(page) {
  const input = page.locator('.native-searchbox input[type="search"]').first();
  await input.fill('CORE035-NO-SUCH-BUSINESS-RECORD-9F3D');
  await input.press('Enter');
  await page.getByRole('heading', { name: '没有符合当前条件的记录', exact: true }).waitFor({
    timeout: 45_000,
  });
  check(await page.getByText(/已应用 \d+ 项查询条件/).count() > 0, 'ACTIVE_CONDITION_SUMMARY_MISSING');
  const screenshot = path.join(outputDir, 'payment-filter-empty.png');
  await page.screenshot({ path: screenshot, fullPage: true, animations: 'disabled' });
  await page.getByRole('button', { name: '清除查询条件', exact: true }).click();
  await page.getByRole('heading', { name: '没有符合当前条件的记录', exact: true }).waitFor({
    state: 'hidden',
    timeout: 45_000,
  });
  check(await input.inputValue() === '', 'CLEAR_CONDITIONS_DID_NOT_CLEAR_SEARCH');
  return screenshot;
}

async function main() {
  const browser = await launchChromium({ headless: true });
  const result = {
    result: 'PASS',
    database,
    base_url: baseUrl,
    pages: [],
    accessibility: [],
    filtered_empty: null,
    console_errors: [],
    page_errors: [],
    blocking_http_errors: [],
  };
  try {
    for (const targetPage of pages) {
      for (const viewport of viewports) {
        const context = await browser.newContext({
          viewport: { width: viewport.width, height: viewport.height },
          locale: 'zh-CN',
        });
        const page = await context.newPage();
        page.on('console', (message) => {
          if (message.type() === 'error' && !/favicon|ResizeObserver/.test(message.text())) {
            result.console_errors.push({ page: targetPage.key, viewport: viewport.label, message: message.text() });
          }
        });
        page.on('pageerror', (error) => result.page_errors.push({
          page: targetPage.key,
          viewport: viewport.label,
          message: error.message,
        }));
        page.on('response', (response) => {
          if (response.status() >= 500) {
            result.blocking_http_errors.push({
              page: targetPage.key,
              viewport: viewport.label,
              status: response.status(),
              url: response.url(),
            });
          }
        });
        await login(page, targetPage.login);
        const route = await openTarget(page, targetPage.target);
        const observation = await inspect(page, targetPage.key, viewport);
        result.pages.push({ ...observation, route, login: targetPage.login });
        if (viewport.label === '1440x900') {
          const axe = await new AxeBuilder({ page })
            .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
            .analyze();
          const blocking = axe.violations.filter((row) => row.impact === 'critical' || row.impact === 'serious');
          result.accessibility.push({
            page: targetPage.key,
            critical: blocking.filter((row) => row.impact === 'critical').length,
            serious: blocking.filter((row) => row.impact === 'serious').length,
            rules: blocking.map((row) => ({
              id: row.id,
              help: row.help,
              targets: row.nodes.flatMap((node) => node.target),
            })),
          });
          if (targetPage.key === 'payment') {
            result.filtered_empty = await verifyFilteredEmpty(page);
          }
        }
        await context.close();
      }
    }
    check(result.console_errors.length === 0, 'CONSOLE_ERRORS_PRESENT');
    check(result.page_errors.length === 0, 'PAGE_ERRORS_PRESENT');
    check(result.blocking_http_errors.length === 0, 'BLOCKING_HTTP_ERRORS_PRESENT');
    check(result.accessibility.every((row) => row.critical === 0 && row.serious === 0), 'BLOCKING_AXE_VIOLATIONS_PRESENT');
  } catch (error) {
    result.result = 'FAIL';
    result.error = error instanceof Error ? error.message : String(error);
    throw error;
  } finally {
    fs.writeFileSync(path.join(outputDir, 'report.json'), `${JSON.stringify(result, null, 2)}\n`);
    await browser.close();
  }
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
