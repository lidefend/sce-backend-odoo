import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';
import { launchChromium } from './playwright_runtime.mjs';
import { measureRuntimeSample, startupTiming } from './frontend_runtime_performance_sample.mjs';

const digest = value => crypto.createHash('sha256').update(value).digest('hex');
export function validateBackend(row, root) {
  assert.equal(row.Config.Labels['com.docker.compose.project'], 'sc-local-dev');
  assert.equal(row.State.Running, true);
  const env = Object.fromEntries(row.Config.Env.map(item => [item.slice(0, item.indexOf('=')), item.slice(item.indexOf('=') + 1)]));
  assert.equal(env.DB_NAME, 'sc_dev_demo');
  assert.equal(env.ODOO_DBFILTER, '^sc_dev_demo$');
  assert.equal(row.Mounts.find(item => item.Destination === '/mnt/source-addons')?.Source, path.join(root, 'addons'));
  assert.equal(row.Mounts.find(item => item.Destination === '/var/lib/odoo')?.Name, 'sc_local_dev_odoo_data');
  return { container_id: row.Id, started_at: row.State.StartedAt, source_root: root,
    database: env.DB_NAME, dbfilter: env.ODOO_DBFILTER, revision: env.SC_SOURCE_REVISION || null };
}

export function requestShape(payload) {
  const safe = value => typeof value === 'string' && /^[a-zA-Z0-9_.:-]{1,100}$/.test(value) ? value : null;
  const params = payload?.params || {};
  return {intent: safe(payload?.intent), model: safe(params.model), op: safe(params.op),
    preference_key: safe(params.preference_key), projection: safe(params.projection), view_type: safe(params.view_type),
    action_id: Number.isSafeInteger(params.action_id) ? params.action_id : null,
    fields: Array.isArray(params.fields) ? params.fields.map(safe).filter(Boolean).slice(0,500) : null};
}

export function projectionTiming(value) {
  if (!value || typeof value !== 'object') return null;
  const safe = text => typeof text === 'string' && /^[a-zA-Z0-9_.:-]{1,100}$/.test(text) ? text : null;
  return {status: safe(value.status), reason: safe(value.reason),
    stages_ms: Object.fromEntries(Object.entries(value.stages_ms || {}).filter(([key, number]) =>
      safe(key) && typeof number === 'number' && Number.isFinite(number) && number >= 0))};
}

async function observeChain(page, action) {
  const started = performance.now();
  const rows = [];
  const pending = [];
  const capture = request => {
    if (!request.url().includes('/api/v1/intent')) return;
    if (rows.length >= 120) return;
    let payload;
    try { payload = request.postDataJSON(); } catch { return; }
    const row = {...requestShape(payload), started_ms: Math.round(performance.now() - started)};
    rows.push(row);
    pending.push(async () => {
      try {
        const response = await request.response();
        if (!response) { row.diagnostic = 'no_response'; return; }
        await response.finished();
        row.status = response.status();
        row.server_timing = (await response.headerValue("server-timing")) || null;
        row.http_timing = request.timing();
        row.duration_ms = request.timing().responseEnd;
        const body = await response.body();
        row.bytes = body.length;
        const envelope = JSON.parse(body.toString());
        row.ok = envelope.ok === true;
        row.preference_projection = envelope.data?.projection === "stored" ? "stored" : null;
        row.startup_profile = startupTiming(envelope.meta?.startup_profile);
        row.projection_cache = projectionTiming(envelope.meta?.projection_cache);
        row.language = typeof envelope.data?.user?.lang === 'string' ? envelope.data.user.lang : null;
        row.company_id = typeof envelope.data?.record_context?.company_id === 'number' ? envelope.data.record_context.company_id : null;
        row.server_elapsed_ms = typeof envelope.meta?.elapsed_ms === 'number' ? envelope.meta.elapsed_ms : null;
        row.data_fields = Object.keys(envelope.data?.dataContract?.mainData || {}).filter(key => /^[a-zA-Z0-9_.:-]{1,100}$/.test(key)).sort().slice(0,500);
        row.diagnostic = 'captured';
      } catch { row.diagnostic = 'unavailable'; }
    });
  };
  page.on('request', capture);
  let error;
  try { await action(); } catch (failure) { error = failure; }
  const total = Math.round(performance.now() - started);
  page.off('request', capture);
  await Promise.all(pending.map(read => read()));
  return {status: error ? 'failed' : 'observed', total_automation_ms: total, requests: rows,
    failure: error ? 'page_operation_did_not_complete' : null};
}

