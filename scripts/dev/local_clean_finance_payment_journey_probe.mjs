// P4 acceptance probe for one complete finance payment-request journey on the
// disposable local.clean runtime. It uses the released menu, real relation
// controls, the actual save/submit actions and authoritative API readback.
import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from '../verify/playwright_runtime.mjs';
import { matrixLoginUrl } from '../verify/business_entry_matrix_model.mjs';
import { captureReleasedNavigation } from '../verify/released_navigation_target.mjs';
import { fillLoginCredentials } from '../verify/frontend_authenticated_intent.mjs';

const BASE = String(
  process.env.SC_ACCEPTANCE_FRONTEND_URL || 'http://127.0.0.1:18083/t/clean',
).replace(/\/$/, '');
const DATABASE = String(process.env.SC_ACCEPTANCE_DATABASE || 'sc_clean');
const LOGIN = String(process.env.ACCEPTANCE_LOGIN || 'fixture_role_finance');
const PASSWORD = String(process.env.ACCEPTANCE_PASSWORD || '');
const TARGET_SHA = String(process.env.SC_ACCEPTANCE_TARGET_SHA || '');
const BUILD_SHA256 = String(process.env.SC_ACCEPTANCE_BUILD_SHA256 || '');
const OUTPUT_DIR = path.resolve(
  process.env.SC_ACCEPTANCE_OUTPUT_DIR
    || '.runtime/agent-runs/FE-CONSUMPTION-CLOSEOUT-20261126/local-clean-finance-payment-journey',
);
const FIXTURE_PATH = path.resolve(
  process.env.SC_ACCEPTANCE_FINANCE_FIXTURE
    || '.runtime/agent-runs/FE-CONSUMPTION-CLOSEOUT-20261126/local-clean-finance-e2e/finance-fixture.json',
);
const AMOUNT = 123.45;
const NOTE = 'local.clean 付款申请典型办理闭环';
let fixture;
try {
  fixture = JSON.parse(fs.readFileSync(FIXTURE_PATH, 'utf8'));
} catch (error) {
  throw new Error(`finance fixture receipt is required: ${FIXTURE_PATH}: ${error.message}`);
}
const COMPANY_ID = Number(process.env.SC_ACCEPTANCE_COMPANY_ID || fixture.company?.id || 0);
const PROJECT = {
  id: Number(fixture.project?.id || 0),
  model: 'project.project',
  label: String(fixture.project?.display_name || fixture.project?.name || '').trim(),
};
const PARTNER = {
  id: Number(fixture.partner?.id || 0),
  model: 'res.partner',
  label: String(fixture.partner?.display_name || fixture.partner?.name || '').trim(),
};
const CATEGORY = {
  id: Number(fixture.business_category?.id || 0),
  model: 'sc.business.category',
  label: String(
    fixture.business_category?.display_name || fixture.business_category?.name || '',
  ).trim(),
};
const CONTRACT = {
  id: Number(fixture.payment_basis?.contract_id || 0),
  model: 'construction.contract',
  label: String(fixture.payment_basis?.contract_name || '').trim(),
};
const SETTLEMENT = {
  id: Number(fixture.payment_basis?.settlement_id || 0),
  model: 'sc.settlement.order',
  label: String(fixture.payment_basis?.settlement_name || '').trim(),
};

if (!PASSWORD) throw new Error('ACCEPTANCE_PASSWORD is required');
fs.mkdirSync(OUTPUT_DIR, { recursive: true });

const report = {
  schema: 'local_clean.finance_payment_journey.v1',
  pass: false,
  generated_at: new Date().toISOString(),
  runtime: {
    base: BASE,
    database: DATABASE,
    login: LOGIN,
    source_revision: TARGET_SHA,
    frontend_build_sha256: BUILD_SHA256,
  },
  navigation: null,
  form_contract: null,
  interactions: [],
  requests: [],
  mutation_requests: [],
  readback: {},
  screenshots: [],
  console_errors: [],
  failed_requests: [],
  assertions: [],
};

function check(condition, assertion, facts = {}) {
  report.assertions.push({ assertion, pass: Boolean(condition), ...facts });
  if (!condition) throw new Error(`${assertion}: ${JSON.stringify(facts)}`);
}

