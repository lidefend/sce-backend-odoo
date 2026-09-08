#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';

const target = JSON.parse(process.env.LOCAL_DEV_PAYMENT_FLOORPLAN_JSON || '{}');
const approvalTarget = JSON.parse(process.env.LOCAL_DEV_PAYMENT_APPROVAL_CHAIN_JSON || '{}');
const baseUrl = process.env.FRONTEND_URL || '';
const database = process.env.DB_NAME || '';
const password = process.env.E2E_PASSWORD || '';
const sourceSha = process.env.SOURCE_SHA || '';
const candidateFingerprint = process.env.CANDIDATE_FINGERPRINT || '';
const requestId = Number(target?.actionable_record?.id || 0);
const requestName = String(target?.actionable_record?.name || '');
const actionId = Number(target?.action?.id || 0);
const menuId = Number(target?.menu?.id || 0);
const managerLogin = String(target?.user?.login || '');
const approvalChain = Array.isArray(approvalTarget?.chain) ? approvalTarget.chain : [];
const executionPolicy = approvalTarget?.payment_execution_policy || {};
const financeUserLogin = String(approvalChain.find(
  (row) => row?.group_xmlid === 'smart_construction_core.group_sc_role_finance_user',
)?.actor_login || '');
const outputDir = path.resolve('artifacts/playwright/local-dev-payment-request-full-chain');

for (const [name, value] of Object.entries({ baseUrl, database, password, sourceSha, candidateFingerprint, requestId, requestName, actionId, menuId, managerLogin })) {
  if (!value) throw new Error(`missing governed full-chain input: ${name}`);
}
if (approvalTarget?.request_id !== requestId || !approvalChain.length || approvalChain.some((row) => !row?.review_id || !row?.actor_login)) {
  throw new Error('governed runtime payment approval chain is incomplete');
}
if (!executionPolicy?.id || !executionPolicy?.code || !['none', 'single', 'multi'].includes(String(executionPolicy?.mode || ''))) {
  throw new Error('governed runtime payment execution approval policy is incomplete');
}
if (!financeUserLogin) throw new Error('governed payment chain has no finance user for execution submission');
fs.mkdirSync(outputDir, { recursive: true });

const report = {
  schema: 'local_dev.payment_request.full_chain.v1',
  pass: false,
  generated_at: new Date().toISOString(),
  source: { head_sha: sourceSha, candidate_fingerprint: candidateFingerprint },
  runtime: { database, frontend_url: baseUrl, request_id: requestId, action_id: actionId, menu_id: menuId },
  roles: { approval_chain: approvalChain, finance_user: financeUserLogin, finance_manager: managerLogin },
  payment_execution_policy: executionPolicy,
  transitions: [], screenshots: [], errors: [], failed_requests: [], assertions: [],
  action_responses: [],
};

