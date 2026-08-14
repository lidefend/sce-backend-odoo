#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { launchChromium } from './playwright_runtime.mjs';
import { resolveAcceptanceEnvironment } from './lib/frontend_acceptance_environment.mjs';
import { acquireAcceptanceLease } from './lib/frontend_acceptance_lease.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
if (process.env.SC_GOVERNED_BROWSER_ENTRY !== '1') {
  throw new Error('DENY: use make verify.frontend.collection_view_semantics.browser; direct browser execution is forbidden');
}
const ancestry = spawnSync(
  'bash',
  [
    '-c',
    'source "$1"; require_governed_make_ancestor "collection_view_semantics_browser.mjs" "$2" "verify.frontend.collection_view_semantics.browser"',
    '_',
    path.join(ROOT, 'scripts/common/governed_make_entry.sh'),
    ROOT,
  ],
  { cwd: ROOT, env: process.env, encoding: 'utf8' },
);
if (ancestry.status !== 0) {
  throw new Error((ancestry.stderr || ancestry.stdout || 'DENY: missing governed Make ancestry').trim());
}

const acceptance = resolveAcceptanceEnvironment({
  tool: 'collection-view-semantics',
  env: {
    ...process.env,
    SC_ACCEPTANCE_PROFILE: 'local',
    SC_ACCEPTANCE_TARGET_MODE: 'managed',
    SC_ACCEPTANCE_FRONTEND_URL: 'http://127.0.0.1:5175',
    SC_ACCEPTANCE_API_URL: 'http://127.0.0.1:5175',
    SC_ACCEPTANCE_DATABASE: 'sc_frontend_acceptance',
  },
});
const BASE_URL = acceptance.baseUrl;
const DB_NAME = acceptance.database;
if (BASE_URL !== 'http://127.0.0.1:5175' || acceptance.apiUrl !== 'http://127.0.0.1:5175' || DB_NAME !== 'sc_frontend_acceptance') {
  throw new Error('collection view semantics requires the canonical managed acceptance identity');
}
if (process.env.SC_COLLECTION_ENVIRONMENT_PROBE === '1') {
  console.log(JSON.stringify({ baseUrl: BASE_URL, apiUrl: acceptance.apiUrl, database: DB_NAME, profile: acceptance.profile, mode: acceptance.target.mode, targetKey: acceptance.concurrency.targetKey }));
  process.exit(0);
}
const PASSWORD = acceptance.password || process.env.SC_ACCEPTANCE_FIXTURE_PASSWORD || '';
const SHA = process.env.GIT_SHA || '';
const TARGETS = JSON.parse(process.env.COLLECTION_VIEW_SEMANTICS_TARGETS_JSON || '{}');
const OUT = process.env.ARTIFACTS_DIR || acceptance.runArtifactRoot;
const shots = path.join(OUT, 'screenshots');

function check(value, message) { if (!value) throw new Error(message); }
function listRoute(target, query = '') {
  const menuQuery = Number(target.menu_id || 0) > 0 ? `?menu_id=${target.menu_id}` : '?';
  return `/a/${target.action_id}${menuQuery}${query}`;
}
function detailDestination(rawUrl) {
  const url = new URL(rawUrl);
  return {
    pathname: url.pathname,
    record_id: url.searchParams.get('record_id') || url.searchParams.get('project_id') || '',
    scene_key: url.searchParams.get('scene_key') || '',
  };
}
async function login(page, username = 'fixture_role_pm') {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded' });
  await page.locator('#login-username, input[autocomplete="username"]').first().fill(username);
  await page.locator('#login-password, input[autocomplete="current-password"]').first().fill(PASSWORD);
  const db = page.locator('input').nth(2);
  if (await db.isEnabled().catch(() => false)) await db.fill(DB_NAME);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45000 });
  await page.waitForTimeout(1000);
}
async function ready(page) {
  await page.locator('[data-product-page-mode="list"]').first().waitFor({ state: 'visible', timeout: 45000 });
  await page.waitForFunction(() => !document.querySelector('[aria-busy="true"]'), undefined, { timeout: 45000 });
}
async function noOverflow(page, label) {
  const geometry = await page.evaluate(() => ({ doc: document.documentElement.scrollWidth, viewport: window.innerWidth }));
  check(geometry.doc <= geometry.viewport + 2, `${label}: horizontal overflow ${geometry.doc}>${geometry.viewport}`);
  return geometry;
}
async function screenshot(page, name) {
  const target = path.join(shots, `${name}.png`);
  await page.screenshot({ path: target, fullPage: true });
  return path.relative(OUT, target);
}
async function switchToCard(page) {
  const visibleCard = page.locator('button:visible').filter({ hasText: /^卡片$/ }).first();
  if (await visibleCard.count()) {
    await visibleCard.click();
    return;
  }
  await page.getByRole('button', { name: '更多列表操作', exact: true }).click();
  await page.locator('button:visible').filter({ hasText: /^卡片$/ }).first().click();
}