for (const [name, target] of Object.entries({
  company: { id: COMPANY_ID },
  project: PROJECT,
  partner: PARTNER,
  business_category: CATEGORY,
  contract: CONTRACT,
  settlement: SETTLEMENT,
})) {
  check(Number(target.id) > 0 && Boolean(target.label || name === 'company'),
    `finance fixture exposes an exact ${name} identity`, { target });
}

function envelopeData(body) {
  return body?.data || body?.result?.data || body?.result || {};
}

function intentOf(response) {
  if (!response.url().includes('/api/v1/intent')) return '';
  try {
    return String(JSON.parse(response.request().postData() || '{}')?.intent || '');
  } catch {
    return '';
  }
}

function requestOf(response) {
  try {
    return JSON.parse(response.request().postData() || '{}');
  } catch {
    return {};
  }
}

function relationLabel(record) {
  return String(record?.display_name || record?.name || '').trim();
}

function findPaymentNavigationTarget(nav) {
  const pending = Array.isArray(nav) ? [...nav] : [];
  while (pending.length) {
    const node = pending.shift();
    if (!node || typeof node !== 'object') continue;
    const model = String(node?.entry_target?.compatibility_refs?.model || '').trim();
    const actionId = Number(node.action_id || 0);
    const menuId = Number(node.menu_id || 0);
    if (model === 'payment.request' && actionId > 0 && menuId > 0) {
      return {
        action_id: actionId,
        menu_id: menuId,
        route: String(node.route || '').trim(),
        scene_key: String(node.scene_key || '').trim(),
        entry_target: node.entry_target || {},
      };
    }
    if (Array.isArray(node.children)) pending.push(...node.children);
  }
  return null;
}

async function waitForPaymentNavigationTarget(released, timeoutMs = 60000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const target = findPaymentNavigationTarget(released.nav());
    if (target) return target;
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error('released navigation has no payment.request action target');
}

async function shot(page, name) {
  const file = path.join(OUTPUT_DIR, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  report.screenshots.push({ name, file, url: page.url() });
}

async function apiEnvelope(page, envelope) {
  const token = await page.evaluate(() => {
    const entryBase = (
      window.location.pathname.match(/^\/(?:t\/[a-z0-9][a-z0-9-]*|platform-admin)/) || ['']
    )[0];
    const audience = entryBase === '/platform-admin'
      ? 'platform-admin'
      : (entryBase ? 'tenant' : 'unscoped');
    return sessionStorage.getItem(`sc_auth_token:${audience}:${entryBase || 'root'}`) || '';
  });
  return page.evaluate(async ({ tokenValue, envelopeValue }) => {
    const entryBase = (
      window.location.pathname.match(/^\/(?:t\/[a-z0-9][a-z0-9-]*|platform-admin)/) || ['']
    )[0];
    const response = await fetch(`${entryBase}/api/v1/intent`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: tokenValue ? `Bearer ${tokenValue}` : '',
        'X-Trace-Id': `clean-payment-journey-${Date.now()}`,
      },
      body: JSON.stringify(envelopeValue),
    });
    return {
      status: response.status,
      body: await response.json().catch(() => ({})),
    };
  }, { tokenValue: token, envelopeValue: envelope });
}

async function readPayment(page, id) {
  const response = await apiEnvelope(page, {
    intent: 'api.data',
    params: {
      op: 'list',
      model: 'payment.request',
      fields: [
        'id',
        'name',
        'state',
        'validation_status',
        'project_id',
        'partner_id',
        'business_category_id',
        'date_request',
        'amount',
        'currency_id',
        'contract_id',
        'settlement_id',
        'note',
        'attachment_ids',
        'review_ids',
      ],
      domain: [['id', '=', id]],
      limit: 1,
      context: { allowed_company_ids: [COMPANY_ID] },
    },
  });
  const records = envelopeData(response.body)?.records || [];
  check(response.status === 200 && records.length === 1, 'payment request is authoritatively readable', {
    id,
    status: response.status,
    records,
  });
  return records[0];
}

