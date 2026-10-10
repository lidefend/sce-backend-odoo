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

const FRONTEND_URL = process.env.FRONTEND_URL || 'http://127.0.0.1:5180';
const DB_NAME = process.env.DB_NAME || 'sc_demo';
const LOGIN = process.env.E2E_LOGIN || '';
const PASSWORD = process.env.E2E_PASSWORD || '';
const EXPECTED_SHA = process.env.SC_ACCEPTANCE_TARGET_SHA || '';
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
const MAX_CONTROLS = Number(process.env.RELATION_MAX_CONTROLS || 6);
const ARTIFACTS_DIR = process.env.ARTIFACTS_DIR || '.runtime/final-acceptance/relation-roundtrip';

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
  if (body && body.schema && body.schema !== 'acceptance.record_identity_resolution.v1') {
    throw new Error(`unexpected resolution schema ${body.schema}`);
  }
  const targets = body && body.targets;
  if (!targets || typeof targets !== 'object') {
    throw new Error('managed resolution is not the governed envelope (targets missing)');
  }
  const entry = targets[RESOLUTION_KEY];
  if (!entry) throw new Error(`managed resolution is missing key ${RESOLUTION_KEY}`);
  const model = String(entry.model || '').trim();
  if (!model) throw new Error(`resolution ${RESOLUTION_KEY}.model is missing`);
  for (const key of ['record_id', 'action_id', 'menu_id']) {
    if (!(Number(entry[key]) > 0)) throw new Error(`resolution ${RESOLUTION_KEY}.${key} is missing`);
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

const ts = new Date().toISOString().replace(/[-:]/g, '').slice(0, 15);
const outDir = path.join(ARTIFACTS_DIR, ts);
const RECORD_ROUTE = /^\/(?:r|f)\/[-a-zA-Z_.]+\/\d+$/;

function writeJson(name, data) {
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, name), JSON.stringify(data, null, 2), 'utf8');
}

function sourceUrl() {
  const menu = MENU_ID ? `&menu_id=${MENU_ID}` : '';
  return `${FRONTEND_URL}/r/${MODEL}/${RECORD_ID}?db=${encodeURIComponent(DB_NAME)}&action_id=${ACTION_ID}${menu}`;
}

function declaredEntriesFrom(contract) {
  const out = {};
  const walk = (node) => {
    if (Array.isArray(node)) {
      node.forEach(walk);
      return;
    }
    if (!node || typeof node !== 'object') return;
    const entry = node.relation_entry || node.relationEntry;
    const name = String(node.name || node.fieldName || node.field_name || '').trim();
    if (entry && typeof entry === 'object' && name && !out[name]) {
      out[name] = {
        model: String(entry.model || '').trim(),
        action_id: entry.action_id ?? null,
        menu_id: entry.menu_id ?? null,
        entry_intent: String(entry.entry_intent || ''),
        can_read: entry.can_read ?? null,
        can_open: entry.can_open ?? null,
        model_write_authority: entry.model_write_authority ?? null,
      };
    }
    Object.values(node).forEach(walk);
  };
  walk(contract);
  return out;
}

async function login(page) {
  await page.goto(`${FRONTEND_URL}/login?db=${encodeURIComponent(DB_NAME)}`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.locator('input').nth(0).fill(LOGIN);
  await page.locator('input[type="password"]').fill(PASSWORD);
  const dbInput = page.locator('input').nth(2);
  if (await dbInput.count() && await dbInput.isEnabled().catch(() => false)) await dbInput.fill(DB_NAME).catch(() => {});
  await page.locator('button[type="submit"]').click();
  await page.waitForFunction(() => Object.keys(window.sessionStorage).some((key) => key.startsWith('sc_auth_token')), null, { timeout: 60000 });
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
      [...document.querySelectorAll('[data-appearance="readonly-relation"]')].some((node) => {
        const rect = node.getBoundingClientRect();
        return rect.width > 1 && rect.height > 1;
      })
    )).catch(() => false);
    if (ready) return true;
    if (Date.now() >= deadline) return false;
    await page.waitForTimeout(1000);
  }
}

