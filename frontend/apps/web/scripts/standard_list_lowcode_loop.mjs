import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { createHash, randomUUID } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { launchChromium } from '../../../../scripts/verify/playwright_runtime.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../..');
const base = 'http://127.0.0.1:5180';
const database = 'sc_frontend_acceptance';
const source = '8adfff9e9d649c309f010bcbeae48e4be1386ba6';
const digest = (value) => createHash('sha256').update(value).digest('hex');

// Recovery reads the authoritative state even when publish timed out. It never
// repeats publish, overwrites somebody else's conflict, or hides cleanup failure.
export async function recoverChangeSet(cs, token, requestId, publishAttempted = false) {
  const current = await cs('get', { change_set_token: token });
  if (current.state === 'published') {
    const result = await cs('rollback', { change_set_token: token, request_id: requestId });
    assert.equal(result.state, 'published', 'rollback must return a published restoration');
    assert.equal(result.publish_result?.published_content_verified, true, 'rollback content must be verified');
    return 'rolled_back';
  }
  if (['draft', 'ready', 'failed'].includes(current.state)) {
    assert.equal(publishAttempted, false, 'publish outcome unresolved; preserve recovery identity, do not discard');
    const result = await cs('discard', { change_set_token: token });
    assert.equal(result.state, 'discarded');
    return 'discarded';
  }
  assert.ok(['superseded', 'discarded'].includes(current.state), `unknown recovery state: ${current.state}`);
  return current.state;
}

export function listLabels(contract) {
  assert.equal(contract?.pageInfo?.model, 'payment.request', 'wrong contract model');
  assert.ok(contract.layoutContract, 'missing normalized layout');
  const rows = [];
  const visit = (value) => {
    if (!value || typeof value !== 'object') return;
    if (typeof value.label === 'string') rows.push([value.fieldCode || value.name || value.widgetId || '', value.label]);
    Object.values(value).forEach(visit);
  };
  visit(contract.layoutContract);
  assert.ok(rows.length > 0, 'empty label projection');
  return rows;
}

async function servedIdentity() {
  // This is a bounded continuation of TPL-06A's existing build, not a new port
  // or acceptance profile. A changed frontend requires its own reviewed build.
  execFileSync('git', ['diff', '--quiet', source, '--', 'frontend', ':!frontend/apps/web/scripts'], { cwd: root });
  assert.equal(execFileSync('git', ['ls-files', '--others', '--exclude-standard', '--', 'frontend/apps/web/src'], { cwd: root, encoding: 'utf8' }).trim(), '');
  const dist = path.resolve(root, '../sce-offrepo/artifacts/tpl06a-20260929/dist');
  const listener = execFileSync('ss', ['-ltnp', 'sport = :5180'], { encoding: 'utf8' });
  const pids = [...listener.matchAll(/pid=(\d+)/g)].map((match) => match[1]);
  assert.equal(pids.length, 1, 'one registered frontend listener required');
  const processRoot = `/proc/${pids[0]}`;
  assert.equal((await fs.stat(processRoot)).uid, process.getuid());
  const environment = Object.fromEntries((await fs.readFile(`${processRoot}/environ`, 'utf8')).split('\0').filter(Boolean).map((item) => [item.slice(0, item.indexOf('=')), item.slice(item.indexOf('=') + 1)]));
  assert.equal(environment.STATIC_ROOT, dist);
  assert.equal(environment.API_PROXY_TARGET, 'http://127.0.0.1:18082');
  assert.equal(environment.STATIC_PORT, '5180');
  assert.ok((await fs.readFile(`${processRoot}/cmdline`, 'utf8')).includes('scripts/release/release_static_server.mjs'));
  const html = await fs.readFile(path.join(dist, 'index.html'), 'utf8');
  const served = await fetch(`${base}/login`).then((res) => { assert.ok(res.ok); return res.text(); });
  assert.equal(served, html, '5180 is not the registered TPL-06A build');
  const entry = html.match(/src="(\/assets\/index-[^"]+\.js)"/)?.[1];
  assert.ok(entry, 'entry asset missing');
  const bytes = await fs.readFile(path.join(dist, entry));
  const remote = Buffer.from(await fetch(`${base}${entry}`).then((res) => { assert.ok(res.ok); return res.arrayBuffer(); }));
  assert.equal(digest(remote), digest(bytes));
  assert.equal(digest(bytes), '57ad457282cb449e6190d757c8b3d5c7f6051cc1f9c3ca89f072d31d5e5984f9', 'reviewed entry digest');
  return { source, entry, entry_sha256: digest(bytes), backend_source: process.env.WEB_LC_BACKEND_REVISION };
}

