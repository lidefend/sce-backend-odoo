#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';

const baseUrl = String(process.env.FRONTEND_URL || 'http://127.0.0.1:18083').replace(/\/$/, '');
const database = process.env.DB_NAME || 'sc_clean';
const loginName = process.env.E2E_LOGIN || 'sc_clean_acceptance';
const password = String(process.env.E2E_PASSWORD || '');
const outputDir = process.env.ARTIFACTS_DIR || 'artifacts/target-cost-entry-browser';
const entryRoute = process.env.TARGET_COST_ENTRY_ROUTE || [
  '/a/520?product_domain=cost_budget',
  'entry_intent=handling',
  'disposition_policy=keep_list_form',
  'integration_target=project.budget+%E7%9B%AE%E6%A0%87%E6%88%90%E6%9C%AC',
  'entry_target_policy=keep_list_form',
  'business_entry_contract_version=business_entry_disposition.v1',
  'menu_id=396',
  'action_id=520',
].join('&');

function check(value, reason) {
  if (!value) throw new Error(reason);
}

async function login(page) {
  await page.goto(`${baseUrl}/login`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  const inputs = page.locator('input');
  await inputs.nth(0).fill(loginName);
  await inputs.nth(1).fill(password);
  if (await inputs.nth(2).isEnabled().catch(() => false)) {
    await inputs.nth(2).fill(database);
  } else {
    check(await inputs.nth(2).inputValue() === database, 'LOGIN_DATABASE_MISMATCH');
  }
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45_000 });
  await page.locator('.layout-shell').waitFor({ timeout: 45_000 });
}

async function main() {
  check(password, 'E2E_PASSWORD_REQUIRED');
  fs.mkdirSync(outputDir, { recursive: true });
  const browser = await launchChromium({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'zh-CN' });
  const page = await context.newPage();
  const runtime = { pageErrors: [], consoleErrors: [], httpErrors: [] };
  page.on('pageerror', (error) => runtime.pageErrors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') runtime.consoleErrors.push(message.text());
  });
  page.on('response', (response) => {
    if (response.status() >= 400) runtime.httpErrors.push({ status: response.status(), url: response.url() });
  });

  try {
    await login(page);
    await page.goto(`${baseUrl}${entryRoute}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
    try {
      await page.locator('[data-product-page-mode="list"]').first().waitFor({ timeout: 45_000 });
    } catch (error) {
      const failureScreenshot = path.join(outputDir, '00-entry-list-unavailable.png');
      await page.screenshot({ path: failureScreenshot, fullPage: true });
      const body = (await page.locator('body').innerText()).replace(/\s+/g, ' ').slice(0, 2400);
      throw new Error(`TARGET_COST_LIST_UNAVAILABLE:url=${page.url()}:body=${body}; ${error.message}`);
    }
    await page.waitForFunction(() => {
      const text = document.body.innerText || '';
      return Boolean(document.querySelector('table tbody tr, .desktop-record-table tbody tr'))
        && !/加载中|正在载入数据|正在加载列表|正在加载/.test(text);
    }, undefined, { timeout: 45_000 });

    const listText = await page.locator('body').innerText();
    for (const expected of ['目标成本计划', '消防站项目目标成本计划 V5', 'V5-20260810']) {
      check(listText.includes(expected), `TARGET_COST_LIST_FACT_MISSING:${expected}`);
    }
    const listScreenshot = path.join(outputDir, '01-target-cost-list-action-520-menu-396.png');
    await page.screenshot({ path: listScreenshot, fullPage: true, animations: 'disabled' });

    const row = page.locator('.desktop-record-table tbody tr, table tbody tr')
      .filter({ hasText: '消防站项目目标成本计划 V5' }).first();
    await row.click();
    await page.waitForURL((url) => /\/(?:f|r)\/project\.cost\.plan\/21(?:\?|$)/.test(url.pathname + url.search), { timeout: 45_000 });
    await page.locator('[data-product-page-mode="form"]').first().waitFor({ timeout: 45_000 });
    await page.locator('.product-form-loading').waitFor({ state: 'detached', timeout: 45_000 });
    const formScreenshot = path.join(outputDir, '02-target-cost-plan-v5-form.png');
    await page.screenshot({ path: formScreenshot, fullPage: true, animations: 'disabled' });

    const fieldValue = async (fieldName) => {
      const field = page.locator(`[data-field-name="${fieldName}"]`).first();
      const input = field.locator('input').first();
      if (await input.count()) return input.inputValue();
      return (await field.count()) ? field.innerText() : '';
    };
    const formText = await page.locator('body').innerText();
    const formFacts = {
      name: (await fieldValue('name')) || (formText.includes('消防站项目目标成本计划 V5') ? '消防站项目目标成本计划 V5' : ''),
      versionCode: await fieldValue('version_code'),
      lineCount: await fieldValue('line_count'),
    };
    if (!formFacts.name || !formFacts.versionCode || !formFacts.lineCount) {
      const body = (await page.locator('body').innerText()).replace(/\s+/g, ' ').slice(0, 2400);
      throw new Error(`TARGET_COST_FORM_FIELDS_MISSING:url=${page.url()}:facts=${JSON.stringify(formFacts)}:body=${body}`);
    }
    check(formFacts.name.includes('消防站项目目标成本计划 V5'), `TARGET_COST_FORM_NAME_INVALID:${formFacts.name}`);
    check(formFacts.versionCode === 'V5-20260810', `TARGET_COST_FORM_VERSION_INVALID:${formFacts.versionCode}`);
    check(formFacts.lineCount.replace(/\D/g, '') === '7441', `TARGET_COST_FORM_LINE_COUNT_INVALID:${formFacts.lineCount}`);
    check(formText.includes('29,922,323.10'), 'TARGET_COST_FORM_AMOUNT_MISSING');
    check(page.url().includes('/project.cost.plan/21'), `TARGET_COST_FORM_MODEL_INVALID:${page.url()}`);

    check(runtime.pageErrors.length === 0, `PAGE_ERRORS:${JSON.stringify(runtime.pageErrors)}`);
    check(runtime.consoleErrors.length === 0, `CONSOLE_ERRORS:${JSON.stringify(runtime.consoleErrors)}`);
    check(runtime.httpErrors.length === 0, `HTTP_ERRORS:${JSON.stringify(runtime.httpErrors)}`);

    const result = {
      status: 'PASS',
      database,
      login: loginName,
      entry: { actionId: 520, menuId: 396, model: 'project.cost.plan' },
      plan: { id: 21, versionCode: formFacts.versionCode, lineCount: Number(formFacts.lineCount.replace(/\D/g, '')), targetAmount: 29922323.10 },
      screenshots: { list: listScreenshot, form: formScreenshot },
      runtime,
    };
    fs.writeFileSync(path.join(outputDir, 'result.json'), `${JSON.stringify(result, null, 2)}\n`);
    console.log(`TARGET_COST_ENTRY_BROWSER=PASS ${JSON.stringify(result)}`);
  } finally {
    await context.close();
    await browser.close();
  }
}

main().catch((error) => {
  console.error(`TARGET_COST_ENTRY_BROWSER=FAIL ${error.stack || error.message}`);
  process.exitCode = 2;
});
