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
const ENTERPRISE_COMPANY_ACTION_XMLID =
  'smart_construction_core.action_sc_enterprise_company';
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
  assert.equal(refreshed.company_id, COMPANY_ID);
  const refreshedRow = (refreshed.business_scenarios || []).find((row) => row.scene_key === sceneKey);
  assert.ok(refreshedRow, `scenario ${sceneKey} must remain in the refreshed business catalog`);
  assert.equal(refreshedRow.tenant_enabled, action.enabled);
  await panel.waitFor({ timeout: 30000 });
  assert.equal(await panel.getAttribute('data-state'), 'ready');
  return { before, action, readback, refreshed };
}

function companyReadIntent(request, recordId) {
  const body = intentBody(request);
  return body?.intent === 'api.data'
    && body?.params?.op === 'read'
    && body?.params?.model === 'res.company'
    && Array.isArray(body?.params?.ids)
    && body.params.ids.includes(recordId);
}

function companyStreet2WriteIntent(request, recordId) {
  const body = intentBody(request);
  return body?.intent === 'api.data'
    && body?.params?.op === 'write'
    && body?.params?.model === 'res.company'
    && Array.isArray(body?.params?.ids)
    && body.params.ids.includes(recordId)
    && Object.hasOwn(body?.params?.vals || {}, 'street2');
}

async function saveCompanyStreet2(page, recordId, value) {
  const field = page.locator('input[placeholder="请输入详细地址"]');
  await field.waitFor({ timeout: 30000 });
  await field.fill(value);
  const writeResponsePromise = page.waitForResponse(
    response => response.url().includes('/api/v1/intent')
      && companyStreet2WriteIntent(response.request(), recordId),
    { timeout: 30000 },
  );
  const readResponsePromise = page.waitForResponse(
    response => response.url().includes('/api/v1/intent')
      && companyReadIntent(response.request(), recordId),
    { timeout: 30000 },
  );
  await page.locator('button[data-action-ref="form.save"]:visible').click();
  const writeResponse = await writeResponsePromise;
  const writeBody = await writeResponse.json();
  assert.equal(writeResponse.status(), 200);
  assert.equal(writeBody?.ok, true, JSON.stringify(writeBody?.error || {}));
  assert.deepEqual(writeBody?.data?.ids, [recordId]);
  const readResponse = await readResponsePromise;
  const readBody = await readResponse.json();
  assert.equal(readResponse.status(), 200);
  assert.equal(readBody?.ok, true, JSON.stringify(readBody?.error || {}));
  const record = (readBody?.data?.records || [])[0];
  assert.ok(record, 'company readback must contain the saved record');
  assert.equal(record.id, recordId);
  assert.equal(record.street2, value);
  return {
    submitted: value,
    record,
    recordVersion: writeBody?.data?.record_version || '',
    writeStatus: writeResponse.status(),
    readStatus: readResponse.status(),
  };
}

