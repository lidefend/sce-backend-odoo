#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const require = createRequire(path.join(process.cwd(), 'frontend/apps/web/package.json'));
const { chromium } = require('playwright');
const baseUrl = String(process.env.FRONTEND_URL || 'http://127.0.0.1:18081').replace(/\/$/, '');
const db = process.env.DB_NAME || '';
const login = process.env.E2E_LOGIN || 'wutao';
const password = process.env.E2E_PASSWORD || '';
const actionId = Number(process.env.NORM_ACTION_ID || 0);
const menuId = Number(process.env.NORM_MENU_ID || 0);
const artifactDir = process.env.ARTIFACT_DIR || '/tmp/norm-engine-browser-acceptance';
const importFixture = process.env.NORM_IMPORT_FIXTURE || '';
const expectedSpecialties = Number(process.env.NORM_EXPECTED_SPECIALTIES || 1);
const expectedChapters = Number(process.env.NORM_EXPECTED_CHAPTERS || 3);
const expectedItems = Number(process.env.NORM_EXPECTED_ITEMS || 8);
const filterNodeName = process.env.NORM_FILTER_NODE_NAME || 'A.A 土石方工程';
const expectedFilterCount = Number(process.env.NORM_EXPECTED_FILTER_COUNT || 3);
const expectedExistingText = process.env.NORM_EXPECTED_EXISTING_TEXT || '人工挖沟槽土方';
const deepFilterPath = String(process.env.NORM_DEEP_FILTER_PATH || '').split('>').map((value) => value.trim()).filter(Boolean);
const expectedDeepFilterCount = Number(process.env.NORM_EXPECTED_DEEP_FILTER_COUNT || 0);
const searchCode = process.env.NORM_SEARCH_CODE || '';
const expectedResultFragment = process.env.NORM_EXPECTED_RESULT_FRAGMENT || '';
const expectedTotalCount = Number(process.env.NORM_EXPECTED_TOTAL_COUNT || expectedItems);
const workbenchTitle = process.env.NORM_WORKBENCH_TITLE || '定额库';
const filterRevealPath = String(process.env.NORM_FILTER_REVEAL_PATH || '').split('>').map((value) => value.trim()).filter(Boolean);
const confirmImport = String(process.env.NORM_IMPORT_CONFIRM || '1') !== '0';

