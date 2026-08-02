#!/usr/bin/env node

import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { launchChromium } from './playwright_runtime.mjs';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const baseUrl = process.env.BASE_URL || process.env.FRONTEND_URL || 'http://127.0.0.1:5175';
const dbName = process.env.DB_NAME || 'sc_demo';
const loginName = process.env.E2E_LOGIN || 'wutao';
const password = process.env.E2E_PASSWORD || '';
const secondLogin = process.env.E2E_SECOND_LOGIN || 'fixture_role_pm';
const secondPassword = process.env.E2E_SECOND_PASSWORD || password;
const expectedActionId = Number(process.env.EXPECTED_ACTION_ID || 723);
const outputDir = path.resolve(repoRoot, process.env.ARTIFACTS_DIR || 'artifacts/frontend-navigation-initialization-race');

function check(value, message) {
  if (!value) throw new Error(message);
}

function requestIntent(request) {
  if (!request.url().includes('/api/v1/intent')) return { intent: '', params: {} };
  try {
    const body = JSON.parse(request.postData() || '{}');
    return { intent: String(body.intent || ''), params: body.params || {} };
  } catch {
    return { intent: '', params: {} };
  }
}

function createInitController(page, counters) {
  let delayNext = false;
  let failNext = false;
  let releaseDelay = null;
  let releaseRequested = false;
  let notifyStarted = null;
  let startedPromise = Promise.resolve();
  let initPending = false;

  const arm = ({ fail = false } = {}) => {
    delayNext = !fail;
    failNext = fail;
    releaseRequested = false;
    startedPromise = new Promise((resolve) => { notifyStarted = resolve; });
    return {
      started: startedPromise,
      release: () => {
        releaseRequested = true;
        if (releaseDelay) releaseDelay();
      },
    };
  };

  page.route('**/api/v1/intent?**', async (route) => {
    const { intent, params } = requestIntent(route.request());
    if (initPending && intent && !['system.init', 'auth.login'].includes(intent)) {
      counters.PRE_INIT_BUSINESS_REQUEST_COUNT += 1;
      counters.pre_init_intents.push(intent);
    }
    if (intent !== 'system.init') {
      await route.continue();
      return;
    }
    initPending = true;
    notifyStarted?.();
    notifyStarted = null;
    if (failNext) {
      failNext = false;
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ ok: false, error: { code: 'INJECTED_INIT_FAILURE', message: 'injected init failure' } }),
      });
      initPending = false;
      return;
    }
    if (delayNext) {
      delayNext = false;
      await new Promise((resolve) => {
        if (releaseRequested) resolve();
        else releaseDelay = resolve;
      });
      releaseDelay = null;
    }
    const response = await route.fetch();
    await route.fulfill({ response });
    initPending = false;
    counters.init_responses.push({ status: response.status(), company_id: params.company_id || null });
  });

  return { arm };
}

async function fillLogin(page, login, loginPassword) {
  await page.locator('input').nth(0).fill(login);
  await page.locator('input[type="password"]').fill(loginPassword);
  if (await page.locator('input').count() >= 3) {
    await page.locator('input').nth(2).fill(dbName).catch(() => {});
  }
  await page.getByRole('button', { name: /^登录$/ }).click();
}

async function waitNavigationReady(page) {
  await page.locator('.nav-shell[data-navigation-state="ready"]').waitFor({ timeout: 90000 });
  await page.locator('.primary-navigation').waitFor({ timeout: 30000 });
}

async function assertNavigationClosed(page, counters, label) {
  const targetCount = await page.locator('.nav-shell').getByText(/^(公司内部人员维护|用户账号与权限)$/).count();
  if (targetCount) counters.STALE_SESSION_NAVIGATION_COUNT += targetCount;
  const readyCount = await page.locator('.nav-shell[data-navigation-state="ready"]').count();
  if (readyCount) counters.STALE_SESSION_NAVIGATION_COUNT += readyCount;
  const shell = page.locator('.nav-shell').first();
  if (await shell.count()) {
    for (let index = 0; index < 8; index += 1) {
      await shell.click({ position: { x: 80 + index, y: 90 + index }, force: true }).catch(() => {});
    }
  }
  await page.screenshot({ path: path.join(outputDir, `${label}.png`), fullPage: true });
}

