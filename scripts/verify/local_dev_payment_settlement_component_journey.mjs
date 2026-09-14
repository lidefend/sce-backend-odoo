import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';

const target = JSON.parse(process.env.LOCAL_DEV_PAYMENT_SETTLEMENT_COMPONENT_JSON || '{}');
const frontendUrl = String(process.env.FRONTEND_URL || '');
const database = String(process.env.DB_NAME || '');
const password = String(process.env.E2E_PASSWORD || '');
const candidateHead = String(process.env.CANDIDATE_GIT_HEAD || '');
const phase = String(process.env.JOURNEY_PHASE || '');
const login = String(target?.user?.login || '');
const actionId = Number(target?.action?.id || 0);
const menuId = Number(target?.menu?.id || 0);
const recordId = Number(target?.request?.id || 0);
const settlementName = String(target?.settlement?.name || '');
const outputDir = path.resolve(
  process.env.EVIDENCE_DIR || 'artifacts/playwright/local-dev-payment-settlement-component-journey',
);

function check(value, message, details = undefined) {
  if (value) return;
  throw new Error(`${message}${details === undefined ? '' : ` ${JSON.stringify(details)}`}`);
}

function normalize(value) {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

function numberFromText(value) {
  const match = normalize(value).replaceAll(',', '').match(/-?\d+(?:\.\d+)?/);
  return match ? Number(match[0]) : Number.NaN;
}

check(frontendUrl && database && password && login, 'local.dev settlement journey identity is incomplete');
check(/^[0-9a-f]{40}$/.test(candidateHead), 'candidate head is invalid');
check(['introduce', 'remove'].includes(phase), 'JOURNEY_PHASE must be introduce or remove');
check(actionId > 0 && menuId > 0 && recordId > 0 && settlementName,
  'local.dev settlement journey target is invalid', target);
fs.mkdirSync(outputDir, { recursive: true });

const browser = await launchChromium({ headless: true });
const context = await browser.newContext({ viewport: { width: 1088, height: 791 }, locale: 'zh-CN' });
const page = await context.newPage();
const errors = [];
const mutations = [];
const report = {
  schemaVersion: 'payment_settlement_component_journey.v2',
  candidateHead,
  phase,
  target,
  pass: false,
};

page.on('console', (message) => {
  if (message.type() === 'error' && !message.text().includes('favicon')) errors.push(message.text());
});
page.on('pageerror', (error) => errors.push(error.message));
page.on('request', (request) => {
  if (request.method() !== 'POST') return;
  let payload = {};
  try { payload = JSON.parse(request.postData() || '{}'); } catch {}
  const intent = String(payload?.intent || '');
  if (intent === 'payment.request.add.settlement.lines') {
    mutations.push({ intent, params: payload?.params || {} });
  }
  if (intent === 'api.data' && payload?.params?.op === 'write' && payload?.params?.model === 'payment.request') {
    mutations.push({ intent, params: payload?.params || {} });
  }
});

async function loginAndOpenForm() {
  await page.goto(`${frontendUrl}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const inputs = page.locator('input');
  await inputs.nth(0).fill(login);
  await inputs.nth(1).fill(password);
  if (await inputs.nth(2).count() && !(await inputs.nth(2).isDisabled())) await inputs.nth(2).fill(database);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 30000 });
  await page.goto(`${frontendUrl}/f/payment.request/${recordId}?menu_id=${menuId}&action_id=${actionId}`,
    { waitUntil: 'domcontentloaded', timeout: 45000 });
  const form = page.locator(
    `[data-product-page-mode="form"][data-form-model="payment.request"][data-form-record="${recordId}"]`,
  ).first();
  await form.waitFor({ timeout: 45000 });
  const component = form.locator(
    '[data-semantic-component="ProfessionalDetailCollectionControl"]'
      + '[data-amount-binding-mode="sum_when_nonempty"]',
  ).first();
  await component.waitFor({ timeout: 45000 });
  return { form, component };
}

async function fieldAmount(form, fieldName) {
  const field = form.locator(`[data-field-name="${fieldName}"]`).first();
  await field.waitFor({ timeout: 30000 });
  const input = field.locator('input').first();
  if (await input.count()) return numberFromText(await input.inputValue());
  return numberFromText(await field.innerText());
}

async function ensureDetailOpen(component) {
  if (await component.locator('[data-detail-collection-content]').count()) return;
  await component.getByRole('button', { name: /按明细填写/ }).first().click();
  await component.locator('[data-detail-collection-content]').first().waitFor({ timeout: 10000 });
}

async function runIntroduce() {
  const { form, component } = await loginAndOpenForm();
  const beforeRows = Number(await component.getAttribute('data-row-count') || 0);
  check(beforeRows === 0, 'dedicated fixture must start without optional details', { beforeRows });
  await ensureDetailOpen(component);
  await page.screenshot({ path: path.join(outputDir, 'introduce-before.png'), fullPage: true });

  await component.getByRole('button', { name: /从结算单引入/ }).click();
  const dialog = page.locator('[data-settle-introduce]').first();
  await dialog.waitFor({ timeout: 30000 });
  const option = dialog.locator('.settle-option').filter({ hasText: settlementName }).first();
  await option.waitFor({ timeout: 30000 });
  await option.click();
  const preview = dialog.locator('[data-settle-preview]').first();
  await preview.waitFor({ timeout: 30000 });
  check(await preview.locator('.settle-line:not(.is-disabled)').count() > 0,
    'settlement preview has no selectable lines');
  const ratioInput = preview.locator('.settle-apply-input input').first();
  await ratioInput.fill('1');
  check(await ratioInput.inputValue() === '1', 'settlement apply ratio was not set to the fixture value');

  const mutationResponse = page.waitForResponse(async (response) => {
    if (!response.url().includes('/api/v1/intent') || response.request().method() !== 'POST') return false;
    try {
      const payload = JSON.parse(response.request().postData() || '{}');
      return payload?.intent === 'payment.request.add.settlement.lines';
    } catch {
      return false;
    }
  }, { timeout: 30000 });
  await page.getByRole('button', { name: /^确认引入$/ }).click();
  const response = await mutationResponse;
  const responseBody = await response.json();
  check(response.ok(), 'settlement introduce request failed', { status: response.status(), responseBody });
  check(responseBody?.ok !== false, 'settlement introduce intent returned failure', responseBody);
  await dialog.waitFor({ state: 'hidden', timeout: 30000 });

  await page.reload({ waitUntil: 'domcontentloaded', timeout: 45000 });
  await form.waitFor({ timeout: 45000 });
  await component.waitFor({ timeout: 45000 });
  const afterRows = Number(await component.getAttribute('data-row-count') || 0);
  const requestAmount = await fieldAmount(form, 'amount');
  const returnedTotal = Number(responseBody?.data?.total_applied || 0);
  check(afterRows > beforeRows, 'introduced detail is not visible after authoritative reload', { beforeRows, afterRows });
  check(Number.isFinite(requestAmount) && Math.abs(requestAmount - returnedTotal) < 0.01,
    'reloaded request amount does not match introduced total', { requestAmount, returnedTotal });
  check(mutations.length === 1, 'introduce phase must execute one mutation', mutations);
  check(errors.length === 0, 'browser emitted console or page errors', errors);
  await page.screenshot({ path: path.join(outputDir, 'introduce-after-authoritative-reload.png'), fullPage: true });
  Object.assign(report, { pass: true, beforeRows, afterRows, requestAmount, returnedTotal, mutations, errors });
}

async function waitForRowCount(component, expected) {
  await component.evaluate((node, value) => new Promise((resolve, reject) => {
    const deadline = Date.now() + 10000;
    const poll = () => {
      if (Number(node.getAttribute('data-row-count') || 0) === value) return resolve();
      if (Date.now() >= deadline) return reject(new Error(`row count did not become ${value}`));
      setTimeout(poll, 50);
    };
    poll();
  }), expected);
}

async function runRemove() {
  const { form, component } = await loginAndOpenForm();
  const beforeRows = Number(await component.getAttribute('data-row-count') || 0);
  check(beforeRows === 1, 'remove phase requires exactly one dedicated fixture detail', { beforeRows });
  const amountBefore = await fieldAmount(form, 'amount');
  const removeButton = component.getByRole('button', { name: /^删除/ }).first();
  await removeButton.waitFor({ state: 'visible', timeout: 10000 });
  check(normalize(await removeButton.textContent()) === '删除',
    'persisted one2many removal must present child-record deletion semantics');
  await removeButton.click();
  const confirmation = page.locator('[data-dialog-purpose="intent-confirmation"][data-state="open"]').first();
  await confirmation.waitFor({ timeout: 10000 });
  await confirmation.getByRole('button', { name: /^取消$/ }).click();
  await confirmation.waitFor({ state: 'hidden', timeout: 10000 });
  check(Number(await component.getAttribute('data-row-count') || 0) === beforeRows,
    'cancelling last-detail removal changed the draft rows');
  check(mutations.length === 0, 'cancelling last-detail removal emitted a write', mutations);
  await page.screenshot({ path: path.join(outputDir, 'remove-after-cancel-before-save.png'), fullPage: true });

  await removeButton.click();
  await confirmation.waitFor({ timeout: 10000 });
  await confirmation.getByRole('button', { name: /^确认/ }).click();
  await waitForRowCount(component, 0);
  check(Number(await component.getAttribute('data-removed-row-count') || 0) === 1,
    'persisted detail was not retained as a pending deletion before save');
  check(mutations.length === 0, 'draft deletion emitted a write before save', mutations);
  await page.screenshot({ path: path.join(outputDir, 'remove-after-confirm-before-save.png'), fullPage: true });

  const restoreButton = component.getByRole('button', { name: /^撤销删除/ }).first();
  await restoreButton.waitFor({ state: 'visible', timeout: 10000 });
  await restoreButton.click();
  await waitForRowCount(component, beforeRows);
  check(Number(await component.getAttribute('data-removed-row-count') || 0) === 0,
    'undo did not restore the pending-deletion row');
  check(mutations.length === 0, 'undo emitted a write before save', mutations);
  await page.screenshot({ path: path.join(outputDir, 'remove-after-undo-before-save.png'), fullPage: true });

  await removeButton.click();
  await confirmation.waitFor({ timeout: 10000 });
  await confirmation.getByRole('button', { name: /^确认/ }).click();
  await waitForRowCount(component, 0);
  check(Number(await component.getAttribute('data-removed-row-count') || 0) === 1,
    'second confirmed deletion did not restore pending-save state');

  const writeResponse = page.waitForResponse(async (response) => {
    if (!response.url().includes('/api/v1/intent') || response.request().method() !== 'POST') return false;
    try {
      const payload = JSON.parse(response.request().postData() || '{}');
      return payload?.intent === 'api.data'
        && payload?.params?.op === 'write'
        && payload?.params?.model === 'payment.request';
    } catch {
      return false;
    }
  }, { timeout: 30000 });
  await page.getByRole('button', { name: /^保存修改$/ }).first().click();
  const response = await writeResponse;
  const responseBody = await response.json();
  check(response.ok(), 'last-detail removal save failed', { status: response.status(), responseBody });
  check(responseBody?.ok !== false, 'last-detail removal returned failure', responseBody);

  await page.reload({ waitUntil: 'domcontentloaded', timeout: 45000 });
  await form.waitFor({ timeout: 45000 });
  await component.waitFor({ timeout: 45000 });
  const afterRows = Number(await component.getAttribute('data-row-count') || 0);
  const amountAfter = await fieldAmount(form, 'amount');
  check(afterRows === 0, 'last detail remains after authoritative reload', { afterRows });
  check(Math.abs(amountAfter - amountBefore) < 0.01,
    'last authoritative detail total was not preserved after removal', { amountBefore, amountAfter });
  check(mutations.length === 1, 'remove phase must execute one payment.request write', mutations);
  check(errors.length === 0, 'browser emitted console or page errors', errors);
  await page.screenshot({ path: path.join(outputDir, 'remove-after-authoritative-reload.png'), fullPage: true });
  Object.assign(report, { pass: true, beforeRows, afterRows, amountBefore, amountAfter, mutations, errors });
}

try {
  if (phase === 'introduce') await runIntroduce();
  else await runRemove();
  fs.writeFileSync(path.join(outputDir, `${phase}-summary.json`), JSON.stringify(report, null, 2));
  console.log(`[local.dev.payment.settlement-component] PASS phase=${phase} record=${recordId} mutations=${mutations.length}`);
} catch (error) {
  report.error = String(error instanceof Error ? error.stack || error.message : error);
  report.errors = errors;
  report.mutations = mutations;
  fs.writeFileSync(path.join(outputDir, `${phase}-summary.json`), JSON.stringify(report, null, 2));
  await page.screenshot({ path: path.join(outputDir, `${phase}-failure.png`), fullPage: true }).catch(() => {});
  throw error;
} finally {
  await browser.close();
}
