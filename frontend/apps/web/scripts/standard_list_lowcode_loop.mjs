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
const digest = (value) => createHash('sha256').update(value).digest('hex');

// Recovery reads the authoritative state even when publish timed out. It never
// repeats publish, overwrites somebody else's conflict, or hides cleanup failure.
export function permitsOwnedChangeSetUiWrite(body, token) {
  return Boolean(token && ['ui.business_config.change_set.validate', 'ui.business_config.change_set.publish',
    'ui.business_config.change_set.rollback'].includes(body?.intent)
    && body.params?.change_set_token === token && !body.params?.role_key);
}

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

// Preserve the complete column universe; visibility and mappings inherit from
// the authoritative schema. Direct `visible:false` would REMOVE a column.
export function completeLabelColumns(contract, label) {
  listLabels(contract);
  const profile = contract.layoutContract.listProfile;
  const columns = profile?.columns;
  assert.ok(Array.isArray(columns) && columns.length > 0, 'complete list profile required');
  assert.ok(columns.every((name) => typeof name === 'string' && name.length), 'column names required');
  assert.equal(new Set(columns).size, columns.length, 'duplicate profile columns');
  assert.ok(columns.includes('name'), 'label target missing');
  for (const key of ['fact_columns', 'hidden_columns']) {
    assert.ok(Array.isArray(profile[key]), `missing ${key}`);
    assert.ok(profile[key].every((name) => columns.includes(name)), `uncovered ${key}`);
  }
  const fields = [];
  const visit = (node) => {
    if (!node || typeof node !== 'object') return;
    if (node.widgetType === 'table' && node.fieldCode) fields.push(node.fieldCode);
    Object.values(node).forEach(visit);
  };
  visit(contract.layoutContract.containerTree);
  assert.deepEqual(fields, columns, 'table widgets must match complete ordered profile');
  return columns.map((name, index) => ({ name, sequence: (index + 1) * 10, ...(name === 'name' ? { label } : {}) }));
}

export function labelOnlyProjection(contract, label, configured = false) {
  completeLabelColumns(contract, label);
  const result = structuredClone(contract);
  const profile = result.layoutContract.listProfile;
  // Full-list configuration becomes the strict column authority only during
  // draft/published comparison. Restoration must remove that authority again.
  if (configured) {
    assert.deepEqual(profile.column_policy, {
      mode: 'strict', reason: 'business_list_config_contract_authoritative',
      owner_layer: 'ui.business.config.contract.view_orchestration',
    }, 'only the exact configured column authority is allowed');
    assert.equal(profile.sourceAuthority?.source_key, 'list_profile.business_config_contract_authoritative');
    delete profile.column_policy;
    profile.sourceAuthority.source_key = 'list_profile';
  } else {
    assert.equal(profile.column_policy, undefined, 'baseline/restored configuration authority must be absent');
    assert.equal(profile.sourceAuthority?.source_key, 'list_profile', 'baseline/restored native authority required');
  }

  if (profile.column_labels?.name === label) profile.column_labels.name = '__LABEL_UNDER_TEST__';
  const visitContainer = (node) => {
    for (const widget of node.widgetList || []) {
      if (widget.widgetType !== 'table' || widget.fieldCode !== 'name') continue;
      if (widget.label === label) widget.label = '__LABEL_UNDER_TEST__';
      if (widget.fieldDescriptor?.name === 'name') {
        for (const key of ['label', 'string']) {
          if (widget.fieldDescriptor[key] === label) widget.fieldDescriptor[key] = '__LABEL_UNDER_TEST__';
        }
      }
    }
    for (const child of node.children || []) visitContainer(child);
  };
  result.layoutContract.containerTree.forEach(visitContainer);
  // Only documented request identities and content hashes vary independently
  // of capabilities. Definition, authority, trim counts and all runtime remain.
  const meta = result.meta || {};
  for (const key of ['etag', 'snapshotId', 'traceId', 'requestId']) delete meta[key];
  if (meta.lifecycle?.generation) delete meta.lifecycle.generation.sourceSha256;
  if (meta.lifecycle?.integrity) delete meta.lifecycle.integrity.contractSha256;
  if (meta.lifecycle?.runtime) {
    delete meta.lifecycle.runtime.requestId;
    delete meta.lifecycle.runtime.traceId;
  }
  return result;
}

export function recordIds(records) {
  assert.ok(Array.isArray(records) && records.length > 0, 'nonempty record set required');
  const ids = records.map((row) => row.id);
  assert.ok(ids.every((id) => Number.isInteger(id) && id > 0), 'positive record identity required');
  assert.equal(new Set(ids).size, ids.length, 'duplicate record identity');
  return ids;
}

