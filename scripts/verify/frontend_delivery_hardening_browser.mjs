#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';
import { launchChromium } from './playwright_runtime.mjs';
import { applyReleasedNavigationTarget, captureReleasedNavigation } from './released_navigation_target.mjs';
import { evaluateRelativePerformanceBudget } from './frontend_performance_budget.mjs';
import { resolveAcceptanceEnvironment } from './lib/frontend_acceptance_environment.mjs';
import { acquireAcceptanceLease } from './lib/frontend_acceptance_lease.mjs';
import {
  captureEvidenceScreenshot,
  installEvidenceSensitivityTracker,
  stopEvidenceTrace,
} from './frontend_evidence_capture_guard.mjs';

const require = createRequire(import.meta.url);
const axeModule = require(require.resolve('@axe-core/playwright', { paths: [path.resolve('frontend/apps/web/node_modules')] }));
const AxeBuilder = axeModule.default || axeModule;
const acceptance = resolveAcceptanceEnvironment({ tool: 'delivery-hardening', operation: 'read' });
const BASE_URL = acceptance.baseUrl;
const DB_NAME = acceptance.database;
const PASSWORD = acceptance.password || process.env.SC_ACCEPTANCE_FIXTURE_PASSWORD || '';
const FINANCE_LOGIN = acceptance.roleBindings.finance || 'fixture_role_finance';
const PROJECT_MEMBER_LOGIN = acceptance.roleBindings.project_member || 'fixture_role_project_a_member';
const PROJECT_MANAGER_LOGIN = acceptance.roleBindings.project_manager || 'fixture_role_pm';
const CONTRACT_OPERATOR_LOGIN = acceptance.roleBindings.contract_operator || 'fixture_role_contract_operator';
const OUT = process.env.ARTIFACTS_DIR || 'artifacts/frontend-delivery-hardening';
const TARGETS = JSON.parse(process.env.FRONTEND_DELIVERY_HARDENING_TARGETS_JSON || '{}');
const SCREENSHOTS = path.join(OUT, 'screenshots');
const TRACES = path.join(OUT, 'traces');
const PERF_ONLY = process.env.DELIVERY_HARDENING_PERF_ONLY === '1';
const SKIP_PERF = process.env.DELIVERY_HARDENING_SKIP_PERF === '1';
const PERF_BASELINE_CAPTURE = process.env.DELIVERY_HARDENING_BASELINE_CAPTURE === '1';
const PERF_BUDGET_PATH = process.env.DELIVERY_HARDENING_BUDGET_JSON
  || 'config/frontend/release_performance_budgets_v1.json';
const performanceBudgets = JSON.parse(fs.readFileSync(PERF_BUDGET_PATH, 'utf8'));
const PERF_BASELINE_PATH = process.env.DELIVERY_HARDENING_BASELINE_JSON
  || performanceBudgets.relative_baseline_path
  || 'docs/frontend_productization/frontend_delivery_performance_baseline_v1.json';
const PERF_RUNS = Number(process.env.DELIVERY_HARDENING_PERF_RUNS || 5);
const FORM_SURFACE_SELECTOR = '[data-workspace-primary-content]';
const runtimeByPage = new WeakMap();
fs.rmSync(SCREENSHOTS, { recursive: true, force: true });
fs.rmSync(TRACES, { recursive: true, force: true });
fs.mkdirSync(SCREENSHOTS, { recursive: true });
fs.mkdirSync(TRACES, { recursive: true });

function check(value, message) { if (!value) throw new Error(message); }
const capturedScreenshotHashes = new Map();

async function waitForSurfaceReady(page, surface) {
  const selectors = {
    home: '[data-role-home]',
    'my-work': '.product-work',
    'project-list': '[data-product-page-mode="list"]',
    'contract-list': '[data-product-page-mode="list"]',
    'settlement-list': '[data-product-page-mode="list"]',
    'payment-list': '[data-product-page-mode="list"]',
    'project-detail': '[data-product-page-mode="form"]',
    'contract-detail': '[data-product-page-mode="form"]',
    'settlement-detail': '[data-product-page-mode="form"]',
    'payment-detail': '[data-product-page-mode="form"]',
    'execution-detail': '[data-product-page-mode="form"]',
    'not-found': 'main [role="alert"], main .sc-alert',
  };
  const selector = selectors[surface.name];
  if (selector) await page.locator(selector).first().waitFor({ state: 'visible', timeout: 45000 });
  await page.waitForFunction(() => {
    const app = document.querySelector('#app');
    const text = String(app?.textContent || '').replace(/\s+/g, ' ').trim();
    const rect = app?.getBoundingClientRect();
    return Boolean(app && rect && rect.width > 0 && rect.height > 0 && app.querySelectorAll('*').length >= 5 && text.length >= 4);
  }, undefined, { timeout: 45000 });
  await page.waitForFunction(() => {
    const pending = [...document.querySelectorAll('[aria-busy="true"]')].some((element) => {
      const rect = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      return rect.width > 1 && rect.height > 1 && style.visibility !== 'hidden' && style.display !== 'none';
    });
    return !pending;
  }, undefined, { timeout: 45000 });
}

async function renderedSurfaceMetrics(page, buffer) {
  const dom = await page.evaluate(() => {
    const visible = [...document.querySelectorAll('#app *')].filter((element) => {
      const rect = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      return rect.width > 1 && rect.height > 1 && style.visibility !== 'hidden' && style.display !== 'none';
    });
    const colors = new Set();
    for (const element of visible) {
      const style = getComputedStyle(element);
      colors.add(`${style.color}|${style.backgroundColor}|${style.borderColor}`);
    }
    return {
      visible_element_count: visible.length,
      visible_text_length: String(document.querySelector('#app')?.textContent || '').replace(/\s+/g, ' ').trim().length,
      semantic_color_count: colors.size,
      interactive_count: visible.filter((element) => element.matches('a,button,input,select,textarea,[role="button"],[role="link"]')).length,
    };
  });
  return { ...dom, sha256: crypto.createHash('sha256').update(buffer).digest('hex') };
}

