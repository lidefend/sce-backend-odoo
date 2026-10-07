#!/usr/bin/env node
// Focused product-surface acceptance for the 日常合同 formal business entry
// (sc.general.contract). The correctness anchor is the runtime contract, not a
// duplicated local declaration: the probe captures the record's `ui.contract.v2`
// envelope and the startup `system.init` identity, then drives exactly the
// transitions `workflowContract.availableActions` declares for the state the
// runtime reports, asserting the declared successor `rawState` after every
// refresh. A CSS selector string, a pixel literal or a handler-level diagnosis
// is never treated as proof.
//
// Registered environment: external daily development server
//   config/frontend/acceptance_environments_v1.json profiles.daily
//   ENV=dev, database sc_demo, expected served revision required.
// The owner explicitly authorized mutating the sc_demo acceptance fixture, so
// this lane fails closed unless the caller presents the explicit write token and
// a resolved record/company boundary. It never writes outside that boundary.
import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';

const BASE = (process.env.SC_ACCEPTANCE_FRONTEND_URL || process.env.FRONTEND_URL || '').replace(/\/$/, '');
const DB = process.env.SC_ACCEPTANCE_DATABASE || process.env.DB_NAME || 'sc_demo';
const LOGIN = process.env.ACCEPTANCE_LOGIN || '';
const PASSWORD = process.env.ACCEPTANCE_PASSWORD || '';
const EXPECTED_SHA = process.env.SC_ACCEPTANCE_TARGET_SHA || '';
const RECORD_XMLID = (process.env.SC_ENTRY_RECORD_XMLID || 'smart_construction_acceptance_fixture.fe_general_contract_carrier').trim();
const RESOLUTION_PATH = process.env.ACCEPTANCE_RECORD_RESOLUTION || '';
// 'list' drives the declared product entry (menu -> list -> search -> open record);
// 'record' is a bounded diagnostic that opens the record route directly.
const ENTRY_MODE = (process.env.SC_ENTRY_ENTRY_MODE || 'list').trim();
// The role that holds none of this entry's declared groups. The negative case is
// only meaningful when the acting identity is a different, authorized role, so the
// probe refuses to run the pair against the same login.
const DENIED_ROLE_LOGIN = (process.env.SC_ENTRY_DENIED_ROLE_LOGIN || 'fixture_role_finance').trim();
// This lane mutates a real product record on an external environment, so it fails
// closed unless the caller presents the explicit write-authority token.
const WRITE_CONFIRM = process.env.SC_ENTRY_WRITE_CONFIRM || '';
const WRITE_CONFIRM_TOKEN = 'DRIVE_DAILY_SC_DEMO_GENERAL_CONTRACT';
// Read-only smoke: resolves and verifies the declared entry, then stops before the
// first mutating action. It never substitutes for the full walk and issues no pass.
const DRY_RUN = process.env.SC_ENTRY_DRY_RUN === '1';
const OUT_DIR = process.env.SC_ACCEPTANCE_OUTPUT_DIR || path.join('artifacts', 'frontend-business-entry-general-contract', String(Date.now()));
const MODEL = 'sc.general.contract';
const STATE_FIELD = 'state';
const START_STATE = 'draft';

// The canonical 日常合同 business ladder: the declared transition keys the entry
// must offer, each paired with the raw `state` the declaration says it produces.
// This names business states, never a selector string or a pixel value. The action
// method is never declared here: it is read from the runtime contract.
const CANONICAL_LADDER = [
  { action: 'submit', expect_state: 'confirmed' },
  { action: 'complete', expect_state: 'signed' },
];

const problems = [];
const observations = [];
const contracts = [];
let sessionUser = null;
let browser;
let context;

function fail(message) { problems.push(message); }
function sleep(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }

