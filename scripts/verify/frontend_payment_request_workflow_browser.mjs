#!/usr/bin/env node
// Focused product-surface acceptance for the 付款申请 workflow.
// The runtime ui.contract.v2 workflowContract is the authority for the current
// state, stable action identities and business denial reasons. The probe opens
// the real menu/list entry, executes the declared submit and approval actions,
// proves automatic server readback, and retains local input after an injected
// transport failure before retrying the same declared action.
import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';

const BASE = String(process.env.SC_ACCEPTANCE_FRONTEND_URL || '').replace(/\/$/, '');
const DATABASE = String(process.env.SC_ACCEPTANCE_DATABASE || '');
const EXPECTED_SHA = String(process.env.SC_ACCEPTANCE_TARGET_SHA || '');
const LOGIN = String(process.env.ACCEPTANCE_LOGIN || '');
const PASSWORD = String(process.env.ACCEPTANCE_PASSWORD || '');
const RESOLUTION_PATH = String(process.env.ACCEPTANCE_RECORD_RESOLUTION || '');
const WRITE_CONFIRM = String(process.env.SC_ENTRY_WRITE_CONFIRM || '');
const WRITE_CONFIRM_TOKEN = 'DRIVE_ACCEPTANCE_PAYMENT_REQUEST_WORKFLOW';
const OUT_DIR = String(process.env.SC_ACCEPTANCE_OUTPUT_DIR || 'artifacts/frontend-payment-request-workflow');
const MODEL = 'payment.request';
const DECLARED_RECORD_XMLID = 'smart_construction_acceptance_fixture.fe_delivery_hardening_payment_request_a';

const problems = [];
const contracts = [];
const observations = [];
const consoleErrors = [];
const expectedConsoleErrors = [];
const requests = [];
let expectedTransportFailures = 0;

function check(condition, message, detail = undefined) {
  if (!condition) problems.push(detail === undefined ? message : `${message}: ${JSON.stringify(detail)}`);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function readResolution() {
  if (!RESOLUTION_PATH) throw new Error('ACCEPTANCE_RECORD_RESOLUTION is required');
  const body = JSON.parse(fs.readFileSync(RESOLUTION_PATH, 'utf8'));
  const entry = body?.targets?.payment_request;
  if (!entry) throw new Error('managed resolution is missing payment_request');
  if (String(entry.record_xmlid || '') !== DECLARED_RECORD_XMLID) {
    throw new Error(`resolution record_xmlid ${entry.record_xmlid} != ${DECLARED_RECORD_XMLID}`);
  }
  for (const key of ['record_id', 'menu_id', 'action_id']) {
    if (!(Number(entry[key]) > 0)) throw new Error(`resolution ${key} is missing`);
  }
  if (Number(entry.record_id) <= 0) throw new Error('resolution record_id is invalid');
  return entry;
}

function envelopeData(body) {
  return body?.data || body?.result?.data || body?.result || {};
}

function attachContractCapture(page) {
  page.on('console', (message) => {
    if (message.type() === 'error' && !/favicon|ResizeObserver/i.test(message.text())) {
      if (expectedTransportFailures > 0 && /503|Service Unavailable/i.test(message.text())) {
        expectedTransportFailures -= 1;
        expectedConsoleErrors.push(message.text());
      } else {
        consoleErrors.push(message.text());
      }
    }
  });
  page.on('pageerror', (error) => consoleErrors.push(`pageerror:${error.message}`));
  page.on('request', (request) => {
    if (!request.url().includes('/api/v1/intent')) return;
    try {
      const payload = JSON.parse(request.postData() || '{}');
      requests.push({
        intent: String(payload.intent || ''),
        op: String(payload.params?.op || ''),
        model: String(payload.params?.model || ''),
        record_id: Number(payload.params?.record_id || payload.params?.res_id || 0) || null,
        method: String(payload.params?.button?.name || payload.params?.button?.method || ''),
      });
      if (requests.length > 200) requests.shift();
    } catch {
      // Ignore unrelated non-JSON requests.
    }
  });
  page.on('response', async (response) => {
    if (!response.url().includes('/api/v1/intent')) return;
    let request = {};
    try {
      request = JSON.parse(response.request().postData() || '{}');
    } catch {
      return;
    }
    if (request.intent !== 'ui.contract.v2' || response.status() !== 200) return;
    try {
      const data = envelopeData(await response.json());
      const workflow = data?.workflowContract;
      const mainData = data?.dataContract?.mainData || {};
      if (!workflow || !Array.isArray(workflow.availableActions)) return;
      if (Number(mainData.id) !== Number(request?.params?.record_id || mainData.id)) return;
      contracts.push({
        mainData,
        workflow,
        actionRules: data?.actionContract?.actionRuleList || [],
        buttonStatus: data?.statusContract?.buttonStatus || [],
        pageInfo: data?.pageInfo || {},
      });
    } catch {
      // Invalid network payloads are caught by the UI contract gap state.
    }
  });
}

function latestContract(recordId) {
  for (let index = contracts.length - 1; index >= 0; index -= 1) {
    const contract = contracts[index];
    if (Number(contract?.mainData?.id) === Number(recordId) && contract?.workflow?.stateField) return contract;
  }
  return null;
}

async function waitForContract(recordId, since = 0, timeout = 30000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    for (let index = contracts.length - 1; index >= since; index -= 1) {
      const contract = contracts[index];
      if (Number(contract?.mainData?.id) === Number(recordId) && contract?.workflow?.stateField) return contract;
    }
    await sleep(200);
  }
  throw new Error(`payment request contract ${recordId} was not observed after index ${since}`);
}

