import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';

const target = JSON.parse(process.env.LOCAL_DEV_PAYMENT_SETTLEMENT_COMPONENT_JSON || '{}');
const frontendUrl = String(process.env.FRONTEND_URL || '');
const database = String(process.env.DB_NAME || '');
const password = String(process.env.E2E_PASSWORD || '');
const login = String(target?.user?.login || '');
const actionId = Number(target?.action?.id || 0);
const menuId = Number(target?.menu?.id || 0);
const recordId = Number(target?.request?.id || 0);
const settlementName = String(target?.settlement?.name || '');
const outputDir = path.resolve('artifacts/playwright/local-dev-payment-settlement-component-journey');

function check(value, message, details = undefined) {
  if (value) return;
  throw new Error(`${message}${details === undefined ? '' : ` ${JSON.stringify(details)}`}`);
}

function normalize(value) {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

check(frontendUrl && database && password && login, 'local.dev settlement journey identity is incomplete');
check(actionId > 0 && menuId > 0 && recordId > 0 && settlementName,
  'local.dev settlement journey target is invalid', target);
fs.mkdirSync(outputDir, { recursive: true });

const browser = await launchChromium({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
const page = await context.newPage();
const errors = [];
const mutations = [];
const report = {
  schemaVersion: 'payment_settlement_component_journey.v1',
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
});

try {
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
  const component = form.locator('[data-semantic-component="PaymentSettlementDetailCollectionControl"]').first();
  await component.waitFor({ timeout: 45000 });
  const beforeRows = await component.locator('tbody tr:visible').count();
  await page.screenshot({ path: path.join(outputDir, 'before-introduce.png'), fullPage: true });

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
  check(await ratioInput.inputValue() === '1', 'settlement apply ratio was not reduced to the repeatable fixture value');
  await page.screenshot({ path: path.join(outputDir, 'settlement-preview.png'), fullPage: true });

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
  await page.waitForTimeout(800);

  await page.reload({ waitUntil: 'domcontentloaded', timeout: 45000 });
  await form.waitFor({ timeout: 45000 });
  await component.waitFor({ timeout: 45000 });
  const afterRows = await component.locator('tbody tr:visible').count();
  const componentText = normalize(await component.innerText());
  check(afterRows > beforeRows || componentText.includes(String(target.settlement.name || '')),
    'introduced settlement line is not visible after authoritative reload',
    { beforeRows, afterRows, componentText, settlement: target.settlement });
  check(mutations.length === 1, 'journey must execute exactly one settlement-introduction mutation', mutations);
  check(errors.length === 0, 'browser emitted console or page errors', errors);
  await page.screenshot({ path: path.join(outputDir, 'after-reload.png'), fullPage: true });

  report.pass = true;
  report.beforeRows = beforeRows;
  report.afterRows = afterRows;
  report.mutations = mutations;
  report.response = responseBody;
  report.errors = errors;
  fs.writeFileSync(path.join(outputDir, 'summary.json'), JSON.stringify(report, null, 2));
  console.log(`[local.dev.payment.settlement-component] PASS record=${recordId} mutations=${mutations.length}`);
} catch (error) {
  report.error = String(error instanceof Error ? error.stack || error.message : error);
  report.errors = errors;
  report.mutations = mutations;
  fs.writeFileSync(path.join(outputDir, 'summary.json'), JSON.stringify(report, null, 2));
  await page.screenshot({ path: path.join(outputDir, 'failure.png'), fullPage: true }).catch(() => {});
  throw error;
} finally {
  await browser.close();
}
