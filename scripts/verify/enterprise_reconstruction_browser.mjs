import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { launchChromium } from './playwright_runtime.mjs';

const OUT = process.env.RECONSTRUCTION_OUT;
const BASE = 'http://127.0.0.1:19083/t/clean';
const SOURCE = process.env.SC_SOURCE_REVISION;
assert.match(SOURCE || '', /^[0-9a-f]{40}$/);
assert.equal(process.env.DB_NAME, 'sc_init_6b0769da09e2');
assert.equal(process.env.COMPOSE_PROJECT_NAME, 'sc-init-6b0769da09e2');
assert.ok(OUT && process.env.FRESH_DB_PASSWORD);
const reference = JSON.parse(fs.readFileSync(path.join(OUT, 'reference.json'), 'utf8'));
const businessUsers = reference.records.filter(row => row.model === 'res.users' && /group_sc_role_/.test(row.fields.groups_id?.eval || ''));
const previous = fs.existsSync(path.join(OUT, 'configuration-progress.json')) ? JSON.parse(fs.readFileSync(path.join(OUT, 'configuration-progress.json'), 'utf8')) : null;
if (previous) fs.copyFileSync(path.join(OUT, 'browser-report.json'), path.join(OUT, `browser-report-${Date.now()}.json`));
const lastAttempt = fs.existsSync(path.join(OUT, 'browser-report.json')) ? JSON.parse(fs.readFileSync(path.join(OUT, 'browser-report.json'), 'utf8')) : null;
const report = { stage: 'base_plus_declared_dirty_scope', product_patch_sha256: Object.fromEntries(['addons/smart_core/core/unified_page_contract_v2_assembler.py', 'addons/smart_core/app_config_engine/services/assemblers/page_assembler.py'].map(file => [file, createHash('sha256').update(fs.readFileSync(file)).digest('hex')])), pendingRecord: lastAttempt?.pendingRecord || (lastAttempt?.writes?.some(write => write.model === 'res.users' && write.op === 'create' && write.ok && write.id === 7) ? { model: 'res.users', id: 7, xmlid: 'smart_construction_demo.user_sc_operation_demo' } : null), status: 'running', source: SOURCE, identity: {}, stages: {}, writes: [], errors: [] };
const save = () => {
  fs.writeFileSync(path.join(OUT, 'browser-report.json'), `${JSON.stringify(report, null, 2)}\n`);
  if (Object.values(report.stages).some(stage => stage.records?.length)) {
    fs.writeFileSync(path.join(OUT, 'configuration-progress.json'), `${JSON.stringify({ ...report, stages: { ...previous?.stages, ...report.stages } }, null, 2)}\n`);
  }
};
const value = (row, key) => row.fields[key]?.text || '';
const redact = data => JSON.parse(JSON.stringify(data, (key, val) => /password|token|secret/i.test(key) ? '[REDACTED]' : val));
const unwrap = body => body.data || body.result?.data || body.result || {};
const bodyOf = request => { try { return request.postDataJSON() || {}; } catch { return {}; } };
const browser = await launchChromium({ headless: true });
const context = await browser.newContext({ locale: 'zh-CN', viewport: { width: 1440, height: 1000 } });
const page = await context.newPage();
const observed = [];
page.on('response', async response => {
  if (!response.url().includes('/api/v1/intent')) return;
  try {
    const request = bodyOf(response.request());
    const body = await response.json();
    const data = unwrap(body);
    observed.push(redact({ request, body }));
    if (request.intent === 'login') {
      report.identity = { user: data.user, principal: data.principal };
    }
    if (request.intent === 'api.data' && ['create', 'write', 'unlink'].includes(request.params?.op)) {
      // Passwords and credentials must not be copied to the public report.
      report.writes.push({ model: request.params?.model, op: request.params?.op,
        fields: Object.keys(request.params?.vals || {}), ok: body.ok === true, ids: data.ids, id: data.id });
    }
  } catch { /* explicit save/readback assertions remain authoritative */ }
});

