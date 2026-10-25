#!/usr/bin/env node
'use strict';

// Real, single-user round trip through declared relation entries on one record.
//
// The probe does not assume that a rendered control is proof of a working
// relation: it captures the contract the page itself consumed, keeps only the
// relation fields the contract declares readable/openable, clicks every such
// control, and classifies the resulting navigation as opened / denied / none.
// A denial is a user-visible failure of the declaration, not a probe error.
// For the first opened entry it then verifies the return_* contract the
// frontend emitted, walks back, and requires the source presentation (path,
// title, statusbar, tabs, record actions) to be restored. A 403/401 anywhere
// in the trip fails the run.

const fs = require('fs');
const path = require('path');
const { createRequire } = require('module');

const requireBase = fs.existsSync(path.join(process.cwd(), 'frontend/apps/web/package.json'))
  ? path.join(process.cwd(), 'frontend/apps/web/package.json')
  : path.join(process.cwd(), 'package.json');
const { chromium } = createRequire(requireBase)('playwright');

let FRONTEND_URL;
let DB_NAME;
let ENTRY_BASE_PATH;
let LOGIN;
let PASSWORD;
let EXPECTED_SHA;
let authenticateBrowserProbe;
function relativePathname(pathname) {
  if (!ENTRY_BASE_PATH) return pathname;
  if (pathname === ENTRY_BASE_PATH) return '/';
  return pathname.startsWith(`${ENTRY_BASE_PATH}/`) ? pathname.slice(ENTRY_BASE_PATH.length) : pathname;
}
// The source record is never a literal in this file. It is resolved from the
// governed acceptance-record envelope (the same body every other declaration
// driven lane reads), so a database rebuild that renumbers the fixture cannot
// leave the probe pointing at whatever record used to hold that id.
const RESOLUTION_PATH = String(process.env.ACCEPTANCE_RECORD_RESOLUTION || '').trim();
const RESOLUTION_KEY = String(process.env.RELATION_RESOLUTION_KEY || 'project').trim();
// A diagnostic may still name a record explicitly, but only explicitly: there
// is no built-in default, so omitting the resolution can never silently fall
// back to a stale id.
const IDENTITY_SOURCE = String(process.env.RELATION_IDENTITY_SOURCE || 'resolution').trim();
const PINNED_FIELD = String(process.env.RELATION_FIELD || '').trim();
const DIAGNOSTIC_ONLY = process.env.RELATION_DIAGNOSTIC_ONLY === '1';
let outDir;

let MODEL = '';
let RECORD_ID = 0;
let ACTION_ID = 0;
let MENU_ID = 0;
let RECORD_IDENTITY = '';
let EXPECTED_COMPANY_ID = 0;
let IDENTITY_EVIDENCE = null;

function readResolution() {
  if (!RESOLUTION_PATH) {
    throw new Error('ACCEPTANCE_RECORD_RESOLUTION must point at the managed resolution body');
  }
  const body = JSON.parse(fs.readFileSync(RESOLUTION_PATH, 'utf8'));
  if (!body || body.schema !== 'acceptance.record_identity_resolution.v1') {
    throw new Error(`unexpected resolution schema ${body.schema}`);
  }
  if (body.expected_sha !== EXPECTED_SHA) throw new Error('managed resolution candidate mismatch');
  if (body.producer !== 'scripts/verify/frontend_delivery_hardening_runtime_ids.py') throw new Error('managed resolution producer mismatch');
  const targets = body && body.targets;
  if (!targets || typeof targets !== 'object') {
    throw new Error('managed resolution is not the governed envelope (targets missing)');
  }
  const entry = targets[RESOLUTION_KEY];
  if (!entry) throw new Error(`managed resolution is missing key ${RESOLUTION_KEY}`);
  const model = String(entry.model || '').trim();
  if (!model) throw new Error(`resolution ${RESOLUTION_KEY}.model is missing`);
  for (const key of ['record_id', 'action_id', 'menu_id']) {
    if (!Number.isSafeInteger(entry[key]) || entry[key] <= 0) throw new Error(`resolution ${RESOLUTION_KEY}.${key} is missing`);
  }
  // One declared identity, one match: a key that resolves to a model/id pair the
  // envelope contradicts would make the run ambiguous, so it is refused.
  if (process.env.RELATION_MODEL && String(process.env.RELATION_MODEL).trim() !== model) {
    throw new Error(`resolution model ${model} != RELATION_MODEL ${process.env.RELATION_MODEL}`);
  }
  MODEL = model;
  RECORD_ID = Number(entry.record_id);
  ACTION_ID = Number(entry.action_id);
  MENU_ID = Number(entry.menu_id);
  RECORD_IDENTITY = String(entry.record_identity || '').trim();
  EXPECTED_COMPANY_ID = Number(entry.company_id || 0) || 0;
  IDENTITY_EVIDENCE = {
    source: 'managed_resolution',
    path: RESOLUTION_PATH,
    key: RESOLUTION_KEY,
    schema: body.schema || null,
    producer: body.producer || null,
    expected_sha: body.expected_sha || null,
    model,
    record_id: RECORD_ID,
    action_id: ACTION_ID,
    menu_id: MENU_ID,
    record_identity: RECORD_IDENTITY || null,
    company_id: EXPECTED_COMPANY_ID || null,
    declared_start_state: entry.declared_start_state || null,
  };
}

