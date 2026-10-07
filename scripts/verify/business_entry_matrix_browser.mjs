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
const EXPOSURE_REGISTRY_PATH = process.env.SC_ENTRY_MATRIX_EXPOSURE_REGISTRY
  || 'config/frontend/role_surface_exposure_declarations_v1.json';
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

// Count the released navigation targets a principal actually received. A node
// only carries a route when the runtime published a positive action_id/menu_id
// pair; a candidate that received none cannot support a denial, because "the
// entry is absent" would be vacuously true rather than exercised.
function countReleasedNavigationTargets(nav) {
  const pending = Array.isArray(nav) ? [...nav] : [];
  let count = 0;
  while (pending.length) {
    const node = pending.shift();
    if (!node || typeof node !== 'object') continue;
    const meta = node.meta && typeof node.meta === 'object' ? node.meta : {};
    const actionId = Number(node.action_id || meta.action_id || 0);
    const menuId = Number(node.menu_id || meta.menu_id || 0);
    if (actionId > 0 && menuId > 0) count += 1;
    if (Array.isArray(node.children)) pending.push(...node.children);
  }
  return count;
}

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
    deniedRoleCandidates: Array.isArray(body.denied_role_candidates)
      ? body.denied_role_candidates.map(String)
      : [],
  };
}

// The governed exposure registry already adjudicates entries that exist but are
// deliberately not delivered to any business role, and entries whose authority
// is still pending runtime resolution. The probe consumes that declaration
// instead of re-deriving a second opinion; it never relaxes an
// authorization/ACL/field-permission assertion and never invents a pass.
function loadExposureRegistry() {
  const body = JSON.parse(fs.readFileSync(EXPOSURE_REGISTRY_PATH, 'utf8'));
  const declared = new Map();
  const unauthored = Array.isArray(body.capability_reachable_by_no_role)
    ? body.capability_reachable_by_no_role : [];
  for (const key of unauthored) {
    declared.set(String(key), {
      kind: 'capability_reachable_by_no_role',
      reason: String(body.capability_reachable_by_no_role_reason || ''),
    });
  }
  const pending = body.authority_pending_entries && typeof body.authority_pending_entries === 'object'
    ? body.authority_pending_entries : {};
  for (const [key, reason] of Object.entries(pending)) {
    declared.set(String(key), { kind: 'authority_pending', reason: String(reason || '') });
  }
  return {
    source: EXPOSURE_REGISTRY_PATH,
    policy: String(body.policy || ''),
    declared,
    unauthored_count: unauthored.length,
    pending_count: Object.keys(pending).length,
  };
}

function overlayFor(overlay, menuXmlid) {
  const merged = { ...overlay.defaults, ...(overlay.entries[menuXmlid] || {}) };
  if (!('detail' in merged)) merged.detail = true;
  if (!('expect_write' in merged)) merged.expect_write = null;
  return merged;
}