async function openPersonnelMenu(page) {
  const search = page.locator('.primary-navigation input[type="search"]');
  await search.fill('用户账号与权限');
  let target = page.locator('.nav-shell button.label').filter({ hasText: '用户账号与权限' }).first();
  if (!(await target.isVisible().catch(() => false))) {
    await search.fill('公司内部人员维护');
    target = page.locator('.nav-shell button.label').filter({ hasText: '公司内部人员维护' }).first();
  }
  await target.waitFor({ timeout: 30000 });
  const beforeUrl = page.url();
  await target.click();
  await page.waitForURL((url) => (
    url.toString() !== beforeUrl
    && (/\/(?:a|m)\//.test(url.pathname) || url.searchParams.has('action_id'))
  ), { timeout: 30000 });
  await page.waitForTimeout(300);
  return new URL(page.url());
}

async function main() {
  check(password, 'E2E_PASSWORD is required');
  await fs.mkdir(outputDir, { recursive: true });
  const counters = {
    WRONG_ACTION_OPEN_COUNT: 0,
    CROSS_SCENE_COMPOSITION_COUNT: 0,
    STALE_SESSION_NAVIGATION_COUNT: 0,
    PRE_INIT_BUSINESS_REQUEST_COUNT: 0,
    NAVIGATION_AUTHORITY_DENIED_COUNT: 0,
    pre_init_intents: [],
    init_responses: [],
  };
  const browser = await launchChromium({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, locale: 'zh-CN' });
  await page.addInitScript(() => localStorage.setItem('DEBUG_INTENT', '1'));
  const controller = createInitController(page, counters);
  page.on('console', (message) => {
    if (/NAVIGATION_AUTHORITY_DENIED/.test(message.text())) counters.NAVIGATION_AUTHORITY_DENIED_COUNT += 1;
  });
  page.on('response', async (response) => {
    if (!response.url().includes('/api/v1/intent') || response.status() < 400) return;
    let body = '';
    try { body = await response.text(); } catch {}
    if (/NAVIGATION_AUTHORITY_DENIED/.test(body)) counters.NAVIGATION_AUTHORITY_DENIED_COUNT += 1;
  });

  try {
    // Login with a delayed system.init: no old menu may be rendered or clicked.
    const loginDelay = controller.arm();
    console.log('[navigation-race-browser] login init delay');
    await page.goto(`${baseUrl}/login?db=${encodeURIComponent(dbName)}`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await fillLogin(page, loginName, password);
    await loginDelay.started;
    await assertNavigationClosed(page, counters, '01-login-init-pending');
    loginDelay.release();
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 90000 });
    await waitNavigationReady(page);

    // Re-initialization keeps the shell visible but atomically removes the old navigation.
    const refreshDelay = controller.arm();
    console.log('[navigation-race-browser] refresh init delay');
    await page.getByRole('button', { name: '刷新', exact: true }).click();
    await refreshDelay.started;
    await page.locator('.nav-shell[data-navigation-state="loading"]').waitFor({ timeout: 30000 });
    await assertNavigationClosed(page, counters, '02-refresh-init-pending');
    refreshDelay.release();
    await waitNavigationReady(page);

    // The first boundary click after readiness must retain one menu/action/scene tuple.
    const targetUrl = await openPersonnelMenu(page);
    console.log(`[navigation-race-browser] selected ${targetUrl.pathname}${targetUrl.search}`);
    const actualActionId = Number(targetUrl.pathname.match(/\/a\/(\d+)/)?.[1] || targetUrl.searchParams.get('action_id') || 0);
    const sceneKey = targetUrl.searchParams.get('scene_key') || targetUrl.pathname.match(/\/s\/([^/?]+)/)?.[1] || '';
    if (actualActionId !== expectedActionId) counters.WRONG_ACTION_OPEN_COUNT += 1;
    if (sceneKey && sceneKey !== 'users.list') counters.CROSS_SCENE_COMPOSITION_COUNT += 1;
    await page.screenshot({ path: path.join(outputDir, '03-correct-action-after-ready.png'), fullPage: true });

    // A refresh on an existing business URL must not restore menu/action caches before init.
    const reloadDelay = controller.arm();
    console.log('[navigation-race-browser] reload init delay');
    await page.reload({ waitUntil: 'domcontentloaded', timeout: 60000 });
    await reloadDelay.started;
    await assertNavigationClosed(page, counters, '04-reload-init-pending');
    reloadDelay.release();
    await waitNavigationReady(page);

    // A failed init remains fail-closed; retry installs a new whole snapshot.
    const failedInit = controller.arm({ fail: true });
    console.log('[navigation-race-browser] injected init failure');
    await page.getByRole('button', { name: '刷新', exact: true }).click();
    await failedInit.started;
    await page.locator('.nav-shell[data-navigation-state="error"]').waitFor({ timeout: 30000 });
    await assertNavigationClosed(page, counters, '05-init-failed');
    const retryDelay = controller.arm();
    console.log('[navigation-race-browser] retry init delay');
    await page.getByRole('button', { name: /重试/ }).click();
    await retryDelay.started;
    await assertNavigationClosed(page, counters, '06-init-retry-pending');
    retryDelay.release();
    await waitNavigationReady(page);

    // Logout and switch roles: the next user may not inherit wutao's selected action or menu.
    await page.getByRole('button', { name: '退出登录' }).click();
    await page.waitForURL((url) => url.pathname.includes('/login'), { timeout: 30000 });
    const switchDelay = controller.arm();
    console.log(`[navigation-race-browser] role switch ${secondLogin}`);
    await fillLogin(page, secondLogin, secondPassword);
    await switchDelay.started;
    await assertNavigationClosed(page, counters, '07-role-switch-init-pending');
    switchDelay.release();
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 90000 });
    await waitNavigationReady(page);
    const stalePersonnelTarget = await page.locator('.nav-shell button.label').filter({ hasText: /用户账号与权限|公司内部人员维护/ }).count();
    if (stalePersonnelTarget) counters.STALE_SESSION_NAVIGATION_COUNT += stalePersonnelTarget;

    const result = {
      RESULT: Object.entries(counters).every(([key, value]) => !key.endsWith('_COUNT') || value === 0) ? 'PASS' : 'FAIL',
      ...counters,
      CORRECT_ACTION_AFTER_READY: actualActionId === expectedActionId ? 'PASS' : 'FAIL',
      expected_action_id: expectedActionId,
      actual_action_id: actualActionId,
      final_login: secondLogin,
      final_url: page.url(),
    };
    await fs.writeFile(path.join(outputDir, 'report.json'), `${JSON.stringify(result, null, 2)}\n`, 'utf8');
    console.log(JSON.stringify(result, null, 2));
    check(result.RESULT === 'PASS' && result.CORRECT_ACTION_AFTER_READY === 'PASS', 'navigation initialization race browser acceptance failed');
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
