#!/usr/bin/env node
import './lib/probe_toolchain_blocked.mjs';
/**
 * S4 browser evidence probe for the batch-C path namespace acceptance.
 *
 * Opens two tabs in ONE browser context (same origin), logs the same-name admin
 * into /t/demo/ and /platform-admin/, records per-tab storage and token claims,
 * checks cross-namespace replay, then performs a page-level logout in the demo
 * tab and verifies the platform tab is unaffected.
 *
 * Read-only with respect to business data. Logout bumps the demo admin
 * token_version, so run it only inside an agreed evidence window.
 *
 * Credentials are per entry and never checked in.  Each governed entry owns its
 * own variable; a missing variable fails closed before Playwright is loaded.
 *
 *   SC_DEMO_USER_PASSWORD       demo tenant administrator password
 *   SC_PLATFORM_ADMIN_PASSWORD  platform administrator password
 *
 * Usage:
 *   node scripts/verify/path_ns_c_s4_browser_probe.mjs \
 *     --base-url http://127.0.0.1:18099 \
 *     --out-dir .runtime/path-ns-c-20261018/evidence-r2/browser \
 *     [--playwright <repo>/frontend/apps/web/node_modules/playwright] \
 *     [--executable <chrome binary>]
 */
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const repoRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..', '..');
const args = Object.fromEntries(process.argv.slice(2).reduce((acc, cur, i, arr) => {
  if (cur.startsWith('--')) acc.push([cur.slice(2), arr[i + 1]]);
  return acc;
}, []));
const BASE = args['base-url'] || 'http://127.0.0.1:18081';
const OUT = path.resolve(args['out-dir'] || path.join(repoRoot, '.runtime/path-ns-c-20261018/evidence-r2/browser'));
const pwPath = args.playwright || path.join(repoRoot, 'frontend/apps/web/node_modules/playwright');
const executable = args.executable || path.join(process.env.HOME || '', '.cache/ms-playwright/chromium-1217/chrome-linux64/chrome');

const ENTRY_CREDENTIALS = {
  demo: { entry: '/t/demo/', login: 'admin', passwordEnv: 'SC_DEMO_USER_PASSWORD' },
  platform: { entry: '/platform-admin/', login: 'admin', passwordEnv: 'SC_PLATFORM_ADMIN_PASSWORD' },
};

function resolveEntryCredential(role) {
  const spec = ENTRY_CREDENTIALS[role];
  const password = (process.env[spec.passwordEnv] || '').trim();
  if (!password) {
    console.error(
      `[path-ns-c-s4-browser-probe] ${spec.passwordEnv} is required for the ${role} entry; refusing to use a literal credential`,
    );
    process.exit(2);
  }
  return { login: spec.login, password };
}

const credentials = {
  demo: resolveEntryCredential('demo'),
  platform: resolveEntryCredential('platform'),
};
const { chromium } = createRequire(pwPath)(pwPath);

fs.mkdirSync(OUT, { recursive: true });
const result = { base: BASE, started_at: new Date().toISOString(), tabs: {}, checks: [] };

const snapshot = (page) => page.evaluate(() => {
  const ssKeys = [];
  for (let i = 0; i < sessionStorage.length; i += 1) ssKeys.push(sessionStorage.key(i));
  const lsKeys = {};
  for (let i = 0; i < localStorage.length; i += 1) {
    const k = localStorage.key(i);
    lsKeys[k] = String(localStorage.getItem(k) || '').slice(0, 60);
  }
  const tokenKey = ssKeys.find((k) => k.startsWith('sc_auth_token:'));
  let claims = null;
  let token = null;
  let tokenLen = 0;
  if (tokenKey) {
    token = sessionStorage.getItem(tokenKey) || '';
    tokenLen = token.length;
    try {
      const payload = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
      claims = JSON.parse(decodeURIComponent(escape(atob(payload))));
    } catch (e) { claims = null; }
  }
  return {
    url: location.href, title: document.title, ss_keys: ssKeys, ls_keys: lsKeys,
    token_key: tokenKey || null, token_len: tokenLen, token,
    claims: claims && { db: claims.db, namespace_id: claims.namespace_id, aud: claims.aud, user_id: claims.user_id, company_id: claims.company_id, allowed_company_ids: claims.allowed_company_ids },
  };
});

async function login(page, entry, credential) {
  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text().slice(0, 160)); });
  await page.goto(BASE + entry, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForSelector('input[aria-label="账号"]', { timeout: 20000 });
  await page.fill('input[aria-label="账号"]', credential.login);
  await page.fill('input[aria-label="密码"]', credential.password);
  await page.click('button[type="submit"]');
  await page.waitForTimeout(4500);
  return errors;
}

async function crossReplay(page, target) {
  return page.evaluate(async (t) => {
    const key = Object.keys(sessionStorage).find((k) => k.startsWith('sc_auth_token:'));
    const token = key ? sessionStorage.getItem(key) : '';
    const r = await fetch(t, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token, 'X-Anonymous-Intent': '1' },
      body: JSON.stringify({ intent: 'app.nav', params: {} }),
    });
    return { status: r.status };
  }, target);
}

