import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';

const BASE_URL = String(process.env.FRONTEND_URL || '');
const LOGIN = String(process.env.CONFIG_ADMIN_LOGIN || '');
const USER_ID = Number(process.env.CONFIG_ADMIN_USER_ID || 0);
const COMPANY_ID = Number(process.env.CONFIG_COMPANY_ID || 0);
const PASSWORD = String(process.env.E2E_PASSWORD || '');
const CANDIDATE_SHA = String(process.env.CANDIDATE_GIT_HEAD || '');
const TEST_TOOL_GIT_HEAD = String(process.env.TEST_TOOL_GIT_HEAD || '');
const SCENARIO_ONLY = ['1', 'true', 'yes'].includes(
  String(process.env.C02_SCENARIO_ONLY || '').trim().toLowerCase(),
);
const OUTPUT = path.resolve(
  process.env.ARTIFACT_DIR
    || '.runtime/agent-runs/SCENE-PRODUCT-02-ENTERPRISE-CONFIG-JOURNEY-20261120/enterprise-configuration-consumer',
);

assert.equal(BASE_URL, 'http://127.0.0.1:5176');
assert.match(CANDIDATE_SHA, /^[0-9a-f]{40}$/);
assert.match(TEST_TOOL_GIT_HEAD, /^[0-9a-f]{40}$/);
assert.ok(LOGIN);
assert.ok(USER_ID > 0);
assert.ok(COMPANY_ID > 0);
assert.ok(PASSWORD);
fs.mkdirSync(OUTPUT, { recursive: true });

const report = {
  schema: 'local_dev_enterprise_configuration_consumer.v1',
  status: 'failed',
  candidate_sha: CANDIDATE_SHA,
  test_tool_git_head: TEST_TOOL_GIT_HEAD,
  identity: { login: LOGIN, user_id: USER_ID, company_id: COMPANY_ID },
  scenario_only: SCENARIO_ONLY,
  entry_feedback: null,
  scenario_catalog: null,
  writes: [],
  errors: [],
};

function intentBody(request) {
  try {
    return JSON.parse(request.postData() || '{}');
  } catch {
    return {};
  }
}

function isBusinessWrite(request) {
  const body = intentBody(request);
  if (body?.intent === 'scenario.activation.set') return true;
  return body?.intent === 'api.data'
    && ['create', 'write', 'unlink'].includes(String(body?.params?.op || ''));
}

async function login(page) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.locator('#login-username, input[autocomplete="username"]').first().fill(LOGIN);
  await page.locator('#login-password, input[autocomplete="current-password"]').first().fill(PASSWORD);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForFunction(() => !location.pathname.includes('/login'), null, { timeout: 60000 });
}

async function catalogBodyFrom(response) {
  const body = await response.json();
  assert.equal(response.status(), 200);
  assert.equal(body?.ok, true);
  return body?.data?.data ?? body?.data;
}

async function toggleScenario(page, catalog, sceneKey) {
  const before = (catalog.business_scenarios || []).find((row) => row.scene_key === sceneKey);
  assert.ok(before, `scenario ${sceneKey} must be in the business catalog`);
  const action = before.actions[0];
  assert.ok(action, `scenario ${sceneKey} must expose an action`);
  const panel = page.locator('#enterprise-scenario-activation[data-state="ready"]');
  await panel.waitFor({ timeout: 30000 });
  const index = catalog.business_scenarios.findIndex((row) => row.scene_key === sceneKey);
  const row = panel.locator('li').nth(index);

  const setResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/intent')
    && intentBody(response.request()).intent === 'scenario.activation.set'
  ), { timeout: 30000 });
  const refreshResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/intent')
    && intentBody(response.request()).intent === 'scenario.activation.catalog.get'
  ), { timeout: 30000 });
  await row.getByRole('button', { name: action.label, exact: true }).click();
  const setBody = await (await setResponsePromise).json();
  assert.equal(setBody?.ok, true, JSON.stringify(setBody?.error || {}));
  const readback = setBody?.data?.data ?? setBody?.data;
  assert.equal(readback.scene_key, sceneKey);
  assert.equal(readback.enabled, action.enabled);
  assert.equal(readback.target_scope.company_id, COMPANY_ID);
  assert.equal(readback.readback.company_id, COMPANY_ID);
  assert.equal(readback.readback.requested_scene_key, sceneKey);
  assert.equal(readback.readback.target_state, action.enabled);
  assert.equal(readback.readback.write_committed, true);
  assert.equal(readback.readback.access_granted, false);
  const refreshed = await catalogBodyFrom(await refreshResponsePromise);
  await panel.waitFor({ timeout: 30000 });
  assert.ok((await panel.innerText()).includes('已回读'));
  return { before, action, readback, refreshed };
}

