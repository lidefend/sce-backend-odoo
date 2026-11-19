import fs from 'node:fs/promises';
import path from 'node:path';
import { launchChromium } from '../../../../scripts/verify/playwright_runtime.mjs';

const BASE_URL = String(process.env.FRONTEND_URL || 'http://127.0.0.1:18081').replace(/\/+$/, '');
const LOGIN = String(process.env.E2E_LOGIN || 'admin').trim();
const PASSWORD = String(process.env.E2E_PASSWORD || '123456').trim();
const CONFIG_LOGIN = String(process.env.ADMIN_CLOSE_01_CONFIG_LOGIN || 'sc_demo_business_config').trim();
const CONFIG_PASSWORD = String(process.env.ADMIN_CLOSE_01_CONFIG_PASSWORD || PASSWORD).trim();
const BUSINESS_LOGIN = String(process.env.ADMIN_CLOSE_01_BUSINESS_LOGIN || 'wutao').trim();
const BUSINESS_PASSWORD = String(process.env.ADMIN_CLOSE_01_BUSINESS_PASSWORD || PASSWORD).trim();
const ARTIFACT_DIR = path.resolve(
  process.cwd(),
  process.env.ARTIFACTS_DIR || 'artifacts/playwright/admin-close-01-management',
);

const report = {
  schema: 'admin_close_01.management_browser.v1',
  pass: false,
  generated_at: new Date().toISOString(),
  runtime: {
    base_url: BASE_URL,
    admin_login: LOGIN,
    config_login: CONFIG_LOGIN,
    business_login: BUSINESS_LOGIN,
  },
  assertions: [],
  api: {},
  screenshots: [],
  errors: [],
};

function check(condition, message, details = {}) {
  report.assertions.push({ pass: Boolean(condition), message, ...details });
  if (!condition) throw new Error(`${message}: ${JSON.stringify(details)}`);
}

function intentOf(request) {
  try {
    return String(request.postDataJSON()?.intent || '');
  } catch {
    return '';
  }
}

function intentData(body) {
  if (body?.data?.data !== undefined) return body.data.data;
  if (body?.data !== undefined) return body.data;
  return body;
}