const browser = await chromium.launch({ executablePath: executable, headless: true, args: ['--no-sandbox'] });
try {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const demo = await ctx.newPage();
  const platform = await ctx.newPage();

  const demoErrors = await login(demo, ENTRY_CREDENTIALS.demo.entry, credentials.demo);
  const demoSnap = await snapshot(demo);
  const platformErrors = await login(platform, ENTRY_CREDENTIALS.platform.entry, credentials.platform);
  const platformSnap = await snapshot(platform);

  const clean = ({ token, ...rest }) => rest;
  result.tabs.demo_tab = { ...clean(demoSnap), console_errors: demoErrors.slice(0, 3) };
  result.tabs.platform_tab = { ...clean(platformSnap), console_errors: platformErrors.slice(0, 3) };
  result.shared_cookies = (await ctx.cookies()).map((c) => ({ name: c.name, domain: c.domain, path: c.path, httpOnly: c.httpOnly }));
  result.cross_replay = {
    demo_token_on_platform: await crossReplay(demo, '/platform-admin/api/v1/intent'),
    platform_token_on_demo: await crossReplay(platform, '/t/demo/api/v1/intent'),
  };
  await demo.screenshot({ path: path.join(OUT, 'demo_tab.png') });
  await platform.screenshot({ path: path.join(OUT, 'platform_tab.png') });

  const add = (name, expected, actual, ok) => result.checks.push({ scenario: 'S4', name, expected, actual, status: ok ? 'pass' : 'fail' });
  const c1 = demoSnap.claims || {};
  const c2 = platformSnap.claims || {};
  add('distinct_db', 'sc_demo vs sc_platform_control', [c1.db, c2.db], c1.db === 'sc_demo' && c2.db === 'sc_platform_control');
  add('distinct_namespace', 'differ', [c1.namespace_id, c2.namespace_id], !!c1.namespace_id && c1.namespace_id !== c2.namespace_id);
  add('distinct_audience', 'tenant vs platform-admin', [c1.aud, c2.aud], c1.aud === 'tenant' && c2.aud === 'platform-admin');
  add('per_tab_token_keys', 'namespace-scoped keys', [demoSnap.token_key, platformSnap.token_key],
    !!demoSnap.token_key && !!platformSnap.token_key && demoSnap.token_key !== platformSnap.token_key);
  add('demo_token_on_platform', 401, result.cross_replay.demo_token_on_platform.status, result.cross_replay.demo_token_on_platform.status === 401);
  add('platform_token_on_demo', 401, result.cross_replay.platform_token_on_demo.status, result.cross_replay.platform_token_on_demo.status === 401);

  const candidates = await demo.evaluate(() => [...document.querySelectorAll('button,a,[role="button"]')]
    .map((e) => (e.innerText || '').trim()).filter((t) => /退出|注销|登出|logout/i.test(t)).slice(0, 10));
  result.logout_candidates = candidates;
  if (candidates.length) {
    await demo.getByText(/退出|注销|登出|logout/i).first().click({ timeout: 5000 });
    await demo.waitForTimeout(3000);
    const confirm = await demo.evaluate(() => [...document.querySelectorAll('button')]
      .map((e) => (e.innerText || '').trim()).filter((t) => /确定|确认/.test(t)).slice(0, 10));
    result.confirm_candidates = confirm;
    if (confirm.length) {
      await demo.getByText(/确定|确认/).first().click({ timeout: 3000 });
      await demo.waitForTimeout(2500);
    }
  }
  result.logout = {
    clicked: candidates[0] || null,
    after_url: demo.url(),
    after_ss_keys: await demo.evaluate(() => Object.keys(sessionStorage)),
    after_title: await demo.title(),
    old_demo_token_status: await demo.evaluate(async (token) => {
      const r = await fetch('/t/demo/api/v1/intent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token, 'X-Anonymous-Intent': '1' },
        body: JSON.stringify({ intent: 'app.nav', params: {} }),
      });
      return r.status;
    }, demoSnap.token),
    platform_token_status: await crossReplay(platform, '/platform-admin/api/v1/intent').then((r) => r.status),
  };
  await demo.screenshot({ path: path.join(OUT, 'after_logout_demo.png') });
  add('demo_logout_invalidates_demo_token', 401, result.logout.old_demo_token_status, result.logout.old_demo_token_status === 401);
  add('platform_token_unaffected', 200, result.logout.platform_token_status, result.logout.platform_token_status === 200);
} finally {
  await browser.close();
}
result.finished_at = new Date().toISOString();
result.summary = { total: result.checks.length, passed: result.checks.filter((c) => c.status === 'pass').length };
fs.writeFileSync(path.join(OUT, 's4-browser-run.json'), JSON.stringify(result, null, 2) + '\n');
console.log(JSON.stringify({ summary: result.summary, logout: result.logout, cross_replay: result.cross_replay }, null, 2));
if (result.summary.passed !== result.summary.total) process.exit(1);