async function enterprise() {
  const catalogResponse = page.waitForResponse(response => response.url().includes('/api/v1/intent')
    && bodyOf(response.request()).intent === 'scenario.activation.catalog.get', { timeout: 60000 });
  const diagnosisResponse = page.waitForResponse(response => response.url().includes('/api/v1/intent')
    && bodyOf(response.request()).intent === 'enterprise.readiness.diagnosis.get', { timeout: 60000 });
  await page.goto(`${BASE}/s/enterprise.setup`, { waitUntil: 'domcontentloaded' });
  await page.locator('button.handling-item[data-action-xmlid]').first().waitFor({ timeout: 45000 });
  const [catalogBody, diagnosisBody] = await Promise.all([
    catalogResponse.then(response => response.json()), diagnosisResponse.then(response => response.json()),
  ]);
  assert.equal(catalogBody.ok, true, JSON.stringify(catalogBody.error || {}));
  assert.equal(diagnosisBody.ok, true, JSON.stringify(diagnosisBody.error || {}));
  report.diagnosis = unwrap(diagnosisBody);
  return unwrap(catalogBody);
}

async function entry(label, create = true) {
  await enterprise();
  await page.locator('button.handling-item[data-action-xmlid]').filter({ hasText: label }).click();
  await page.locator('[data-semantic-component="ActionView"]:visible').waitFor({ timeout: 45000 });
  if (create) await page.getByRole('button', { name: /^(新建|新增|创建)$/ }).first().waitFor({ timeout: 30000 });
  else await page.locator('tr[data-record-key] button[data-semantic-cell-kind="primary"]:visible').first().waitFor({ timeout: 45000 });
  return page.url();
}

async function relation(field, label, expectedId) {
  const input = page.locator(`[data-field-name="${field}"] input:visible`).first();
  await input.click();
  await input.fill(label);
  const popup = page.locator('.many2one-option-panel:visible');
  await popup.waitFor({ state: 'visible' });
  await popup.getByRole('button', { name: /搜索更多/ }).click();
  const dialog = page.locator('.relation-dialog:visible');
  await dialog.waitFor({ state: 'visible' });
  const query = dialog.locator('input[type="search"]');
  await query.fill(label);
  await dialog.getByRole('button', { name: /^搜索$/ }).click();
  const result = expectedId ? dialog.locator(`[data-semantic-component="RelationSearchResult"][data-record-id="${expectedId}"]:visible`) : dialog.locator('[data-semantic-component="RelationSearchResult"]:visible').filter({ hasText: label });
  await result.first().click({ timeout: 15000 });
  await dialog.getByRole('button', { name: /^选择$/ }).click();
  await dialog.waitFor({ state: 'hidden' });
}

async function checkVisible(scope) {
  const input = scope.locator('input[type="checkbox"]').first();
  if (!await input.isChecked()) await scope.locator('label.t-checkbox').first().click();
  assert.equal(await input.isChecked(), true);
}