function readExplicitIdentity() {
  const model = String(process.env.RELATION_MODEL || '').trim();
  const recordId = Number(process.env.RELATION_RECORD_ID || 0);
  const actionId = Number(process.env.RELATION_ACTION_ID || 0);
  if (!model || !(recordId > 0) || !(actionId > 0)) {
    throw new Error('explicit identity needs RELATION_MODEL, RELATION_RECORD_ID and RELATION_ACTION_ID');
  }
  MODEL = model;
  RECORD_ID = recordId;
  ACTION_ID = actionId;
  MENU_ID = Number(process.env.RELATION_MENU_ID || 0) || 0;
  RECORD_IDENTITY = String(process.env.RELATION_RECORD_IDENTITY || '').trim();
  EXPECTED_COMPANY_ID = Number(process.env.RELATION_COMPANY_ID || 0) || 0;
  IDENTITY_EVIDENCE = { source: 'explicit_env', model, record_id: RECORD_ID, action_id: ACTION_ID, menu_id: MENU_ID || null };
}

async function servedRevision() {
  const response = await fetch(`${FRONTEND_URL}/api/runtime-version`, { headers: { Accept: 'application/json' } });
  if (!response.ok) throw new Error(`runtime-version status=${response.status}`);
  return await response.json();
}

const RECORD_ROUTE = /^\/(?:r|f)\/[-a-zA-Z_.]+\/\d+$/;

function writeJson(name, data) {
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, name), JSON.stringify(data, null, 2), 'utf8');
}

function sourceUrl() {
  const menu = MENU_ID ? `&menu_id=${MENU_ID}` : '';
  return `${FRONTEND_URL}/r/${MODEL}/${RECORD_ID}?action_id=${ACTION_ID}${menu}`;
}

