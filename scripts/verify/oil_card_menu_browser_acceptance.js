#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const { createRequire } = require('module');

const requireFromRoot = createRequire(path.join(process.cwd(), 'frontend/apps/web/package.json'));
const { chromium } = requireFromRoot('playwright');

const BASE = String(process.env.FRONTEND_URL || '').replace(/\/$/, '');
const DB = String(process.env.DB_NAME || '');
const LOGIN = String(process.env.E2E_LOGIN || '');
const PASSWORD = String(process.env.E2E_PASSWORD || '');
const OUT_DIR = path.join(
  process.env.ARTIFACTS_DIR || 'artifacts',
  'browser',
  'oil-card-menu',
  new Date().toISOString().replace(/[-:]/g, '').replace(/\..+$/, ''),
);
const TARGETS = [
  { label: '油卡登记', xmlid: 'smart_construction_core.menu_sc_legacy_fuel_card_fact_acceptance' },
  { label: '充值登记', xmlid: 'smart_construction_core.menu_sc_legacy_fuel_card_recharge_fact_acceptance' },
];

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function sanitized(message) {
  const text = String(message || '');
  return PASSWORD ? text.split(PASSWORD).join('[REDACTED]') : text;
}

function findNavNode(nodes, xmlid) {
  for (const node of Array.isArray(nodes) ? nodes : []) {
    const meta = node && typeof node.meta === 'object' ? node.meta : {};
    if (String(node.menu_xmlid || node.xmlid || meta.menu_xmlid || '') === xmlid) return node;
    const found = findNavNode(node.children, xmlid);
    if (found) return found;
  }
  return null;
}

function actionIdFromNode(node) {
  const meta = node && typeof node.meta === 'object' ? node.meta : {};
  const direct = Number(node.action_id || node.native_action_id || meta.action_id || 0);
  if (direct > 0) return direct;
  const route = String(node.route || meta.route || '');
  const match = route.match(/^\/a\/([1-9]\d*)(?:[/?#]|$)/);
  return match ? Number(match[1]) : 0;
}

function authorityHasPair(contract, menuId, actionId) {
  return ['primary_actions', 'role_home_actions', 'contextual_actions', 'admin_actions'].some((bucket) => (
    (Array.isArray(contract && contract[bucket]) ? contract[bucket] : []).some((row) => (
      Number(row.menu_id || 0) === menuId && Number(row.action_id || 0) === actionId
    ))
  ));
}

async function login(page) {
  await page.goto(`${BASE}/login?db=${encodeURIComponent(DB)}&t=${Date.now()}`, {
    waitUntil: 'networkidle',
    timeout: 45000,
  });
  await page.locator('input[autocomplete="username"]').fill(LOGIN);
  await page.locator('input[autocomplete="current-password"]').fill(PASSWORD);
  const databaseInput = page.locator('input[autocomplete="off"]');
  if (await databaseInput.isEditable().catch(() => false)) await databaseInput.fill(DB);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForFunction(() => !window.location.pathname.includes('/login'), null, { timeout: 45000 });
  await page.waitForSelector('[data-component="SidebarNav"] .menu', { timeout: 45000 });
}

(async function main() {
  assert(BASE && DB && LOGIN && PASSWORD, 'FRONTEND_URL, DB_NAME, E2E_LOGIN and E2E_PASSWORD are required');
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 }, locale: 'zh-CN' });
  const consoleErrors = [];
  const pageErrors = [];
  const intents = [];
  let systemInit = null;
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(sanitized(message.text()));
  });
  page.on('pageerror', (error) => pageErrors.push(sanitized(error.message)));
  page.on('request', (request) => {
    if (!request.url().includes('/api/v1/intent')) return;
    try {
      const payload = JSON.parse(request.postData() || '{}');
      intents.push(String(payload.intent || 'unknown'));
    } catch {
      intents.push('unparsed');
    }
  });
  page.on('response', async (response) => {
    if (!response.url().includes('/api/v1/intent')) return;
    try {
      const requestPayload = JSON.parse(response.request().postData() || '{}');
      if (String(requestPayload.intent || '') !== 'system.init') return;
      const body = await response.json();
      systemInit = body && typeof body.data === 'object' ? body.data : null;
    } catch {
      systemInit = null;
    }
  });

  const rows = [];
  try {
    await login(page);
    for (let attempt = 0; attempt < 50 && !systemInit; attempt += 1) await page.waitForTimeout(100);
    assert(systemInit, 'system.init response was not captured');
    for (const [index, target] of TARGETS.entries()) {
      const navNode = findNavNode(systemInit.nav, target.xmlid);
      assert(navNode, `${target.label} navigation node is missing`);
      const expectedMenuId = Number(navNode.menu_id || navNode.id || 0);
      const expectedActionId = actionIdFromNode(navNode);
      assert(expectedMenuId > 0 && expectedActionId > 0, `${target.label} navigation target is incomplete`);
      const authorityFound = authorityHasPair(systemInit.route_authority_v1, expectedMenuId, expectedActionId);
      const search = page.locator('.primary-navigation__search input');
      await search.fill(target.label);
      const button = page.locator('[data-component="SidebarNav"] .node button.label').filter({ hasText: target.label });
      await button.first().waitFor({ state: 'visible', timeout: 10000 });
      const beforeUrl = page.url();
      const intentOffset = intents.length;
      await button.first().click();
      await page.waitForURL((url) => url.href !== beforeUrl, { timeout: 8000 }).catch(() => {});
      await page.waitForTimeout(1500);
      const current = new URL(page.url());
      const row = {
        label: target.label,
        menuXmlid: target.xmlid,
        expectedActionId,
        expectedMenuId,
        authorityFound,
        beforePath: new URL(beforeUrl).pathname,
        afterPath: current.pathname,
        afterMenuId: Number(current.searchParams.get('menu_id') || 0),
        intents: intents.slice(intentOffset),
        opened: authorityFound && current.pathname === `/a/${expectedActionId}` && Number(current.searchParams.get('menu_id')) === expectedMenuId,
      };
      rows.push(row);
      await page.screenshot({ path: path.join(OUT_DIR, `${index + 1}-${target.label}.png`), fullPage: true });
      await search.fill('');
    }
    const report = {
      status: rows.every((row) => row.opened) && pageErrors.length === 0 ? 'PASS' : 'FAIL',
      frontendUrl: BASE,
      database: DB,
      login: LOGIN,
      passwordRecorded: false,
      rows,
      consoleErrors,
      pageErrors,
    };
    fs.writeFileSync(path.join(OUT_DIR, 'report.json'), `${JSON.stringify(report, null, 2)}\n`);
    process.stdout.write(`${JSON.stringify({ ...report, artifactDir: OUT_DIR })}\n`);
    if (report.status !== 'PASS') process.exitCode = 1;
  } catch (error) {
    const report = {
      status: 'FAIL',
      frontendUrl: BASE,
      database: DB,
      login: LOGIN,
      passwordRecorded: false,
      error: sanitized(error && error.stack ? error.stack : error),
      rows,
      consoleErrors,
      pageErrors,
    };
    fs.writeFileSync(path.join(OUT_DIR, 'report.json'), `${JSON.stringify(report, null, 2)}\n`);
    process.stderr.write(`${JSON.stringify({ ...report, artifactDir: OUT_DIR })}\n`);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}());
