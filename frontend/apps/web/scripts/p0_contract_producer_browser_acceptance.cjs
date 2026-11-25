#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const { createRequire } = require('module');

const requireFromWeb = createRequire(path.join(process.cwd(), 'frontend/apps/web/package.json'));
const { chromium } = requireFromWeb('playwright');

const BASE_URL = process.env.P0A_BASE_URL || 'http://127.0.0.1:18081/t/demo';
const LOGIN = process.env.P0A_LOGIN || 'demo_role_executive';
const PASSWORD = process.env.P0A_PASSWORD || '123456';
const SCENE_KEY = 'dashboard.company';
const ENTRY_INTENT = 'dashboard.company.enter';
const METRIC_BLOCK_KEY = 'company_projects';
const DATA_SOURCE_KEY = 'ds_company_projects';
const ARTIFACT_DIR = path.join(process.cwd(), 'artifacts/p0_contract_producer_01');
const REPORT_PATH = path.join(ARTIFACT_DIR, 'p0a_browser_acceptance.json');
const VIEWPORTS = [
  { name: 'desktop', width: 1440, height: 960 },
  { name: 'mobile', width: 390, height: 844 },
];

function ensureDir(directory) {
  fs.mkdirSync(directory, { recursive: true });
}

async function login(page) {
  await page.goto(`${BASE_URL}/login?t=${Date.now()}`, { waitUntil: 'networkidle' });
  await page.locator('input[autocomplete="username"]').fill(LOGIN);
  await page.locator('input[autocomplete="current-password"]').fill(PASSWORD);
  const loginResponsePromise = page.waitForResponse((response) => {
    if (!response.url().includes('/api/v1/intent')) return false;
    try {
      return JSON.parse(response.request().postData() || '{}')?.intent === 'login';
    } catch {
      return false;
    }
  }, { timeout: 30000 });
  await page.getByRole('button', { name: /^登录$/ }).click();
  const loginResponse = await loginResponsePromise;
  const loginBody = await loginResponse.json().catch(() => ({}));
  const token = String(loginBody?.data?.session?.token || loginBody?.data?.token || '');
  if (!loginResponse.ok() || loginBody?.ok !== true || !token) {
    throw new Error(`login failed: ${JSON.stringify({
      status: loginResponse.status(),
      ok: loginBody?.ok,
      code: loginBody?.error?.code || '',
    })}`);
  }
  await page.waitForFunction(() => !window.location.pathname.includes('/login'), null, { timeout: 30000 });
  await page.waitForLoadState('networkidle').catch(() => {});
  return token;
}

