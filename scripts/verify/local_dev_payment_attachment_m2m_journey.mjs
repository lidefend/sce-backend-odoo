import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';

const target = JSON.parse(process.env.LOCAL_DEV_PAYMENT_ATTACHMENT_M2M_JSON || '{}');
const frontendUrl = String(process.env.FRONTEND_URL || '');
const database = String(process.env.DB_NAME || '');
const password = String(process.env.E2E_PASSWORD || '');
const candidateHead = String(process.env.CANDIDATE_GIT_HEAD || '');
const candidateFingerprint = String(process.env.CANDIDATE_FINGERPRINT || '');
const outputDir = path.resolve(process.env.EVIDENCE_DIR || 'artifacts/playwright/local-dev-payment-attachment-m2m-journey');
const login = String(target?.user?.login || '');
const actionId = Number(target?.action?.id || 0);
const menuId = Number(target?.menu?.id || 0);
const recordId = Number(target?.request?.id || 0);
const attachmentId = Number(target?.attachment?.id || 0);
const attachmentName = String(target?.attachment?.name || '');

function check(value, message, details = undefined) {
  if (value) return;
  throw new Error(`${message}${details === undefined ? '' : ` ${JSON.stringify(details)}`}`);
}

function normalize(value) {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

check(frontendUrl && database && password && login, 'payment attachment M2M identity is incomplete');
check(/^[0-9a-f]{40}$/.test(candidateHead), 'candidate head is invalid');
check(/^[0-9a-f]{64}$/.test(candidateFingerprint), 'candidate fingerprint is invalid');
check(actionId > 0 && menuId > 0 && recordId > 0 && attachmentId > 0 && attachmentName,
  'payment attachment M2M target is invalid', target);
fs.mkdirSync(outputDir, { recursive: true });

async function openSample(viewport) {
  const browser = await launchChromium({ headless: true });
  const context = await browser.newContext({ viewport, locale: 'zh-CN' });
  const page = await context.newPage();
  const errors = [];
  const writes = [];
  page.on('console', (message) => {
    if (message.type() === 'error' && !message.text().includes('favicon')) errors.push(message.text());
  });
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('request', (request) => {
    if (request.method() !== 'POST') return;
    let payload = {};
    try { payload = JSON.parse(request.postData() || '{}'); } catch {}
    const ids = Array.isArray(payload?.params?.ids) ? payload.params.ids.map(Number) : [];
    if (
      payload?.intent === 'api.data'
      && payload?.params?.op === 'write'
      && payload?.params?.model === 'payment.request'
      && (
        ids.includes(recordId)
        || Number(payload?.params?.id || payload?.params?.record_id || 0) === recordId
      )
    ) writes.push(payload.params);
  });
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
  await form.waitFor({ timeout: 60000 });
  const field = form.locator('[data-field-name="attachment_ids"]:visible').first();
  await field.waitFor({ timeout: 30000 });
  await field.scrollIntoViewIfNeeded();
  const unlink = field.getByRole('button', { name: `解除关联${attachmentName}`, exact: true });
  await unlink.waitFor({ state: 'visible', timeout: 30000 });
  return { browser, page, form, field, unlink, writes, errors };
}

async function exerciseCancel(viewport, key) {
  const sample = await openSample(viewport);
  try {
    await sample.page.screenshot({ path: path.join(outputDir, `${key}-before.png`), fullPage: true });
    await sample.unlink.click();
    await sample.unlink.waitFor({ state: 'hidden', timeout: 10000 });
    check(sample.writes.length === 0, 'draft unlink wrote before save', sample.writes);
    check(await sample.page.getByRole('button', { name: '放弃', exact: true }).isVisible(),
      'draft unlink did not expose the form discard action');
    await sample.page.screenshot({ path: path.join(outputDir, `${key}-pending.png`), fullPage: true });
    await sample.page.getByRole('button', { name: '放弃', exact: true }).click();
    await sample.field.getByRole('button', { name: `解除关联${attachmentName}`, exact: true })
      .waitFor({ state: 'visible', timeout: 30000 });
    check(sample.writes.length === 0, 'discarding draft unlink wrote to the backend', sample.writes);
    await sample.page.screenshot({ path: path.join(outputDir, `${key}-restored.png`), fullPage: true });
    return {
      viewport,
      route: sample.page.url(),
      pendingAction: '解除关联',
      cancelAction: '放弃',
      restored: true,
      writeCount: sample.writes.length,
      errors: sample.errors,
    };
  } finally {
    await sample.browser.close();
  }
}

async function exercisePersist() {
  const sample = await openSample({ width: 1088, height: 791 });
  try {
    await sample.unlink.click();
    await sample.unlink.waitFor({ state: 'hidden', timeout: 10000 });
    check(sample.writes.length === 0, 'relationship unlink wrote before save', sample.writes);
    await sample.page.screenshot({ path: path.join(outputDir, 'persist-pending.png'), fullPage: true });
    const writeResponse = sample.page.waitForResponse((response) => {
      if (!response.url().includes('/api/v1/intent') || response.request().method() !== 'POST') return false;
      try {
        const payload = JSON.parse(response.request().postData() || '{}');
        const ids = Array.isArray(payload?.params?.ids) ? payload.params.ids.map(Number) : [];
        return payload?.intent === 'api.data'
          && payload?.params?.op === 'write'
          && payload?.params?.model === 'payment.request'
          && ids.includes(recordId);
      } catch {
        return false;
      }
    }, { timeout: 30000 });
    await sample.page.getByRole('button', { name: '保存修改', exact: true }).click();
    const response = await writeResponse;
    const responseBody = await response.json();
    check(response.ok() && responseBody?.ok !== false,
      'payment attachment relationship save failed', { status: response.status(), responseBody });
    await sample.form.locator('[data-dirty-state="clean"]').first().waitFor({ timeout: 30000 });
    check(sample.writes.length === 1, 'expected one payment.request write', sample.writes);
    const values = sample.writes[0]?.vals || sample.writes[0]?.values || {};
    check(Object.prototype.hasOwnProperty.call(values, 'attachment_ids'),
      'payment.request write omitted attachment_ids', sample.writes[0]);
    check(!normalize(await sample.field.innerText()).includes(attachmentName),
      'saved form still renders the detached attachment');
    await sample.page.screenshot({ path: path.join(outputDir, 'persist-saved.png'), fullPage: true });
    return {
      viewport: { width: 1088, height: 791 },
      route: sample.page.url(),
      writeCount: sample.writes.length,
      actualAttachmentProtocol: values.attachment_ids,
      errors: sample.errors,
    };
  } finally {
    await sample.browser.close();
  }
}

const report = {
  schemaVersion: 'payment_attachment_m2m_journey.v1',
  candidateHead,
  candidateFingerprint,
  target,
  startedAt: new Date().toISOString(),
  pass: false,
};

try {
  report.cancelSamples = [
    await exerciseCancel({ width: 1088, height: 791 }, 'desktop-cancel'),
    await exerciseCancel({ width: 390, height: 844 }, 'mobile-cancel'),
  ];
  report.persistSample = await exercisePersist();
  check(report.cancelSamples.every((sample) => sample.restored && sample.writeCount === 0 && !sample.errors.length),
    'cancel sample failed', report.cancelSamples);
  check(report.persistSample.writeCount === 1 && !report.persistSample.errors.length,
    'persist sample failed', report.persistSample);
  report.pass = true;
} catch (error) {
  report.failure = error instanceof Error ? error.message : String(error);
} finally {
  report.finishedAt = new Date().toISOString();
  fs.writeFileSync(path.join(outputDir, 'browser-summary.json'), `${JSON.stringify(report, null, 2)}\n`);
}

if (!report.pass) throw new Error(report.failure || 'payment attachment M2M journey failed');