async function servedIdentity() {
  const build = JSON.parse(execFileSync('python3', [path.join(root, 'scripts/dev/frontend_standard_preview.py'), 'identity'], { cwd: root, encoding: 'utf8' }));
  const bytes = Buffer.from(await fetch(`${base}${build.entry}`).then((res) => { assert.ok(res.ok); return res.arrayBuffer(); }));
  assert.equal(digest(bytes), build.entry_sha256, 'live managed preview entry');
  return { ...build, backend_source: process.env.WEB_LC_BACKEND_REVISION };
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
  let browser, page, workbench, token, baseline, baselineProjection, baselineLabel, publishAttempted = false;
  const uiPublish = process.env.WEB_LC_UI_PUBLISH === '1';
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
  // The authenticated actor is config_admin; the target is the existing
  // company/action list configuration, not a role-specific form override.
  const cs = (op, params = {}) => intent(`ui.business_config.change_set.${op}`, { role_key: '', ...params });
  const contract = (extra = {}) => intent('ui.contract.v2', { op: 'action_open', action_id: 775, menu_id: 545, view_type: 'tree', client_type: 'web_pc', delivery_profile: 'full', ...extra });
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
    const query = { domain: request.domain, context: request.context, order: request.order, limit: request.limit, offset: request.offset };
    // Presentation projections legitimately change when a configuration changes.
    // Compare the actual ordered IDs and a separate fixed business-field read,
    // rather than equating the whole presentation response with business facts.
    const ids = recordIds(body.data.records);
    const facts = await intent('api.data', { op: 'list', model: 'payment.request', ...query, fields: ['id', 'name', 'amount', 'state', 'write_date'] });
    assert.deepEqual(recordIds(facts.records), ids, 'fixed-field read retains the exact authorized result set');
    const values = facts.records.map((row) => ['id', 'name', 'amount', 'state', 'write_date'].map((key) => {
      assert.ok(Object.hasOwn(row, key), `missing business field: ${key}`);
      return row[key];
    }));
    return { headers: headers.map((value) => value.replace(/\s+/g, ' ').trim()), request: query, record_ids: ids, business_facts_sha256: digest(JSON.stringify(values)) };
  }
  try {
    report.identity = await servedIdentity();
    browser = await launchChromium({ headless: true });
    const browserContext = await browser.newContext({ viewport: { width: 1440, height: 950 }, locale: 'zh-CN' });
    page = await browserContext.newPage();
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
    const baselineContract = await contract();
    await fs.writeFile(path.join(out, 'baseline-contract.json'), JSON.stringify(baselineContract, null, 2), { mode: 0o600 });
    baseline = listLabels(baselineContract);
    const field = baseline.find(([key]) => key === 'name');
    assert.ok(field, 'name column must exist in effective contract');
    baselineLabel = field[1];
    baselineProjection = labelOnlyProjection(baselineContract, baselineLabel);
    const beforeHeaders = await observe(field[1]);
    check('bootstrap includes system.init and contract', bootstrap.has('system.init') && [...bootstrap].some((name) => /^ui\.contract/.test(name)));
    report.baseline = { labels: baseline, surface: beforeHeaders };
    await page.screenshot({ path: path.join(out, 'before.png') });
    check('readonly has no browser exceptions', errors.length === 0);
    report.status = 'readonly_passed';
    if (process.env.WEB_LC_APPLY !== '1') return;

    assert.deepEqual(baselineContract.dataContract?.dataSource?.primary?.params?.context?.allowed_company_ids, [8], 'exact existing acceptance company scope');
    if (uiPublish) {
      const existing = await cs('open', { resume_only: true, target_model: 'payment.request', target_action_id: 775 });
      assert.equal(existing.created, false);
      assert.ok(!existing.token, 'existing scoped draft must not be changed by this probe');
    }
    const opened = await cs('open', { name: run, ...(uiPublish ? { fresh: true, target_model: 'payment.request', target_action_id: 775 } : {}) });
    if (uiPublish) assert.equal(opened.created, true, 'UI probe owns a fresh isolated draft');
    token = opened.token;
    report.change_set_token = token;
    await save(); // Recovery identity is durable before any publish request.
    const label = `配置闭环-${run.slice(-8)}`;
    await cs('stage', { change_set_token: token, config_type: 'list', target_key: run, model: 'payment.request', action_id: 775, view_type: 'tree', draft_payload: { view_orchestration: { source: 'smart_core.lowcode.business_config', views: { tree: { columns: completeLabelColumns(baselineContract, label) } } } } });
    check('validated ready', (await cs('validate', { change_set_token: token })).state === 'ready');
    const preview = await cs('preview', { change_set_token: token, device: 'desktop' });
    check('preview has no formal configuration writes', preview.preview?.formal_config_mutation_count === 0);
    assert.equal(preview.preview?.creator_only, true);
    assert.equal(preview.preview?.company_id, 8);
    assert.equal(preview.preview?.role_key, '');
    const draft = await contract({ preview_token: preview.preview.token, preview_role_key: '' });
    await fs.writeFile(path.join(out, 'draft-contract.json'), JSON.stringify(draft, null, 2), { mode: 0o600 });
    check('draft consumes label', listLabels(draft).some(([key, value]) => key === 'name' && value === label));
    assert.deepEqual(labelOnlyProjection(draft, label, true), baselineProjection, 'draft changes capabilities beyond target label; publish prohibited');
    check('draft preserves complete capabilities', true);
    report.publish_request_id = `${run}-publish`;
    report.publish_attempted = publishAttempted = !uiPublish;
    await save();
    let published;
    if (uiPublish) {
      workbench = await page.context().newPage();
      const session = await page.evaluate(() => Object.fromEntries(Object.entries(sessionStorage)));
      await workbench.addInitScript((values) => { for (const [key, value] of Object.entries(values)) sessionStorage.setItem(key, value); }, session);
      workbench.on('pageerror', (error) => errors.push(error.message));
      await workbench.route('**/api/v1/intent*', async (route) => {
        const body = route.request().postDataJSON();
        const name = body?.intent || '';
        if (name.startsWith('ui.business_config.change_set.') && !['get', 'open', 'resume'].some((op) => name.endsWith(`.${op}`))) {
          if (!permitsOwnedChangeSetUiWrite(body, token)) { errors.push('UI attempted an unowned change-set mutation'); return route.abort(); }
          if (name.endsWith('.publish')) {
            report.publish_request_id = body.params.request_id;
            report.publish_attempted = publishAttempted = true;
            await save();
          }
        }
        if (name === 'ui.business_config.change_set.open' && body.params?.resume_only !== true) {
          errors.push('UI attempted to open a new draft'); return route.abort();
        }
        if (name === 'api.data' && !['list', 'read', 'default_get'].includes(body.params?.op)) {
          errors.push('UI attempted a business write'); return route.abort();
        }
        return route.continue();
      });
      const resumed = workbench.waitForResponse((res) => {
        try { const body = res.request().postDataJSON(); return body?.intent === 'ui.business_config.change_set.open' && body.params?.target_model === 'payment.request' && Number(body.params?.target_action_id) === 775; } catch { return false; }
      });
      await workbench.goto(`${base}/admin/business-config?model=payment.request&action_id=775&menu_id=545`);
      const resumedResponse = await resumed;
      const resumedBody = await resumedResponse.json();
      report.uiResume = { params: resumedResponse.request().postDataJSON()?.params, ok: resumedBody.ok, state: resumedBody.data?.state, keys: Object.keys(resumedBody.data || {}), owned: resumedBody.data?.token === token };
      await save();
      assert.ok(report.uiResume.owned, 'workbench resumes the owned draft');
      const response = workbench.waitForResponse((res) => {
        try { return res.request().postDataJSON()?.intent === 'ui.business_config.change_set.publish'; } catch { return false; }
      });
      await workbench.getByRole('button', { name: '发布全部可逆配置', exact: true }).click();
      await workbench.getByRole('button', { name: '确认继续', exact: true }).click();
      const result = await (await response).json();
      assert.equal(result.ok, true);
      published = result.data;
      await workbench.getByRole('button', { name: '按批次回滚', exact: true }).waitFor();
      await workbench.screenshot({ path: path.join(out, 'workbench-published.png') });
      check('workbench UI published owned configuration', true);
    } else published = await cs('publish', { change_set_token: token, request_id: report.publish_request_id });
    check('published content verified', published.state === 'published' && published.publish_result?.published_content_verified === true);
    const publishedContract = await contract();
    assert.deepEqual(labelOnlyProjection(publishedContract, label, true), baselineProjection, 'published capabilities must match baseline');
    report.published_labels = listLabels(publishedContract);
    check('effective contract consumes label', report.published_labels.some(([key, value]) => key === 'name' && value === label));
    report.changed_headers = await observe(label);
    assert.deepEqual(report.changed_headers.record_ids, beforeHeaders.record_ids, 'configuration must preserve ordered record identity');
    assert.equal(report.changed_headers.business_facts_sha256, beforeHeaders.business_facts_sha256, 'configuration must preserve fixed business fields and write_date');
    assert.deepEqual(report.changed_headers.request, beforeHeaders.request, 'configuration must preserve query and authorization context');
    await page.screenshot({ path: path.join(out, 'published.png') });
    if (uiPublish) {
      const response = workbench.waitForResponse((res) => {
        try { return res.request().postDataJSON()?.intent === 'ui.business_config.change_set.rollback'; } catch { return false; }
      });
      await workbench.getByRole('button', { name: '按批次回滚', exact: true }).click();
      const result = await (await response).json();
      assert.equal(result.ok, true);
      assert.equal(result.data?.publish_result?.published_content_verified, true);
      report.recovery = 'rolled_back';
      await workbench.screenshot({ path: path.join(out, 'workbench-restored.png') });
      check('workbench UI rollback verified', true);
    } else report.recovery = await recoverChangeSet(cs, token, `${run}-rollback`, publishAttempted);
    token = null;
    assert.deepEqual(labelOnlyProjection(await contract(), baselineLabel), baselineProjection, 'restored complete capabilities');
    assert.deepEqual(await observe(field[1]), beforeHeaders, 'restored visible headers, query and records');
    await page.screenshot({ path: path.join(out, 'restored.png') });
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
        if (baselineProjection) assert.deepEqual(labelOnlyProjection(await contract(), baselineLabel), baselineProjection, 'emergency complete capability restoration');
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