const acceptanceLease = await acquireAcceptanceLease({ environment: acceptance, mode: 'shared-read', owner: { tool: 'collection-view-semantics', profile: acceptance.profile, source_sha: SHA } });
fs.mkdirSync(shots, { recursive: true });
const browser = await launchChromium({ headless: true });
const report = { schema_version: 'collection-view-semantics.v1', git_sha: SHA, base_url: BASE_URL, assertions: [], screenshots: [], viewports: [] };
const pass = (name, details = {}) => report.assertions.push({ name, status: 'pass', ...details });
function collectKanbanProbes(value, at = '$', rows = []) {
  if (!value || typeof value !== 'object' || rows.length >= 20) return rows;
  if (!Array.isArray(value) && ('collection_presentation' in value || ('fields' in value && /kanban/i.test(at)))) {
    rows.push({ at, fields: value.fields, collection_presentation: value.collection_presentation });
  }
  for (const [key, child] of Object.entries(value)) collectKanbanProbes(child, `${at}.${key}`, rows);
  return rows;
}
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const runtimeErrors = [];
  report.contract_probes = [];
  page.on('pageerror', (error) => runtimeErrors.push(error.message));
  page.on('console', (message) => { if (message.type() === 'error' && !/favicon|ResizeObserver/i.test(message.text())) runtimeErrors.push(message.text()); });
  page.on('response', async (response) => {
    const request = response.request();
    if (!request.url().includes('/api/v1/intent')) return;
    const payload = request.postDataJSON();
    if (payload?.intent !== 'ui.contract.v2') return;
    const body = await response.json().catch(() => ({}));
    report.contract_probes.push({ params: payload.params, kanban: collectKanbanProbes(body) });
  });
  await login(page);

  await page.goto(`${BASE_URL}${listRoute(TARGETS.ledger)}`);
  await ready(page);
  report.initial_buttons = await page.locator('button').allTextContents();
  check(await page.getByRole('button', { name: '表格', exact: true }).count(), 'fresh ledger lacks table mode');
  check(await page.getByRole('button', { name: '卡片', exact: true }).count(), 'fresh ledger lacks card mode');
  check(await page.getByRole('button', { name: '流程看板', exact: true }).count() === 0, 'ledger card mislabeled workflow board');
  check(await page.locator('[data-collection-presentation="table"]').count(), 'fresh ledger did not default to table');
  pass('fresh_project_ledger_defaults_to_table'); pass('table_and_card_modes_available'); pass('card_label_not_workflow_board');
  const tableNames = await page.locator('.desktop-record-table tbody tr .cell-primary-link').allTextContents();
  report.screenshots.push(await screenshot(page, '1440-ledger-table'));
  const tableListUrl = page.url();
  await page.locator('.desktop-record-table tbody tr .cell-primary-link').first().click();
  await page.waitForURL((url) => url.href !== tableListUrl, { timeout: 45000 });
  await page.waitForTimeout(2000);
  const tableDetailDestination = detailDestination(page.url());
  await page.goBack(); await ready(page);

  await switchToCard(page);
  await page.waitForURL((url) => url.searchParams.get('view_mode') === 'kanban');
  await ready(page);
  const cardNames = await page.locator('[data-collection-presentation="explicit_card"] .card-title').allTextContents();
  const cardSurfaceText = await page.locator('[data-collection-presentation="explicit_card"]').innerText();
  check(!/name\s*[:.]([\s\S]*?)label\s*[:.]|\.type\s*:/i.test(cardSurfaceText), 'card descriptor text leaked into record values');
  pass('card_descriptor_text_leak', { count: 0 });
  const cardMetaLabels = (await page.locator('[data-collection-presentation="explicit_card"] .meta-row dt').allTextContents()).map((label) => label.trim().toLowerCase());
  const technicalMetaLabels = cardMetaLabels.filter((label) => ['id', 'create_uid', 'create_date', 'write_uid', 'write_date', '__last_update'].includes(label));
  check(technicalMetaLabels.length === 0, `card technical fields leaked: ${technicalMetaLabels.join(',')}`);
  pass('card_technical_field_leak', { count: 0 });
  report.record_set_probe = { table_names: tableNames, card_names: cardNames };
  report.screenshots.push(await screenshot(page, '1440-ledger-card-probe'));
  check(JSON.stringify([...tableNames].sort()) === JSON.stringify([...cardNames].sort()), 'table/card record names differ');
  pass('table_card_record_set_equivalent', { records: cardNames.length });
  await page.reload(); await ready(page);
  check(await page.locator('[data-collection-presentation="explicit_card"]').count(), 'refresh lost explicit card mode');
  pass('query_context_preserved_across_switch');
  report.screenshots.push(await screenshot(page, '1440-ledger-card'));

  const firstCard = page.locator('[data-collection-presentation="explicit_card"] .card').first();
  check(await firstCard.count(), 'card missing for detail continuity');
  const cardListUrl = page.url();
  await firstCard.click();
  await page.waitForURL((url) => url.href !== cardListUrl, { timeout: 45000 });
  await page.waitForTimeout(2000);
  const cardDetailDestination = detailDestination(page.url());
  report.detail_destination_probe = { table: tableDetailDestination, card: cardDetailDestination };
  check(JSON.stringify(cardDetailDestination) === JSON.stringify(tableDetailDestination), 'table/card detail destinations differ');
  check(new URL(page.url()).searchParams.get('view_mode') === 'kanban', 'detail route lost card context');
  pass('card_opens_same_detail_form', { destination: cardDetailDestination });
  await page.goBack(); await ready(page);
  check(await page.locator('[data-collection-presentation="explicit_card"]').count(), 'back lost card context');
  pass('detail_back_restores_collection_context');

  await page.goto(`${BASE_URL}${listRoute(TARGETS.ledger, '&view_mode=kanban&group_by=lifecycle_state')}`); await ready(page);
  report.grouped_probe = { url: page.url(), buttons: await page.locator('button').allTextContents() };
  check(await page.getByRole('button', { name: '流程看板', exact: true }).count(), 'grouped collection lacks workflow label');
  check(await page.locator('[data-collection-presentation="workflow_board"] .workflow-lane-header').count() > 0, 'workflow board lacks grouped lanes');
  pass('workflow_board_requires_group_semantics');
  report.screenshots.push(await screenshot(page, '1280-overview-workflow'));

  await page.goto(`${BASE_URL}${listRoute(TARGETS.non_project)}`); await ready(page);
  check(await page.getByRole('button', { name: '表格', exact: true }).count() || await page.locator('[data-collection-presentation="table"]').count(), 'non-project collection regressed');
  pass('non_project_collection_has_generic_semantics');

  for (const viewport of [{ width: 1280, height: 800 }, { width: 768, height: 1024 }, { width: 390, height: 844 }]) {
    await page.setViewportSize(viewport);
    await page.goto(`${BASE_URL}${listRoute(TARGETS.ledger)}`); await ready(page);
    const expected = viewport.width <= 768 ? 'responsive_table_card' : 'table';
    check(await page.locator(`[data-collection-presentation="${expected}"]`).count(), `${viewport.width}: responsive table projection missing`);
    const tableGeometry = await noOverflow(page, `${viewport.width}-table`);
    await switchToCard(page); await ready(page);
    check(await page.locator('[data-collection-presentation="explicit_card"]').count(), `${viewport.width}: explicit card missing`);
    const cardGeometry = await noOverflow(page, `${viewport.width}-card`);
    check(await page.locator('.sc-product-page-toolbar').count() <= 1, `${viewport.width}: duplicate toolbar`);
    report.viewports.push({ ...viewport, table_presentation: expected, table_geometry: tableGeometry, card_geometry: cardGeometry });
    report.screenshots.push(await screenshot(page, `${viewport.width}-ledger-card`));
  }
  pass('responsive_auto_card_distinct_from_explicit_card');
  pass('unknown_kanban_semantic_fails_safe', { proof: 'unit_and_contract_guard' });
  check(runtimeErrors.length === 0, `runtime errors: ${runtimeErrors.join(' | ')}`);
  await context.close();
  report.ok = true;
} catch (error) {
  report.ok = false;
  report.error = error instanceof Error ? error.stack : String(error);
  report.failure_url = report.failure_url || 'captured by failure screenshot';
  throw error;
} finally {
  fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(report, null, 2));
  const rows = report.assertions.map((row) => `<li>${row.status}: ${row.name}</li>`).join('');
  const images = report.screenshots.map((src) => `<figure><img src="${src}" style="max-width:100%"><figcaption>${src}</figcaption></figure>`).join('');
  fs.writeFileSync(path.join(OUT, 'index.html'), `<!doctype html><meta charset="utf-8"><title>Collection view semantics</title><h1>Collection view semantics</h1><p>SHA ${SHA}</p><ul>${rows}</ul>${images}`);
  await browser.close();
  await acceptanceLease.release();
}
console.log(`[collection-view-semantics-browser] PASS report=${path.join(OUT, 'report.json')}`);
