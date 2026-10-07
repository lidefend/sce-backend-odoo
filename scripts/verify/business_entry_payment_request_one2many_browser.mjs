#!/usr/bin/env node
// Focused product-surface acceptance for the 付款申请 formal business entry
// (payment.request) detail collection. It reproduces the recorded gap "edit an
// existing imported detail row, then save is refused as a duplicate row" and
// proves the behaviour from the runtime contract and the persisted result, not
// from a selector string or an implementation diagnosis.
//
// Registered environment: external daily development server
//   config/frontend/acceptance_environments_v1.json profiles.daily
//   ENV=dev, database sc_demo, expected served revision required.
// The owner explicitly authorized mutating the sc_demo acceptance fixture, so the
// lane fails closed unless the caller presents the explicit write token and the
// managed record resolution. It only writes the declared fixture carrier and
// restores it to the declared empty start state before returning.
//
// The carrier is bound by its declared fixture xmlid through the managed
// resolution body; no database id is hardcoded. The declared precondition of the
// reproduced defect is a collection whose first business column holds one constant
// value, so the lane introduces lines from two declared settlements and asserts
// that constant before editing.
import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';

const BASE = (process.env.SC_ACCEPTANCE_FRONTEND_URL || process.env.FRONTEND_URL || '').replace(/\/$/, '');
const DB = process.env.SC_ACCEPTANCE_DATABASE || process.env.DB_NAME || 'sc_demo';
const LOGIN = process.env.ACCEPTANCE_LOGIN || '';
const PASSWORD = process.env.ACCEPTANCE_PASSWORD || '';
const EXPECTED_SHA = process.env.SC_ACCEPTANCE_TARGET_SHA || '';
const RESOLUTION_PATH = process.env.ACCEPTANCE_RECORD_RESOLUTION || '';
const WRITE_CONFIRM = process.env.SC_ENTRY_WRITE_CONFIRM || '';
const WRITE_CONFIRM_TOKEN = 'DRIVE_DAILY_SC_DEMO_PAYMENT_REQUEST_ONE2MANY';
const OUT_DIR = process.env.SC_ACCEPTANCE_OUTPUT_DIR
  || path.join('artifacts', 'frontend-business-entry-payment-request', String(Date.now()));

const O2M_MODEL = 'payment.request.line';
const INTRODUCE_DIALOG_PURPOSE = 'payment-settlement-introduce';
const DECLARED_RECORD_XMLID = 'smart_construction_acceptance_fixture.fe_delivery_hardening_payment_request_a';
const DECLARED_SETTLEMENTS = ['FE-B05-WORK-SETTLEMENT-001', 'FE-J06-SETTLEMENT-001'];
const DECLARED_EDIT_COLUMN = '本次申请';
const DECLARED_EDIT_VALUE = '150';
const DECLARED_EMPTY_AMOUNT = '20.00';
const DUPLICATE_BLOCK = /存在重复|重复行值|主值重复|明细行重复|重复明细/;
// The rendered control id is derived from the field path and carries a per-render
// hash suffix, so the driver matches the stable prefix only; the assertion that
// the write actually landed is the persisted readback below, never the selector.
const AMOUNT_INPUT = 'input[id*="-field-amount-occ"]';

const problems = [];
const observations = [];
const requests = [];

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
  const entry = targets.payment_request;
  if (!entry) throw new Error('managed resolution is missing payment_request');
  if (String(entry.record_xmlid || '') !== DECLARED_RECORD_XMLID) {
    throw new Error(`resolution record_xmlid ${entry.record_xmlid} != declared ${DECLARED_RECORD_XMLID}`);
  }
  for (const key of ['record_id', 'menu_id', 'action_id']) {
    if (!(Number(entry[key]) > 0)) throw new Error(`resolution ${key} is missing`);
  }
  return entry;
}

async function servedRevision() {
  const response = await fetch(`${BASE}/api/runtime-version`);
  return response.json();
}