function readResolution() {
  if (!RESOLUTION_PATH) throw new Error('ACCEPTANCE_RECORD_RESOLUTION must point at the managed resolution body');
  const body = JSON.parse(fs.readFileSync(RESOLUTION_PATH, 'utf8'));
  // The resolution body is the canonical governed envelope
  // (schema/producer/expected_sha/targets); every consumer reads the same shape.
  const targets = body && body.targets;
  if (!targets || typeof targets !== 'object') {
    throw new Error('managed resolution is not the governed envelope (targets missing)');
  }
  const entry = targets.general_contract_carrier;
  if (!entry) throw new Error('managed resolution is missing general_contract_carrier');
  if (String(entry.record_xmlid || '') !== RECORD_XMLID) {
    throw new Error(`resolution record_xmlid ${entry.record_xmlid} != declared ${RECORD_XMLID}`);
  }
  for (const key of ['record_id', 'company_id', 'menu_id', 'action_id']) {
    if (!(Number(entry[key]) > 0)) throw new Error(`resolution ${key} is missing`);
  }
  const declared = (entry.declared_start_state && entry.declared_start_state[STATE_FIELD]) || null;
  if (declared !== START_STATE) {
    throw new Error(`resolution declared start ${STATE_FIELD}=${declared} != ${START_STATE}`);
  }
  return entry;
}

function envelopeData(body) {
  return (body && (body.data || (body.result && (body.result.data || body.result)))) || {};
}

function attachContractCapture(page) {
  page.on('response', async (response) => {
    const request = response.request();
    let payload = {};
    try { payload = JSON.parse(request.postData() || '{}'); } catch { return; }
    const intent = String(payload && payload.intent ? payload.intent : '');
    if (response.status() >= 400) return;
    if (intent === 'system.init' || intent === 'app.init') {
      try {
        const body = await response.json();
        const user = envelopeData(body).user;
        if (user && Number(user.company_id) > 0) sessionUser = user;
      } catch { /* identity stays null and the probe fails closed */ }
      return;
    }
    if (intent !== 'ui.contract.v2') return;
    try {
      const body = await response.json();
      const data = envelopeData(body);
      const workflow = data && data.workflowContract;
      if (!workflow || !Array.isArray(workflow.availableActions)) return;
      contracts.push({
        url: response.url(),
        mainData: (data && data.dataContract && data.dataContract.mainData) || {},
        pageInfo: (data && data.pageInfo) || {},
        layoutContract: (data && data.layoutContract) || {},
        workflow,
      });
    } catch { /* unparseable envelope is ignored, not trusted */ }
  });
}

function latestRecordContract(recordId) {
  for (let index = contracts.length - 1; index >= 0; index -= 1) {
    const row = contracts[index];
    if (row && Number(row.mainData && row.mainData.id) === recordId && row.workflow && row.workflow.stateField) return row;
  }
  return null;
}

async function waitForRecordContract(recordId, sinceIndex = 0, timeout = 30000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    for (let index = contracts.length - 1; index >= sinceIndex; index -= 1) {
      const row = contracts[index];
      if (row && Number(row.mainData && row.mainData.id) === recordId && row.workflow && row.workflow.stateField) return row;
    }
    await sleep(250);
  }
  throw new Error('record ui.contract.v2 envelope was not observed');
}

async function servedRevision() {
  const response = await fetch(`${BASE}/api/runtime-version`, { headers: { Accept: 'application/json' } });
  if (!response.ok) throw new Error(`runtime-version status=${response.status}`);
  return await response.json();
}

function recordState(contract) {
  const workflow = contract.workflow;
  const mainData = contract.mainData;
  const rawState = String(workflow.rawState || '');
  const declaredField = String(workflow.stateField || '');
  const mainState = String((mainData && mainData[declaredField]) || '');
  return {
    state_field: declaredField,
    raw_state: rawState,
    main_state: mainState,
    approval_phase: String(workflow.approvalPhase || ''),
    editability: String(workflow.editability || ''),
    company_id: Number((Array.isArray(mainData.company_id) ? mainData.company_id[0] : mainData.company_id) || 0) || null,
  };
}

function availableRows(contract) {
  return (contract.workflow.availableActions || [])
    .map((row) => ({
      key: String((row && row.key) || '').trim(),
      label: String((row && row.label) || '').trim(),
      method: String((row && row.method) || (row && row.target && row.target.method) || '').trim(),
      enabled: row.enabled !== false,
    }))
    .filter((row) => row.key && row.method);
}