async function createRecord(listUrl, row, parentLabel = '', parentId) {
  await page.goto(listUrl, { waitUntil: 'domcontentloaded' });
  await page.getByRole('button', { name: /^(新建|新增|创建)$/ }).first().click({ timeout: 30000 });
  await page.locator('[data-semantic-component="ContractFormPage"][data-state="ok"]:visible').waitFor({ timeout: 30000 });
  const nameInput = page.locator('[data-field-name="name"] input:visible').first();
  await nameInput.fill(value(row, 'name'));
  await nameInput.press('Tab');
  assert.equal(await nameInput.inputValue(), value(row, 'name'));
  if (parentLabel) await relation('parent_id', parentLabel, parentId);
  if (row.model === 'res.users') {
    const email = value(row, 'email');
    if (email) await page.locator('[data-field-name="email"] input:visible').first().fill(email);
    const employee = reference.records.find(item => item.model === 'hr.employee' && item.fields.user_id?.ref === row.xmlid);
    if (employee) {
      for (const [target, source] of [['sc_personnel_department_id', 'department_id'], ['sc_personnel_job_id', 'job_id']]) {
        const related = reference.records.find(item => item.xmlid === employee.fields[source]?.ref);
        assert.ok(related, `unresolved employee reference ${source}`);
        const binding = report.stages[related.model]?.records.find(item => item.xmlid === related.xmlid);
        assert.ok(binding);
        await relation(target, value(related, 'name'), binding.id);
      }
    }
    if (employee) await checkVisible(page.locator('[data-field-name="sc_personnel_active"]'));
    const loginInput = page.locator('[data-field-name="login"] input:visible').first();
    if (!await loginInput.isVisible()) await page.getByText('登录与账号', { exact: true }).click();
    await loginInput.fill(value(row, 'login'));
    await page.locator('[data-field-name="password"] input:visible').first().fill(process.env.FRESH_DB_PASSWORD);
  }
  const write = page.waitForResponse(response => {
    const body = bodyOf(response.request());
    return response.url().includes('/api/v1/intent') && body.intent === 'api.data'
      && body.params?.model === row.model && body.params?.op === 'create';
  }, { timeout: 30000 });
  const mark = observed.length;
  await page.locator('button[data-action-ref="form.save"]:visible').click();
  const response = await write;
  const body = await response.json();
  assert.equal(response.status(), 200);
  assert.equal(body.ok, true, JSON.stringify(body.error || {}));
  report.pendingRecord = { xmlid: row.xmlid, id: unwrap(body).id, model: row.model }; save();
  await page.waitForURL(url => !url.pathname.endsWith('/new'), { timeout: 30000 });
  await page.locator('[data-semantic-component="ContractFormPage"][data-state="ok"]:visible').waitFor({ timeout: 30000 });
  const name = await page.locator('[data-field-name="name"] input:visible').first().inputValue();
  assert.equal(name, value(row, 'name'));
  const id = Number(new URL(page.url()).pathname.split('/').pop());
  assert.ok(id > 0, 'save must establish a real record');
  report.pendingRecord = null;
  return { xmlid: row.xmlid, name, id, model: row.model, url: page.url(), status: 'passed', observed_responses: observed.length - mark };
}

