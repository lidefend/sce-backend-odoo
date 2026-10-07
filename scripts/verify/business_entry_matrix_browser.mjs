#!/usr/bin/env node
// Declaration-driven product-surface acceptance for the formal business entry
// matrix (docs/product/frontend_business_entry_acceptance_v1.csv).
//
// The authority is the runtime contract, never a duplicated local declaration:
//   * the entry must resolve inside the *released navigation* the acting role
//     actually receives from `system.init` (not merely the raw route),
//   * list lifecycle is read from the declared `data-list-status` surface,
//   * pagination facts come from the declared CollectionPaginationFooter surface,
//   * the record envelope `ui.contract.v2` supplies company, the declared state
//     field and the workflow `availableActions`.
// A CSS selector string or a pixel literal is never treated as proof.
//
// Read-only by default. `query_responsibility` (list query / filter / detail
// read-back) is asserted for every selected entry. A mutating expectation is only
// checked when the overlay declares it, and the lane refuses to run such an entry
// without the explicit write token.
//
// Registered environment: external daily development server
//   config/frontend/acceptance_environments_v1.json profiles.daily
//   ENV=dev, database sc_demo, expected served revision required.
import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';
import { findReleasedNavigationTarget } from './released_navigation_target.mjs';

const BASE = (process.env.SC_ACCEPTANCE_FRONTEND_URL || process.env.FRONTEND_URL || '').replace(/\/$/, '');
const DB = process.env.SC_ACCEPTANCE_DATABASE || process.env.DB_NAME || 'sc_demo';
const EXPECTED_SHA = process.env.SC_ACCEPTANCE_TARGET_SHA || '';
const LOGIN = process.env.ACCEPTANCE_LOGIN || '';
const PASSWORD = process.env.ACCEPTANCE_PASSWORD || '';
const CSV_PATH = process.env.SC_ENTRY_MATRIX_CSV || 'docs/product/frontend_business_entry_acceptance_v1.csv';
const OVERLAY_PATH = process.env.SC_ENTRY_MATRIX_OVERLAY || 'scripts/verify/business_entry_matrix_overlay.json';
const DOMAIN_FILTER = (process.env.SC_ENTRY_MATRIX_DOMAIN || '').trim();
const KEYS_FILTER = (process.env.SC_ENTRY_MATRIX_KEYS || '').split(',').map((s) => s.trim()).filter(Boolean);
const SKIP_PASSED = process.env.SC_ENTRY_MATRIX_INCLUDE_PASSED === '1';
const WRITE_CONFIRM = process.env.SC_ENTRY_WRITE_CONFIRM || '';
const WRITE_CONFIRM_TOKEN = 'DRIVE_DAILY_SC_DEMO_ENTRY_MATRIX';
const OUT_DIR = process.env.SC_ACCEPTANCE_OUTPUT_DIR
  || path.join('artifacts', 'frontend-business-entry-matrix', String(Date.now()));

const problems = [];
const observations = [];
const consoleErrors = [];
let browser;

function fail(message) { problems.push(message); }
function sleep(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = '';
  let quoted = false;
  for (let index = 0; index < text.length; index += 1) {
    const ch = text[index];
    if (quoted) {
      if (ch === '"') {
        if (text[index + 1] === '"') { field += '"'; index += 1; } else { quoted = false; }
      } else { field += ch; }
      continue;
    }
    if (ch === '"') { quoted = true; continue; }
    if (ch === ',') { row.push(field); field = ''; continue; }
    if (ch === '\n') { row.push(field); field = ''; rows.push(row); row = []; continue; }
    if (ch === '\r') continue;
    field += ch;
  }
  if (field.length || row.length) { row.push(field); rows.push(row); }
  return rows;
}