async function visibleRelationControls(page) {
  return page.evaluate(() => {
    const rows = [...document.querySelectorAll('[data-field-name]')];
    const seen = new Set();
    const out = [];
    rows.forEach((row) => {
      const name = row.getAttribute('data-field-name');
      if (!name || seen.has(name)) return;
      const control = row.querySelector('[data-appearance="readonly-relation"]');
      if (!control) return;
      const rect = control.getBoundingClientRect();
      if (rect.width <= 1 || rect.height <= 1) return;
      seen.add(name);
      out.push({ field: name, label: String(control.textContent || '').replace(/\s+/g, ' ').trim() });
    });
    return out;
  });
}

async function clickAndClassify(page, field, sourcePath) {
  const locator = page.locator(`[data-field-name="${field}"] [data-appearance="readonly-relation"]`).first();
  if (!await locator.count()) return { field, outcome: 'control_missing' };
  await locator.click({ timeout: 10000 });
  const deadline = Date.now() + 25000;
  for (;;) {
    const current = new URL(page.url());
    const currentPath = `${current.pathname}${current.search}`;
    if (current.pathname !== sourcePath) {
      if (current.pathname === '/access-denied') {
        return {
          field,
          outcome: 'denied',
          reason: current.searchParams.get('reason') || '',
          target: current.searchParams.get('from') || '',
        };
      }
      if (RECORD_ROUTE.test(current.pathname)) {
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
    console_errors: [],
    declared_openable: [],
    attempts: [],
    failures: [],
  };
  const browser = await chromium.launch({ headless: true });
  try {
    const context = await browser.newContext({ locale: 'zh-CN', viewport: { width: 1440, height: 1000 } });
    const page = await context.newPage();
    page.on('console', (msg) => { if (msg.type() === 'error') result.console_errors.push(msg.text()); });
    page.on('pageerror', (err) => result.console_errors.push(err.message));
    page.on('response', (response) => {
      if ([401, 403].includes(response.status())) result.denied_requests.push({ status: response.status(), url: response.url() });
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
    const declared = contractPayload ? declaredEntriesFrom(contractPayload) : {};
    result.declared_entry_count = Object.keys(declared).length;
    const controls = await visibleRelationControls(page);
    const ordered = PINNED_FIELD
      ? [PINNED_FIELD, ...controls.map((row) => row.field)]
      : controls.map((row) => row.field);
    const targets = [...new Set(ordered)].slice(0, MAX_CONTROLS);
    if (!targets.length) throw new Error('no visible declared relation-open control found on the source record');
    result.controls = controls;
    result.declared_openable = targets.map((field) => ({
      field,
      label: controls.find((row) => row.field === field)?.label || '',
      declared: declared[field] || null,
    }));

    for (const field of targets) {
      const attempt = await clickAndClassify(page, field, before.pathname);
      const declaredEntry = declared[field] || null;
      attempt.declared = declaredEntry;
      if (declaredEntry && declaredEntry.can_read !== true) {
        attempt.failure = 'control rendered for a field the contract does not declare readable';
      } else if (attempt.outcome === 'denied') {
        attempt.failure = `declared openable entry rejected by route authority (${attempt.reason || 'unknown'})`;
      } else if (attempt.outcome !== 'opened') {
        attempt.failure = `declared openable entry produced no record navigation (${attempt.outcome})`;
      }
      if (attempt.outcome === 'opened') {
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
    result.status = result.failures.length ? 'fail' : 'pass';
  } catch (err) {
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
    denied_requests: result.denied_requests.length,
    console_errors: result.console_errors.length,
    error: result.error,
    artifacts: outDir,
  }, null, 2));
  process.exit(result.status === 'pass' ? 0 : 1);
}

main();