async function returnToEnterpriseSetup(page, listLocation) {
  await page.getByRole('button', { name: '返回', exact: true }).click();
  await page.waitForFunction(
    expected => location.pathname === expected.pathname && location.search === expected.search,
    listLocation,
    { timeout: 30000 },
  );
  const diagnosisResponsePromise = page.waitForResponse(
    response => response.url().includes('/api/v1/intent')
      && intentBody(response.request()).intent === 'enterprise.readiness.diagnosis.get',
    { timeout: 45000 },
  );
  const setupTab = page.locator('button[aria-label="切换至企业初始化"]:visible');
  await setupTab.waitFor({ timeout: 30000 });
  await setupTab.click();
  await page.waitForFunction(
    () => location.pathname === '/s/enterprise.setup',
    null,
    { timeout: 30000 },
  );
  await page.getByRole('heading', { name: '企业初始化' }).waitFor({ timeout: 30000 });
  const diagnosisResponse = await diagnosisResponsePromise;
  const diagnosisBody = await diagnosisResponse.json();
  assert.equal(diagnosisResponse.status(), 200);
  assert.equal(diagnosisBody?.ok, true, JSON.stringify(diagnosisBody?.error || {}));
  const diagnosis = diagnosisBody?.data?.data ?? diagnosisBody?.data;
  assert.equal(diagnosis.company_id, COMPANY_ID);
  assert.equal(diagnosis.contract_version, 'enterprise_readiness.v2');
  return { url: page.url(), diagnosis };
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
    const businessWritesBeforeEntry = requests.filter(isBusinessWrite).length;
    await page.goto(`${BASE_URL}/s/enterprise.setup`, { waitUntil: 'domcontentloaded', timeout: 45000 });
    const entry = page.locator(
      `button.handling-item[data-action-xmlid="${ENTERPRISE_COMPANY_ACTION_XMLID}"]`,
    ).first();
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
      assert.equal(
        missing,
        `scene_ready_contract.scene_internal_actions.enterprise.setup:${ENTERPRISE_COMPANY_ACTION_XMLID}`,
      );
      assert.equal(layer, 'P0:smart_core:system_init_scene_runtime_surface_builder');
      assert.match(await gap.innerText(), /页面执行契约暂不可用/);
      assert.match(await gap.innerText(), /ContractGapError/);
      assert.doesNotMatch(await page.locator('body').innerText(), /无权访问/);
      assert.equal(
        requests.filter(isBusinessWrite).length,
        businessWritesBeforeEntry,
        'a blocked entry must not issue an additional business write',
      );
      report.entry_feedback = { kind: 'contract_gap', missing, layer, path: page.url() };
    } else {
      assert.notEqual(new URL(page.url()).pathname, '/access-denied');
      assert.match(new URL(page.url()).pathname, /^\/a\/\d+$/);
      report.entry_feedback = { kind: 'resolved_target', path: page.url() };
      const companyName = catalog.target_scope?.company_name || '';
      assert.ok(companyName, 'resolved company entry must expose the target company name');
      const listLocation = {
        pathname: new URL(page.url()).pathname,
        search: new URL(page.url()).search,
      };
      await page.locator(
        'tr[data-record-key] button[data-semantic-cell-kind="primary"]:visible',
      ).first().click();
      await page.waitForFunction(
        () => /^\/f\/res\.company\/\d+$/.test(location.pathname),
        null,
        { timeout: 30000 },
      );
      const companyRecordId = Number(new URL(page.url()).pathname.split('/').pop());
      assert.ok(Number.isInteger(companyRecordId) && companyRecordId > 0);
      const street2 = page.locator('[data-field-name="street2"] input');
      await street2.waitFor({ timeout: 30000 });
      const originalStreet2 = await street2.inputValue();
      const marker = `C02-01-${Date.now()}`;
      report.c02_01 = {
        company_id: COMPANY_ID,
        company_record_id: companyRecordId,
        company_name: companyName,
        original_street2: originalStreet2,
        submitted_street2: marker,
      };
      try {
        const saved = await saveCompanyStreet2(page, companyRecordId, marker);
        report.c02_01.write = saved;
        report.c02_01.readback = saved.record;
      } finally {
        const restore = await saveCompanyStreet2(page, companyRecordId, originalStreet2);
        report.c02_01.restore = restore;
      }
      const returned = await returnToEnterpriseSetup(page, listLocation);
      report.c02_01.return_url = returned.url;
      report.c02_01.diagnosis = {
        contract_version: returned.diagnosis.contract_version,
        company_id: returned.diagnosis.company_id,
        company_name: returned.diagnosis.company_name,
        summary: returned.diagnosis.summary,
        enterprise_identity: (returned.diagnosis.rules || []).find(
          row => row.label === '企业身份',
        ) || null,
      };
      assert.equal(
        report.c02_01.restore.record.street2,
        originalStreet2,
        'C02-01 must restore the original company detail address',
      );
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