// The published form structure is the authority for which field widgets the entry
// renders. The probe reads it from the served envelope, so an attachment claim is
// made against the contract rather than against a DOM class.
function publishedFormWidgets(contract) {
  const layout = contract.layoutContract || {};
  const tree = Array.isArray(layout.containerTree) ? layout.containerTree : [];
  const widgets = [];
  const walk = (nodes) => {
    for (const node of nodes || []) {
      if (!node || typeof node !== 'object') continue;
      const name = String(node.name || node.fieldName || '').trim();
      const type = String(node.type || '').trim();
      if (name && (type === 'field' || String(node.widgetId || '').startsWith('field.'))) {
        widgets.push({ name, type, source: String(node.sourceAuthority && node.sourceAuthority.runtime_carrier || '') });
      }
      walk(node.children);
    }
  };
  walk(tree);
  return widgets;
}

async function workflowSnapshot(page) {
  return page.evaluate(() => ({
    route: window.location.pathname + window.location.search,
    statusbar_state: (() => {
      const node = document.querySelector('[data-professional-workflow-component="statusbar"]');
      return node ? node.getAttribute('data-workflow-current') : null;
    })(),
    error_text: (() => {
      const node = document.querySelector('[data-semantic-status="error"], .status-panel.error');
      return node ? String(node.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 200) : '';
    })(),
    dialog_text: (() => {
      const node = document.querySelector('[data-dialog-purpose="intent-confirmation"], [role="dialog"]');
      return node ? String(node.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 200) : '';
    })(),
  }));
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

async function waitForRecordForm(page, timeout = 30000) {
  await page.waitForFunction(
    () => Boolean(document.querySelector('[data-professional-workflow-component="statusbar"][data-workflow-current]')),
    undefined,
    { timeout },
  );
  await sleep(900);
}

async function waitForListRows(page, timeout = 30000) {
  await page.waitForFunction(
    () => document.querySelectorAll('button[data-semantic-cell-kind="primary"]').length > 0,
    undefined,
    { timeout },
  );
  await sleep(600);
}

function listSearchInput(page) {
  return page.locator('input[placeholder*="搜索关键字"]:visible').first();
}

async function enterEntryList(page, entry) {
  await page.goto(`${BASE}/a/${entry.action_id}?menu_id=${entry.menu_id}`, { waitUntil: 'networkidle' });
  await waitForListRows(page);
}

// Queries/filters the declared list and returns the matching row count. A
// non-unique match is returned so the caller can fail closed with the real number.
async function filterList(page, term) {
  const search = listSearchInput(page);
  if (!(await search.count())) {
    fail('entry list did not expose the declared search field');
    return -1;
  }
  await search.fill(term);
  await page.getByRole('button', { name: /^搜索$/ }).first().click();
  await sleep(3500);
  return await page.locator('tbody tr').count();
}

async function openRecordFromList(page, entry) {
  const since = contracts.length;
  await page.locator('button[data-semantic-cell-kind="primary"]:visible').first().click();
  await waitForRecordForm(page);
  return await waitForRecordContract(entry.record_id, since);
}

async function refreshRecord(page, entry) {
  const since = contracts.length;
  await page.goto(`${BASE}/f/${MODEL}/${entry.record_id}?menu_id=${entry.menu_id}&action_id=${entry.action_id}`, { waitUntil: 'networkidle' });
  await waitForRecordForm(page);
  return await waitForRecordContract(entry.record_id, since);
}

async function openOverflow(page) {
  const triggers = [
    page.locator('button.form-header-more-actions:visible').first(),
    page.locator('button[aria-label="展开更多表单操作"]:visible').first(),
  ];
  for (const trigger of triggers) {
    if (await trigger.count()) {
      await trigger.click();
      await sleep(700);
      return true;
    }
  }
  return false;
}

async function confirmIfAsked(page) {
  const scopes = [
    page.locator('[data-dialog-purpose="intent-confirmation"]:visible'),
    page.locator('.intent-confirmation:visible'),
    page.locator('[role="dialog"]:visible'),
  ];
  for (const scope of scopes) {
    const dialog = scope.last();
    if (!(await dialog.count())) continue;
    const text = String((await dialog.textContent()) || '').replace(/\s+/g, ' ').trim();
    const confirm = dialog.locator('button').filter({ hasText: /^确认/ });
    if (await confirm.count()) {
      await confirm.first().click();
      await sleep(700);
      return text.slice(0, 200);
    }
    return `unconfirmed:${text.slice(0, 120)}`;
  }
  return '';
}

async function invoke(page, row) {
  let direct = page.locator(`button[data-action-method="${row.method}"]:visible`);
  if (await direct.count()) {
    const allowed = await direct.first().getAttribute('data-action-allowed');
    if (allowed === 'false') return { invoked: false, reason: 'action exposed but declared not allowed' };
    await direct.first().click();
    await sleep(500);
    return { invoked: true, confirmation: await confirmIfAsked(page), via: 'direct' };
  }
  const opened = await openOverflow(page);
  if (!opened) return { invoked: false, reason: 'action not exposed by the product surface' };
  const item = page.locator('li', { hasText: new RegExp(`^${escapeRegExp(row.label)}$`) }).last();
  if (!(await item.count())) {
    await page.keyboard.press('Escape').catch(() => {});
    return { invoked: false, reason: `declared action ${row.key} is in no exposed surface` };
  }
  await item.click();
  await sleep(500);
  return { invoked: true, confirmation: await confirmIfAsked(page), via: 'overflow' };
}

// Bounded paging walk. The footer is located by its declared semantic component;
// the assertions are on the rendered row count and the page marker, never on the
// presence of a vendor class.
async function pagingWalk(page) {
  const footer = page.locator('[data-semantic-component="CollectionPaginationFooter"]').last();
  if (!(await footer.count())) {
    observations.push({ stage: 'paging', skipped: true, reason: 'entry list rendered no declared pagination footer' });
    return;
  }
  const mode = String((await footer.getAttribute('data-pagination-mode')) || '');
  const totalText = String((await footer.locator('.pagination-total').first().textContent().catch(() => '')) || '').trim();
  const pageBefore = await page.locator('tbody tr').count();
  if (mode !== 'paged') {
    observations.push({ stage: 'paging', mode, total: totalText, skipped: true, reason: `entry list pagination mode is ${mode || 'unknown'}` });
    return;
  }
  const sizeSelect = footer.locator('.t-pagination__select, .t-select-input, [class*="pagination__select"]').first();
  const sizeOption = footer.locator('.t-select-option, [class*="select-option"]');
  let sizeChanged = null;
  if (await sizeSelect.count()) {
    await sizeSelect.click();
    await sleep(600);
    const options = await sizeOption.count();
    if (options > 0) {
      const smallest = sizeOption.first();
      const sizeLabel = String((await smallest.textContent()) || '').trim();
      await smallest.click();
      await sleep(2600);
      const after = await page.locator('tbody tr').count();
      sizeChanged = { option: sizeLabel, rows_before: pageBefore, rows_after: after };
      if (after > pageBefore && pageBefore > 0) {
        fail(`paging: shrinking the page size grew the rendered rows (${pageBefore} -> ${after})`);
      }
    } else {
      await page.keyboard.press('Escape').catch(() => {});
    }
  }
  const next = footer.locator('.t-pagination__btn-next, [class*="pagination__btn-next"], [aria-label="下一页"]').first();
  let nextMoved = null;
  if (await next.count()) {
    const disabled = await next.getAttribute('class');
    const isDisabled = /disabled/.test(String(disabled || '')) || (await next.getAttribute('disabled')) !== null;
    if (!isDisabled) {
      const rowsBeforeNext = await page.locator('tbody tr').count();
      await next.click();
      await sleep(2600);
      const current = String((await footer.locator('.t-is-current, [class*="is-current"]').first().textContent().catch(() => '')) || '').trim();
      nextMoved = { current_page: current, rows_before: rowsBeforeNext, rows_after: await page.locator('tbody tr').count() };
      if (!current) fail('paging: the declared next-page control did not publish a current page marker');
      const prev = footer.locator('.t-pagination__btn-prev, [class*="pagination__btn-prev"], [aria-label="上一页"]').first();
      if (await prev.count()) {
        await prev.click();
        await sleep(2200);
      }
    } else {
      nextMoved = { skipped: true, reason: 'declared next-page control is disabled on page 1 of 1' };
    }
  }
  observations.push({ stage: 'paging', mode, total: totalText, rows_on_page_1: pageBefore, page_size: sizeChanged, next_page: nextMoved });
}

async function login(page, login, password) {
  await page.goto(`${BASE}/login?db=${DB}`, { waitUntil: 'networkidle' });
  const inputs = page.locator('input');
  await inputs.nth(0).fill(login);
  await inputs.nth(1).fill(password);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 30000 });
  await page.waitForTimeout(3000);
}