function intentName(response) {
  if (!response.url().includes('/api/v1/intent')) return '';
  try { return String(JSON.parse(response.request().postData() || '{}')?.intent || ''); } catch { return ''; }
}
function check(condition, assertion, facts = {}) {
  report.assertions.push({ assertion, pass: Boolean(condition), ...facts });
  if (!condition) throw new Error(`${assertion}: ${JSON.stringify(facts)}`);
}
function attachDiagnostics(page, role) {
  page.on('console', (message) => {
    if (message.type() === 'error' && !/favicon|ResizeObserver/i.test(message.text())) {
      report.errors.push({ role, type: 'console', text: message.text(), url: page.url() });
    }
  });
  page.on('pageerror', (error) => report.errors.push({ role, type: 'pageerror', text: error.message, url: page.url() }));
  page.on('response', (response) => {
    if (response.status() >= 400) report.failed_requests.push({ role, status: response.status(), intent: intentName(response), url: response.url() });
  });
}
async function login(page, loginName) {
  await page.goto(`${baseUrl}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const inputs = page.locator('input');
  await inputs.nth(0).fill(loginName);
  await inputs.nth(1).fill(password);
  const databaseInputs = page.getByLabel(/数据库/);
  const databaseInputCount = await databaseInputs.count();
  check(databaseInputCount <= 1, 'login database identity is unique', { databaseInputCount });
  if (databaseInputCount === 1 && await databaseInputs.first().isVisible() && await databaseInputs.first().isEnabled()) {
    await databaseInputs.first().fill(database);
  }
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45000 });
  await page.locator('.layout-shell').waitFor({ timeout: 45000 });
}
async function waitForm(page, model, id = null) {
  const suffix = id ? `[data-form-record="${id}"]` : '';
  await page.locator(`[data-product-page-mode="form"][data-form-model="${model}"]${suffix}:visible`).waitFor({ timeout: 45000 });
  await page.waitForFunction(() => !/正在加载页面|正在加载记录|正在载入数据|加载中/.test(document.body?.innerText || ''), null, { timeout: 45000 });
  await page.waitForTimeout(350);
}
async function shot(page, name) {
  const file = path.join(outputDir, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  report.screenshots.push({ name, file, url: page.url(), viewport: page.viewportSize() });
}
async function apiIntent(page, intent, params) {
  return apiEnvelope(page, { intent, params });
}
async function apiEnvelope(page, envelope) {
  const token = await page.evaluate((db) => sessionStorage.getItem(`sc_auth_token:${db}`) || '', database);
  return page.evaluate(async ({ db, tokenValue, envelopeValue }) => {
    const response = await fetch(`/api/v1/intent?db=${encodeURIComponent(db)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: tokenValue ? `Bearer ${tokenValue}` : '', 'X-Trace-Id': `local-dev-payment-full-chain-${Date.now()}` },
      body: JSON.stringify(envelopeValue),
    });
    return { status: response.status, body: await response.json().catch(() => ({})) };
  }, { db: database, tokenValue: token, envelopeValue: envelope });
}
async function clickAction(page, selector, expectedIntent, label) {
  const button = page.locator(selector);
  check(await button.count() === 1, `${label} has one component-system action`, { selector, count: await button.count() });
  check(await button.isVisible() && await button.isEnabled(), `${label} is visible and enabled`);
  const responsePromise = expectedIntent ? page.waitForResponse((response) => intentName(response) === expectedIntent, { timeout: 45000 }) : null;
  await button.click();
  const dialog = page.locator('[data-dialog-purpose="intent-confirmation"][role="dialog"]:visible, [role="dialog"]:visible').first();
  if (await dialog.waitFor({ state: 'visible', timeout: 2500 }).then(() => true).catch(() => false)) {
    const confirm = dialog.getByRole('button', { name: /^确认/ }).last();
    await confirm.waitFor({ state: 'visible', timeout: 10000 });
    await confirm.click();
  }
  if (responsePromise) {
    const response = await responsePromise;
    check(response.status() < 400, `${label} request succeeds`, { status: response.status() });
    const body = await response.json().catch(() => ({}));
    const requestPayload = JSON.parse(response.request().postData() || '{}');
    const result = body?.data?.result || body?.result || {};
    const rawAction = result?.raw_action || {};
    report.action_responses.push({
      label,
      status: response.status(),
      action_id: Number(result?.action_id || rawAction?.id || rawAction?.action_id || 0),
      menu_id: Number(rawAction?.menu_id || rawAction?.entry_target?.compatibility_refs?.menu_id || 0),
      entry_target: result?.entry_target || rawAction?.entry_target || null,
      request_payload: requestPayload,
    });
    return result;
  }
  return {};
}
async function readOne(page, model, fields, id) {
  const response = await apiIntent(page, 'api.data', { op: 'list', model, fields, domain: [['id', '=', id]], limit: 1 });
  const rows = response.body?.data?.records || response.body?.result?.records || [];
  check(response.status === 200 && rows.length === 1, `${model} authoritative row is readable`, { status: response.status, rows });
  return rows[0];
}