function declaredEntryGroups(row) {
  try {
    const parsed = JSON.parse(String(row.role_authority || '{}'));
    if (Array.isArray(parsed.action_groups) && parsed.action_groups.length) {
      return parsed.action_groups.map(String);
    }
    if (Array.isArray(parsed.menu_chain)) {
      return [...new Set(parsed.menu_chain
        .flatMap((node) => (node && Array.isArray(node.groups) ? node.groups : []))
        .map(String))];
    }
    return [];
  } catch {
    return [];
  }
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
    if (intent === 'login') {
      // The runtime declares the acting principal's full capability closure
      // (`principal.role_xmlids`, external ids of every effective group) in the
      // login envelope. The negative-authority case reads it from here rather
      // than from a hand-kept role map.
      try {
        const body = await response.json();
        const data = envelopeData(body);
        const principal = data && data.principal;
        if (principal && Array.isArray(principal.role_xmlids)) {
          state.roleXmlids = principal.role_xmlids.map(String);
        }
      } catch { /* identity stays null and the probe fails closed */ }
      return;
    }
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
      const params = (payload && payload.params) || {};
      const mainData = (data && data.dataContract && data.dataContract.mainData) || {};
      state.contracts.push({
        url: response.url(),
        op: String(params.op || ''),
        model: String(params.model || ''),
        view_type: String(params.view_type || ''),
        render_profile: String(params.render_profile || ''),
        mainData,
        mainDataKeys: Object.keys(mainData),
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

// The runtime, not the probe, declares an entry's presentation. It publishes
// that declaration on the surfaces it renders: `data-product-page-mode` on the
// page root and `data-surface-semantic` on the action surface renderer host.
// The probe reads the declaration and binds it to the owning presentation
// adapter below; it never assumes a table and never guesses from the URL.
//
// Each adapter owns the declared readiness attribute, the declared record
// surface, the declared empty-state surface and the record-open gesture for one
// presentation kind. A selector is a locator, never the proof: the proof is the
// declared state attribute plus the declaration-versus-behaviour binding.
const PRESENTATIONS = {
  table: {
    csvTokens: ['tree:table'],
    surfaceSelector: '[data-semantic-component="ListPage"][data-list-status]',
    stateAttribute: 'data-list-status',
    emptySurfaceSelector: '[data-semantic-component="ScEmptyState"][data-state="empty"]',
    recordSelector: 'button[data-semantic-cell-kind="primary"]:visible',
    expectsRecords: true,
  },
  kanban: {
    csvTokens: ['kanban:', 'tree:kanban'],
    surfaceSelector: '[data-semantic-component="KanbanPage"][data-collection-state]',
    stateAttribute: 'data-collection-state',
    emptySurfaceSelector: '[data-semantic-component="ScEmptyState"][data-state="empty"]',
    recordSelector: '[data-semantic-component="CollectionKanbanRecordCard"]:visible',
    recordTextSelector: 'h3.collection-kanban-record-card__title',
    expectsRecords: true,
  },
  hierarchical: {
    csvTokens: ['tree:hierarchical_worksheet', 'tree:hierarchy'],
    surfaceSelector: '[data-semantic-component="HierarchicalWorksheet"][data-state]',
    stateAttribute: 'data-state',
    emptySurfaceSelector: '[data-semantic-component="ScEmptyState"][data-state="empty"]',
    recordSelector: '[data-semantic-component="HierarchicalWorksheet"] [data-record-id]:not([data-record-id=""])',
    recordTextSelector: 'td',
    recordOpenGesture: 'select_then_action',
    expectsRecords: true,
  },
  form: {
    csvTokens: ['form:form_structure'],
    surfaceSelector: '[data-semantic-component="ContractFormPage"][data-product-page-mode="form"][data-state]',
    stateAttribute: 'data-state',
    emptySurfaceSelector: null,
    recordSelector: null,
    expectsRecords: false,
  },
  // A page can override its action's tree/form surface through the action
  // context (`sc_web_route`); the runtime then publishes the page-mode
  // declaration on the page root. The adapter only reads that declaration.
  admin: {
    csvTokens: ['admin:business_config_surface'],
    surfaceSelector: '[data-product-page-mode="admin"]',
    stateAttribute: 'data-page-sections-ready',
    emptySurfaceSelector: null,
    recordSelector: null,
    expectsRecords: false,
  },
  aggregate: {
    csvTokens: ['pivot:', 'graph:'],
    surfaceSelector: '[data-semantic-component="ActionView"][data-collection-state]',
    stateAttribute: 'data-collection-state',
    emptySurfaceSelector: '[data-semantic-component="ScEmptyState"][data-state="empty"]',
    recordSelector: null,
    readableRowSelector: '[data-semantic-component="ActionView"] table tbody tr',
    expectsRecords: false,
  },
};

// Runtime-declared surface semantic → presentation adapter. The semantic is the
// one the renderer registry publishes
// (frontend/apps/web/src/app/renderers/actionSurfaceRendererRegistry.ts), so
// this table mirrors a declared system registry instead of a page guess.
const SEMANTIC_PRESENTATIONS = {
  table: 'table',
  card: 'kanban',
  workflow_board: 'kanban',
  hierarchy_browser: 'hierarchical',
  hierarchy_planner: 'hierarchical',
  hierarchical_worksheet: 'hierarchical',
  pivot: 'aggregate',
  graph: 'aggregate',
  calendar: 'aggregate',
  gantt: 'aggregate',
  activity: 'aggregate',
  dashboard: 'aggregate',
};

function presentationSpec(presentation) {
  return PRESENTATIONS[presentation] || PRESENTATIONS.table;
}

function presentationSurface(page, presentation) {
  return page.locator(presentationSpec(presentation).surfaceSelector).last();
}

async function presentationStatus(page, presentation) {
  const spec = presentationSpec(presentation);
  return String((await presentationSurface(page, presentation).getAttribute(spec.stateAttribute)) || '');
}

async function rendererHostDeclaration(page) {
  const host = page.locator('.action-surface-renderer-host[data-surface-semantic]').first();
  if (!(await host.count())) return null;
  return {
    semantic: String((await host.getAttribute('data-surface-semantic')) || ''),
    requested: String((await host.getAttribute('data-requested-renderer')) || ''),
    active: String((await host.getAttribute('data-active-renderer')) || ''),
    status: String((await host.getAttribute('data-renderer-status')) || ''),
  };
}

// Page-mode declarations that a runtime page root can publish. This mirrors the
// declarations the product ships (ContractFormPage, BusinessConfigSurfaceView),
// never an entry-specific special case.
const PRODUCT_PAGE_MODES = {
  form: 'form',
  admin: 'admin',
};

// Read the presentation the runtime declares, in the order the product
// publishes it: an explicit page-mode declaration, then the action surface
// renderer host, then whichever declared record surface is attached.
async function detectPresentation(page) {
  for (const [mode, presentation] of Object.entries(PRODUCT_PAGE_MODES)) {
    const node = page.locator(`[data-product-page-mode="${mode}"]`).first();
    if (await node.count()) {
      return { presentation, declaredBy: `[data-product-page-mode="${mode}"]`, semantic: null };
    }
  }
  const host = await rendererHostDeclaration(page);
  if (host && SEMANTIC_PRESENTATIONS[host.semantic]) {
    return {
      presentation: SEMANTIC_PRESENTATIONS[host.semantic],
      declaredBy: `action-surface-renderer-host[data-surface-semantic="${host.semantic}"]`,
      semantic: host.semantic,
      host,
    };
  }
  for (const candidate of ['hierarchical', 'kanban', 'table']) {
    if (await page.locator(PRESENTATIONS[candidate].surfaceSelector).count()) {
      return { presentation: candidate, declaredBy: PRESENTATIONS[candidate].surfaceSelector, semantic: null };
    }
  }
  return { presentation: null, declaredBy: null, semantic: null };
}

async function navigateEntry(page, navTarget) {
  await page.goto(`${BASE}/a/${navTarget.action_id}?menu_id=${navTarget.menu_id}`, { waitUntil: 'networkidle' });
  await sleep(900);
}

async function awaitPresentation(page, presentation) {
  const spec = presentationSpec(presentation);
  const surface = presentationSurface(page, presentation);
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

// The rendered record count is read from the declared record surface of the
// active presentation: table rows carry `data-semantic-cell-kind="primary"`,
// kanban records are the declared `CollectionKanbanRecordCard` nodes,
// hierarchical worksheet rows declare `data-record-id`.
async function renderedRecordCount(page, presentation) {
  const spec = presentationSpec(presentation);
  if (!spec.recordSelector) return 0;
  return await page.locator(spec.recordSelector).count();
}

async function firstRecordText(page, presentation) {
  const spec = presentationSpec(presentation);
  if (!spec.recordSelector) return '';
  const node = page.locator(spec.recordSelector).first();
  if (!(await node.count())) return '';
  if (spec.recordTextSelector) {
    const parts = node.locator(spec.recordTextSelector);
    const count = Math.min(await parts.count(), 6);
    for (let index = 0; index < count; index += 1) {
      const text = String((await parts.nth(index).textContent().catch(() => '')) || '').trim();
      if (text) return text;
    }
  }
  for (const attribute of ['title', 'aria-label']) {
    const value = await node.getAttribute(attribute);
    if (value && value.trim()) return value.trim();
  }
  return String((await node.textContent().catch(() => '')) || '').trim();
}

// The declared search surface is the collection header search field: ListPage
// emits `input[placeholder*="搜索关键字"]`, the product list header emits
// `input[type="search"]`. Both are the same declared query control.
function declaredSearchInput(page) {
  return page.locator('input[type="search"]:visible, input[placeholder*="搜索"]:visible').first();
}

async function searchAndVerify(page, entryKey, term, presentation) {
  const search = declaredSearchInput(page);
  if (!(await search.count())) {
    fail(`${entryKey}: entry list did not expose the declared search field`);
    return;
  }
  await search.fill(term);
  await page.getByRole('button', { name: /^搜索$/ }).first().click();
  await sleep(3500);
  const status = await presentationStatus(page, presentation);
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

// A form workspace (create/edit) declares its record through a model contract
// envelope (`op=model`), not through a first-row open. Its mainData carries the
// declared default field values, which is exactly the read-back the form
// entries claim.
async function waitForModelContract(state, sinceIndex, model, timeout = 20000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    for (let index = state.contracts.length - 1; index >= sinceIndex; index -= 1) {
      const row = state.contracts[index];
      if (row && row.op === 'model' && (!model || row.model === model)) return row;
    }
    await sleep(300);
  }
  return null;
}

async function openFirstRecord(page, state, presentation) {
  const spec = presentationSpec(presentation);
  if (!spec.recordSelector) return null;
  const node = page.locator(spec.recordSelector).first();
  if (!(await node.count())) return null;
  const since = state.contracts.length;
  const gesture = spec.recordOpenGesture || 'click';
  if (gesture === 'select_then_action') {
    // The worksheet selects a row on a single click and publishes a declared
    // `record.open` action for the selected row; a double click opens directly.
    await node.click();
    await sleep(500);
    const openAction = page.locator('[data-semantic-action="record.open"]:visible').first();
    if (await openAction.count()) await openAction.click();
    else await node.dblclick();
  } else if (gesture === 'dblclick') {
    await node.dblclick();
  } else {
    await node.click();
  }
  await sleep(1500);
  return await waitForRecordContract(state, since);
}

// Bind a record ui.contract.v2 envelope to the entry result. Company and
// declared workflow actions are read from the envelope, never invented.
function applyRecordContract(record, contract, behaviour, sessionCompany, entryKey) {
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

// One entry's full read-only journey. Kept as a single unit so that a locator
// timeout or an unexpected DOM shape fails only this entry and the batch keeps
// covering its siblings.
async function runEntry(page, state, row, behaviour, sessionCompany) {
  const entryKey = row.menu_xmlid;
  const navTarget = findReleasedNavigationTarget(state.nav, row.action_xmlid);
  if (!navTarget) {
    const declaration = state.exposureDeclared.get(entryKey);
    if (declaration) {
      // The governed registry declares this entry as existing but not delivered
      // to any business role (or awaiting runtime authority resolution). The
      // absence is therefore a registered declaration, not a probe failure; it
      // is recorded with its registry reason and never counted as a pass.
      observations.push({
        entry: entryKey, stage: 'exposure_declaration', status: 'declared',
        kind: declaration.kind, reason: declaration.reason,
        source: state.exposureSource,
      });
      return {
        entry: entryKey, label: row.label, status: 'declared',
        declaration: declaration.kind,
      };
    }
    fail(`${entryKey}: the acting role's released navigation does not contain ${row.action_xmlid}`);
    return { entry: entryKey, label: row.label, status: 'unreachable' };
  }
  const contractBaseline = state.contracts.length;
  await navigateEntry(page, navTarget);
  const detected = await detectPresentation(page);
  const presentation = detected.presentation;
  if (!presentation) {
    fail(`${entryKey}: the runtime declared no recognised presentation surface (declared by ${detected.declaredBy || 'nothing'})`);
    return { entry: entryKey, label: row.label, menu_id: navTarget.menu_id, action_id: navTarget.action_id, status: 'unknown-presentation' };
  }
  if (detected.host) {
    observations.push({
      entry: entryKey, stage: 'renderer', semantic: detected.host.semantic,
      requested: detected.host.requested, active: detected.host.active, status: detected.host.status,
    });
    if (detected.host.status === 'unsupported') {
      fail(`${entryKey}: runtime declared an unsupported action surface renderer (${detected.host.requested || detected.host.semantic})`);
    }
  }
  // Declaration-versus-behaviour: the presentation the runtime activated must be
  // one the entry declares in its rendering_path, and an overlay that names a
  // presentation must agree with what the runtime declared.
  const declaredPath = String(row.rendering_path || '');
  if (declaredPath && !presentationSpec(presentation).csvTokens.some((token) => declaredPath.includes(token))) {
    fail(`${entryKey}: runtime activated presentation "${presentation}" (${detected.declaredBy}) not declared in rendering_path: ${declaredPath}`);
  }
  if (behaviour.presentation && behaviour.presentation !== presentation) {
    fail(`${entryKey}: overlay declares presentation "${behaviour.presentation}" but the runtime activated "${presentation}" (${detected.declaredBy})`);
  }
  const spec = presentationSpec(presentation);
  const status = await awaitPresentation(page, presentation);
  const record = {
    entry: entryKey, label: row.label, menu_id: navTarget.menu_id,
    action_id: navTarget.action_id, presentation, list_status: status,
  };
  if (status === 'error') {
    fail(`${entryKey}: ${presentation} surface rendered the declared error state`);
    return record;
  }
  if (status === 'loading') {
    fail(`${entryKey}: ${presentation} surface never left the declared loading state`);
    return record;
  }
  await readPaging(page, entryKey, presentation);
  const rendered = await renderedRecordCount(page, presentation);
  record.records_rendered = rendered;
  if (spec.expectsRecords && status === 'ok' && rendered < 1) {
    fail(`${entryKey}: declared collection state ok but no declared record surface was rendered`);
  }
  if (spec.expectsRecords && status === 'empty' && rendered > 0) {
    fail(`${entryKey}: declared collection state empty but ${rendered} record surface(s) were rendered`);
  }
  if (presentation === 'aggregate') {
    // A report entry declares a pivot/graph surface; the product still promises
    // a readable records surface. Record its declared state and readable rows.
    const readableRows = await page.locator(spec.readableRowSelector || '').count().catch(() => 0);
    record.readable_rows = readableRows;
    observations.push({
      entry: entryKey, stage: 'aggregate_surface', state: status, readable_rows: readableRows,
      active_renderer: detected.host ? detected.host.active : null,
    });
  }
  // When the declared surface publishes `empty` the product is stating there is
  // no record to open. Lock that declaration to the rendered behaviour: the
  // surface must give way to the declared empty-state component. This is a
  // declaration→behaviour binding, not a selector-literal assertion.
  if (status === 'empty') {
    let emptyStateRendered = true;
    if (spec.emptySurfaceSelector) emptyStateRendered = (await page.locator(spec.emptySurfaceSelector).count()) > 0;
    observations.push({
      entry: entryKey, stage: 'empty_state',
      declared: `${spec.stateAttribute}=empty`, empty_state_component: emptyStateRendered,
    });
    if (!emptyStateRendered) {
      fail(`${entryKey}: surface declared empty but no declared empty-state component was rendered`);
    }
  }
  if (spec.searchable !== false && status === 'ok' && rendered > 0) {
    const term = await firstRecordText(page, presentation);
    if (term) await searchAndVerify(page, entryKey, term, presentation);
  }
  if (behaviour.detail) {
    if (presentation === 'form') {
      // A form workspace declares its record through the model contract
      // envelope: the surface declares the model, and the contract carries the
      // declared default field values (create) or the declared record (edit).
      const surface = page.locator(PRESENTATIONS.form.surfaceSelector).first();
      const formModel = String((await surface.getAttribute('data-form-model')) || '');
      const formRecord = String((await surface.getAttribute('data-form-record')) || '');
      record.form_model = formModel;
      record.form_record = formRecord;
      if (row.model && formModel && formModel !== row.model) {
        fail(`${entryKey}: form surface declared model ${formModel} != matrix model ${row.model}`);
      }
      const envelope = await waitForModelContract(state, contractBaseline, row.model || formModel);
      if (!envelope) {
        fail(`${entryKey}: form surface published no declared model contract envelope (ui.contract.v2 op=model)`);
      } else {
        record.contract_view_type = envelope.view_type;
        record.contract_render_profile = envelope.render_profile;
        record.main_data_fields = envelope.mainDataKeys;
        if (formRecord === 'new') {
          if (envelope.render_profile !== 'create') {
            fail(`${entryKey}: create workspace declared render_profile=${envelope.render_profile || 'unknown'}, not create`);
          }
          if (!envelope.mainDataKeys.length) {
            fail(`${entryKey}: create workspace model contract declared no default field values`);
          }
        } else if (Number(envelope.mainData.id || 0) !== Number(formRecord)) {
          fail(`${entryKey}: form contract mainData id ${envelope.mainData.id} != declared form record ${formRecord}`);
        }
      }
    } else if (!spec.expectsRecords) {
      // An aggregated report surface has no declared first row to open; read
      // back whichever record ui.contract.v2 envelope this entry produced
      // instead of fabricating a row.
      const contract = await waitForRecordContract(state, contractBaseline);
      if (!contract) {
        observations.push({
          entry: entryKey, stage: 'detail', skipped: true,
          reason: `${presentation} surface published no record ui.contract.v2 envelope`,
        });
      } else {
        applyRecordContract(record, contract, behaviour, sessionCompany, entryKey);
      }
    } else if (rendered < 1) {
      // The declared collection published no record surface, so there is no
      // first row to open by design (a legitimate empty state for the acting
      // company's data). Record the skipped read-back instead of fabricating a
      // failure; the readiness/empty declaration above already locked the fact.
      observations.push({
        entry: entryKey, stage: 'detail', skipped: true,
        reason: `declared collection state ${status || 'unknown'} rendered ${rendered} record surface(s)`,
      });
    } else {
      const contract = await openFirstRecord(page, state, presentation);
      if (!contract) {
        fail(`${entryKey}: record ui.contract.v2 envelope was not observed after opening the first row`);
      } else {
        applyRecordContract(record, contract, behaviour, sessionCompany, entryKey);
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
  const exposure = loadExposureRegistry();
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
  const state = {
    user: null, nav: null, contracts: [], roleXmlids: null,
    exposureDeclared: exposure.declared, exposureSource: exposure.source,
  };
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

  // Negative authority is declared by the runtime, never by a hand-kept map.
  // The login envelope publishes the acting principal's full capability closure
  // (`principal.role_xmlids`), so a candidate is a valid negative for an entry
  // only when that closure is disjoint from the entry's declared groups.
  const candidateRoles = overlay.deniedRoleCandidates;
  const candidateState = new Map();
  for (const role of candidateRoles) {
    if (candidateState.has(role)) continue;
    const observed = await deniedRoleNavigation(role);
    if (!observed.nav && observed.error) {
      fail(`authority: ${role} login/navigation failed (${observed.error})`);
    }
    if (!Array.isArray(observed.roleXmlids) || !observed.roleXmlids.length) {
      fail(`authority: ${role} login envelope declared no capability closure (principal.role_xmlids)`);
    }
    // A candidate is only a valid negative baseline when the runtime actually
    // released navigation targets to it. An empty nav tree makes "the entry is
    // absent" vacuously true, which would fabricate a denial that was never
    // exercised, so such a candidate is ineligible rather than a denial.
    const releasedTargets = countReleasedNavigationTargets(observed.nav);
    candidateState.set(role, {
      ...observed,
      released_targets: releasedTargets,
      eligible: releasedTargets > 0,
    });
  }
  for (const role of candidateRoles) {
    const candidate = candidateState.get(role);
    if (candidate && !candidate.eligible) {
      observations.push({
        stage: 'authority_negative_candidate',
        login: role,
        eligible: false,
        released_navigation_targets: candidate.released_targets || 0,
        capability_closure_size: (candidate.roleXmlids || []).length,
        reason: 'runtime released no navigation target to the candidate, so a denial cannot be distinguished from a missing navigation',
      });
    }
  }
  const negativeByRole = new Map();
  const candidateClosures = candidateRoles
    .map((role) => candidateState.get(role))
    .filter((candidate) => candidate && candidate.eligible)
    .map((candidate) => candidate.roleXmlids)
    .filter((caps) => Array.isArray(caps) && caps.length);
  const universalCaps = candidateClosures.length
    ? candidateClosures.reduce((acc, caps) => acc.filter((cap) => caps.includes(cap)))
    : [];
  for (const { row, behaviour } of selected) {
    const declared = declaredEntryGroups(row);
    if (!declared.length) {
      observations.push({
        stage: 'authority_negative', entry: row.menu_xmlid, skipped: true,
        reason: 'entry role_authority declares no group to deny',
      });
      continue;
    }
    const pinned = behaviour.denied_role ? String(behaviour.denied_role) : null;
    let chosen = null;
    for (const role of candidateRoles) {
      if (pinned && role !== pinned) continue;
      const candidate = candidateState.get(role);
      if (!candidate || !candidate.eligible) continue;
      const caps = Array.isArray(candidate.roleXmlids) ? candidate.roleXmlids : [];
      if (!caps.length) continue;
      if (!caps.some((cap) => declared.includes(cap))) { chosen = role; break; }
    }
    if (!chosen) {
      const blocking = declared.filter((cap) => universalCaps.includes(cap));
      observations.push({
        stage: 'authority_negative', entry: row.menu_xmlid, skipped: true,
        declared_groups: declared,
        baseline_groups: blocking,
        reason: 'no eligible denied-role candidate declares a capability closure disjoint from the entry declared groups',
      });
      continue;
    }
    if (!negativeByRole.has(chosen)) negativeByRole.set(chosen, []);
    negativeByRole.get(chosen).push({ action: row.action_xmlid, menu: row.menu_xmlid });
  }
  let negativeChecked = 0;
  for (const [deniedRole, entries] of negativeByRole) {
    const observed = candidateState.get(deniedRole);
    const leaked = entries
      .filter((item) => findReleasedNavigationTarget(observed.nav || [], item.action))
      .map((item) => item.action);
    negativeChecked += entries.length;
    observations.push({
      stage: 'authority_negative',
      login: deniedRole,
      capability_closure_size: (observed.roleXmlids || []).length,
      navigation_observed: Boolean(observed.nav),
      checked_entries: entries.length,
      leaked_entries: leaked,
    });
    if (leaked.length) {
      fail(`authority: ${deniedRole} capability closure is disjoint from the declared groups yet received ${leaked.join(', ')}`);
    }
  }
  observations.push({
    stage: 'authority_negative_summary',
    candidates: candidateRoles,
    checked_entries: negativeChecked,
    uncovered_entries: selected.length - negativeChecked,
  });
  if (selected.length - negativeChecked > 0) {
    fail(`authority: ${selected.length - negativeChecked} selected entries have no eligible denied-role candidate whose released navigation was observed and whose capability closure is disjoint from the declared groups`);
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
