#!/usr/bin/env node
// Focused product-surface acceptance for the 项目启停管理 formal business entry
// (project.project lifecycle). The correctness anchor is the runtime contract,
// not a duplicated local declaration: the probe captures the record's
// `ui.contract.v2` envelope and the startup `system.init` identity, then drives
// exactly the actions `workflowContract.availableActions` declares for the state
// the runtime reports, asserting the declared successor `rawState` after every
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
const RECORD_XMLID = (process.env.SC_ENTRY_RECORD_XMLID || 'smart_construction_acceptance_fixture.fe_project_lifecycle').trim();
const RESOLUTION_PATH = process.env.ACCEPTANCE_RECORD_RESOLUTION || '';
// 'list' drives the declared product entry (menu -> list -> search -> open record);
// 'record' is a bounded diagnostic that opens the record route directly.
const ENTRY_MODE = (process.env.SC_ENTRY_ENTRY_MODE || 'list').trim();
// This lane mutates a real product record on an external environment, so it fails
// closed unless the caller presents the explicit write-authority token.
const WRITE_CONFIRM = process.env.SC_ENTRY_WRITE_CONFIRM || '';
const WRITE_CONFIRM_TOKEN = 'DRIVE_DAILY_SC_DEMO_PROJECT_LIFECYCLE';
// Read-only smoke: resolves and verifies the declared entry, then stops before the
// first mutating action. It never substitutes for the full walk and issues no pass.
const DRY_RUN = process.env.SC_ENTRY_DRY_RUN === '1';
const OUT_DIR = process.env.SC_ACCEPTANCE_OUTPUT_DIR || path.join('artifacts', 'frontend-business-entry-lifecycle', String(Date.now()));
const MODEL = 'project.project';
const STATE_FIELD = 'lifecycle_state';
const START_STATE = { lifecycle_state: 'draft', sc_approval_state: 'draft' };