// Bounded relation search-dialog observation: the search dialog is the only
// consumer of relation_entry.search_dialog. It is opened through the declared
// many2one panel action (搜索更多), never through a self-invented selector.
async function observeRelationDialog(page) {
  const boxes = page.locator('.many2one-combobox');
  const total = Math.min(await boxes.count(), 8);
  const attempts = [];
  for (let index = 0; index < total; index += 1) {
    const input = boxes.nth(index).locator('input').first();
    if (!(await input.isVisible().catch(() => false))) { attempts.push({index, reason: 'not_visible'}); continue; }
    if (await input.isDisabled().catch(() => false)) { attempts.push({index, reason: 'disabled'}); continue; }
    if (await input.getAttribute('readonly') !== null) { attempts.push({index, reason: 'readonly'}); continue; }
    try {
      await input.click();
      const panel = page.locator('.many2one-option-panel:visible');
      await panel.waitFor({state: 'visible', timeout: 8000});
      const more = panel.getByRole('button', {name: /搜索更多/});
      if (!(await more.count())) {
        attempts.push({index, reason: 'no_declared_search_more_entry'});
        await page.keyboard.press('Escape');
        continue;
      }
      const observed = await observeChain(page, async () => {
        await more.first().click();
        await page.locator('.relation-dialog').waitFor({state: 'visible', timeout: 15000});
        await page.locator('.relation-dialog tbody tr').first().waitFor({timeout: 15000});
      });
      const snapshot = await page.evaluate(() => {
        const clean = value => String(value || '').replace(/\s+/g, ' ').trim().slice(0, 160);
        const dialog = document.querySelector('.relation-dialog');
        return {
          visible: Boolean(dialog),
          title: clean(dialog?.querySelector('h3')?.textContent),
          header_count: dialog ? dialog.querySelectorAll('th').length : 0,
          headers: Array.from(dialog?.querySelectorAll('th') || []).map(node => clean(node.textContent)).filter(Boolean).slice(0, 12),
          row_count: dialog ? dialog.querySelectorAll('tbody tr').length : 0,
          contract_gap_error: clean(dialog?.querySelector('[role="alert"]')?.textContent),
        };
      });
      await page.locator('.relation-dialog-footer button').filter({hasText: '取消'}).first().click();
      await page.locator('.relation-dialog').waitFor({state: 'detached', timeout: 10000});
      return {status: 'observed', field_index: index, attempts, request_chain: observed, snapshot};
    } catch (failure) {
      attempts.push({index, reason: String(failure?.message || failure).replace(/\s+/g, ' ').slice(0, 200)});
      await page.keyboard.press('Escape').catch(() => {});
    }
  }
  return {status: 'not_run', reason: 'no_in_view_relation_field_exposed_a_search_dialog', attempts};
}