function loadMatrix() {
  const table = parseCsv(fs.readFileSync(CSV_PATH, 'utf8'));
  const header = table.shift();
  return table
    .filter((cols) => cols.some((value) => String(value).trim() !== ''))
    .map((cols) => Object.fromEntries(header.map((name, index) => [name, cols[index] === undefined ? '' : cols[index]])));
}

function loadOverlay() {
  const body = JSON.parse(fs.readFileSync(OVERLAY_PATH, 'utf8'));
  return {
    defaults: body.defaults && typeof body.defaults === 'object' ? body.defaults : {},
    entries: body.entries && typeof body.entries === 'object' ? body.entries : {},
  };
}

function overlayFor(overlay, menuXmlid) {
  const merged = { ...overlay.defaults, ...(overlay.entries[menuXmlid] || {}) };
  if (!('detail' in merged)) merged.detail = true;
  if (!('expect_write' in merged)) merged.expect_write = null;
  return merged;
}

function selectEntries(matrix, overlay) {
  let selected = matrix.filter((row) => SKIP_PASSED || row.acceptance_status !== 'passed');
  if (KEYS_FILTER.length) selected = selected.filter((row) => KEYS_FILTER.includes(row.menu_xmlid));
  if (DOMAIN_FILTER) selected = selected.filter((row) => row.domain === DOMAIN_FILTER);
  return selected
    .map((row) => ({ row, behaviour: overlayFor(overlay, row.menu_xmlid) }))
    .filter((entry) => entry.row.menu_xmlid && entry.row.action_xmlid);
}

function envelopeData(body) {
  return (body && (body.data || (body.result && (body.result.data || body.result)))) || {};
}

function attachCapture(page, state) {
  page.on('pageerror', (error) => consoleErrors.push(`pageerror: ${error.message}`));
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(`console.error: ${message.text()}`.slice(0, 300));
  });
  page.on('response', async (response) => {
    const request = response.request();
    let payload = {};
    try { payload = JSON.parse(request.postData() || '{}'); } catch { return; }
    const intent = String((payload && payload.intent) || '');
    if (response.status() >= 400) return;
    if (intent === 'system.init' || intent === 'app.init') {
      try {
        const body = await response.json();
        const data = envelopeData(body);
        const user = data && data.user;
        if (user && Number(user.company_id) > 0) {
          state.user = user;
          const nav = data && data.navigation && data.navigation.nav;
          if (Array.isArray(nav)) state.nav = nav;
        }
      } catch { /* identity stays null and the probe fails closed */ }
      return;
    }
    if (intent !== 'ui.contract.v2') return;
    try {
      const body = await response.json();
      const data = envelopeData(body);
      state.contracts.push({
        url: response.url(),
        mainData: (data && data.dataContract && data.dataContract.mainData) || {},
        workflow: (data && data.workflowContract) || null,
        layoutContract: (data && data.layoutContract) || {},
      });
    } catch { /* unparseable envelope is ignored, not trusted */ }
  });
}

async function servedRevision() {
  const response = await fetch(`${BASE}/api/runtime-version`, { headers: { Accept: 'application/json' } });
  if (!response.ok) throw new Error(`runtime-version status=${response.status}`);
  return await response.json();
}

async function login(page) {
  await page.goto(`${BASE}/login?db=${DB}`, { waitUntil: 'networkidle' });
  const inputs = page.locator('input');
  await inputs.nth(0).fill(LOGIN);
  await inputs.nth(1).fill(PASSWORD);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 30000 });
  await page.waitForTimeout(2500);
}

// A collection entry publishes its readiness on the surface the runtime actually
// renders for the declared presentation: the table presentation on ListPage
// (`data-list-status`), the kanban presentation on KanbanPage
// (`data-collection-state`). They are distinct owning-component markers, so the
// probe reads the declared surface for the declared presentation instead of
// assuming a single list page component.
const COLLECTION_SURFACES = {
  table: { component: 'ListPage', stateAttribute: 'data-list-status' },
  kanban: { component: 'KanbanPage', stateAttribute: 'data-collection-state' },
};