// The negative authority case: a role holding none of the entry's declared groups
// must not reach the declared entry. The router redirects unauthorized
// authority-bound routes to the access-denied surface with a declared reason.
async function deniedRoleWalk(entry) {
  const deniedContext = await browser.newContext({ locale: 'zh-CN' });
  const page = await deniedContext.newPage();
  const errors = [];
  page.on('pageerror', (error) => errors.push(`pageerror:${error.message}`));
  try {
    await login(page, DENIED_ROLE_LOGIN, PASSWORD);
    await page.goto(`${BASE}/a/${entry.action_id}?menu_id=${entry.menu_id}`, { waitUntil: 'networkidle' });
    await sleep(2500);
    const url = new URL(page.url());
    const denied = url.pathname.includes('access-denied') || String(url.searchParams.get('reason') || '').includes('NAVIGATION_AUTHORITY_DENIED');
    const rows = await page.locator('button[data-semantic-cell-kind="primary"]').count();
    observations.push({
      stage: 'authority_negative',
      login: DENIED_ROLE_LOGIN,
      route: url.pathname + url.search,
      declared_reason: url.searchParams.get('reason'),
      rows_rendered: rows,
      denied,
    });
    if (!denied) {
      fail(`authority: ${DENIED_ROLE_LOGIN} holds none of the declared groups but still reached the entry (rows=${rows})`);
    }
  } finally {
    await deniedContext.close().catch(() => {});
  }
}

