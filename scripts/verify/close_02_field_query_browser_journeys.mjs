#!/usr/bin/env node
'use strict';

import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';

const FRONTEND_URL = String(process.env.SC_CLOSE_02_FRONTEND_URL || 'http://127.0.0.1:5175').replace(/\/+$/, '');
const DATABASE = String(process.env.SC_CLOSE_02_DB || 'sc_frontend_acceptance');
const LOGIN = String(process.env.SC_CLOSE_02_LOGIN || 'fixture_role_config_admin');
const PASSWORD = String(process.env.SC_CLOSE_02_PASSWORD || '');
const OUTPUT_DIR = path.resolve(String(
  process.env.SC_CLOSE_02_BROWSER_OUTPUT
    || '.runtime/agent-runs/CLOSE-02-FIELD-QUERY-SORT-DETAIL-20261118/browser_journeys',
));
const SAMPLE_SUMMARY = path.resolve(String(
  process.env.SC_CLOSE_02_SAMPLE_SUMMARY
    || '.runtime/agent-runs/CLOSE-02-FIELD-QUERY-SORT-DETAIL-20261118/search_contract_samples/summary.json',
));

const ENTRIES = [
  {
    key: 'project_ledger',
    label: '项目台账',
    model: 'project.project',
    menuId: 382,
    actionId: 590,
    filterKey: 'filter_operation_direct',
  },
  {
    key: 'payment_request',
    label: '付款申请',
    model: 'payment.request',
    menuId: 560,
    actionId: 881,
    filterKey: 'type_pay',
  },
];

function check(condition, message, detail = undefined) {
  if (condition) return;
  throw new Error(`${message}${detail === undefined ? '' : ` ${JSON.stringify(detail)}`}`);
}

function normalize(value) {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

function writeJson(name, value) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  fs.writeFileSync(path.join(OUTPUT_DIR, name), `${JSON.stringify(value, null, 2)}\n`, 'utf8');
}

function listPayload(request) {
  try {
    const payload = JSON.parse(request.postData() || '{}');
    return payload?.intent === 'api.data' && payload?.params?.op === 'list' ? payload : null;
  } catch {
    return null;
  }
}

