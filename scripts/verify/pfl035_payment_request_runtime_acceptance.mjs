#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';

const BASE_URL = process.env.FRONTEND_URL || 'http://127.0.0.1:5193';
const RUNTIME_TARGETS = JSON.parse(process.env.PFL035_RUNTIME_TARGETS_JSON || '{}');
const DB_NAME = process.env.DB_NAME || RUNTIME_TARGETS.database || '';
const PASSWORD = process.env.SC_ACCEPTANCE_PFL035_PASSWORD || '';
const SOURCE_SHA = process.env.SOURCE_SHA || '';
const DIRTY_DIFF_SHA256 = process.env.DIRTY_DIFF_SHA256 || '';
const ACTION_ID = Number(process.env.ACTION_ID || RUNTIME_TARGETS.action?.id || 0);
const MENU_ID = Number(process.env.MENU_ID || RUNTIME_TARGETS.menu?.id || 0);
const IDS = {
  approved: Number(process.env.APPROVED_REQUEST_ID || RUNTIME_TARGETS.records?.approved?.id || 0),
  draft: Number(process.env.DRAFT_REQUEST_ID || RUNTIME_TARGETS.records?.draft?.id || 0),
  receive: Number(process.env.RECEIVE_REQUEST_ID || RUNTIME_TARGETS.records?.receive?.id || 0),
  incomplete: Number(process.env.INCOMPLETE_REQUEST_ID || RUNTIME_TARGETS.records?.incomplete?.id || 0),
};
const LOGINS = {
  manager: process.env.FINANCE_MANAGER_LOGIN || RUNTIME_TARGETS.users?.manager?.login || '',
  user: process.env.FINANCE_USER_LOGIN || RUNTIME_TARGETS.users?.user?.login || '',
  empty: process.env.EMPTY_FINANCE_LOGIN || RUNTIME_TARGETS.users?.empty?.login || '',
  forbidden: process.env.FORBIDDEN_LOGIN || RUNTIME_TARGETS.users?.forbidden?.login || '',
};
const COMPANY = process.env.COMPANY_NAME || RUNTIME_TARGETS.company?.name || '';
const CREATE_JOURNEY = RUNTIME_TARGETS.journey?.settlement || {};
const OUTPUT_DIR = process.env.ARTIFACTS_DIR || 'artifacts/playwright/pfl035-payment-request-runtime/latest';
const FIELD_MATRIX_PATH = path.resolve('config/p1_payment_request_field_completeness_v1.json');
const FIELD_MATRIX = JSON.parse(fs.readFileSync(FIELD_MATRIX_PATH, 'utf8'));

for (const [name, value] of Object.entries({ DB_NAME, PASSWORD, SOURCE_SHA, ACTION_ID, MENU_ID, COMPANY, ...IDS, ...LOGINS, create_journey_settlement: CREATE_JOURNEY.id })) {
  if (!value) throw new Error(`missing required acceptance input: ${name}`);
}
fs.mkdirSync(OUTPUT_DIR, { recursive: true });

const result = {
  schema: 'pfl035.payment_request.runtime_acceptance.v1',
  pass: false,
  generated_at: new Date().toISOString(),
  source: { head_sha: SOURCE_SHA, dirty_diff_sha256: DIRTY_DIFF_SHA256 },
  runtime: {
    database: DB_NAME,
    frontend_url: BASE_URL,
    company: COMPANY,
    action: { xmlid: 'smart_construction_core.action_payment_request_user_payment_apply', id: ACTION_ID },
    menu: { xmlid: 'smart_construction_core.menu_sc_user_payment_apply', id: MENU_ID },
  },
  roles: LOGINS,
  records: IDS,
  states: [],
  business_paths: [],
  screenshots: [],
  console_errors: [],
  expected_console_errors: [],
  unexpected_console_errors: [],
  failed_requests: [],
  unexpected_failed_requests: [],
  assertions: [],
  normalized_action_evidence: [],
  normalized_product_fact_evidence: [],
  field_completeness: {
    schema: FIELD_MATRIX.schema_version,
    benchmark_dimensions: FIELD_MATRIX.industry_benchmarks?.dimensions?.map((row) => ({ key: row.key, status: row.status })) || [],
    journey_coverage: FIELD_MATRIX.journey_gates?.map((row) => ({ key: row.key, status: row.coverage_status })) || [],
    surfaces: [],
  },
  environment_noise: [
    'Odoo mail installation emitted docutils formatting warnings: unexpected indentation / block quote blank-line / title underline length.',
    'Node emitted DEP0169 for url.parse() while restoring the lockfile-pinned offline dependencies.',
  ],
};

function check(condition, assertion, facts = {}) {
  result.assertions.push({ assertion, pass: Boolean(condition), ...facts });
  if (!condition) throw new Error(assertion);
}