if (!db || !password || !actionId) throw new Error('DB_NAME, E2E_PASSWORD and NORM_ACTION_ID are required');
fs.mkdirSync(artifactDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1680, height: 960 }, deviceScaleFactor: 1 });
const consoleErrors = [];
const failedResponses = [];
const failedResponseDetails = [];
const contractCaptures = [];
page.on('console', (message) => { if (message.type() === 'error') consoleErrors.push(message.text()); });
page.on('pageerror', (error) => consoleErrors.push(error.message));
page.on('response', (response) => {
  if (response.status() < 400) return;
  failedResponses.push(`${response.status()} ${response.url()}`);
  failedResponseDetails.push(response.text().then((body) => ({
    status: response.status(),
    url: response.url(),
    request: response.request().postDataJSON(),
    body,
  })).catch(() => ({ status: response.status(), url: response.url() })));
});
page.on('response', (response) => {
  const request = response.request();
  const postData = request.postData() || '';
  if (!postData.includes('ui.contract.v2')) return;
  contractCaptures.push(response.json().then((body) => ({ url: response.url(), request: JSON.parse(postData), body })).catch(() => null));
});
try {
  await page.goto(`${baseUrl}/login?db=${encodeURIComponent(db)}`, { waitUntil: 'networkidle', timeout: 45000 });
  await page.locator('input[autocomplete="username"]').fill(login);
  await page.locator('input[autocomplete="current-password"]').fill(password);
  const dbInput = page.locator('input[autocomplete="off"]');
  if (await dbInput.isEditable().catch(() => false)) await dbInput.fill(db);
  await page.getByRole('button', { name: /^登录$/ }).click();
  try {
    await page.waitForFunction(() => !window.location.pathname.includes('/login'), null, { timeout: 45000 });
  } catch (error) {
    await page.screenshot({ path: path.join(artifactDir, 'login-failure.png'), fullPage: true });
    const alert = await page.locator('[role="alert"]').allTextContents().catch(() => []);
    throw new Error(`login did not leave ${page.url()}; alert=${alert.join(' | ')}; cause=${error instanceof Error ? error.message : error}`);
  }
  const query = menuId ? `?menu_id=${menuId}` : '';
  await page.goto(`${baseUrl}/a/${actionId}${query}`, { waitUntil: 'networkidle', timeout: 45000 });
  await page.getByRole('heading', { name: workbenchTitle, level: 2 }).waitFor({ timeout: 30000 });
  const hierarchyBrowser = page.getByLabel('层级数据浏览');
  await hierarchyBrowser.getByRole('button', { name: '全部', exact: true }).waitFor();
  await hierarchyBrowser.getByText('土建与装饰', { exact: true }).first().waitFor();
  await page.getByText(expectedExistingText, { exact: false }).first().waitFor();
  await page.screenshot({ path: path.join(artifactDir, 'norm-library-workbench.png'), fullPage: true });
  for (const pathNode of filterRevealPath) {
    const node = hierarchyBrowser.getByRole('button', { name: new RegExp(pathNode.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')) });
    await node.waitFor();
    await node.locator('.tree-arrow').click();
  }
  await hierarchyBrowser.getByRole('button', { name: new RegExp(filterNodeName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')) }).click();
  await page.getByText(`共 ${expectedFilterCount} 条`, { exact: true }).waitFor();
  await page.screenshot({ path: path.join(artifactDir, 'norm-library-chapter-filter.png'), fullPage: true });
  if (deepFilterPath.length) {
    for (let index = 0; index < deepFilterPath.length; index += 1) {
      const node = hierarchyBrowser.getByRole('button', { name: new RegExp(deepFilterPath[index].replace(/[.*+?^${}()|[\]\\]/g, '\\$&')) });
      await node.waitFor();
      if (index < deepFilterPath.length - 1) await node.locator('.tree-arrow').click();
      else await node.click();
    }
    if (expectedDeepFilterCount) await page.getByText(`共 ${expectedDeepFilterCount} 条`, { exact: true }).waitFor();
    await page.screenshot({ path: path.join(artifactDir, 'norm-library-deep-filter.png'), fullPage: true });
  }
  if (searchCode) {
    await hierarchyBrowser.getByRole('button', { name: '全部', exact: true }).click();
    await page.getByText(`共 ${expectedTotalCount} 条`, { exact: true }).waitFor();
    const searchInput = hierarchyBrowser.getByRole('searchbox');
    await searchInput.fill(searchCode);
    await searchInput.press('Enter');
    await hierarchyBrowser.getByText(searchCode, { exact: true }).first().waitFor();
    await page.screenshot({ path: path.join(artifactDir, 'norm-library-search.png'), fullPage: true });
    await searchInput.fill('');
    await searchInput.press('Enter');
  }
  await hierarchyBrowser.getByRole('button', { name: '导入定额', exact: true }).click();
  await page.waitForURL(/\/f\/sc\.norm\.import\.wizard\/new(?:\?|$)/, { timeout: 30000 });
  await page.getByRole('heading', { name: '1. 选择文件', exact: true }).waitFor({ timeout: 30000 });
  await page.screenshot({ path: path.join(artifactDir, 'norm-import-upload.png'), fullPage: true });
  if (importFixture) {
    await page.locator('input[type="file"]').setInputFiles(importFixture);
    await page.getByRole('button', { name: /^(预检|提交)$/ }).click();
    await page.waitForLoadState('networkidle');
    const previewPassed = page.getByText('预检通过，可执行增量更新。', { exact: false });
    let previewReady = true;
    try {
      await previewPassed.waitFor({ timeout: 10000 });
    } catch {
      previewReady = false;
    }
    if (!previewReady) {
      const preflightButton = page.getByRole('button', { name: '预检', exact: true });
      if (await preflightButton.isVisible().catch(() => false)) await preflightButton.click();
    }
    await previewPassed.waitFor({ timeout: 120000 });
    await page.getByText(`专业 ${expectedSpecialties} 个`, { exact: false }).waitFor();
    await page.getByText(`章节 ${expectedChapters} 个`, { exact: false }).waitFor();
    await page.getByText(`定额项 ${expectedItems} 条`, { exact: false }).waitFor();
    await page.screenshot({ path: path.join(artifactDir, 'norm-import-preview.png'), fullPage: true });
    if (confirmImport) {
      await page.getByRole('button', { name: '确认导入', exact: true }).click();
      await page.getByText('导入成功（增量更新）', { exact: false }).waitFor({ timeout: 180000 });
      await page.getByText('定额项：新增', { exact: false }).waitFor();
      if (expectedResultFragment) await page.getByText(expectedResultFragment, { exact: false }).waitFor();
      await page.screenshot({ path: path.join(artifactDir, 'norm-import-result.png'), fullPage: true });
    }
  }
  if (consoleErrors.length) throw new Error(`browser console errors: ${consoleErrors.join(' | ')}`);
  const captures = (await Promise.all(contractCaptures)).filter(Boolean);
  fs.writeFileSync(path.join(artifactDir, 'ui-contract-v2-captures.json'), JSON.stringify(captures, null, 2));
  const screenshots = ['norm-library-workbench.png', 'norm-library-chapter-filter.png', 'norm-import-upload.png'];
  if (importFixture) screenshots.push('norm-import-preview.png');
  if (importFixture && confirmImport) screenshots.push('norm-import-result.png');
  process.stdout.write(JSON.stringify({ ok: true, artifactDir, screenshots }) + '\n');
} catch (error) {
  const captures = (await Promise.all(contractCaptures)).filter(Boolean);
  fs.writeFileSync(path.join(artifactDir, 'ui-contract-v2-captures.json'), JSON.stringify(captures, null, 2));
  await page.screenshot({ path: path.join(artifactDir, 'acceptance-failure.png'), fullPage: true }).catch(() => {});
  const body = await page.locator('body').innerText().catch(() => '');
  process.stderr.write(JSON.stringify({ url: page.url(), failedResponses, failedResponseDetails: await Promise.all(failedResponseDetails), consoleErrors, body: body.slice(0, 3000) }, null, 2) + '\n');
  throw error;
} finally {
  await browser.close();
}
