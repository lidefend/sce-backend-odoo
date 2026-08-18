#!/usr/bin/env node
// Productization topic: local-dev frontend delivery inspection (v5).
// Clicks every visible menu leaf and home shortcut card to discover the
// actual route (pathname + query) each one resolves to, then inspects every
// unique route with its full query so route-authority bound links keep their
// menu_id context. Also captures scene_ready contract evidence for /s/ routes.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { launchChromium } from '../verify/playwright_runtime.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '..', '..');
const envFile = fs.readFileSync(path.join(repoRoot, '.env.dev'), 'utf8');
const PASSWORD = envFile.match(/^SC_DEMO_USER_PASSWORD=(.+)$/m)?.[1]?.trim() || '';
const BASE_URL = process.env.INSPECT_BASE_URL || 'http://127.0.0.1:18081';
const DB_NAME = process.env.INSPECT_DB || 'sc_dev_demo';
const USER = process.env.INSPECT_USER || 'demo_pm';
const OUT = process.env.INSPECT_OUT || 'artifacts/frontend-dev-inspection';
const SHOTS = path.join(OUT, 'screenshots');

fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(SHOTS, { recursive: true });
if (!PASSWORD) { console.error('SC_DEMO_USER_PASSWORD missing'); process.exit(2); }

const report = { startedAt: new Date().toISOString(), baseUrl: BASE_URL, user: USER, login: null, discoveredRoutes: [], routes: [] };

function attachRuntime(page, state) {
  page.on('console', (msg) => { if (msg.type() === 'error') state.console.push(String(msg.text()).slice(0, 500)); });
  page.on('pageerror', (err) => state.pageerror.push(String(err?.message || err).slice(0, 500)));
  page.on('response', (response) => {
    const url = response.url();
    if (url.includes('/api/') && response.status() >= 400) {
      state.http.push({ status: response.status(), url: url.replace(BASE_URL, ''), method: response.request().method() });
    }
    if (url.includes('/api/v1/intent') && response.status() === 200) {
      try {
        const body = JSON.parse(response.body());
        const contract = body?.data?.scene_ready_contract_v1;
        if (contract && Array.isArray(contract.scenes)) {
          for (const row of contract.scenes) {
            const key = row?.scene?.key || row?.key || '';
            state.sceneContracts = state.sceneContracts || [];
            if (state.sceneContracts.some((c) => c.key === key)) continue;
            state.sceneContracts.push({
              key,
              has_runtime_handoff_surface: Boolean(row.runtime_handoff_surface),
              has_product_delivery_surface: Boolean(row.product_delivery_surface),
              final_scene: row?.runtime_handoff_surface?.final_scene || row?.product_delivery_surface?.final_scene || '',
              delivery_mode: row?.product_delivery_surface?.delivery_mode || '',
            });
          }
        }
      } catch {}
    }
  });
}

async function login(page) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.locator('#login-username, input[autocomplete="username"]').first().waitFor({ state: 'visible', timeout: 45000 });
  await page.locator('#login-username, input[autocomplete="username"]').first().fill(USER);
  await page.locator('#login-password, input[autocomplete="current-password"]').first().fill(PASSWORD);
  const dbInput = page.locator('input').nth(2);
  if (await dbInput.isEnabled()) await dbInput.fill(DB_NAME);
  const respPromise = page.waitForResponse((r) => {
    if (!r.url().includes('/api/v1/intent')) return false;
    try { return JSON.parse(r.request().postData() || '{}').intent === 'login'; } catch { return false; }
  }, { timeout: 45000 });
  await page.getByRole('button', { name: /^登录$/ }).click();
  const resp = await respPromise;
  let env = {};
  try { env = await resp.json(); } catch {}
  await page.waitForURL((u) => !u.pathname.includes('/login'), { timeout: 45000 });
  await page.locator('.layout-shell').waitFor({ timeout: 45000 });
  await page.waitForTimeout(1200);
  return { httpStatus: resp.status(), ok: resp.ok() && env?.ok !== false, errorText: env?.error?.message || null };
}

