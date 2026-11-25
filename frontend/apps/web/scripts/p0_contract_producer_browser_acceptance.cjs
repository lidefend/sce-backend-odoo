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
    accepted_contract_versions: ['2.7.x'],
    client_contract_capabilities: [],
  };
  const cases = {
    current_base: base,
    missing_versions: {
      client_type: 'web_pc',
    },
    pre_v27: {
      ...base,
      accepted_contract_versions: ['2.6.x'],
    },
    current_page_block_data: {
      ...base,
      client_contract_capabilities: ['page_block_data.v1'],
    },
    current_page_block_action: {
      ...base,
      client_contract_capabilities: ['page_block_action.v1'],
    },
    current_page_block_data_and_action: {
      ...base,
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
    accepted_contract_versions: ['2.7.x'],
    client_contract_capabilities: [
      'container_tree.v2',
      'data_source.v2',
      'action_rule.v2',
      'relation_entry.v2',
      'status_contract.v2',
      'form_layout.children_owner.v1',
    ],
  };
  return {
    current_v27: await requestIntent(page, 'ui.contract.v2', base, token),
    rejected_pre_v27: await requestIntent(page, 'ui.contract.v2', {
      ...base,
      accepted_contract_versions: ['2.6.x'],
    }, token),
  };
}

function requestParams(response) {
  try {
    return JSON.parse(response.request().postData() || '{}').params || {};
  } catch {
    return {};
  }
}

function contractDescriptor(contract, fieldCode) {
  let found = null;
  const visit = (value) => {
    if (found || !value || typeof value !== 'object') return;
    if (Array.isArray(value)) {
      value.forEach(visit);
      return;
    }
    const descriptor = value.fieldDescriptor;
    if (descriptor && typeof descriptor === 'object' && descriptor.fieldCode === fieldCode) {
      found = descriptor;
      return;
    }
    Object.values(value).forEach(visit);
  };
  visit(contract);
  return found;
}

