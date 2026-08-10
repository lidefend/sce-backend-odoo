#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';

const baseUrl = String(process.env.FRONTEND_URL || 'http://127.0.0.1:18083').replace(/\/$/, '');
const database = process.env.DB_NAME || 'sc_clean';
const login = process.env.E2E_LOGIN || 'wutao';
const bootstrapSecret = process.env.SC_ACCEPTANCE_BOOTSTRAP_SECRET || '';
const outputDir = process.env.ARTIFACTS_DIR || 'artifacts/target-cost-tree-browser';

function check(value, reason) {
  if (!value) throw new Error(reason);
}

async function bootstrap(page) {
  check(bootstrapSecret, 'SC_ACCEPTANCE_BOOTSTRAP_SECRET_REQUIRED');
  const response = await page.request.post(`${baseUrl}/api/v1/intent`, {
    data: { intent: 'session.bootstrap', params: { db: database, login } },
    headers: { 'X-Anonymous-Intent': '1', 'X-Bootstrap-Secret': bootstrapSecret, 'X-Odoo-DB': database },
  });
  const envelope = await response.json();
  const token = String(envelope?.data?.token || envelope?.result?.token || '');
  check(response.ok() && token, `BOOTSTRAP_FAILED:${response.status()}:${JSON.stringify(envelope?.error || envelope?.message || envelope?.meta || {})}`);
  await page.goto(`${baseUrl}/login`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  await page.evaluate(({ db, authToken }) => {
    sessionStorage.setItem(`sc_auth_token:${db}`, authToken);
    sessionStorage.setItem('sc_active_db:acceptance', db);
  }, { db: database, authToken: token });
  await page.goto(`${baseUrl}/`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  await page.locator('.layout-shell').waitFor({ timeout: 45_000 });
}

async function main() {
  fs.mkdirSync(outputDir, { recursive: true });
  const browser = await launchChromium({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'zh-CN' });
  const page = await context.newPage();
  const runtime = { pageErrors: [], consoleErrors: [], httpErrors: [], contracts: [] };
  page.on('pageerror', (error) => runtime.pageErrors.push(error.message));
  page.on('console', (message) => { if (message.type() === 'error') runtime.consoleErrors.push(message.text()); });
  page.on('response', async (response) => {
    if (response.status() >= 400) runtime.httpErrors.push({ status: response.status(), url: response.url() });
    if ((response.request().postData() || '').includes('ui.contract.v2')) {
      const payload = await response.json().catch(() => null);
      if (payload) runtime.contracts.push(payload);
    }
  });
  try {
    await bootstrap(page);
    await page.goto(`${baseUrl}/a/520?menu_id=396&action_id=520`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
    await page.locator('[data-product-page-mode="list"]').first().waitFor({ timeout: 45_000 });
    const planRow = page.locator('.desktop-record-table tbody tr, table tbody tr').filter({ hasText: '消防站项目目标成本计划 V5' }).first();
    await planRow.waitFor({ timeout: 45_000 });
    await planRow.click();
    await page.locator('[data-product-page-mode="form"]').waitFor({ timeout: 45_000 });
    let compileButton = page.getByRole('button', { name: '成本编制', exact: true });
    if (!await compileButton.waitFor({ timeout: 3_000 }).then(() => true).catch(() => false)) {
      await page.getByText('更多操作', { exact: true }).first().click();
      compileButton = page.getByRole('button', { name: '成本编制', exact: true });
    }
    if (!await compileButton.waitFor({ timeout: 10_000 }).then(() => true).catch(() => false)) {
      await page.screenshot({ path: path.join(outputDir, '00-plan-form-missing-cost-compile.png'), fullPage: true });
      throw new Error(`COST_COMPILE_ACTION_MISSING:${(await page.locator('body').innerText()).replace(/\s+/g, ' ').slice(0, 1800)}`);
    }
    await compileButton.click();
    if (!await page.locator('.hierarchy-planner:visible').last().waitFor({ timeout: 30_000 }).then(() => true).catch(() => false)) {
      await page.screenshot({ path: path.join(outputDir, '00-after-cost-compile.png'), fullPage: true });
      fs.writeFileSync(path.join(outputDir, '00-contract-debug.json'), `${JSON.stringify(runtime.contracts, null, 2)}\n`);
      throw new Error(`COST_TREE_NOT_OPENED:url=${page.url()}:body=${(await page.locator('body').innerText()).replace(/\s+/g, ' ').slice(0, 1800)}`);
    }
    const plannerSurface = page.locator('.hierarchy-planner:visible').last();
    await plannerSurface.locator('.planner-state').waitFor({ state: 'detached', timeout: 90_000 }).catch(() => {});

    const rows = plannerSurface.locator('.planner-grid tbody tr');
    if (!await rows.first().waitFor({ timeout: 10_000 }).then(() => true).catch(() => false)) {
      await page.screenshot({ path: path.join(outputDir, '00-cost-tree-empty-or-error.png'), fullPage: true });
      fs.writeFileSync(path.join(outputDir, '00-contract-debug.json'), `${JSON.stringify(runtime.contracts, null, 2)}\n`);
      throw new Error(`COST_TREE_ROWS_MISSING:${(await page.locator('body').innerText()).replace(/\s+/g, ' ').slice(0, 1800)}`);
    }
    const initialCount = await rows.count();
    const initialText = await plannerSurface.innerText();
    const initialRows = await rows.allInnerTexts();
    check(initialCount === 8, `DEFAULT_DEPTH_INVALID:${initialCount}:${JSON.stringify(initialRows)}`);
    for (const label of ['人工费', '材料费', '机械费', '管理费', '措施费', '规费', '税金', '其他成本']) {
      check(initialText.includes(label), `DIMENSION_MISSING:${label}`);
    }
    check(initialText.includes('11,699') || initialText.includes('11699'), 'TREE_TOTAL_MISSING');
    const initialScreenshot = path.join(outputDir, '01-cost-dimension-roots.png');
    await page.screenshot({ path: initialScreenshot, fullPage: true, animations: 'disabled' });

    const laborRow = rows.filter({ hasText: '人工费' }).first();
    await laborRow.locator('.outline-toggle').click();
    await page.waitForFunction(() => document.querySelectorAll('.planner-grid tbody tr').length > 8, null, { timeout: 30_000 });
    const boqRow = rows.filter({ hasText: '清单项目' }).first();
    await boqRow.waitFor({ timeout: 30_000 });
    await boqRow.locator('.outline-toggle').click();
    const resourceRow = rows.filter({ hasText: '资源/费用明细' }).first();
    await resourceRow.waitFor({ timeout: 30_000 });
    await resourceRow.click();
    await page.getByRole('button', { name: '节点详情', exact: true }).click();
    await page.locator('.planner-drawer').waitFor({ timeout: 30_000 });
    const drillScreenshot = path.join(outputDir, '02-cost-tree-drilldown.png');
    await page.screenshot({ path: drillScreenshot, fullPage: true, animations: 'disabled' });

    await plannerSurface.locator('.planner-drawer button').filter({ hasText: '×' }).click();
    await page.getByRole('button', { name: '视图', exact: true }).click();
    await page.getByRole('button', { name: '全部折叠', exact: true }).click();
    check(await rows.count() === 8, `COLLAPSE_INVALID:${await rows.count()}`);
    check(runtime.pageErrors.length === 0, `PAGE_ERRORS:${JSON.stringify(runtime.pageErrors)}`);
    check(runtime.consoleErrors.length === 0, `CONSOLE_ERRORS:${JSON.stringify(runtime.consoleErrors)}`);
    check(runtime.httpErrors.length === 0, `HTTP_ERRORS:${JSON.stringify(runtime.httpErrors)}`);
    const runtimeSummary = {
      pageErrors: runtime.pageErrors,
      consoleErrors: runtime.consoleErrors,
      httpErrors: runtime.httpErrors,
    };
    const result = {
      status: 'PASS', database, login, planId: 21, nodeCount: 11699, rootCount: initialCount,
      hierarchy: ['成本维度', '清单项目', '资源/费用明细'],
      screenshots: { initial: initialScreenshot, drilldown: drillScreenshot }, runtime: runtimeSummary,
    };
    fs.writeFileSync(path.join(outputDir, 'result.json'), `${JSON.stringify(result, null, 2)}\n`);
    console.log(`TARGET_COST_TREE_BROWSER=PASS ${JSON.stringify(result)}`);
  } finally {
    await context.close();
    await browser.close();
  }
}

main().catch((error) => {
  console.error(`TARGET_COST_TREE_BROWSER=FAIL ${error.stack || error.message}`);
  process.exitCode = 2;
});