async function waitForContractState(recordId, expectedState, since = 0, timeout = 12000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    for (let index = contracts.length - 1; index >= since; index -= 1) {
      const contract = contracts[index];
      if (Number(contract?.mainData?.id) === Number(recordId)
        && contract?.workflow?.stateField
        && String(contract?.workflow?.rawState || '') === expectedState) {
        return contract;
      }
    }
    await sleep(200);
  }
  return null;
}

async function servedRevision() {
  const response = await fetch(`${BASE}/api/runtime-version`, { headers: { Accept: 'application/json' } });
  if (!response.ok) throw new Error(`runtime-version status=${response.status}`);
  return response.json();
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

async function waitForForm(page, timeout = 30000) {
  await page.waitForFunction(
    () => Boolean(document.querySelector('[data-professional-workflow-component="statusbar"][data-workflow-current]')),
    undefined,
    { timeout },
  );
  await page.locator('[data-field-name]').first().waitFor({ state: 'visible', timeout });
  await sleep(600);
}

async function enterRecordFromList(page, entry) {
  const since = contracts.length;
  await page.goto(`${BASE}/a/${entry.action_id}?menu_id=${entry.menu_id}`, { waitUntil: 'networkidle' });
  await page.waitForFunction(
    () => document.querySelectorAll('button[data-semantic-cell-kind="primary"]').length > 0,
    undefined,
    { timeout: 30000 },
  );
  const search = page.locator('input[placeholder*="搜索关键字"]:visible').first();
  await search.waitFor({ state: 'visible', timeout: 20000 });
  await search.fill(entry.record_identity);
  await page.getByRole('button', { name: /^搜索$/ }).first().click();
  await sleep(2500);
  const rows = page.locator('tbody tr');
  const count = await rows.count();
  check(count === 1, `payment entry search matched ${count} rows; expected exactly one`, {
    identity: entry.record_identity,
  });
  if (count !== 1) throw new Error('payment entry is not uniquely addressable');
  await page.locator('button[data-semantic-cell-kind="primary"]:visible').first().click();
  await waitForForm(page);
  return waitForContract(entry.record_id, since);
}

function workflowState(contract) {
  const workflow = contract.workflow;
  const field = String(workflow.stateField || '').trim();
  const current = String(workflow.rawState || '').trim();
  const mainValue = String(contract.mainData?.[field] ?? '').trim();
  const statusbar = workflow.statusbar || {};
  return {
    field,
    current,
    mainValue,
    statusbarField: String(statusbar.field || ''),
    statusbarCurrent: String(statusbar.current || ''),
    statusbarReadonly: statusbar.readonly,
    statusbarSource: statusbar.source,
  };
}

function availableRows(contract) {
  return (contract.workflow.availableActions || []).map((row) => ({
    key: String(row?.key || '').trim(),
    label: String(row?.label || '').trim(),
    method: String(row?.method || row?.target?.method || '').trim(),
    enabled: row?.enabled === true,
    reasonCode: String(row?.reason_code || '').trim(),
    blockedMessage: String(row?.blocked_message || '').trim(),
  })).filter((row) => row.key);
}

async function statusbarSnapshot(page) {
  return page.evaluate(() => {
    const nodes = [...document.querySelectorAll('[data-professional-workflow-component="statusbar"]')]
      .filter((node) => node.getClientRects().length > 0);
    return nodes.map((node) => ({
      field: node.getAttribute('data-workflow-field') || '',
      current: node.getAttribute('data-workflow-current') || '',
      stateCount: Number(node.getAttribute('data-workflow-state-count') || 0),
      readonly: node.getAttribute('data-workflow-readonly') || '',
    }));
  });
}

async function assertAuthoritativeSurface(page, contract, stage) {
  const state = workflowState(contract);
  check(state.field && state.current, `${stage}: workflow state identity is missing`, state);
  check(state.mainValue === state.current, `${stage}: mainData state differs from workflow rawState`, state);
  check(state.statusbarField === state.field, `${stage}: workflow statusbar field differs`, state);
  check(state.statusbarCurrent === state.current, `${stage}: workflow statusbar current differs`, state);
  check(state.statusbarReadonly === true && state.statusbarSource === 'workflowContract',
    `${stage}: workflow statusbar authority is incomplete`, state);
  const bars = await statusbarSnapshot(page);
  check(bars.length === 1, `${stage}: expected one visible primary statusbar`, bars);
  if (bars.length === 1) {
    check(bars[0].current === state.current, `${stage}: rendered status differs from workflow state`, bars[0]);
    check(bars[0].stateCount > 0, `${stage}: rendered status has no declared options`, bars[0]);
  }
  return state;
}

async function openOverflow(page) {
  const trigger = page.locator('button.form-header-more-actions:visible').first();
  if (!(await trigger.count())) return false;
  await trigger.click();
  await sleep(500);
  return true;
}

async function actionLocator(page, row) {
  const direct = page.locator(`button[data-action-method="${row.method}"]:visible`).first();
  if (await direct.count()) return direct;
  if (!(await openOverflow(page))) return null;
  const item = page.locator('li', { hasText: new RegExp(`^${escapeRegExp(row.label)}$`) }).last();
  return (await item.count()) ? item : null;
}

async function confirmIfAsked(page) {
  const scope = page.locator('[data-dialog-purpose="intent-confirmation"]:visible, [role="dialog"]:visible').last();
  if (!(await scope.count())) return '';
  const text = String((await scope.textContent()) || '').replace(/\s+/g, ' ').trim();
  const confirm = scope.locator('button').filter({ hasText: /^确认/ }).last();
  if (await confirm.count()) {
    await confirm.click();
    await sleep(500);
  }
  return text.slice(0, 240);
}

async function clickAction(page, row, { force = false } = {}) {
  const target = await actionLocator(page, row);
  if (!target) throw new Error(`declared action ${row.key} has no rendered surface`);
  const disabled = await target.isDisabled().catch(() => false);
  check(!disabled, `declared enabled action ${row.key} rendered disabled`);
  await target.click({ force });
  await page.locator('[data-dialog-purpose="intent-confirmation"][data-state="open"]:visible')
    .waitFor({ state: 'visible', timeout: 1800 })
    .catch(() => {});
  await sleep(350);
  return confirmIfAsked(page);
}

async function failureFeedback(page) {
  return page.evaluate(() => {
    const nodes = [...document.querySelectorAll('[role="alert"], .sc-inline-state, .sc-state-panel, .toast')]
      .filter((node) => node.getClientRects().length > 0);
    return nodes.map((node) => String(node.textContent || '').replace(/\s+/g, ' ').trim())
      .filter(Boolean)
      .join(' | ')
      .slice(0, 500);
  });
}

async function invokeWithTransientFailure(page, row) {
  const noteInput = page.locator('[data-field-name="note"] textarea:visible, [data-field-name="note"] input:visible').first();
  await noteInput.waitFor({ state: 'visible', timeout: 20000 });
  const marker = `FE workflow retry ${Date.now()}`;
  await noteInput.fill(marker);
  await noteInput.blur();

  let failed = false;
  const routeHandler = async (route) => {
    let request = {};
    try {
      request = JSON.parse(route.request().postData() || '{}');
    } catch {
      await route.continue();
      return;
    }
    const writeLike = request.intent === 'execute_button'
      || (request.intent === 'api.data' && ['write', 'create'].includes(String(request.params?.op || '')));
    if (!failed && writeLike) {
      failed = true;
      expectedTransportFailures += 1;
      await route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({
          ok: false,
          error: { reason_code: 'FE_TRANSIENT_FAILURE', message: '临时保存失败，请修正后重试' },
        }),
      });
      return;
    }
    await route.continue();
  };
  await page.route('**/api/v1/intent**', routeHandler);
  const target = await actionLocator(page, row);
  if (!target) throw new Error(`declared action ${row.key} has no rendered surface`);
  await target.click();
  await sleep(2500);
  await page.unroute('**/api/v1/intent**', routeHandler);
  const feedback = await failureFeedback(page);
  const retainedValue = await noteInput.inputValue();
  check(failed, 'failure-retention probe did not intercept a write-like request');
  check(retainedValue === marker, 'failure-retention probe lost the user input');
  check(Boolean(feedback), 'failure-retention probe did not expose a visible error');
  const state = await statusbarSnapshot(page);
  check(state.length === 1 && state[0].current === 'draft', 'transient failure changed the authoritative state', state);
  await page.screenshot({ path: path.join(OUT_DIR, 'transient-failure.png'), fullPage: true });
  await page.keyboard.press('Escape');
  await page.mouse.click(8, 8);
  await sleep(700);
  return { marker, retained: retainedValue === marker, feedback, state };
}