async function assertMeaningfulScreenshot(page, buffer, label) {
  const metrics = await renderedSurfaceMetrics(page, buffer);
  check(metrics.visible_element_count >= 5, `${label}: blank rendered surface visible_elements=${metrics.visible_element_count}`);
  check(metrics.visible_text_length >= 4, `${label}: blank rendered surface text_length=${metrics.visible_text_length}`);
  check(metrics.semantic_color_count >= 2, `${label}: near-blank rendered surface semantic_colors=${metrics.semantic_color_count}`);
  const previous = capturedScreenshotHashes.get(metrics.sha256);
  check(!previous, `${label}: screenshot is identical to ${previous}`);
  capturedScreenshotHashes.set(metrics.sha256, label);
  return metrics;
}
function recordRoute(target) { return `/r/${target.model}/${target.record_id}?action_id=${target.action_id}&menu_id=${target.menu_id}`; }
function listRoute(target) { return `/a/${target.action_id}?menu_id=${target.menu_id}`; }
function waitForRecordContractResponse(page, target) {
  return page.waitForResponse((response) => {
    if (!response.url().includes('/api/v1/intent')) return false;
    try {
      const body = JSON.parse(response.request().postData() || '{}');
      const params = body.params || {};
      return body.intent === 'ui.contract.v2'
        && params.op === 'action_open'
        && Number(params.record_id || params.recordId || params.res_id || 0) === Number(target.record_id);
    } catch {
      return false;
    }
  }, { timeout: 45000 });
}
async function normalizedDeniedSubmitEvidence(response, evidenceLabel) {
  const envelope = await response.json();
  const data = envelope?.data || envelope?.result?.data || envelope?.result || {};
  const rules = Array.isArray(data?.actionContract?.actionRuleList) ? data.actionContract.actionRuleList : [];
  const statuses = Array.isArray(data?.statusContract?.buttonStatus) ? data.statusContract.buttonStatus : [];
  const submitRules = rules.filter((row) => row?.backendIdentity === 'button:object:action_submit');
  const submitStatuses = statuses.filter((row) => row?.backendIdentity === 'button:object:action_submit');
  const evidence = {
    rules: submitRules.map((row) => ({
      actionKey: row.actionKey || '', backendIdentity: row.backendIdentity || '', label: row.label || '',
      allowed: row.allowed, enabled: row.enabled, disabled: row.disabled,
      visibleProfiles: row.visibleProfiles || [], presentation: row.presentation || {},
    })),
    statuses: submitStatuses.map((row) => ({
      visible: row.visible, disabled: row.disabled, reasonCode: row.reasonCode || '',
    })),
  };
  console.log(`[frontend_delivery_hardening] NORMALIZED_ACTION_DIAGNOSTIC ${evidenceLabel} ${JSON.stringify(evidence)}`);
  check(submitRules.length === 1, `${evidenceLabel}: normalized action_submit count must be 1; evidence=${JSON.stringify(evidence)}`);
  check(submitRules[0].allowed === false, `${evidenceLabel}: finance manager unexpectedly allowed action_submit`);
  check(submitRules[0].enabled === false, `${evidenceLabel}: finance manager unexpectedly enabled action_submit`);
  check(Array.isArray(submitRules[0].visibleProfiles) && submitRules[0].visibleProfiles.includes('readonly'), `${evidenceLabel}: normalized action_submit missing readonly profile`);
  check(submitStatuses.length === 1, `${evidenceLabel}: normalized action_submit status count must be 1`);
  check(submitStatuses[0].visible === false && submitStatuses[0].disabled === true, `${evidenceLabel}: denied action_submit status was not fail-closed; evidence=${JSON.stringify(evidence)}`);
  return evidence;
}
async function canonicalCancelAction(page, evidenceLabel, normalizedEvidence = null) {
  if (normalizedEvidence) await normalizedEvidence;
  const selector = '.template-page-header-actions button[data-backend-identity="button:object:action_cancel"]';
  let action = page.locator(selector);
  if (!(await action.count()) || !(await action.first().isVisible())) {
    const more = page.locator('.form-header-more-actions > summary').filter({ hasText: /^更多操作$/ }).first();
    if (await more.count()) {
      await more.focus();
      await more.press('Enter');
    }
    action = page.locator(selector);
  }
  const actions = await page.locator('.template-page-header-actions button').evaluateAll((buttons) => buttons.map((button) => ({
    text: String(button.textContent || '').replace(/\s+/g, ' ').trim(),
    actionKey: button.getAttribute('data-action-key') || '',
    backendIdentity: button.getAttribute('data-backend-identity') || '',
    method: button.getAttribute('data-action-method') || '',
    allowed: button.getAttribute('data-action-allowed') || '',
    enabled: button.getAttribute('data-action-enabled') || '',
    visibleProfiles: button.getAttribute('data-visible-profiles') || '',
    disabled: button instanceof HTMLButtonElement ? button.disabled : false,
    visible: Boolean(button.getClientRects().length),
  })));
  console.log(`[frontend_delivery_hardening] ACTION_DIAGNOSTIC ${evidenceLabel} ${JSON.stringify(actions)}`);
  check(await action.count() === 1, `${evidenceLabel}: canonical action_cancel count must be 1; actions=${JSON.stringify(actions)}`);
  const button = action.first();
  check(await button.isVisible(), `${evidenceLabel}: canonical action_cancel is not visible; actions=${JSON.stringify(actions)}`);
  const metadata = await button.evaluate((node) => ({
    text: String(node.textContent || '').replace(/\s+/g, ' ').trim(),
    allowed: node.getAttribute('data-action-allowed'),
    enabled: node.getAttribute('data-action-enabled'),
    visibleProfiles: String(node.getAttribute('data-visible-profiles') || '').split(',').filter(Boolean),
    disabled: node instanceof HTMLButtonElement ? node.disabled : true,
  }));
  check(metadata.text === '取消', `${evidenceLabel}: canonical action_cancel label=${metadata.text || '<empty>'}, expected=取消`);
  check(metadata.allowed === 'true', `${evidenceLabel}: canonical action_cancel allowed=${metadata.allowed}`);
  check(metadata.enabled === 'true', `${evidenceLabel}: canonical action_cancel enabled=${metadata.enabled}`);
  check(metadata.visibleProfiles.includes('readonly'), `${evidenceLabel}: canonical action_cancel missing readonly profile`);
  check(metadata.disabled === false, `${evidenceLabel}: canonical action_cancel rendered disabled`);
  return button;
}
function median(values) { const rows = [...values].sort((a, b) => a - b); return rows[Math.floor(rows.length / 2)] || 0; }
function percentile95(values) {
  const rows = [...values].sort((a, b) => a - b);
  return rows[Math.max(0, Math.ceil(rows.length * 0.95) - 1)] || 0;
}
function stats(values) {
  return {
    samples_ms: values,
    sample_count: values.length,
    median_ms: median(values),
    p95_ms: percentile95(values),
    max_ms: Math.max(...values, 0),
    slowest_ms: Math.max(...values, 0),
  };
}
async function time(run) { const start = performance.now(); await run(); return Math.round(performance.now() - start); }
function capture(page) {
  const state = {
    console: [], pageerror: [], unhandled: [], http: [], expectedHttp: [], expectedConsole: [],
    network: [], expectForbidden: false, expectedConsoleAllowance: 0, pendingExpectedForbiddenResponses: 0,
    requestCounts: {}, relationCandidateCounts: {},
  };
  runtimeByPage.set(page, state);
  page.on('request', (request) => {
    if (request.url().includes('/api/v1/intent')) {
      let payload = {};
      try { payload = JSON.parse(request.postData() || '{}'); } catch {}
      state.network.push({
        event: 'request',
        intent: payload.intent || '',
        op: payload.params?.op || '',
        model: payload.params?.model || '',
      });
      const requestKey = `${payload.intent || ''}:${payload.params?.op || ''}:${payload.params?.model || ''}`;
      state.requestCounts[requestKey] = Number(state.requestCounts[requestKey] || 0) + 1;
      const fields = Array.isArray(payload.params?.fields) ? payload.params.fields : [];
      const isRelationCandidateEnumeration = payload.intent === 'api.data'
        && payload.params?.op === 'list'
        && Number(payload.params?.limit || 0) >= 80
        && fields.length > 0
        && fields.every((field) => ['id', 'name', 'display_name'].includes(String(field)));
      if (isRelationCandidateEnumeration) {
        const candidateKey = String(payload.params?.model || '');
        state.relationCandidateCounts[candidateKey] = Number(state.relationCandidateCounts[candidateKey] || 0) + 1;
      }
      state.network = state.network.slice(-30);
    }
    if (!state.expectForbidden || !request.url().includes('/api/v1/intent')) return;
    try {
      const body = JSON.parse(request.postData() || '{}');
      // The denied surface may encode the target model in either the v1 or v2
      // contract shape.  The request is authoritative here: this flag is only
      // enabled while opening the deliberately forbidden responsive surface.
      if (body.intent === 'ui.contract.v2') state.pendingExpectedForbiddenResponses += 1;
    } catch {}
  });
  page.on('console', (message) => {
    if (message.type() !== 'error' || /favicon|ResizeObserver/i.test(message.text())) return;
    if (/Failed to load resource/i.test(message.text()) && state.expectedConsoleAllowance > 0) {
      state.expectedConsoleAllowance -= 1;
      state.expectedConsole.push(message.text());
      return;
    }
    state.console.push(message.text());
  });
  page.on('pageerror', (error) => state.pageerror.push(error.message));
  page.on('response', (response) => {
    if (response.url().includes('/api/v1/intent')) {
      let payload = {};
      try { payload = JSON.parse(response.request().postData() || '{}'); } catch {}
      state.network.push({
        event: 'response',
        status: response.status(),
        intent: payload.intent || '',
        op: payload.params?.op || '',
        model: payload.params?.model || '',
      });
      state.network = state.network.slice(-30);
    }
    if (response.status() < 400 || !response.url().includes('/api/v1/')) return;
    let requestPayload = {};
    try { requestPayload = JSON.parse(response.request().postData() || '{}'); } catch {}
    const row = {
      status: response.status(),
      url: response.url(),
      intent: requestPayload.intent || '',
      op: requestPayload.params?.op || '',
      model: requestPayload.params?.model || '',
      res_id: Number(requestPayload.params?.res_id || 0) || 0,
    };
    const intent = row.intent;
    if (
      response.status() === 403
      && intent === 'ui.contract.v2'
      && (state.pendingExpectedForbiddenResponses > 0 || state.expectForbidden)
    ) {
      if (state.pendingExpectedForbiddenResponses > 0) state.pendingExpectedForbiddenResponses -= 1;
      state.expectedHttp.push(row);
      const consoleIndex = state.console.findIndex((line) => /Failed to load resource/i.test(line));
      if (consoleIndex >= 0) state.expectedConsole.push(...state.console.splice(consoleIndex, 1));
      else state.expectedConsoleAllowance += 1;
      return;
    }
    state.http.push(row);
  });
  return state;
}
function assertRuntimeClean(state, label, allowed = []) {
  check(!state.console.length, `${label}: console=${state.console.join(' | ')} http=${JSON.stringify(state.http)}`);
  check(!state.pageerror.length, `${label}: pageerror=${state.pageerror.join(' | ')}`);
  const bad = state.http.filter((row) => !allowed.includes(row.status));
  check(!bad.length, `${label}: http=${JSON.stringify(bad)}`);
}
function resetRuntime(state) {
  state.console.length = 0; state.pageerror.length = 0; state.unhandled.length = 0; state.http.length = 0;
}
async function gotoLogin(page) {
  try {
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  } catch (error) {
    if (!new URL(page.url()).pathname.includes('/login')) throw error;
  }
  await page.waitForURL((url) => url.pathname.includes('/login'), { timeout: 45000 });
  await page.locator('#login-username, input[autocomplete="username"]').first().waitFor({ state: 'visible', timeout: 45000 });
}
async function login(page, user, keyboard = false) {
  await gotoLogin(page);
  const username = page.locator('#login-username, input[autocomplete="username"]').first();
  const password = page.locator('#login-password, input[autocomplete="current-password"]').first();
  await username.fill(user);
  await password.fill(PASSWORD);
  const db = page.locator('input').nth(2);
  if (await db.isEnabled()) await db.fill(DB_NAME);
  const loginResponsePromise = page.waitForResponse((response) => {
    if (!response.url().includes('/api/v1/intent')) return false;
    try {
      return JSON.parse(response.request().postData() || '{}').intent === 'login';
    } catch {
      return false;
    }
  }, { timeout: 45000 });
  if (keyboard) await password.press('Enter');
  else await page.getByRole('button', { name: /^登录$/ }).click();
  const loginResponse = await loginResponsePromise;
  let loginEnvelope = {};
  try { loginEnvelope = await loginResponse.json(); } catch {}
  const envelopeCode = Number(loginEnvelope?.code || loginEnvelope?.error?.code || 0);
  const rejected = !loginResponse.ok() || loginEnvelope?.ok === false || envelopeCode >= 400;
  check(
    !rejected,
    `login intent rejected http=${loginResponse.status()} code=${envelopeCode || 'unknown'} error_code=${String(loginEnvelope?.error?.error_code || loginEnvelope?.error_code || 'unknown')}`,
  );
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45000 });
  await page.locator('.layout-shell').waitFor({ timeout: 45000 });
}
async function logout(page) {
  const logoutButton = page.getByRole('button', { name: '退出登录' });
  if (!(await logoutButton.isVisible().catch(() => false))) {
    const menuButton = page.getByRole('button', { name: '菜单', exact: true });
    if (await menuButton.isVisible().catch(() => false)) await menuButton.click();
  }
  await logoutButton.click();
  await page.waitForURL((url) => url.pathname.includes('/login'), { timeout: 30000 });
}
async function waitBusiness(page) {
  await page.locator('.financial-workspace, .product-work, .sc-product-main-surface, .sc-state-panel').first().waitFor({ timeout: 45000 });
}
async function open(page, route) {
  await page.goto(`${BASE_URL}${route}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await waitBusiness(page);
}
async function selectCompany(page, label) {
  await page.getByRole('button', { name: '公司空间：切换公司', exact: true }).click();
  const companyPanel = page.locator('.workspace-scope-panel').filter({
    has: page.getByRole('heading', { name: '公司空间', exact: true }),
  });
  await companyPanel.waitFor({ state: 'visible', timeout: 30000 });
  const companyOption = companyPanel.locator('.workspace-scope-options > button').filter({ hasText: label }).first();
  await companyOption.waitFor({ state: 'visible', timeout: 30000 });
  if (await companyOption.getAttribute('aria-current') === 'true') {
    await companyOption.click();
    return false;
  }
  const initialized = page.waitForResponse((response) => {
    if (!response.url().includes('/api/v1/intent')) return false;
    try { return JSON.parse(response.request().postData() || '{}').intent === 'system.init'; } catch { return false; }
  }, { timeout: 45000 });
  await companyOption.click();
  const initializedResponse = await initialized;
  check(initializedResponse.ok(), `company switch system.init failed: HTTP ${initializedResponse.status()}`);
  await companyPanel.waitFor({ state: 'hidden', timeout: 45000 });
  return true;
}
async function navigateSpa(page, route, readySelector = '.sc-product-main-surface, .financial-workspace, .product-work, .sc-state-panel') {
  await page.evaluate((target) => {
    window.history.pushState({}, '', target);
    window.dispatchEvent(new PopStateEvent('popstate'));
  }, route);
  const target = new URL(route, BASE_URL);
  await page.waitForURL((url) => (
    url.pathname === target.pathname
    && [...target.searchParams.entries()].every(([key, value]) => url.searchParams.get(key) === value)
  ), { timeout: 45000 });
  // The route's stable UI is authoritative: some surfaces issue api.data while
  // others use a product intent or satisfy metadata from the initialized store.
  // Waiting for one guessed intent turns a valid navigation into a false timeout.
  await page.waitForTimeout(50);
  try {
    await page.locator(readySelector).first().waitFor({ state: 'visible', timeout: 45000 });
  } catch (error) {
    const runtime = runtimeByPage.get(page);
    const diagnostic = await page.evaluate(() => ({
      url: window.location.href,
      title: document.title,
      bodyText: document.body.innerText.slice(0, 1200),
      statePanels: Array.from(document.querySelectorAll('.sc-state-panel')).map((node) => node.textContent?.trim().slice(0, 400) || ''),
      workspaces: Array.from(document.querySelectorAll('[data-workspace-kind]')).map((node) => node.getAttribute('data-workspace-kind')),
    })).catch(() => ({ url: page.url() }));
    throw new Error(`${error instanceof Error ? error.message : String(error)} diagnostic=${JSON.stringify({
      ...diagnostic,
      console: runtime?.console || [],
      pageerror: runtime?.pageerror || [],
      http: runtime?.http || [],
      network: runtime?.network || [],
    })}`);
  }
  await page.waitForTimeout(50);
}
async function assertNoOverflow(page, label) {
  const size = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }));
  check(size.scroll <= size.client + 1, `${label}: overflow ${size.scroll}/${size.client}`);
}
async function axe(page, label) {
  const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
  const blocking = result.violations.filter((item) => ['critical', 'serious'].includes(item.impact));
  return { label, violations: result.violations.map((item) => ({
    id: item.id,
    impact: item.impact,
    node_count: item.nodes.length,
    help: item.help,
    nodes: item.nodes.map((node) => ({ target: node.target, html: node.html, failure_summary: node.failureSummary })),
  })), blocking: blocking.length };
}
function fulfillError(route, status, code, message) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify({ error: { message, reason_code: code, retryable: true } }) });
}
async function interceptNextBusiness(page, handler, expectedTarget) {
  let used = false;
  const callback = async (route) => {
    let payload = {};
    try { payload = JSON.parse(route.request().postData() || '{}'); } catch {}
    const intent = payload.intent || '';
    const params = payload.params || {};
    const ids = Array.isArray(params.ids) ? params.ids.map(Number) : [];
    const isTargetRead = intent === 'api.data' && params.op === 'read'
      && params.model === expectedTarget.model && ids.includes(Number(expectedTarget.record_id));
    const isTargetActionContract = intent === 'ui.contract.v2' && params.op === 'action_open'
      && Number(params.action_id || 0) === Number(expectedTarget.action_id)
      && Number(params.record_id || 0) === Number(expectedTarget.record_id);
    const isTargetModelContract = intent === 'ui.contract.v2' && params.op === 'model'
      && params.model === expectedTarget.model
      && Number(params.record_id || 0) === Number(expectedTarget.record_id);
    const isTargetContract = isTargetActionContract || isTargetModelContract;
    if (isTargetRead || isTargetContract) {
      if (!used) console.log(`[delivery-hardening] injecting ${intent}:${params.op}:${params.model || ''}:${params.record_id || ids.join(',')}`);
      used = true;
      await handler(route, intent);
      return;
    }
    await route.continue();
  };
  await page.route('**/api/v1/intent**', callback);
  return async () => page.unroute('**/api/v1/intent**', callback);
}

async function main() {
  for (const key of ['project', 'contract', 'settlement', 'payment_request', 'payment_execution', 'journey_request', 'work_settlement']) check(TARGETS[key]?.record_id > 0, `missing ${key}`);
  check(PERF_RUNS >= 5, `performance sample count must be >=5, got ${PERF_RUNS}`);
  const acceptanceLease = await acquireAcceptanceLease({ root: acceptance.artifactRoot, mode: 'shared-read', owner: { tool: 'delivery-hardening', profile: acceptance.profile, source_sha: process.env.GIT_SHA || '' } });
  const journeyName = String(TARGETS.journey_request.display_name || '').trim();
  check(journeyName.length > 0, 'missing journey_request display_name');
  const journeyIdentity = String(TARGETS.journey_request.record_identity || '').trim();
  check(journeyIdentity.length > 0, 'missing journey_request record_identity');
  const browser = await launchChromium({ headless: true });
  const browserVersion = browser.version();
  const generatedAt = new Date().toISOString();
  const environment = {
    browser: browserVersion,
    viewport: { width: 1440, height: 900 },
    platform: `${os.platform()}-${os.arch()}`,
    cpu_count: os.cpus().length,
    memory_mb: Math.round(os.totalmem() / 1024 / 1024),
    database: DB_NAME,
    base_url: BASE_URL,
  };
  const report = {
    schema_version: 'frontend-delivery-hardening/v2',
    git_sha: process.env.GIT_SHA || '',
    generated_at: generatedAt,
    environment,
    database: DB_NAME,
    base_url: BASE_URL,
    pass: false,
    journeys: {},
    runtime: {},
  };
  const errorRecovery = {
    schema_version: 'frontend-error-recovery/v2',
    git_sha: process.env.GIT_SHA || '',
    generated_at: generatedAt,
    environment,
  };
  const accessibility = {
    schema_version: 'frontend-accessibility/v2',
    git_sha: process.env.GIT_SHA || '',
    generated_at: generatedAt,
    environment,
    engine: '@axe-core/playwright@4.10.2',
    ruleset: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'],
    scans: [],
    violations: 0,
    critical: 0,
    serious: 0,
    blocking: 0,
    result: 'NOT_RUN',
  };
  const responsive = {
    schema_version: 'frontend-responsive/v2',
    git_sha: process.env.GIT_SHA || '',
    generated_at: generatedAt,
    environment,
    viewports: [],
    pages: [],
    horizontal_overflow: 0,
  };
  const performanceReport = {
    schema_version: 'frontend-performance/v2',
    git_sha: process.env.GIT_SHA || '',
    generated_at: generatedAt,
    environment,
    warmup_runs_per_scenario: 1,
    warmup_runs: {},
    runs_per_scenario: PERF_RUNS,
    scenarios: {},
    budgets: performanceBudgets.scenarios || {},
    budget_source: PERF_BUDGET_PATH,
    relative_regression_percent: null,
    result: 'NOT_RUN',
  };
  let context;
  try {
    context = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'zh-CN' });
    await installEvidenceSensitivityTracker(context);
    await context.tracing.start({ screenshots: true, snapshots: true, sources: false });
    let page = await context.newPage();
    let runtime = capture(page);
    const releasedNavigation = captureReleasedNavigation(page);
    await login(page, FINANCE_LOGIN);
    applyReleasedNavigationTarget(
      TARGETS,
      ['payment_request', 'journey_request'],
      await releasedNavigation.targetByMenuXmlid(TARGETS.payment_request.menu_xmlid),
    );

    if (process.env.DELIVERY_HARDENING_A11Y_PROBE === '1') {
      await open(page, recordRoute(TARGETS.work_settlement));
      await page.getByRole('button', { name: '新建付款申请' }).click();
      await page.locator('[data-field-name="amount"] input').first().waitFor({ timeout: 45000 });
      accessibility.scans.push(await axe(page, 'payment-form'));
      const removeProbe = await interceptNextBusiness(page, (route) => route.abort('failed'), TARGETS.payment_request);
      await page.goto(`${BASE_URL}${recordRoute(TARGETS.payment_request)}`, { waitUntil: 'domcontentloaded' });
      await page.getByRole('heading', { name: '网络连接异常' }).waitFor({ timeout: 45000 });
      accessibility.scans.push(await axe(page, 'network-error'));
      await removeProbe();
      accessibility.blocking = accessibility.scans.reduce((sum, row) => sum + row.blocking, 0);
      accessibility.violations = accessibility.scans.reduce((sum, row) => sum + row.violations.length, 0);
      accessibility.critical = accessibility.scans.reduce((sum, row) => sum + row.violations.filter((item) => item.impact === 'critical').length, 0);
      accessibility.serious = accessibility.scans.reduce((sum, row) => sum + row.violations.filter((item) => item.impact === 'serious').length, 0);
      accessibility.result = accessibility.blocking === 0 ? 'PASS' : 'FAIL';
      fs.writeFileSync(path.join(OUT, 'accessibility-probe.json'), `${JSON.stringify(accessibility, null, 2)}\n`);
      console.log(`[verify.frontend.delivery_hardening.a11y_probe] findings=${accessibility.blocking}`);
      return;
    }

    if (!PERF_ONLY) {
    // J09: network, conflict and expired-session recovery use the real current request.
    let remove = await interceptNextBusiness(page, (route) => route.abort('failed'), TARGETS.payment_request);
    await open(page, recordRoute(TARGETS.payment_request));
    await page.getByRole('heading', { name: '网络连接异常' }).waitFor({ timeout: 30000 });
    await remove();
    await page.getByRole('button', { name: '重试' }).click();
    await page.locator(FORM_SURFACE_SELECTOR).waitFor({ timeout: 45000 });
    errorRecovery.network_retry = 'PASS';

    remove = await interceptNextBusiness(page, (route) => fulfillError(route, 409, 'CONFLICT', 'stale write conflict'), TARGETS.payment_request);
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.getByRole('heading', { name: '数据已发生变化' }).waitFor({ timeout: 30000 });
    await remove();
    await page.getByRole('button', { name: '获取最新数据' }).click();
    await page.locator(FORM_SURFACE_SELECTOR).waitFor({ timeout: 45000 });
    errorRecovery.conflict_refresh = 'PASS';

    remove = await interceptNextBusiness(page, (route) => fulfillError(route, 401, 'SESSION_EXPIRED', 'expired'), TARGETS.payment_request);
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForURL(/\/login\?reason=session_expired/, { timeout: 30000 });
    check(!page.url().includes('redirect=') && new URL(page.url()).pathname === '/login', 'expired session retained sensitive route');
    await remove();
    errorRecovery.session_expired = 'PASS';
    report.journeys.J09 = 'PASS';
    await page.waitForTimeout(300);
    check(!runtime.pageerror.length, `J09 pageerror=${runtime.pageerror.join(' | ')}`);
    check(runtime.console.every((line) => /Failed to load resource/i.test(line)), `J09 unexpected console=${runtime.console.join(' | ')}`);
    check(runtime.http.every((row) => [401, 409].includes(row.status)), `J09 unexpected HTTP=${JSON.stringify(runtime.http)}`);
    errorRecovery.expected_injected_browser_errors = { console: runtime.console.length, http: runtime.http.length };
    await page.close();
    page = await context.newPage();
    runtime = capture(page);

    // J10: narrow-screen keyboard path and native dialog focus containment/restore.
    await page.setViewportSize({ width: 390, height: 844 });
    await login(page, FINANCE_LOGIN, true);
    await page.getByRole('button', { name: '我的工作' }).focus();
    await page.keyboard.press('Enter');
    await page.locator('.product-work').waitFor({ timeout: 45000 });
    await page.locator('.count-card[data-section-key="todo"]').press('Enter');
    const cardButton = page.locator('.work-section[data-section-key="todo"] .work-card').filter({ hasText: journeyName }).getByRole('button', { name: '打开详情' }).first();
    const workUrl = page.url();
    await cardButton.focus(); await cardButton.press('Enter');
    await page.waitForFunction((previous) => window.location.href !== previous, workUrl, { timeout: 45000 });
    check(new URL(page.url()).pathname.startsWith('/r/payment.request/'), `J10 My Work target route invalid: ${page.url()}`);
    const detailIdentity = page.locator(`.layout-shell[data-page-identity-title="${journeyIdentity}"]`).first();
    await detailIdentity.waitFor({ timeout: 45000 });
    check((await page.title()).startsWith(`${journeyIdentity} - `), 'detail document title did not use the concise stable record identity');
    const submitContractResponse = waitForRecordContractResponse(page, TARGETS.journey_request);
    await open(page, recordRoute(TARGETS.journey_request));
    const submitEvidence = submitContractResponse.then((response) => normalizedDeniedSubmitEvidence(response, 'J10'));
    const cancel = await canonicalCancelAction(page, 'J10', submitEvidence);
    await cancel.focus(); await cancel.press('Enter');
    const dialog = page.getByRole('dialog');
    await dialog.waitFor({ timeout: 15000 });
    check(await dialog.getByRole('button', { name: '确认取消' }).evaluate((node) => node === document.activeElement), 'dialog initial focus missing');
    await page.keyboard.press('Tab'); await page.keyboard.press('Tab');
    check(await dialog.evaluate((node) => node.contains(document.activeElement)), 'dialog focus escaped');
    await page.keyboard.press('Escape');
    check(await cancel.evaluate((node) => node === document.activeElement), 'dialog focus did not return');
    await assertNoOverflow(page, 'J10');
    report.journeys.J10 = 'PASS';

    // J11: force system.init response reordering; epoch must retain only final company B.
    await page.setViewportSize({ width: 1440, height: 900 });
    let initSequence = 0;
    const reorder = async (route) => {
      let intent = ''; try { intent = JSON.parse(route.request().postData() || '{}').intent || ''; } catch {}
      if (intent === 'system.init') {
        initSequence += 1;
        await new Promise((resolve) => setTimeout(resolve, initSequence === 1 ? 900 : initSequence === 2 ? 500 : 80));
      }
      await route.continue();
    };
    await page.route('**/api/v1/intent**', reorder);
    await selectCompany(page, 'FE Company B');
    await selectCompany(page, 'FE Company A');
    await selectCompany(page, 'FE Company B');
    await page.waitForTimeout(1800);
    await page.goto(`${BASE_URL}/my-work`, { waitUntil: 'domcontentloaded' });
    await page.locator('.product-work').waitFor({ timeout: 45000 });
    const workText = await page.locator('body').innerText();
    check(workText.includes('FE-C-PR-001') && !workText.includes(journeyName), 'stale company response polluted final B context');
    await page.unroute('**/api/v1/intent**', reorder);
    await logout(page); await login(page, PROJECT_MEMBER_LOGIN);
    await page.goto(`${BASE_URL}/my-work`); await page.locator('.product-work').waitFor({ timeout: 45000 });
    const memberText = await page.locator('body').innerText();
    check(!/FE-C-PR-001|FE-JOURNEY-PAYMENT|FE-DELIVERY-HARDENING|80\.00|100\.00/.test(memberText), 'finance data survived role switch');
    report.journeys.J11 = 'PASS';
    assertRuntimeClean(runtime, 'J10-J11');

    // Representative responsive and accessibility matrix. Existing role permissions are preserved.
    const surfaces = [
      { name: 'login', route: '/login', role: '' }, { name: 'home', route: '/', role: FINANCE_LOGIN }, { name: 'my-work', route: '/my-work', role: FINANCE_LOGIN },
      { name: 'project-list', route: listRoute(TARGETS.project), role: PROJECT_MANAGER_LOGIN }, { name: 'project-detail', route: recordRoute(TARGETS.project), role: PROJECT_MANAGER_LOGIN },
      { name: 'contract-list', route: listRoute(TARGETS.contract), role: CONTRACT_OPERATOR_LOGIN }, { name: 'contract-detail', route: recordRoute(TARGETS.contract), role: CONTRACT_OPERATOR_LOGIN },
      { name: 'settlement-list', route: listRoute(TARGETS.settlement), role: FINANCE_LOGIN }, { name: 'settlement-detail', route: recordRoute(TARGETS.settlement), role: FINANCE_LOGIN },
      { name: 'payment-list', route: listRoute(TARGETS.payment_request), role: FINANCE_LOGIN }, { name: 'payment-detail', route: recordRoute(TARGETS.payment_request), role: FINANCE_LOGIN },
      { name: 'payment-form', route: recordRoute(TARGETS.work_settlement), role: FINANCE_LOGIN, mode: 'form' },
      { name: 'execution-detail', route: recordRoute(TARGETS.payment_execution), role: FINANCE_LOGIN },
      { name: 'approval-dialog', route: recordRoute(TARGETS.journey_request), role: FINANCE_LOGIN, mode: 'dialog' },
      { name: 'denied', route: recordRoute(TARGETS.payment_request), role: PROJECT_MEMBER_LOGIN },
      { name: 'not-found', route: `/r/payment.request/999999?action_id=${TARGETS.payment_request.action_id}&menu_id=${TARGETS.payment_request.menu_id}`, role: FINANCE_LOGIN },
      { name: 'network-error', route: recordRoute(TARGETS.payment_request), role: FINANCE_LOGIN, mode: 'network' },
    ];
    const noEagerCandidateSurfaces = new Set([
      'contract-detail', 'settlement-detail', 'payment-detail', 'payment-form', 'execution-detail',
    ]);
    for (const viewport of [{ width: 1440, height: 900 }, { width: 1280, height: 800 }, { width: 768, height: 1024 }, { width: 390, height: 844 }]) {
      responsive.viewports.push(viewport);
      await page.setViewportSize(viewport);
      await logout(page).catch(() => {});
      let currentRole = '';
      for (const surface of surfaces) {
        let removeFault = null;
        let faultSnapshot = null;
        const constructionContractCandidateCount = Number(runtime.relationCandidateCounts['construction.contract'] || 0);
        if (!surface.role) {
          await gotoLogin(page);
          currentRole = '';
        } else {
          if (currentRole !== surface.role || page.url().includes('/login')) {
            if (currentRole) await logout(page).catch(() => {});
            await login(page, surface.role);
            currentRole = surface.role;
          }
          if (surface.name === 'denied') {
            faultSnapshot = { console: runtime.console.length, http: runtime.http.length, pageerror: runtime.pageerror.length };
            runtime.expectForbidden = true;
          }
          if (surface.name === 'not-found') {
            faultSnapshot = { console: runtime.console.length, http: runtime.http.length, pageerror: runtime.pageerror.length };
          }
          if (surface.mode === 'network') {
            faultSnapshot = { console: runtime.console.length, http: runtime.http.length, pageerror: runtime.pageerror.length };
            removeFault = await interceptNextBusiness(page, (route) => route.abort('failed'), TARGETS.payment_request);
          }
          await page.goto(`${BASE_URL}${surface.route}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
          if (surface.mode === 'form') {
            await page.locator(FORM_SURFACE_SELECTOR).waitFor({ timeout: 45000 });
            await page.getByRole('button', { name: '新建付款申请' }).click();
            await page.locator('[data-field-name="amount"] input').first().waitFor({ timeout: 45000 });
          } else if (surface.mode === 'dialog') {
            await page.locator(FORM_SURFACE_SELECTOR).waitFor({ timeout: 45000 });
            const cancelAction = await canonicalCancelAction(page, `${surface.name}-${viewport.width}`);
            await cancelAction.click();
            await page.getByRole('dialog').waitFor({ timeout: 15000 });
          } else if (surface.mode === 'network') {
            await page.getByRole('heading', { name: '网络连接异常' }).waitFor({ timeout: 45000 });
          } else if (surface.name === 'denied') {
            await page.locator('main').getByRole('heading', { name: '访问受限', exact: true }).waitFor({ timeout: 45000 });
          } else {
            await waitForSurfaceReady(page, surface);
          }
        }
        await assertNoOverflow(page, `${surface.name}-${viewport.width}`);
        const shot = path.join(SCREENSHOTS, `${surface.name}-${viewport.width}x${viewport.height}.png`);
        const screenshot = await captureEvidenceScreenshot(page, { path: shot, fullPage: false });
        const visual = await assertMeaningfulScreenshot(page, screenshot, `${surface.name}-${viewport.width}x${viewport.height}`);
        responsive.pages.push({ name: surface.name, role: surface.role || 'anonymous', viewport, pass: true, screenshot: shot, visual });
        if (viewport.width === 1440) {
          const scan = await axe(page, surface.name);
          accessibility.scans.push(scan); accessibility.blocking += scan.blocking;
        }
        if (noEagerCandidateSurfaces.has(surface.name)) {
          await page.waitForTimeout(250);
          check(
            Number(runtime.relationCandidateCounts['construction.contract'] || 0) === constructionContractCandidateCount,
            `${surface.name}: surface eagerly enumerated construction.contract relation candidates`,
          );
        }
        if (surface.mode === 'dialog') await page.keyboard.press('Escape');
        if (surface.name === 'not-found' && faultSnapshot) {
          await page.waitForTimeout(250);
          const expectedConsole = runtime.console.slice(faultSnapshot.console);
          const expectedHttp = runtime.http.slice(faultSnapshot.http);
          check(expectedConsole.every((line) => /Failed to load resource/i.test(line)), `not-found surface unexpected console=${expectedConsole.join(' | ')}`);
          check(expectedHttp.length > 0 && expectedHttp.every((row) => row.status === 404 && ['api.data', 'chatter.timeline'].includes(row.intent)), `not-found surface unexpected HTTP=${JSON.stringify(expectedHttp)}`);
          check(runtime.pageerror.length === faultSnapshot.pageerror, 'not-found surface caused pageerror');
          runtime.expectedConsole.push(...expectedConsole);
          runtime.expectedHttp.push(...expectedHttp);
          runtime.console.length = faultSnapshot.console;
          runtime.http.length = faultSnapshot.http;
        }
        if (surface.name === 'denied' && faultSnapshot) {
          await page.waitForTimeout(250);
          runtime.expectForbidden = false;
          const expectedConsole = runtime.console.slice(faultSnapshot.console);
          const expectedHttp = runtime.http.slice(faultSnapshot.http);
          check(expectedConsole.every((line) => /Failed to load resource/i.test(line)), `denied surface unexpected console=${expectedConsole.join(' | ')}`);
          check(expectedHttp.every((row) => row.status === 403), `denied surface unexpected HTTP=${JSON.stringify(expectedHttp)}`);
          check(runtime.pageerror.length === faultSnapshot.pageerror, 'denied surface caused pageerror');
          runtime.console.length = faultSnapshot.console;
          runtime.http.length = faultSnapshot.http;
        }
        if (removeFault) {
          await removeFault();
          await page.getByRole('button', { name: '重试' }).click();
          await page.locator(FORM_SURFACE_SELECTOR).waitFor({ timeout: 45000 });
          const injectedConsole = runtime.console.slice(faultSnapshot.console);
          check(injectedConsole.every((line) => /Failed to load resource/i.test(line)), `responsive network unexpected console=${injectedConsole.join(' | ')}`);
          check(runtime.pageerror.length === faultSnapshot.pageerror, 'responsive network caused pageerror');
          runtime.console.length = faultSnapshot.console;
          runtime.http.length = faultSnapshot.http;
        }
      }
    }
    check(accessibility.blocking === 0, `accessibility blocking findings=${accessibility.blocking}`);
    }

    if (SKIP_PERF) {
      const performancePath = path.join(OUT, 'performance.json');
      check(fs.existsSync(performancePath), 'isolated performance evidence is missing');
      const isolatedPerformance = JSON.parse(fs.readFileSync(performancePath, 'utf8'));
      check(isolatedPerformance.schema_version === 'frontend-performance/v2', 'isolated performance evidence schema mismatch');
      check(isolatedPerformance.git_sha === (process.env.GIT_SHA || ''), 'isolated performance evidence SHA mismatch');
      check(isolatedPerformance.result === 'PASS', 'isolated performance evidence is not PASS');
      Object.assign(performanceReport, isolatedPerformance);
    } else {
      // Performance is a release signal, so measure it in a fresh renderer
      // before the full release journey can contribute memory, listener, axe,
      // or responsive-layout pressure. The Make release entrypoint runs this
      // PERF_ONLY phase first, then consumes its SHA-bound evidence here.
      await page.close();
      page = await context.newPage();
      runtime = capture(page);

      // Five-run fixed-runtime measurements: login and true SPA navigation, without fixture mutation.
      const performanceRequests = [];
      page.on('request', (request) => {
        if (!request.url().includes('/api/v1/intent')) return;
        try {
          const payload = JSON.parse(request.postData() || '{}');
          performanceRequests.push(`${payload.intent || ''}:${payload.params?.op || ''}:${payload.params?.model || ''}`);
        } catch {}
      });
      await page.setViewportSize({ width: 1440, height: 900 });
      await logout(page).catch(() => {});
      await login(page, FINANCE_LOGIN);
      await logout(page);
      await login(page, FINANCE_LOGIN);
      const loginSamples = [];
      for (let i = 0; i < PERF_RUNS; i += 1) {
        await logout(page);
        loginSamples.push(await time(() => login(page, FINANCE_LOGIN)));
      }
      performanceReport.scenarios.login_to_interactive = stats(loginSamples);
      for (const [name, route, readySelector] of [
        ['my_work', '/my-work', '.product-work'],
        ['payment_detail', recordRoute(TARGETS.payment_request), FORM_SURFACE_SELECTOR],
        ['settlement_detail', recordRoute(TARGETS.settlement), FORM_SURFACE_SELECTOR],
        ['execution_detail', recordRoute(TARGETS.payment_execution), FORM_SURFACE_SELECTOR],
      ]) {
        const samples = [];
        const requestSamples = [];
        if (name === 'my_work') {
          await page.goto(`${BASE_URL}/`, { waitUntil: 'domcontentloaded', timeout: 45000 });
          await page.waitForTimeout(2000);
        } else {
          await navigateSpa(page, '/my-work', '.product-work');
        }
        await navigateSpa(page, route, readySelector);
        for (let i = 0; i < PERF_RUNS; i += 1) {
          if (name === 'my_work') {
            await page.goto(`${BASE_URL}/`, { waitUntil: 'domcontentloaded', timeout: 45000 });
            await page.waitForTimeout(2000);
          } else {
            await navigateSpa(page, '/my-work', '.product-work');
          }
          const requestOffset = performanceRequests.length;
          samples.push(await time(() => navigateSpa(page, route, readySelector)));
          requestSamples.push(performanceRequests.slice(requestOffset));
        }
        if (name.endsWith('_detail')) {
          const repeatedContractLoads = requestSamples.flat().filter((row) => row.startsWith('ui.contract.v2:'));
          check(
            repeatedContractLoads.length === 0,
            `${name}: warmed retained detail page reloaded its primary contract ${repeatedContractLoads.length} time(s)`,
          );
        }
        performanceReport.scenarios[name] = { ...stats(samples), request_samples: requestSamples };
      }
      const formSamples = [];
      await navigateSpa(page, recordRoute(TARGETS.work_settlement), FORM_SURFACE_SELECTOR);
      await page.locator('#main-content').getByRole('button', { name: '新建付款申请', exact: true }).click();
      await page.waitForURL((url) => /\/payment\.request\/new$/.test(url.pathname), { timeout: 45000 });
      await page.locator('[data-field-name="amount"] input').first().waitFor({ timeout: 45000 });
      for (let i = 0; i < PERF_RUNS; i += 1) {
        await navigateSpa(page, recordRoute(TARGETS.work_settlement), FORM_SURFACE_SELECTOR);
        formSamples.push(await time(async () => {
          await page.locator('#main-content').getByRole('button', { name: '新建付款申请', exact: true }).click();
          await page.waitForURL((url) => /\/payment\.request\/new$/.test(url.pathname), { timeout: 45000 });
          await page.locator('[data-field-name="amount"] input').first().waitFor({ timeout: 45000 });
        }));
      }
      performanceReport.scenarios.form_open = stats(formSamples);
      const switchSamples = [];
      const companySwitchWarmupRuns = Number(performanceBudgets.company_switch_warmup_runs);
      check(
        Number.isInteger(companySwitchWarmupRuns) && companySwitchWarmupRuns >= PERF_RUNS,
        'governed company-switch warm-up count must be an integer no smaller than the measured sample count',
      );
      // system.init assembles the governed navigation and role projection. Give
      // both company scopes a governed bounded warm-up before measuring the
      // steady-state switch; samples still perform real alternating company
      // transitions and retain the unchanged absolute/relative budgets.
      let selectedCompanyLabel = '';
      for (let i = 0; i < companySwitchWarmupRuns; i += 1) {
        selectedCompanyLabel = i % 2 ? 'FE Company A' : 'FE Company B';
        await selectCompany(page, selectedCompanyLabel);
      }
      performanceReport.warmup_runs.company_switch = companySwitchWarmupRuns;
      for (let i = 0; i < PERF_RUNS; i += 1) {
        selectedCompanyLabel = selectedCompanyLabel === 'FE Company A' ? 'FE Company B' : 'FE Company A';
        switchSamples.push(await time(() => selectCompany(page, selectedCompanyLabel)));
      }
      performanceReport.scenarios.company_switch = stats(switchSamples);
      if (PERF_BASELINE_CAPTURE) {
        performanceReport.baseline_scope = 'login_initialized_navigation_and_governed_company_switch';
        performanceReport.result = 'CAPTURED';
        fs.writeFileSync(path.join(OUT, 'performance-baseline.json'), `${JSON.stringify(performanceReport, null, 2)}\n`);
        console.log('[verify.frontend.delivery_hardening.performance_baseline] CAPTURED');
        return;
      }
      const absoluteScenarioPass = Object.fromEntries(Object.entries(performanceReport.scenarios).map(([name, metrics]) => {
        const budget = performanceReport.budgets[name];
        check(budget, `performance budget missing: ${name}`);
        return [name, (
          metrics.sample_count >= Number(performanceBudgets.minimum_sample_count || 5)
          && metrics.median_ms <= Number(budget.median_ms)
          && metrics.p95_ms <= Number(budget.p95_ms)
          && metrics.max_ms <= Number(budget.max_ms)
        )];
      }));
      performanceReport.absolute_scenario_pass = absoluteScenarioPass;
      performanceReport.absolute_budget_pass = Object.values(absoluteScenarioPass).every(Boolean);
      if (PERF_BASELINE_PATH) {
        const baseline = JSON.parse(fs.readFileSync(PERF_BASELINE_PATH, 'utf8'));
        const relative = evaluateRelativePerformanceBudget({
          scenarios: performanceReport.scenarios,
          budgets: performanceReport.budgets,
          baseline,
          maximumRegressionPercent: performanceBudgets.maximum_relative_regression_percent,
        });
        performanceReport.metric_regression_percent = relative.metric_regression_percent;
        performanceReport.relative_regression_percent = relative.relative_regression_percent;
        performanceReport.relative_baseline_path = PERF_BASELINE_PATH;
        performanceReport.relative_budget_pass = relative.relative_budget_pass;
      } else {
        performanceReport.relative_budget_pass = false;
      }
      check(performanceReport.absolute_budget_pass || performanceReport.relative_budget_pass, `performance budget exceeded: ${JSON.stringify(performanceReport.scenarios)}`);
      performanceReport.result = 'PASS';
      if (PERF_ONLY) {
        fs.writeFileSync(path.join(OUT, 'performance.json'), `${JSON.stringify(performanceReport, null, 2)}\n`);
        fs.writeFileSync(path.join(OUT, 'performance-probe.json'), `${JSON.stringify(performanceReport, null, 2)}\n`);
        console.log('[verify.frontend.delivery_hardening.performance_probe] PASS');
        return;
      }
    }

    assertRuntimeClean(runtime, 'final delivery hardening runtime');
    accessibility.violations = accessibility.scans.reduce((sum, row) => sum + row.violations.length, 0);
    accessibility.critical = accessibility.scans.reduce((sum, row) => sum + row.violations.filter((item) => item.impact === 'critical').length, 0);
    accessibility.serious = accessibility.scans.reduce((sum, row) => sum + row.violations.filter((item) => item.impact === 'serious').length, 0);
    accessibility.result = accessibility.blocking === 0 ? 'PASS' : 'FAIL';
    errorRecovery.expected_denied_browser_errors = {
      console: runtime.expectedConsole.length,
      http: runtime.expectedHttp.length,
    };
    report.pass = true;
    report.evidence = responsive.pages.map((row) => ({ role: row.role, viewport: row.viewport, journey: 'responsive', surface: row.name, pass: row.pass, screenshot: row.screenshot }));
    report.runtime = {
      console: runtime.console,
      pageerror: runtime.pageerror,
      unhandled: runtime.unhandled,
      http: runtime.http,
    };
    await stopEvidenceTrace(context, context.pages(), path.join(TRACES, 'j09-j11-responsive-performance.zip'));
    fs.writeFileSync(path.join(OUT, 'report.json'), `${JSON.stringify(report, null, 2)}\n`);
    fs.writeFileSync(path.join(OUT, 'performance.json'), `${JSON.stringify(performanceReport, null, 2)}\n`);
    fs.writeFileSync(path.join(OUT, 'accessibility.json'), `${JSON.stringify(accessibility, null, 2)}\n`);
    fs.writeFileSync(path.join(OUT, 'responsive.json'), `${JSON.stringify(responsive, null, 2)}\n`);
    fs.writeFileSync(path.join(OUT, 'error-recovery.json'), `${JSON.stringify(errorRecovery, null, 2)}\n`);
    console.log(`[verify.frontend.delivery_hardening.browser] PASS J09-J11 responsive=${responsive.pages.length} accessibility_blocking=0`);
  } catch (error) {
    if (context) {
      const pages = context.pages();
      if (pages[0]) await captureEvidenceScreenshot(pages[0], { path: path.join(SCREENSHOTS, 'failure.png'), fullPage: true }).catch(() => {});
    }
    accessibility.violations = accessibility.scans.reduce((sum, row) => sum + row.violations.length, 0);
    accessibility.critical = accessibility.scans.reduce((sum, row) => sum + row.violations.filter((item) => item.impact === 'critical').length, 0);
    accessibility.serious = accessibility.scans.reduce((sum, row) => sum + row.violations.filter((item) => item.impact === 'serious').length, 0);
    accessibility.result = accessibility.scans.length > 0 && accessibility.blocking === 0 ? 'PASS' : 'NOT_RUN';
    // The release entrypoint measures performance in an isolated renderer and
    // then consumes that SHA-bound PASS evidence in the full browser matrix.
    // A later functional failure must not relabel valid performance evidence.
    if (performanceReport.result !== 'PASS') performanceReport.result = 'FAIL';
    fs.writeFileSync(path.join(OUT, 'report.json'), `${JSON.stringify(report, null, 2)}\n`);
    fs.writeFileSync(path.join(OUT, 'performance.json'), `${JSON.stringify(performanceReport, null, 2)}\n`);
    fs.writeFileSync(path.join(OUT, 'accessibility.json'), `${JSON.stringify(accessibility, null, 2)}\n`);
    fs.writeFileSync(path.join(OUT, 'responsive.json'), `${JSON.stringify(responsive, null, 2)}\n`);
    fs.writeFileSync(path.join(OUT, 'error-recovery.json'), `${JSON.stringify(errorRecovery, null, 2)}\n`);
    fs.writeFileSync(path.join(OUT, 'failure.json'), `${JSON.stringify({ report, accessibility, error: error.stack || error.message }, null, 2)}\n`);
    if (context) await stopEvidenceTrace(context, context.pages(), path.join(TRACES, 'failure.zip')).catch(() => {});
    throw error;
  } finally {
    await context?.close(); await browser.close();
    await acceptanceLease.release();
  }
}

main().catch((error) => { console.error(`[verify.frontend.delivery_hardening.browser] FAIL ${error.stack || error.message}`); process.exitCode = 1; });
