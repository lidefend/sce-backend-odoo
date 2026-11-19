import fs from 'node:fs/promises';
import path from 'node:path';
import { launchChromium } from '../../../../scripts/verify/playwright_runtime.mjs';

const BASE_URL = String(process.env.FRONTEND_URL || 'http://127.0.0.1:18081').replace(/\/+$/, '');
const ENTRY_NAMESPACE = String(process.env.SC_ENTRY_NAMESPACE || 'demo').trim();
const BROWSER_LOCALE = String(process.env.E2E_LOCALE || 'zh-CN');
const LOGIN = String(process.env.E2E_LOGIN || 'admin').trim();
const PASSWORD = String(process.env.E2E_PASSWORD || '123456').trim();
const ADMIN_LOGIN = String(process.env.ADMIN_CLOSE_01_ADMIN_LOGIN || LOGIN).trim();
const ADMIN_PASSWORD = String(process.env.ADMIN_CLOSE_01_ADMIN_PASSWORD || PASSWORD).trim();
const CONFIG_LOGIN = String(process.env.ADMIN_CLOSE_01_CONFIG_LOGIN || 'sc_demo_business_config').trim();
const CONFIG_PASSWORD = String(process.env.ADMIN_CLOSE_01_CONFIG_PASSWORD || PASSWORD).trim();
const BUSINESS_LOGIN = String(process.env.ADMIN_CLOSE_01_BUSINESS_LOGIN || 'wutao').trim();
const BUSINESS_PASSWORD = String(process.env.ADMIN_CLOSE_01_BUSINESS_PASSWORD || PASSWORD).trim();
const REQUIRE_POSITIVE = process.env.ADMIN_CLOSE_01_REQUIRE_POSITIVE === '1';
const REQUIRE_PLATFORM_RELEASE = process.env.ADMIN_CLOSE_01_REQUIRE_PLATFORM_RELEASE === undefined
  ? REQUIRE_POSITIVE
  : process.env.ADMIN_CLOSE_01_REQUIRE_PLATFORM_RELEASE === '1';
const REQUIRE_ENTERPRISE_POSITIVE = process.env.ADMIN_CLOSE_01_REQUIRE_ENTERPRISE_POSITIVE === undefined
  ? REQUIRE_POSITIVE
  : process.env.ADMIN_CLOSE_01_REQUIRE_ENTERPRISE_POSITIVE === '1';
const PROJECT_SCENE_KEY = String(process.env.ADMIN_CLOSE_01_PROJECT_SCENE_KEY || '').trim();
const SKIP_EXPLORER = process.env.ADMIN_CLOSE_01_SKIP_EXPLORER === '1';
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
    admin_login: ADMIN_LOGIN,
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

function watchPage(page, label) {
  page.on('console', (message) => {
    if (message.type() === 'error' && !/favicon|ResizeObserver/i.test(message.text())) {
      report.errors.push({ type: 'console', page: label, text: message.text(), url: page.url() });
    }
  });
  page.on('pageerror', (error) => report.errors.push({
    type: 'pageerror', page: label, text: error.message, url: page.url(),
  }));
}

