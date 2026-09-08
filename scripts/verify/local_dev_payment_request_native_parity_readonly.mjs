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
  await page.waitForFunction(() => (
    document.querySelector('[data-contract-form-driver]')
    || document.querySelector('.sc-state-panel[role="alert"]')
  ), null, { timeout: 45000 });
  const errorPanel = page.locator('.sc-state-panel[role="alert"]').first();
  if (await errorPanel.count()) {
    const message = normalize(await errorPanel.innerText());
    throw new Error(`custom form render failed: ${message.slice(0, 2000)}`);
  }
  const root = page.locator('[data-contract-form-driver]').first();
  const nativeTabs = root.locator('.native-tabs .native-tab');
  const nativeTabCount = await nativeTabs.count();
  const tabs = unique(nativeTabCount
    ? await nativeTabs.allTextContents()
    : await root.locator('[data-canonical-node-kind="page"][data-group-title]').evaluateAll((nodes) => (
      nodes.map((node) => node.getAttribute('data-group-title') || '')
    )));
  if (nativeTabCount) {
    for (const label of tabs) {
      await nativeTabs.filter({ hasText: label }).first().click();
    }
  }
  const structure = await root.evaluate((driver) => {
    const root = driver;
    const text = (selector) => [...root.querySelectorAll(selector)].map((node) => String(node.textContent || '').replace(/\s+/g, ' ').trim()).filter(Boolean);
    return {
      presentation: root.querySelector('[data-object-task-page]') ? 'task' : 'workspace',
      floorplanRegions: [...root.querySelectorAll('[data-floorplan-region]')].map((node) => node.getAttribute('data-floorplan-region')).filter(Boolean),
      groups: [...root.querySelectorAll('[data-group-title]')].map((node) => node.getAttribute('data-group-title')).filter(Boolean),
      fields: [...root.querySelectorAll('[data-field-name]')].map((node) => node.getAttribute('data-field-name')).filter(Boolean),
      smartActions: text('.native-actions--smart button, [data-floorplan-region="relation"] button[data-action-key]'),
      x2manyColumns: text('.o2m-header-cell, .o2m-field .meta, th'),
    };
  });
  return {
    ...structure,
    tabs,
    headerActions: unique(await page.locator(
      '.contract-form-command-bar button[data-action-key], [data-canonical-action-bar] button[data-action-key]',
    ).allTextContents()),
    statusbar: unique(await page.locator(
      'button[aria-label^="第 "][aria-label*="步，共"], .native-statusbar-summary',
    ).allTextContents()),
  };
}

async function locateCollectionRecord(page, id, name) {
  const byIdentity = page.locator(`[data-record-key="${id}"]`).first();
  const byText = page.locator('tbody tr').filter({ hasText: String(name || '') }).first();
  for (let pageIndex = 0; pageIndex < 50; pageIndex += 1) {
    const pagination = page.locator('[data-semantic-component="CollectionPaginationFooter"]').first();
    await pagination.waitFor({ state: 'visible', timeout: 45000 });
    await page.waitForFunction(() => (
      document.querySelector('[data-semantic-component="CollectionPaginationFooter"]')?.getAttribute('data-state') === 'ready'
    ), null, { timeout: 45000 });
    if (await byIdentity.isVisible().catch(() => false)) return byIdentity;
    if (await byText.isVisible().catch(() => false)) return byText;
    const expandAll = page.getByRole('button', { name: '全部展开', exact: true }).first();
    if (await expandAll.isVisible().catch(() => false) && await expandAll.isEnabled().catch(() => false)) {
      await expandAll.click();
      if (await byIdentity.isVisible().catch(() => false)) return byIdentity;
      if (await byText.isVisible().catch(() => false)) return byText;
    }
    const nextPage = pagination.locator('.t-pagination__btn-next').first();
    const nextPageClass = await nextPage.getAttribute('class').catch(() => '');
    const nextPageDisabled = await nextPage.getAttribute('disabled').catch(() => null);
    const nextPageAriaDisabled = await nextPage.getAttribute('aria-disabled').catch(() => null);
    if (
      !await nextPage.isVisible().catch(() => false)
      || !await nextPage.isEnabled().catch(() => false)
      || nextPageDisabled !== null
      || nextPageAriaDisabled === 'true'
      || String(nextPageClass || '').includes('t-is-disabled')
    ) break;
    const rowSignature = normalize(await page.locator('tbody tr:visible').first().innerText().catch(() => ''));
    const listResponse = page.waitForResponse((response) => {
      if (!response.url().includes('/api/v1/intent') || response.request().method() !== 'POST') return false;
      try {
        const payload = JSON.parse(response.request().postData() || '{}');
        return payload?.intent === 'api.data' && payload?.params?.op === 'list';
      } catch {
        return false;
      }
    }, { timeout: 45000 });
    await nextPage.click();
    await listResponse;
    await page.waitForFunction((previousRowSignature) => {
      const footer = document.querySelector('[data-semantic-component="CollectionPaginationFooter"]');
      const visibleRow = [...document.querySelectorAll('tbody tr')].find((row) => {
        const style = window.getComputedStyle(row);
        return style.visibility !== 'hidden' && style.display !== 'none' && row.getClientRects().length > 0;
      });
      const currentRowSignature = String(visibleRow?.textContent || '').replace(/\s+/g, ' ').trim();
      return footer?.getAttribute('data-state') === 'ready'
        && Boolean(currentRowSignature)
        && currentRowSignature !== previousRowSignature;
    }, rowSignature, { timeout: 45000 });
  }
  throw new Error(`governed record ${id}/${String(name || '')} is not reachable through collection pagination`);
}