const browser = await launchChromium({ headless: true });
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: 'zh-CN' });
  const page = await context.newPage();
  page.on('pageerror', (error) => report.errors.push(error.message));
  const requests = [];
  page.on('request', (request) => {
    if (request.method() === 'POST' && request.url().includes('/api/v1/intent')) requests.push(request);
  });
  await login(page);

  const catalogResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/intent')
    && intentBody(response.request()).intent === 'scenario.activation.catalog.get'
  ), { timeout: 45000 });
  await page.goto(`${BASE_URL}/s/enterprise.setup`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  let catalog = await catalogBodyFrom(await catalogResponsePromise);
  await page.getByRole('heading', { name: '企业初始化' }).first().waitFor({ timeout: 45000 });
  assert.equal(catalog.company_id, COMPANY_ID);
  assert.equal(catalog.actor.user_id, USER_ID);
  assert.equal(catalog.actor.login, LOGIN);
  assert.equal(catalog.actor.platform_admin, false);
  assert.equal(catalog.target_scope.company_id, COMPANY_ID);
  assert.equal(catalog.target_scope.is_global_product_release, false);

  const panel = page.locator('#enterprise-scenario-activation[data-state="ready"]');
  await panel.waitFor({ timeout: 30000 });
  const catalogRows = Array.isArray(catalog.rows) ? catalog.rows : [];
  const businessRows = Array.isArray(catalog.business_scenarios) ? catalog.business_scenarios : [];
  const actionable = businessRows.find((row) => Array.isArray(row.actions) && row.actions.length);
  const blockerCounts = {};
  for (const row of catalogRows) {
    for (const blocker of row.enablement_blockers || []) {
      blockerCounts[blocker] = (blockerCounts[blocker] || 0) + 1;
    }
  }
  report.scenario_catalog = {
    contract_version: catalog.contract_version,
    row_count: catalog.row_count,
    business_scenario_count: businessRows.length,
    actionable_count: businessRows.filter((row) => Array.isArray(row.actions) && row.actions.length).length,
    blocker_counts: blockerCounts,
    panel_text: await panel.innerText(),
    mode: actionable ? 'executed' : 'blocked_by_declared_qualification',
  };
  if (!actionable) {
    assert.ok(catalogRows.length > 0, 'blocked scenario catalog must expose its source rows');
    assert.ok(Object.keys(blockerCounts).length > 0, 'blocked scenario catalog must expose reasons');
    assert.match(await panel.innerText(), new RegExp(`场景目录共 ${catalog.row_count} 项`));
    for (const blocker of Object.keys(blockerCounts)) {
      assert.ok((await panel.innerText()).includes(blocker));
    }
  } else {
    const selected = actionable.scene_key;
    const first = await toggleScenario(page, catalog, selected);
    catalog = first.refreshed;
    const restored = await toggleScenario(page, catalog, selected);
    assert.equal(restored.action.enabled, first.before.tenant_enabled);
    assert.equal(restored.readback.readback.enabled, first.before.tenant_enabled);
    report.scenario_catalog.selection_readback = first.readback;
    report.scenario_catalog.restore_readback = restored.readback;
  }

  if (SCENARIO_ONLY) {
    assert.equal(report.scenario_catalog.mode, 'executed');
    assert.ok(report.scenario_catalog.selection_readback);
    assert.ok(report.scenario_catalog.restore_readback);
    report.entry_feedback = { kind: 'not_run', reason: 'scenario_only' };
  } else {
    await page.goto(`${BASE_URL}/s/enterprise.setup`, { waitUntil: 'domcontentloaded', timeout: 45000 });
    const entry = page.getByRole('button', { name: '企业信息', exact: true }).first();
    await entry.waitFor({ timeout: 30000 });
    const urlBefore = page.url();
    await entry.click();
    await page.waitForFunction(
      () => location.pathname !== '/s/enterprise.setup' || document.querySelector('[data-contract-gap]') !== null,
      null,
      { timeout: 10000 },
    );
    const gap = page.locator('[data-contract-gap]').first();
    const gapCount = await gap.count();
    if (gapCount) {
      const missing = await gap.getAttribute('data-contract-gap');
      const layer = await gap.getAttribute('data-contract-gap-layer');
      assert.equal(page.url(), urlBefore, 'a contract gap must not navigate to a guessed target');
      assert.equal(missing, 'scene_ready_contract.scene_internal_actions.enterprise.setup:smart_construction_core.action_sc_enterprise_company');
      assert.equal(layer, 'P0:smart_core:system_init_scene_runtime_surface_builder');
      assert.match(await gap.innerText(), /页面执行契约暂不可用/);
      assert.match(await gap.innerText(), /ContractGapError/);
      assert.doesNotMatch(await page.locator('body').innerText(), /无权访问/);
      assert.equal(requests.filter(isBusinessWrite).length, 0, 'a blocked entry must not issue a business write');
      report.entry_feedback = { kind: 'contract_gap', missing, layer, path: page.url() };
    } else {
      assert.notEqual(new URL(page.url()).pathname, '/access-denied');
      assert.match(new URL(page.url()).pathname, /^\/a\/\d+$/);
      report.entry_feedback = { kind: 'resolved_target', path: page.url() };
    }
  }

  report.writes = requests.filter(isBusinessWrite).map((request) => intentBody(request));
  if (SCENARIO_ONLY) {
    assert.ok(
      report.writes.some((body) => body?.intent === 'scenario.activation.set'),
      'scenario-only execution must record its actual enable/restore writes',
    );
  }
  assert.deepEqual(report.errors, []);
  report.status = 'passed';
  fs.writeFileSync(path.join(OUTPUT, 'report.json'), JSON.stringify(report, null, 2));
  console.log(`[enterprise_configuration_consumer] PASS entry=${report.entry_feedback.kind} catalog=${report.scenario_catalog.mode} rows=${report.scenario_catalog.row_count} scenario_only=${SCENARIO_ONLY}`);
  await context.close();
} catch (error) {
  report.failure = error instanceof Error ? error.stack || error.message : String(error);
  fs.writeFileSync(path.join(OUTPUT, 'report.json'), JSON.stringify(report, null, 2));
  console.error(`[enterprise_configuration_consumer] FAIL ${report.failure}`);
  process.exitCode = 1;
} finally {
  await browser.close();
}