async function surfaceInfo(page) {
  return page.evaluate(() => {
    const app = document.querySelector('#app');
    const text = String(app?.textContent || '').replace(/\s+/g, ' ').trim();
    return {
      textLength: text.length,
      nodeCount: app ? app.querySelectorAll('*').length : 0,
      heading: (document.querySelector('h1, .headline, .sc-page-title, .page-title, [class*="headline"]')?.textContent || '').trim().slice(0, 100),
      snippet: text.slice(0, 200),
    };
  });
}

function fullRoute(urlText) {
  const u = new URL(urlText);
  return u.pathname + u.search;
}

const browser = await launchChromium();
const harvestCtx = await browser.newContext({ viewport: { width: 1600, height: 900 } });
const harvestPage = await harvestCtx.newPage();
const harvestState = { console: [], pageerror: [], http: [] };
attachRuntime(harvestPage, harvestState);
report.login = await login(harvestPage);

// Expand every category so leaves become visible.
for (let i = 0; i < 4; i += 1) {
  await harvestPage.evaluate(() => {
    document.querySelectorAll('.primary-navigation__tree .toggle').forEach((b) => {
      if (b.getAttribute('aria-expanded') === 'false') b.click();
    });
  });
  await harvestPage.waitForTimeout(350);
}
await harvestPage.screenshot({ path: path.join(SHOTS, '00_home_expanded.png') });

// Collect every leaf button text.
const leafLabels = await harvestPage.evaluate(() => {
  const out = [];
  document.querySelectorAll('.primary-navigation__tree li').forEach((li) => {
    const node = li.querySelector(':scope > .node');
    if (!node || !node.classList.contains('leaf')) return;
    const btn = node.querySelector(':scope > .label');
    if (!btn) return;
    out.push((btn.textContent || '').replace(/\s+/g, ' ').trim());
  });
  return out;
});
report.leafLabels = leafLabels;

// Click each leaf, capture resulting full route (pathname + query), then go home.
const discovered = new Map();
discovered.set('/', { label: 'home' });
discovered.set('/my-work', { label: 'my-work' });

for (const text of leafLabels) {
  if (!text) continue;
  // Re-expand (in case navigation collapsed state).
  await harvestPage.evaluate(() => {
    document.querySelectorAll('.primary-navigation__tree .toggle').forEach((b) => {
      if (b.getAttribute('aria-expanded') === 'false') b.click();
    });
  });
  const clicked = await harvestPage.evaluate((target) => {
    const labels = [...document.querySelectorAll('.primary-navigation__tree li > .node.leaf > .label')];
    const match = labels.find((b) => (b.textContent || '').replace(/\s+/g, ' ').trim() === target);
    if (!match) return false;
    match.click();
    return true;
  }, text);
  if (!clicked) { report.leafLabelsSkipped = (report.leafLabelsSkipped || []).concat([text]); continue; }
  try {
    await harvestPage.waitForURL((u) => !new URL(u.toString()).pathname.endsWith('/') || new URL(u.toString()).pathname !== '/', { timeout: 15000 });
  } catch {}
  await harvestPage.waitForTimeout(700);
  const finalPath = fullRoute(harvestPage.url());
  if (!discovered.has(finalPath)) discovered.set(finalPath, { label: text });
  await harvestPage.goto(`${BASE_URL}/`, { waitUntil: 'domcontentloaded' });
  await harvestPage.locator('.layout-shell').waitFor({ timeout: 30000 });
  await harvestPage.waitForTimeout(400);
}