async function invokeAndWaitForReadback(page, entry, row, expectedState, maxAttempts = 1, recoveryClick = false) {
  const attempts = [];
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    const since = contracts.length;
    const confirmation = await clickAction(page, row, { force: recoveryClick });
    const contract = await waitForContractState(entry.record_id, expectedState, since, 12000)
      || await waitForContract(entry.record_id, since, 12000);
    await sleep(1800);
    const rendered = await statusbarSnapshot(page);
    const state = workflowState(contract);
    attempts.push({ attempt, confirmation, state, rendered });
    if (state.current === expectedState && rendered.length === 1 && rendered[0].current === expectedState) {
      const authoritative = await assertAuthoritativeSurface(page, contract, row.key);
      return { contract, confirmation, state: authoritative, attempts };
    }
  }
  const last = attempts.at(-1);
  check(false, `${row.key}: state did not reach ${expectedState}`, { attempts });
  return {
    contract: await waitForContract(entry.record_id, 0, 1000),
    confirmation: last?.confirmation || '',
    state: last?.state || null,
    attempts,
  };
}

async function assertBlockedAction(page, contract, row, stage) {
  check(row.enabled === false, `${stage}: ${row.key} must be disabled`, row);
  check(Boolean(row.reasonCode), `${stage}: ${row.key} disabled reason code is missing`, row);
  check(Boolean(row.blockedMessage), `${stage}: ${row.key} user-facing reason is missing`, row);
  const button = page.locator(`button[data-action-method="${row.method}"]`).first();
  if (!(await button.count())) {
    await openOverflow(page);
  }
  const renderedActions = await page.locator('button[data-action-method]').evaluateAll((buttons) => buttons.map((button) => ({
    label: String(button.textContent || '').replace(/\s+/g, ' ').trim(),
    method: button.getAttribute('data-action-method') || '',
    backendIdentity: button.getAttribute('data-backend-identity') || '',
    enabled: button.getAttribute('data-action-enabled') || '',
    allowed: button.getAttribute('data-action-allowed') || '',
    disabled: button instanceof HTMLButtonElement ? button.disabled : null,
    visible: Boolean(button.getClientRects().length),
  })));
  const declaredRules = (contract.actionRules || []).map((rule) => ({
    actionKey: rule?.actionKey || '',
    backendIdentity: rule?.backendIdentity || '',
    method: rule?.button?.name || rule?.button?.method || '',
    visible: rule?.visible,
    reasonCode: rule?.reasonCode || rule?.reason_code || '',
    authorizationAllowed: rule?.authorizationAllowed,
    businessAvailable: rule?.businessAvailable,
    allowed: rule?.allowed,
    enabled: rule?.enabled,
    disabled: rule?.disabled,
    visibleProfiles: rule?.visibleProfiles || [],
  }));
  const declaredStatuses = (contract.buttonStatus || [])
    .filter((status) => String(status?.backendIdentity || '') === String(row.backendIdentity || ''))
    .map((status) => ({
      visible: status?.visible,
      disabled: status?.disabled,
      reasonCode: status?.reasonCode || '',
      reasonMessage: status?.reasonMessage || '',
      visibilityExplanation: status?.visibilityExplanation || '',
    }));
  check(await button.count() === 1, `${stage}: disabled ${row.key} is not exposed`, {
    row,
    renderedActions,
    declaredRules,
    declaredStatuses,
  });
  if (!(await button.count())) return;
  check(await button.isDisabled(), `${stage}: ${row.key} is not disabled in the product surface`);
  const presented = await button.evaluate((node) => ({
    title: String(node.getAttribute('title') || ''),
    parentLabel: String(node.parentElement?.getAttribute('aria-label') || ''),
  }));
  const visibleReason = `${presented.title} ${presented.parentLabel}`;
  check(visibleReason.includes(row.blockedMessage),
    `${stage}: ${row.key} does not expose the backend blocked_message`, presented);
}