async function requestIntent(page, intent, params, token) {
  return page.evaluate(async ({ baseUrl, intent: requestIntentName, params: requestParams, authToken }) => {
    const response = await fetch(`${baseUrl}/api/v1/intent`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${authToken}`,
      },
      body: JSON.stringify({
        intent: requestIntentName,
        params: requestParams,
      }),
    });
    return { status: response.status, body: await response.json() };
  }, { baseUrl: BASE_URL, intent, params, authToken: token });
}

async function requestScene(page, params, token) {
  return requestIntent(page, ENTRY_INTENT, params, token);
}

async function validateCompatMatrix(page, token) {
  const base = {
    client_type: 'web_pc',
    accepted_contract_versions: ['2.5.x'],
    client_contract_capabilities: [],
  };
  const cases = {
    known_old_without_versions: {
      client_type: 'web_pc',
    },
    pre_negotiation_without_identity: {},
    only_24: {
      ...base,
      accepted_contract_versions: ['2.4.x'],
    },
    legacy_25: base,
    legacy_26_without_capability: {
      ...base,
      accepted_contract_versions: ['2.5.x', '2.6.x'],
    },
    current_page_block_data: {
      ...base,
      accepted_contract_versions: ['2.5.x', '2.6.x'],
      client_contract_capabilities: ['page_block_data.v1'],
    },
    current_page_block_action: {
      ...base,
      accepted_contract_versions: ['2.5.x', '2.6.x'],
      client_contract_capabilities: ['page_block_action.v1'],
    },
    current_page_block_data_and_action: {
      ...base,
      accepted_contract_versions: ['2.5.x', '2.6.x'],
      client_contract_capabilities: ['page_block_data.v1', 'page_block_action.v1'],
    },
    no_common_version: {
      ...base,
      accepted_contract_versions: ['1.0.x', '9.9.x'],
    },
    unknown_client_without_versions: {
      client_type: 'unknown_native',
    },
  };
  const result = {};
  for (const [key, params] of Object.entries(cases)) {
    result[key] = await requestScene(page, params, token);
  }
  return result;
}

async function validateContractV2Matrix(page, token) {
  const base = {
    op: 'model',
    model: 'project.project',
    view_type: 'list',
    client_type: 'web_pc',
    accepted_contract_versions: ['2.5.x', '2.6.x'],
    client_contract_capabilities: [],
  };
  return {
    legacy_26_without_capability: await requestIntent(page, 'ui.contract.v2', base, token),
    current_26: await requestIntent(page, 'ui.contract.v2', {
      ...base,
      client_contract_capabilities: ['page_block_data.v1'],
    }, token),
  };
}

async function captureProjectLedgerForm(page) {
  const formResponsePromise = page.waitForResponse((response) => {
    if (!response.url().includes('/api/v1/intent')) return false;
    try {
      const payload = JSON.parse(response.request().postData() || '{}');
      const params = payload.params || {};
      return (
        payload.intent === 'ui.contract.v2'
        && params.op === 'action_open'
        && Number(params.record_id) > 0
        && String(params.view_type || '') === 'form'
      );
    } catch {
      return false;
    }
  }, { timeout: 30000 });
  await page.goto(`${BASE_URL}/s/projects.ledger`, {
    waitUntil: 'domcontentloaded',
    timeout: 30000,
  });
  const row = page.locator('button[data-semantic-cell-kind="primary"]:visible').first();
  await row.waitFor({ state: 'visible', timeout: 30000 });
  await row.click();
  const response = await formResponsePromise;
  const body = await response.json();
  if (!response.ok() || body?.ok !== true || !body?.data) {
    throw new Error(`project ledger form contract failed: ${JSON.stringify({
      status: response.status(),
      ok: body?.ok,
      code: body?.error?.code || '',
    })}`);
  }
  return body.data;
}

function assertProjectLedgerRowNavigation(contract) {
  const rules = contract?.actionContract?.actionRuleList || [];
  const rowRule = rules.find((rule) => (
    rule?.sourceWidgetId === 'page.row'
    && rule?.actionKey === 'open_form'
  ));
  if (!rowRule) {
    throw new Error('project ledger list contract is missing the open_form row rule');
  }
  const recordEntry = rowRule.target?.record_entry || {};
  if (
    recordEntry.model !== 'project.project'
    || recordEntry.record_id !== '${id}'
    || recordEntry.entry_intent !== 'open'
    || typeof recordEntry.model_write_authority !== 'boolean'
  ) {
    throw new Error(`project ledger row record_entry is incomplete: ${JSON.stringify(recordEntry)}`);
  }
}

async function renderViewport(browser, viewport) {
  const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height } });
  const page = await context.newPage();
  const consoleErrors = [];
  const pageErrors = [];
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  page.on('pageerror', (error) => pageErrors.push(String(error && error.message || error)));
  const token = await login(page);
  await page.goto(`${BASE_URL}/s/${SCENE_KEY}`, { waitUntil: 'networkidle' });
  await page.waitForFunction(() => {
    const text = String(document.body?.textContent || '');
    return !text.includes('正在加载场景') && !text.includes('正在加载页面');
  }, null, { timeout: 30000 });
  await page.waitForSelector(`[data-block-key="${METRIC_BLOCK_KEY}"]`, { timeout: 30000 });
  const result = await page.evaluate((metricBlockKey) => {
    const bodyText = String(document.body?.textContent || '');
    const metric = document.querySelector(`[data-block-key="${metricBlockKey}"]`);
    return {
      path: window.location.pathname,
      metricText: String(metric?.textContent || '').replace(/\s+/g, ' ').trim(),
      semanticRoot: Boolean(document.querySelector('[data-semantic-component="PageRenderer"]')),
      overflow: document.documentElement.scrollWidth > window.innerWidth + 1,
      bodyText,
    };
  }, METRIC_BLOCK_KEY);
  await page.screenshot({
    path: path.join(ARTIFACT_DIR, `company-dashboard-${viewport.width}.png`),
    fullPage: true,
  });
  const uiConsoleErrors = [...consoleErrors];
  const uiPageErrors = [...pageErrors];
  const matrix = await validateCompatMatrix(page, token);
  const contractV2Matrix = await validateContractV2Matrix(page, token);
  assertProjectLedgerRowNavigation(contractV2Matrix.current_26.body?.data);
  const projectLedgerForm = viewport.name === 'desktop'
    ? await captureProjectLedgerForm(page)
    : null;
  if (viewport.name === 'desktop') {
    fs.writeFileSync(
      path.join(ARTIFACT_DIR, 'ui-contract-v2-project-list.json'),
      `${JSON.stringify(contractV2Matrix.current_26.body.data, null, 2)}\n`,
      'utf8',
    );
    fs.writeFileSync(
      path.join(ARTIFACT_DIR, 'ui-contract-v2-project-form.json'),
      `${JSON.stringify(projectLedgerForm, null, 2)}\n`,
      'utf8',
    );
  }
  await context.close();
  return {
    viewport,
    result,
    matrix,
    contractV2Matrix,
    projectLedgerForm,
    consoleErrors: uiConsoleErrors,
    pageErrors: uiPageErrors,
  };
}

function assertCurrentProjection(label, payload) {
  if (payload.status !== 200 || payload.body?.ok !== true) {
    throw new Error(`${label}: request failed ${JSON.stringify(payload)}`);
  }
  const orchestration = payload.body.data.page_orchestration;
  if (orchestration.contract_version !== '2.1.0' || orchestration.schema_version !== '2.1.0') {
    throw new Error(`${label}: expected 2.1.0`);
  }
  if (orchestration.attachment_facts || orchestration.action_feedback) {
    throw new Error(`${label}: undeclared carrier leaked`);
  }
  return orchestration;
}

function assertCurrentDataPayload(label, payload) {
  const orchestration = assertCurrentProjection(label, payload);
  if (!orchestration.block_data_contracts?.[DATA_SOURCE_KEY]) {
    throw new Error(`${label}: missing company_projects page-block-data`);
  }
  const value = orchestration.block_data_contracts[DATA_SOURCE_KEY].rows[0].values.value;
  if (typeof value !== 'number') throw new Error(`${label}: company_projects raw value is not numeric`);
  if (orchestration.action_schema || orchestration.action_contract) {
    throw new Error(`${label}: undeclared page-block-action leaked`);
  }
}

function assertCurrentActionPayload(label, payload, expectData) {
  const orchestration = assertCurrentProjection(label, payload);
  const actions = orchestration.action_schema?.actions;
  if (orchestration.action_schema?.carrier !== 'page-block-action.v1' || !actions) {
    throw new Error(`${label}: missing page-block-action carrier`);
  }
  const projectAction = actions['action.open_company_projects'];
  if (!projectAction) throw new Error(`${label}: missing company-projects action`);
  if (projectAction.actionRuleRef !== projectAction.actionId) {
    throw new Error(`${label}: action rule reference mismatch`);
  }
  if (projectAction.target?.value?.action_xmlid !== 'smart_construction_core.action_sc_project_list') {
    throw new Error(`${label}: resolved action target was changed`);
  }
  if (projectAction.permission?.evaluated !== true) {
    throw new Error(`${label}: action permission was not evaluated`);
  }
  if (Boolean(orchestration.block_data_contracts) !== expectData) {
    throw new Error(`${label}: page-block-data capability mismatch`);
  }
}

function assertLegacyPayload(label, payload) {
  if (payload.status !== 200 || payload.body?.ok !== true) {
    throw new Error(`${label}: request failed ${JSON.stringify(payload)}`);
  }
  const orchestration = payload.body.data.page_orchestration;
  if (orchestration.contract_version !== '2.0.0' || orchestration.schema_version !== '2.0.0') {
    throw new Error(`${label}: expected complete 2.0.0 projection`);
  }
  if (
    orchestration.block_data_contracts
    || orchestration.block_field_descriptors
    || orchestration.action_schema
    || orchestration.action_contract
  ) {
    throw new Error(`${label}: new semantic carrier leaked`);
  }
}

function assertContractV2(label, payload, expectedVersion) {
  if (payload.status !== 200 || payload.body?.ok !== true) {
    throw new Error(`${label}: request failed ${JSON.stringify(payload)}`);
  }
  if (payload.body.data?.pageInfo?.contractVersion !== expectedVersion) {
    throw new Error(`${label}: expected Contract V2 ${expectedVersion}`);
  }
  if (payload.body.meta?.contract_negotiation?.contractVersion !== expectedVersion) {
    throw new Error(`${label}: negotiation metadata mismatch`);
  }
}

async function main() {
  ensureDir(ARTIFACT_DIR);
  const browser = await chromium.launch({ headless: true });
  try {
    const runs = [];
    for (const viewport of VIEWPORTS) {
      const run = await renderViewport(browser, viewport);
      assertCurrentDataPayload(`${viewport.name}.current_data`, run.matrix.current_page_block_data);
      assertCurrentActionPayload(
        `${viewport.name}.current_action`,
        run.matrix.current_page_block_action,
        false,
      );
      assertCurrentActionPayload(
        `${viewport.name}.current_data_and_action`,
        run.matrix.current_page_block_data_and_action,
        true,
      );
      assertLegacyPayload(`${viewport.name}.known_old_without_versions`, run.matrix.known_old_without_versions);
      assertLegacyPayload(
        `${viewport.name}.pre_negotiation_without_identity`,
        run.matrix.pre_negotiation_without_identity,
      );
      if (run.matrix.pre_negotiation_without_identity.body?.meta?.contract_negotiation?.clientType !== '') {
        throw new Error(`${viewport.name}: missing client identity was implicitly assigned`);
      }
      assertLegacyPayload(`${viewport.name}.legacy_25`, run.matrix.legacy_25);
      if (run.matrix.only_24.status === 200 && run.matrix.only_24.body?.ok !== false) {
        throw new Error(`${viewport.name}: 2.4-only client was upgraded to a supported version`);
      }
      if (
        (run.matrix.only_24.body?.error?.reason_code || run.matrix.only_24.body?.error?.reasonCode)
        !== 'CONTRACT_VERSION_UNSUPPORTED'
      ) {
        throw new Error(`${viewport.name}: 2.4-only client did not fail with CONTRACT_VERSION_UNSUPPORTED`);
      }
      assertLegacyPayload(`${viewport.name}.legacy_26_without_capability`, run.matrix.legacy_26_without_capability);
      if (run.matrix.no_common_version.status === 200 && run.matrix.no_common_version.body?.ok !== false) {
        throw new Error(`${viewport.name}: no common version did not fail closed`);
      }
      if (
        run.matrix.unknown_client_without_versions.status === 200
        && run.matrix.unknown_client_without_versions.body?.ok !== false
      ) {
        throw new Error(`${viewport.name}: unknown client did not fail closed`);
      }
      assertContractV2(`${viewport.name}.contract_v2_legacy`, run.contractV2Matrix.legacy_26_without_capability, '2.5.0');
      assertContractV2(`${viewport.name}.contract_v2_current`, run.contractV2Matrix.current_26, '2.6.0');
      if (!run.result.semanticRoot) throw new Error(`${viewport.name}: PageRenderer missing`);
      if (!/项目规模/.test(run.result.metricText)) throw new Error(`${viewport.name}: company_projects not rendered`);
      if (run.result.overflow) throw new Error(`${viewport.name}: horizontal overflow`);
      if (run.consoleErrors.length || run.pageErrors.length) {
        throw new Error(`${viewport.name}: browser errors ${JSON.stringify({
          consoleErrors: run.consoleErrors,
          pageErrors: run.pageErrors,
        })}`);
      }
      runs.push(run);
    }
    const report = {
      ok: true,
      base_url: BASE_URL,
      login: LOGIN,
      runs: runs.map((run) => ({
        viewport: run.viewport,
        path: run.result.path,
        metric_text: run.result.metricText,
        semantic_root: run.result.semanticRoot,
        overflow: run.result.overflow,
        compatibility: Object.fromEntries(Object.entries(run.matrix).map(([key, value]) => [
          key,
          {
            status: value.status,
            ok: value.body?.ok,
            contract_version: value.body?.data?.page_orchestration?.contract_version,
            reason_code: value.body?.error?.reason_code || value.body?.error?.reasonCode || '',
            client_type: value.body?.meta?.contract_negotiation?.clientType,
          },
        ])),
        contract_v2: Object.fromEntries(Object.entries(run.contractV2Matrix).map(([key, value]) => [
          key,
          {
            status: value.status,
            ok: value.body?.ok,
            contract_version: value.body?.data?.pageInfo?.contractVersion,
            negotiation_version: value.body?.meta?.contract_negotiation?.contractVersion,
          },
        ])),
        project_ledger_form: run.projectLedgerForm ? {
          action_rules: run.projectLedgerForm.actionContract?.actionRuleList?.length || 0,
          layout_contract_present: Boolean(run.projectLedgerForm.layoutContract),
        } : null,
        action_carrier: (() => {
          const orchestration = run.matrix.current_page_block_action.body?.data?.page_orchestration;
          const schema = orchestration?.action_schema;
          return {
            contract_version: orchestration?.contract_version,
            carrier: schema?.carrier,
            actions: Object.values(schema?.actions || {}).map((action) => ({
              action_id: action.actionId,
              action_rule_ref: action.actionRuleRef,
              action_key: action.actionKey,
              action_xmlid: action.target?.value?.action_xmlid,
              authorization_allowed: action.permission?.authorizationAllowed,
              business_available: action.permission?.businessAvailable,
              enabled: action.state?.enabled,
              reason_code: action.state?.reasonCode,
            })),
          };
        })(),
        console_errors: run.consoleErrors,
        page_errors: run.pageErrors,
      })),
    };
    fs.writeFileSync(REPORT_PATH, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
    process.stdout.write(`P0_A_BROWSER_ACCEPTANCE=PASS report=${REPORT_PATH}\n`);
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  ensureDir(ARTIFACT_DIR);
  fs.writeFileSync(path.join(ARTIFACT_DIR, 'p0a_browser_acceptance_failure.json'), `${JSON.stringify({
    ok: false,
    error: String(error && error.stack || error),
  }, null, 2)}\n`, 'utf8');
  process.stderr.write(`${String(error && error.stack || error)}\n`);
  process.exitCode = 1;
});