const recordRoute = (entry) => `/f/${entry.model || 'payment.request'}/${entry.record_id}`
  + `?menu_id=${entry.menu_id}&action_id=${entry.action_id}`;

const o2m = (page) => page.locator(`[data-relation-model="${O2M_MODEL}"]`);

async function o2mState(page) {
  return page.evaluate((model) => {
    const node = document.querySelector(`[data-relation-model="${model}"]`);
    if (!node) return null;
    return {
      row_count: Number(node.getAttribute('data-row-count') || -1),
      removed_row_count: Number(node.getAttribute('data-removed-row-count') || -1),
      can_inline_edit: node.getAttribute('data-can-inline-edit'),
      control_state: node.getAttribute('data-control-state'),
      validation_visible: node.getAttribute('data-validation-visible'),
      dirty_summary: (node.innerText.match(/待提交：[^\n]*/) || [''])[0],
      columns: Array.from(node.querySelectorAll('thead th')).map((th) => th.innerText.trim()).filter(Boolean),
      source_types: Array.from(node.querySelectorAll('input[placeholder="来源类型"]')).map((n) => n.value),
    };
  }, O2M_MODEL);
}

async function openRecord(page, entry) {
  await page.goto(`${BASE}${recordRoute(entry)}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(3500);
  const disclosure = page.getByRole('button', { name: '按明细填写' }).first();
  if (await disclosure.count()) {
    try { await disclosure.click({ timeout: 8000 }); } catch { /* already expanded */ }
  }
  await page.waitForTimeout(1500);
  const state = await o2mState(page);
  if (!state) fail('the record form did not expose the declared detail collection');
  return state;
}

async function saveDraft(page) {
  const since = requests.length;
  await page.getByRole('button', { name: '保存草稿' }).first().click();
  await page.waitForTimeout(6000);
  return requests.slice(since);
}

async function confirmIfAsked(page) {
  const dialog = page.locator('section[role="dialog"][data-state="open"], div[role="dialog"]:visible').last();
  if (!(await dialog.count())) return '';
  const text = String((await dialog.textContent()) || '').replace(/\s+/g, ' ').trim();
  const confirm = dialog.locator('button').filter({ hasText: /^确认/ }).last();
  if (await confirm.count()) {
    await confirm.click();
    await page.waitForTimeout(1500);
    return text.slice(0, 200);
  }
  return `unconfirmed:${text.slice(0, 120)}`;
}

async function removeAllRows(page) {
  const collection = o2m(page);
  for (let guard = 0; guard < 8; guard += 1) {
    const rowCount = Number(await collection.getAttribute('data-row-count'));
    if (rowCount <= 0) break;
    const remove = collection.locator('button.o2m-row-remove').first();
    if (!(await remove.count())) break;
    await remove.click({ timeout: 10000 });
    await page.waitForTimeout(1200);
    await confirmIfAsked(page);
  }
}

async function introduceSettlement(page, settlement) {
  await page.locator('[data-contract-entry-label="从结算单引入"]').first().click();
  await page.waitForTimeout(3000);
  const dialog = page.locator(`[data-dialog-purpose="${INTRODUCE_DIALOG_PURPOSE}"]`);
  await dialog.waitFor({ state: 'visible', timeout: 20000 });
  const back = dialog.getByRole('button', { name: '换一个结算单' });
  if (await back.count()) {
    await back.first().click();
    await page.waitForTimeout(1800);
  }
  await dialog.getByPlaceholder('搜索结算单号 / 名称').fill(settlement);
  await dialog.getByRole('button', { name: '搜索' }).click();
  await page.waitForTimeout(3500);
  const option = dialog.locator('.settle-option', { hasText: settlement });
  if (!(await option.count())) throw new Error(`declared settlement ${settlement} is not offered by the entry`);
  await option.first().click();
  await page.waitForTimeout(3000);
  const confirm = dialog.getByRole('button', { name: '确认引入' });
  if (await confirm.isDisabled()) {
    const selectAll = dialog.locator('.settle-preview-toolbar input[type=checkbox]');
    if (await selectAll.count()) {
      await selectAll.first().click({ force: true });
      await page.waitForTimeout(1200);
    }
    const lineBoxes = dialog.locator('.settle-line input[type=checkbox]');
    const count = await lineBoxes.count();
    for (let index = 0; index < count; index += 1) {
      await lineBoxes.nth(index).click({ force: true });
      await page.waitForTimeout(400);
    }
  }
  if (await confirm.isDisabled()) throw new Error(`settlement ${settlement} offered no selectable line`);
  await confirm.click();
  await page.waitForTimeout(5000);
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
  const browser = await launchChromium({ headless: true });
  const context = await browser.newContext({ locale: 'zh-CN', viewport: { width: 1440, height: 1200 } });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on('console', (message) => { if (message.type() === 'error') consoleErrors.push(message.text()); });
  page.on('pageerror', (error) => consoleErrors.push(`pageerror:${error.message}`));
  page.on('response', async (response) => {
    if (!response.url().includes('/api/v1/intent')) return;
    try {
      const payload = JSON.parse(response.request().postData() || '{}');
      requests.push({ intent: payload.intent, model: payload.params?.model || '', status: response.status() });
    } catch { /* non-JSON request bodies are unrelated */ }
  });

  await page.goto(`${BASE}/login?db=${DB}`, { waitUntil: 'networkidle' });
  const inputs = page.locator('input');
  await inputs.nth(0).fill(LOGIN);
  await inputs.nth(1).fill(PASSWORD);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45000 });
  await page.waitForTimeout(3000);

  // Reset to the declared empty start state so a previously interrupted run can
  // never be mistaken for a pass, and so restoration below is verifiable.
  let state = await openRecord(page, entry);
  if (state.row_count > 0) {
    observations.push({ stage: 'reset_start_state', row_count: state.row_count });
    await removeAllRows(page);
    await saveDraft(page);
    state = await openRecord(page, entry);
  }
  if (state.row_count !== 0) fail(`carrier did not reach the declared empty start (row_count=${state.row_count})`);

  for (const settlement of DECLARED_SETTLEMENTS) {
    await introduceSettlement(page, settlement);
    await page.waitForTimeout(1200);
  }
  state = await o2mState(page);
  observations.push({ stage: 'after_introduce', ...state });
  if (state.row_count !== DECLARED_SETTLEMENTS.length) {
    fail(`introduced row_count ${state.row_count} != declared ${DECLARED_SETTLEMENTS.length}`);
  }
  if (!state.columns.includes(DECLARED_EDIT_COLUMN)) {
    fail(`the contract-rendered collection does not expose the declared column ${DECLARED_EDIT_COLUMN}; columns=${state.columns.join(',')}`);
  }
  // The reproduced defect needs the declared shape: every row shares the value of
  // the collection's first business column, so a value-keyed duplicate rule fires.
  // The rendered control count may exceed the row count, so the precondition is
  // "every rendered value is the same non-empty value", bound to the row count.
  const distinct = new Set(state.source_types);
  if (state.source_types.length < state.row_count || distinct.size !== 1 || state.source_types.includes('')) {
    fail(`declared constant-first-column precondition not met: rows=${state.row_count} values=${JSON.stringify(state.source_types)}`);
  }

  const target = page.getByPlaceholder(DECLARED_EDIT_COLUMN).first();
  const previous = await target.inputValue();
  await target.fill(DECLARED_EDIT_VALUE);
  await page.waitForTimeout(1200);
  const beforeSave = await o2mState(page);
  const saveRequests = await saveDraft(page);
  const bodyText = await page.locator('body').innerText();
  state = await o2mState(page);
  await page.screenshot({ path: path.join(OUT_DIR, 'after-save.png'), fullPage: true });

  if (DUPLICATE_BLOCK.test(bodyText)) fail('saving an edited row still reports a duplicate-row block');
  if (String(beforeSave.validation_visible) === 'true' || String(state.validation_visible) === 'true') {
    fail('the collection still shows a validation block after editing a row');
  }
  if (!/待提交：无变更/.test(String(state.dirty_summary))) {
    fail(`the collection did not accept the save (${state.dirty_summary || 'no dirty summary'})`);
  }
  const writeObserved = saveRequests.some((row) => row.model === entry.model && row.status === 200);
  if (!writeObserved) fail(`no successful ${entry.model} request was issued by the save: ${JSON.stringify(saveRequests)}`);

  // Decisive evidence: a fresh load must show the edited value persisted.
  state = await openRecord(page, entry);
  const persisted = await page.getByPlaceholder(DECLARED_EDIT_COLUMN).first().inputValue();
  observations.push({ stage: 'readback_after_save', persisted, row_count: state.row_count, edits: {
    previous, edited: DECLARED_EDIT_VALUE,
  } });
  if (state.row_count !== DECLARED_SETTLEMENTS.length) fail(`readback row_count ${state.row_count} changed after save`);
  if (String(persisted) !== DECLARED_EDIT_VALUE) fail(`edited value ${persisted} != declared ${DECLARED_EDIT_VALUE} after readback`);

  // Restore the declared empty start state through the same product surface:
  // remove the introduced lines, persist, reload into the declared direct-entry
  // state, enter the declared empty amount, persist again, then read back.
  await removeAllRows(page);
  await saveDraft(page);
  let restored = await openRecord(page, entry);
  if (restored.row_count !== 0) fail(`restoration left row_count ${restored.row_count}`);
  const amount = page.locator(AMOUNT_INPUT).first();
  if (await amount.count()) {
    await amount.fill(DECLARED_EMPTY_AMOUNT);
    await page.waitForTimeout(900);
  } else {
    const inventory = await page.evaluate(() => Array.from(document.querySelectorAll('input'))
      .filter((node) => node.offsetParent || node.getClientRects().length)
      .map((node) => `${node.id || '<no-id>'}|${node.getAttribute('placeholder') || ''}`));
    observations.push({ stage: 'amount_field_absent', visible_inputs: inventory });
    fail('the declared amount field is not exposed for restoration');
  }
  await saveDraft(page);
  restored = await openRecord(page, entry);
  let restoredAmount = '';
  if (await page.locator(AMOUNT_INPUT).count()) {
    restoredAmount = await page.locator(AMOUNT_INPUT).first().inputValue();
  } else {
    fail('the declared amount field is not exposed after restoration');
  }
  observations.push({ stage: 'restored', row_count: restored.row_count, amount: restoredAmount });
  if (restored.row_count !== 0) fail(`restoration left row_count ${restored.row_count}`);
  if (String(restoredAmount) !== DECLARED_EMPTY_AMOUNT) fail(`restoration left amount ${restoredAmount}`);
  if (consoleErrors.length) fail(`runtime console errors observed: ${consoleErrors.slice(0, 3).join(' | ')}`);

  await browser.close();
  const report = {
    ok: problems.length === 0,
    schema: 'frontend.business_entry.payment_request_one2many.v1',
    served_revision: served,
    database: DB,
    carrier: { record_xmlid: entry.record_xmlid, record_identity: entry.record_identity },
    declared: {
      settlements: DECLARED_SETTLEMENTS,
      edit_column: DECLARED_EDIT_COLUMN,
      edit_value: DECLARED_EDIT_VALUE,
      empty_amount: DECLARED_EMPTY_AMOUNT,
    },
    observations,
    problems,
  };
  fs.writeFileSync(path.join(OUT_DIR, 'report.json'), `${JSON.stringify(report, null, 2)}\n`);
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
  if (problems.length) process.exitCode = 1;
}

main().catch((error) => {
  fail(`exception:${error.message}`);
  fs.mkdirSync(OUT_DIR, { recursive: true });
  fs.writeFileSync(path.join(OUT_DIR, 'report.json'), `${JSON.stringify({ ok: false, problems }, null, 2)}\n`);
  process.stdout.write(`${JSON.stringify({ ok: false, problems }, null, 2)}\n`);
  process.exitCode = 1;
});