async function main() {
  const root = process.cwd();
  const base = 'http://127.0.0.1:18081';
  const password = process.env.SC_DEMO_USER_PASSWORD;
  assert.ok(password, 'governed demo password missing');
  assert.equal(process.env.DB_NAME, 'sc_dev_demo');
  assert.equal(process.env.COMPOSE_PROJECT_NAME, 'sc-local-dev');
  const operation = process.env.PRODUCT_PERFORMANCE_BROWSER_SCOPE || 'login';
  assert.ok(['login', 'company', 'identity', 'chain', 'record', 'relation-dialog'].includes(operation), 'unknown browser observation scope');
  const output = path.join(root, `artifacts/main-scheduled-ci-closeout-20261016/local-browser-${operation}-performance.json`);
  const inspect = JSON.parse(execFileSync('docker', ['inspect', 'sc-local-dev-odoo-1'], { encoding: 'utf8' }))[0];
  const backend = validateBackend(inspect, root);
  const hashes = {};
  for (const relative of ['handlers/system_init.py', 'delivery/menu_service.py', 'governance/scene_normalizer.py', 'app_config_engine/models/app_nav_config.py', 'handlers/ui_contract_v2.py', 'utils/load_contract_response_cache.py', 'handlers/ui_contract.py', 'handlers/user_view_preference.py', 'controllers/intent_dispatcher.py', 'core/intent_router.py', 'app_config_engine/services/dispatchers/action_dispatcher.py', 'app_config_engine/services/assemblers/page_assembler.py']) {
    const source = path.join(root, 'addons/smart_core', relative);
    assert.ok(fs.statSync(source).mtimeMs <= Date.parse(backend.started_at), `backend source changed after service start: ${relative}`);
    const expected = digest(fs.readFileSync(source));
    const actual = execFileSync('docker', ['exec', inspect.Id, 'sha256sum', `/mnt/source-addons/smart_core/${relative}`], { encoding: 'utf8' }).split(/\s/)[0];
    assert.equal(actual, expected, `served backend mismatch: ${relative}`);
    hashes[relative] = actual;
  }
  const dist = path.resolve(process.env.FRONTEND_DIST_DIR || 'frontend/apps/web/dist-dev');
  const index = fs.readFileSync(path.join(dist, 'index.html'));
  const servedIndex = Buffer.from(await (await fetch(`${base}/login`)).arrayBuffer());
  assert.equal(digest(servedIndex), digest(index), 'served frontend index mismatch');
  const assets = {};
  for (const match of index.toString().matchAll(/(?:src|href)="(\/assets\/[^"]+\.(?:js|css))"/g)) {
    const asset = match[1];
    assert.ok(!asset.includes('..'), 'unsafe asset path');
    const localHash = digest(fs.readFileSync(path.join(dist, asset)));
    const remoteHash = digest(Buffer.from(await (await fetch(`${base}${asset}`)).arrayBuffer()));
    assert.equal(remoteHash, localHash, `served entry asset mismatch: ${asset}`);
    assets[asset] = localHash;
  }
  assert.ok(Object.keys(assets).length > 0, 'no entry assets found');
  const report = { schema: 'local-runtime-browser-observation/v1', status: 'running', acceptance_pass: false,
    scope: 'local_demo_development_build', observed_at: new Date().toISOString(), backend, backend_hashes: hashes,
    entry_assets: assets, asset_scope: 'index-referenced JS/CSS only; lazy chunks not fully inventoried',
    runtime_refresh_evidence: ['chain', 'record', 'relation-dialog'].includes(operation) ? '/tmp/sce-chain-runtime-restart.log' : '/tmp/sce-runtime-browser-up.log',
    frontend_index_sha256: digest(index), head: execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim(),
    dirty: Boolean(execFileSync('git', ['status', '--porcelain'], { encoding: 'utf8' }).trim()),
    operation, probe_sha256: digest(fs.readFileSync(new URL(import.meta.url))),
    login_samples: [], company_switch: { status: 'not_run' }, warmups: operation === 'login' ? 2 : 0,
    limitation: 'not_release_or_capacity_acceptance; company switch needs an actually assigned alternative company' };
  if (operation === 'identity') {
    report.status = 'observed';
    fs.mkdirSync(path.dirname(output), { recursive: true });
    fs.writeFileSync(output, JSON.stringify(report, null, 2) + '\n');
    console.log(JSON.stringify({status: report.status, operation, output}));
    return;
  }
  let browser;
  let context;
  let page;
  const intentResponse = name => page.waitForResponse(response => {
    try { return response.url().includes('/api/v1/intent') && response.request().postDataJSON()?.intent === name; }
    catch { return false; }
  });
  async function login() {
    await page.goto(`${base}/login`, { waitUntil: 'domcontentloaded' });
    await page.locator('#login-username, input[autocomplete="username"]').first().fill('demo_role_finance');
    await page.locator('#login-password, input[autocomplete="current-password"]').first().fill(password);
    const loginReply = intentResponse('login');
    const initReply = intentResponse('system.init');
    const replies = Promise.all([loginReply, initReply]);
    // Attach immediately: a failed click must not leave pending rejections unhandled.
    replies.catch(() => {});
    await page.getByRole('button', { name: /^登录$/ }).click();
    for (const response of await replies) {
      const body = await response.json();
      assert.ok(response.ok() && body.ok === true, 'login/startup rejected');
    }
    await page.waitForURL(url => !url.pathname.includes('/login'));
    await page.locator('[data-role-home][data-state="ready"]').waitFor({ state: 'visible' });
  }
  async function logout() {
    await page.getByRole('button', { name: '退出登录' }).click();
    await page.waitForURL(url => url.pathname.includes('/login'));
  }
  try {
    browser = await launchChromium({ headless: true });
    report.browser_version = browser.version();
    context = await browser.newContext({ viewport: { width: 1440, height: 960 } });
    page = await context.newPage();
    page.setDefaultTimeout(30000);
    if (operation === 'login') {
      for (let i = 0; i < 2; i++) { await login(); await logout(); }
      for (let i = 0; i < 5; i++) {
        report.login_samples.push(await measureRuntimeSample(page, login,
          { index: i + 1, role: 'finance', cache_state: 'after_two_warmups', ready: 'WorkspaceHome.ready' }));
        if (i < 4) await logout();
      }
    } else if (operation === 'record') {
      // Login/navigation are setup only; reuse the separate list observations.
      await login();
      await page.getByRole('searchbox', {name: '搜索菜单', exact: true}).fill('付款申请');
      await page.locator('[data-navigation-node="canonical"][data-navigation-label="付款申请"]:visible').click();
      await page.locator('[data-semantic-component="ListPage"][data-list-status="ok"]:visible').waitFor();
      report.chain = {};
      const row = page.locator('[data-semantic-component="ListPage"] [data-record-key]:visible').first();
      assert.equal(await row.count(), 1, 'no declared record row');
      report.chain.record = await observeChain(page, async () => {
        await row.click();
        await page.locator('[data-product-page-mode="form"][data-form-model="payment.request"][data-state="ok"]:visible').waitFor();
      });
      assert.equal(report.chain.record.status, 'observed', 'record operation failed');
      const edit = page.getByRole('button', {name: '编辑', exact: true});
      report.chain.edit = await edit.count() === 1 && await edit.isEnabled() ? await observeChain(page, async () => {
        await edit.click();
        await page.getByRole('button', {name: '保存修改', exact: true}).waitFor();
      }) : {status: 'not_run', reason: 'no_enabled_unique_edit_action'};
      if (report.chain.edit.status !== 'not_run') assert.equal(report.chain.edit.status, 'observed', 'edit operation failed');
    } else if (operation === 'relation-dialog') {
      report.chain = {};
      report.chain.login = await observeChain(page, login);
      assert.equal(report.chain.login.status, 'observed', 'login failed');
      const readyDialogList = () => page.locator('[data-semantic-component="ListPage"][data-list-status="ok"]:visible').waitFor();
      const captureContract = () => page.waitForResponse(async response => {
        try {
          if (!response.url().includes('/api/v1/intent')) return false;
          return response.request().postDataJSON()?.intent === 'ui.contract.v2';
        } catch { return false; }
      }).then(async response => {
        const body = await response.body();
        return {request: requestShape(response.request().postDataJSON()), status: response.status(), sha256: digest(body), body};
      }).catch(() => null);
      const storeEnvelope = (name, captured) => {
        if (!captured) return {status: 'not_run', reason: 'no_ui_contract_v2_response_captured'};
        const relative = `artifacts/main-scheduled-ci-closeout-20261016/local-browser-relation-${name}-envelope.json`;
        fs.writeFileSync(path.join(root, relative), JSON.stringify(
          {request: captured.request, status: captured.status, sha256: captured.sha256, envelope: JSON.parse(captured.body.toString())}) + '\n');
        return {path: relative, sha256: captured.sha256, status: captured.status, request: captured.request};
      };
      report.contract_envelopes = {};
      const listReply = captureContract();
      await page.getByRole('searchbox', {name: '搜索菜单', exact: true}).fill('付款申请');
      await page.locator('[data-navigation-node="canonical"][data-navigation-label="付款申请"]:visible').click();
      await readyDialogList();
      report.contract_envelopes.list = storeEnvelope('list', await listReply);
      const row = page.locator('[data-semantic-component="ListPage"] [data-record-key]:visible').first();
      assert.equal(await row.count(), 1, 'no declared payment.request record row');
      const recordReply = captureContract();
      report.chain.record = await observeChain(page, async () => {
        await row.click();
        await page.locator('[data-product-page-mode="form"][data-form-model="payment.request"][data-state="ok"]:visible').waitFor();
      });
      assert.equal(report.chain.record.status, 'observed', 'record operation failed');
      report.contract_envelopes.record = storeEnvelope('dialog', await recordReply);
      report.relation_dialog = await observeRelationDialog(page);
      report.relation_dialog_limitation = 'one page, one record form and the first in-view many2one field that exposes the declared 搜索更多 panel action; not a per-field matrix';
    } else if (operation === 'chain') {
      report.chain = {};
      report.chain.login = await observeChain(page, login);
      assert.equal(report.chain.login.status, 'observed', 'chain login failed');
      const readyList = () => page.locator('[data-semantic-component="ListPage"][data-list-status="ok"]:visible').waitFor();
      await page.getByRole('searchbox', {name: '搜索菜单', exact: true}).fill('付款申请');
      report.chain.list = await observeChain(page, async () => {
        const link = page.locator('[data-navigation-node="canonical"][data-navigation-label="付款申请"]:visible');
        assert.equal(await link.count(), 1, 'payment menu link must be unique');
        await link.click();
        await readyList();
      });
      assert.equal(report.chain.list.status, 'observed', 'list operation failed');
      report.chain.query = await observeChain(page, async () => {
        const input = page.locator('[data-list-query-action-bar] input[type="search"]:visible');
        await input.fill('DEMO');
        const reply = intentResponse('api.data');
        reply.catch(() => {});
        await page.locator('[data-list-query-action-bar]').getByRole('button', {name: '搜索', exact: true}).click();
        await reply;
        await readyList();
      });
      assert.equal(report.chain.query.status, 'observed', 'query operation failed');
      const record = page.locator('a[href*="/r/payment.request/"]:visible').first();
      if (await record.count()) {
        report.chain.record = await observeChain(page, async () => {
          await record.click();
          await page.locator('[data-product-page-mode="form"][data-form-model="payment.request"][data-state="ok"]:visible').waitFor();
        });
        assert.equal(report.chain.record.status, 'observed', 'record operation failed');
        const edit = page.getByRole('button', {name: '编辑', exact: true});
        report.chain.edit = await edit.count() === 1 ? await observeChain(page, async () => {
          await edit.click();
          await page.getByRole('button', {name: '保存修改', exact: true}).waitFor();
        }) : {status: 'not_run', reason: 'no_unique_declared_edit_action'};
        if (report.chain.edit.status !== 'not_run') assert.equal(report.chain.edit.status, 'observed', 'edit operation failed');
      } else report.chain.record = {status: 'not_run', reason: 'no_visible_record_link'};
    } else {
      await login();
      const indicator = page.locator('[data-semantic-component="WorkspaceContextIndicator"]:visible');
      assert.equal(await indicator.count(), 1, 'context indicator must be unique');
      await indicator.getByRole('button', { name: /^切换公司：/ }).click();
      const panel = page.locator('.workspace-scope-panel').filter({has: page.getByRole('heading', { name: '公司空间', exact: true })});
      await panel.waitFor({state: 'visible'});
      const choices = panel.locator('.workspace-scope-options > button');
      report.company_switch.option_count = await choices.count();
      report.company_switch.reason = report.company_switch.option_count < 2 ? 'no_assigned_alternative_company' : 'separate_bounded_switch_measurement_required';
    }
    report.status = 'observed';
  } catch (error) {
    report.status = 'failed';
    report.error = String(error.message).replaceAll(password, '[redacted]');
    process.exitCode = 1;
  } finally {
    for (const resource of [context, browser].filter(Boolean)) {
      try { await resource.close(); }
      catch (error) {
        report.status = 'failed';
        report.cleanup_errors ||= [];
        report.cleanup_errors.push(String(error.message).replaceAll(password, '[redacted]'));
        process.exitCode = 1;
      }
    }
    fs.mkdirSync(path.dirname(output), { recursive: true });
    fs.writeFileSync(output, JSON.stringify(report, null, 2) + '\n');
    console.log(JSON.stringify({ status: report.status, samples: report.login_samples.length, output }));
  }
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch(error => { console.error(String(error.message).replaceAll(process.env.SC_DEMO_USER_PASSWORD || '\0', '[redacted]')); process.exitCode = 1; });
}
