// P4 user-journey probe: define the payment-request approval chain through the
// business configuration surface, using only declared approval scopes.
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
const PASSWORD = String(process.env.ACCEPTANCE_PASSWORD || '');
const TARGET_SHA = String(process.env.SC_ACCEPTANCE_TARGET_SHA || '');
const BUILD_SHA256 = String(process.env.SC_ACCEPTANCE_BUILD_SHA256 || '');
const OUTPUT_DIR = path.resolve(
  process.env.SC_ACCEPTANCE_OUTPUT_DIR
    || '.runtime/agent-runs/FE-CONSUMPTION-CLOSEOUT-20261126/local-clean-finance-approval-configuration',
);
let configUrl = '';
const STEPS = [
  ['财务经办复核', '财务经办人'],
  ['项目负责人复核', '项目负责人'],
  ['财务复核', '财务审核人'],
  ['总经理终审', '管理层/总经理终审'],
];

if (!PASSWORD) throw new Error('ACCEPTANCE_PASSWORD is required');
fs.mkdirSync(OUTPUT_DIR, { recursive: true });

const report = {
  schema: 'local_clean.finance_approval_configuration.v1',
  pass: false,
  generated_at: new Date().toISOString(),
  runtime: {
    base: BASE,
    login: LOGIN,
    source_revision: TARGET_SHA,
    frontend_build_sha256: BUILD_SHA256,
    configuration_url: configUrl,
  },
  selected: {
    approval_required: true,
    mode: '多级顺序审核',
    default_scope: '财务审核人',
    steps: STEPS,
  },
  requests: [],
  responses: [],
  screenshots: [],
  assertions: [],
  console_errors: [],
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

async function selectOption(page, label, optionLabel) {
  let control = page.locator(`[aria-label="${label}"]`).first();
  if (!await control.count()) {
    const container = page.locator('.approval-config-grid label').filter({ hasText: label }).last();
    control = container.locator('input.t-input__inner').first();
  }
  await control.waitFor({ state: 'visible', timeout: 20000 });
  await control.click();
  const popupId = String(
    await control.getAttribute('aria-controls')
      || await control.getAttribute('aria-owns')
      || '',
  ).trim();
  const popup = popupId
    ? page.locator(`[id="${popupId}"]`).last()
    : page.locator('.t-popup:visible').filter({ has: page.locator('.t-select-option') }).last();
  await popup.waitFor({ state: 'visible', timeout: 10000 });
  const option = popup.locator('.t-select-option').filter({ hasText: optionLabel }).last();
  await option.waitFor({ state: 'visible', timeout: 10000 });
  check(
    String(await option.innerText()).replace(/\s+/g, ' ').trim() === optionLabel,
    `${label} option label matches`,
    { expected: optionLabel, actual: await option.innerText() },
  );
  await option.scrollIntoViewIfNeeded();
  await option.click();
  await page.waitForTimeout(250);
  check(
    String(await control.inputValue()).trim() === optionLabel,
    `${label} control displays the selected option`,
    { expected: optionLabel, actual: await control.inputValue() },
  );
}

const browser = await launchChromium({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
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
  if (!envelope || !String(envelope.intent || '').startsWith('sc.approval_policy.')) return;
  report.requests.push({
    intent: envelope.intent,
    params: envelope.params || {},
  });
});
page.on('response', async (response) => {
  const request = requestOf(response);
  if (!String(request.intent || '').startsWith('sc.approval_policy.')) return;
  const body = await response.json().catch(() => ({}));
  report.responses.push({
    intent: request.intent,
    status: response.status(),
    ok: body?.ok,
    error: body?.error || null,
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
  await navigation.ready();

  const businessConfigTarget = await navigation.targetByMenuXmlid(
    'smart_construction_core.menu_sc_business_config_workbench',
    '',
    60000,
  );
  configUrl = `${BASE}/admin/business-config?model=payment.request`
    + `&action_id=${businessConfigTarget.action_id}`
    + `&menu_id=${businessConfigTarget.menu_id}`;
  report.runtime.configuration_target = businessConfigTarget;
  report.runtime.configuration_url = configUrl;
  await page.goto(configUrl, { waitUntil: 'networkidle' });
  await page.locator('#main-content').waitFor({ state: 'visible', timeout: 45000 });
  await page.waitForFunction(
    () => !/正在加载|读取中/.test(document.querySelector('#main-content')?.textContent || ''),
    null,
    { timeout: 45000 },
  );
  report.available_buttons = await page.getByRole('button').evaluateAll((nodes) => nodes.map((node) => ({
    text: String(node.textContent || '').replace(/\s+/g, ' ').trim(),
    visible: node instanceof HTMLElement && node.offsetParent !== null,
  })).filter((row) => row.text));
  await shot(page, '01-business-configuration');

  const approvalCard = page.getByRole('button', { name: /^审批配置/ }).last();
  await approvalCard.waitFor({ state: 'visible', timeout: 20000 });
  await approvalCard.click();
  const panelHeading = page.getByRole('heading', { name: '审批规则', exact: true }).last();
  if (!await panelHeading.waitFor({ state: 'visible', timeout: 2000 }).then(() => true).catch(() => false)) {
    const configure = page.getByRole('button', { name: /^配置审批规则$/ }).first();
    await configure.waitFor({ state: 'visible', timeout: 20000 });
    await configure.click();
  }
  await panelHeading.waitFor({ state: 'visible', timeout: 30000 });
  await page.waitForFunction(
    () => !document.body.innerText.includes('金额条件能力尚未读取'),
    null,
    { timeout: 30000 },
  );
  report.approval_controls = await page.locator('.approval-panel').evaluate((panel) => (
    [...panel.querySelectorAll('input, button, [role], .t-select')].map((node) => ({
      tag: node.tagName,
      role: node.getAttribute('role'),
      aria_label: node.getAttribute('aria-label'),
      name: node.getAttribute('name'),
      type: node.getAttribute('type'),
      text: String(node.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 120),
      class_name: String(node.className || ''),
      visible: node instanceof HTMLElement && node.offsetParent !== null,
    }))
  ));
  await shot(page, '02-approval-rule-loaded');

  const enabled = page.getByRole('checkbox', { name: '启用审批', exact: true }).first();
  await enabled.waitFor({ state: 'visible', timeout: 15000 });
  if (!await enabled.isChecked()) await enabled.click();
  await selectOption(page, '审批方式', '多级顺序审核');
  await selectOption(page, '默认审批岗位', '财务审核人');

  const stepTable = page.getByRole('table', { name: '审批步骤', exact: true });
  await stepTable.waitFor({ state: 'visible', timeout: 15000 });
  let rows = stepTable.getByRole('row');
  while (await rows.count() < STEPS.length + 1) {
    await page.getByRole('button', { name: '添加步骤', exact: true }).click();
    rows = stepTable.getByRole('row');
  }

  for (let index = 0; index < STEPS.length; index += 1) {
    const [name, scope] = STEPS[index];
    const nameInput = page.getByRole('textbox', {
      name: `第${index + 1}步名称`,
      exact: true,
    });
    await nameInput.fill(name);
    await selectOption(page, `第${index + 1}步审批岗位`, scope);
  }
  await shot(page, '03-approval-steps-defined');

  const save = page.getByRole('button', { name: '保存审批设置', exact: true });
  check(await save.isEnabled(), 'approval configuration save is enabled');
  await save.click();
  const impactDialog = page.getByRole('dialog').filter({ hasText: '确认配置影响' }).last();
  await impactDialog.waitFor({ state: 'visible', timeout: 15000 });
  await impactDialog.getByRole('button', { name: '确认继续', exact: true }).click();
  await page.waitForFunction(
    () => /审批设置已保存/.test(document.body.innerText),
    null,
    { timeout: 45000 },
  );
  await shot(page, '04-approval-configuration-saved');

  const configSet = report.responses.filter((row) => row.intent === 'sc.approval_policy.config.set');
  const stepsSet = report.responses.filter((row) => row.intent === 'sc.approval_policy.steps.set');
  check(configSet.length === 1 && configSet[0].status === 200 && configSet[0].ok === true,
    'approval policy configuration persisted through the product API', { configSet });
  check(stepsSet.length === 1 && stepsSet[0].status === 200 && stepsSet[0].ok === true,
    'approval steps persisted through the product API', { stepsSet });

  const stepPayload = report.requests.find((row) => row.intent === 'sc.approval_policy.steps.set')?.params?.steps || [];
  check(Array.isArray(stepPayload) && stepPayload.length >= 4, 'saved payload contains the four business steps', {
    stepPayload,
  });
  for (const [index, [name, scope]] of STEPS.entries()) {
    check(
      String(stepPayload[index]?.name || '') === name
        && String(stepPayload[index]?.approval_scope_key || '') === ({
          财务经办人: 'finance_user',
          项目负责人: 'project_manager',
          财务审核人: 'finance_manager',
          '管理层/总经理终审': 'executive',
        })[scope],
      `saved step ${index + 1} matches the user-defined business role`,
      { expected: { name, scope }, actual: stepPayload[index] },
    );
  }
  check(report.console_errors.length === 0, 'approval configuration page has no browser errors', {
    errors: report.console_errors,
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
    responses: report.responses,
    assertions: report.assertions,
    console_errors: report.console_errors,
  }, null, 2));
  await context.close();
  await browser.close();
  if (!report.pass) process.exitCode = 1;
}
