import fs from 'node:fs/promises';
import path from 'node:path';
import { launchChromium } from '../../../../scripts/verify/playwright_runtime.mjs';
import { authenticateDeniedProbe, createExpectedHttpFailureBudget } from './platform_capability_explorer_browser_support.mjs';

const BASE_URL = String(process.env.FRONTEND_URL || 'http://127.0.0.1:18081').replace(/\/+$/, '');
const DB_NAME = String(process.env.DB_NAME || 'sc_dev_demo').trim();
const LOGIN = String(process.env.E2E_LOGIN || 'admin').trim();
const PASSWORD = String(process.env.E2E_PASSWORD || '123456').trim();
const DENIED_LOGIN = String(process.env.E2E_DENIED_LOGIN || 'wutao').trim();
const DENIED_PASSWORD = String(process.env.E2E_DENIED_PASSWORD || '123456').trim();
const ARTIFACT_DIR = path.resolve(
  process.cwd(),
  process.env.ARTIFACTS_DIR || 'artifacts/playwright/platform-capability-explorer',
);
const ROUTE = `${BASE_URL}/t/demo/admin/capability-explorer`;

const report = {
  schema: 'platform.capability.explorer.browser.v1',
  pass: false,
  generated_at: new Date().toISOString(),
  runtime: { base_url: BASE_URL, database: DB_NAME, login: LOGIN },
  assertions: [],
  screenshots: [],
  api: {},
  errors: [],
  failed_requests: [],
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

function intentParams(request) {
  try {
    return request.postDataJSON()?.params || {};
  } catch {
    return {};
  }
}

function explorerPayload(body) {
  const candidate = body?.data?.meta ? body.data : body?.data?.data?.meta ? body.data.data : null;
  if (!candidate || typeof candidate !== 'object') throw new Error('capability explorer payload missing');
  return candidate;
}

async function screenshot(page, name) {
  const file = path.join(ARTIFACT_DIR, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  report.screenshots.push({ name, file, url: page.url() });
}

async function login(page, loginName = LOGIN, password = PASSWORD, captureDeniedIntent = false) {
  await page.goto(`${BASE_URL}/t/demo/login`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.locator('#login-username, input[autocomplete="username"]').first().fill(loginName);
  await page.locator('#login-password, input[autocomplete="current-password"]').first().fill(password);
  const submit = () => page.getByRole('button', { name: /^登录$/ }).click();
  const deniedIntent = captureDeniedIntent
    ? await authenticateDeniedProbe(
      page,
      loginName,
      submit,
      `${BASE_URL}/t/demo/`,
      String(process.env.E2E_TENANT || 'default'),
    )
    : await submit();
  await page.waitForFunction(() => !window.location.pathname.includes('/login'), null, { timeout: 60000 });
  await page.locator('.layout-shell').waitFor({ timeout: 60000 });
  return deniedIntent;
}

const browser = await launchChromium({ headless: true });
try {
  await fs.mkdir(ARTIFACT_DIR, { recursive: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
  const page = await context.newPage();
  const expectedHttpFailures = createExpectedHttpFailureBudget();
  let expectedConsoleFailures = 0;
  page.on('console', (message) => {
    if (message.type() === 'error' && !/favicon|ResizeObserver/i.test(message.text())) {
      if (expectedConsoleFailures > 0 && /status of 409/i.test(message.text())) {
        expectedConsoleFailures -= 1;
        return;
      }
      report.errors.push({ type: 'console', text: message.text(), url: page.url() });
    }
  });
  page.on('pageerror', (error) => report.errors.push({ type: 'pageerror', text: error.message, url: page.url() }));
  page.on('response', (response) => {
    if (response.status() < 400) return;
    const expected = expectedHttpFailures.consume({
      status: response.status(),
      intent: intentOf(response.request()),
    });
    report.failed_requests.push({ status: response.status(), url: response.url(), expected });
  });

  await login(page);
  const listStartedAt = Date.now();
  const initialListResponse = page.waitForResponse((response) => (
    response.url().includes('/api/v1/intent')
    && intentOf(response.request()) === 'platform.capability.explorer.list'
    && response.status() === 200
  ));
  await page.goto(ROUTE, { waitUntil: 'domcontentloaded', timeout: 60000 });
  const listResponse = await initialListResponse;
  const listPayload = explorerPayload(await listResponse.json());
  const catalogToken = String(listPayload.meta?.catalog_token || '');
  check(catalogToken.startsWith('sha256:'), 'initial list returns catalog token', { catalogToken });
  check(
    String(listPayload.meta?.runtime_database || '') === DB_NAME,
    'list database matches runtime identity',
    { responseDatabase: listPayload.meta?.runtime_database, DB_NAME },
  );
  await page.getByRole('heading', { name: '平台能力浏览器' }).waitFor({ timeout: 60000 });
  await page.locator('.capability-explorer__metrics').waitFor({ timeout: 60000 });
  await page.waitForFunction((total) => {
    const text = document.querySelector('.capability-explorer__metrics')?.textContent || '';
    return text.includes(String(total)) && !text.includes('—');
  }, String(listPayload.meta.total), { timeout: 60000 });
  const desktopListReadyMs = Date.now() - listStartedAt;
  const metricsText = await page.locator('.capability-explorer__metrics').innerText();
  check(metricsText.includes(String(listPayload.meta.total)), 'summary renders backend total', { metricsText });
  check(
    metricsText.includes(String(listPayload.facets.scene_status.bound || 0)),
    'summary renders backend scene-bound count',
  );
  check(
    metricsText.includes(String(listPayload.facets.scene_status.unbound || 0)),
    'summary renders backend unbound count',
  );
  check(
    metricsText.includes(String(listPayload.facets.centers.length)),
    'summary renders backend center count',
  );
  check(listPayload.rows.length > 0, 'runtime contains visible capability entries');
  report.api.list = {
    total: listPayload.meta.total,
    filtered_total: listPayload.meta.filtered_total,
    row_count: listPayload.rows.length,
    catalog_token: catalogToken,
    centers: listPayload.facets.centers,
    scene_status: listPayload.facets.scene_status,
  };
  await screenshot(page, '01-desktop-list');

  const firstRow = listPayload.rows[0];
  const firstLabel = String(firstRow.label || '');
  const table = page.locator('[data-semantic-component="ScTable"]');
  const detailStartedAt = Date.now();
  await table.getByText(firstLabel, { exact: true }).first().click();
  const drawer = page.getByRole('dialog');
  await drawer.waitFor({ state: 'visible', timeout: 60000 });
  await page.waitForFunction(() => {
    const node = document.querySelector('.sc-design-drawer [role="dialog"]');
    const text = node?.textContent || '';
    return !text.includes('正在读取入口详情并执行诊断');
  }, null, { timeout: 60000 });
  const detailReadyMs = Date.now() - detailStartedAt;
  const drawerText = await drawer.innerText();
  const sectionTitles = await page.locator('.sc-design-drawer .sc-design-section h2').allInnerTexts();
  const drawerHeadings = await page.locator('.sc-design-drawer [role="dialog"] h2').allInnerTexts();
  const sectionCount = await page.locator('.sc-design-drawer .sc-design-section').count();
  check(
    drawerText.includes(String(firstRow.entry_ref.menu_xmlid)),
    'detail renders Menu XMLID',
    { drawerText: drawerText.slice(0, 1200) },
  );
  check(
    drawerText.includes(String(firstRow.entry_ref.action_xmlid)),
    'detail renders Action XMLID',
    { drawerText: drawerText.slice(0, 1200) },
  );
  check(sectionTitles.includes('技术来源'), 'detail technical section rendered', {
    sectionTitles,
    drawerHeadings,
    sectionCount,
  });
  check(sectionTitles.includes('最终可用性'), 'detail final availability section rendered');
  check(sectionTitles.includes('事实分层'), 'detail fact-layer section rendered');
  check(drawerText.includes('当前用户可用') || drawerText.includes('当前用户不可用'), 'detail separates current-user access');
  check(drawerText.includes('生效产品版本'), 'detail renders active product version');
  check(drawerText.includes('模块'), 'detail renders module facts');
  check(drawerText.includes('模型'), 'detail renders model facts');
  check(drawerText.includes('View'), 'detail renders view summary');
  check(drawerText.includes('ACL 摘要'), 'detail renders ACL authorization summary');
  check(drawerText.includes('Record Rules'), 'detail renders record rule count');
  check(drawerText.includes('Preview 资格'), 'detail separates Preview qualification');
  check(drawerText.includes('Standard 资格'), 'detail separates Standard qualification');
  report.api.detail = {
    menu_xmlid: firstRow.entry_ref.menu_xmlid,
    action_xmlid: firstRow.entry_ref.action_xmlid,
    catalog_token: catalogToken,
  };
  await screenshot(page, '02-desktop-detail');
  await page.getByRole('button', { name: '关闭' }).click();

  let interceptedList = false;
  await page.route('**/api/v1/intent', async (route) => {
    const request = route.request();
    if (!interceptedList && intentOf(request) === 'platform.capability.explorer.list') {
      interceptedList = true;
      expectedConsoleFailures += 1;
      expectedHttpFailures.arm({
        status: 409,
        intent: 'platform.capability.explorer.list',
      });
      await route.fulfill({
        status: 409,
        contentType: 'application/json',
        body: JSON.stringify({
          ok: false,
          error: {
            code: 'CATALOG_STALE',
            reason_code: 'CATALOG_STALE',
            message: 'catalog changed',
          },
          meta: { trace_id: 'platform-capability-stale-review' },
        }),
      });
      return;
    }
    if (interceptedList && intentOf(request) === 'platform.capability.explorer.list') {
      await new Promise((resolve) => setTimeout(resolve, 700));
    }
    await route.continue();
  });
  const recoveryList = page.waitForResponse((response) => (
    response.url().includes('/api/v1/intent')
    && intentOf(response.request()) === 'platform.capability.explorer.list'
    && response.status() === 200
  ));
  const staleRecoveryStartedAt = Date.now();
  await page.getByPlaceholder('搜索名称、模块、模型、Action 或场景').fill('项目');
  await page.getByText('运行时目录已变化，旧 token 已失效；页面正在重新读取同一逻辑快照。').waitFor({ timeout: 60000 });
  const recovered = explorerPayload(await (await recoveryList).json());
  const staleRecoveryMs = Date.now() - staleRecoveryStartedAt;
  check(recovered.meta.catalog_token.startsWith('sha256:'), 'stale token triggers a refreshed catalog');
  check(
    recovered.meta.filtered_total > 0 && recovered.meta.filtered_total < listPayload.meta.total,
    'search applies a server-side filtered result',
    {
      total: listPayload.meta.total,
      filtered_total: recovered.meta.filtered_total,
      row_count: recovered.rows.length,
    },
  );
  report.api.stale_recovery = {
    intercepted_list: interceptedList,
    refreshed_token: recovered.meta.catalog_token,
    total: recovered.meta.total,
    filtered_total: recovered.meta.filtered_total,
    row_count: recovered.rows.length,
  };
  await page.unroute('**/api/v1/intent');

  const resetListResponse = page.waitForResponse((response) => (
    response.url().includes('/api/v1/intent')
    && intentOf(response.request()) === 'platform.capability.explorer.list'
    && response.status() === 200
  ));
  await page.getByRole('button', { name: '清除筛选' }).click();
  await resetListResponse;

  const centerFilter = listPayload.facets.centers.find((center) => (
    center.count > 0 && center.count < listPayload.meta.total
  ));
  if (centerFilter) {
    const filteredListResponse = page.waitForResponse((response) => (
      response.url().includes('/api/v1/intent')
      && intentOf(response.request()) === 'platform.capability.explorer.list'
      && response.status() === 200
    ));
    await page.getByRole('button', { name: new RegExp(String(centerFilter.label)) }).first().click();
    const filteredPayload = explorerPayload(await (await filteredListResponse).json());
    check(
      filteredPayload.rows.length === centerFilter.count,
      'native center filter returns its server-projected row count',
      {
        center: centerFilter,
        row_count: filteredPayload.rows.length,
        filtered_total: filteredPayload.meta.filtered_total,
      },
    );
    report.api.center_filter = {
      center: centerFilter,
      row_count: filteredPayload.rows.length,
      filtered_total: filteredPayload.meta.filtered_total,
    };
  }

  const raceResetResponse = page.waitForResponse((response) => (
    response.url().includes('/api/v1/intent')
    && intentOf(response.request()) === 'platform.capability.explorer.list'
    && response.status() === 200
  ));
  await page.getByRole('button', { name: '清除筛选' }).click();
  await raceResetResponse;

  const staleDetailRow = listPayload.rows[1];
  if (staleDetailRow) {
    await table.getByText(firstLabel, { exact: true }).first().click();
    await page.getByRole('button', { name: '重新诊断' }).waitFor({ state: 'visible', timeout: 60000 });

    let interceptLateDiagnose = true;
    let markLateDiagnoseStarted;
    let markLateDiagnoseFinished;
    let releaseLateDiagnose;
    const lateDiagnoseStarted = new Promise((resolve) => { markLateDiagnoseStarted = resolve; });
    const lateDiagnoseFinished = new Promise((resolve) => { markLateDiagnoseFinished = resolve; });
    const lateDiagnoseRelease = new Promise((resolve) => { releaseLateDiagnose = resolve; });
    await page.route('**/api/v1/intent', async (route) => {
      const request = route.request();
      const params = intentParams(request);
      if (
        !interceptLateDiagnose
        || intentOf(request) !== 'platform.capability.explorer.diagnose'
        || String(params?.entry_ref?.menu_xmlid || '') !== String(firstRow.entry_ref.menu_xmlid)
      ) {
        await route.continue();
        return;
      }
      interceptLateDiagnose = false;
      markLateDiagnoseStarted();
      await lateDiagnoseRelease;
      const response = await route.fetch();
      const body = await response.json();
      const payload = body?.data?.meta ? body.data : body?.data?.data?.meta ? body.data.data : null;
      if (payload) payload.blockers = ['LATE_ENTRY_A'];
      await route.fulfill({ response, json: body });
      markLateDiagnoseFinished();
    });

    await page.getByRole('button', { name: '重新诊断' }).click();
    await lateDiagnoseStarted;
    await page.getByRole('button', { name: '关闭' }).click();
    await table.getByText(String(staleDetailRow.label), { exact: true }).first().click();
    await page.waitForFunction(() => {
      const node = document.querySelector('.sc-design-drawer [role="dialog"]');
      const text = node?.textContent || '';
      return !text.includes('正在读取入口详情并执行诊断');
    }, null, { timeout: 60000 });
    releaseLateDiagnose();
    await lateDiagnoseFinished;
    const currentDrawerText = await page.getByRole('dialog').innerText();
    check(
      currentDrawerText.includes(String(staleDetailRow.entry_ref.action_xmlid))
        && !currentDrawerText.includes('LATE_ENTRY_A'),
      'late detail diagnosis cannot overwrite the currently selected entry',
      {
        selectedAction: staleDetailRow.entry_ref.action_xmlid,
        drawerText: currentDrawerText.slice(0, 1200),
      },
    );
    report.race_guard = {
      stale_entry: firstRow.entry_ref,
      current_entry: staleDetailRow.entry_ref,
      late_blocker: 'LATE_ENTRY_A',
    };
    await page.unroute('**/api/v1/intent');
    await page.getByRole('button', { name: '关闭' }).click();
  }

  await page.setViewportSize({ width: 390, height: 844 });
  const mobileStartedAt = Date.now();
  await page.goto(ROUTE, { waitUntil: 'domcontentloaded', timeout: 60000 });
  const mobileList = page.locator('.capability-explorer__mobile-list');
  await mobileList.waitFor({ state: 'visible', timeout: 60000 });
  const firstMobileRow = mobileList.locator('.capability-explorer__mobile-row').first();
  await firstMobileRow.waitFor({ state: 'visible', timeout: 60000 });
  const firstMobileText = await firstMobileRow.innerText();
  check(
    firstMobileText.includes(String(listPayload.rows[0]?.label || '')),
    'mobile list renders backend capability entries',
    { firstMobileText },
  );
  await firstMobileRow.scrollIntoViewIfNeeded();
  const mobileListReadyMs = Date.now() - mobileStartedAt;
  const mobileMetrics = await page.evaluate(() => ({
    viewport: window.innerWidth,
    body_scroll_width: document.body.scrollWidth,
    document_scroll_width: document.documentElement.scrollWidth,
  }));
  check(
    mobileMetrics.body_scroll_width <= mobileMetrics.viewport + 1
      && mobileMetrics.document_scroll_width <= mobileMetrics.viewport + 1,
    'mobile layout has no horizontal page overflow',
    mobileMetrics,
  );
  await screenshot(page, '03-mobile-list');
  report.performance = {
    desktop_list_ready_ms: desktopListReadyMs,
    detail_ready_ms: detailReadyMs,
    stale_recovery_ms: staleRecoveryMs,
    mobile_list_ready_ms: mobileListReadyMs,
  };
  report.api.pagination = {
    total: listPayload.meta.total,
    filtered_total: listPayload.meta.filtered_total,
    row_count: listPayload.rows.length,
    offset: listPayload.meta.offset,
    limit: listPayload.meta.limit,
    next_offset: listPayload.meta.next_offset,
    has_more: listPayload.meta.has_more,
  };

  const deniedContext = await browser.newContext({ viewport: { width: 1280, height: 800 }, locale: 'zh-CN' });
  try {
    const deniedPage = await deniedContext.newPage();
    const deniedIntent = await login(deniedPage, DENIED_LOGIN, DENIED_PASSWORD, true);
    const deniedListRequests = [];
    deniedPage.on('request', (request) => {
      if (intentOf(request) === 'platform.capability.explorer.list') deniedListRequests.push(request.url());
    });
    await deniedPage.goto(ROUTE, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await deniedPage.waitForFunction(
      () => !window.location.pathname.endsWith('/admin/capability-explorer'),
      null,
      { timeout: 60000 },
    );
    check(
      !deniedPage.url().endsWith('/admin/capability-explorer'),
      'non-management user is redirected away from the explorer route',
      { deniedUrl: deniedPage.url() },
    );
    const deniedRouteRequestCount = deniedListRequests.length;
    check(
      deniedRouteRequestCount === 0,
      'non-management route access never calls the explorer API',
      { deniedRouteRequestCount, deniedListRequests },
    );
    const deniedHandler = await deniedIntent(deniedContext);
    check(
      deniedHandler.status === 403 && deniedHandler.reasonCode === 'PERMISSION_DENIED',
      'backend returns exact permission denial for a non-management user',
      deniedHandler,
    );
    report.permissions = {
      denied_login: DENIED_LOGIN,
      redirected: true,
      route_list_request_count: deniedRouteRequestCount,
      direct_handler_list_request_count: deniedHandler.requestCount,
      handler: deniedHandler,
    };
  } finally {
    await deniedContext.close();
  }

  const unexpectedFailures = report.failed_requests.filter((row) => !row.expected);
  check(expectedHttpFailures.pending() === 0, 'every expected HTTP failure was observed', {
    pending: expectedHttpFailures.pending(),
  });
  check(unexpectedFailures.length === 0, 'no unexpected HTTP failures', { unexpectedFailures });
  check(report.errors.length === 0, 'no console or page errors', { errors: report.errors });
  report.pass = true;
  report.completed_at = new Date().toISOString();
  await fs.writeFile(path.join(ARTIFACT_DIR, 'report.json'), JSON.stringify(report, null, 2));
  console.log(`[platform-capability-explorer-browser] PASS entries=${listPayload.meta.total} stale=${interceptedList}`);
} catch (error) {
  report.errors.push({ type: 'runner', text: error instanceof Error ? error.message : String(error) });
  await fs.mkdir(ARTIFACT_DIR, { recursive: true });
  await fs.writeFile(path.join(ARTIFACT_DIR, 'report.json'), JSON.stringify(report, null, 2));
  console.error(`[platform-capability-explorer-browser] FAIL ${error instanceof Error ? error.message : error}`);
  process.exitCode = 1;
} finally {
  await browser.close();
}