// Also click each 常用入口 card on the home main area.
await harvestPage.goto(`${BASE_URL}/`, { waitUntil: 'domcontentloaded' });
await harvestPage.locator('.layout-shell').waitFor({ timeout: 30000 });
await harvestPage.waitForTimeout(800);
const cardLabels = await harvestPage.evaluate(() => {
  const out = [];
  document.querySelectorAll('main a, main [role="link"], main button, [class*="shortcut"] button, [class*="card"]').forEach((el) => {
    const text = (el.textContent || '').replace(/\s+/g, ' ').trim();
    if (text && text.length < 30) out.push(text);
  });
  return [...new Set(out)];
});
report.homeCardLabels = cardLabels.slice(0, 20);
for (const text of cardLabels.slice(0, 8)) {
  const clicked = await harvestPage.evaluate((target) => {
    const candidates = [...document.querySelectorAll('main a, main [role="link"], main button')];
    const match = candidates.find((el) => (el.textContent || '').replace(/\s+/g, ' ').trim() === target);
    if (!match) return false;
    match.click();
    return true;
  }, text);
  if (!clicked) continue;
  try {
    await harvestPage.waitForURL((u) => !u.toString().endsWith('/'), { timeout: 15000 });
  } catch {}
  await harvestPage.waitForTimeout(700);
  const finalPath = fullRoute(harvestPage.url());
  if (!discovered.has(finalPath)) discovered.set(finalPath, { label: `card:${text}` });
  await harvestPage.goto(`${BASE_URL}/`, { waitUntil: 'domcontentloaded' });
  await harvestPage.locator('.layout-shell').waitFor({ timeout: 30000 });
  await harvestPage.waitForTimeout(400);
}

report.discoveredRoutes = [...discovered.entries()].map(([route, info]) => ({ route, label: info.label }));
await harvestCtx.close();

console.log(`discovered ${report.discoveredRoutes.length} routes:`);
for (const r of report.discoveredRoutes) console.log(`  ${r.route} <- ${r.label}`);

// Inspect each unique route (full route incl. query) in a fresh logged-in context.
for (const target of report.discoveredRoutes) {
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 900 } });
  const page = await ctx.newPage();
  const state = { console: [], pageerror: [], http: [] };
  attachRuntime(page, state);
  const entry = { route: target.route, label: target.label };
  try {
    await login(page);
    await page.goto(`${BASE_URL}${target.route}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
    entry.finalUrl = fullRoute(page.url());
    await page.waitForTimeout(2200);
    entry.surface = await surfaceInfo(page);
    const shotName = String(target.label || target.route).replace(/[^a-zA-Z0-9_一-龥]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 50) || 'route';
    await page.screenshot({ path: path.join(SHOTS, `${shotName}.png`), fullPage: false });
  } catch (error) {
    entry.fatal = String(error?.message || error).slice(0, 300);
    try {
      const shotName = (String(target.label || target.route) + '_error').replace(/[^a-zA-Z0-9_一-龥]+/g, '_').slice(0, 50);
      await page.screenshot({ path: path.join(SHOTS, `${shotName}.png`), fullPage: false });
    } catch {}
  }
  entry.consoleErrors = state.console.slice(0, 10);
  entry.pageErrors = state.pageerror.slice(0, 10);
  entry.apiFailures = state.http.slice(0, 15);
  entry.sceneContracts = (state.sceneContracts || []).slice(0, 8);
  entry.errorCount = state.console.length + state.pageerror.length + state.http.length;
  report.routes.push(entry);
  await ctx.close();
  process.stdout.write(`.${target.label?.slice(0, 12) || '?'}`);
}
console.log('');

report.finishedAt = new Date().toISOString();
fs.writeFileSync(path.join(OUT, 'inspection_report.json'), JSON.stringify(report, null, 2));

const problemRoutes = report.routes.filter((r) => r.errorCount > 0 || r.fatal);
console.log(`inspected ${report.routes.length} routes, problems on ${problemRoutes.length}`);
for (const r of problemRoutes) {
  console.log(`--- ${r.label} (${r.route}) final=${r.finalUrl || '?'} heading="${r.surface?.heading || ''}" errors=${r.errorCount}${r.fatal ? ' FATAL=' + r.fatal : ''}`);
  for (const e of (r.consoleErrors || []).slice(0, 2)) console.log(`    console: ${e.slice(0, 220)}`);
  for (const e of (r.pageErrors || []).slice(0, 2)) console.log(`    pageerror: ${e.slice(0, 220)}`);
  for (const e of (r.apiFailures || []).slice(0, 3)) console.log(`    http: ${e.status} ${e.method} ${e.url}`);
}
await browser.close();