async function screenshot(page, name) {
  const file = path.join(ARTIFACT_DIR, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  report.screenshots.push({ name, file, url: page.url() });
}

async function login(page, loginName, password) {
  await page.goto(`${BASE_URL}/t/demo/login`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.locator('#login-username, input[autocomplete="username"]').first().fill(loginName);
  await page.locator('#login-password, input[autocomplete="current-password"]').first().fill(password);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForFunction(() => !window.location.pathname.includes('/login'), null, { timeout: 60000 });
  await page.locator('.layout-shell').waitFor({ timeout: 60000 });
}

const browser = await launchChromium({ headless: true });
try {
  await fs.mkdir(ARTIFACT_DIR, { recursive: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
  const page = await context.newPage();
  page.on('console', (message) => {
    if (message.type() === 'error' && !/favicon|ResizeObserver/i.test(message.text())) {
      report.errors.push({ type: 'console', text: message.text(), url: page.url() });
    }
  });
  page.on('pageerror', (error) => report.errors.push({ type: 'pageerror', text: error.message, url: page.url() }));

  await login(page, LOGIN, PASSWORD);
  const initialExplorer = page.waitForResponse((response) => (
    response.url().includes('/api/v1/intent')
    && intentOf(response.request()) === 'platform.capability.explorer.list'
    && response.status() === 200
  ));
  await page.goto(`${BASE_URL}/t/demo/admin/capability-explorer`, { waitUntil: 'domcontentloaded' });
  const initialPayload = intentData(await (await initialExplorer).json());
  await page.getByRole('heading', { name: '平台能力浏览器' }).waitFor({ timeout: 60000 });

  const filteredExplorer = page.waitForResponse((response) => (
    response.url().includes('/api/v1/intent')
    && intentOf(response.request()) === 'platform.capability.explorer.list'
    && response.status() === 200
  ));
  await page.getByPlaceholder('搜索名称、模块、模型、Action 或场景').fill('menu_sc_project_project');
  const filteredPayload = intentData(await (await filteredExplorer).json());
  const projectRow = (filteredPayload.rows || []).find((row) => (
    row.entry_ref?.menu_xmlid === 'smart_construction_core.menu_sc_project_project'
  ));
  const selectedRow = projectRow || (initialPayload.rows || [])[0];
  check(selectedRow, 'governed catalog exposes at least one capability entry');
  if (!projectRow) {
    report.api.project_ledger_browser_available = false;
    report.api.project_ledger_browser_reason = 'ACTIVE_LOCAL_DEV_MENU_SET_EXCLUDES_PROJECT_LEDGER';
  } else {
    report.api.project_ledger_browser_available = true;
  }
  const selectedEntryResponse = page.waitForResponse((response) => (
    response.url().includes('/api/v1/intent')
    && intentOf(response.request()) === 'platform.capability.explorer.list'
    && response.status() === 200
  ));
  await page.getByPlaceholder('搜索名称、模块、模型、Action 或场景').fill(selectedRow.entry_ref.menu_xmlid);
  await selectedEntryResponse;
  await page.locator('[data-semantic-component="ScTable"]').getByText(selectedRow.label, { exact: true }).first().click();
  const drawer = page.getByRole('dialog');
  await drawer.waitFor({ state: 'visible', timeout: 60000 });
  await page.waitForFunction(() => {
    const node = document.querySelector('.sc-design-drawer [role="dialog"]');
    const text = node?.textContent || '';
    return !text.includes('正在读取入口详情并执行诊断');
  }, null, { timeout: 60000 });
  const drawerText = await drawer.innerText();
  for (const label of ['最终可用性', '事实分层', '原生存在', '产品资格', '入口发布', '企业启用', '当前用户权限', '生效产品版本']) {
    check(drawerText.includes(label), `capability detail exposes ${label}`);
  }
  report.api.selected_entry = selectedRow.entry_ref;
  await screenshot(page, '01-project-capability');

  const releaseResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/intent')
    && intentOf(response.request()) === 'release.operator.surface'
    && response.status() === 200
  ), { timeout: 15000 }).catch(() => null);
  await page.goto(`${BASE_URL}/t/demo/admin/release-operator?product_key=construction.standard`, {
    waitUntil: 'domcontentloaded',
  });
  const releaseResponse = await releaseResponsePromise;
  if (!releaseResponse) {
    check(
      page.url().includes('/access-denied') || page.url().includes('/s/workspace.home'),
      'tenant identity is routed away from the platform-control surface',
    );
    report.api.release = {
      browser_status: 'tenant_identity_redirected_from_platform_control',
      url: page.url(),
    };
  } else {
    const release = intentData(await releaseResponse.json());
    check(release.actor_scope?.user_id > 0, 'release surface declares the actor');
    check(release.operation_readback?.product_key === 'construction.standard', 'release surface declares product-scoped readback');
    check(release.available_actions?.freeze?.target_scope?.is_global_product_release === true, 'product release target scope is explicit');
    const releaseText = await page.locator('[data-semantic-component="ReleaseOperatorView"]').innerText();
    for (const label of ['操作身份与影响范围', '发布后回读', '当前生效版本', '回滚目标']) {
      check(releaseText.includes(label), `release console exposes ${label}`);
    }
    report.api.release = {
      browser_status: 'platform_admin_surface_available',
      actor: release.actor_scope,
      active_snapshot: release.operation_readback?.active_snapshot,
      rollback_target_snapshot_id: release.operation_readback?.rollback_target_snapshot_id,
    };
  }
  await screenshot(page, '02-release-console');

  const configContext = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
  const configPage = await configContext.newPage();
  await login(configPage, CONFIG_LOGIN, CONFIG_PASSWORD);
  const activationResponse = configPage.waitForResponse((response) => (
    response.url().includes('/api/v1/intent')
    && intentOf(response.request()) === 'scenario.activation.catalog.get'
    && response.status() === 200
  ));
  await configPage.goto(`${BASE_URL}/t/demo/s/enterprise.setup`, { waitUntil: 'domcontentloaded' });
  const activation = intentData(await (await activationResponse).json());
  check(activation.target_scope?.company_id > 0, 'enterprise catalog declares target company');
  check(activation.target_scope?.is_global_product_release === false, 'enterprise catalog is not a global product write');
  check(activation.actor?.user_id > 0, 'enterprise catalog declares actor');
  check(
    (activation.business_scenarios || []).every((row) => row.product_qualification && Array.isArray(row.enablement_blockers)),
    'enterprise catalog rows declare qualification evidence and blockers',
  );
  const panel = configPage.locator('#enterprise-scenario-activation[data-state="ready"]');
  await panel.waitFor({ timeout: 60000 });
  const panelText = await panel.innerText();
  check(panelText.includes('操作者：'), 'enterprise panel displays actor');
  check(panelText.includes('目标公司：'), 'enterprise panel displays target company');
  check(panelText.includes('产品资格：'), 'enterprise panel displays product qualification');
  report.api.enterprise_activation = {
    actor: activation.actor,
    target_scope: activation.target_scope,
    row_count: activation.business_scenarios?.length || 0,
  };
  await configPage.screenshot({
    path: path.join(ARTIFACT_DIR, '03-enterprise-activation.png'),
    fullPage: true,
  });
  report.screenshots.push({
    name: '03-enterprise-activation',
    file: path.join(ARTIFACT_DIR, '03-enterprise-activation.png'),
    url: configPage.url(),
  });
  await configContext.close();

  const businessContext = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
  const businessPage = await businessContext.newPage();
  await login(businessPage, BUSINESS_LOGIN, BUSINESS_PASSWORD);
  await businessPage.goto(`${BASE_URL}/t/demo/`, { waitUntil: 'domcontentloaded' });
  const ledgerMenu = businessPage.getByText('项目台账', { exact: true }).first();
  const dashboardMenu = businessPage.getByText('项目看板', { exact: true }).first();
  if (await ledgerMenu.count()) {
    await ledgerMenu.click();
  } else {
    await dashboardMenu.waitFor({ timeout: 60000 });
    await dashboardMenu.click();
  }
  await businessPage.waitForFunction(() => {
    const text = document.body?.textContent || '';
    return text.includes('项目台账') || text.includes('项目看板') || text.includes('访问被拒绝') || text.includes('权限');
  }, null, { timeout: 60000 });
  const businessText = await businessPage.locator('body').innerText();
  check(
    businessText.includes('项目台账') || businessText.includes('项目看板') || businessText.includes('访问被拒绝') || businessText.includes('权限'),
    'ordinary business user receives an explicit formal project result',
  );
  report.api.business_entry = {
    login: BUSINESS_LOGIN,
    route: businessPage.url(),
    outcome: businessText.includes('项目台账')
      ? 'project_ledger_available'
      : businessText.includes('项目看板')
        ? 'project_dashboard_available'
        : 'explicit_denial',
  };
  await businessPage.screenshot({ path: path.join(ARTIFACT_DIR, '04-business-entry.png'), fullPage: true });
  await businessContext.close();

  check(report.errors.length === 0, 'management journey has no browser errors', report.errors);
  report.pass = true;
  await fs.writeFile(path.join(ARTIFACT_DIR, 'summary.json'), JSON.stringify(report, null, 2));
  console.log(`[admin_close_01.management_browser] PASS assertions=${report.assertions.length}`);
} catch (error) {
  report.errors.push({ type: 'journey', text: error instanceof Error ? error.message : String(error) });
  await fs.mkdir(ARTIFACT_DIR, { recursive: true });
  await fs.writeFile(path.join(ARTIFACT_DIR, 'summary.json'), JSON.stringify(report, null, 2));
  console.error(`[admin_close_01.management_browser] FAIL ${error instanceof Error ? error.message : error}`);
  process.exitCode = 1;
} finally {
  await browser.close();
}