function collectionSurfaceSpec(presentation) {
  return COLLECTION_SURFACES[presentation] || COLLECTION_SURFACES.table;
}

function collectionSurface(page, presentation) {
  const spec = collectionSurfaceSpec(presentation);
  return page.locator(`[data-semantic-component="${spec.component}"][${spec.stateAttribute}]`).last();
}

async function collectionSurfaceStatus(page, presentation) {
  const spec = collectionSurfaceSpec(presentation);
  return String((await collectionSurface(page, presentation).getAttribute(spec.stateAttribute)) || '');
}

async function openEntryList(page, navTarget, presentation) {
  const spec = collectionSurfaceSpec(presentation);
  await page.goto(`${BASE}/a/${navTarget.action_id}?menu_id=${navTarget.menu_id}`, { waitUntil: 'networkidle' });
  const surface = collectionSurface(page, presentation);
  await surface.waitFor({ state: 'attached', timeout: 30000 });
  const deadline = Date.now() + 30000;
  let status = '';
  while (Date.now() < deadline) {
    status = String((await surface.getAttribute(spec.stateAttribute)) || '');
    if (status && status !== 'loading') break;
    await sleep(400);
  }
  await sleep(600);
  return status;
}

async function readPaging(page, entryKey, presentation) {
  const footer = page.locator('[data-semantic-component="CollectionPaginationFooter"]').last();
  if (!(await footer.count())) {
    observations.push({ entry: entryKey, stage: 'paging', skipped: true, reason: 'no declared pagination footer' });
    return;
  }
  await footer.waitFor({ state: 'attached', timeout: 15000 });
  const mode = String((await footer.getAttribute('data-pagination-mode')) || '');
  const state = String((await footer.getAttribute('data-state')) || '');
  const regionLabel = String((await footer.getAttribute('aria-label')) || '');
  const totalText = String((await footer.locator('.pagination-total').first().textContent().catch(() => '')) || '').trim();
  const rows = await renderedRecordCount(page, presentation);
  const parsedTotal = Number((totalText.match(/\d+/) || [])[0] || NaN);
  observations.push({ entry: entryKey, stage: 'paging', mode, state, region_label: regionLabel, total: totalText, rows_on_page: rows });
  if (!mode) fail(`${entryKey}: pagination footer published no data-pagination-mode`);
  if (state !== 'ready') fail(`${entryKey}: pagination footer state=${state || 'unknown'}, not ready`);
  if (!regionLabel) fail(`${entryKey}: pagination footer published no region label`);
  if (!Number.isFinite(parsedTotal)) fail(`${entryKey}: record-count text ${JSON.stringify(totalText)} carries no count`);
  if (parsedTotal < rows) fail(`${entryKey}: declared total ${parsedTotal} < ${rows} rendered rows`);
  if (parsedTotal > rows && mode !== 'paged') {
    fail(`${entryKey}: multi-page collection (total ${parsedTotal} > ${rows}) not declared mode=paged (mode=${mode || 'unknown'})`);
  }
}

function primaryRows(page) {
  return page.locator('button[data-semantic-cell-kind="primary"]:visible').count();
}

// The rendered record count is read from whichever declared record surface the
// presentation renders: table rows carry `data-semantic-cell-kind="primary"`,
// kanban records are the declared `CollectionKanbanRecordCard` nodes.
async function renderedRecordCount(page, presentation) {
  if (presentation === 'kanban') return await kanbanCards(page).count();
  return await primaryRows(page);
}

async function firstRowText(page) {
  const cell = page.locator('button[data-semantic-cell-kind="primary"]:visible').first();
  if (!(await cell.count())) return '';
  const title = await cell.getAttribute('title');
  if (title && title.trim()) return title.trim();
  const aria = await cell.getAttribute('aria-label');
  if (aria && aria.trim()) return aria.trim();
  return String((await cell.textContent().catch(() => '')) || '').trim();
}