try {
  let runtimeResponse;
  for (let attempt = 0; attempt < 40; attempt += 1) {
    runtimeResponse = await context.request.get(`${BASE}/api/runtime-version`);
    if (runtimeResponse.status() === 200) break;
    await page.waitForTimeout(1000);
  }
  assert.equal(runtimeResponse.status(), 200);
  report.runtime = await runtimeResponse.json();
  assert.equal(report.runtime.database, process.env.DB_NAME);
  assert.equal(report.runtime.source_revision, SOURCE);
  assert.match(report.runtime.frontend_build_sha256, /^[0-9a-f]{64}$/);
  if (previous) {
    assert.equal(previous.runtime.database, report.runtime.database);
    report.prior_configuration_build = previous.runtime.frontend_build_sha256; // data progress, not a current-build test receipt
    report.prior_configuration_source = previous.source; // only committed data identities are reused
  }
  await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded' });
  await page.locator('#login-username').fill('init_business_admin');
  await page.locator('#login-password').fill(process.env.FRESH_DB_PASSWORD);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 45000 });
  const catalog = await enterprise();
  assert.equal(catalog.actor?.login, 'init_business_admin');
  assert.equal(catalog.actor?.platform_admin, false);
  await page.screenshot({ path: path.join(OUT, '00-initialization.png'), fullPage: true });
  save();
  for (const [model, label] of [['hr.department', '组织架构'], ['hr.job', '岗位管理'], ['res.users', '人员与账号']]) {
    const stage = report.stages[model] = { status: 'running', records: previous?.stages?.[model]?.records || [], expected: 0 };
    try {
      save();
      const scopedRecords = model === 'res.users' ? businessUsers : reference.records.filter(row => row.model === model);
      stage.expected = scopedRecords.length;
      if (model === 'res.users') report.technical_accounts_separate = reference.records.filter(row => row.model === model && !businessUsers.includes(row)).map(row => ({ xmlid: row.xmlid, login: value(row, 'login'), reason: 'direct platform capability fixture; owner excluded from business configuration parity' }));
      if (stage.records.length === stage.expected) { stage.status = 'passed'; stage.reused = true; save(); continue; }
      const listUrl = await entry(label);
      const created = new Map(stage.records.map(row => [row.xmlid, row]));
      if (model === 'res.users' && report.pendingRecord?.model === model && !created.has(report.pendingRecord.xmlid)) {
        // Recover the recorded successful first create; never repeat a committed write.
        const pending = report.pendingRecord;
        const row = reference.records.find(item => item.xmlid === pending.xmlid);
        assert.ok(row);
        await page.getByText(value(row, 'name'), { exact: true }).and(page.locator(':visible')).first().click();
        await page.waitForURL(url => url.pathname.endsWith(`/${pending.id}`), { timeout: 30000 });
        await page.locator('[data-semantic-component="ContractFormPage"][data-state="ok"]:visible').waitFor({ timeout: 30000 });
        assert.equal(await page.locator('[data-field-name="name"] input:visible').first().inputValue(), value(row, 'name'));
        await checkVisible(page.locator('[data-field-name="sc_personnel_active"]'));
        const response = page.waitForResponse(res => bodyOf(res.request()).intent === 'api.data' && bodyOf(res.request()).params?.op === 'write');
        await page.locator('button[data-action-ref="form.save"]:visible').click();
        assert.equal((await (await response).json()).ok, true);
        const recovered = { xmlid: row.xmlid, id: pending.id, model, name: value(row, 'name'), url: page.url(), status: 'passed', recovered_committed_create: true };
        stage.records.push(recovered); created.set(row.xmlid, recovered); report.pendingRecord = null; save();
      }
      const remaining = scopedRecords.filter(row => !created.has(row.xmlid));
      while (remaining.length) {
        const index = remaining.findIndex(row => !row.fields.parent_id?.ref || created.has(row.fields.parent_id.ref));
        assert.ok(index >= 0, 'reference contains an unresolved parent');
        const row = remaining.splice(index, 1)[0];
        const result = await createRecord(listUrl, row, created.get(row.fields.parent_id?.ref)?.name, created.get(row.fields.parent_id?.ref)?.id);
        created.set(row.xmlid, result);
        stage.records.push(result);
        save();
      }
      stage.status = 'passed';
    } catch (error) {
      stage.status = 'failed';
      stage.error = error.message;
      stage.contract_observations = observed.filter(row => row.request.intent === 'ui.contract.v2').slice(-2);
      stage.read_observations = observed.filter(row => row.request.intent === 'api.data' && row.request.params?.model === model && !['create', 'write', 'unlink'].includes(row.request.params?.op)).slice(-6);
      report.errors.push(`${model}: ${error.message}`);
      await page.screenshot({ path: path.join(OUT, `${model}.failure.png`), fullPage: true });
      fs.writeFileSync(path.join(OUT, `${model}.failure.txt`), await page.locator('body').innerText());
    }
    save();
  }
  const alignment = report.stages.relationship_alignment = { status: 'running', records: previous?.stages?.relationship_alignment?.records || [] };
  try {
    const facts = JSON.parse(fs.readFileSync(path.join(OUT, 'configuration-facts.json'), 'utf8'));
    const binding = new Map(Object.values(report.stages).flatMap(stage => stage.records || []).filter(row => row.id).map(row => [row.xmlid, row]));
    const employeeId = xmlid => {
      const source = reference.records.find(row => row.xmlid === xmlid);
      const user = binding.get(source?.fields.user_id?.ref);
      const matches = facts['hr.employee'].rows.filter(row => user && row.user_id?.[0] === user.id);
      assert.equal(matches.length, 1);
      return { id: matches[0].id, name: value(source, 'name') };
    };
    const updates = [];
    for (const source of reference.records.filter(row => row.model === 'hr.department')) {
      const record = binding.get(source.xmlid);
      const actual = facts['hr.department'].rows.find(row => row.id === record?.id);
      assert.ok(actual);
      for (const field of ['parent_id', 'manager_id']) {
        const ref = source.fields[field]?.ref;
        if (!ref) continue;
        const target = field === 'manager_id' ? employeeId(ref) : binding.get(ref);
        assert.ok(target);
        if (actual[field]?.[0] !== target.id) updates.push({ record, field: field === 'manager_id' ? 'sc_manager_public_id' : field, target });
      }
    }
    for (const employee of reference.records.filter(row => row.model === 'hr.employee')) {
      const record = binding.get(employee.fields.user_id.ref);
      const actual = facts['res.users'].rows.find(row => row.id === record?.id);
      for (const [field, sourceField] of [['sc_personnel_department_id', 'department_id'], ['sc_personnel_job_id', 'job_id']]) {
        const target = binding.get(employee.fields[sourceField].ref);
        if (actual[field]?.[0] !== target.id) updates.unshift({ record, field, target });
      }
    }
    for (const { record, field, target } of updates) {
      await page.goto(record.url, { waitUntil: 'domcontentloaded' });
      await page.locator('[data-semantic-component="ContractFormPage"][data-state="ok"]:visible').waitFor({ timeout: 30000 });
      await relation(field, target.name, target.id);
      const write = page.waitForResponse(res => bodyOf(res.request()).intent === 'api.data' && bodyOf(res.request()).params?.op === 'write');
      await page.locator('button[data-action-ref="form.save"]:visible').click();
      const response = await write;
      assert.equal(bodyOf(response.request()).params.vals[field], target.id);
      assert.equal((await response.json()).ok, true);
      alignment.records.push({ xmlid: record.xmlid, field, target_id: target.id, status: 'saved_pending_parity' }); save();
    }
    alignment.status = 'saved_pending_parity';
  } catch (error) {
    alignment.status = 'failed'; alignment.error = error.message; report.errors.push(`relationships: ${error.message}`);
    alignment.contract_observations = observed.filter(row => row.request.intent === 'ui.contract.v2').slice(-2);
    await page.screenshot({ path: path.join(OUT, 'relationships.failure.png'), fullPage: true });
    fs.writeFileSync(path.join(OUT, 'relationships.failure.txt'), await page.locator('body').innerText());
  }
  const roles = report.stages.roles = { status: 'running', records: previous?.stages?.roles?.records || [] };
  try {
    await entry('业务权限分配', false);
    const permissionOpen = observed.filter(item => item.request.intent === 'ui.contract.v2' && item.request.params?.op === 'action_open').at(-1);
    const actionId = Number(permissionOpen?.request.params.action_id);
    assert.ok(Number.isInteger(actionId));
    const groupFacts = JSON.parse(fs.readFileSync(path.join(OUT, 'configuration-facts.json'), 'utf8'))['res.groups'];
    const groupIdByXmlid = new Map(Object.entries(groupFacts.external_ids).map(([id, xmlid]) => [xmlid, Number(id)]));
    const groups = new Map(groupFacts.rows.map(group => [group.id, group]));
    for (const account of report.stages['res.users'].records) {
      if (roles.records.some(row => row.xmlid === account.xmlid)) continue;
      const source = businessUsers.find(row => row.xmlid === account.xmlid);
      const refs = [...source.fields.groups_id.eval.matchAll(/ref\(['"]([^'"]+)['"]\)/g)].map(match => match[1]).filter(ref => ref.includes('.group_sc_role_'));
      assert.ok(refs.length);
      const expected = refs.map(ref => groups.get(groupIdByXmlid.get(ref)));
      assert.ok(expected.every(Boolean));
      const url = new URL(account.url);
      url.searchParams.set('action_id', String(actionId));
      await page.goto(url.href, { waitUntil: 'domcontentloaded' });
      await page.locator('[data-semantic-component="ContractFormPage"][data-state="ok"]:visible').waitFor({ timeout: 30000 });
      const field = page.locator('[data-field-name="sc_user_permission_group_ids"]:visible');
      // Roles are assigned by the actual native import batch. This step only
      // verifies the resulting user-facing labels; do not repeat per-user writes.
      const userFacts = JSON.parse(fs.readFileSync(path.join(OUT, 'configuration-facts.json'), 'utf8'))['res.users'];
      const saved = userFacts.rows.find(row => row.id === account.id);
      assert.ok(expected.every(group => saved.groups_id.includes(group.id)), 'native role import must precede UI readback');
      await page.reload({ waitUntil: 'domcontentloaded' });
      await page.locator('[data-semantic-component="ContractFormPage"][data-state="ok"]:visible').waitFor({ timeout: 30000 });
      for (const group of expected) await field.getByText(group.name, { exact: false }).first().waitFor({ timeout: 20000 });
      roles.records.push({ xmlid: account.xmlid, user_id: account.id, groups: refs, status: 'passed' }); save();
    }
    roles.status = roles.records.length === businessUsers.length ? 'passed' : 'partial';
  } catch (error) {
    roles.status = 'failed'; roles.error = error.message; report.errors.push(`roles: ${error.message}`);
    await page.screenshot({ path: path.join(OUT, 'roles.failure.png'), fullPage: true });
    fs.writeFileSync(path.join(OUT, 'roles.failure.txt'), await page.locator('body').innerText());
  }
  try {
    const catalog = await enterprise();
    const centers = catalog.business_centers;
    assert.equal(centers.length, 10, 'demo reference has ten enabled business centers');
    const sceneKeys = [...new Set(centers.flatMap(center => center.scene_keys))].sort();
    assert.equal(sceneKeys.length, 42, 'demo reference has 42 center-bound scenes');
    if (centers.some(center => center.status !== 'enabled')) {
      for (const center of centers) {
        assert.equal(center.enable_allowed, true);
        await checkVisible(page.locator(`article[data-center-key="${center.key}"]`));
      }
      const response = page.waitForResponse(res => bodyOf(res.request()).intent === catalog.center_activation.intent);
      await page.getByRole('button', { name: catalog.center_activation.apply_label, exact: true }).click();
      const body = await (await response).json();
      assert.equal(body.ok, true, JSON.stringify(body.error || {}));
      const readback = unwrap(body);
      assert.deepEqual([...readback.scene_keys].sort(), sceneKeys);
      assert.equal(readback.enabled_scene_count, 42);
      report.scenario_readback = readback;
    }
    const refreshed = await enterprise();
    assert.ok(refreshed.business_centers.every(center => center.status === 'enabled'));
    report.stages.scenarios = { status: 'passed', centers: 10, scene_keys: sceneKeys,
      reference: 'enterprise-initialization-final/report.json: ten enabled centers, 42 scenes',
      actor: refreshed.actor };
  } catch (error) {
    report.stages.scenarios = { status: 'failed', error: error.message };
    report.errors.push(`scenarios: ${error.message}`);
    await page.screenshot({ path: path.join(OUT, 'scenarios.failure.png'), fullPage: true });
    fs.writeFileSync(path.join(OUT, 'scenarios.failure.txt'), await page.locator('body').innerText());
  }
  report.status = report.errors.length ? 'failed' : 'partial';
  report.remaining = ['people_and_accounts', 'roles', 'scenario_enablement', 'representative_business_journeys'];
} catch (error) {
  report.status = 'failed';
  report.errors.push(error.stack || error.message);
  await page.screenshot({ path: path.join(OUT, 'fatal.png'), fullPage: true }).catch(() => {});
  fs.writeFileSync(path.join(OUT, 'fatal.txt'), await page.locator('body').innerText().catch(() => ''));
} finally {
  save();
  await browser.close();
}
console.log(`[enterprise-reconstruction] ${report.status} writes=${report.writes.length}`);
if (report.status === 'failed') process.exitCode = 1;
