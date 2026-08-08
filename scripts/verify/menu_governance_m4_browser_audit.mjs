#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';

const ROOT = process.cwd();
const BASE_URL = process.env.FRONTEND_URL || 'http://127.0.0.1:18121';
const DB_NAME = process.env.DB_NAME || 'sc_frontend_acceptance';
const PASSWORD = process.env.SC_ACCEPTANCE_FIXTURE_PASSWORD || '';
const EXPECTED_SHA = process.env.GIT_SHA || '';
const OUTPUT_DIR = path.resolve(ROOT, process.env.ARTIFACTS_DIR || 'artifacts/menu-governance/browser');
const RUNTIME_REPORT = path.resolve(ROOT, process.env.MENU_M4_RUNTIME_REPORT || 'artifacts/menu-governance/menu-m4-runtime-resource-probe.json');
const ROLES = [
  'fixture_role_finance',
  'fixture_role_project_a_member',
  'fixture_role_pm',
  'fixture_role_contract_operator',
  'fixture_role_config_admin',
  'fixture_role_config_admin_peer',
  'fixture_role_owner',
  'fixture_role_executive',
];
const VIEWPORTS = [
  { key: 'desktop', width: 1440, height: 900 },
  { key: 'mobile', width: 390, height: 844 },
];

function check(value, message) {
  if (!value) throw new Error(message);
}

function payloadData(payload) {
  return payload?.result?.data || payload?.result || payload?.data || payload;
}

function navigationFromPayload(payload) {
  const data = payloadData(payload);
  return Array.isArray(data?.navigation_v1?.nav) ? data.navigation_v1.nav : null;
}

function sourceShaFromPayload(payload) {
  const data = payloadData(payload);
  return String(data?.source_revision || data?.git_sha || data?.sha || '').trim();
}

function flatten(nodes, ancestors = []) {
  const rows = [];
  for (const node of Array.isArray(nodes) ? nodes : []) {
    const meta = node?.meta && typeof node.meta === 'object' ? node.meta : {};
    const label = String(node?.title || node?.label || node?.name || '').trim();
    const menuXmlid = String(node?.xmlid || node?.menu_xmlid || meta.menu_xmlid || '').trim();
    const pathLabels = [...ancestors, label].filter(Boolean);
    rows.push({ menu_xmlid: menuXmlid, label, path: pathLabels, child_count: Array.isArray(node?.children) ? node.children.length : 0 });
    rows.push(...flatten(node?.children, pathLabels));
  }
  return rows;
}

function capturePage(page) {
  const state = { navigation: null, sourceSha: '', consoleErrors: [], pageErrors: [], httpErrors: [] };
  page.on('console', (message) => {
    if (message.type() === 'error' && !/favicon|ResizeObserver/i.test(message.text())) state.consoleErrors.push(message.text());
  });
  page.on('pageerror', (error) => state.pageErrors.push(error.message));
  page.on('response', async (response) => {
    if (response.status() >= 400 && response.url().includes('/api/')) state.httpErrors.push({ status: response.status(), url: response.url() });
    if (!response.url().includes('/api/v1/intent')) return;
    let body;
    try { body = await response.json(); } catch { return; }
    const navigation = navigationFromPayload(body);
    if (Array.isArray(navigation)) state.navigation = navigation;
    const sha = sourceShaFromPayload(body);
    if (sha) state.sourceSha = sha;
  });
  return state;
}

async function login(page, role) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.locator('#login-username, input[autocomplete="username"]').first().fill(role);
  await page.locator('#login-password, input[autocomplete="current-password"]').first().fill(PASSWORD);
  const database = page.locator('#login-database, input[name="database"]');
  if (await database.count() && await database.isEnabled().catch(() => false)) await database.fill(DB_NAME);
  await page.getByRole('button', { name: /^登录$/ }).click();
  try {
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45000 });
  } catch (error) {
    const body = await page.locator('body').innerText().catch(() => '');
    throw new Error(`${role}: login did not complete: ${body.slice(0, 800)}`, { cause: error });
  }
  await page.locator('.layout-shell').waitFor({ timeout: 45000 });
  await page.waitForFunction(() => !(document.body.innerText || '').includes('正在初始化'), null, { timeout: 45000 });
  await page.waitForFunction(
    () => !/正在加载(?:场景|页面|列表)/.test(document.body.innerText || ''),
    null,
    { timeout: 45000 },
  );
}

fs.mkdirSync(path.join(OUTPUT_DIR, 'screenshots'), { recursive: true });
const runtime = JSON.parse(fs.readFileSync(RUNTIME_REPORT, 'utf8'));
const frozen = new Set(runtime.rows.map((row) => row.menu_xmlid));
const browser = await launchChromium({ headless: true });
const observations = [];
try {
  for (const viewport of VIEWPORTS) {
    for (const role of ROLES) {
      const context = await browser.newContext({ viewport, locale: 'zh-CN' });
      const page = await context.newPage();
      const state = capturePage(page);
      await login(page, role);
      check(Array.isArray(state.navigation), `${role}/${viewport.key}: authoritative navigation missing`);
      check(state.sourceSha === EXPECTED_SHA, `${role}/${viewport.key}: runtime SHA ${state.sourceSha || '(missing)'} != ${EXPECTED_SHA}`);
      if (viewport.key === 'mobile') {
        await page.getByRole('button', { name: '菜单', exact: true }).click();
        await page.locator('#primary-sidebar').waitFor({ timeout: 5000 });
      }
      const documentOverflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      const nodes = flatten(state.navigation);
      const scoped = nodes.filter((row) => frozen.has(row.menu_xmlid));
      await page.screenshot({
        path: path.join(OUTPUT_DIR, 'screenshots', `${viewport.key}-${role}.png`),
        fullPage: true,
      });
      observations.push({
        role,
        viewport,
        source_sha: state.sourceSha,
        document_horizontal_overflow_px: documentOverflow,
        console_errors: state.consoleErrors,
        page_errors: state.pageErrors,
        http_errors: state.httpErrors,
        frozen_navigation: scoped,
      });
      check(documentOverflow === 0, `${role}/${viewport.key}: horizontal overflow=${documentOverflow}`);
      check(state.consoleErrors.length === 0, `${role}/${viewport.key}: console errors: ${state.consoleErrors.join(' | ')}`);
      check(state.pageErrors.length === 0, `${role}/${viewport.key}: page errors: ${state.pageErrors.join(' | ')}`);
      check(state.httpErrors.length === 0, `${role}/${viewport.key}: HTTP errors present`);
      await context.close();
    }
  }
} finally {
  await browser.close();
}

const report = {
  schema: 'sce.menu_governance_m4_browser.v1',
  source_commit_sha: EXPECTED_SHA,
  base_url: BASE_URL,
  database_role: 'isolated_acceptance_rehearsal',
  database: DB_NAME,
  scope_count: frozen.size,
  role_count: ROLES.length,
  viewport_count: VIEWPORTS.length,
  observations,
};
fs.writeFileSync(path.join(OUTPUT_DIR, 'report.json'), `${JSON.stringify(report, null, 2)}\n`, 'utf8');
console.log(`[menu-governance-m4-browser] PASS roles=${ROLES.length} viewports=${VIEWPORTS.length} scope=${frozen.size}`);
