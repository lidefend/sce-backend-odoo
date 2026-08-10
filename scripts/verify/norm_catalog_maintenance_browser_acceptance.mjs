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
const catalogActionId = Number(process.env.NORM_CATALOG_ACTION_ID || 0);
const catalogMenuId = Number(process.env.NORM_CATALOG_MENU_ID || 0);
const regionActionId = Number(process.env.NORM_REGION_ACTION_ID || 0);
const regionMenuId = Number(process.env.NORM_REGION_MENU_ID || 0);
const artifactDir = process.env.ARTIFACT_DIR || '/tmp/norm-catalog-maintenance';

if (!db || !password || !catalogActionId || !regionActionId) throw new Error('database, credential and action ids are required');
fs.mkdirSync(artifactDir, { recursive: true });
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1680, height: 960 } });
const failures = [];
page.on('response', (response) => { if (response.status() >= 400) failures.push(`${response.status()} ${response.url()}`); });
try {
  await page.goto(`${baseUrl}/login?db=${encodeURIComponent(db)}`, { waitUntil: 'networkidle', timeout: 45000 });
  await page.locator('input[autocomplete="username"]').fill(login);
  await page.locator('input[autocomplete="current-password"]').fill(password);
  const dbInput = page.locator('input[autocomplete="off"]');
  if (await dbInput.isEditable().catch(() => false)) await dbInput.fill(db);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForFunction(() => !window.location.pathname.includes('/login'), null, { timeout: 45000 });

  await page.goto(`${baseUrl}/a/${catalogActionId}?menu_id=${catalogMenuId}`, { waitUntil: 'networkidle', timeout: 45000 });
  const catalogTable = page.locator('tbody');
  await catalogTable.getByText('四川省2015版建设工程预算定额', { exact: true }).waitFor({ timeout: 30000 });
  await catalogTable.getByText('2015', { exact: true }).waitFor();
  await catalogTable.getByText('2015版', { exact: true }).waitFor();
  await page.screenshot({ path: path.join(artifactDir, 'catalog-version-list.png'), fullPage: true });
  await page.getByRole('button', { name: '新建', exact: true }).click();
  await page.waitForURL(/\/f\/sc\.norm\.catalog\/new(?:\?|$)/, { timeout: 30000 });
  await page.getByText('填写业务信息', { exact: true }).waitFor({ timeout: 30000 });
  const createFormText = await page.locator('body').innerText();
  for (const label of ['定额库编码', '定额库名称', '适用地区', '发布年份', '版本号', '定额类型']) {
    if (!createFormText.includes(label)) throw new Error(`catalog create form misses ${label}`);
  }
  const hasCnyDefault = await page.locator('input').evaluateAll((inputs) => inputs.some((input) => input.value === 'CNY'));
  if (!hasCnyDefault) throw new Error('catalog create form currency default is not CNY');
  await page.screenshot({ path: path.join(artifactDir, 'catalog-version-create.png'), fullPage: true });

  await page.goto(`${baseUrl}/a/${catalogActionId}?menu_id=${catalogMenuId}`, { waitUntil: 'networkidle', timeout: 45000 });
  await page.locator('tbody').getByText('四川省2015版建设工程预算定额', { exact: true }).click();
  await page.waitForURL(/\/(?:f|r)\/sc\.norm\.catalog\/\d+(?:\?|$)/, { timeout: 30000 });
  await page.getByText('查看', { exact: true }).waitFor({ timeout: 30000 });
  const detailText = await page.locator('body').innerText();
  for (const value of ['草稿', '启用', '归档', 'CNY']) {
    if (!detailText.includes(value)) throw new Error(`catalog detail misses ${value}`);
  }
  await page.screenshot({ path: path.join(artifactDir, 'catalog-version-detail.png'), fullPage: true });

  await page.goto(`${baseUrl}/a/${regionActionId}?menu_id=${regionMenuId}`, { waitUntil: 'networkidle', timeout: 45000 });
  await page.locator('tbody').getByText('四川省', { exact: true }).waitFor({ timeout: 30000 });
  await page.screenshot({ path: path.join(artifactDir, 'region-list.png'), fullPage: true });
  if (failures.length) throw new Error(`failed responses: ${failures.join(' | ')}`);
  process.stdout.write(JSON.stringify({ ok: true, artifactDir }) + '\n');
} catch (error) {
  await page.screenshot({ path: path.join(artifactDir, 'acceptance-failure.png'), fullPage: true }).catch(() => {});
  process.stderr.write(JSON.stringify({ url: page.url(), failures, body: (await page.locator('body').innerText().catch(() => '')).slice(0, 4000) }, null, 2) + '\n');
  throw error;
} finally {
  await browser.close();
}
