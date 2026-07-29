#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { launchChromium } from './playwright_runtime.mjs';

const require = createRequire(import.meta.url);
const axeModule = require(require.resolve('@axe-core/playwright', {
  paths: [path.resolve('frontend/apps/web/node_modules')],
}));
const AxeBuilder = axeModule.default || axeModule;

const BASE_URL = process.env.FRONTEND_URL || 'http://127.0.0.1:5175';
const DB_NAME = process.env.DB_NAME || 'sc_frontend_acceptance';
const PASSWORD = process.env.SC_ACCEPTANCE_FIXTURE_PASSWORD || '';
const OUTPUT = process.env.FE_DETAIL_FORM_ARTIFACTS || 'artifacts/frontend-detail-form-productization';
const TARGETS = JSON.parse(process.env.FRONTEND_DETAIL_FORM_TARGETS_JSON || '{}');
const VIEWPORTS = [
  { width: 1440, height: 900 },
  { width: 1280, height: 800 },
  { width: 768, height: 1024 },
];
const DOMAINS = [
  { key: 'payment_request', role: 'fixture_role_finance' },
  { key: 'contract', role: 'fixture_role_contract_operator' },
  { key: 'project', role: 'fixture_role_pm' },
];

function check(value, message) {
  if (!value) throw new Error(message);
}

function route(target, mode) {
  const prefix = mode === 'detail' ? 'r' : 'f';
  return `/${prefix}/${encodeURIComponent(target.model)}/${target.record_id}?action_id=${target.action_id}&menu_id=${target.menu_id}`;
}

function runtimeEvidence(page) {
  const evidence = { console: [], pageerror: [], http: [] };
  page.on('console', (message) => {
    if (message.type() === 'error' && !/favicon|ResizeObserver/i.test(message.text())) evidence.console.push(message.text());
  });
  page.on('pageerror', (error) => evidence.pageerror.push(error.message));
  page.on('response', (response) => {
    if (response.status() >= 500) evidence.http.push({ status: response.status(), url: response.url() });
  });
  return evidence;
}

async function login(page, role) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.locator('#login-username, input[autocomplete="username"]').first().fill(role);
  await page.locator('#login-password, input[autocomplete="current-password"]').first().fill(PASSWORD);
  const database = page.locator('input').nth(2);
  if (await database.isEnabled().catch(() => false)) await database.fill(DB_NAME);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45000 });
  await page.locator('.layout-shell').waitFor({ timeout: 45000 });
}

async function waitForSurface(page) {
  await page.locator('[data-product-page-mode="form"]').waitFor({ state: 'visible', timeout: 45000 });
  await page.locator('[data-product-page-mode="form"] .product-form-loading').waitFor({ state: 'detached', timeout: 45000 });
  await page.locator('[data-product-page-mode="form"] [data-workspace-primary-content]').waitFor({ state: 'visible', timeout: 45000 });
  await page.waitForFunction(() => {
    const surface = document.querySelector('[data-product-page-mode="form"]');
    const heading = document.querySelector('h1')?.textContent || '';
    return Boolean(surface)
      && !/(正在加载|正在初始化)/.test(surface?.textContent || '')
      && !/加载中/.test(heading);
  }, undefined, { timeout: 45000 });
}