async function waitForForm(page, id = 'new') {
  const selector = id === 'new'
    ? '[data-product-page-mode="form"][data-form-model="payment.request"][data-form-record="new"]'
    : `[data-product-page-mode="form"][data-form-model="payment.request"][data-form-record="${id}"]`;
  await page.locator(`${selector}:visible`).waitFor({ timeout: 45000 });
  await page.waitForFunction(
    () => !/正在加载页面|正在加载记录|正在载入数据/.test(document.body?.innerText || ''),
    null,
    { timeout: 45000 },
  );
  await page.waitForTimeout(500);
}

async function waitForPath(page, matcher, timeout = 45000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    if (matcher(new URL(page.url()).pathname)) return;
    await page.waitForTimeout(100);
  }
  throw new Error(`route did not reach expected identity: ${page.url()}`);
}

async function fillRelation(page, target) {
  const field = page.locator(`[data-field-name="${target.field}"]:visible`).first();
  await field.scrollIntoViewIfNeeded();
  const input = field.locator('input:visible').first();
  await input.waitFor({ state: 'visible', timeout: 15000 });
  await input.click();

  const fieldType = String(await field.getAttribute('data-field-type') || '').toLowerCase();
  if (fieldType === 'selection') {
    const option = page.getByRole('option', { name: target.label, exact: true }).last();
    await option.waitFor({ state: 'visible', timeout: 15000 });
    await option.click();
  } else {
    check(fieldType === 'many2one', `${target.field} uses a declared many2one control`, {
      fieldType,
    });
    const responsePromise = page.waitForResponse((response) => {
      if (intentOf(response) !== 'api.data') return false;
      const request = requestOf(response);
      return String(request?.params?.op || '') === 'list'
        && String(request?.params?.model || '') === target.model
        && String(request?.params?.search_term || '') === target.label;
    }, { timeout: 30000 });
    await input.fill(target.label);
    const response = await responsePromise;
    const body = await response.json().catch(() => ({}));
    const recordsCarrier = [];
    const visit = (value) => {
      if (Array.isArray(value)) {
        value.forEach(visit);
        return;
      }
      if (!value || typeof value !== 'object') return;
      if (Array.isArray(value.records)) recordsCarrier.push(value.records);
      Object.values(value).forEach(visit);
    };
    visit(body);
    const matches = recordsCarrier.flat().filter((record) => relationLabel(record) === target.label);
    check(response.status() === 200, `${target.field} relation query succeeds`, {
      target,
      status: response.status(),
      matches: matches.map((record) => ({ id: record.id, label: relationLabel(record) })),
    });

    const optionPanel = page.locator('.many2one-option-panel:visible').last();
    const exactOption = optionPanel.locator(
      `[data-relation-option-value="${target.id}"]`,
    );
    if (await exactOption.count()) {
      await exactOption.waitFor({ state: 'visible', timeout: 15000 });
      check(
        String(await exactOption.innerText()).replace(/\s+/g, ' ').trim() === target.label,
        `${target.field} filtered option label matches the expected relation`,
        { expected: target.label, actual: await exactOption.innerText() },
      );
      await exactOption.click();
    } else {
      check(matches.length === 1, `${target.field} relation response is unique`, {
        target,
        matches: matches.map((record) => ({ id: record.id, label: relationLabel(record) })),
      });
      check(Number(matches[0].id) === target.id, `${target.field} relation id matches the fixture`, {
        expected: target.id,
        actual: matches[0].id,
      });
      const selectedValue = String(await input.inputValue().catch(() => '')).trim();
      check(
        selectedValue === target.label && !await optionPanel.count(),
        `${target.field} relation is either explicitly selected or uniquely auto-selected`,
        { selectedValue, optionPanelCount: await optionPanel.count() },
      );
    }
    await page.waitForFunction(({ fieldName, label }) => {
      const candidates = [
        ...document.querySelectorAll(
          `[data-product-page-mode="form"] [data-field-name="${fieldName}"] input`,
        ),
      ].filter((node) => node instanceof HTMLInputElement && node.offsetParent !== null);
      return candidates.some((node) => node.value === label);
    }, { fieldName: target.field, label: target.label }, { timeout: 30000 });
  }

  report.interactions.push({
    action: 'select-relation',
    field: target.field,
    model: target.model,
    id: target.id,
    label: target.label,
    field_type: fieldType,
    control_value: String(await page
      .locator(`[data-field-name="${target.field}"] input:visible`)
      .first()
      .inputValue()),
  });
  await page.waitForTimeout(700);
}

