// P4 user-journey probe: business configuration administrator grants the
// existing data-read capability to the finance operator through Data Permission.
import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from '../verify/playwright_runtime.mjs';
import { matrixLoginUrl } from '../verify/business_entry_matrix_model.mjs';
import { fillLoginCredentials } from '../verify/frontend_authenticated_intent.mjs';
import { captureReleasedNavigation } from '../verify/released_navigation_target.mjs';

const BASE = String(
  process.env.SC_ACCEPTANCE_FRONTEND_URL || 'http://127.0.0.1:18083/t/clean',
).replace(/\/$/, '');
const LOGIN = String(
  process.env.CONFIGURATION_ADMIN_LOGIN || 'fixture_role_business_config_admin',
);
const TARGET_LOGIN = String(process.env.FINANCE_LOGIN || 'fixture_role_finance');
const PASSWORD = String(process.env.ACCEPTANCE_PASSWORD || '');
const TARGET_SHA = String(process.env.SC_ACCEPTANCE_TARGET_SHA || '');
const BUILD_SHA256 = String(process.env.SC_ACCEPTANCE_BUILD_SHA256 || '');
const OUTPUT_DIR = path.resolve(
  process.env.SC_ACCEPTANCE_OUTPUT_DIR
    || '.runtime/agent-runs/FE-CONSUMPTION-CLOSEOUT-20261126/local-clean-finance-data-permission',
);
const CAPABILITY_LABEL = 'SC 能力 - 数据中心只读';

if (!PASSWORD) throw new Error('ACCEPTANCE_PASSWORD is required');
fs.mkdirSync(OUTPUT_DIR, { recursive: true });

const report = {
  schema: 'local_clean.finance_data_permission.v1',
  pass: false,
  generated_at: new Date().toISOString(),
  runtime: {
    base: BASE,
    administrator: LOGIN,
    target_login: TARGET_LOGIN,
    source_revision: TARGET_SHA,
    frontend_build_sha256: BUILD_SHA256,
  },
  capability_label: CAPABILITY_LABEL,
  requests: [],
  assertions: [],
  screenshots: [],
  console_errors: [],
  failed_requests: [],
};

function check(condition, assertion, facts = {}) {
  report.assertions.push({ assertion, pass: Boolean(condition), ...facts });
  if (!condition) throw new Error(`${assertion}: ${JSON.stringify(facts)}`);
}

function requestOf(response) {
  try {
    return JSON.parse(response.request().postData() || '{}');
  } catch {
    return {};
  }
}

async function shot(page, name) {
  const file = path.join(OUTPUT_DIR, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  report.screenshots.push({ name, file, url: page.url() });
}

async function selectTag(page, input, optionLabel) {
  await input.waitFor({ state: 'visible', timeout: 15000 });
  await input.click();
  const popupId = String(
    await input.getAttribute('aria-controls')
      || await input.getAttribute('aria-owns')
      || '',
  ).trim();
  const popup = popupId
    ? page.locator(`[id="${popupId}"]`).last()
    : page.locator('.t-popup:visible').filter({ has: page.locator('.t-select-option') }).last();
  await popup.waitFor({ state: 'visible', timeout: 15000 });
  const option = popup.locator('.t-select-option').filter({ hasText: optionLabel }).last();
  await option.waitFor({ state: 'visible', timeout: 15000 });
  check(
    String(await option.innerText()).replace(/\s+/g, ' ').trim() === optionLabel,
    'data-read capability option label matches',
    { expected: optionLabel, actual: await option.innerText() },
  );
  await option.click();
  await page.waitForTimeout(250);
}

const browser = await launchChromium({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 960 },
  locale: 'zh-CN',
});
const page = await context.newPage();
const navigation = captureReleasedNavigation(page);
page.setDefaultTimeout(30000);
page.on('pageerror', (error) => report.console_errors.push(`pageerror: ${error.message}`));
page.on('console', (message) => {
  if (message.type() === 'error' && !/favicon|ResizeObserver/i.test(message.text())) {
    report.console_errors.push(`console.error: ${message.text()}`.slice(0, 500));
  }
});
page.on('request', (request) => {
  const envelope = request.postDataJSON?.();
  if (!envelope || String(envelope.params?.model || '') !== 'res.users') return;
  report.requests.push({ intent: envelope.intent, params: envelope.params || {} });
});
page.on('response', (response) => {
  if (response.status() < 400) return;
  const request = requestOf(response);
  report.failed_requests.push({
    status: response.status(),
    intent: request.intent || '',
    model: request.params?.model || '',
  });
});