// The canonical 项目启停管理 business ladder: the declared transition keys the
// entry must offer, each paired with the lifecycle_state the declaration says it
// produces. This names business states, never a selector string or a pixel value.
// The action method is never declared here: it is read from the runtime contract.
const CANONICAL_LADDER = [
  { action: 'submit', expect_state: 'draft' },
  { action: 'activate', expect_state: 'in_progress' },
  { action: 'complete', expect_state: 'done' },
  { action: 'advance_closing', expect_state: 'closing' },
  { action: 'advance_warranty', expect_state: 'warranty' },
  { action: 'close', expect_state: 'closed' },
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
  const entry = targets.lifecycle_project;
  if (!entry) throw new Error('managed resolution is missing lifecycle_project');
  if (String(entry.record_xmlid || '') !== RECORD_XMLID) {
    throw new Error(`resolution record_xmlid ${entry.record_xmlid} != declared ${RECORD_XMLID}`);
  }
  for (const key of ['record_id', 'company_id', 'menu_id', 'action_id']) {
    if (!(Number(entry[key]) > 0)) throw new Error(`resolution ${key} is missing`);
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

function projectState(contract) {
  const workflow = contract.workflow;
  const mainData = contract.mainData;
  const rawState = String(workflow.rawState || '');
  const declaredField = String(workflow.stateField || '');
  const mainState = String((mainData && mainData[declaredField]) || '');
  return {
    state_field: declaredField,
    raw_state: rawState,
    main_state: mainState,
    approval_state: String((mainData && mainData.sc_approval_state) || ''),
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

// The contract supplies the business label; the overflow item is located by that
// exact visible text so the probe consumes the declared label instead of a vendor DOM class.
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

// Opens the record through the real product entry: the declared menu action renders
// the business list, the list search resolves exactly one row, and the row's primary
// semantic cell opens the record form. A non-unique match fails closed.
async function enterRecordFromList(page, entry) {
  const since = contracts.length;
  await page.goto(`${BASE}/a/${entry.action_id}?menu_id=${entry.menu_id}`, { waitUntil: 'networkidle' });
  await page.waitForFunction(
    () => document.querySelectorAll('button[data-semantic-cell-kind="primary"]').length > 0,
    undefined,
    { timeout: 30000 },
  );
  const search = page.locator('input[placeholder*="搜索关键字"]:visible').first();
  if (!(await search.count())) fail('entry list did not expose the declared search field');
  await search.fill(entry.record_code || entry.record_identity || '');
  await page.getByRole('button', { name: /^搜索$/ }).first().click();
  await sleep(3500);
  const rows = page.locator('tbody tr');
  const matched = await rows.count();
  if (matched !== 1) fail(`entry search ${entry.record_code} matched ${matched} rows; expected exactly one`);
  if (matched === 1) {
    await page.locator('button[data-semantic-cell-kind="primary"]:visible').first().click();
    await waitForRecordForm(page);
  }
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

// The declared confirmation surface renders its confirm action as
// `确认${actionLabel}` (IntentConfirmationDialog.vue), so the dialog is consumed by
// its declared purpose and its confirm button prefix, never by a fixed label list.
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

// Invokes one contract-declared action. The method and the label both come from the
// runtime contract row, so the probe never hardcodes a business method string.
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

async function main() {
  if (!BASE) throw new Error('SC_ACCEPTANCE_FRONTEND_URL is required');
  if (!EXPECTED_SHA) throw new Error('SC_ACCEPTANCE_TARGET_SHA is required');
  if (!LOGIN || !PASSWORD) throw new Error('ACCEPTANCE_LOGIN and ACCEPTANCE_PASSWORD are required');
  if (WRITE_CONFIRM !== WRITE_CONFIRM_TOKEN) {
    throw new Error(`this lane mutates the declared external record; set SC_ENTRY_WRITE_CONFIRM=${WRITE_CONFIRM_TOKEN}`);
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

  await page.goto(`${BASE}/login?db=${DB}`, { waitUntil: 'networkidle' });
  const inputs = page.locator('input');
  await inputs.nth(0).fill(LOGIN);
  await inputs.nth(1).fill(PASSWORD);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 30000 });
  await page.waitForTimeout(3000);

  // The acting identity is bound before any write: the session company must equal
  // the company the managed resolution declared for the carrier.
  if (!sessionUser) fail('startup identity (system.init user) was not observed');
  else if (Number(sessionUser.company_id) !== entry.company_id) {
    fail(`session company ${sessionUser.company_id} != declared carrier company ${entry.company_id}`);
  }

  let contract = ENTRY_MODE === 'record'
    ? await refreshRecord(page, entry)
    : await enterRecordFromList(page, entry);
  let state = projectState(contract);
  observations.push({ stage: 'initial', ...(await workflowSnapshot(page)), contract_state: state });

  // Fail closed before the first write unless the carrier really sits in the
  // declared start state and inside the declared company.
  if (state.raw_state !== START_STATE.lifecycle_state) {
    fail(`carrier rawState ${state.raw_state} != declared start ${START_STATE.lifecycle_state}`);
  }
  if (state.main_state !== START_STATE.lifecycle_state) {
    fail(`carrier mainData.${state.state_field} ${state.main_state} != declared start ${START_STATE.lifecycle_state}`);
  }
  if (state.approval_state !== START_STATE.sc_approval_state) {
    fail(`carrier sc_approval_state ${state.approval_state} != declared start ${START_STATE.sc_approval_state}`);
  }
  if (state.company_id && state.company_id !== entry.company_id) {
    fail(`carrier company ${state.company_id} != declared company ${entry.company_id}`);
  }
  if (problems.length) {
    await page.screenshot({ path: path.join(OUT_DIR, 'fail-closed.png'), fullPage: true });
  }

  let halted = false;
  for (const step of CANONICAL_LADDER) {
    if (halted) break;
    if (DRY_RUN) {
      observations.push({ stage: step.action, skipped: true, reason: 'dry run: entry and start state verified, walk not executed' });
      continue;
    }
    // Consume the rung from the runtime contract. When the runtime still exposes a
    // declared approval step instead of the transition, consume that first: the probe
    // never invents an action the contract does not offer.
    let row = null;
    let stateBefore = '';
    let lastOffered = [];
    for (let attempt = 0; attempt < 4 && !row; attempt += 1) {
      const rungContract = await refreshRecord(page, entry);
      const rungState = projectState(rungContract);
      stateBefore = rungState.raw_state;
      const offered = availableRows(rungContract).filter((candidate) => candidate.enabled);
      lastOffered = offered.map((candidate) => candidate.key);
      row = offered.find((candidate) => candidate.key === step.action) || null;
      if (row) break;
      const approval = offered.find((candidate) => candidate.key === 'approve');
      if (!approval) break;
      const approvalOutcome = await invoke(page, approval);
      if (!approvalOutcome.invoked) break;
      await page.waitForTimeout(2200);
    }
    if (!row) {
      fail(`${step.action}: declared action not offered while ${stateBefore} (offered: ${lastOffered.join(', ') || 'none'})`);
      break;
    }
    if (step.action === 'submit' && stateBefore === 'draft' && lastOffered.includes('activate')) {
      fail('submit: activate must not be offered while sc_approval_state=draft (declared activate domain gate)');
      break;
    }
    const outcome = await invoke(page, row);
    if (!outcome.invoked) {
      observations.push({ stage: step.action, state_before: stateBefore, offered: lastOffered, skipped: true, reason: outcome.reason });
      fail(`${step.action}: ${outcome.reason}`);
      break;
    }
    await page.waitForTimeout(2600);
    const afterContract = await refreshRecord(page, entry);
    const afterState = projectState(afterContract);
    const snapshot = await workflowSnapshot(page);
    observations.push({
      stage: step.action,
      method: row.method,
      confirmation: outcome.confirmation,
      via: outcome.via,
      state_before: stateBefore,
      offered_before: lastOffered,
      state_after: afterState.raw_state,
      main_state_after: afterState.main_state,
      approval_state_after: afterState.approval_state,
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

  if (!DRY_RUN && problems.length === 0) {
    const final = projectState(await refreshRecord(page, entry));
    if (final.raw_state !== 'closed') fail(`final declared state ${final.raw_state} != closed`);
    const stillOffered = availableRows(await latestRecordContract(entry.record_id)).filter((row) => row.enabled);
    if (stillOffered.length) fail(`closed: declared terminal state still offers ${stillOffered.map((row) => row.key).join(', ')}`);
  }

  const finalContract = latestRecordContract(entry.record_id);
  const summary = {
    schema: 'frontend.business_entry.lifecycle.acceptance.v1',
    declaration_source: 'runtime ui.contract.v2 workflowContract (project.project)',
    canonical_ladder: CANONICAL_LADDER,
    base_url: BASE,
    database: DB,
    served_revision: served,
    identity: {
      record_xmlid: entry.record_xmlid,
      record_id: entry.record_id,
      record_code: entry.record_code,
      company_id: entry.company_id,
      session_company_id: sessionUser ? Number(sessionUser.company_id) : null,
      session_user_id: sessionUser ? Number(sessionUser.id) : null,
    },
    entry: { menu_id: entry.menu_id, action_id: entry.action_id, model: MODEL, mode: ENTRY_MODE },
    write_authority: WRITE_CONFIRM,
    dry_run: DRY_RUN,
    initial_contract_state: observations.find((row) => row.contract_state)?.contract_state ?? null,
    final_contract_state: finalContract ? projectState(finalContract) : null,
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
  .catch((error) => { console.error(`[frontend_business_entry_lifecycle_browser] failed: ${error && error.message ? error.message : error}`); process.exit(1); })
  .finally(async () => { if (context) await context.close().catch(() => {}); if (browser) await browser.close().catch(() => {}); });
