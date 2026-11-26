import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';

assert.equal(process.env.DB_NAME, 'sc_init_6b0769da09e2');
assert.equal(process.env.COMPOSE_PROJECT_NAME, 'sc-init-6b0769da09e2');
const BASE = 'http://127.0.0.1:19083/t/clean';
const OUT = process.env.RECONSTRUCTION_OUT;
assert.ok(OUT && process.env.FRESH_DB_PASSWORD);
const scope = process.env.RECONSTRUCTION_IMPORT_SCOPE || 'all';
const previousReport = path.join(OUT, 'import-report.json');
if (fs.existsSync(previousReport)) fs.copyFileSync(previousReport, path.join(OUT, `import-report-${Date.now()}.json`));
const report = { scope, status: 'running', cases: [], imports: [], errors: [] };
const save = () => fs.writeFileSync(path.join(OUT, 'import-report.json'), `${JSON.stringify(report, null, 2)}\n`);
const bodyOf = request => { try { return request.postDataJSON() || {}; } catch { return {}; } };
const browser = await launchChromium({ headless: true });
const context = await browser.newContext({ locale: 'zh-CN', viewport: { width: 1440, height: 1000 } });
const page = await context.newPage();
page.on('response', async response => {
  const request = bodyOf(response.request());
  if (request.intent !== 'api.data.import') return;
  const body = await response.json().catch(() => ({}));
  const data = body.data || {};
  // Never retain uploaded file contents or credentials in evidence.
  report.imports.push({ model: request.params?.model, dry_run: request.params?.dry_run, phase: request.params?.phase,
    ok: body.ok, error: body.error, mapping: data.mapping, ids: data.ids,
    file_length: data.file_length, imported_count: data.imported_count,
    error_count: data.error_count, valid: data.valid, messages: data.messages });
  save();
});
function parseCsv(text) {
  const rows = []; let row = []; let field = ''; let quoted = false;
  const input = text.replace(/^\uFEFF/, '');
  for (let i = 0; i < input.length; i++) {
    const char = input[i];
    if (char === '"') {
      if (quoted && input[i + 1] === '"') { field += '"'; i++; }
      else quoted = !quoted;
    } else if (!quoted && char === ',') { row.push(field); field = ''; }
    else if (!quoted && char === '\n') { row.push(field.replace(/\r$/, '')); rows.push(row); row = []; field = ''; }
    else field += char;
  }
  assert.equal(quoted, false);
  if (field || row.length) { row.push(field); rows.push(row); }
  return rows;
}
async function exportUpdateIdentities() {
  await page.getByRole('button', { name: '批量导入', exact: true }).click();
  const wizard = page.locator('[data-dialog-purpose="native-import"]:visible');
  await wizard.waitFor({ timeout: 45000 });
  const downloadPromise = page.waitForEvent('download', { timeout: 45000 });
  downloadPromise.catch(() => {});
  const exportResponse = page.waitForResponse(response => bodyOf(response.request()).intent === 'api.data'
    && bodyOf(response.request()).params?.op === 'export_csv', { timeout: 45000 });
  await wizard.getByRole('button', { name: '下载更新标识文件', exact: true }).click();
  const exported = await (await exportResponse).json();
  report.update_export = { ok: exported.ok, error: exported.error, count: exported.data?.count }; save();
  assert.equal(exported.ok, true, JSON.stringify(exported.error));
  assert.ok(exported.data?.count > 0, JSON.stringify(exported));
  const download = await downloadPromise;
  const rows = parseCsv(fs.readFileSync(await download.path(), 'utf8'));
  assert.deepEqual(rows.shift(), ['id', 'name']);
  assert.ok(rows.length);
  await wizard.getByRole('button', { name: '取消', exact: true }).last().click();
  return rows;
}
async function upload(name, content, decision = 'confirm', expectedIds = null) {
  report.step = `upload:${name}`; save();
  await page.getByRole('button', { name: '批量导入', exact: true }).click();
  const wizard = page.locator('[data-dialog-purpose="native-import"]:visible');
  await wizard.waitFor({ timeout: 45000 });
  const previewPromise = page.waitForResponse(response => {
    const body = bodyOf(response.request());
    return body.intent === 'api.data.import' && body.params?.phase === 'inspect';
  }, { timeout: 45000 });
  const chooser = page.waitForEvent('filechooser');
  await wizard.getByRole('button', { name: '选择导入文件', exact: true }).click();
  await (await chooser).setFiles({ name, mimeType: 'text/csv', buffer: Buffer.from(content) });
  await wizard.getByRole('button', { name: '读取预览', exact: true }).click();
  const inspected = await (await previewPromise).json();
  assert.equal(inspected.ok, true, JSON.stringify(inspected.error || {}));
  assert.equal(inspected.data.phase, 'inspect');
  if (name === 'business-jobs.csv') {
    await wizard.getByRole('button', { name: '文件解析选项', exact: true }).click();
    const headers = wizard.locator('[data-semantic-primitive="ScCheckbox"]').filter({ hasText: '首行为列标题' });
    await headers.click();
    assert.equal(await wizard.getByRole('button', { name: '校验数据', exact: true }).isDisabled(), true);
    await headers.click();
    const reinspection = page.waitForResponse(response => bodyOf(response.request()).params?.phase === 'inspect');
    await wizard.getByRole('button', { name: '读取预览', exact: true }).click();
    assert.equal((await (await reinspection).json()).ok, true);
    await wizard.getByRole('button', { name: '文件解析选项', exact: true }).click();
  }
  if (decision === 'cancel') {
    await wizard.getByRole('button', { name: '取消', exact: true }).last().click();
    return inspected.data;
  }
  if (name === 'manual-mapping.csv') {
    assert.equal(inspected.data.mapping[1], false);
    const nameField = inspected.data.native_fields.find(field => field.id === 'name');
    assert.ok(nameField);
    await wizard.locator('[data-import-column="1"] input').first().click();
    await page.getByRole('listitem').getByText(nameField.string, { exact: true }).click();
    assert.equal(await wizard.getByRole('button', { name: '确认导入', exact: true }).isDisabled(), true);
  }
  const validationPromise = page.waitForResponse(response => bodyOf(response.request()).intent === 'api.data.import'
    && bodyOf(response.request()).params?.phase === 'validate');
  await wizard.getByRole('button', { name: '校验数据', exact: true }).click();
  let preview = await (await validationPromise).json();
  assert.equal(preview.ok, true, JSON.stringify(preview.error || {}));
  let data = preview.data;
  const confirm = wizard.getByRole('button', { name: '确认导入', exact: true });
  if (decision === 'forbidden') {
    assert.ok(data.error_count > 0);
    await wizard.getByRole('alert').waitFor();
    assert.equal(await confirm.isDisabled(), true);
    assert.ok(data.messages.some(item => /不可分配|权限/.test(item.message)));
    await wizard.getByRole('button', { name: '取消', exact: true }).last().click();
    return data;
  }
  if (decision === 'invalid' || decision === 'retry') {
    assert.ok(data.error_count > 0, 'invalid rows must fail preview');
    await wizard.getByRole('alert').waitFor({ timeout: 10000 });
    assert.equal(await confirm.isDisabled(), true);
    assert.ok(data.messages.some(item => item.row_label === '第 3 行'), 'native row location must reach the user');
    assert.ok((await wizard.getByRole('alert').innerText()).includes('第 3 行'));
    if (decision === 'invalid') {
      await wizard.getByRole('button', { name: '取消', exact: true }).last().click();
      return data;
    }
    const replacement = page.waitForEvent('filechooser');
    await wizard.getByRole('button', { name: '选择导入文件', exact: true }).click();
    await (await replacement).setFiles({ name: 'corrected.csv', mimeType: 'text/csv',
      buffer: Buffer.from('id,name\n__import__.enterprise_bulk_job_a,修正后岗位甲\n__import__.enterprise_bulk_job_b,修正后岗位乙\n') });
    assert.equal(await confirm.isDisabled(), true);
    const reinspection = page.waitForResponse(response => bodyOf(response.request()).params?.phase === 'inspect');
    await wizard.getByRole('button', { name: '读取预览', exact: true }).click();
    assert.equal((await (await reinspection).json()).ok, true);
    const revalidation = page.waitForResponse(response => bodyOf(response.request()).params?.phase === 'validate');
    await wizard.getByRole('button', { name: '校验数据', exact: true }).click();
    preview = await (await revalidation).json(); data = preview.data;

  }
  assert.equal(data.error_count, 0, JSON.stringify(data.messages));
  assert.equal(data.file_length, expectedIds?.length || 2, 'header is not a data row');
  if (expectedIds) assert.deepEqual([...data.ids].sort((a, b) => a - b), [...expectedIds].sort((a, b) => a - b), 'preview must address exactly the existing records');
  if (name === 'manual-mapping.csv') {
    await wizard.locator('[data-import-column="1"] input').first().click();
    await page.getByRole('listitem').getByText('不导入此列', { exact: true }).click();
    assert.equal(await confirm.isDisabled(), true);
    await wizard.locator('[data-import-column="1"] input').first().click();
    const nameField = inspected.data.native_fields.find(field => field.id === 'name');
    await page.getByRole('listitem').getByText(nameField.string, { exact: true }).click();
    assert.equal(await confirm.isDisabled(), true);
    const revalidation = page.waitForResponse(response => bodyOf(response.request()).params?.phase === 'validate');
    await wizard.getByRole('button', { name: '校验数据', exact: true }).click();
    assert.equal((await (await revalidation).json()).data.valid, true);
  }
  const committed = page.waitForResponse(response => {
    const body = bodyOf(response.request());
    return body.intent === 'api.data.import' && body.params?.dry_run === false;
  }, { timeout: 45000 });
  await confirm.click();
  const result = await (await committed).json();
  assert.equal(result.ok, true, JSON.stringify(result.error || {}));
  assert.equal(result.data.error_count, 0, JSON.stringify(result.data.messages));
  await wizard.getByRole('button', { name: '完成并返回列表', exact: true }).click();
  await page.getByText(`已导入 ${result.data.imported_count} 条记录`, { exact: true }).first().waitFor({ timeout: 30000 });
  return result.data;
}
try {
  let runtimeResponse;
  for (let attempt = 0; attempt < 40; attempt++) {
    runtimeResponse = await context.request.get(`${BASE}/api/runtime-version`);
    if (runtimeResponse.status() === 200) break;
    await page.waitForTimeout(1000);
  }
  assert.equal(runtimeResponse.status(), 200);
  report.runtime = await runtimeResponse.json();
  assert.equal(report.runtime.database, process.env.DB_NAME);
  await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded' });
  await page.locator('#login-username').fill('init_business_admin');
  await page.locator('#login-password').fill(process.env.FRESH_DB_PASSWORD);
  await page.getByRole('button', { name: '登录', exact: true }).click();
  await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 45000 });
  if (scope === 'all') {
  await page.goto(`${BASE}/s/enterprise.setup`, { waitUntil: 'domcontentloaded' });
  await page.locator('button.handling-item[data-action-xmlid]').filter({ hasText: '岗位管理' }).click();
  await page.getByRole('button', { name: '批量导入', exact: true }).waitFor({ timeout: 45000 });
  report.actor = 'init_business_admin'; report.entry_url = page.url(); save();
  const first = await upload('business-jobs.csv', 'id,name\n__import__.enterprise_bulk_job_a,批量验收岗位甲\n__import__.enterprise_bulk_job_b,批量验收岗位乙\n');
  assert.deepEqual(first.mapping, ['id', 'name']); assert.equal(first.ids.length, 2);
  for (const name of ['批量验收岗位甲', '批量验收岗位乙']) await page.getByText(name, { exact: true }).and(page.locator(':visible')).first().waitFor({ timeout: 30000 });
  report.cases.push({ name: 'two_row_import_and_ui_readback', status: 'passed', ids: first.ids }); save();
  const updated = await upload('business-jobs-update.csv', 'id,name\n__import__.enterprise_bulk_job_a,批量验收岗位甲更新\n__import__.enterprise_bulk_job_b,批量验收岗位乙更新\n');
  assert.deepEqual([...updated.ids].sort(), [...first.ids].sort(), 'same external ids must update rather than duplicate');
  for (const name of ['批量验收岗位甲更新', '批量验收岗位乙更新']) await page.getByText(name, { exact: true }).and(page.locator(':visible')).first().waitFor({ timeout: 30000 });
  report.cases.push({ name: 'external_id_update_without_duplicates', status: 'passed', ids: updated.ids }); save();
  const mapped = await upload('manual-mapping.csv', `id,unrecognized_${Date.now()}\n__import__.enterprise_bulk_job_a,批量验收岗位甲映射\n__import__.enterprise_bulk_job_b,批量验收岗位乙映射\n`);
  assert.deepEqual(mapped.mapping, ['id', 'name']);
  assert.deepEqual([...mapped.ids].sort(), [...first.ids].sort());
  report.cases.push({ name: 'native_field_tree_manual_mapping', status: 'passed', ids: mapped.ids }); save();
  const commits = report.imports.filter(row => row.dry_run === false).length;
  await upload('invalid-jobs.csv', 'name,description\n预检不得写入岗位,valid row\n,missing required name\n', 'invalid');
  assert.equal(report.imports.filter(row => row.dry_run === false).length, commits);
  report.cases.push({ name: 'invalid_required_row_rejected_before_commit', status: 'passed' }); save();
  await upload('cancel-jobs.csv', 'name\n取消不得写入岗位\n', 'cancel');
  assert.equal(report.imports.filter(row => row.dry_run === false).length, commits);
  report.cases.push({ name: 'cancel_preview_without_commit', status: 'passed' });
  const retried = await upload('retry-invalid.csv', 'name,description\n预检不得写入岗位,valid row\n,missing required name\n', 'retry');
  assert.deepEqual([...retried.ids].sort(), [...first.ids].sort());
  report.cases.push({ name: 'replace_invalid_file_and_retry_in_same_wizard', status: 'passed' }); save();
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.getByRole('button', { name: '批量导入', exact: true }).waitFor({ timeout: 45000 });
  const text = await page.locator('body').innerText();
  assert.ok(!text.includes('预检不得写入岗位') && !text.includes('取消不得写入岗位'));
  await page.goto(`${BASE}/s/enterprise.setup`, { waitUntil: 'domcontentloaded' });
  await page.locator('button.handling-item[data-action-xmlid]').filter({ hasText: '组织架构' }).click();
  await page.getByRole('button', { name: '批量导入', exact: true }).waitFor({ timeout: 45000 });
  const departments = await upload('related-departments.csv',
    'id,name,parent_id/id\n__import__.enterprise_bulk_department_a,批量验收部门甲,hr.dep_administration\n__import__.enterprise_bulk_department_b,批量验收部门乙,hr.dep_administration\n');
  assert.deepEqual(departments.mapping, ['id', 'name', 'parent_id/id']);
  for (const name of ['批量验收部门甲', '批量验收部门乙']) {
    await page.getByText(name, { exact: true }).and(page.locator(':visible')).first().waitFor({ timeout: 30000 });
  }
  report.cases.push({ name: 'department_import_with_native_external_relation', status: 'passed', ids: departments.ids }); save();
  await page.goto(`${BASE}/s/enterprise.setup`, { waitUntil: 'domcontentloaded' });
  await page.locator('button.handling-item[data-action-xmlid]').filter({ hasText: '人员与账号' }).click();
  await page.getByRole('button', { name: '批量导入', exact: true }).waitFor({ timeout: 45000 });
  // Password remains only in process memory and the transport, never evidence.
  const passwordCell = `"${process.env.FRESH_DB_PASSWORD.replaceAll('"', '""')}"`;
  const people = await upload('related-personnel.csv',
    'id,name,login,password,sc_personnel_department_id/id,sc_personnel_job_id/id,sc_personnel_active\n'
    + `__import__.enterprise_bulk_person_a,批量验收人员甲,enterprise_bulk_person_a,${passwordCell},__import__.enterprise_bulk_department_a,__import__.enterprise_bulk_job_a,True\n`
    + `__import__.enterprise_bulk_person_b,批量验收人员乙,enterprise_bulk_person_b,${passwordCell},__import__.enterprise_bulk_department_b,__import__.enterprise_bulk_job_b,True\n`);
  assert.equal(people.ids.length, 2);
  for (const name of ['批量验收人员甲', '批量验收人员乙']) {
    await page.getByText(name, { exact: true }).and(page.locator(':visible')).first().waitFor({ timeout: 30000 });
  }
  report.cases.push({ name: 'personnel_import_with_department_and_job', status: 'passed', ids: people.ids }); save();
  }
  await page.goto(`${BASE}/s/enterprise.setup`, { waitUntil: 'domcontentloaded' });
  await page.locator('button.handling-item[data-action-xmlid]').filter({ hasText: '人员与账号' }).click();
  await page.getByRole('button', { name: '批量导入', exact: true }).waitFor({ timeout: 45000 });
  if (scope === 'configuration') {
    const reference = JSON.parse(fs.readFileSync(path.join(OUT, 'reference.json'), 'utf8'));
    const progress = JSON.parse(fs.readFileSync(path.join(OUT, 'configuration-progress.json'), 'utf8'));
    const accounts = progress.stages['res.users'].records;
    const identities = await exportUpdateIdentities();
    const batches = new Map();
    for (const account of accounts) {
      const source = reference.records.find(row => row.xmlid === account.xmlid);
      const roles = [...source.fields.groups_id.eval.matchAll(/ref\(['"]([^'"]+)['"]\)/g)]
        .map(match => match[1]).filter(ref => ref.includes('.group_sc_role_'));
      assert.ok(roles.length);
      const matches = identities.filter(row => row[1] === account.name);
      assert.equal(matches.length, 1, `exported identity must be unambiguous: ${account.name}`);
      const optional = ['lang', 'tz'].filter(field => source.fields[field]?.text);
      const header = ['id', 'sc_user_role_group_ids/id', ...optional].join(',');
      if (!batches.has(header)) batches.set(header, { lines: [header], ids: [] });
      const batch = batches.get(header);
      batch.lines.push([matches[0][0], `"${roles.join(',')}"`, ...optional.map(field => source.fields[field].text)].join(','));
      batch.ids.push(account.id);
    }
    assert.equal(accounts.length, 21);
    for (const [index, batch] of [...batches.values()].entries()) {
      const result = await upload(`enterprise-business-roles-${index}.csv`, batch.lines.join('\n') + '\n', 'confirm', batch.ids);
      report.cases.push({ name: 'formal_business_role_configuration_import', status: 'passed', ids: result.ids }); save();
    }
  } else {
  const authorized = await upload('business-role-assignment.csv',
    'id,sc_user_role_group_ids/id\n__import__.enterprise_bulk_person_a,smart_construction_core.group_sc_role_project_manager\n__import__.enterprise_bulk_person_b,smart_construction_core.group_sc_role_project_manager\n');
  assert.deepEqual(authorized.mapping, ['id', 'sc_user_role_group_ids/id']);
  report.cases.push({ name: 'imported_people_business_role_assignment', status: 'passed', ids: authorized.ids }); save();
  const priorWrites = report.imports.filter(row => row.dry_run === false).length;
  await upload('forbidden-role-assignment.csv',
    'id,sc_user_role_group_ids/id\n__import__.enterprise_bulk_person_a,base.group_system\n__import__.enterprise_bulk_person_b,base.group_system\n', 'forbidden');
  assert.equal(report.imports.filter(row => row.dry_run === false).length, priorWrites);
  report.cases.push({ name: 'platform_role_import_rejected_for_business_admin', status: 'passed' }); save();
  }
  report.status = 'passed_scoped';
  report.remaining = ['imported_people_role_closure_readback', 'representative_business_journey'];
} catch (error) {
  report.status = 'failed'; report.errors.push(error.stack || error.message);
  await page.screenshot({ path: path.join(OUT, 'import-failure.png'), fullPage: true }).catch(() => {});
  fs.writeFileSync(path.join(OUT, 'import-failure.txt'), await page.locator('body').innerText().catch(() => ''));
} finally { save(); await browser.close(); }
console.log(`[enterprise-import] ${report.status} cases=${report.cases.length}`);
if (report.status === 'failed') process.exitCode = 1;
