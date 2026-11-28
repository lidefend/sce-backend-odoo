// P4 user-journey probe: initialize the disposable clean enterprise through the
// product's enterprise setup page and read back the committed center scope.
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
    || '.runtime/agent-runs/FE-CONSUMPTION-CLOSEOUT-20261126/local-clean-enterprise-setup',
);
if (!PASSWORD) throw new Error('ACCEPTANCE_PASSWORD is required');
fs.mkdirSync(OUTPUT_DIR, { recursive: true });

const report = {
  schema: 'local_clean.enterprise_setup.v1',
  pass: false,
  generated_at: new Date().toISOString(),
  runtime: {
    base: BASE,
    login: LOGIN,
    source_revision: TARGET_SHA,
    frontend_build_sha256: BUILD_SHA256,
  },
  requests: [],
  responses: [],
  intent_responses: [],
  contract_observations: [],
  failed_requests: [],
  navigations: [],
  readback: null,
  screenshots: [],
  assertions: [],
  console_errors: [],
};

function check(condition, assertion, facts = {}) {
  report.assertions.push({ assertion, pass: Boolean(condition), ...facts });
  if (!condition) throw new Error(`${assertion}: ${JSON.stringify(facts)}`);
}

function envelopeData(body) {
  return body?.data || body?.result?.data || body?.result || {};
}

function requestOf(response) {
  try {
    return JSON.parse(response.request().postData() || '{}');
  } catch {
    return {};
  }
}

function diagnosticParams(intent, params) {
  const value = params && typeof params === 'object' ? params : {};
  if (String(intent || '') === 'login') {
    return {
      login: String(value.login || ''),
      contract_mode: String(value.contract_mode || ''),
    };
  }
  return value;
}