async function clickAndConfirm(page, button, responseMatcher, label) {
  const responsePromise = page.waitForResponse(responseMatcher, { timeout: 45000 });
  await button.click();
  const dialog = page.getByRole('dialog').last();
  if (await dialog.waitFor({ state: 'visible', timeout: 2500 }).then(() => true).catch(() => false)) {
    const confirm = dialog.getByRole('button', { name: /^确认/ }).last();
    await confirm.waitFor({ state: 'visible', timeout: 10000 });
    await confirm.click();
  }
  const response = await responsePromise;
  const body = await response.json().catch(() => ({}));
  report.requests.push({
    label,
    status: response.status(),
    intent: intentOf(response),
    params: requestOf(response)?.params || {},
    ok: body?.ok,
    error: body?.error || null,
  });
  return { response, body };
}

const browser = await launchChromium({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 960 },
  locale: 'zh-CN',
});
const page = await context.newPage();
page.setDefaultTimeout(30000);
page.on('pageerror', (error) => report.console_errors.push(`pageerror: ${error.message}`));
page.on('console', (message) => {
  if (message.type() === 'error' && !/favicon|ResizeObserver/i.test(message.text())) {
    report.console_errors.push(`console.error: ${message.text()}`.slice(0, 500));
  }
});
page.on('request', (request) => {
  const envelope = request.postDataJSON?.();
  if (!envelope || !['api.onchange', 'api.data'].includes(String(envelope.intent || ''))) return;
  report.mutation_requests.push({
    intent: envelope.intent,
    op: envelope.params?.op || '',
    model: envelope.params?.model || '',
    vals: envelope.params?.vals || null,
    fields: Array.isArray(envelope.params?.fields) ? envelope.params.fields : null,
    search_term: envelope.params?.search_term || null,
  });
  if (report.mutation_requests.length > 100) report.mutation_requests.shift();
});
page.on('response', async (response) => {
  const request = requestOf(response);
  if (response.status() >= 400) {
    report.failed_requests.push({
      status: response.status(),
      intent: request.intent || '',
      model: request.params?.model || '',
      op: request.params?.op || '',
      url: response.url(),
    });
  }
  if (response.status() !== 200 || request.intent !== 'ui.contract.v2') return;
  try {
    const data = envelopeData(await response.json());
    if (
      String(data?.pageInfo?.model || request?.params?.model || '') === 'payment.request'
      && String(data?.pageInfo?.viewType || request?.params?.view_type || '') === 'form'
    ) {
      report.form_contract = {
        request_params: request.params,
        page_info: data.pageInfo,
        data_contract: data.dataContract,
        workflow_contract: data.workflowContract,
        action_rules: data.actionContract?.actionRuleList || [],
        status_contract: data.statusContract,
        form_structure: data.formStructureContract,
        field_ownership: data.fieldOwnership,
      };
    }
  } catch {
    // The UI exposes malformed contracts as a fail-closed state.
  }
});