function clean(value) {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

function attachDiagnostics(page, role) {
  page.on('console', (message) => {
    if (message.type() !== 'error') return;
    const text = message.text();
    if (/favicon|ResizeObserver/i.test(text)) return;
    result.console_errors.push({ role, url: page.url(), text });
  });
  page.on('pageerror', (error) => {
    result.console_errors.push({ role, url: page.url(), text: error.message });
  });
  page.on('response', async (response) => {
    const request = response.request();
    let payload = {};
    try { payload = JSON.parse(request.postData() || '{}'); } catch {}
    if (response.status() < 400 && payload?.intent === 'ui.contract.v2') {
      try {
        const body = await response.json();
        const contract = body?.data || body?.result?.data || body?.result || {};
        const rules = contract?.actionContract?.actionRuleList || [];
        const factNames = new Set([
          'payment_flow_label',
          'payee_account_completeness',
          'payee_account_source_display',
          'payment_execution_status_display',
          'payment_blocking_reason_display',
          'legal_next_action_display',
        ]);
        const factOccurrences = [];
        const relevantContractFragments = [];
        const allFieldNames = new Set();
        const layoutFieldNames = new Set();
        const visitLayoutFields = (value) => {
          if (!value || typeof value !== 'object') return;
          if (!Array.isArray(value)) {
            const fieldName = String(value.name || value.field || value.fieldName || value.fieldCode || '');
            if (fieldName) layoutFieldNames.add(fieldName);
          }
          for (const nested of Object.values(value)) {
            if (nested && typeof nested === 'object') visitLayoutFields(nested);
          }
        };
        visitLayoutFields(contract?.layoutContract?.containerTree || []);
        const visitFacts = (value, pathParts = []) => {
          if (!value || typeof value !== 'object' || pathParts.length > 14) return;
          const declaredFieldName = !Array.isArray(value) ? String(value.name || value.field || value.fieldName || value.fieldCode || '') : '';
          if (!Array.isArray(value) && Object.values(value).some((item) => typeof item === 'string' && factNames.has(item))) {
            relevantContractFragments.push({
              path: pathParts.join('.'),
              values: Object.fromEntries(Object.entries(value).filter(([, item]) => (
                item === null || ['string', 'number', 'boolean'].includes(typeof item)
              ))),
              component_config: value.componentConfig || value.component_config || null,
            });
          }
          if (declaredFieldName) allFieldNames.add(declaredFieldName);
          if (!Array.isArray(value) && factNames.has(declaredFieldName)) {
            factOccurrences.push({
              path: pathParts.join('.'),
              name: String(value.name || value.field || value.fieldName || ''),
              label: clean(value.label || value.string || value.title),
              value: typeof value.value === 'object' ? '[structured]' : value.value,
              visible: value.visible,
              readonly: value.readonly,
              optional: value.optional,
              invisible: value.invisible,
              component_config: value.componentConfig || value.component_config || null,
              status: value.status || value.buttonStatus || null,
            });
          }
          for (const [key, nested] of Object.entries(value)) {
            if (factNames.has(key)) {
              factOccurrences.push({
                path: [...pathParts, key].join('.'),
                name: key,
                value: typeof nested === 'object' ? '[structured]' : nested,
              });
            }
            if (nested && typeof nested === 'object') visitFacts(nested, [...pathParts, key]);
          }
        };
        visitFacts(contract);
        const contractModel = String(
          payload?.params?.model
          || payload?.params?.res_model
          || contract?.pageInfo?.model
          || '',
        );
        result.normalized_product_fact_evidence.push({
          role,
          model: contractModel,
          record_id: Number(payload?.params?.record_id || payload?.params?.res_id || 0) || null,
          request_params: Object.fromEntries(
            Object.entries(payload?.params || {}).filter(([key]) => [
              'source_type', 'action_id', 'menu_id', 'model', 'res_model', 'view_type',
              'record_id', 'res_id', 'render_profile', 'profile', 'client_type',
            ].includes(key)),
          ),
          contract_keys: Object.keys(contract).sort(),
          list_profile: contract?.layoutContract?.listProfile || null,
          field_names: [...allFieldNames].sort(),
          layout_field_names: [...layoutFieldNames].sort(),
          applicability: {
            type: String(contract?.dataContract?.mainData?.type || ''),
            state: String(contract?.dataContract?.mainData?.state || ''),
            eligibility: String(contract?.dataContract?.mainData?.partner_transaction_eligibility || ''),
            basis: String(contract?.dataContract?.mainData?.payment_basis_type || ''),
            partner_selected: Boolean(contract?.dataContract?.mainData?.partner_id),
            contract_selected: Boolean(contract?.dataContract?.mainData?.contract_id),
            settlement_selected: Boolean(contract?.dataContract?.mainData?.settlement_id),
            material_settlement_selected: Boolean(contract?.dataContract?.mainData?.material_settlement_id),
          },
          layout_outline: (contract?.layoutContract?.containerTree || []).map((row) => ({
            type: row?.type,
            title: clean(row?.string || row?.label || row?.name),
            fields: (row?.children || []).map((child) => clean(child?.name || child?.field || child?.fieldName)).filter(Boolean),
          })),
          facts: factOccurrences,
          relevant_contract_fragments: relevantContractFragments,
        });
        result.normalized_action_evidence.push({
          role,
          model: contractModel,
          record_id: Number(payload?.params?.record_id || payload?.params?.res_id || 0) || null,
          actions: rules.map((row) => ({
            actionKey: row?.actionKey,
            backendIdentity: row?.backendIdentity,
            label: row?.label || row?.button?.label,
            allowed: row?.allowed,
            enabled: row?.enabled,
            disabled: row?.disabled,
            presentation: row?.presentation,
            presentationTier: row?.presentationTier,
            semantic: row?.semantic,
            visibleProfiles: row?.visibleProfiles,
            sourceTrace: row?.sourceTrace,
          })),
        });
      } catch {}
      return;
    }
    if (response.status() < 400) return;
    const recordId = Number(payload?.params?.res_id || payload?.params?.record_id || 0);
    const expected = payload?.intent === 'execute_button'
      && [IDS.draft, IDS.receive, IDS.incomplete, IDS.approved].includes(recordId);
    let responseReason = '';
    try {
      const body = await response.json();
      responseReason = clean(
        body?.error?.reason_code || body?.error?.code || body?.error?.message
        || body?.data?.reason_code || body?.data?.message || '',
      );
    } catch {}
    const row = {
      role,
      status: response.status(),
      url: response.url(),
      method: request.method(),
      intent: String(payload?.intent || ''),
      record_id: recordId || null,
      op: clean(payload?.params?.op),
      model: clean(payload?.params?.model || payload?.params?.res_model),
      fields: Array.isArray(payload?.params?.fields) ? payload.params.fields.map(clean) : [],
      reason: responseReason,
      expected,
    };
    result.failed_requests.push(row);
    if (!expected) result.unexpected_failed_requests.push(row);
  });
}

async function login(page, loginName, role) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const inputs = page.locator('input');
  await inputs.nth(0).fill(loginName);
  await inputs.nth(1).fill(PASSWORD);
  if (await inputs.nth(2).isEnabled()) {
    await inputs.nth(2).fill(DB_NAME);
  } else {
    check(await inputs.nth(2).inputValue() === DB_NAME, `${role}: locked database must equal acceptance database`);
  }
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45000 });
  await page.locator('.layout-shell').waitFor({ timeout: 45000 });
}