async function main() {
  if (!BASE) throw new Error('SC_ACCEPTANCE_FRONTEND_URL is required');
  if (!EXPECTED_SHA) throw new Error('SC_ACCEPTANCE_TARGET_SHA is required');
  if (!LOGIN || !PASSWORD) throw new Error('ACCEPTANCE_LOGIN and ACCEPTANCE_PASSWORD are required');
  if (WRITE_CONFIRM !== WRITE_CONFIRM_TOKEN) {
    throw new Error(`this lane mutates the declared external record; set SC_ENTRY_WRITE_CONFIRM=${WRITE_CONFIRM_TOKEN}`);
  }
  if (DENIED_ROLE_LOGIN === LOGIN) {
    throw new Error('SC_ENTRY_DENIED_ROLE_LOGIN must differ from the acting login');
  }
  const entry = readResolution();
  const runtime = await servedRevision();
  const served = String(runtime.git_sha || runtime.source_revision || '');
  if (served !== EXPECTED_SHA) throw new Error(`served revision ${served} != SC_ACCEPTANCE_TARGET_SHA ${EXPECTED_SHA}`);
  if (String(runtime.database || '') !== DB) throw new Error(`served database ${runtime.database} != ${DB}`);

  fs.mkdirSync(OUT_DIR, { recursive: true });
  browser = await launchChromium({ headless: true });
  context = await browser.newContext({ locale: 'zh-CN' });
  const page = await context.newPage();
  attachContractCapture(page);
  const consoleErrors = [];
  page.on('console', (message) => { if (message.type() === 'error') consoleErrors.push(message.text()); });
  page.on('pageerror', (error) => consoleErrors.push(`pageerror:${error.message}`));

  await login(page, LOGIN, PASSWORD);

  // The acting identity is bound before any write: the session company must equal
  // the company the managed resolution declared for the carrier.
  if (!sessionUser) fail('startup identity (system.init user) was not observed');
  else if (Number(sessionUser.company_id) !== entry.company_id) {
    fail(`session company ${sessionUser.company_id} != declared carrier company ${entry.company_id}`);
  }

  let contract = null;
  if (ENTRY_MODE === 'list') {
    await enterEntryList(page, entry);
    await pagingWalk(page);
    const matched = await filterList(page, entry.record_identity || '');
    observations.push({ stage: 'list_query', term: entry.record_identity, matched_rows: matched });
    if (matched !== 1) {
      fail(`entry search ${entry.record_identity} matched ${matched} rows; expected exactly one`);
    } else {
      contract = await openRecordFromList(page, entry);
      // Detail-return context: the browser back navigation must restore the same
      // filtered list, not just any list.
      await page.goBack({ waitUntil: 'networkidle' });
      await waitForListRows(page);
      await sleep(1200);
      const restoredInput = String((await listSearchInput(page).inputValue().catch(() => '')) || '').trim();
      const restoredRows = await page.locator('tbody tr').count();
      observations.push({ stage: 'detail_return', term_restored: restoredInput, rows_restored: restoredRows, route: new URL(page.url()).pathname });
      if (restoredInput !== (entry.record_identity || '') || restoredRows !== 1) {
        fail(`detail return restored term=${restoredInput || '(empty)'} rows=${restoredRows}; expected the same single-row filter`);
      }
      await page.screenshot({ path: path.join(OUT_DIR, 'list-detail-return.png'), fullPage: true });
    }
  } else {
    contract = await refreshRecord(page, entry);
  }

  let state = contract ? recordState(contract) : null;
  if (state) {
    observations.push({ stage: 'initial', ...(await workflowSnapshot(page)), contract_state: state });
    if (state.raw_state !== START_STATE) fail(`carrier rawState ${state.raw_state} != declared start ${START_STATE}`);
    if (state.main_state !== START_STATE) fail(`carrier mainData.${state.state_field} ${state.main_state} != declared start ${START_STATE}`);
    if (state.company_id && state.company_id !== entry.company_id) {
      fail(`carrier company ${state.company_id} != declared company ${entry.company_id}`);
    }
    const widgets = publishedFormWidgets(contract);
    observations.push({
      stage: 'published_form_surface',
      field_widgets: widgets.map((row) => row.name),
      attachment_widgets: widgets.filter((row) => row.name.includes('attachment')).map((row) => row.name),
    });
  }
  if (problems.length) {
    await page.screenshot({ path: path.join(OUT_DIR, 'fail-closed.png'), fullPage: true });
  }

  let halted = problems.length > 0;
  for (const step of CANONICAL_LADDER) {
    if (halted || DRY_RUN) {
      if (DRY_RUN) observations.push({ stage: step.action, skipped: true, reason: 'dry run: entry and start state verified, walk not executed' });
      if (halted) break;
      continue;
    }
    const beforeContract = await refreshRecord(page, entry);
    const beforeState = recordState(beforeContract);
    const offered = availableRows(beforeContract).filter((candidate) => candidate.enabled);
    const row = offered.find((candidate) => candidate.key === step.action) || null;
    if (!row) {
      fail(`${step.action}: declared action not offered while ${beforeState.raw_state} (offered: ${offered.map((candidate) => candidate.key).join(', ') || 'none'})`);
      break;
    }
    const outcome = await invoke(page, row);
    if (!outcome.invoked) {
      observations.push({ stage: step.action, state_before: beforeState.raw_state, offered: offered.map((c) => c.key), skipped: true, reason: outcome.reason });
      fail(`${step.action}: ${outcome.reason}`);
      break;
    }
    await page.waitForTimeout(2600);
    const afterContract = await refreshRecord(page, entry);
    const afterState = recordState(afterContract);
    const snapshot = await workflowSnapshot(page);
    observations.push({
      stage: step.action,
      method: row.method,
      confirmation: outcome.confirmation,
      via: outcome.via,
      state_before: beforeState.raw_state,
      offered_before: offered.map((candidate) => candidate.key),
      state_after: afterState.raw_state,
      main_state_after: afterState.main_state,
      declared_state_after: step.expect_state,
      offered_after: availableRows(afterContract).filter((candidate) => candidate.enabled).map((candidate) => candidate.key),
      error: snapshot.error_text || '',
    });
    if (afterState.raw_state !== step.expect_state) {
      fail(`${step.action}: rawState ${afterState.raw_state} != declared ${step.expect_state}`);
      halted = true;
      break;
    }
    if (afterState.main_state !== afterState.raw_state) {
      fail(`${step.action}: mainData.${afterState.state_field} ${afterState.main_state} != workflow rawState ${afterState.raw_state}`);
      halted = true;
      break;
    }
    await page.screenshot({ path: path.join(OUT_DIR, `${step.action}.png`), fullPage: true });
  }

  // The declared machine ends at a signed contract: the terminal rung must offer
  // no transition, because `action_cancel` refuses anything past `confirmed`.
  if (!DRY_RUN && !halted) {
    const finalContract = await refreshRecord(page, entry);
    const finalState = recordState(finalContract);
    const stillOffered = availableRows(finalContract).filter((row) => row.enabled);
    observations.push({
      stage: 'terminal',
      state: finalState.raw_state,
      offered: stillOffered.map((row) => row.key),
      declared_actions: (finalContract.workflow.availableActions || []).map((row) => row.key),
    });
    if (finalState.raw_state !== CANONICAL_LADDER[CANONICAL_LADDER.length - 1].expect_state) {
      fail(`final declared state ${finalState.raw_state} != ${CANONICAL_LADDER[CANONICAL_LADDER.length - 1].expect_state}`);
    }
    if (stillOffered.length) {
      fail(`terminal state ${finalState.raw_state} still offers ${stillOffered.map((row) => `${row.key}(${row.method})`).join(', ')}`);
    }
  }

  if (!DRY_RUN && !halted) {
    await deniedRoleWalk(entry);
  }

  const finalContract = latestRecordContract(entry.record_id);
  const summary = {
    schema: 'frontend.business_entry.general_contract.acceptance.v1',
    declaration_source: 'runtime ui.contract.v2 workflowContract (sc.general.contract)',
    canonical_ladder: CANONICAL_LADDER,
    base_url: BASE,
    database: DB,
    served_revision: served,
    identity: {
      record_xmlid: entry.record_xmlid,
      record_id: entry.record_id,
      record_identity: entry.record_identity,
      company_id: entry.company_id,
      session_company_id: sessionUser ? Number(sessionUser.company_id) : null,
      session_user_id: sessionUser ? Number(sessionUser.id) : null,
      denied_role_login: DENIED_ROLE_LOGIN,
    },
    entry: { menu_id: entry.menu_id, action_id: entry.action_id, model: MODEL, mode: ENTRY_MODE },
    write_authority: WRITE_CONFIRM,
    dry_run: DRY_RUN,
    initial_contract_state: observations.find((row) => row.contract_state)?.contract_state ?? null,
    final_contract_state: finalContract ? recordState(finalContract) : null,
    observations,
    console_errors: consoleErrors.slice(-20),
    problems,
    ok: problems.length === 0,
  };
  fs.writeFileSync(path.join(OUT_DIR, 'summary.json'), `${JSON.stringify(summary, null, 2)}\n`, 'utf8');
  await page.screenshot({ path: path.join(OUT_DIR, 'final.png'), fullPage: true });
  console.log(JSON.stringify({ ok: summary.ok, out_dir: OUT_DIR, states: observations.map((row) => `${row.stage}:${row.state_after ?? row.raw_state ?? '-'}`), problems }, null, 2));
  process.exit(summary.ok ? 0 : 1);
}

main()
  .catch((error) => { console.error(`[frontend_business_entry_general_contract_browser] failed: ${error && error.message ? error.message : error}`); process.exit(1); })
  .finally(async () => { if (context) await context.close().catch(() => {}); if (browser) await browser.close().catch(() => {}); });