async function inspectMode(page, domain, target, mode) {
  await page.goto(`${BASE_URL}${route(target, mode)}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await waitForSurface(page);
  if (mode === 'edit') {
    await page.getByText('编辑业务信息', { exact: true }).waitFor({ state: 'visible', timeout: 45000 });
  }
  const surface = page.locator('[data-product-page-mode="form"]');
  const text = await surface.innerText();
  check(!(await surface.locator('[data-component="DevContextPanel"]:visible').count()), `${domain}/${mode}: HUD exposed`);
  check(!/model=.*id=.*action=/.test(text), `${domain}/${mode}: technical context exposed`);
  if (mode === 'edit') {
    check(text.includes('编辑业务信息'), `${domain}/edit: shared edit baseline missing`);
    check(!(await surface.locator('.financial-workspace:visible').count()), `${domain}/edit: readonly workspace rendered before form`);
    check(text.includes('尚未修改') || text.includes('有未保存修改'), `${domain}/edit: dirty state missing`);
  }
  const heading = (await page.locator('h1:visible').first().innerText()).trim();
  check(heading.length > 0 && heading.length <= 80, `${domain}/${mode}: page identity is not concise (${heading.length})`);
  const axe = await new AxeBuilder({ page }).analyze();
  const blocking = axe.violations.filter((item) => ['critical', 'serious'].includes(String(item.impact || '')));
  check(blocking.length === 0, `${domain}/${mode}: axe blocking=${blocking.flatMap((item) => item.nodes.map((node) => `${item.id}:${node.target.join(' ')}`)).join(',')}`);
  return {
    domain,
    mode,
    route: route(target, mode),
    heading,
    blocking_axe: blocking.length,
    relation_ids_exposed: /\b(?:项目|往来单位|合同)\s*\*?\s*\n\s*\d+\b/.test(text),
    readonly_state_labels: await surface.locator('.field-state').count(),
  };
}

async function captureViewports(page, domain, mode) {
  const screenshots = [];
  for (const viewport of VIEWPORTS) {
    await page.setViewportSize(viewport);
    await page.waitForTimeout(150);
    const file = path.join(OUTPUT, `${domain}-${mode}-${viewport.width}x${viewport.height}.png`);
    await page.screenshot({ path: file, fullPage: false });
    const overflow = await page.evaluate(() => Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth));
    check(overflow === 0, `${domain}/${mode}/${viewport.width}: horizontal overflow=${overflow}`);
    screenshots.push(file);
  }
  return screenshots;
}

async function verifyDirtyState(page, domain) {
  const input = page.locator('[data-product-page-mode="form"] [data-field-name] input:not([readonly]):not([disabled]), [data-product-page-mode="form"] [data-field-name] textarea:not([readonly]):not([disabled])').first();
  if (!(await input.count()) || !(await input.isVisible().catch(() => false))) {
    return { domain, result: 'NOT_APPLICABLE_CURRENT_STATE_READONLY' };
  }
  const type = await input.getAttribute('type');
  if (['checkbox', 'radio', 'file'].includes(String(type || '').toLowerCase())) {
    return { domain, result: 'NOT_APPLICABLE_NO_SAFE_TEXT_FIELD' };
  }
  const original = await input.inputValue();
  await input.fill(`${original} 定向验收`);
  await page.waitForTimeout(200);
  const dirtyVisible = (await page.locator('[data-product-page-mode="form"]').innerText()).includes('有未保存修改');
  await input.fill(original);
  return { domain, result: dirtyVisible ? 'PASS' : 'NOT_APPLICABLE_RUNTIME_FIELD_READONLY' };
}

async function main() {
  check(PASSWORD, 'SC_ACCEPTANCE_FIXTURE_PASSWORD is required');
  fs.mkdirSync(OUTPUT, { recursive: true });
  const browser = await launchChromium();
  const results = [];
  const screenshots = [];
  const dirty = [];
  try {
    for (const domain of DOMAINS) {
      const target = TARGETS[domain.key];
      check(target?.record_id > 0 && target?.action_id > 0 && target?.menu_id > 0, `missing target ${domain.key}`);
      const context = await browser.newContext({ viewport: VIEWPORTS[0] });
      const page = await context.newPage();
      const runtime = runtimeEvidence(page);
      await login(page, domain.role);
      for (const mode of ['detail', 'edit']) {
        const row = await inspectMode(page, domain.key, target, mode);
        results.push(row);
        screenshots.push(...await captureViewports(page, domain.key, mode));
        if (mode === 'edit') dirty.push(await verifyDirtyState(page, domain.key));
      }
      check(runtime.console.length === 0, `${domain.key}: console errors`);
      check(runtime.pageerror.length === 0, `${domain.key}: page errors`);
      check(runtime.http.length === 0, `${domain.key}: blocking HTTP errors`);
      await context.close();
    }
  } finally {
    await browser.close();
  }
  check(results.every((row) => !row.relation_ids_exposed), 'raw relation ids exposed');
  check(dirty.some((row) => row.result === 'PASS'), 'no editable representative route projected dirty-state feedback');
  const report = {
    schema_version: 'frontend_detail_form_productization.v1',
    git_sha: process.env.GIT_SHA || '',
    database: DB_NAME,
    base_url: BASE_URL,
    results,
    dirty_state: dirty,
    screenshots,
    runtime_errors: { console: 0, pageerror: 0, blocking_http: 0 },
    result: 'PASS',
  };
  const reportPath = path.join(OUTPUT, 'report.json');
  fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({ report: reportPath, pages: results.length, screenshots: screenshots.length, result: report.result }, null, 2));
}

main().catch((error) => {
  console.error(`[frontend_detail_form_productization_browser] ${error.stack || error.message}`);
  process.exit(2);
});