function missing(nativeValues, customValues) {
  const custom = new Set(unique(customValues));
  return unique(nativeValues).filter((value) => !custom.has(value));
}

function collectContractStrings(value, strings = new Set()) {
  if (typeof value === 'string') {
    const normalized = normalize(value);
    if (normalized) strings.add(normalized);
    return strings;
  }
  if (Array.isArray(value)) {
    value.forEach((item) => collectContractStrings(item, strings));
    return strings;
  }
  if (value && typeof value === 'object') {
    Object.values(value).forEach((item) => collectContractStrings(item, strings));
  }
  return strings;
}

function missingContractSemantics(nativeValues, contractStrings) {
  return unique(nativeValues).filter((value) => !contractStrings.has(value));
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
  await customPage.goto(`${frontendUrl}/a/${actionId}?menu_id=${menuId}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await customPage.locator('[data-product-page-mode="list"]').first().waitFor({ timeout: 45000 });
  const targetRow = await locateCollectionRecord(customPage, recordId, target.record.name);
  await targetRow.click();
  await customPage.waitForURL((url) => (
    url.pathname === `/f/${model}/${recordId}`
    && url.searchParams.get('action_id') === String(actionId)
    && url.searchParams.get('menu_id') === String(menuId)
    && Number(url.searchParams.get('list_offset') || -1) >= 0
  ), { timeout: 45000 });
  report.custom = await collectCustom(customPage);
  await customPage.screenshot({ path: path.join(outputDir, 'custom-payment-request.png'), fullPage: true });
  await customContext.close();

  report.projectionGaps = {
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
  const formContract = contractBodies.at(-1);
  check(formContract, 'form ui.contract.v2 response was not observed');
  const contractStrings = collectContractStrings(formContract);
  report.gaps = {
    tabs: missingContractSemantics(report.native.tabs, contractStrings),
    groups: missingContractSemantics(report.native.groups, contractStrings),
    fields: missingContractSemantics(report.native.fields, contractStrings),
    headerActions: missingContractSemantics(report.native.headerActions, contractStrings),
    smartActions: missingContractSemantics(report.native.smartActions, contractStrings),
    x2manyColumns: missingContractSemantics(report.native.x2manyColumns, contractStrings),
    statusbar: missingContractSemantics(report.native.statusbar, contractStrings),
  };
  report.contractSemanticEvidence = {
    stringCount: contractStrings.size,
    presentation: report.custom.presentation,
    renderedFieldCount: unique(report.custom.fields).length,
    floorplanRegions: unique(report.custom.floorplanRegions || []),
  };
  report.errors = errors;
  report.blockedMutations = blockedMutations;
  report.pass = Object.values(report.gaps).every((rows) => rows.length === 0)
    && ['task', 'workspace'].includes(report.custom.presentation)
    && unique(report.custom.fields).length > 0
    && (report.custom.presentation !== 'task' || unique(report.custom.floorplanRegions || []).length > 0)
    && errors.length === 0
    && blockedMutations.length === 0;
  fs.writeFileSync(path.join(outputDir, 'summary.json'), `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({ pass: report.pass, gaps: report.gaps, errors, blockedMutations }, null, 2));
  check(report.pass, 'payment request native/custom structure parity failed', report.gaps);
} catch (error) {
  report.errors = errors;
  report.blockedMutations = blockedMutations;
  report.failure = error instanceof Error ? error.message : String(error);
  const pages = browser.contexts().flatMap((context) => context.pages());
  const activePage = pages.at(-1);
  if (activePage) {
    report.failureSurface = {
      url: activePage.url(),
      visibleRows: await activePage.locator('tbody tr:visible').allTextContents().catch(() => []),
      groups: await activePage.locator('[data-group-key]').evaluateAll((nodes) => nodes.map((node) => ({
        key: node.getAttribute('data-group-key') || '',
        state: node.getAttribute('data-group-state') || '',
      }))).catch(() => []),
      pagination: await activePage.locator('[data-semantic-component="CollectionPaginationFooter"]').evaluateAll((nodes) => nodes.map((node) => ({
        mode: node.getAttribute('data-pagination-mode') || '',
        state: node.getAttribute('data-state') || '',
        text: String(node.textContent || '').replace(/\s+/g, ' ').trim(),
        buttons: [...node.querySelectorAll('button')].map((button) => ({
          text: String(button.textContent || '').replace(/\s+/g, ' ').trim(),
          className: button.className,
          disabled: button.disabled,
          ariaLabel: button.getAttribute('aria-label') || '',
          title: button.getAttribute('title') || '',
        })),
      }))).catch(() => []),
    };
    await activePage.screenshot({ path: path.join(outputDir, 'failure.png'), fullPage: true }).catch(() => {});
  }
  fs.writeFileSync(path.join(outputDir, 'summary.json'), `${JSON.stringify(report, null, 2)}\n`);
  throw error;
} finally {
  await browser.close();
}