function cleanText(value) {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

function firstBoolean(...values) {
  return values.find((value) => typeof value === 'boolean') ?? null;
}

function relationEntryPayload(entry) {
  return {
    model: cleanText(entry.model),
    action_id: entry.action_id ?? null,
    menu_id: entry.menu_id ?? null,
    entry_intent: cleanText(entry.entry_intent),
    can_read: entry.can_read ?? null,
    can_open: entry.can_open ?? null,
    model_write_authority: entry.model_write_authority ?? null,
    reason_code: cleanText(entry.reason_code),
  };
}

function declaredEntriesFrom(contract) {
  const out = {};
  const statusByWidget = new Map(
    ((contract?.statusContract?.widgetStatus) || [])
      .filter((row) => row && typeof row === 'object' && row.widgetId)
      .map((row) => [String(row.widgetId), row]),
  );
  const walk = (node) => {
    if (Array.isArray(node)) {
      node.forEach(walk);
      return;
    }
    if (!node || typeof node !== 'object') return;
    const fieldInfo = node.fieldInfo && typeof node.fieldInfo === 'object' ? node.fieldInfo : {};
    const entry = fieldInfo.relation_entry || node.relation_entry || node.relationEntry;
    const name = String(node.name || node.fieldName || node.field_name || '').trim();
    if (entry && typeof entry === 'object' && name && !out[name]) {
      const widgetId = cleanText(node.widgetId);
      const status = statusByWidget.get(widgetId) || {};
      out[name] = {
        ...relationEntryPayload(entry),
        widget_id: widgetId || null,
        field_type: cleanText(fieldInfo.type || fieldInfo.ttype || node.fieldType),
        label: cleanText(node.displayLabel || node.label || node.string || node.title || fieldInfo.label || fieldInfo.string),
        label_hidden: firstBoolean(node.nolabel, node.hideLabel),
        visible: firstBoolean(
          status.visible,
          typeof fieldInfo.invisible === 'boolean' ? !fieldInfo.invisible : null,
          node.modifiers?.visible,
          fieldInfo.visible,
          node.visible,
          typeof node.invisible === 'boolean' ? !node.invisible : null,
        ),
        readonly: firstBoolean(status.readonly, fieldInfo.readonly, node.modifiers?.readonly, node.readonly),
        required: firstBoolean(status.required, fieldInfo.required, node.modifiers?.required, node.required),
        presentation_usage: cleanText(fieldInfo.sc_ui_usage || node.sc_ui_usage),
        auth: cleanText(status.auth || node.auth),
        render_reason_code: cleanText(status.reasonCode || node.reasonCode),
      };
    }
    Object.values(node).forEach(walk);
  };
  walk(contract);
  return out;
}

function layoutRelationEntriesFrom(contract) {
  const layout = contract && typeof contract === 'object'
    ? (contract.layoutContract || contract.layout || null)
    : null;
  return layout ? declaredEntriesFrom({ ...layout, statusContract: contract.statusContract }) : {};
}

async function login(page) {
  await page.goto(`${FRONTEND_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.locator('input').nth(0).fill(LOGIN);
  await page.locator('input[type="password"]').fill(PASSWORD);
  await authenticateBrowserProbe(page, LOGIN, () => page.locator('button[type="submit"]').click());
}

async function waitForRecordSurface(page) {
  await page.locator('.template-layout-shell').first().waitFor({ timeout: 45000 });
  await page.waitForFunction(() => {
    const text = String(document.querySelector('.template-layout-shell')?.textContent || '');
    if (text.includes('页面加载失败') || text.includes('页面渲染失败')) return true;
    return !text.includes('正在加载页面');
  }, null, { timeout: 45000 });
  await page.waitForFunction(() => document.querySelectorAll('[data-field-name]').length > 0, null, { timeout: 45000 });
  await page.waitForTimeout(600);
}

async function recordSnapshot(page) {
  return page.evaluate(() => {
    const clean = (value) => String(value || '').replace(/\s+/g, ' ').trim();
    const shell = document.querySelector('.template-layout-shell');
    const actions = [...document.querySelectorAll('.template-page-header-actions button')]
      .map((node) => ({ label: clean(node.textContent), disabled: Boolean(node.disabled || node.getAttribute('aria-disabled') === 'true') }))
      .filter((row) => row.label);
    return {
      url: window.location.href,
      path_search: `${window.location.pathname}${window.location.search}`,
      pathname: window.location.pathname,
      title: clean(document.querySelector('.template-page-title, h1')?.textContent),
      statusbar: [...document.querySelectorAll('.native-statusbar-step')].map((node) => clean(node.textContent)).filter(Boolean),
      tabs: [...document.querySelectorAll('[role="tab"]')].map((node) => clean(node.textContent)).filter(Boolean),
      actions,
      input_count: document.querySelectorAll('.template-layout-shell input, .template-layout-shell textarea, .template-layout-shell select').length,
      has_error: /页面加载失败|页面渲染失败|渲染失败/.test(clean(shell?.textContent || '')),
    };
  });
}

// Wait for the renderer to settle: relation open controls appear only after the
// entitlement contract lands, so poll the declaration-driven selector.
async function waitForRelationControls(page, timeoutMs = 60000) {
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    const ready = await page.evaluate(() => (
      [...document.querySelectorAll('[data-appearance="readonly-relation"], .many2one-relation-control')].some((node) => {
        const rect = node.getBoundingClientRect();
        const style = window.getComputedStyle(node);
        return rect.width > 1 && rect.height > 1
          && style.display !== 'none' && style.visibility !== 'hidden';
      })
    )).catch(() => false);
    if (ready) return true;
    if (Date.now() >= deadline) return false;
    await page.waitForTimeout(1000);
  }
}

async function visibleFieldStates(page) {
  return page.evaluate(() => {
    const clean = (value) => String(value || '').replace(/\s+/g, ' ').trim();
    const isVisible = (node) => {
      if (!node) return false;
      const rect = node.getBoundingClientRect();
      const style = window.getComputedStyle(node);
      return rect.width > 1 && rect.height > 1
        && style.display !== 'none' && style.visibility !== 'hidden';
    };
    const rows = [...document.querySelectorAll('[data-field-name]')];
    const byField = new Map();
    rows.forEach((row) => {
      const name = row.getAttribute('data-field-name');
      if (!name || !isVisible(row)) return;
      const control = row.querySelector('[data-appearance="readonly-relation"]');
      const editable = row.querySelector('.many2one-relation-control');
      const selected = control || editable;
      const contentCell = row.closest('td');
      const previousCell = contentCell?.previousElementSibling;
      const descriptionsLabel = previousCell?.tagName === 'TD'
        ? previousCell
        : null;
      const labelNode = row.querySelector('.field-label-row label, label')
        || descriptionsLabel;
      const valueNode = row.querySelector(
        '.readonly-relation-label, .readonly-value, .many2one-relation-control input, .many2one-relation-control textarea, .many2one-relation-control select',
      );
      const input = row.querySelector('.many2one-relation-control input, .many2one-relation-control textarea, .many2one-relation-control select');
      const valueText = input ? clean(input.value) : clean(valueNode?.textContent);
      const next = {
        field: name,
        visible: true,
        label: clean(labelNode?.textContent),
        label_hidden: !labelNode,
        value_text: valueText,
        has_value: !['', '-'].includes(valueText),
        control_kind: control ? 'readonly_relation' : editable ? 'editable_many2one' : 'readonly_value',
        has_control: Boolean(selected && isVisible(selected)),
        readonly: Boolean(control)
          || !editable
          || row.getAttribute('data-field-state') === 'readonly'
          || Boolean(input?.readOnly || input?.disabled),
        required: Boolean(row.querySelector('.field-state--required'))
          || String(row.getAttribute('data-field-state') || '') === 'required',
        field_state: clean(row.getAttribute('data-field-state')),
        field_auth: clean(row.getAttribute('data-field-auth')),
        widget_type: clean(row.getAttribute('data-widget-type')),
      };
      const previous = byField.get(name);
      if (!previous || (!previous.has_control && next.has_control) || (!previous.has_value && next.has_value)) {
        byField.set(name, next);
      }
    });
    return [...byField.values()].sort((left, right) => left.field.localeCompare(right.field));
  });
}

async function visibleFieldNames(page) {
  return page.evaluate(() => [...new Set(
    [...document.querySelectorAll('[data-field-name]')]
      .filter((node) => {
        const rect = node.getBoundingClientRect();
        const style = window.getComputedStyle(node);
        return rect.width > 1 && rect.height > 1
          && style.display !== 'none' && style.visibility !== 'hidden';
      })
      .map((node) => String(node.getAttribute('data-field-name') || '').trim())
      .filter(Boolean),
  )].sort());
}

async function clickAndClassify(page, field, sourcePath) {
  const readonly = page.locator(`[data-field-name="${field}"] [data-appearance="readonly-relation"]`).first();
  if (await readonly.count()) {
    await readonly.click({ timeout: 10000 });
  } else {
    const editable = page.locator(`[data-field-name="${field}"] .many2one-relation-control`).first();
    if (!await editable.count()) return { field, outcome: 'control_missing' };
    await editable.click({ timeout: 10000 });
    const openActions = page.locator('.many2one-action--record');
    let opened = false;
    for (let index = 0; index < await openActions.count(); index += 1) {
      const action = openActions.nth(index);
      if (!await action.isVisible().catch(() => false)) continue;
      await action.click();
      opened = true;
      break;
    }
    if (!opened) return { field, outcome: 'open_action_missing' };
  }
  const deadline = Date.now() + 25000;
  const sourceRelativePath = relativePathname(sourcePath);
  for (;;) {
    const current = new URL(page.url());
    const currentPath = `${current.pathname}${current.search}`;
    const currentRelativePath = relativePathname(current.pathname);
    if (currentRelativePath !== sourceRelativePath) {
      if (currentRelativePath === '/access-denied') {
        return {
          field,
          outcome: 'denied',
          reason: current.searchParams.get('reason') || '',
          target: current.searchParams.get('from') || '',
        };
      }
      if (RECORD_ROUTE.test(currentRelativePath)) {
        return {
          field,
          outcome: 'opened',
          pathname: current.pathname,
          search: current.search,
          return_contract: {
            return_model: current.searchParams.get('return_model'),
            return_field: current.searchParams.get('return_field'),
            return_record_id: current.searchParams.get('return_record_id'),
            return_action_id: current.searchParams.get('return_action_id'),
            return_menu_id: current.searchParams.get('return_menu_id'),
            return_url: current.searchParams.get('return_url'),
          },
        };
      }
      return { field, outcome: 'other_route', path: currentPath };
    }
    if (Date.now() >= deadline) return { field, outcome: 'no_navigation' };
    await page.waitForTimeout(500);
  }
}

async function main() {
  const environment = await import('./lib/frontend_acceptance_environment.mjs');
  ({ authenticateBrowserProbe } = await import('./frontend_authenticated_intent.mjs'));
  const acceptance = environment.resolveAcceptanceEnvironment({ tool: 'relation-roundtrip', operation: 'readonly' });
  const { acquireAcceptanceLease } = await import('./lib/frontend_acceptance_lease.mjs');
  const lease = await acquireAcceptanceLease({ environment: acceptance, mode: 'shared-read', owner: { tool: 'relation-roundtrip' } });
  try { await runProbe(acceptance, environment); }
  finally { await lease.release(); }
}

async function runProbe(acceptance, environment) {
  outDir = acceptance.artifacts.runRoot;
  FRONTEND_URL = acceptance.baseUrl.replace(/\/+$/, '');
  DB_NAME = acceptance.database;
  ENTRY_BASE_PATH = new URL(FRONTEND_URL).pathname.replace(/\/+$/, '');
  LOGIN = acceptance.login;
  PASSWORD = acceptance.password;
  EXPECTED_SHA = acceptance.provenance.expectedSha;
  await environment.verifyServedIdentity(acceptance);

  if (!LOGIN || !PASSWORD) throw new Error('E2E_LOGIN and E2E_PASSWORD are required');
  if (!EXPECTED_SHA) throw new Error('SC_ACCEPTANCE_TARGET_SHA is required');
  if (IDENTITY_SOURCE === 'explicit') readExplicitIdentity();
  else readResolution();
  const runtime = await servedRevision();
  const served = String(runtime.git_sha || runtime.source_revision || '');
  if (served !== EXPECTED_SHA) throw new Error(`served revision ${served} != SC_ACCEPTANCE_TARGET_SHA ${EXPECTED_SHA}`);
  if (String(runtime.database || '') !== DB_NAME) throw new Error(`served database ${runtime.database} != ${DB_NAME}`);
  const result = {
    schema: 'record-relation-roundtrip-acceptance.v1',
    frontend_url: FRONTEND_URL,
    database: DB_NAME,
    login: LOGIN,
    served_revision: served,
    expected_sha: EXPECTED_SHA,
    declared_company_id: EXPECTED_COMPANY_ID || null,
    identity: IDENTITY_EVIDENCE,
    source: { model: MODEL, record_id: RECORD_ID, action_id: ACTION_ID, menu_id: MENU_ID, record_identity: RECORD_IDENTITY || null },
    status: 'fail',
    artifacts: outDir,
    denied_requests: [],
    failed_requests: [],
    diagnostic_only: DIAGNOSTIC_ONLY,
    console_errors: [],
    declared_openable: [],
    attempts: [],
    failures: [],
  };
  const browser = await chromium.launch({ headless: true });
  let page;
  try {
    const context = await browser.newContext({ locale: 'zh-CN', viewport: { width: 1440, height: 1000 } });
    page = await context.newPage();
    page.on('console', (msg) => { if (msg.type() === 'error') result.console_errors.push(msg.text()); });
    page.on('pageerror', (err) => result.console_errors.push(err.message));
    page.on('response', (response) => {
      if ([401, 403].includes(response.status())) result.denied_requests.push({ status: response.status(), url: response.url() });
      if (response.status() >= 400) {
        let body = {};
        try { body = response.request().postDataJSON() || {}; } catch { /* non-JSON resource */ }
        const params = body.params || {};
        // Diagnostic metadata only: never retain login payloads, headers or tokens.
        result.failed_requests.push({
          status: response.status(), pathname: new URL(response.url()).pathname,
          intent: body.intent || null, operation: params.op || null,
          model: params.model || null, record_id: params.record_id || params.res_id || params.id || null,
          ids: Array.isArray(params.ids) ? params.ids : null,
        });
      }
    });
    let contractPayload = null;
    page.on('response', (response) => {
      try {
        const request = response.request();
        const body = request.postData();
        if (!body || !body.includes('"ui.contract.v2"')) return;
        if (!body.includes(`"action_id":${ACTION_ID}`) && !body.includes(`"record_id":${RECORD_ID}`)) return;
        if (contractPayload) return;
        response.json().then((json) => { contractPayload = json?.data || json || null; }).catch(() => {});
      } catch { /* contract capture is best effort */ }
    });

    await login(page);
    await page.goto(sourceUrl(), { waitUntil: 'domcontentloaded', timeout: 60000 });
    await waitForRecordSurface(page);
    const before = await recordSnapshot(page);
    result.before = before;
    if (before.has_error) throw new Error('source record surface did not render');

    await waitForRelationControls(page);
    const broadDeclared = contractPayload ? declaredEntriesFrom(contractPayload) : {};
    const layoutDeclared = contractPayload ? layoutRelationEntriesFrom(contractPayload) : {};
    const declared = Object.keys(layoutDeclared).length ? layoutDeclared : broadDeclared;
    result.declared_entry_count = Object.keys(declared).length;
    result.declared_relation_entries = declared;
    const fieldStates = await visibleFieldStates(page);
    const controls = fieldStates.filter((row) => row.has_control);
    const visibleFields = [...new Set([
      ...(await visibleFieldNames(page)),
      ...fieldStates.map((row) => row.field),
    ])].sort();
    const contractOpenable = Object.entries(declared)
      .filter(([, entry]) => entry && entry.can_read === true && entry.can_open === true)
      .map(([field, entry]) => ({ field, declared: entry }));
    const contractOpenableFields = contractOpenable.map((row) => row.field);
    const visibleOpenableFields = contractOpenableFields.filter((field) => visibleFields.includes(field));
    const notVisibleOpenableFields = contractOpenableFields.filter((field) => !visibleFields.includes(field));
    const missingVisibleState = visibleOpenableFields.filter(
      (field) => !fieldStates.some((row) => row.field === field),
    );
    if (missingVisibleState.length) {
      throw new Error(`visible openable relations have no rendered field state: ${missingVisibleState.join(',')}`);
    }
    const emptyValueOpenableFields = visibleOpenableFields.filter(
      (field) => !fieldStates.find((row) => row.field === field)?.has_value,
    );
    const populatedOpenableFields = visibleOpenableFields.filter(
      (field) => !emptyValueOpenableFields.includes(field),
    );
    const controlFieldSet = new Set(controls.map((row) => row.field));
    const controlFields = contractOpenableFields.filter((field) => controlFieldSet.has(field));
    const missingControls = populatedOpenableFields.filter((field) => !controlFields.includes(field));
    const undeclaredControls = controlFields.filter((field) => {
      const entry = declared[field];
      return !entry || entry.can_read !== true || entry.can_open !== true;
    });
    const invalidOpeners = contractOpenable
      .filter(({ declared: entry }) => !(Number(entry.action_id) > 0 && Number(entry.menu_id) > 0))
      .map((row) => row.field);
    if (missingControls.length) throw new Error(`declared openable relations have no public control: ${missingControls.join(',')}`);
    if (undeclaredControls.length) throw new Error(`public relation controls are not declared openable: ${undeclaredControls.join(',')}`);
    if (invalidOpeners.length) throw new Error(`declared openable relations lack action/menu authority: ${invalidOpeners.join(',')}`);
    const comparisonByField = new Map(contractOpenable.map(({ field, declared: entry }) => {
      const rendered = fieldStates.find((row) => row.field === field) || {
        field,
        visible: false,
        label: '',
        label_hidden: null,
        value_text: '',
        has_value: false,
        control_kind: null,
        has_control: false,
        readonly: null,
        required: null,
        field_state: '',
        field_auth: '',
        widget_type: '',
      };
      const contractSurface = {
        label: entry.label || '',
        label_hidden: entry.label_hidden,
        visible: entry.visible,
        readonly: entry.readonly,
        required: entry.required,
        presentation_usage: entry.presentation_usage || '',
        field_type: entry.field_type || '',
        relation_model: entry.model,
        can_read: entry.can_read,
        can_open: entry.can_open,
        action_id: entry.action_id,
        menu_id: entry.menu_id,
        reason_code: entry.reason_code || '',
      };
      const renderedSurface = {
        label: rendered.label,
        label_hidden: rendered.label_hidden,
        visible: rendered.visible,
        readonly: rendered.readonly,
        required: rendered.required,
        field_type: rendered.widget_type,
        has_value: rendered.has_value,
        value_text: rendered.value_text,
        has_open_control: rendered.has_control,
        control_kind: rendered.control_kind,
        field_state: rendered.field_state,
        field_auth: rendered.field_auth,
      };
      const differences = [];
      const recordDifference = (kind, blocking, reason, contractValue, renderedValue) => {
        differences.push({
          kind,
          blocking,
          contract: contractValue,
          rendered: renderedValue,
          reason,
        });
      };
      if (typeof contractSurface.visible === 'boolean' && contractSurface.visible !== renderedSurface.visible) {
        recordDifference(
          'CONTRACT_VISIBILITY_MISMATCH',
          false,
          'Declared field visibility differs from the final rendered field presence; retain it as a reviewed presentation difference.',
          contractSurface.visible,
          renderedSurface.visible,
        );
      }
      if (typeof contractSurface.readonly === 'boolean'
        && renderedSurface.visible
        && contractSurface.readonly !== renderedSurface.readonly) {
        recordDifference(
          'CONTRACT_READONLY_MISMATCH',
          false,
          'Declared readonly state differs from the final rendered control state; retain it as a reviewed presentation difference.',
          contractSurface.readonly,
          renderedSurface.readonly,
        );
      }
      if (typeof contractSurface.required === 'boolean'
        && renderedSurface.visible
        && contractSurface.required !== renderedSurface.required) {
        recordDifference(
          'CONTRACT_REQUIRED_MISMATCH',
          false,
          'Declared required state differs from the final rendered required marker; retain it as a reviewed presentation difference.',
          contractSurface.required,
          renderedSurface.required,
        );
      }
      if (contractSurface.label && renderedSurface.visible
        && contractSurface.label_hidden !== true && renderedSurface.label !== contractSurface.label) {
        recordDifference(
          'CONTRACT_LABEL_RENDER_DIFF',
          false,
          'The declared field label and the final user-facing label differ; keep this visible for presentation iteration.',
          contractSurface.label,
          renderedSurface.label,
        );
      }
      if (contractSurface.can_open === true && !renderedSurface.has_value && !renderedSurface.has_open_control) {
        recordDifference(
          'OPENABLE_EMPTY_VALUE_HAS_NO_TARGET',
          false,
          'The relation is openable in the contract, but this record has no related value and therefore no current-record target to open.',
          true,
          false,
        );
      }
      if (contractSurface.can_open === true && renderedSurface.has_value && !renderedSurface.has_open_control) {
        recordDifference(
          'VALUE_WITHOUT_OPEN_CONTROL',
          true,
          'A populated openable relation did not render an open control.',
          true,
          false,
        );
      }
      return [field, {
        field,
        contract: contractSurface,
        rendered: renderedSurface,
        differences,
      }];
    }));
    if (DIAGNOSTIC_ONLY && !PINNED_FIELD) throw new Error('bounded diagnostic requires RELATION_FIELD');
    const ordered = DIAGNOSTIC_ONLY ? [PINNED_FIELD] : PINNED_FIELD
      ? [PINNED_FIELD, ...populatedOpenableFields]
      : populatedOpenableFields;
    const targets = [...new Set(ordered)];
    if (!targets.length) throw new Error('no visible declared relation-open control found on the source record');
    result.controls = controls;
    result.visible_relation_field_states = fieldStates;
    result.contract_openable_fields = contractOpenableFields;
    result.visible_openable_fields = visibleOpenableFields;
    result.populated_openable_fields = populatedOpenableFields;
    result.empty_value_openable_fields = emptyValueOpenableFields;
    result.not_visible_openable_fields = notVisibleOpenableFields;
    result.visible_relation_control_fields = controlFields;
    result.contract_render_comparison = [...comparisonByField.values()];
    result.declared_openable = targets.map((field) => ({
      field,
      label: controls.find((row) => row.field === field)?.label || '',
      declared: declared[field],
    }));

    for (const field of targets) {
      const attempt = await clickAndClassify(page, field, before.pathname);
      const declaredEntry = declared[field] || null;
      attempt.declared = declaredEntry;
      if (!declaredEntry || declaredEntry.can_read !== true || declaredEntry.can_open !== true) {
        attempt.failure = 'control rendered for a field the contract does not declare readable';
      } else if (attempt.outcome === 'denied') {
        attempt.failure = `declared openable entry rejected by route authority (${attempt.reason || 'unknown'})`;
      } else if (attempt.outcome !== 'opened') {
        attempt.failure = `declared openable entry produced no record navigation (${attempt.outcome})`;
      }
      if (attempt.outcome === 'opened') {
        const targetPath = relativePathname(new URL(attempt.pathname, FRONTEND_URL).pathname);
        const targetMatch = targetPath.match(/^\/(?:r|f)\/([^/]+)\/\d+$/);
        const targetSearch = new URLSearchParams(attempt.search || '');
        attempt.observed_relation = {
          model: targetMatch?.[1] || '',
          action_id: Number(targetSearch.get('action_id') || 0) || null,
          menu_id: Number(targetSearch.get('menu_id') || 0) || null,
        };
        const comparison = comparisonByField.get(field);
        const recordBehaviorDifference = (kind, contractValue, renderedValue, reason) => {
          if (!comparison) return;
          comparison.differences.push({
            kind,
            blocking: true,
            contract: contractValue,
            rendered: renderedValue,
            reason,
          });
        };
        if (attempt.observed_relation.model !== declaredEntry.model) {
          recordBehaviorDifference(
            'RELATION_TARGET_MODEL_MISMATCH',
            declaredEntry.model,
            attempt.observed_relation.model,
            'The opened relation target model differs from the contract declaration.',
          );
          attempt.failure = `target model mismatch: ${attempt.observed_relation.model} != ${declaredEntry.model}`;
        } else if (attempt.observed_relation.action_id !== Number(declaredEntry.action_id)) {
          recordBehaviorDifference(
            'RELATION_TARGET_ACTION_MISMATCH',
            declaredEntry.action_id,
            attempt.observed_relation.action_id,
            'The opened relation used a different action id from the contract declaration.',
          );
          attempt.failure = `target action mismatch: ${attempt.observed_relation.action_id} != ${declaredEntry.action_id}`;
        } else if (attempt.observed_relation.menu_id !== Number(declaredEntry.menu_id)) {
          recordBehaviorDifference(
            'RELATION_TARGET_MENU_MISMATCH',
            declaredEntry.menu_id,
            attempt.observed_relation.menu_id,
            'The opened relation used a different menu id from the contract declaration.',
          );
          attempt.failure = `target menu mismatch: ${attempt.observed_relation.menu_id} != ${declaredEntry.menu_id}`;
        }
        if (attempt.return_contract.return_model !== MODEL) attempt.failure = `return_model mismatch: ${attempt.return_contract.return_model}`;
        else if (attempt.return_contract.return_field !== field) attempt.failure = `return_field mismatch: ${attempt.return_contract.return_field}`;
        else if (attempt.return_contract.return_record_id !== String(RECORD_ID)) attempt.failure = `return_record_id mismatch: ${attempt.return_contract.return_record_id}`;
        else if (!result.roundtrip) {
          await waitForRecordSurface(page);
          attempt.target_snapshot = await recordSnapshot(page);
          await page.goBack({ waitUntil: 'domcontentloaded', timeout: 45000 });
          await waitForRecordSurface(page);
          const after = await recordSnapshot(page);
          const same = (left, right) => JSON.stringify(left) === JSON.stringify(right);
          const restored = {
            path_restored: after.path_search === before.path_search,
            title_restored: same(after.title, before.title),
            statusbar_restored: same(after.statusbar, before.statusbar),
            tabs_restored: same(after.tabs, before.tabs),
            actions_restored: same(after.actions, before.actions),
            error_free: after.has_error === false,
          };
          result.roundtrip = { field, restored, after };
          if (Object.values(restored).some((value) => value !== true)) {
            attempt.failure = `source presentation was not restored: ${JSON.stringify(restored)}`;
          }
        }
      }
      result.attempts.push(attempt);
      if (attempt.failure) result.failures.push({ field, reason: attempt.failure });
      await page.goto(sourceUrl(), { waitUntil: 'domcontentloaded', timeout: 60000 });
      await waitForRecordSurface(page);
      await waitForRelationControls(page);
    }

    if (result.denied_requests.length) result.failures.push({ field: '-', reason: `denied requests during round trip: ${JSON.stringify(result.denied_requests)}` });
    if (result.console_errors.length) result.failures.push({ field: '-', reason: `console errors: ${JSON.stringify(result.console_errors.slice(0, 3))}` });
    if (!result.roundtrip) result.failures.push({ field: '-', reason: 'no declared relation entry completed a verified open-and-return round trip' });
    const comparisonRows = [...comparisonByField.values()];
    const blockingDifferences = comparisonRows.flatMap((row) => row.differences.filter((item) => item.blocking));
    result.contract_render_comparison_summary = {
      complete: comparisonRows.length === contractOpenableFields.length,
      contract_field_count: contractOpenableFields.length,
      compared_field_count: comparisonRows.length,
      fields_with_differences: comparisonRows.filter((row) => row.differences.length).length,
      difference_count: comparisonRows.reduce((count, row) => count + row.differences.length, 0),
      blocking_count: blockingDifferences.length,
      non_blocking_count: comparisonRows.reduce(
        (count, row) => count + row.differences.filter((item) => !item.blocking).length,
        0,
      ),
    };
    if (blockingDifferences.length) {
      result.failures.push({
        field: '-',
        reason: `blocking contract/render differences: ${blockingDifferences.map((item) => item.kind).join(',')}`,
      });
    }
    result.status = DIAGNOSTIC_ONLY ? 'diagnostic_only' : result.failures.length ? 'fail' : 'pass';
  } catch (err) {
    if (page) {
      result.failure_path = new URL(page.url()).pathname;
      fs.mkdirSync(outDir, { recursive: true });
      await page.screenshot({ path: path.join(outDir, 'failure.png'), fullPage: true }).catch(() => {});
    }
    result.error = err instanceof Error ? err.message : String(err);
    result.failures.push({ field: '-', reason: result.error });
    if (err instanceof Error && err.stack) result.stack = err.stack.split('\n').slice(0, 6).join('\n');
  } finally {
    await browser.close().catch(() => {});
  }
  writeJson('summary.json', result);
  console.log(JSON.stringify({
    status: result.status,
    declared_entry_count: result.declared_entry_count,
    attempts: result.attempts.map((row) => ({ field: row.field, outcome: row.outcome, reason: row.reason, failure: row.failure })),
    roundtrip: result.roundtrip ? { field: result.roundtrip.field, restored: result.roundtrip.restored } : null,
    contract_render_comparison_summary: result.contract_render_comparison_summary,
    denied_requests: result.denied_requests.length,
    console_errors: result.console_errors.length,
    error: result.error,
    failure_path: result.failure_path,
    artifacts: outDir,
  }, null, 2));
  process.exitCode = result.status === 'pass' ? 0 : 1;
}

main().catch((error) => {
  // Keep exception text and arguments private; source locations identify the
  // failed prerequisite without leaking credentials or request bodies.
  const locations = String(error?.stack || '').split('\n').slice(1)
    .map(line => line.match(/record_relation_roundtrip_acceptance\.js:\d+:\d+/)?.[0])
    .filter(Boolean);
  console.error(JSON.stringify({ status: 'fail', phase: 'prerequisite', locations }));
  process.exitCode = 1;
});