function kanbanCards(page) {
  return page.locator('[data-semantic-component="CollectionKanbanRecordCard"]:visible');
}

async function firstKanbanCardText(page) {
  const title = kanbanCards(page).first().locator('h3.collection-kanban-record-card__title').first();
  if (!(await title.count())) return '';
  return String((await title.textContent().catch(() => '')) || '').trim();
}

async function searchAndVerify(page, entryKey, term, presentation) {
  const search = page.locator('input[placeholder*="搜索关键字"]:visible').first();
  if (!(await search.count())) {
    fail(`${entryKey}: entry list did not expose the declared search field`);
    return;
  }
  await search.fill(term);
  await page.getByRole('button', { name: /^搜索$/ }).first().click();
  await sleep(3500);
  const status = await collectionSurfaceStatus(page, presentation);
  const rows = await renderedRecordCount(page, presentation);
  observations.push({ entry: entryKey, stage: 'search', term, status, rows });
  if (status === 'error') fail(`${entryKey}: search by the rendered row identity surfaced an error state`);
  if (rows < 1) fail(`${entryKey}: search by the rendered row identity returned ${rows} rows`);
  const clear = page.getByRole('button', { name: /^清除$/ }).first();
  if (await clear.count()) {
    await clear.click().catch(() => {});
    await sleep(1500);
  } else {
    await search.fill('').catch(() => {});
    await page.getByRole('button', { name: /^搜索$/ }).first().click().catch(() => {});
    await sleep(1500);
  }
}

async function waitForRecordContract(state, sinceIndex, timeout = 30000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    for (let index = state.contracts.length - 1; index >= sinceIndex; index -= 1) {
      const row = state.contracts[index];
      if (row && Number(row.mainData && row.mainData.id) > 0) return row;
    }
    await sleep(300);
  }
  return null;
}

async function openFirstRecord(page, state, presentation) {
  const since = state.contracts.length;
  if (presentation === 'kanban') {
    const card = page.locator('[data-semantic-component="CollectionKanbanRecordCard"]:visible').first();
    if (!(await card.count())) return null;
    await card.click();
  } else {
    const cell = page.locator('button[data-semantic-cell-kind="primary"]:visible').first();
    if (!(await cell.count())) return null;
    await cell.click();
  }
  await sleep(1200);
  return await waitForRecordContract(state, since);
}

// One entry's full read-only journey. Kept as a single unit so that a locator
// timeout or an unexpected DOM shape fails only this entry and the batch keeps
// covering its siblings.
async function runEntry(page, state, row, behaviour, sessionCompany) {
  const entryKey = row.menu_xmlid;
  const navTarget = findReleasedNavigationTarget(state.nav, row.action_xmlid);
  if (!navTarget) {
    fail(`${entryKey}: the acting role's released navigation does not contain ${row.action_xmlid}`);
    return { entry: entryKey, label: row.label, status: 'unreachable' };
  }
  const presentation = behaviour.presentation === 'kanban' ? 'kanban' : 'table';
  const status = await openEntryList(page, navTarget, presentation);
  const record = {
    entry: entryKey, label: row.label, menu_id: navTarget.menu_id,
    action_id: navTarget.action_id, presentation, list_status: status,
  };
  if (status === 'error') {
    fail(`${entryKey}: entry list rendered the declared error state`);
    return record;
  }
  if (status === 'loading') {
    fail(`${entryKey}: entry list never left the declared loading state`);
    return record;
  }
  await readPaging(page, entryKey, presentation);
  const rendered = await renderedRecordCount(page, presentation);
  record.records_rendered = rendered;
  if (status === 'ok' && rendered < 1) {
    fail(`${entryKey}: declared collection state ok but no declared record surface was rendered`);
  }
  if (status === 'ok' && rendered > 0) {
    const term = presentation === 'kanban' ? await firstKanbanCardText(page) : await firstRowText(page);
    if (term) await searchAndVerify(page, entryKey, term, presentation);
  }
  if (behaviour.detail) {
    const contract = await openFirstRecord(page, state, presentation);
    if (!contract) {
      fail(`${entryKey}: record ui.contract.v2 envelope was not observed after opening the first row`);
    } else {
      const companyId = Number(contract.mainData.company_id || 0) || null;
      record.record_id = Number(contract.mainData.id);
      record.record_company_id = companyId;
      record.workflow_actions = contract.workflow && Array.isArray(contract.workflow.availableActions)
        ? contract.workflow.availableActions.map((action) => String((action && action.key) || '')).filter(Boolean)
        : null;
      if (sessionCompany && companyId && companyId !== sessionCompany) {
        fail(`${entryKey}: record company ${companyId} != session company ${sessionCompany}`);
      }
      if (behaviour.expect_write === true && !(record.workflow_actions && record.workflow_actions.length)) {
        fail(`${entryKey}: overlay declares a mutating expectation but the record contract offers no action`);
      }
    }
  }
  return record;
}

