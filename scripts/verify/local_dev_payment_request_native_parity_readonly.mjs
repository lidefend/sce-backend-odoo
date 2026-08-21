import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';

const target = JSON.parse(process.env.LOCAL_DEV_PAYMENT_PARITY_JSON || '{}');
const frontendUrl = process.env.FRONTEND_URL || '';
const odooUrl = process.env.ODOO_URL || '';
const database = process.env.DB_NAME || '';
const password = process.env.E2E_PASSWORD || '';
const login = String(target?.user?.login || '');
const actionId = Number(target?.action?.id || 0);
const menuId = Number(target?.menu?.id || 0);
const recordId = Number(target?.record?.id || 0);
const model = 'payment.request';
const outputDir = path.resolve('artifacts/playwright/local-dev-payment-request-native-parity');

function check(value, message, details = undefined) {
  if (value) return;
  const suffix = details === undefined ? '' : ` ${JSON.stringify(details)}`;
  throw new Error(`${message}${suffix}`);
}

check(frontendUrl && odooUrl && database && password && login, 'local.dev parity identity is incomplete');
check(actionId > 0 && menuId > 0 && recordId > 0, 'local.dev parity record identity is invalid', target);

function normalize(value) {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

function unique(values) {
  return [...new Set(values.map(normalize).filter((value) => value && value !== '...'))];
}

function attachDiagnostics(page, label, errors, blockedMutations, contractBodies = []) {
  page.on('console', (message) => {
    if (message.type() === 'error' && !message.text().includes('favicon')) errors.push(`${label}: ${message.text()}`);
  });
  page.on('pageerror', (error) => errors.push(`${label}: ${error.message}`));
  page.on('request', (request) => {
    if (request.method() !== 'POST') return;
    let payload = {};
    try { payload = JSON.parse(request.postData() || '{}'); } catch {}
    const intent = String(payload?.intent || '');
    const method = String(payload?.params?.method || payload?.method || '');
    const mutation = /(^|\.)(create|write|unlink|execute_button|onchange|upload)(\.|$)/.test(intent)
      || /^(create|write|unlink|web_save|action_)/.test(method);
    if (mutation) blockedMutations.push({ label, url: request.url(), intent, method });
  });
  page.on('response', async (response) => {
    if (label !== 'custom' || !response.url().includes('/api/v1/intent')) return;
    let requestPayload = {};
    try { requestPayload = JSON.parse(response.request().postData() || '{}'); } catch {}
    if (requestPayload?.intent !== 'ui.contract.v2') return;
    try { contractBodies.push(await response.json()); } catch {}
  });
}

async function loginCustom(page) {
  await page.goto(`${frontendUrl}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const inputs = page.locator('input');
  await inputs.nth(0).fill(login);
  await inputs.nth(1).fill(password);
  if (await inputs.nth(2).count()) {
    if (!(await inputs.nth(2).isDisabled())) await inputs.nth(2).fill(database);
  }
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 30000 });
}

async function loginNative(page) {
  await page.goto(`${odooUrl}/web/login?db=${encodeURIComponent(database)}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  if (await page.locator('input[name="db"]').count()) await page.locator('input[name="db"]').fill(database);
  await page.locator('input[name="login"]').fill(login);
  await page.locator('input[name="password"]').fill(password);
  await page.locator('button[type="submit"], input[type="submit"]').first().click();
  await page.waitForURL((url) => !url.pathname.includes('/web/login'), { timeout: 30000 });
}

async function collectNative(page) {
  await page.locator('.o_form_view').waitFor({ timeout: 45000 });
  const tabs = unique(await page.locator('.o_notebook .nav-link, .o_notebook [role="tab"]').allTextContents());
  for (const label of tabs) {
    await page.locator('.o_notebook .nav-link, .o_notebook [role="tab"]').filter({ hasText: label }).first().click().catch(() => {});
  }
  return page.locator('.o_form_view').evaluate((root) => {
    const text = (selector) => [...root.querySelectorAll(selector)].map((node) => String(node.textContent || '').replace(/\s+/g, ' ').trim()).filter(Boolean);
    return {
      tabs: text('.o_notebook .nav-link, .o_notebook [role="tab"]'),
      groups: text('.o_group_name, .o_inner_group > tbody > tr:first-child th, legend'),
      fields: [...root.querySelectorAll('.o_field_widget[name]')].map((node) => node.getAttribute('name')).filter(Boolean),
      headerActions: text('.o_form_statusbar .o_statusbar_buttons button'),
      statusbar: text('.o_statusbar_status button, .o_statusbar_status .dropdown-item'),
      smartActions: text('.o_form_button_box button'),
      x2manyColumns: text('.o_field_x2many_list thead th, .o_list_table thead th'),
    };
  });
}

async function collectCustom(page) {
  await page.locator('[data-native-contract-structure] .native-form-tree').first().waitFor({ timeout: 45000 });
  const tabs = unique(await page.locator('[data-native-contract-structure] .native-tabs .native-tab').allTextContents());
  for (const label of tabs) {
    await page.locator('[data-native-contract-structure] .native-tabs .native-tab').filter({ hasText: label }).first().click();
  }
  const structure = await page.locator('[data-native-contract-structure]').evaluate((root) => {
    const text = (selector) => [...root.querySelectorAll(selector)].map((node) => String(node.textContent || '').replace(/\s+/g, ' ').trim()).filter(Boolean);
    return {
      tabs: text('.native-tabs .native-tab'),
      groups: [...root.querySelectorAll('[data-group-title]')].map((node) => node.getAttribute('data-group-title')).filter(Boolean),
      fields: [...root.querySelectorAll('[data-field-name]')].map((node) => node.getAttribute('data-field-name')).filter(Boolean),
      headerActions: text('.native-container--header .native-action-btn'),
      smartActions: text('.native-actions--smart button'),
      x2manyColumns: text('.o2m-header-cell, .o2m-field .meta, th'),
    };
  });
  return {
    ...structure,
    statusbar: unique(await page.locator('button[aria-label^="第 "][aria-label*="步，共"]').evaluateAll((buttons) => (
      buttons.map((button) => String(button.lastElementChild?.textContent || '').replace(/\s+/g, ' ').trim()).filter(Boolean)
    ))),
  };
}

function missing(nativeValues, customValues) {
  const custom = new Set(unique(customValues));
  return unique(nativeValues).filter((value) => !custom.has(value));
}

fs.mkdirSync(outputDir, { recursive: true });
const browser = await launchChromium({ headless: true });
const errors = [];
const blockedMutations = [];
const contractBodies = [];
const report = { target, frontendUrl, odooUrl, database, pass: false };
try {
  const nativeContext = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
  const nativePage = await nativeContext.newPage();
  attachDiagnostics(nativePage, 'native', errors, blockedMutations);
  await loginNative(nativePage);
  await nativePage.goto(`${odooUrl}/web#id=${recordId}&model=${model}&view_type=form&action=${actionId}&menu_id=${menuId}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  report.native = await collectNative(nativePage);
  await nativePage.screenshot({ path: path.join(outputDir, 'native-payment-request.png'), fullPage: true });
  await nativeContext.close();

  const customContext = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
  const customPage = await customContext.newPage();
  attachDiagnostics(customPage, 'custom', errors, blockedMutations, contractBodies);
  await loginCustom(customPage);
  await customPage.goto(`${frontendUrl}/r/${model}/${recordId}?action_id=${actionId}&menu_id=${menuId}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  report.custom = await collectCustom(customPage);
  await customPage.screenshot({ path: path.join(outputDir, 'custom-payment-request.png'), fullPage: true });
  await customContext.close();

  report.gaps = {
    tabs: missing(report.native.tabs, report.custom.tabs),
    groups: missing(report.native.groups, report.custom.groups),
    fields: missing(report.native.fields, report.custom.fields),
    headerActions: missing(report.native.headerActions, report.custom.headerActions),
    smartActions: missing(report.native.smartActions, report.custom.smartActions),
    x2manyColumns: missing(report.native.x2manyColumns, report.custom.x2manyColumns),
    extraTabs: missing(report.custom.tabs, report.native.tabs),
    extraFields: missing(report.custom.fields, report.native.fields),
    statusbar: missing(report.native.statusbar, report.custom.statusbar),
  };
  report.contractBodies = contractBodies;
  report.errors = errors;
  report.blockedMutations = blockedMutations;
  report.pass = Object.values(report.gaps).every((rows) => rows.length === 0)
    && errors.length === 0
    && blockedMutations.length === 0;
  fs.writeFileSync(path.join(outputDir, 'summary.json'), `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({ pass: report.pass, gaps: report.gaps, errors, blockedMutations }, null, 2));
  check(report.pass, 'payment request native/custom structure parity failed', report.gaps);
} finally {
  await browser.close();
}