const browser = await launchChromium({ headless: true });
try {
  for (const [index, review] of approvalChain.entries()) {
    const approvalContext = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
    const approvalPage = await approvalContext.newPage();
    attachDiagnostics(approvalPage, `payment_reviewer_${review.group_xmlid || review.sequence}`);
    await login(approvalPage, review.actor_login);
    await approvalPage.goto(`${baseUrl}/my-work`, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await approvalPage.locator('.product-work').waitFor({ timeout: 45000 });
    await approvalPage.locator('.count-card[data-section-key="todo"]').click();
    const approvalCard = approvalPage.locator('.work-section[data-section-key="todo"] .work-card').filter({ hasText: requestName });
    await approvalCard.waitFor({ state: 'visible', timeout: 45000 });
    const beforeApproval = await readOne(approvalPage, 'payment.request', ['id', 'state', 'validation_status', 'review_ids'], requestId);
    check(beforeApproval.state === 'submit' && ['waiting', 'pending'].includes(String(beforeApproval.validation_status)), `review ${review.review_id} receives the pending payment request`, { beforeApproval, review });
    await shot(approvalPage, `approval-${index + 1}-pending`);
    const approvalResponse = approvalPage.waitForResponse((response) => {
      if (intentName(response) !== 'payment.request.execute') return false;
      try {
        const payload = JSON.parse(response.request().postData() || '{}');
        return payload?.params?.id === requestId && payload?.params?.action === 'approve';
      } catch { return false; }
    }, { timeout: 45000 });
    await approvalCard.getByRole('button', { name: '审批', exact: true }).click();
    const approvalDialog = approvalPage.getByRole('dialog');
    await approvalDialog.waitFor({ state: 'visible', timeout: 10000 });
    await approvalDialog.getByRole('button', { name: /^确认审批$/ }).click();
    check((await approvalResponse).status() < 400, `review ${review.review_id} approval request succeeds`);
    await approvalDialog.waitFor({ state: 'hidden', timeout: 45000 });
    const afterApproval = await readOne(approvalPage, 'payment.request', ['id', 'state', 'validation_status', 'review_ids'], requestId);
    const finalStep = index === approvalChain.length - 1;
    check(
      finalStep
        ? afterApproval.state === 'approved' && afterApproval.validation_status === 'validated'
        : afterApproval.state === 'submit' && ['waiting', 'pending'].includes(String(afterApproval.validation_status)),
      `review ${review.review_id} advances exactly one configured payment approval step`,
      { beforeApproval, afterApproval, review },
    );
    report.transitions.push({ actor: review.actor_login, reviewer_group: review.group_xmlid, review_id: review.review_id, step: index + 1, state: afterApproval.state, validation_status: afterApproval.validation_status, review_ids: afterApproval.review_ids });
    await shot(approvalPage, `approval-${index + 1}-after`);
    await approvalContext.close();
  }

  const managerContext = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
  const manager = await managerContext.newPage();
  attachDiagnostics(manager, 'finance_manager');
  await login(manager, managerLogin);
  await manager.goto(`${baseUrl}/r/payment.request/${requestId}?action_id=${actionId}&menu_id=${menuId}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await waitForm(manager, 'payment.request', requestId);
  await shot(manager, '03-approved-finance');
  const generateResult = await clickAction(
    manager,
    '[data-product-primary-action][data-action-key="payment_execution"][data-action-method="action_create_payment_execution"][data-action-enabled="true"]:visible',
    'execute_button',
    'generate payment execution',
  );
  const generateTarget = generateResult?.entry_target || generateResult?.raw_action?.entry_target || {};
  const generateRefs = generateTarget?.compatibility_refs || {};
  check(
    generateTarget?.type === 'compatibility'
      && generateTarget?.route === '/f/sc.payment.execution/new'
      && Number(generateRefs?.action_id || 0) > 0
      && Number(generateRefs?.menu_id || 0) > 0,
    'generate payment execution returns one authoritative create-form target',
    { generateTarget },
  );
  await manager.waitForURL((url) => url.pathname !== `/r/payment.request/${requestId}`, { timeout: 45000 });
  await waitForm(manager, 'sc.payment.execution');
  const executionCreateSurface = manager.locator('[data-product-page-mode="form"][data-form-model="sc.payment.execution"]:visible');
  const handlerInput = executionCreateSurface.locator('[data-field-name="handler_name"] input:visible');
  check(await handlerInput.count() === 1, 'payment execution intake exposes one visible handler component input');
  await handlerInput.fill('验收财务经办人');
  await shot(manager, '04-execution-create');
  const createResponse = manager.waitForResponse((response) => {
    if (intentName(response) !== 'api.data') return false;
    try { const payload = JSON.parse(response.request().postData() || '{}'); return payload?.params?.op === 'create' && payload?.params?.model === 'sc.payment.execution'; } catch { return false; }
  }, { timeout: 45000 });
  await manager.getByRole('button', { name: /^保存草稿$/, exact: true }).click();
  check((await createResponse).status() < 400, 'payment execution save succeeds');
  await manager.waitForURL((url) => /^\/(?:f|r)\/sc\.payment\.execution\/\d+$/.test(url.pathname), { timeout: 45000 });
  const executionId = Number(new URL(manager.url()).pathname.split('/').pop());
  check(executionId > 0, 'saved payment execution has authoritative id', { executionId });
  await waitForm(manager, 'sc.payment.execution', executionId);
  const requestSnapshot = await readOne(manager, 'payment.request', [
    'id', 'amount',
    'payment_account_name', 'payment_bank_name', 'payment_account_no',
    'partner_account_name', 'partner_bank_name', 'partner_bank_account',
  ], requestId);
  const executionSnapshot = await readOne(manager, 'sc.payment.execution', [
    'id', 'payment_request_id', 'paid_amount', 'handler_name', 'receipt_account_name', 'receipt_bank_name',
    'receipt_account_no',
  ], executionId);
  const value = (item) => String(item || '');
  check(
    value(executionSnapshot.receipt_account_name) === value(requestSnapshot.payment_account_name || requestSnapshot.partner_account_name)
      && value(executionSnapshot.receipt_bank_name) === value(requestSnapshot.payment_bank_name || requestSnapshot.partner_bank_name)
      && value(executionSnapshot.receipt_account_no) === value(requestSnapshot.payment_account_no || requestSnapshot.partner_bank_account)
      && value(executionSnapshot.handler_name) === '验收财务经办人'
      && Number(executionSnapshot.paid_amount) === Number(requestSnapshot.amount),
    'submitted payment execution preserves the authoritative request amount and payee snapshot',
    { requestSnapshot, executionSnapshot },
  );
  const executionUrl = manager.url();
  const submitterContext = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
  const submitter = await submitterContext.newPage();
  attachDiagnostics(submitter, 'finance_user_execution_submitter');
  await login(submitter, financeUserLogin);
  await submitter.goto(executionUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await waitForm(submitter, 'sc.payment.execution', executionId);
  await clickAction(submitter, '[data-product-primary-action][data-action-method="action_confirm"][data-action-enabled="true"]:visible', 'execute_button', 'submit payment execution');
  await waitForm(submitter, 'sc.payment.execution', executionId);
  const waiting = await readOne(submitter, 'sc.payment.execution', ['id', 'state', 'validation_status', 'review_ids'], executionId);
  if (executionPolicy.approval_required) {
    check(
      waiting.state === 'draft'
        && ['waiting', 'pending'].includes(String(waiting.validation_status))
        && Array.isArray(waiting.review_ids)
        && waiting.review_ids.length > 0,
      'configured payment execution approval creates tier reviews',
      { waiting, executionPolicy },
    );
  } else {
    check(
      executionPolicy.mode === 'none'
        && waiting.state === 'confirmed'
        && ['no', ''].includes(String(waiting.validation_status || ''))
        && Array.isArray(waiting.review_ids)
        && waiting.review_ids.length === 0,
      'optional payment execution approval confirms directly when disabled',
      { waiting, executionPolicy },
    );
  }
  await shot(submitter, '04b-execution-submitted');
  await submitterContext.close();
  await manager.reload({ waitUntil: 'domcontentloaded', timeout: 45000 });
  await waitForm(manager, 'sc.payment.execution', executionId);
  if (executionPolicy.approval_required) {
    check(
      executionPolicy.steps?.length === 1
        && executionPolicy.steps[0]?.group_xmlid === 'smart_construction_core.group_sc_cap_finance_manager',
      'enabled payment execution acceptance policy has one finance-manager step',
      { executionPolicy },
    );
    await clickAction(manager, '[data-action-method="validate_tier"][data-action-enabled="true"]:visible', 'execute_button', 'approve payment execution');
    await waitForm(manager, 'sc.payment.execution', executionId);
  }
  const confirmed = await readOne(manager, 'sc.payment.execution', ['id', 'state', 'validation_status', 'review_ids'], executionId);
  check(
    confirmed.state === 'confirmed'
      && (executionPolicy.approval_required ? confirmed.validation_status === 'validated' : ['no', ''].includes(String(confirmed.validation_status || ''))),
    'payment execution reaches policy-authorized confirmed state',
    { confirmed, executionPolicy },
  );
  await clickAction(manager, '[data-action-method="action_paid"][data-action-enabled="true"]:visible', 'execute_button', 'register paid');
  const paidRequestPayload = report.action_responses.findLast((row) => row.label === 'register paid')?.request_payload;
  check(
    paidRequestPayload?.intent === 'execute_button'
      && paidRequestPayload?.params?.button?.name === 'action_paid'
      && Number(paidRequestPayload?.meta?.action_id || 0) > 0
      && Number(paidRequestPayload?.meta?.menu_id || 0) > 0
      && Boolean(paidRequestPayload?.params?.button?.action_id)
      && Boolean(paidRequestPayload?.params?.button?.backend_identity)
      && Boolean(paidRequestPayload?.params?.button?.source_widget_id),
    'successful paid request captures complete contract authority envelope',
    { paidRequestPayload },
  );
  await waitForm(manager, 'sc.payment.execution', executionId);
  await manager.reload({ waitUntil: 'domcontentloaded', timeout: 45000 });
  await waitForm(manager, 'sc.payment.execution', executionId);
  const paid = await readOne(manager, 'sc.payment.execution', ['id', 'state', 'paid_amount', 'payment_request_id'], executionId);
  const completed = await readOne(manager, 'payment.request', ['id', 'state', 'amount', 'paid_amount_total', 'unpaid_amount', 'is_fully_paid'], requestId);
  check(paid.state === 'paid' && Number(paid.paid_amount) === 10000, 'execution is paid once', { paid });
  check(completed.state === 'done' && Number(completed.paid_amount_total) === 10000 && Number(completed.unpaid_amount) === 0 && completed.is_fully_paid === true, 'request amount and final state reconcile', { completed });
  report.transitions.push({ actor: managerLogin, execution_id: executionId, from: 'draft', via: ['confirmed'], to: paid.state, request_state: completed.state });
  await shot(manager, '05-paid-desktop');

  const ledger = await apiIntent(manager, 'api.data', { op: 'list', model: 'payment.ledger', fields: ['id', 'state', 'amount', 'payment_execution_id'], domain: [['payment_request_id', '=', requestId]], limit: 10 });
  const ledgerRows = ledger.body?.data?.records || ledger.body?.result?.records || [];
  const posted = ledgerRows.filter((row) => row.state === 'posted');
  check(ledger.status === 200 && posted.length === 1 && Number(posted[0].amount) === 10000, 'exactly one posted ledger reconciles', { rows: ledgerRows });
  const factsBeforeReplay = { paid, completed, ledgerRows };
  const duplicateFailureStart = report.failed_requests.length;
  const duplicateErrorStart = report.errors.length;
  const duplicate = await apiEnvelope(manager, paidRequestPayload);
  const duplicateReason = String(duplicate.body?.error?.reason_code || duplicate.body?.data?.result?.reason_code || '');
  const duplicateMessage = String(duplicate.body?.error?.message || duplicate.body?.data?.result?.message || '');
  const duplicateBusinessStateGuard = duplicate.status === 400
    && duplicateReason === 'BUSINESS_RULE_FAILED'
    && /只有.*已确认状态.*登记付款/.test(duplicateMessage);
  const duplicateContractStateGuard = duplicate.status === 403
    && duplicateReason === 'PERMISSION_DENIED'
    && duplicateMessage === 'ACTION_NOT_VISIBLE_IN_STATE';
  const duplicateGuardKind = duplicateBusinessStateGuard
    ? 'duplicate_payment_business_state_guard'
    : duplicateContractStateGuard
      ? 'duplicate_payment_contract_state_guard'
      : '';
  check(
    Boolean(duplicateGuardKind),
    'exact authorized paid request replay is rejected by an explicit paid-state guard',
    {
      status: duplicate.status,
      reason: duplicateReason,
      message: duplicateMessage,
      guard_kind: duplicateGuardKind,
      authority_metadata_missing: duplicateMessage === 'ACTION_CONTRACT_AUTHORITY_MISSING',
      server_error: duplicate.status >= 500,
    },
  );
  for (const failure of report.failed_requests.slice(duplicateFailureStart)) {
    if (failure.intent === 'execute_button' && failure.status === duplicate.status) failure.expected = duplicateGuardKind;
  }
  for (const error of report.errors.slice(duplicateErrorStart)) {
    if (error.type === 'console' && /status of (400|403)|BAD REQUEST|FORBIDDEN/i.test(error.text || '')) error.expected = duplicateGuardKind;
  }
  const paidAfterReplay = await readOne(manager, 'sc.payment.execution', ['id', 'state', 'paid_amount', 'payment_request_id'], executionId);
  const completedAfterReplay = await readOne(manager, 'payment.request', ['id', 'state', 'amount', 'paid_amount_total', 'unpaid_amount', 'is_fully_paid'], requestId);
  const ledgerAfterReplay = await apiIntent(manager, 'api.data', { op: 'list', model: 'payment.ledger', fields: ['id', 'state', 'amount', 'payment_execution_id'], domain: [['payment_request_id', '=', requestId]], limit: 10 });
  const ledgerRowsAfterReplay = ledgerAfterReplay.body?.data?.records || ledgerAfterReplay.body?.result?.records || [];
  check(
    JSON.stringify({ paid: paidAfterReplay, completed: completedAfterReplay, ledgerRows: ledgerRowsAfterReplay }) === JSON.stringify(factsBeforeReplay),
    'duplicate payment replay leaves execution request and ledger facts unchanged',
    { before: factsBeforeReplay, after: { paid: paidAfterReplay, completed: completedAfterReplay, ledgerRows: ledgerRowsAfterReplay } },
  );

  await manager.setViewportSize({ width: 390, height: 844 });
  await manager.goto(`${baseUrl}/r/payment.request/${requestId}?action_id=${actionId}&menu_id=${menuId}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await waitForm(manager, 'payment.request', requestId);
  const overflow = await manager.evaluate(() => Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth));
  check(overflow === 0, '390px final request has no horizontal overflow', { overflow });
  const refreshed = await readOne(manager, 'payment.request', ['id', 'state', 'paid_amount_total', 'unpaid_amount'], requestId);
  check(refreshed.state === 'done' && Number(refreshed.paid_amount_total) === 10000 && Number(refreshed.unpaid_amount) === 0, 'refresh preserves authoritative completion', { refreshed });
  await shot(manager, '06-paid-390');
  await managerContext.close();

  const unexpectedFailures = report.failed_requests.filter((row) => !row.expected);
  const unexpectedErrors = report.errors.filter((row) => !row.expected);
  check(unexpectedFailures.length === 0, 'no unexpected failed browser requests', { unexpectedFailures });
  check(unexpectedErrors.length === 0, 'no unexpected browser console errors', { unexpectedErrors });
  report.pass = true;
} catch (error) {
  report.error = error instanceof Error ? error.stack || error.message : String(error);
  throw error;
} finally {
  report.completed_at = new Date().toISOString();
  fs.writeFileSync(path.join(outputDir, 'summary.json'), JSON.stringify(report, null, 2));
  await browser.close();
}