async function screenshot(page, name) {
  const file = path.join(ARTIFACT_DIR, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  report.screenshots.push({ name, file, url: page.url() });
}

async function login(page, loginName, password) {
  await page.goto(`${BASE_URL}/t/${ENTRY_NAMESPACE}/login`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.locator('#login-username, input[autocomplete="username"]').first().fill(loginName);
  await page.locator('#login-password, input[autocomplete="current-password"]').first().fill(password);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForFunction(() => !window.location.pathname.includes('/login'), null, { timeout: 60000 });
  await page.locator('.layout-shell').waitFor({ timeout: 60000 });
}

function findNavigationNode(nodes, predicate) {
  for (const node of Array.isArray(nodes) ? nodes : []) {
    if (!node || typeof node !== 'object') continue;
    if (predicate(node)) return node;
    const child = findNavigationNode(node.children || node.nodes || [], predicate);
    if (child) return child;
  }
  return null;
}

function checkActivationReadback(payload, expected, label) {
  const readback = payload?.readback || {};
  check(payload?.scene_key === expected.sceneKey, `${label} returns requested scene`, payload);
  check(payload?.enabled === expected.targetState, `${label} returns target state`, payload);
  check(readback?.company_id === expected.companyId, `${label} binds target company`, readback);
  check(readback?.requested_scene_key === expected.sceneKey, `${label} binds requested scene`, readback);
  check(readback?.enabled === expected.targetState, `${label} binds persisted state`, readback);
  check(readback?.target_state === expected.targetState, `${label} declares target state`, readback);
  check(readback?.enablement_scope === expected.scope, `${label} binds enablement scope`, readback);
  check(readback?.source === 'ir.config_parameter', `${label} declares storage source`, readback);
  check(Boolean(readback?.storage_key), `${label} declares storage key`, readback);
  check(readback?.write_committed === true, `${label} confirms committed write`, readback);
  check(readback?.access_granted === false, `${label} does not grant user access`, readback);
}

async function executeScenarioAction(configPage, scenario, actionKey) {
  const actionLabel = actionKey === 'enable' ? '启用' : '停用';
  const panel = configPage.locator('#enterprise-scenario-activation[data-state="ready"]');
  const row = panel.locator('li').filter({ hasText: scenario.name }).first();
  const button = row.getByRole('button', { name: actionLabel, exact: true });
  const writeResponse = configPage.waitForResponse((response) => (
    response.url().includes('/api/v1/intent')
    && intentOf(response.request()) === 'scenario.activation.set'
    && response.status() === 200
  ));
  const refreshResponse = configPage.waitForResponse((response) => (
    response.url().includes('/api/v1/intent')
    && intentOf(response.request()) === 'scenario.activation.catalog.get'
    && response.status() === 200
  ));
  await button.click();
  const payload = intentData(await (await writeResponse).json());
  checkActivationReadback(payload, {
    companyId: Number(scenario.company_id),
    sceneKey: scenario.scene_key,
    scope: scenario.enablement_scope,
    targetState: actionKey === 'enable',
  }, `enterprise ${actionLabel}`);
  const refreshed = intentData(await (await refreshResponse).json());
  await panel.waitFor({ state: 'visible', timeout: 60000 });
  return { payload, refreshed };
}

const browser = await launchChromium({ headless: true });
try {
  await fs.mkdir(ARTIFACT_DIR, { recursive: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: BROWSER_LOCALE });
  const page = await context.newPage();
  watchPage(page, 'platform');

  await login(page, ADMIN_LOGIN, ADMIN_PASSWORD);
  let projectRow = null;
  if (SKIP_EXPLORER) {
    await page.goto(`${BASE_URL}/t/${ENTRY_NAMESPACE}/`, { waitUntil: 'domcontentloaded' });
    report.api.project_ledger_browser_available = false;
    report.api.project_ledger_browser_reason = 'EXPLORER_SEPARATELY_VERIFIED_BY_PLATFORM_ADMIN';
  } else {
    const initialExplorer = page.waitForResponse((response) => (
      response.url().includes('/api/v1/intent')
      && intentOf(response.request()) === 'platform.capability.explorer.list'
      && response.status() === 200
    ));
    await page.goto(`${BASE_URL}/t/${ENTRY_NAMESPACE}/admin/capability-explorer`, { waitUntil: 'domcontentloaded' });
    const initialPayload = intentData(await (await initialExplorer).json());
    await page.getByRole('heading', { name: '平台能力浏览器' }).waitFor({ timeout: 60000 });

    const filteredExplorer = page.waitForResponse((response) => (
      response.url().includes('/api/v1/intent')
      && intentOf(response.request()) === 'platform.capability.explorer.list'
      && response.status() === 200
    ));
    await page.getByPlaceholder('搜索名称、模块、模型、Action 或场景').fill('menu_sc_project_project');
    const filteredPayload = intentData(await (await filteredExplorer).json());
    projectRow = (filteredPayload.rows || []).find((row) => (
      row.entry_ref?.menu_xmlid === 'smart_construction_core.menu_sc_project_project'
    ));
    const selectedRow = projectRow || (initialPayload.rows || [])[0];
    check(selectedRow, 'governed catalog exposes at least one capability entry');
    if (REQUIRE_POSITIVE) {
      check(projectRow, 'positive journey exposes the project-ledger capability', filteredPayload.rows);
    }
    if (!projectRow) {
      report.api.project_ledger_browser_available = false;
      report.api.project_ledger_browser_reason = 'ACTIVE_ACCEPTANCE_MENU_SET_EXCLUDES_PROJECT_LEDGER';
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
  }

  const releaseResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/intent')
    && intentOf(response.request()) === 'release.operator.surface'
    && response.status() === 200
  ), { timeout: 15000 }).catch(() => null);
  await page.goto(`${BASE_URL}/t/${ENTRY_NAMESPACE}/admin/release-operator?product_key=construction.standard`, {
    waitUntil: 'domcontentloaded',
  });
  const releaseResponse = await releaseResponsePromise;
  if (!releaseResponse) {
    if (REQUIRE_PLATFORM_RELEASE) {
      check(false, 'positive journey opens the platform release console', { url: page.url() });
    }
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
    const promotionActions = Array.isArray(release.available_actions?.promote)
      ? release.available_actions.promote
      : [];
    if (REQUIRE_PLATFORM_RELEASE) {
      check(promotionActions.length > 0, 'positive journey exposes a candidate promotion contract');
      const action = promotionActions.find((item) => (
        item?.enabled === true
        && item?.actor?.user_id === release.actor_scope?.user_id
        && item?.target_scope?.product_key === 'construction.standard'
        && item?.operation_object?.kind === 'release_snapshot'
        && item?.prerequisites?.satisfied === true
        && item?.readback?.mode === 'authoritative_after_write'
      ));
      check(action, 'candidate promotion declares complete executable contract', promotionActions);
      const promotedSnapshotId = Number(action.params?.snapshot_id || 0);
      const writeResponse = page.waitForResponse((response) => (
        response.url().includes('/api/v1/intent')
        && intentOf(response.request()) === 'release.operator.promote'
        && response.status() === 200
      ));
      await page.getByRole('button', { name: action.label, exact: true }).first().click();
      const dialog = page.getByRole('dialog');
      await dialog.waitFor({ state: 'visible', timeout: 30000 });
      await dialog.getByRole('button', { name: `确认${action.label}`, exact: true }).click();
      const result = intentData(await (await writeResponse).json());
      const promotedReadback = result?.surface?.operation_readback || result?.operation_readback || {};
      check(
        Number(promotedReadback?.active_snapshot?.id || 0) === promotedSnapshotId,
        'promotion is confirmed by authoritative snapshot readback',
        promotedReadback,
      );
      report.api.promoted_snapshot_id = promotedSnapshotId;
      report.api.promotion_readback = promotedReadback;
    }
    report.api.release = {
      browser_status: 'platform_admin_surface_available',
      actor: release.actor_scope,
      active_snapshot: release.operation_readback?.active_snapshot,
      rollback_target_snapshot_id: release.operation_readback?.rollback_target_snapshot_id,
    };
  }
  await screenshot(page, '02-release-console');

  const configContext = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: BROWSER_LOCALE });
  const configPage = await configContext.newPage();
  watchPage(configPage, 'enterprise');
  await login(configPage, CONFIG_LOGIN, CONFIG_PASSWORD);
  const activationResponse = configPage.waitForResponse((response) => (
    response.url().includes('/api/v1/intent')
    && intentOf(response.request()) === 'scenario.activation.catalog.get'
    && response.status() === 200
  ));
  await configPage.goto(`${BASE_URL}/t/${ENTRY_NAMESPACE}/s/enterprise.setup`, { waitUntil: 'domcontentloaded' });
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
  let positiveScenario = null;
  if (REQUIRE_ENTERPRISE_POSITIVE) {
    const sceneKey = String(projectRow?.business_domain?.key || PROJECT_SCENE_KEY).trim();
    positiveScenario = (activation.business_scenarios || []).find((scenario) => (
      scenario.scene_key === sceneKey
      && scenario.enable_allowed === true
      && Array.isArray(scenario.actions)
      && scenario.actions.some((action) => action.key === 'enable' || action.key === 'disable')
    ));
    check(positiveScenario, 'project-ledger scene exposes an executable enterprise action', {
      sceneKey,
      rows: activation.business_scenarios,
    });
    positiveScenario.company_id = activation.company_id;
    if (positiveScenario.tenant_enabled) {
      await executeScenarioAction(configPage, positiveScenario, 'disable');
      positiveScenario.tenant_enabled = false;
    }
    const enabled = await executeScenarioAction(configPage, positiveScenario, 'enable');
    positiveScenario.tenant_enabled = true;
    report.api.enterprise_activation.enable_readback = enabled.payload;
  }
  await configPage.screenshot({
    path: path.join(ARTIFACT_DIR, '03-enterprise-activation.png'),
    fullPage: true,
  });
  report.screenshots.push({
    name: '03-enterprise-activation',
    file: path.join(ARTIFACT_DIR, '03-enterprise-activation.png'),
    url: configPage.url(),
  });
  const businessContext = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: BROWSER_LOCALE });
  const businessPage = await businessContext.newPage();
  watchPage(businessPage, 'business');
  const businessStartupResponse = businessPage.waitForResponse((response) => (
    response.url().includes('/api/v1/intent')
    && intentOf(response.request()) === 'system.init'
    && response.status() === 200
  ));
  await login(businessPage, BUSINESS_LOGIN, BUSINESS_PASSWORD);
  const businessStartup = intentData(await (await businessStartupResponse).json());
  const ledgerNode = findNavigationNode(businessStartup?.navigation?.nav || [], (node) => (
    node.menu_xmlid === 'smart_construction_core.menu_sc_project_project'
    || node.meta?.menu_xmlid === 'smart_construction_core.menu_sc_project_project'
  ));
  const ledgerMenuId = Number(
    ledgerNode?.menu_id
    || ledgerNode?.meta?.menu_id
    || ledgerNode?.id
    || 0,
  );
  let businessPositiveFailure = '';
  if (ledgerMenuId > 0) {
    await businessPage.goto(
      `${BASE_URL}/t/${ENTRY_NAMESPACE}/m/${ledgerMenuId}`,
      { waitUntil: 'domcontentloaded' },
    );
  } else {
    await businessPage.goto(`${BASE_URL}/t/${ENTRY_NAMESPACE}/`, { waitUntil: 'domcontentloaded' });
  }
  const ledgerMenu = businessPage.getByText('项目台账', { exact: true }).first();
  const dashboardMenu = businessPage.getByText('项目看板', { exact: true }).first();
  if (ledgerMenuId > 0) {
    // The resolved formal navigation identity is the authoritative route.
  } else if (await ledgerMenu.count()) {
    await ledgerMenu.click();
  } else if (REQUIRE_ENTERPRISE_POSITIVE) {
    businessPositiveFailure = 'positive journey reaches the project-ledger formal menu';
  } else {
    const navigationMenuId = await dashboardMenu.evaluate((element) => (
      element.closest('li[data-navigation-menu-id]')?.getAttribute('data-navigation-menu-id') || ''
    ));
    check(navigationMenuId, 'project dashboard formal navigation node declares its menu identity');
    await businessPage.goto(
      `${BASE_URL}/t/${ENTRY_NAMESPACE}/m/${encodeURIComponent(navigationMenuId)}`,
      { waitUntil: 'domcontentloaded' },
    );
  }
  await businessPage.waitForFunction(() => {
    const text = document.body?.textContent || '';
    return text.includes('项目台账') || text.includes('项目看板') || text.includes('访问被拒绝') || text.includes('权限');
  }, null, { timeout: 60000 });
  const businessText = await businessPage.locator('body').innerText();
  if (REQUIRE_ENTERPRISE_POSITIVE) {
    if (!businessText.includes('项目台账')) {
      businessPositiveFailure = 'ordinary business user opens the enabled project ledger';
    }
    if (!businessPositiveFailure) {
      report.assertions.push({ pass: true, message: 'ordinary business user opens the enabled project ledger' });
    }
  } else {
    check(
      businessText.includes('项目台账') || businessText.includes('项目看板') || businessText.includes('访问被拒绝') || businessText.includes('权限'),
      'ordinary business user receives an explicit formal project result',
    );
  }
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

  if (positiveScenario) {
    const disabled = await executeScenarioAction(configPage, positiveScenario, 'disable');
    report.api.enterprise_activation.disable_readback = disabled.payload;
    const afterDisable = (disabled.refreshed.business_scenarios || []).find(
      (scenario) => scenario.scene_key === positiveScenario.scene_key,
    );
    check(afterDisable?.tenant_enabled === false, 'enterprise disable is read back as disabled');
    await configPage.screenshot({
      path: path.join(ARTIFACT_DIR, '05-enterprise-readback.png'),
      fullPage: true,
    });
    report.screenshots.push({
      name: '05-enterprise-readback',
      file: path.join(ARTIFACT_DIR, '05-enterprise-readback.png'),
      url: configPage.url(),
    });
    if (businessPositiveFailure) check(false, businessPositiveFailure);
  }
  await configContext.close();

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