async function intent(page, intentName, params, traceSuffix = '') {
  const token = await page.evaluate((database) => sessionStorage.getItem(`sc_auth_token:${database}`) || '', DB_NAME);
  return page.evaluate(async ({ database, bearer, intentName: name, payload, traceSuffix: suffix }) => {
    const response = await fetch(`/api/v1/intent?db=${encodeURIComponent(database)}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: bearer ? `Bearer ${bearer}` : '',
        'X-Trace-Id': `pfl035-${suffix || name}-${Date.now()}`,
      },
      body: JSON.stringify({ intent: name, params: payload }),
    });
    const body = await response.json().catch(() => ({}));
    return { status: response.status, body, data: body?.data || body?.result || {} };
  }, { database: DB_NAME, bearer: token, intentName, payload: params, traceSuffix });
}

async function waitForStablePage(page, mode) {
  await page.locator('.layout-shell').waitFor({ timeout: 45000 });
  if (mode) await page.locator(`[data-product-page-mode="${mode}"]`).first().waitFor({ timeout: 45000 });
  if (mode === 'list') {
    await page.waitForFunction(() => {
      const visibleSurfaces = [...document.querySelectorAll('[data-product-page-mode="list"]')]
        .filter((node) => {
          const style = window.getComputedStyle(node);
          return style.display !== 'none' && style.visibility !== 'hidden';
        });
      return visibleSurfaces.length > 0
        && visibleSurfaces.every((node) => node.getAttribute('data-list-status') !== 'loading');
    }, null, { timeout: 45000 });
  }
  await page.waitForFunction(() => !/正在加载列表|正在加载页面|正在加载记录|正在载入数据|加载中/.test(document.body?.innerText || ''), null, { timeout: 45000 });
  await page.waitForTimeout(400);
}

async function surface(page) {
  return page.evaluate(() => {
    const text = (node) => String(node?.textContent || '').replace(/\s+/g, ' ').trim();
    const root = document.documentElement;
    const selectedCompanies = [
      ...[...document.querySelectorAll('label.business-scope-field select')]
        .map((select) => select.selectedOptions?.[0]?.textContent?.trim() || ''),
      ...[...document.querySelectorAll('.topbar-scope-label')]
        .map((node) => node.textContent?.trim() || ''),
    ].filter(Boolean);
    return {
      url: window.location.href,
      viewport: { width: window.innerWidth, height: window.innerHeight },
      document_width: { client: root.clientWidth, scroll: root.scrollWidth, overflow: Math.max(0, root.scrollWidth - root.clientWidth) },
      product_modes: [...document.querySelectorAll('[data-product-page-mode]')].map((node) => node.getAttribute('data-product-page-mode')),
      headings: [...document.querySelectorAll('h1,h2,h3')].map(text).filter(Boolean).slice(0, 20),
      buttons: [...document.querySelectorAll('button')].filter((node) => node.offsetParent !== null).map(text).filter(Boolean).slice(0, 60),
      selected_companies: selectedCompanies,
      shell_context: text(document.querySelector('.sidebar .brand .subtitle')),
      body_sample: text(document.body).slice(0, 2000),
      table_headers: [...document.querySelectorAll('thead th')].map(text).filter(Boolean),
      table_rows: document.querySelectorAll('tbody tr').length,
      list_visible_columns: document.querySelector('[data-visible-columns]')?.getAttribute('data-visible-columns') || '',
      list_column_decision_trace: (() => {
        const raw = document.querySelector('[data-column-decision-trace]')?.getAttribute('data-column-decision-trace') || '';
        try { return raw ? JSON.parse(raw) : null; } catch { return { malformed: raw }; }
      })(),
      form_inputs: document.querySelectorAll('input:not([type="hidden"]), textarea, select').length,
    };
  });
}

function fieldRuleApplies(row, applicability = {}) {
  const rule = String(row.applicability || 'always');
  if (rule === 'always') return true;
  if (rule === 'type_pay') return applicability.type === 'pay';
  if (rule === 'type_receive') return applicability.type === 'receive';
  if (rule === 'partner_selected') return applicability.partner_selected;
  if (rule === 'eligibility_not_eligible') return applicability.partner_selected && applicability.eligibility !== 'eligible';
  if (rule === 'contract_selected') return applicability.contract_selected;
  if (rule === 'settlement_selected' || rule === 'basis_settlement') return applicability.settlement_selected;
  if (rule === 'basis_contract_or_settlement') return applicability.contract_selected || applicability.settlement_selected;
  if (rule === 'basis_material_settlement') return applicability.material_settlement_selected;
  if (rule === 'state_rejected') return applicability.state === 'rejected';
  if (rule === 'policy_or_exception_requires_evidence') return false;
  return false;
}

function requiredSurfaceFields(model, surfaceName, applicability) {
  return (FIELD_MATRIX.field_rules || [])
    .filter((row) => (
      row.model === model
      && (row.surfaces || []).includes(surfaceName)
      && fieldRuleApplies(row, applicability)
    ))
    .map((row) => row.field);
}

function assertNormalizedFieldSurface(model, recordId, surfaceName) {
  const candidates = result.normalized_product_fact_evidence.filter((row) => (
    row.model === model && (recordId === null || Number(row.record_id || 0) === Number(recordId || 0))
  ));
  const applicability = candidates.find((row) => row.applicability)?.applicability || {};
  const observed = new Set(candidates.flatMap((row) => row.layout_field_names || []));
  const required = requiredSurfaceFields(model, surfaceName, applicability);
  const missing = required.filter((field) => !observed.has(field));
  const evidence = { model, record_id: recordId, surface: surfaceName, applicability, required, observed: [...observed].sort(), missing };
  result.field_completeness.surfaces.push(evidence);
  check(missing.length === 0, `${surfaceName}: normalized field completeness missing`, evidence);
}

async function shot(page, name) {
  const target = path.join(OUTPUT_DIR, `${name}.png`);
  await page.screenshot({ path: target, fullPage: true });
  result.screenshots.push({ name, path: target, url: page.url(), viewport: page.viewportSize() });
}

async function clickAuthoritativeObjectAction(page, methodName, evidenceName) {
  const button = page.locator(`button[data-backend-identity="button:object:${methodName}"]:visible`);
  check(await button.count() === 1, `${evidenceName}: expected one authoritative action`, { method: methodName });
  await button.click();
  const dialog = page.getByRole('dialog');
  const visible = await dialog.first().waitFor({ state: 'visible', timeout: 2500 }).then(() => true).catch(() => false);
  if (visible) {
    const confirm = dialog.getByRole('button', { name: /^确认/ }).last();
    await confirm.waitFor({ state: 'visible', timeout: 10000 });
    await confirm.click();
  }
  await waitForStablePage(page, 'form');
}

async function captureState(page, spec) {
  await page.goto(`${BASE_URL}${spec.route}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  if (spec.mode) await waitForStablePage(page, spec.mode);
  else await page.waitForTimeout(1000);
  const facts = await surface(page);
  await shot(page, spec.name);
  result.states.push({ name: spec.name, role: spec.role, expected_route: spec.route, ...facts });
  check(facts.document_width.overflow === 0, `${spec.name}: horizontal overflow must be zero`, facts.document_width);
  const actualPath = new URL(facts.url).pathname;
  const expectedPaths = Array.isArray(spec.expectedPath) ? spec.expectedPath : [spec.expectedPath];
  check(expectedPaths.includes(actualPath) || (spec.allowDenied && /access-denied/.test(actualPath)), `${spec.name}: fixed route mismatch`, { url: facts.url, expected_paths: expectedPaths });
  if (!spec.allowDenied) check(
    facts.selected_companies.includes(COMPANY) || facts.shell_context.includes(COMPANY),
    `${spec.name}: fixed company mismatch`,
    { selected: facts.selected_companies, shell_context: facts.shell_context },
  );
  return facts;
}

async function rejectPath(page, role, recordId, name, messagePattern, productPattern = null) {
  const route = `/r/payment.request/${recordId}?action_id=${ACTION_ID}&menu_id=${MENU_ID}`;
  await page.goto(`${BASE_URL}${route}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await waitForStablePage(page, 'form');
  const facts = await surface(page);
  if (productPattern) {
    check(productPattern.test(facts.body_sample), `${name}: product blocking guidance missing`, { sample: facts.body_sample });
  }
  await shot(page, `reject-${name}`);
  const response = await intent(page, 'execute_button', {
    model: 'payment.request',
    res_id: recordId,
    button: { name: 'action_create_payment_execution', type: 'object' },
  }, `reject-${name}`);
  const message = clean(response.body?.error?.message || response.body?.message || response.data?.message);
  const pass = response.status >= 400 && messagePattern.test(message);
  result.business_paths.push({ name, role, record_id: recordId, expected: 'rejected', status: response.status, message, pass });
  check(pass, `${name}: authoritative rejection mismatch`, { status: response.status, message });
}

async function requestCreateSaveReopenJourney(browser, page) {
  const settlementRoute = `/r/sc.settlement.order/${CREATE_JOURNEY.id}?action_id=${CREATE_JOURNEY.action_id}&menu_id=${CREATE_JOURNEY.menu_id}`;
  await page.goto(`${BASE_URL}${settlementRoute}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await waitForStablePage(page, 'form');
  const startFacts = await surface(page);
  check(startFacts.body_sample.includes('FE-B05-WORK-SETTLEMENT-001'), 'request journey: authoritative settlement missing');
  await page.getByRole('button', { name: '新建付款申请', exact: true }).click();
  await page.waitForURL((url) => url.pathname === '/f/payment.request/new', { timeout: 45000 });
  await waitForStablePage(page, 'form');
  const createBody = clean(await page.locator('body').innerText());
  for (const fact of ['付款申请', '2026-07-01', '2026-07-31']) {
    check(createBody.includes(fact), `request journey: carried source fact missing: ${fact}`);
  }
  for (const [fieldName, fact] of Object.entries({
    project_id: 'FE Project A',
    partner_id: 'FE-A Counterparty',
    contract_id: 'CONOUT2600010',
    settlement_id: 'FE-B05-WORK-SETTLEMENT-001',
  })) {
    const value = clean(await page.locator(`[data-field-name="${fieldName}"] input`).first().inputValue());
    check(value.includes(fact), `request journey: carried source relation missing: ${fieldName}`, { value, fact });
  }
  check(createBody.includes('按审定结算金额扣除应扣款项后支付'), 'request journey: contract payment terms missing');

  const amount = page.locator('[data-field-name="amount"] input').first();
  const note = page.locator('[data-field-name="note"] textarea, [data-field-name="note"] input').first();
  await amount.waitFor({ timeout: 30000 });
  await note.waitFor({ timeout: 30000 });
  await amount.fill('37.50');
  const noteValue = `PFL-035 user journey ${SOURCE_SHA.slice(0, 8)}`;
  await note.fill(noteValue);
  const attachmentCapability = page.locator('[data-collaboration-capability="attachments"]');
  check(await attachmentCapability.count() === 1, 'request journey: attachment capability must render exactly once');
  const fileInput = attachmentCapability.locator('input[type="file"]').first();
  await fileInput.waitFor({ state: 'attached', timeout: 30000 });
  await fileInput.setInputFiles({
    name: 'PFL035-payment-evidence.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('PFL-035 governed payment evidence', 'utf8'),
  });

  const createResponse = page.waitForResponse(async (response) => {
    if (!response.url().includes('/api/v1/intent') || response.request().method() !== 'POST') return false;
    try {
      const payload = JSON.parse(response.request().postData() || '{}');
      return payload?.intent === 'api.data' && payload?.params?.op === 'create' && payload?.params?.model === 'payment.request';
    } catch { return false; }
  }, { timeout: 45000 });
  await page.getByRole('button', { name: /^保存(?:草稿)?$/ }).first().click();
  const response = await createResponse;
  check(response.status() < 400, 'request journey: create request failed', { status: response.status() });
  await page.waitForURL((url) => /^\/(?:f|r)\/payment\.request\/\d+$/.test(url.pathname), { timeout: 45000 });
  await waitForStablePage(page, 'form');
  const createdId = Number(new URL(page.url()).pathname.split('/').pop() || 0);
  check(createdId > 0, 'request journey: created record identity missing');
  await shot(page, 'journey-request-saved');

  await page.goto(`${BASE_URL}/m/${MENU_ID}?action_id=${ACTION_ID}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await waitForStablePage(page, 'list');
  const listText = clean(await page.locator('table').first().innerText());
  check(listText.includes('37.50'), 'request journey: saved request is not locatable from list');

  const reopenContext = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
  const reopen = await reopenContext.newPage();
  attachDiagnostics(reopen, 'finance_manager_reopen');
  await login(reopen, LOGINS.manager, 'finance_manager_reopen');
  await reopen.goto(`${BASE_URL}/r/payment.request/${createdId}?action_id=${ACTION_ID}&menu_id=${MENU_ID}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await waitForStablePage(reopen, 'form');
  const reopenedBody = clean(await reopen.locator('body').innerText());
  for (const fact of [noteValue, '37.50', 'FE Project A', 'FE-A Counterparty', 'FE-A Contract', 'PFL035-payment-evidence.txt']) {
    check(reopenedBody.includes(fact), `request journey: reopened fact missing: ${fact}`);
  }
  const backend = await intent(reopen, 'api.data', {
    op: 'list', model: 'payment.request',
    fields: ['id', 'business_category_id', 'project_id', 'partner_id', 'contract_id', 'settlement_id', 'amount', 'date_request', 'note', 'attachment_ids', 'contract_payment_terms', 'settlement_period_start', 'settlement_period_end', 'settlement_submitted_amount', 'settlement_approved_amount', 'settlement_deduction_amount'],
    domain: [['id', '=', createdId]], limit: 1,
  }, 'request-create-reopen');
  const row = backend.data?.records?.[0] || null;
  const pass = backend.status === 200 && Number(row?.id || 0) === createdId
    && Number(row?.amount || 0) === 37.5
    && clean(row?.note) === noteValue
    && Number(row?.project_id?.[0] || row?.project_id) > 0
    && Number(row?.partner_id?.[0] || row?.partner_id) > 0
    && Number(row?.contract_id?.[0] || row?.contract_id) > 0
    && Number(row?.settlement_id?.[0] || row?.settlement_id) === Number(CREATE_JOURNEY.id)
    && Array.isArray(row?.attachment_ids) && row.attachment_ids.length > 0
    && clean(row?.contract_payment_terms).includes('审定结算金额')
    && clean(row?.settlement_period_start) === '2026-07-01'
    && clean(row?.settlement_period_end) === '2026-07-31';
  result.business_paths.push({ name: 'request-create-save-reopen', role: 'finance_manager', record_id: createdId, status: backend.status, row, pass });
  check(pass, 'request journey: persisted backend facts do not match the user task', { status: backend.status, row });
  await shot(reopen, 'journey-request-reopened');
  await reopenContext.close();
  return createdId;
}

async function listSearchFilterPageAndReturnJourney(page) {
  const assertPaymentAmountAggregate = async (data, label) => {
    const aggregate = data?.aggregates?.request_amount_display || {};
    const pageSum = Number(aggregate?.page_sum);
    const filteredTotal = Number(aggregate?.sum);
    check(
      aggregate?.aggregate === 'sum'
        && aggregate?.aggregation_field === 'amount'
        && aggregate?.currency_field === 'currency_id'
        && Number.isFinite(pageSum)
        && Number.isFinite(filteredTotal)
        && pageSum >= 0
        && filteredTotal >= pageSum,
      `list journey: ${label} amount aggregate contract is incomplete`,
      { aggregate },
    );
    const body = clean(await page.locator('main').innerText());
    check(
      body.includes('当前页合计') && body.includes('总计'),
      `list journey: ${label} page and filtered total rows are not visible`,
      { aggregate, body },
    );
    return { page_sum: pageSum, filtered_total: filteredTotal };
  };
  const targetResponse = await intent(page, 'api.data', {
    op: 'list', model: 'payment.request',
    fields: ['id', 'name', 'state', 'legal_next_action_display'],
    domain: [['id', '=', IDS.approved]], limit: 1,
  }, 'list-return-target');
  const target = targetResponse.data?.records?.[0] || null;
  const targetName = clean(target?.name);
  const targetNextAction = clean(target?.legal_next_action_display);
  check(targetResponse.status === 200 && targetName && targetNextAction, 'list journey: target identity or next action missing', { target });

  await page.goto(`${BASE_URL}/m/${MENU_ID}?action_id=${ACTION_ID}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await waitForStablePage(page, 'list');
  const listRegion = page.locator('main');
  const pageSizeSelect = listRegion.getByLabel('选择每页条数', { exact: true });
  await pageSizeSelect.waitFor({ state: 'visible', timeout: 30000 });
  const pageSizeResponsePromise = page.waitForResponse((response) => {
    let payload = {};
    try { payload = JSON.parse(response.request().postData() || '{}'); } catch {}
    const params = payload?.params || {};
    return payload?.intent === 'api.data'
      && params?.op === 'list'
      && params?.model === 'payment.request'
      && Number(params?.limit || 0) === 10;
  }, { timeout: 45000 });
  await pageSizeSelect.selectOption('10');
  const pageSizeResponse = await pageSizeResponsePromise;
  const pageSizeBody = await pageSizeResponse.json().catch(() => ({}));
  const pageSizeData = pageSizeBody?.data || pageSizeBody?.result?.data || pageSizeBody?.result || {};
  const authoritativeTotal = Number(pageSizeData?.total || 0);
  check(
    pageSizeResponse.status() === 200 && authoritativeTotal > 10,
    'list journey: authoritative total must expose at least two pages at page size ten',
    { status: pageSizeResponse.status(), total: authoritativeTotal },
  );
  await waitForStablePage(page, 'list');
  const pageOneAmount = await assertPaymentAmountAggregate(pageSizeData, 'page one');
  const nextPage = listRegion.getByRole('button', { name: '下一页', exact: true });
  await page.waitForFunction(() => (
    [...document.querySelectorAll('button')].some((button) => (
      String(button.textContent || '').replace(/\s+/g, ' ').trim() === '下一页'
      && !button.disabled
    ))
  ), null, { timeout: 30000 });
  check(await nextPage.isEnabled(), 'list journey: fixture must expose at least two pages at page size ten');
  const pageTwoResponsePromise = page.waitForResponse((response) => {
    let payload = {};
    try { payload = JSON.parse(response.request().postData() || '{}'); } catch {}
    const params = payload?.params || {};
    return payload?.intent === 'api.data'
      && params?.op === 'list'
      && params?.model === 'payment.request'
      && Number(params?.limit || 0) === 10
      && Number(params?.offset || 0) === 10;
  }, { timeout: 45000 });
  await nextPage.click();
  const pageTwoHttpResponse = await pageTwoResponsePromise;
  const pageTwoBody = await pageTwoHttpResponse.json().catch(() => ({}));
  const pageTwoData = pageTwoBody?.data || pageTwoBody?.result?.data || pageTwoBody?.result || {};
  await waitForStablePage(page, 'list');
  await listRegion.getByText(/第 2 \/ \d+ 页/).waitFor({ state: 'visible', timeout: 30000 });
  const pageTwoAmount = await assertPaymentAmountAggregate(pageTwoData, 'page two');
  check(
    pageTwoAmount.filtered_total === pageOneAmount.filtered_total,
    'list journey: filtered total changed across pagination',
    { page_one: pageOneAmount, page_two: pageTwoAmount },
  );

  const pageTwoTable = clean(await listRegion.getByRole('table').first().innerText());
  const pageTwoResponse = await intent(page, 'api.data', {
    op: 'list', model: 'payment.request',
    fields: ['id', 'name', 'legal_next_action_display'],
    domain: [], limit: 200,
  }, 'list-page-two-record');
  const pageTwoRows = (pageTwoResponse.data?.records || []).filter((row) => clean(row?.name) && pageTwoTable.includes(clean(row.name)));
  check(pageTwoResponse.status === 200 && pageTwoRows.length > 0, 'list journey: page two record identity missing', { pageTwoRows });
  const pageTwoRow = pageTwoRows[0];
  const pageTwoId = Number(pageTwoRow?.id || 0);
  const pageTwoName = clean(pageTwoRow?.name);
  const pageTwoNextAction = clean(pageTwoRow?.legal_next_action_display);
  check(pageTwoNextAction && pageTwoTable.includes(pageTwoNextAction), 'list journey: page two legal next action missing', { pageTwoName, pageTwoNextAction });
  const pageTwoOpenButton = listRegion.getByRole('button', { name: pageTwoName, exact: true }).first();
  await pageTwoOpenButton.waitFor({ state: 'visible', timeout: 30000 });
  await pageTwoOpenButton.click();
  await page.waitForURL(
    (url) => new RegExp(`^/(?:f|r)/payment\\.request/${pageTwoId}$`).test(url.pathname),
    { timeout: 45000 },
  );
  await waitForStablePage(page, 'form');
  check(clean(await page.locator('body').innerText()).includes(pageTwoName), 'list journey: page two opened record lost identity', { pageTwoName });
  await page.goBack({ waitUntil: 'domcontentloaded', timeout: 45000 });
  await waitForStablePage(page, 'list');
  await page.locator('main').getByText(/第 2 \/ \d+ 页/).waitFor({ state: 'visible', timeout: 30000 });
  const returnedPageTwoTable = clean(await page.locator('main').getByRole('table').first().innerText());
  check(
    returnedPageTwoTable.includes(pageTwoName) && returnedPageTwoTable.includes(pageTwoNextAction),
    'list journey: page two context was lost after record return',
    { pageTwoName, pageTwoNextAction, returnedPageTwoTable },
  );

  await page.locator('main').getByRole('button', { name: '上一页', exact: true }).click();
  await waitForStablePage(page, 'list');

  const searchInput = page.locator('main').getByRole('searchbox').first();
  await searchInput.fill(targetName);
  await searchInput.press('Enter');
  await waitForStablePage(page, 'list');
  await page.locator('main').getByRole('button', { name: '展开搜索菜单', exact: true }).click();
  const approvedFilter = page.locator('main').getByRole('button', { name: '已批准', exact: true }).first();
  await approvedFilter.waitFor({ state: 'visible', timeout: 30000 });
  await approvedFilter.click();
  await waitForStablePage(page, 'list');
  const filteredTable = clean(await page.locator('table').first().innerText());
  check(filteredTable.includes(targetName), 'list journey: searched approved request is not locatable', { targetName, filteredTable });
  check(filteredTable.includes(targetNextAction), 'list journey: legal next action is missing before open', { targetNextAction, filteredTable });

  const recordLink = page.locator('main').getByRole('button', { name: targetName, exact: true }).first();
  await recordLink.click();
  await page.waitForURL(
    (url) => new RegExp(`^/(?:f|r)/payment\\.request/${IDS.approved}$`).test(url.pathname),
    { timeout: 45000 },
  );
  await waitForStablePage(page, 'form');
  const openedBody = clean(await page.locator('body').innerText());
  check(openedBody.includes(targetName) && openedBody.includes(targetNextAction), 'list journey: opened record lost identity or next action');
  await page.goBack({ waitUntil: 'domcontentloaded', timeout: 45000 });
  await waitForStablePage(page, 'list');
  const returnedTable = clean(await page.locator('table').first().innerText());
  const activeFacet = page.locator('main').getByRole('button', { name: /^已批准/ }).first();
  const activeFacets = clean(await activeFacet.allInnerTexts());
  const returnedSearch = await page.locator('main').getByRole('searchbox').first().inputValue();
  const pass = returnedSearch === targetName
    && activeFacets.includes('已批准')
    && returnedTable.includes(targetName)
    && returnedTable.includes(targetNextAction);
  result.business_paths.push({
    name: 'list-search-filter-page-open-return', role: 'finance_manager', record_id: IDS.approved,
    page_two_record_id: pageTwoId, page_two_record: pageTwoName, page_two_next_action: pageTwoNextAction,
    page_one_amount: pageOneAmount, page_two_amount: pageTwoAmount,
    search: returnedSearch, facets: activeFacets, next_action: targetNextAction, pass,
  });
  check(pass, 'list journey: search/filter context or target record was lost after return', {
    returnedSearch, activeFacets, targetName, targetNextAction, returnedTable,
  });
  await shot(page, 'journey-list-return-context');
  const clearAll = page.getByRole('button', { name: /清除全部/ }).first();
  if (await clearAll.count()) {
    await clearAll.click();
    await waitForStablePage(page, 'list');
  }
}

const browser = await launchChromium({ headless: true });
try {
  const managerContext = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
  const manager = await managerContext.newPage();
  attachDiagnostics(manager, 'finance_manager');
  await login(manager, LOGINS.manager, 'finance_manager');

  const init = await intent(manager, 'system.init', {}, 'identity');
  const initData = init.data || {};
  check(init.status === 200, 'system.init must succeed', { status: init.status });
  check(String(initData.source_revision || initData.git_sha || '') === SOURCE_SHA, 'served source revision must equal topic HEAD', { served: initData.source_revision || initData.git_sha });

  const listFacts = await captureState(manager, {
    name: 'list', role: 'finance_manager', route: `/m/${MENU_ID}?action_id=${ACTION_ID}`, expectedPath: [`/a/${ACTION_ID}`, `/m/${MENU_ID}`], mode: 'list',
  });
  check(
    listFacts.body_sample.includes('付款申请'),
    'list: payment request identity missing',
  );
  check(listFacts.table_rows >= 1, 'list: expected business rows missing', { rows: listFacts.table_rows });
  const professionalListLabels = FIELD_MATRIX.surface_requirements?.payment_request_list?.labels || [];
  const missingListLabels = professionalListLabels.filter((label) => !listFacts.table_headers.includes(label));
  result.field_completeness.surfaces.push({ surface: 'list', required: professionalListLabels, observed: listFacts.table_headers, missing: missingListLabels });
  check(missingListLabels.length === 0, 'list: professional field headers incomplete', { required: professionalListLabels, observed: listFacts.table_headers, missing: missingListLabels });
  await listSearchFilterPageAndReturnJourney(manager);

  const readonlyFacts = await captureState(manager, {
    name: 'readonly-detail', role: 'finance_manager', route: `/r/payment.request/${IDS.approved}?action_id=${ACTION_ID}&menu_id=${MENU_ID}`, expectedPath: `/r/payment.request/${IDS.approved}`, mode: 'form',
  });
  check(readonlyFacts.body_sample.includes('已批准'), 'readonly detail: approved state missing');
  check(/办理事项\s*付款申请/.test(readonlyFacts.body_sample), 'readonly detail: handling subject must be explicit');
  check(readonlyFacts.body_sample.includes('账户信息完整'), 'readonly detail: account completeness missing');
  check(/本次申请账户快照|往来单位默认结算账户/.test(readonlyFacts.body_sample), 'readonly detail: account source missing');
  check(readonlyFacts.body_sample.includes('尚未生成'), 'readonly detail: execution status missing');
  check(readonlyFacts.body_sample.includes('无业务阻断'), 'readonly detail: blocking summary missing');
  assertNormalizedFieldSurface('payment.request', IDS.approved, 'readonly');

  await requestCreateSaveReopenJourney(browser, manager);

  // Capture the mobile contract before the positive path creates an execution.
  // This proves the approved continuation itself is directly reachable at 390px,
  // rather than only proving the post-mutation state.
  const mobileContext = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: 'zh-CN', isMobile: true });
  const mobile = await mobileContext.newPage();
  attachDiagnostics(mobile, 'finance_manager_mobile');
  await login(mobile, LOGINS.manager, 'finance_manager_mobile');
  const mobileFacts = await captureState(mobile, {
    name: '390px-mobile', role: 'finance_manager', route: `/r/payment.request/${IDS.approved}?action_id=${ACTION_ID}&menu_id=${MENU_ID}`, expectedPath: `/r/payment.request/${IDS.approved}`, mode: 'form',
  });
  check(mobileFacts.viewport.width === 390, 'mobile: viewport width must be 390', mobileFacts.viewport);
  const mobileGenerate = mobile.locator('button[data-backend-identity="button:object:action_create_payment_execution"]:visible');
  check(await mobileGenerate.count() === 1, 'mobile: approved continuation must be directly reachable', { buttons: mobileFacts.buttons });
  await mobileContext.close();

  await rejectPath(manager, 'finance_manager', IDS.draft, 'draft', /已批准状态/);
  await rejectPath(manager, 'finance_manager', IDS.receive, 'receive-request', /只有付款申请/);
  await rejectPath(
    manager,
    'finance_manager',
    IDS.incomplete,
    'incomplete-account',
    /户名.*开户行.*账号.*完整/,
    /阻断付款执行.*缺少.*请维护往来单位默认结算账户/,
  );

  await manager.goto(`${BASE_URL}/r/payment.request/${IDS.approved}?action_id=${ACTION_ID}&menu_id=${MENU_ID}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await waitForStablePage(manager, 'form');
  const approvedActionEvidence = await manager.locator('button[data-backend-identity]').evaluateAll((buttons) => buttons.map((button) => ({
    label: String(button.textContent || '').replace(/\s+/g, ' ').trim(),
    identity: button.getAttribute('data-backend-identity'),
    key: button.getAttribute('data-action-key'),
    enabled: button.getAttribute('data-action-enabled'),
    allowed: button.getAttribute('data-action-allowed'),
    profiles: button.getAttribute('data-visible-profiles'),
    container: button.closest('.form-header-primary-actions') ? 'direct' : button.closest('.form-header-more-actions') ? 'overflow' : 'other',
  })));
  result.assertions.push({ assertion: 'approved action presentation evidence', pass: true, actions: approvedActionEvidence });
  const generateButton = manager.locator('.form-header-primary-actions button[data-backend-identity="button:object:action_create_payment_execution"]');
  check(await generateButton.count() === 1, 'positive: payment execution must be the unique direct primary action', { actions: approvedActionEvidence });
  await generateButton.waitFor({ state: 'visible', timeout: 30000 });
  await shot(manager, 'positive-approved-ready');
  await generateButton.click();
  await manager.waitForURL((url) => url.pathname !== `/r/payment.request/${IDS.approved}`, { timeout: 45000 });
  await waitForStablePage(manager, 'form');
  const executionCreateFacts = await surface(manager);
  const executionCreatePath = new URL(manager.url()).pathname;
  check(
    executionCreatePath === '/f/sc.payment.execution/new' || /^\/a\/\d+$/.test(executionCreatePath),
    'positive: authoritative execution entry target did not open',
    { url: manager.url() },
  );
  check(executionCreateFacts.body_sample.includes('付款'), 'positive: execution create form did not open');
  check(executionCreateFacts.body_sample.includes('新建付款登记'), 'positive: execution create title is not professional');
  assertNormalizedFieldSurface('sc.payment.execution', null, 'execution_create');
  for (const anchor of ['FE-PFL035-PR-001', 'FE Project A', 'FE-A Counterparty', 'FE-A Contract']) {
    check(executionCreateFacts.body_sample.includes(anchor), `positive: readable relationship anchor missing: ${anchor}`);
  }
  const payerFacts = {
    payment_account_name: 'FE Company A Operating Account',
    payment_bank_name: 'FE Construction Bank',
    payment_account_no: 'FE-PAYER-0001',
    payment_method: '银行转账',
  };
  for (const [fieldName, value] of Object.entries(payerFacts)) {
    const input = manager.locator(`[data-field-name="${fieldName}"] input, [data-field-name="${fieldName}"] textarea`).first();
    await input.waitFor({ state: 'visible', timeout: 30000 });
    await input.fill(value);
  }
  await shot(manager, 'positive-execution-create');
  const createResponse = manager.waitForResponse(async (response) => {
    if (!response.url().includes('/api/v1/intent') || response.request().method() !== 'POST') return false;
    try {
      const payload = JSON.parse(response.request().postData() || '{}');
      return payload?.intent === 'api.data' && payload?.params?.op === 'create' && payload?.params?.model === 'sc.payment.execution';
    } catch { return false; }
  }, { timeout: 45000 });
  await manager.getByRole('button', { name: /^保存(?:草稿)?$/ }).first().click();
  const createResult = await createResponse;
  check(createResult.status() < 400, 'positive: payment execution create request failed', { status: createResult.status() });
  await manager.waitForURL(
    (url) => /^\/(?:f|r)\/sc\.payment\.execution\/\d+$/.test(url.pathname),
    { timeout: 45000 },
  );
  await waitForStablePage(manager, 'form');
  const savedFacts = await surface(manager);
  check(!/正在加载|加载中/.test(savedFacts.body_sample), 'positive: saved execution page remained in loading state');
  check(savedFacts.body_sample.includes('来源申请'), 'positive: saved execution did not expose professional continuation sections');
  await shot(manager, 'positive-execution-saved');
  const executionList = await intent(manager, 'api.data', {
    op: 'list', model: 'sc.payment.execution', fields: ['id', 'payment_request_id', 'project_id', 'partner_id', 'contract_id', 'state'],
    domain: [['payment_request_id', '=', IDS.approved], ['active', '=', true], ['state', '!=', 'cancel']], limit: 10,
  }, 'positive-verify');
  const executionRows = executionList.data?.records || [];
  const createdExecution = executionRows.find((row) => Number(row?.payment_request_id?.[0] || row?.payment_request_id) === IDS.approved) || null;
  const createdExecutionId = Number(createdExecution?.id || 0);
  const positivePass = executionList.status === 200 && createdExecutionId > 0
    && Number(createdExecution?.project_id?.[0] || createdExecution?.project_id) > 0
    && Number(createdExecution?.partner_id?.[0] || createdExecution?.partner_id) > 0
    && Number(createdExecution?.contract_id?.[0] || createdExecution?.contract_id) > 0;
  result.business_paths.push({ name: 'approved-complete-generate-execution', role: 'finance_manager', record_id: IDS.approved, execution_id: createdExecutionId, status: executionList.status, rows: executionRows, pass: positivePass });
  check(positivePass, 'positive: saved execution must trace to approved request');

  // Complete the actual user task in the browser. API reads below verify the
  // resulting facts; they never substitute for the submit/paid UI actions.
  await clickAuthoritativeObjectAction(manager, 'action_confirm', 'execution-submit-confirm');
  const confirmedRows = await intent(manager, 'api.data', {
    op: 'list', model: 'sc.payment.execution', fields: ['id', 'state', 'payment_request_id'],
    domain: [['id', '=', createdExecutionId]], limit: 1,
  }, 'execution-confirmed-verify');
  const confirmed = confirmedRows.data?.records?.[0] || null;
  check(confirmedRows.status === 200 && confirmed?.state === 'confirmed', 'execution: submit must reach confirmed state', { row: confirmed });
  await shot(manager, 'positive-execution-confirmed');

  await clickAuthoritativeObjectAction(manager, 'action_paid', 'execution-register-paid');
  const [paidRows, requestRows, ledgerRows] = await Promise.all([
    intent(manager, 'api.data', {
      op: 'list', model: 'sc.payment.execution', fields: ['id', 'state', 'payment_request_id', 'paid_amount'],
      domain: [['id', '=', createdExecutionId]], limit: 1,
    }, 'execution-paid-verify'),
    intent(manager, 'api.data', {
      op: 'list', model: 'payment.request', fields: ['id', 'state', 'payment_execution_status_display', 'legal_next_action_display'],
      domain: [['id', '=', IDS.approved]], limit: 1,
    }, 'execution-request-done-verify'),
    intent(manager, 'api.data', {
      op: 'list', model: 'payment.ledger', fields: ['id', 'payment_request_id', 'amount', 'state'],
      domain: [['payment_request_id', '=', IDS.approved], ['state', '=', 'posted']], limit: 10,
    }, 'execution-ledger-verify'),
  ]);
  const paid = paidRows.data?.records?.[0] || null;
  const completedRequest = requestRows.data?.records?.[0] || null;
  const ledgers = ledgerRows.data?.records || [];
  const paidPass = paidRows.status === 200 && paid?.state === 'paid'
    && requestRows.status === 200 && completedRequest?.state === 'done'
    && ledgerRows.status === 200 && ledgers.length === 1;
  result.business_paths.push({
    name: 'execution-submit-confirm-paid-reconcile', role: 'finance_manager',
    record_id: IDS.approved, execution_id: createdExecutionId,
    execution: paid, request: completedRequest, ledgers, pass: paidPass,
  });
  check(paidPass, 'execution: paid must reconcile request and exactly one ledger fact');
  await shot(manager, 'positive-execution-paid');

  const reversalReason = '验收冲销：验证付款事实保留、申请回退与重新办理入口';
  const reversalInput = manager.locator('[data-field-name="reversal_reason"] input, [data-field-name="reversal_reason"] textarea').first();
  await reversalInput.waitFor({ state: 'visible', timeout: 30000 });
  await reversalInput.fill(reversalReason);
  await clickAuthoritativeObjectAction(manager, 'action_cancel', 'execution-reverse-paid');
  const [reversedExecutionRows, reversedRequestRows, reversedLedgerRows] = await Promise.all([
    intent(manager, 'api.data', {
      op: 'list', model: 'sc.payment.execution', fields: ['id', 'state', 'cancellation_kind', 'reversal_reason'],
      domain: [['id', '=', createdExecutionId]], limit: 1,
    }, 'execution-reversed-verify'),
    intent(manager, 'api.data', {
      op: 'list', model: 'payment.request', fields: ['id', 'state', 'has_active_payment_execution', 'legal_next_action_display'],
      domain: [['id', '=', IDS.approved]], limit: 1,
    }, 'execution-reversed-request-verify'),
    intent(manager, 'api.data', {
      op: 'list', model: 'payment.ledger', fields: ['id', 'state', 'reversal_reason', 'payment_request_id'],
      domain: [['payment_request_id', '=', IDS.approved]], limit: 20,
    }, 'execution-reversed-ledger-verify'),
  ]);
  const reversedExecution = reversedExecutionRows.data?.records?.[0] || null;
  const reversedRequest = reversedRequestRows.data?.records?.[0] || null;
  const reversedLedgers = reversedLedgerRows.data?.records || [];
  const reversalPass = reversedExecutionRows.status === 200
    && reversedExecution?.state === 'cancel'
    && reversedExecution?.cancellation_kind === 'payment_reversed'
    && clean(reversedExecution?.reversal_reason) === reversalReason
    && reversedRequestRows.status === 200
    && reversedRequest?.state === 'approved'
    && reversedRequest?.has_active_payment_execution === false
    && reversedLedgerRows.status === 200
    && reversedLedgers.some((row) => row?.state === 'reversed' && clean(row?.reversal_reason) === reversalReason)
    && !reversedLedgers.some((row) => row?.state === 'posted');
  result.business_paths.push({
    name: 'paid-reversal-preserves-ledger-and-reopens-request', role: 'finance_manager',
    record_id: IDS.approved, execution_id: createdExecutionId,
    execution: reversedExecution, request: reversedRequest, ledgers: reversedLedgers, pass: reversalPass,
  });
  check(reversalPass, 'reversal: ledger must remain reversed and request must return to approved');
  await manager.goto(`${BASE_URL}/r/payment.request/${IDS.approved}?action_id=${ACTION_ID}&menu_id=${MENU_ID}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await waitForStablePage(manager, 'form');
  const regeneratedAction = manager.locator('.form-header-primary-actions button[data-backend-identity="button:object:action_create_payment_execution"]');
  check(await regeneratedAction.count() === 1, 'reversal: generate payment execution must become the direct primary action again');
  await shot(manager, 'positive-request-after-reversal');

  await managerContext.close();

  const userContext = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
  const user = await userContext.newPage();
  attachDiagnostics(user, 'finance_user');
  await login(user, LOGINS.user, 'finance_user');
  const editFacts = await captureState(user, {
    name: 'create-edit', role: 'finance_user', route: `/f/payment.request/${IDS.draft}?action_id=${ACTION_ID}&menu_id=${MENU_ID}`, expectedPath: `/f/payment.request/${IDS.draft}`, mode: 'form',
  });
  check(editFacts.form_inputs > 0 && editFacts.body_sample.includes('编辑'), 'create/edit: editable form not exposed', { inputs: editFacts.form_inputs });
  assertNormalizedFieldSurface('payment.request', IDS.draft, 'create_edit');
  await rejectPath(user, 'finance_user', IDS.approved, 'non-finance-manager', /没有生成付款登记.*权限/);
  await userContext.close();

  const emptyContext = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
  const empty = await emptyContext.newPage();
  attachDiagnostics(empty, 'empty_finance');
  await login(empty, LOGINS.empty, 'empty_finance');
  const emptyFacts = await captureState(empty, {
    name: 'empty', role: 'empty_finance', route: `/m/${MENU_ID}?action_id=${ACTION_ID}`, expectedPath: [`/a/${ACTION_ID}`, `/m/${MENU_ID}`], mode: 'list',
  });
  check(emptyFacts.table_rows === 0 && /暂无|没有.*数据|空/.test(emptyFacts.body_sample), 'empty: expected an explicit empty list state', { rows: emptyFacts.table_rows, sample: emptyFacts.body_sample });
  await emptyContext.close();

  const forbiddenContext = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
  const forbidden = await forbiddenContext.newPage();
  attachDiagnostics(forbidden, 'forbidden_user');
  await login(forbidden, LOGINS.forbidden, 'forbidden_user');
  const forbiddenFacts = await captureState(forbidden, {
    name: 'forbidden', role: 'forbidden_user', route: `/m/${MENU_ID}?action_id=${ACTION_ID}`, expectedPath: `/m/${MENU_ID}`, allowDenied: true,
  });
  check(/无权访问|没有权限|未授权/.test(forbiddenFacts.body_sample), 'forbidden: explicit permission state missing', { sample: forbiddenFacts.body_sample });
  await forbiddenContext.close();

  const expectedRejectCount = result.failed_requests.filter((row) => row.expected && row.status === 400).length;
  const expectedResourceErrors = result.console_errors.filter((row) => /status of 400 \(BAD REQUEST\)/.test(row.text)).slice(0, expectedRejectCount);
  const expectedResourceErrorSet = new Set(expectedResourceErrors);
  result.expected_console_errors = expectedResourceErrors;
  result.unexpected_console_errors = result.console_errors.filter((row) => !expectedResourceErrorSet.has(row));
  check(result.unexpected_console_errors.length === 0, 'console business errors must be zero', { errors: result.unexpected_console_errors });
  check(result.unexpected_failed_requests.length === 0, 'unexpected failed requests must be zero', { failures: result.unexpected_failed_requests });
  check(result.states.every((state) => state.document_width.overflow === 0), 'all states must have zero horizontal overflow');
  result.pass = true;
} catch (error) {
  result.error = error instanceof Error ? error.stack || error.message : String(error);
  throw error;
} finally {
  result.completed_at = new Date().toISOString();
  fs.writeFileSync(path.join(OUTPUT_DIR, 'acceptance.json'), JSON.stringify(result, null, 2));
  fs.writeFileSync(path.join(OUTPUT_DIR, 'acceptance.md'), [
    '# PFL-035 runtime acceptance',
    '',
    `- Result: ${result.pass ? 'PASS' : 'FAIL'}`,
    `- Source HEAD: ${SOURCE_SHA}`,
    `- Dirty diff SHA-256: ${DIRTY_DIFF_SHA256}`,
    `- Database: ${DB_NAME}`,
    `- Company: ${COMPANY}`,
    `- Fixed route: /m/${MENU_ID}?action_id=${ACTION_ID}`,
    `- States: ${result.states.map((row) => row.name).join(', ')}`,
    `- Business paths: ${result.business_paths.map((row) => `${row.name}:${row.pass ? 'PASS' : 'FAIL'}`).join(', ')}`,
    `- Expected rejection console entries: ${result.expected_console_errors.length}`,
    `- Unexpected console business errors: ${result.unexpected_console_errors.length}`,
    `- Unexpected failed requests: ${result.unexpected_failed_requests.length}`,
    `- Environment noise: ${result.environment_noise.join(' | ')}`,
    '',
  ].join('\n'));
  await browser.close();
}

console.log(JSON.stringify({ pass: result.pass, artifacts: OUTPUT_DIR, states: result.states.length, business_paths: result.business_paths.length, console_errors: result.console_errors.length, unexpected_failed_requests: result.unexpected_failed_requests.length }));