async function deniedRoleNavigation(deniedRole) {
  const context = await browser.newContext({ locale: 'zh-CN' });
  const page = await context.newPage();
  const state = { user: null, nav: null, contracts: [] };
  attachCapture(page, state);
  try {
    await page.goto(`${BASE}/login?db=${DB}`, { waitUntil: 'networkidle' });
    const inputs = page.locator('input');
    await inputs.nth(0).fill(deniedRole);
    await inputs.nth(1).fill(PASSWORD);
    await page.getByRole('button', { name: /^登录$/ }).click();
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 30000 });
    await page.waitForTimeout(2500);
    const deadline = Date.now() + 15000;
    while (Date.now() < deadline && !state.nav) await sleep(300);
    return state;
  } catch (error) {
    return { ...state, error: String(error && error.message) };
  } finally {
    await context.close().catch(() => {});
  }
}

async function main() {
  if (!BASE) throw new Error('SC_ACCEPTANCE_FRONTEND_URL is required');
  if (!EXPECTED_SHA) throw new Error('SC_ACCEPTANCE_TARGET_SHA is required');
  if (!LOGIN || !PASSWORD) throw new Error('ACCEPTANCE_LOGIN and ACCEPTANCE_PASSWORD are required');

  const matrix = loadMatrix();
  const overlay = loadOverlay();
  const selected = selectEntries(matrix, overlay);
  if (!selected.length) throw new Error('no entry selected from the matrix (check SC_ENTRY_MATRIX_DOMAIN / KEYS)');
  const mutating = selected.filter((entry) => entry.behaviour.expect_write === true);
  if (mutating.length && WRITE_CONFIRM !== WRITE_CONFIRM_TOKEN) {
    throw new Error(
      `selected entries declare a mutating expectation; set SC_ENTRY_WRITE_CONFIRM=${WRITE_CONFIRM_TOKEN}`,
    );
  }

  const served = await servedRevision();
  const servedRevisionId = String(
    served.source_revision || served.git_sha || served.revision || served.sha || '',
  );
  if (servedRevisionId !== EXPECTED_SHA) {
    throw new Error(`served revision ${servedRevisionId || 'unknown'} != SC_ACCEPTANCE_TARGET_SHA ${EXPECTED_SHA}`);
  }
  if (String(served.database || '') !== DB) {
    throw new Error(`served database ${served.database} != ${DB}`);
  }

  browser = await launchChromium({ headless: true });
  const context = await browser.newContext({ locale: 'zh-CN' });
  const page = await context.newPage();
  const state = { user: null, nav: null, contracts: [] };
  attachCapture(page, state);

  await login(page);
  {
    const deadline = Date.now() + 15000;
    while (Date.now() < deadline && (!state.nav || !state.user)) await sleep(300);
  }
  const sessionCompany = state.user ? Number(state.user.company_id) : null;
  if (!state.nav) throw new Error('released navigation was not observed from system.init');

  const summary = [];
  for (const { row, behaviour } of selected) {
    const entryKey = row.menu_xmlid;
    const sinceConsole = consoleErrors.length;
    let record;
    try {
      record = await runEntry(page, state, row, behaviour, sessionCompany);
    } catch (error) {
      // A single entry must not abort the whole declaration matrix: bind the
      // failure to this entry and keep covering its siblings.
      fail(`${entryKey}: entry check raised ${String((error && error.message) || error)}`);
      record = { entry: entryKey, label: row.label, status: 'exception' };
    }
    record.console_errors = consoleErrors.slice(sinceConsole);
    summary.push(record);
    await page.goto(`${BASE}/`, { waitUntil: 'networkidle' }).catch(() => {});
  }

  for (const deniedRole of [...new Set(selected.map((entry) => entry.behaviour.denied_role).filter(Boolean))]) {
    const denied = await deniedRoleNavigation(deniedRole);
    const leaked = [];
    for (const { row } of selected) {
      if (findReleasedNavigationTarget(denied.nav || [], row.action_xmlid)) leaked.push(row.action_xmlid);
    }
    observations.push({
      stage: 'authority_negative',
      login: deniedRole,
      navigation_observed: Boolean(denied.nav),
      leaked_entries: leaked,
      error: denied.error || null,
    });
    if (!denied.nav) {
      fail(`authority: ${deniedRole} released navigation was not observed (${denied.error || 'unknown'})`);
    } else if (leaked.length) {
      fail(`authority: ${deniedRole} holds none of the declared groups yet received ${leaked.join(', ')}`);
    }
  }

  fs.mkdirSync(OUT_DIR, { recursive: true });
  const ok = problems.length === 0;
  const output = {
    schema: 'business_entry_matrix_browser.v1',
    generated_at: new Date().toISOString(),
    target_sha: EXPECTED_SHA,
    served_revision: servedRevisionId,
    base_url: BASE,
    database: DB,
    login: LOGIN,
    session_company_id: sessionCompany,
    selection: {
      domain: DOMAIN_FILTER || null,
      keys: KEYS_FILTER,
      entries: selected.map((entry) => entry.row.menu_xmlid),
      mutating: mutating.map((entry) => entry.row.menu_xmlid),
    },
    entries: summary,
    observations,
    console_errors: consoleErrors,
    problems,
    ok,
  };
  fs.writeFileSync(path.join(OUT_DIR, 'summary.json'), `${JSON.stringify(output, null, 2)}\n`);
  process.stdout.write(`[business-entry-matrix] ok=${ok} entries=${summary.length} problems=${problems.length} console_errors=${consoleErrors.length}\n`);
  for (const problem of problems) process.stdout.write(`  - ${problem}\n`);
  for (const error of consoleErrors.slice(0, 10)) process.stdout.write(`  ! ${error}\n`);
  if (browser) await browser.close().catch(() => {});
  process.exit(ok ? 0 : 1);
}

main().catch(async (error) => {
  fail(`fatal: ${String((error && error.message) || error)}`);
  try {
    fs.mkdirSync(OUT_DIR, { recursive: true });
    fs.writeFileSync(path.join(OUT_DIR, 'summary.json'), `${JSON.stringify({
      schema: 'business_entry_matrix_browser.v1',
      generated_at: new Date().toISOString(),
      target_sha: EXPECTED_SHA,
      problems,
      console_errors: consoleErrors,
      ok: false,
      fatal: true,
    }, null, 2)}\n`);
  } catch { /* best effort */ }
  process.stdout.write(`[business-entry-matrix] FATAL ${problems.join(' | ')}\n`);
  if (browser) await browser.close().catch(() => {});
  process.exit(1);
});