async function shot(page, name) {
  const file = path.join(OUTPUT_DIR, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  report.screenshots.push({ name, file, url: page.url() });
}

const browser = await launchChromium({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
  locale: 'zh-CN',
});
const page = await context.newPage();
const navigation = captureReleasedNavigation(page);
page.setDefaultTimeout(30000);
if (process.env.SC_ACCEPTANCE_HUD === '1') {
  await page.addInitScript(() => localStorage.setItem('__HUD__', '1'));
}
page.on('framenavigated', (frame) => {
  if (frame === page.mainFrame()) report.navigations.push(frame.url());
});
page.on('pageerror', (error) => report.console_errors.push(`pageerror: ${error.message}`));
page.on('console', (message) => {
  if (message.type() === 'error' && !/favicon|ResizeObserver/i.test(message.text())) {
    report.console_errors.push(`console.error: ${message.text()}`.slice(0, 500));
  }
});
page.on('request', (request) => {
  const envelope = request.postDataJSON?.();
  if (!envelope || String(envelope.intent || '') !== 'scenario.activation.centers.set') return;
  report.requests.push(envelope);
});
page.on('response', async (response) => {
  if (!response.url().includes('/api/v1/intent')) return;
  const request = requestOf(response);
  const intent = String(request.intent || '');
  const body = await response.json().catch(() => ({}));
  const data = envelopeData(body);
  report.intent_responses.push({
    intent,
    status: response.status(),
    ok: body?.ok,
    code: body?.code || body?.reason_code || body?.error?.code || body?.error?.reason_code || '',
    error: body?.error || null,
    params: diagnosticParams(intent, request.params),
  });
  if (response.status() >= 400 || body?.ok === false) {
    report.failed_requests.push({
      intent,
      status: response.status(),
      request: diagnosticParams(intent, request.params),
      body,
    });
  }
  if (![
    'system.init',
    'scenario.activation.catalog.get',
    'enterprise.readiness.diagnosis.get',
    'ui.contract.v2',
    'execute_button',
    'api.data',
  ].includes(intent)) return;
  if (intent === 'ui.contract.v2') {
    report.contract_observations.push({
      status: response.status(),
      ok: body?.ok,
      request: request.params || {},
      page_info: data?.pageInfo || null,
      permissions: data?.permissions || null,
      data_contract: {
        permissions: data?.dataContract?.permissions || null,
        access_policy: data?.dataContract?.accessPolicy || data?.dataContract?.access_policy || null,
      },
      action_contract: {
        permissions: data?.actionContract?.permissions || null,
        access_policy: data?.actionContract?.accessPolicy || data?.actionContract?.access_policy || null,
      },
      status_contract: data?.statusContract || null,
      error: body?.error || null,
      ...(process.env.SC_ACCEPTANCE_CAPTURE_RAW_CONTRACTS === '1' ? { raw_body: body } : {}),
    });
    return;
  }
  report.observations ||= [];
  report.observations.push({
    intent: request.intent,
    status: response.status(),
    ok: body?.ok,
    code: body?.code || body?.error?.code || '',
    reason_code: body?.reason_code || body?.error?.reason_code || '',
    error: body?.error || null,
    scene_ready_contract: data?.scene_ready_contract || null,
    scene_channel: data?.scene_channel || null,
    startup_capabilities: Array.isArray(data?.capabilities)
      ? data.capabilities
        .map((item) => ({
          key: String(item?.key || item || '').trim(),
          state: String(item?.state || '').trim(),
          capability_state: String(item?.capability_state || '').trim(),
          reason_code: String(item?.capability_state_reason || item?.reason_code || '').trim(),
          default_payload: item?.default_payload || null,
        }))
        .filter((item) => item.key)
      : [],
    route_authority_target: (() => {
      const routeAuthority = data?.navigation?.route_authority || data?.route_authority || {};
      const pending = Object.values(routeAuthority)
        .filter((value) => Array.isArray(value))
        .flat();
      return pending.find((item) => (
        Number(item?.action_id || 0) === 966
        || Number(item?.menu_id || 0) === 719
      )) || null;
    })(),
    navigation_candidates: (() => {
      const found = [];
      const visit = (value) => {
        if (Array.isArray(value)) {
          value.forEach(visit);
          return;
        }
        if (!value || typeof value !== 'object') return;
        const actionId = Number(
          value.action_id || value.actionId || value.action
          || value.meta?.action_id || value.meta?.actionId || 0,
        );
        const menuId = Number(value.menu_id || value.menuId || value.meta?.menu_id || 0);
        if ((actionId === 966 || menuId === 719)
          || String(value.menu_xmlid || value.meta?.menu_xmlid || '').includes('enterprise_initialization')) {
          found.push(value);
        }
        Object.values(value).forEach(visit);
      };
      visit(data?.nav || data?.nav_meta || data?.navigation?.nav || []);
      return found;
    })(),
    ...(process.env.SC_ACCEPTANCE_CAPTURE_RAW_CONTRACTS === '1' ? { raw_body: body } : {}),
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
  const enterpriseTarget = await navigation.targetByMenuXmlid(
    'smart_construction_core.menu_sc_enterprise_initialization',
    '',
    60000,
  );
  report.runtime.enterprise_target = enterpriseTarget;

  const productConfig = page.getByRole('button', { name: /^产品配置/ }).first();
  if (await productConfig.count()) await productConfig.click();
  const enterpriseEntry = page.getByRole('button', { name: /^企业初始化/ }).first();
  const releasedRoute = String(enterpriseTarget.entry_target?.route || enterpriseTarget.route || '').trim();
  check(releasedRoute.startsWith('/s/'), 'released navigation supplies a scene route', {
    route: releasedRoute,
    entry_target: enterpriseTarget.entry_target || null,
  });
  if (await enterpriseEntry.count()) {
    await enterpriseEntry.click();
    await page.waitForURL(
      (url) => url.pathname.includes(releasedRoute),
      { timeout: 45000 },
    );
    check(new URL(page.url()).pathname.includes(releasedRoute), 'product entry consumes the released scene route', {
      expected_route: releasedRoute,
      url: page.url(),
    });
  } else {
    await page.goto(
      `${BASE}${releasedRoute}?menu_id=${enterpriseTarget.menu_id}&action_id=${enterpriseTarget.action_id}`,
      {
      waitUntil: 'networkidle',
      },
    );
  }
  await page.getByRole('heading', { name: /^企业初始化/ }).first()
    .waitFor({ state: 'visible', timeout: 45000 });
  await page.waitForFunction(
    () => !/企业初始化 · 加载中|正在读取页面契约与业务数据/.test(document.body.innerText),
    null,
    { timeout: 45000 },
  );
  const initialBody = String(await page.locator('#main-content').innerText());
  const requiredSections = [
    '企业基础初始化',
    '业务基础配置',
    '角色与权限初始化',
    '审批规则',
    '场景配置',
  ];
  const requiredActions = [
    '企业信息',
    '组织架构',
    '岗位管理',
    '人员与账号',
    '业务分类',
    '业务字典',
    '预算类型',
    '阶段要求',
    '企业角色配置',
    '企业角色分配',
    '业务权限分配',
    '审批岗位人员',
    '审批策略',
    '业务场景配置',
  ];
  const missingSections = requiredSections.filter((label) => !initialBody.includes(label));
  const missingActions = requiredActions.filter((label) => !initialBody.includes(label));
  check(!missingSections.length, 'enterprise initialization exposes every declared configuration section', {
    missing_sections: missingSections,
  });
  check(!missingActions.length, 'enterprise initialization exposes every declared configuration action', {
    missing_actions: missingActions,
  });
  report.readback = {
    page: 'enterprise_initialization',
    sections: requiredSections,
    actions: requiredActions,
    readonly_record_id: page.url().includes('record_id=1') ? 1 : null,
  };
  await shot(page, '01-enterprise-setup-ready');

  await page.getByRole('button', { name: '企业信息', exact: true }).click();
  await page.waitForURL((url) => !url.pathname.includes('/s/entry.smart_construction_core.menu_sc_enterprise_initialization'), {
    timeout: 45000,
  });
  const companyNameField = page.locator('input[name="name"], textarea[name="name"], [data-field-name="name"] input').first();
  await companyNameField.waitFor({ state: 'visible', timeout: 45000 });
  check(await companyNameField.isEditable(), 'enterprise company information opens an editable maintenance form', {
    url: page.url(),
  });
  report.readback.maintenance_entry = {
    label: '企业信息',
    route: page.url(),
    editable_field: 'name',
  };
  await shot(page, '02-enterprise-company-maintenance');

  await page.waitForFunction(
    () => !/正在加载场景/.test(document.body.innerText),
    null,
    { timeout: 45000 },
  );
  await shot(page, '03-enterprise-setup-complete');
  check(report.console_errors.length === 0, 'enterprise setup journey has no browser errors', {
    errors: report.console_errors,
  });
  report.pass = true;
} catch (error) {
  const routeError = page.locator('[data-route-error-kind]').first();
  const routeErrorState = await routeError.count()
    ? await routeError.evaluate((node) => ({
        kind: node.getAttribute('data-route-error-kind') || '',
        status: node.getAttribute('data-route-error-status') || '',
        traceId: node.getAttribute('data-trace-id') || '',
        text: String(node.textContent || '').trim(),
      })).catch(() => null)
    : null;
  const statusPanel = page.locator('.sc-state-panel').first();
  const statusPanelState = await statusPanel.count()
    ? await statusPanel.evaluate((node) => ({
        state: node.getAttribute('data-state') || '',
        errorKind: node.getAttribute('data-error-kind') || '',
        contractGap: node.getAttribute('data-contract-gap') || '',
        contractGapKind: node.getAttribute('data-contract-gap-kind') || '',
        contractGapLayer: node.getAttribute('data-contract-gap-layer') || '',
        text: String(node.textContent || '').trim(),
      })).catch(() => null)
    : null;
  report.error = {
    type: error instanceof Error ? error.name : typeof error,
    message: error instanceof Error ? error.message : String(error),
    url: page.url(),
    query: Object.fromEntries(new URL(page.url()).searchParams.entries()),
    route_error: routeErrorState,
    status_panel: statusPanelState,
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
    intent_responses: report.intent_responses,
    readback: report.readback,
    navigations: report.navigations,
    console_errors: report.console_errors,
  }, null, 2));
  await context.close();
  await browser.close();
  if (!report.pass) process.exitCode = 1;
}
