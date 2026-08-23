import { launchChromium } from './playwright_runtime.mjs';

const target = JSON.parse(process.env.LOCAL_DEV_PROJECT_CREATE_SCOPE_JSON || '{}');
const frontendUrl = String(process.env.FRONTEND_URL || '');
const password = String(process.env.E2E_PASSWORD || '');
const database = String(target.database || '');
const login = String(target.login || '');
if (!frontendUrl || !password || !database || !login || !target.action_id || !target.menu_id) {
  throw new Error('local.dev project driver probe identity is incomplete');
}

const browser = await launchChromium({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
const mutations = [];
const executeRequests = [];
const contractActions = [];
const browserErrors = [];
page.on('console', (message) => {
  if (message.type() === 'error') browserErrors.push(`console:${message.text()}`);
});
page.on('pageerror', (error) => browserErrors.push(`pageerror:${error.message}`));
page.on('request', (request) => {
  if (request.method() !== 'POST') return;
  let payload = {};
  try { payload = JSON.parse(request.postData() || '{}'); } catch {}
  const intent = String(payload.intent || '');
  const op = String(payload?.params?.op || payload.op || '');
  if (intent === 'execute_button') executeRequests.push({
    model: payload?.params?.model,
    recordId: payload?.params?.res_id,
    button: payload?.params?.button,
  });
  if (['create', 'write', 'unlink'].includes(op)) mutations.push({ intent, op });
});
page.on('response', async (response) => {
  if (!response.url().includes('/api/v1/intent')) return;
  let request = {};
  try { request = JSON.parse(response.request().postData() || '{}'); } catch {}
  if (String(request.intent || '') !== 'ui.contract.v2') return;
  let body = {};
  try { body = await response.json(); } catch {}
  const data = body?.data && typeof body.data === 'object' ? body.data : {};
  const rules = Array.isArray(data?.actionContract?.actionRuleList)
    ? data.actionContract.actionRuleList
    : [];
  const statuses = Array.isArray(data?.statusContract?.buttonStatus)
    ? data.statusContract.buttonStatus
    : [];
  contractActions.push(...rules.filter((row) => {
    const source = String(row?.sourceWidgetId || '');
    return String(row?.sourceChannel || '') === 'bound_model_action'
      || source.startsWith('mode.')
      || String(row?.actionId || '') === 'action.payment_submit'
      || String(row?.backendIdentity || '').includes('action_submit');
  }).map((row) => ({
    actionId: row.actionId,
    actionKey: row.actionKey,
    backendIdentity: row.backendIdentity,
    sourceChannel: row.sourceChannel,
    sourceWidgetId: row.sourceWidgetId,
    targetScope: row.targetScope,
    visibleProfiles: row.visibleProfiles,
    allowed: row.allowed,
    enabled: row.enabled,
    disabled: row.disabled,
    entitlementEvaluated: row.entitlementEvaluated,
    triggerType: row.triggerType,
    button: row.button,
    target: row.target,
    visible: row.visible,
    invisible: row.invisible,
    modifiers: row.modifiers,
    status: statuses.filter((status) => (
      String(status?.backendIdentity || '') === String(row?.backendIdentity || '')
    )).map((status) => ({
      btnId: status.btnId,
      backendIdentity: status.backendIdentity,
      visible: status.visible,
      disabled: status.disabled,
      reasonCode: status.reasonCode,
    })),
  })));
});

try {
  await page.goto(`${frontendUrl}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.locator('#login-username').fill(login);
  await page.locator('#login-password').fill(password);
  const databaseInput = page.getByLabel('数据库');
  if (await databaseInput.isEnabled()) await databaseInput.fill(database);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 30000 });
  const route = `${frontendUrl}/f/project.project/new?menu_id=${target.menu_id}&action_id=${target.action_id}`;
  await page.goto(route, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const surface = page.locator(
    `[data-product-page-mode="form"][data-form-model="project.project"][data-form-record="new"]`
    + `[data-form-action-id="${target.action_id}"][data-form-menu-id="${target.menu_id}"]`,
  );
  await surface.waitFor({ state: 'visible', timeout: 45000 });
  await page.waitForFunction(() => (
    document.querySelectorAll('[data-contract-form-driver]').length
    + document.querySelectorAll('[data-contract-form-driver-error]').length === 1
  ), undefined, { timeout: 45000 });
  const drivers = await surface.locator('[data-contract-form-driver]').count();
  const errors = await surface.locator('[data-contract-form-driver-error]').allTextContents();
  if (drivers !== 1 || errors.length !== 0) {
    throw new Error(`project create canonical driver did not load: ${JSON.stringify({ drivers, errors, contractActions })}`);
  }
  if (contractActions.some((row) => String(row.actionId || '').includes('project_share')
    || String(row.actionId || '').includes('send_mail')
    || String(row.actionId || '').includes('sms_composer'))) {
    throw new Error(`project create contract exposed record-bound action: ${JSON.stringify(contractActions)}`);
  }
  if (contractActions.some((row) => String(row.sourceWidgetId || '').startsWith('mode.')
    && String(row.targetScope || '') !== 'runtime')) {
    throw new Error(`mode-local action escaped runtime scope: ${JSON.stringify(contractActions)}`);
  }
  const projectResult = {
    url: page.url(),
    drivers,
    errors,
    contractActions: [...contractActions],
  };

  contractActions.length = 0;
  const paymentRoute = `${frontendUrl}/f/payment.request/${target.payment_record_id}`
    + `?menu_id=${target.payment_menu_id}&action_id=${target.payment_action_id}`;
  await page.goto(paymentRoute, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const paymentSurface = page.locator(
    `[data-product-page-mode="form"][data-form-model="payment.request"]`
    + `[data-form-record="${target.payment_record_id}"]`
    + `[data-form-action-id="${target.payment_action_id}"][data-form-menu-id="${target.payment_menu_id}"]`,
  );
  await paymentSurface.waitFor({ state: 'visible', timeout: 45000 });
  await page.waitForFunction(() => (
    document.querySelectorAll('[data-contract-form-driver]').length
    + document.querySelectorAll('[data-contract-form-driver-error]').length === 1
  ), undefined, { timeout: 45000 });
  const paymentDrivers = await paymentSurface.locator('[data-contract-form-driver]').count();
  const paymentErrors = await paymentSurface.locator('[data-contract-form-driver-error]').allTextContents();
  const paymentResult = {
    url: page.url(),
    drivers: paymentDrivers,
    errors: paymentErrors,
    contractActions: [...contractActions],
  };
  console.log('LOCAL_DEV_CONTRACT_DRIVER_JSON=' + JSON.stringify({
    project: projectResult,
    payment: paymentResult,
    mutations,
    executeRequests,
    browserErrors,
  }));
  if (paymentDrivers !== 1 || paymentErrors.length !== 0) {
    throw new Error(`payment record canonical driver did not load: ${JSON.stringify(paymentResult)}`);
  }
  if (mutations.length) throw new Error('read-only project create driver probe observed mutation');
  if (executeRequests.length) throw new Error(`read-only browser driver probe observed execute request: ${executeRequests.length}`);
  if (browserErrors.length) throw new Error(`browser errors observed: ${JSON.stringify(browserErrors)}`);
} catch (error) {
  const diagnostics = {
    url: page.url(),
    surfaces: await page.locator('[data-product-page-mode], [data-contract-form-driver-error]').evaluateAll((nodes) => (
      nodes.map((node) => ({
        tag: node.tagName,
        text: (node.textContent || '').trim().slice(0, 300),
        attributes: Object.fromEntries([...node.attributes].map((attribute) => [attribute.name, attribute.value])),
      }))
    )).catch(() => []),
    browserErrors,
    executeRequests,
    mutations,
  };
  console.error('LOCAL_DEV_CONTRACT_DRIVER_FAILURE=' + JSON.stringify(diagnostics));
  throw error;
} finally {
  await browser.close();
}