async function captureProjectLedgerContracts(page, viewport) {
  const listResponsePromise = page.waitForResponse((response) => {
    if (!response.url().includes('/api/v1/intent')) return false;
    try {
      const payload = JSON.parse(response.request().postData() || '{}');
      const params = payload.params || {};
      return (
        payload.intent === 'ui.contract.v2'
        && params.op === 'action_open'
        && params.action_id
        && !params.record_id
      );
    } catch {
      return false;
    }
  }, { timeout: 30000 });
  await page.goto(`${BASE_URL}/s/projects.ledger`, {
    waitUntil: 'domcontentloaded',
    timeout: 30000,
  });
  const listResponse = await listResponsePromise;
  const listBody = await listResponse.json();
  if (!listResponse.ok() || listBody?.ok !== true || !listBody?.data) {
    throw new Error(`project ledger list contract failed: ${JSON.stringify({
      status: listResponse.status(),
      ok: listBody?.ok,
      code: listBody?.error?.code || '',
    })}`);
  }
  const listParams = requestParams(listResponse);
  const listScreenshot = path.join(
    ARTIFACT_DIR,
    `project-ledger-list-v27-${viewport.name}.png`,
  );
  await page.screenshot({ path: listScreenshot, fullPage: true });
  const row = page.locator(
    'button[data-semantic-cell-kind="primary"]:visible, button[data-semantic-action="open-record"]:visible',
  ).first();
  await row.waitFor({ state: 'visible', timeout: 30000 });
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
  const formParams = requestParams(response);
  const formRoot = page.locator('[data-semantic-component="ContractFormPage"]:visible').first();
  await formRoot.waitFor({ state: 'visible', timeout: 30000 });
  await page.waitForFunction(() => {
    const root = document.querySelector('[data-semantic-component="ContractFormPage"]');
    return root && !['loading', 'error'].includes(String(root.getAttribute('data-state') || ''));
  }, null, { timeout: 30000 });
  const formState = await formRoot.evaluate((element) => ({
    state: element.getAttribute('data-state') || '',
    model: element.getAttribute('data-form-model') || '',
    record: element.getAttribute('data-form-record') || '',
    action: element.getAttribute('data-form-action-id') || '',
    menu: element.getAttribute('data-form-menu-id') || '',
  }));
  const fieldChecks = await page.evaluate(() => {
    const inspect = (fieldName) => {
      const container = document.querySelector(`[data-field-name="${CSS.escape(fieldName)}"]`);
      if (!container) return null;
      const control = container.querySelector('input, textarea, select');
      return {
        state: container.getAttribute('data-field-state') || '',
        type: container.getAttribute('data-field-type') || '',
        controlType: control?.getAttribute('type') || '',
        readOnly: control instanceof HTMLInputElement || control instanceof HTMLTextAreaElement
          ? control.readOnly
          : false,
      };
    };
    return {
      project_code: inspect('project_code'),
      date_start: inspect('date_start'),
      manager_id: inspect('manager_id'),
    };
  });
  const screenshot = path.join(
    ARTIFACT_DIR,
    `project-ledger-form-v27-${viewport.name}.png`,
  );
  await page.screenshot({ path: screenshot, fullPage: true });
  return {
    form: body.data,
    list: listBody.data,
    formState,
    fieldChecks,
    listParams,
    formParams,
    listScreenshot,
    screenshot,
  };
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

function assertSemanticContractOnly(contract) {
  const forbidden = [];
  const opaqueValueKeys = new Set([
    'dataContract', 'dataPatch', 'dataMeta', 'mainData', 'datasets',
    'payload', 'actionPayload', 'context', 'domain', 'options', 'optionsRaw',
    'values', 'value', 'value_json', 'valueJson', 'default_vals',
  ]);
  const visit = (value, path = '$') => {
    if (Array.isArray(value)) {
      value.forEach((item, index) => visit(item, `${path}[${index}]`));
      return;
    }
    if (!value || typeof value !== 'object') return;
    Object.entries(value).forEach(([key, child]) => {
      const here = `${path}.${key}`;
      if (key === 'componentKey' || key === 'component_key' || key === 'componentRegistry') {
        forbidden.push(here);
        return;
      }
      if (opaqueValueKeys.has(key)) return;
      visit(child, here);
    });
  };
  visit(contract);
  if (forbidden.length) {
    throw new Error(`V2.7 form contract leaked frontend implementation identity: ${JSON.stringify(forbidden)}`);
  }
}

function assertProjectLedgerJourney(label, captured) {
  const model = String(captured.form?.pageInfo?.model || '');
  const recordId = Number(captured.formParams?.record_id || 0);
  const actionId = String(captured.formParams?.action_id || '');
  const menuId = String(captured.formParams?.menu_id || '');
  if (!recordId || !actionId || !menuId) {
    throw new Error(`${label}: Form request is missing record/action/menu identity`);
  }
  if (
    captured.formState.state !== 'ok'
    || captured.formState.model !== model
    || captured.formState.record !== String(recordId)
    || captured.formState.action !== actionId
    || captured.formState.menu !== menuId
  ) {
    throw new Error(`${label}: Form runtime identity mismatch ${JSON.stringify({
      formState: captured.formState,
      expected: { state: 'ok', model, record: String(recordId), action: actionId, menu: menuId },
    })}`);
  }
  if (String(captured.listParams?.action_id || '') !== actionId) {
    throw new Error(`${label}: list and Form action identity differ`);
  }
  const code = contractDescriptor(captured.form, 'project_code');
  const date = contractDescriptor(captured.form, 'date_start');
  const manager = contractDescriptor(captured.form, 'manager_id');
  if (code?.semanticType !== 'text' || code?.readonly !== true) {
    throw new Error(`${label}: project_code contract semantics are incomplete`);
  }
  if (date?.semanticType !== 'date') {
    throw new Error(`${label}: date_start date semantic is missing`);
  }
  if (manager?.semanticType !== 'relation' || manager?.relationEntry?.can_read !== true) {
    throw new Error(`${label}: manager_id relation semantics are incomplete`);
  }
  if (
    captured.fieldChecks.project_code?.state !== 'readonly'
    || captured.fieldChecks.date_start?.type !== 'date'
    || captured.fieldChecks.manager_id?.type !== 'many2one'
  ) {
    throw new Error(`${label}: rendered representative field semantics mismatch ${JSON.stringify(
      captured.fieldChecks,
    )}`);
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
  page.on('pageerror', (error) => pageErrors.push({
    message: String(error && error.message || error),
    stack: String(error && error.stack || ''),
    path: String(page.url() || ''),
  }));
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
  const matrix = await validateCompatMatrix(page, token);
  const contractV2Matrix = await validateContractV2Matrix(page, token);
  const projectLedgerContracts = await captureProjectLedgerContracts(page, viewport);
  assertProjectLedgerRowNavigation(projectLedgerContracts.list);
  assertSemanticContractOnly(projectLedgerContracts.form);
  assertProjectLedgerJourney(`${viewport.name}.projects.ledger`, projectLedgerContracts);
  const uiConsoleErrors = [...consoleErrors];
  const uiPageErrors = [...pageErrors];
  fs.writeFileSync(
    path.join(ARTIFACT_DIR, `ui-contract-v2-project-list-${viewport.name}.json`),
    `${JSON.stringify(projectLedgerContracts.list, null, 2)}\n`,
    'utf8',
  );
  fs.writeFileSync(
    path.join(ARTIFACT_DIR, `ui-contract-v2-project-form-${viewport.name}.json`),
    `${JSON.stringify(projectLedgerContracts.form, null, 2)}\n`,
    'utf8',
  );
  await context.close();
  return {
    viewport,
    result,
    matrix,
    contractV2Matrix,
    projectLedgerForm: projectLedgerContracts.form,
    projectLedgerContracts,
    consoleErrors: uiConsoleErrors,
    pageErrors: uiPageErrors,
  };
}

function assertCurrentProjection(label, payload, expectedOrchestrationVersion = '2.1.0') {
  if (payload.status !== 200 || payload.body?.ok !== true) {
    throw new Error(`${label}: request failed ${JSON.stringify(payload)}`);
  }
  const orchestration = payload.body.data.page_orchestration;
  if (
    orchestration.contract_version !== expectedOrchestrationVersion
    || orchestration.schema_version !== expectedOrchestrationVersion
  ) {
    throw new Error(`${label}: expected ${expectedOrchestrationVersion}, got ${JSON.stringify({
      contract_version: orchestration.contract_version,
      schema_version: orchestration.schema_version,
    })}`);
  }
  if (orchestration.attachment_facts || orchestration.action_feedback) {
    throw new Error(`${label}: undeclared carrier leaked`);
  }
  return orchestration;
}

function assertCurrentBasePayload(label, payload) {
  const orchestration = assertCurrentProjection(label, payload, '2.0.0');
  if (orchestration.block_data_contracts || orchestration.action_schema || orchestration.action_contract) {
    throw new Error(`${label}: undeclared optional carriers leaked without capability`);
  }
  if (payload.body?.meta?.contract_negotiation?.contractVersion !== '2.7.0') {
    throw new Error(`${label}: runtime negotiation did not bind Contract V2.7`);
  }
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

function assertUnsupportedPayload(label, payload, expectedReason) {
  if (payload.status === 200 && payload.body?.ok !== false) {
    throw new Error(`${label}: unsupported request unexpectedly succeeded`);
  }
  const reasonCode = payload.body?.error?.reason_code || payload.body?.error?.reasonCode || '';
  if (reasonCode !== expectedReason) {
    throw new Error(`${label}: expected ${expectedReason}, got ${reasonCode || '<missing>'}`);
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
      assertCurrentBasePayload(`${viewport.name}.current_base`, run.matrix.current_base);
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
      for (const key of ['missing_versions', 'pre_v27', 'no_common_version', 'unknown_client_without_versions']) {
        assertUnsupportedPayload(
          `${viewport.name}.${key}`,
          run.matrix[key],
          'CONTRACT_VERSION_UNSUPPORTED',
        );
      }
      assertContractV2(`${viewport.name}.contract_v2_current`, run.contractV2Matrix.current_v27, '2.7.0');
      assertUnsupportedPayload(
        `${viewport.name}.contract_v2_pre_v27`,
        run.contractV2Matrix.rejected_pre_v27,
        'CONTRACT_VERSION_UNSUPPORTED',
      );
      if (!run.result.semanticRoot) throw new Error(`${viewport.name}: PageRenderer missing`);
      if (!/项目规模/.test(run.result.metricText)) throw new Error(`${viewport.name}: company_projects not rendered`);
      if (run.result.overflow) throw new Error(`${viewport.name}: horizontal overflow`);
      const unexpectedConsoleErrors = run.consoleErrors.filter((message) => !(
        /Failed to load resource: the server responded with a status of 409 \(CONFLICT\)/.test(message)
      ));
      if (unexpectedConsoleErrors.length || run.pageErrors.length) {
        throw new Error(`${viewport.name}: browser errors ${JSON.stringify({
          consoleErrors: unexpectedConsoleErrors,
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
          runtime_state: run.projectLedgerContracts.formState,
          clicked_record_id: Number(run.projectLedgerContracts.formParams.record_id || 0),
          action_id: run.projectLedgerContracts.formParams.action_id,
          menu_id: run.projectLedgerContracts.formParams.menu_id,
          screenshots: {
            list: run.projectLedgerContracts.listScreenshot,
            form: run.projectLedgerContracts.screenshot,
          },
          field_checks: run.projectLedgerContracts.fieldChecks,
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