async function main() {
  if (!BASE) throw new Error('SC_ACCEPTANCE_FRONTEND_URL is required');
  if (!DATABASE) throw new Error('SC_ACCEPTANCE_DATABASE is required');
  if (!EXPECTED_SHA) throw new Error('SC_ACCEPTANCE_TARGET_SHA is required');
  if (!LOGIN || !PASSWORD) throw new Error('ACCEPTANCE_LOGIN and ACCEPTANCE_PASSWORD are required');
  if (WRITE_CONFIRM !== WRITE_CONFIRM_TOKEN) {
    throw new Error(`SC_ENTRY_WRITE_CONFIRM=${WRITE_CONFIRM_TOKEN} is required`);
  }
  const entry = readResolution();
  const runtime = await servedRevision();
  const served = String(runtime.git_sha || runtime.source_revision || runtime.source_sha || '');
  if (served !== EXPECTED_SHA) throw new Error(`served revision ${served} != ${EXPECTED_SHA}`);
  if (String(runtime.database || '') !== DATABASE) {
    throw new Error(`served database ${runtime.database} != ${DATABASE}`);
  }

  fs.mkdirSync(OUT_DIR, { recursive: true });
  const browser = await launchChromium({ headless: true });
  const context = await browser.newContext({ locale: 'zh-CN', viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  attachContractCapture(page);

  await page.goto(`${BASE}/login?db=${DATABASE}`, { waitUntil: 'networkidle' });
  const inputs = page.locator('input');
  await inputs.nth(0).fill(LOGIN);
  await inputs.nth(1).fill(PASSWORD);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45000 });
  await sleep(1500);

  const initial = await enterRecordFromList(page, entry);
  const initialState = await assertAuthoritativeSurface(page, initial, 'initial');
  const initialRows = availableRows(initial);
  observations.push({ stage: 'initial', state: initialState, actions: initialRows });
  const submitRow = initialRows.find((row) => row.key === 'submit' && row.enabled);
  check(Boolean(submitRow), 'initial contract does not expose enabled submit', initialRows);
  if (!submitRow) throw new Error('payment submit action is not contract-declared');
  await page.screenshot({ path: path.join(OUT_DIR, 'initial.png'), fullPage: true });

  const firstAttempt = await invokeWithTransientFailure(page, submitRow);
  observations.push({ stage: 'failure-retention', ...firstAttempt });
  // The failure path retains the dirty note. The first post-failure click saves
  // that user input; the next click executes the same declared workflow action.
  const submit = await invokeAndWaitForReadback(page, entry, submitRow, 'submit', 2, true);
  const submittedRows = availableRows(submit.contract);
  const approveRow = submittedRows.find((row) => row.key === 'approve' && row.enabled);
  check(Boolean(approveRow), 'submitted contract does not expose enabled approve', submittedRows);
  if (!approveRow) throw new Error('payment approve action is not contract-declared');
  await page.screenshot({ path: path.join(OUT_DIR, 'submitted.png'), fullPage: true });

  const approval = await invokeAndWaitForReadback(page, entry, approveRow, 'approved');
  const approvedRows = availableRows(approval.contract);
  const doneRow = approvedRows.find((row) => row.key === 'done');
  check(Boolean(doneRow), 'approved contract does not retain the declared done action', approvedRows);
  if (doneRow) await assertBlockedAction(page, approval.contract, doneRow, 'approved');
  await page.screenshot({ path: path.join(OUT_DIR, 'approved-blocked-done.png'), fullPage: true });

  observations.push(
    { stage: 'submit', confirmation: submit.confirmation, state: submit.state, actions: submittedRows },
    { stage: 'approve', confirmation: approval.confirmation, state: approval.state, actions: approvedRows },
  );
  check(consoleErrors.length === 0, 'browser emitted console/page errors', consoleErrors);
  const report = {
    schema: 'frontend.payment_request.workflow_acceptance.v1',
    pass: problems.length === 0,
    base_url: BASE,
    database: DATABASE,
    served_sha: served,
    expected_sha: EXPECTED_SHA,
    entry,
    observations,
    console_errors: consoleErrors,
    expected_console_errors: expectedConsoleErrors,
    requests,
    problems,
  };
  fs.writeFileSync(path.join(OUT_DIR, 'summary.json'), `${JSON.stringify(report, null, 2)}\n`);
  await browser.close();
  if (problems.length) {
    throw new Error(`payment workflow browser failed: ${problems.join(' | ')}`);
  }
  console.log(JSON.stringify({
    ok: true,
    out_dir: OUT_DIR,
    states: observations.map((row) => `${row.stage}:${row.state?.current || ''}`),
    blocked: doneRow ? { key: doneRow.key, reason_code: doneRow.reasonCode, message: doneRow.blockedMessage } : null,
    retry_input_retained: firstAttempt.retained,
    problems,
  }));
}

main().catch(async (error) => {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  fs.writeFileSync(path.join(OUT_DIR, 'failure.json'), `${JSON.stringify({
    schema: 'frontend.payment_request.workflow_acceptance.failure.v1',
    message: error instanceof Error ? error.message : String(error),
    problems,
    observations,
    console_errors: consoleErrors,
    expected_console_errors: expectedConsoleErrors,
    requests,
  }, null, 2)}\n`);
  console.error(`[frontend_payment_request_workflow_browser] failed: ${error instanceof Error ? error.stack || error.message : String(error)}`);
  process.exit(1);
});