try {
  await page.goto(matrixLoginUrl(BASE), { waitUntil: 'networkidle' });
  await fillLoginCredentials(page, LOGIN, PASSWORD);
  await page.getByRole('button', { name: /^登录$/ }).click();
  const loginDeadline = Date.now() + 45000;
  while (new URL(page.url()).pathname.includes('/login') && Date.now() < loginDeadline) {
    await page.waitForTimeout(250);
  }
  check(!new URL(page.url()).pathname.includes('/login'), 'business configuration administrator logs in', {
    url: page.url(),
  });

  const dataPermissionTarget = await navigation.targetByMenuXmlid(
    'smart_construction_core.menu_sc_product_data_permission_v1',
    '',
    60000,
  );
  report.runtime.data_permission_target = dataPermissionTarget;
  await page.goto(
    `${BASE}/a/${dataPermissionTarget.action_id}?menu_id=${dataPermissionTarget.menu_id}`,
    { waitUntil: 'networkidle' },
  );
  await page.locator('[data-product-page-mode="list"]').first()
    .waitFor({ state: 'visible', timeout: 45000 });
  const search = page.locator('input[placeholder*="搜索"]:visible').first();
  await search.waitFor({ state: 'visible', timeout: 15000 });
  await search.fill(TARGET_LOGIN);
  await page.getByRole('button', { name: /^搜索$/ }).first().click();
  await page.waitForTimeout(800);

  const target = page.getByRole('button', { name: '验收财务经办', exact: true }).first();
  await target.waitFor({ state: 'visible', timeout: 20000 });
  await target.click();
  await page.waitForURL((url) => /\/r\/res\.users\/\d+/.test(url.pathname), {
    waitUntil: 'domcontentloaded',
    timeout: 45000,
  });
  const form = page.locator('[data-product-page-mode="form"][data-form-model="res.users"]').first();
  await form.waitFor({ state: 'visible', timeout: 45000 });
  const permissionInput = form.locator(
    '[data-field-name="sc_user_permission_group_ids"] input:visible',
  ).first();
  await permissionInput.waitFor({ state: 'visible', timeout: 20000 });
  await selectTag(page, permissionInput, CAPABILITY_LABEL);
  check(
    String(await form.innerText()).includes(CAPABILITY_LABEL),
    'data-read capability is visible on the user permission form',
  );
  await shot(page, '01-finance-data-read-selected');

  const saveResponsePromise = page.waitForResponse((response) => {
    const request = requestOf(response);
    return request.intent === 'api.data'
      && request.params?.op === 'write'
      && request.params?.model === 'res.users';
  }, { timeout: 45000 });
  const save = form.locator(
    '[data-action-executor="record.save"]:visible, [data-form-draft-save="save-draft"]:visible',
  ).first();
  await save.waitFor({ state: 'visible', timeout: 15000 });
  await save.click();
  const dialog = page.getByRole('dialog').last();
  if (await dialog.waitFor({ state: 'visible', timeout: 2000 }).then(() => true).catch(() => false)) {
    const confirm = dialog.getByRole('button', { name: /^确认/ }).last();
    await confirm.waitFor({ state: 'visible', timeout: 10000 });
    await confirm.click();
  }
  const saveResponse = await saveResponsePromise;
  const body = await saveResponse.json().catch(() => ({}));
  check(saveResponse.status() === 200 && body?.ok === true,
    'data permission adjustment saves through the product surface', {
      status: saveResponse.status(),
      body,
    });
  await page.waitForTimeout(700);
  check(
    String(await form.innerText()).includes(CAPABILITY_LABEL),
    'saved form retains the data-read capability',
  );
  await shot(page, '02-finance-data-read-saved');
  check(report.console_errors.length === 0, 'data permission journey has no browser errors', {
    errors: report.console_errors,
  });
  check(report.failed_requests.length === 0, 'data permission journey has no failed HTTP responses', {
    failed_requests: report.failed_requests,
  });
  report.pass = true;
} catch (error) {
  report.error = {
    type: error instanceof Error ? error.name : typeof error,
    message: error instanceof Error ? error.message : String(error),
    url: page.url(),
    body_excerpt: String(await page.locator('#main-content').innerText().catch(() => '')).slice(0, 3000),
  };
  await shot(page, 'failure').catch(() => {});
} finally {
  const output = path.join(OUTPUT_DIR, 'receipt.json');
  fs.writeFileSync(output, `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({
    pass: report.pass,
    output,
    error: report.error || null,
    requests: report.requests,
    assertions: report.assertions,
    console_errors: report.console_errors,
    failed_requests: report.failed_requests,
  }, null, 2));
  await context.close();
  await browser.close();
  if (!report.pass) process.exitCode = 1;
}