export async function runStandardListLoop() {
  assert.equal(process.env.DB_NAME, database);
  assert.equal(process.env.COMPOSE_PROJECT_NAME, 'sc-fe-r2-p1-01');
  assert.ok(process.env.WEB_LC_BACKEND_REVISION, 'use the governed Make entry');
  assert.ok(process.env.SC_ACCEPTANCE_FIXTURE_PASSWORD, 'existing fixture password required');
  const run = `web-lc-01-${randomUUID()}`;
  const out = path.join(root, 'artifacts/frontend-web-fix-20260928', run);
  await fs.mkdir(out, { recursive: true, mode: 0o700 });
  const report = { run, status: 'not_run', assertions: [], calls: [], recovery: 'not_needed', candidate: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim(), dirty: execFileSync('git', ['status', '--short'], { cwd: root, encoding: 'utf8' }).trim() };
  const save = () => fs.writeFile(path.join(out, 'report.json'), JSON.stringify(report, null, 2), { mode: 0o600 });
  const check = (name, condition) => { report.assertions.push({ name, passed: Boolean(condition) }); assert.ok(condition, name); };
  let browser, page, token, baseline, publishAttempted = false;
  const bootstrap = new Set();
  const errors = [];
  async function intent(name, params) {
    const result = await page.evaluate(async ({ name, params, database }) => {
      const token = Object.entries(sessionStorage).find(([key]) => key.startsWith('sc_auth_token:'))?.[1];
      const res = await fetch('/api/v1/intent', { method: 'POST', headers: { Authorization: `Bearer ${token || ''}`, 'Content-Type': 'application/json', 'X-Odoo-DB': database }, body: JSON.stringify({ intent: name, params }) });
      return { status: res.status, body: await res.json() };
    }, { name, params, database });
    report.calls.push({ intent: name, status: result.status, ok: result.body?.ok, trace_id: result.body?.trace_id });
    assert.ok(result.status < 400 && result.body?.ok === true, `${name}: ${result.status} ${JSON.stringify(result.body?.error || {})}`);
    return result.body.data;
  }
  const cs = (op, params = {}) => intent(`ui.business_config.change_set.${op}`, { role_key: 'business_config_admin', ...params });
  const contract = () => intent('ui.contract.v2', { op: 'action_open', action_id: 775, menu_id: 545, view_type: 'tree', client_type: 'web_pc', delivery_profile: 'full' });
  async function observe(label) {
    const responsePromise = page.waitForResponse((response) => {
      try {
        const body = response.request().postDataJSON();
        return body?.intent === 'api.data' && body.params?.op === 'list' && body.params?.model === 'payment.request';
      } catch { return false; }
    });
    await page.goto(`${base}/m/545`, { waitUntil: 'domcontentloaded' });
    const response = await responsePromise;
    const request = response.request().postDataJSON().params;
    const body = await response.json();
    assert.ok(response.ok() && body.ok && body.data?.records?.length > 0, 'real nonempty payment list response');
    await page.locator('[data-list-composition="official-standard-list"]').waitFor();
    await page.getByRole('columnheader').filter({ hasText: label }).first().waitFor();
    const headers = await page.getByRole('columnheader').allTextContents();
    check('single official list surface', await page.locator('[data-list-card-container="official"]').count() === 1);
    return { headers: headers.map((value) => value.replace(/\s+/g, ' ').trim()), request: { domain: request.domain, context: request.context, order: request.order, limit: request.limit, offset: request.offset }, records_sha256: digest(JSON.stringify(body.data.records)) };
  }
  try {
    report.identity = await servedIdentity();
    browser = await launchChromium({ headless: true });
    page = await browser.newPage({ viewport: { width: 1440, height: 950 }, locale: 'zh-CN' });
    await page.route('**/api/v1/intent', async (route) => {
      const body = route.request().postDataJSON();
      if (body?.intent === 'api.data' && !['list', 'read'].includes(body.params?.op)) {
        errors.push(`forbidden business operation: ${body.params?.op}`);
        await route.abort();
      } else await route.continue();
    });
    page.on('pageerror', (error) => errors.push(error.message));
    page.on('request', (request) => {
      if (request.url().includes('/api/v1/intent')) {
        try { bootstrap.add(request.postDataJSON()?.intent); } catch { /* non-JSON observation */ }
      }
    });
    await page.goto(`${base}/login`);
    const inputs = page.locator('input');
    await inputs.nth(0).fill('fixture_role_config_admin');
    await inputs.nth(1).fill(process.env.SC_ACCEPTANCE_FIXTURE_PASSWORD);
    if (await inputs.count() > 2 && await inputs.nth(2).isEnabled()) await inputs.nth(2).fill(database);
    await page.getByRole('button', { name: /^登录$/ }).click();
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 60000 });
    await page.locator('.layout-shell').waitFor();
    baseline = listLabels(await contract());
    const field = baseline.find(([key]) => key === 'name');
    assert.ok(field, 'name column must exist in effective contract');
    const beforeHeaders = await observe(field[1]);
    check('bootstrap includes system.init and contract', bootstrap.has('system.init') && [...bootstrap].some((name) => /^ui\.contract/.test(name)));
    report.baseline = { labels: baseline, surface: beforeHeaders };
    check('readonly has no browser exceptions', errors.length === 0);
    report.status = 'readonly_passed';
    if (process.env.WEB_LC_APPLY !== '1') return;
    const opened = await cs('open', { name: run });
    token = opened.token;
    report.change_set_token = token;
    await save(); // Recovery identity is durable before any publish request.
    const label = `配置闭环-${run.slice(-8)}`;
    await cs('stage', { change_set_token: token, config_type: 'list', target_key: run, model: 'payment.request', action_id: 775, view_type: 'tree', draft_payload: { view_orchestration: { source: 'smart_core.lowcode.business_config', views: { tree: { columns: [{ name: 'name', label, visible: true }] } } } } });
    check('validated ready', (await cs('validate', { change_set_token: token })).state === 'ready');
    report.publish_request_id = `${run}-publish`;
    report.publish_attempted = publishAttempted = true;
    await save();
    const published = await cs('publish', { change_set_token: token, request_id: report.publish_request_id });
    check('published content verified', published.state === 'published' && published.publish_result?.published_content_verified === true);
    check('effective contract consumes label', listLabels(await contract()).some(([key, value]) => key === 'name' && value === label));
    report.changed_headers = await observe(label);
    assert.equal(report.changed_headers.records_sha256, beforeHeaders.records_sha256, 'configuration must preserve returned business records');
    assert.deepEqual(report.changed_headers.request, beforeHeaders.request, 'configuration must preserve query and authorization context');
    await page.screenshot({ path: path.join(out, 'published.png') });
    report.recovery = await recoverChangeSet(cs, token, `${run}-rollback`, publishAttempted);
    token = null;
    assert.deepEqual(listLabels(await contract()), baseline, 'restored effective labels');
    assert.deepEqual(await observe(field[1]), beforeHeaders, 'restored visible headers, query and records');
    check('restoration verified in contract and page', true);
    check('no browser exceptions', errors.length === 0);
    report.status = 'passed';
  } catch (error) {
    report.status = 'failed';
    report.error = error.message;
    throw error;
  } finally {
    try {
      if (token) {
        report.recovery = await recoverChangeSet(cs, token, `${run}-rollback`, publishAttempted);
        if (baseline) assert.deepEqual(listLabels(await contract()), baseline, 'emergency restoration');
      }
    } catch (error) {
      report.recovery = 'failed';
      report.recovery_error = error.message;
      process.exitCode = 1;
    }
    report.browser_errors = errors;
    await save();
    await browser?.close();
    console.log(`[standard_list_lowcode_loop] ${report.status} recovery=${report.recovery} assertions=${report.assertions.length} report=${path.join(out, 'report.json')}`);
    if (report.recovery === 'failed') throw new Error('configuration recovery failed; see private report');
  }
}