let createdId = 0;
try {
  const navigation = captureReleasedNavigation(page);
  await page.goto(matrixLoginUrl(BASE), { waitUntil: 'networkidle' });
  await fillLoginCredentials(page, LOGIN, PASSWORD);
  await page.getByRole('button', { name: /^登录$/ }).click();
  const loginDeadline = Date.now() + 45000;
  while (new URL(page.url()).pathname.includes('/login') && Date.now() < loginDeadline) {
    await page.waitForTimeout(250);
  }
  check(!new URL(page.url()).pathname.includes('/login'), 'finance user logs in', {
    url: page.url(),
    body: (await page.locator('body').innerText()).slice(0, 500),
  });

  const target = await waitForPaymentNavigationTarget(navigation);
  report.navigation = target;
  const baseUrl = `${BASE}/a/${target.action_id}?menu_id=${target.menu_id}`;

  await page.goto(baseUrl, { waitUntil: 'networkidle' });
  await page.locator('[data-product-page-mode="list"]:visible').first().waitFor({ timeout: 45000 });
  await shot(page, '01-payment-list');

  const createButton = page.getByRole('button', { name: /^新建(?:付款申请)?$/ }).first();
  await createButton.waitFor({ state: 'visible', timeout: 15000 });
  await createButton.click();
  await page.waitForURL((url) => url.pathname.includes('/f/payment.request/new'), {
    timeout: 45000,
  });
  await waitForForm(page);
  check(
    !/契约缺口|ContractGapError|页面渲染失败/.test(await page.locator('body').innerText()),
    'payment create form has no contract gap',
  );
  await shot(page, '02-payment-new');

  await fillRelation(page, { field: 'business_category_id', ...CATEGORY });
  await fillRelation(page, { field: 'project_id', ...PROJECT });
  await fillRelation(page, { field: 'partner_id', ...PARTNER });
  await fillRelation(page, { field: 'contract_id', ...CONTRACT });
  await fillRelation(page, { field: 'settlement_id', ...SETTLEMENT });
  await page.keyboard.press('Escape').catch(() => {});

  const dateInput = page.locator('[data-field-name="date_request"] input:visible').first();
  const dateValue = String(await dateInput.inputValue()).trim();
  check(dateValue === '2026-11-28', 'date_request uses the declared business default', {
    actual: dateValue,
  });
  check(await dateInput.isEditable() === false, 'date_request remains readonly after business defaults', {
    editable: await dateInput.isEditable(),
  });
  const amountInput = page.locator('[data-field-name="amount"] input:visible').first();
  check(await amountInput.getAttribute('step') === 'any', 'money input does not invent currency precision');
  await amountInput.fill(String(AMOUNT));
  const noteInput = page
    .locator('[data-field-name="note"] textarea:visible, [data-field-name="note"] input:visible')
    .first();
  await noteInput.fill(NOTE);
  report.interactions.push({
    action: 'fill',
    fields: {
      date_request: dateValue,
      amount: AMOUNT,
      note: NOTE,
    },
  });

  const attachmentInput = page
    .locator('[data-collaboration-capability="attachments"] input[type="file"]')
    .first();
  await attachmentInput.waitFor({ state: 'attached', timeout: 15000 });
  await attachmentInput.setInputFiles({
    name: 'local-clean-payment-evidence.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('local.clean payment request acceptance evidence\n', 'utf8'),
  });
  report.interactions.push({
    action: 'attach',
    name: 'local-clean-payment-evidence.txt',
  });
  for (const [field, expected] of [
    ['project_id', PROJECT.label],
    ['partner_id', PARTNER.label],
    ['business_category_id', CATEGORY.label],
    ['contract_id', CONTRACT.label],
    ['settlement_id', SETTLEMENT.label],
  ]) {
    const actual = String(await page
      .locator(`[data-field-name="${field}"] input:visible`)
      .first()
      .inputValue()).trim();
    check(actual === expected, `${field} remains selected after all dependent inputs`, {
      expected,
      actual,
    });
  }
  const preSaveBody = String(
    await page.locator('[data-product-page-mode="form"]:visible').first().innerText(),
  );
  check(!preSaveBody.includes('项目不能为空'), 'project required-field error is absent before save');
  check(!preSaveBody.includes('往来单位不能为空'), 'partner required-field error is absent before save');
  await shot(page, '03-payment-filled');

  const save = page.locator(
    '[data-action-executor="record.save"]:visible, [data-form-draft-save="save-draft"]:visible',
  ).first();
  await save.waitFor({ state: 'visible', timeout: 15000 });
  check(await save.isEnabled(), 'save draft action is enabled');
  const saved = await clickAndConfirm(
    page,
    save,
    (response) => {
      const request = requestOf(response);
      return request.intent === 'api.data'
        && request.params?.op === 'create'
        && request.params?.model === 'payment.request';
    },
    'save-draft',
  );
  check(saved.response.status() < 400, 'save draft succeeds', {
    status: saved.response.status(),
    body: saved.body,
  });
  await waitForPath(page, (pathname) => /\/f\/payment\.request\/\d+$/.test(pathname));
  createdId = Number(new URL(page.url()).pathname.split('/').pop() || 0);
  check(createdId > 0, 'saved payment request receives a record id', { url: page.url() });
  await waitForForm(page, createdId);
  await shot(page, '04-payment-saved');

  const afterSave = await readPayment(page, createdId);
  report.readback.after_save = afterSave;
  check(Number(afterSave.project_id?.[0] || afterSave.project_id) === PROJECT.id, 'saved project matches selection');
  check(Number(afterSave.partner_id?.[0] || afterSave.partner_id) === PARTNER.id, 'saved partner matches selection');
  check(
    Number(afterSave.business_category_id?.[0] || afterSave.business_category_id) === CATEGORY.id,
    'saved business category matches selection',
  );
  check(String(afterSave.date_request || '') === '2026-11-28', 'saved date matches input');
  check(Number(afterSave.amount || 0) === AMOUNT, 'saved amount matches input');
  check(String(afterSave.note || '') === NOTE, 'saved note matches input');
  check(Array.isArray(afterSave.attachment_ids) && afterSave.attachment_ids.length > 0, 'saved attachment is present');
  check(
    Number(afterSave.contract_id?.[0] || afterSave.contract_id) === CONTRACT.id,
    'saved contract matches selection',
  );
  check(
    Number(afterSave.settlement_id?.[0] || afterSave.settlement_id) === SETTLEMENT.id,
    'saved settlement matches selection',
  );
  check(String(afterSave.state || '') === 'draft', 'saved request remains a draft', {
    state: afterSave.state,
  });

  await page.goto(baseUrl, { waitUntil: 'networkidle' });
  await page.locator('table:visible').first().waitFor({ timeout: 45000 });
  const listText = String(await page.locator('#main-content').innerText());
  check(listText.includes(String(afterSave.name || '')), 'saved payment request appears in the product list', {
    name: afterSave.name,
  });
  await shot(page, '05-payment-list-readback');

  const openRecord = page.getByRole('button', { name: String(afterSave.name), exact: true }).first();
  await openRecord.waitFor({ state: 'visible', timeout: 15000 });
  await openRecord.click();
  await waitForPath(
    page,
    (pathname) => new RegExp(`/(?:f|r)/payment\\.request/${createdId}$`).test(pathname),
  );
  await waitForForm(page, createdId);
  await shot(page, '06-payment-reopened');

  const submit = page.getByRole('button', { name: /^提交审批$/ }).first();
  await submit.waitFor({ state: 'visible', timeout: 15000 });
  check(await submit.isEnabled(), 'submit action is enabled for the saved draft');
  const submitted = await clickAndConfirm(
    page,
    submit,
    (response) => {
      const request = requestOf(response);
      return ['execute_button', 'payment.request.submit'].includes(request.intent)
        && String(request.params?.model || '') === 'payment.request';
    },
    'submit-approval',
  );
  check(submitted.response.status() < 400, 'submit approval succeeds', {
    status: submitted.response.status(),
    body: submitted.body,
  });
  await page.waitForTimeout(2000);
  const afterSubmit = await readPayment(page, createdId);
  report.readback.after_submit = afterSubmit;
  check(
    ['submit', 'approved', 'done'].includes(String(afterSubmit.state || '')),
    'submit transitions the request out of draft',
    { state: afterSubmit.state, validation_status: afterSubmit.validation_status },
  );
  await shot(page, '07-payment-submitted');

  check(report.console_errors.length === 0, 'journey has no unexpected browser errors', {
    errors: report.console_errors,
  });
  check(report.failed_requests.length === 0, 'journey has no failed HTTP responses', {
    failed_requests: report.failed_requests,
  });
  report.pass = true;
} catch (error) {
  report.error = {
    type: error instanceof Error ? error.name : typeof error,
    message: error instanceof Error ? error.message : String(error),
    url: page.url(),
    body_excerpt: String(await page.locator('body').innerText().catch(() => '')).slice(0, 2000),
  };
} finally {
  const output = path.join(OUTPUT_DIR, 'receipt.json');
  fs.writeFileSync(output, `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({
    pass: report.pass,
    output,
    record_id: createdId,
    error: report.error || null,
    assertions: report.assertions,
    readback: report.readback,
    console_errors: report.console_errors,
    failed_requests: report.failed_requests,
  }, null, 2));
  await context.close();
  await browser.close();
  if (!report.pass) process.exitCode = 1;
}