async function login(page) {
  await page.goto(`${FRONTEND_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const inputs = page.locator('input');
  await inputs.nth(0).fill(LOGIN);
  await inputs.nth(1).fill(PASSWORD);
  if (await inputs.nth(2).count()) {
    if (!(await inputs.nth(2).isDisabled())) await inputs.nth(2).fill(DATABASE);
  }
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45000 });
}

async function chooseSelectOption(page, panel, index, label) {
  const select = panel.locator('[data-semantic-component="ScSelect"]').nth(index);
  await select.click();
  const option = page.getByText(label, { exact: true }).last();
  await option.waitFor({ state: 'visible', timeout: 15000 });
  await option.click();
}

async function waitForList(page, action) {
  const response = page.waitForResponse((candidate) => (
    candidate.url().includes('/api/v1/intent')
    && candidate.request().method() === 'POST'
    && Boolean(listPayload(candidate.request()))
  ), { timeout: 45000 });
  await action();
  const result = await response;
  const body = await result.json();
  const data = body?.data && typeof body.data === 'object' ? body.data : body?.result || {};
  return {
    status: result.status(),
    request: listPayload(result.request()),
    body,
    records: Array.isArray(data.records) ? data.records : [],
    total: Number(data.total || 0),
    meta: body?.meta || {},
  };
}

async function waitForListReady(page) {
  const footer = page.locator('[data-semantic-component="CollectionPaginationFooter"]').first();
  await footer.waitFor({ state: 'visible', timeout: 45000 });
  await page.waitForFunction(() => (
    document.querySelector('[data-semantic-component="CollectionPaginationFooter"]')
      ?.getAttribute('data-state') === 'ready'
  ), null, { timeout: 45000 });
  return footer;
}

async function openCustomFilter(page) {
  const toggle = page.getByRole('button', { name: /展开搜索菜单/ }).first();
  await toggle.click();
  const entry = page.locator('#collection-search-disclosure .custom-entry').first();
  await entry.waitFor({ state: 'visible', timeout: 15000 });
  if (!(await page.locator('.custom-search-panel').isVisible().catch(() => false))) await entry.click();
  const panel = page.locator('.custom-search-panel').first();
  await panel.waitFor({ state: 'visible', timeout: 15000 });
  return panel;
}

async function applyFieldFilter(page, field, value, label) {
  const panel = await openCustomFilter(page);
  await chooseSelectOption(page, panel, 0, label);
  const valueInput = panel.locator('input').last();
  await valueInput.fill(String(value));
  const applied = await waitForList(page, async () => {
    await panel.locator('.custom-search-actions button').first().click();
  });
  await page.waitForURL((url) => Boolean(url.searchParams.get('field_filter')), { timeout: 30000 });
  return applied;
}

async function applyExistingFilter(page, label) {
  const toggle = page.getByRole('button', { name: /展开搜索菜单/ }).first();
  await toggle.click();
  const button = page.locator('#collection-search-disclosure button').filter({ hasText: label }).first();
  await button.waitFor({ state: 'visible', timeout: 15000 });
  return await waitForList(page, async () => {
    await button.click();
  });
}

async function goNextPage(page, footer) {
  const next = footer.getByRole('listitem').filter({ hasText: /^2$/ }).first();
  check(await next.isVisible(), 'pagination page two is missing');
  const pageTwo = await waitForList(page, async () => {
    await next.click();
  });
  await page.waitForURL((url) => Number(url.searchParams.get('list_offset') || 0) > 0, { timeout: 30000 });
  return pageTwo;
}

async function runEntry(browser, declaration, sample) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
  const page = await context.newPage();
  const errors = [];
  const requests = [];
  let contract = null;
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error' && !message.text().includes('favicon')) errors.push(message.text());
  });
  page.on('request', (request) => {
    const payload = listPayload(request);
    if (payload) requests.push(payload);
  });
  page.on('response', async (response) => {
    if (!response.url().includes('/api/v1/intent') || response.request().method() !== 'POST') return;
    try {
      const payload = JSON.parse(response.request().postData() || '{}');
      if (payload.intent !== 'ui.contract.v2') return;
      const body = await response.json();
      const data = body?.data && typeof body.data === 'object' ? body.data : null;
      if (data?.searchContract && data?.dataContract?.dataSource?.primary) contract = data;
    } catch {
      // A failed or non-contract response is handled by the journey assertions.
    }
  });

  try {
    await login(page);
    await page.goto(`${FRONTEND_URL}/a/${declaration.actionId}?menu_id=${declaration.menuId}`, {
      waitUntil: 'domcontentloaded',
      timeout: 45000,
    });
    await page.locator('[data-product-page-mode="list"]').first().waitFor({ timeout: 45000 });
    let footer = await waitForListReady(page);
    check(contract, `${declaration.key}: ui.contract.v2 was not observed`);
    const fields = contract.searchContract.fields || [];
    const textField = fields.find((row) => ['char', 'text', 'html'].includes(String(row.type)));
    const relationField = fields.find((row) => row.type === 'many2one');
    check(textField && relationField, `${declaration.key}: native text/relation fields missing`);
    const filter = (contract.searchContract.filters || []).find((row) => row.key === declaration.filterKey);
    check(filter, `${declaration.key}: declared existing filter missing`, declaration.filterKey);
    const relationValue = sample.samples.relation_hit.value;

    const textResult = await applyFieldFilter(page, textField, 'F', textField.label);
    check(textResult.total > 20, `${declaration.key}: text query did not exceed one page`, textResult.total);
    check(new URL(page.url()).searchParams.get('list_offset') === null, `${declaration.key}: text query retained old page`);
    const filterResult = await applyExistingFilter(page, filter.label);
    check(filterResult.total > 20, `${declaration.key}: existing filter did not exceed one page`, filterResult.total);
    footer = await waitForListReady(page);
    const pageTwo = await goNextPage(page, footer);
    check(pageTwo.records.length > 0, `${declaration.key}: second page is empty`);
    const confirmedUrl = page.url();
    const confirmedFieldFilter = new URL(confirmedUrl).searchParams.get('field_filter');
    check(Boolean(confirmedFieldFilter), `${declaration.key}: field_filter missing on second page`);

    const row = page.locator('tbody tr:visible').first();
    await row.waitFor({ state: 'visible', timeout: 15000 });
    const recordKey = String(await row.getAttribute('data-record-key') || '');
    await row.locator('td').nth(1).click();
    await page.waitForURL((url) => url.pathname.includes(`/${declaration.model}/`) && url.pathname !== '/login', {
      timeout: 45000,
    });
    const detailUrl = page.url();
    await page.goBack({ waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForURL((url) => url.href === confirmedUrl, { timeout: 45000 });
    footer = await waitForListReady(page);
    check(normalize(await page.locator('.search-facet').allTextContents().then((rows) => rows.join(' '))).includes(
      normalize(textField.label).slice(0, 6),
    ), `${declaration.key}: field-filter chip was not restored from detail`);
    check(Number(new URL(page.url()).searchParams.get('list_offset') || 0) > 0, `${declaration.key}: detail return lost page`);

    const relationResult = await applyFieldFilter(page, relationField, relationValue, relationField.label);
    check(relationResult.total > 20, `${declaration.key}: relation query did not exceed one page`, relationResult.total);
    const resetUrl = new URL(page.url());
    check(!resetUrl.searchParams.has('list_offset'), `${declaration.key}: changed query retained URL page`);
    check(relationResult.request?.params?.offset === 0, `${declaration.key}: changed query request offset is not zero`, relationResult.request);

    await page.reload({ waitUntil: 'domcontentloaded', timeout: 45000 });
    await waitForListReady(page);
    check(new URL(page.url()).searchParams.get('field_filter') === resetUrl.searchParams.get('field_filter'), (
      `${declaration.key}: field filter was not restored after reload`
    ));
    check(
      normalize(await page.locator('.search-facet').allTextContents().then((rows) => rows.join(' '))).includes(
        normalize(relationField.label).slice(0, 6),
      ),
      `${declaration.key}: relation-filter chip was not restored after reload`,
    );

    const customChip = page.locator('.search-facet').filter({ hasText: relationField.label }).first();
    const cleared = await waitForList(page, async () => customChip.click());
    const clearedUrl = new URL(page.url());
    check(!clearedUrl.searchParams.has('field_filter'), `${declaration.key}: clearing condition retained field_filter`);
    check(!clearedUrl.searchParams.has('list_offset'), `${declaration.key}: clearing condition retained URL page`);
    check(cleared.request?.params?.offset === 0, `${declaration.key}: clearing condition request offset is not zero`);
    check(cleared.total > 20, `${declaration.key}: entry base scope disappeared after clearing`, cleared.total);
    check(errors.length === 0, `${declaration.key}: browser errors observed`, errors);

    const artifact = {
      entry: declaration.key,
      label: declaration.label,
      model: declaration.model,
      menu_id: declaration.menuId,
      action_id: declaration.actionId,
      text_field: textField.field,
      relation_field: relationField.field,
      relation_value: relationValue,
      exists_filter: declaredFilterKey(filter),
      text_total: textResult.total,
      filter_total: filterResult.total,
      second_page_total: pageTwo.total,
      second_page_records: pageTwo.records.length,
      detail_url: detailUrl,
      confirmed_list_url: confirmedUrl,
      reset_url: page.url(),
      request_offsets: requests.map((payload) => Number(payload?.params?.offset || 0)),
      errors,
    };
    writeJson(`${declaration.key}.json`, artifact);
    return artifact;
  } finally {
    await context.close();
  }
}

function declaredFilterKey(row) {
  return String(row?.key || '').trim();
}

function readSamples() {
  const body = JSON.parse(fs.readFileSync(SAMPLE_SUMMARY, 'utf8'));
  check(body?.summary?.status === 'PASS', 'backend sample summary did not pass');
  return new Map((body.entries || []).map((entry) => [entry.key, entry]));
}

async function main() {
  check(PASSWORD, 'SC_CLOSE_02_PASSWORD is required');
  fs.rmSync(OUTPUT_DIR, { recursive: true, force: true });
  const samples = readSamples();
  const browser = await launchChromium({ headless: true });
  const results = [];
  try {
    for (const entry of ENTRIES) {
      const sample = samples.get(entry.key);
      check(sample, `missing backend sample for ${entry.key}`);
      results.push(await runEntry(browser, entry, sample));
    }
  } finally {
    await browser.close();
  }
  writeJson('summary.json', {
    schema: 'close_02.field_query_browser_journeys.v1',
    status: 'PASS',
    frontend_url: FRONTEND_URL,
    database: DATABASE,
    login: LOGIN,
    entries: results,
  });
  process.stdout.write(`[close-02-browser] PASS entries=${results.length}\n`);
}

main().catch((error) => {
  process.stderr.write(`[close-02-browser] FAIL ${error?.message || error}\n`);
  process.exitCode = 1;
});
