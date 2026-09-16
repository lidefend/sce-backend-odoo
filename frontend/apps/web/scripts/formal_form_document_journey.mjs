import assert from 'node:assert/strict';
import path from 'node:path';
import fs from 'node:fs/promises';

// Bounded UC3 observations, called by the existing governed form loop.
// No record writes; the configuration lifecycle remains in the shared designer journey.
export async function checkDocumentDefaults({ page, entry, outside, contract, out, report }) {
  const base = process.env.BASE_URL;
  report.stages.defaults = [];
  const prior = process.env.FORM_LOWCODE_DOCUMENT_RESUME === '1'
    ? JSON.parse(await fs.readFile(path.join(out, 'document-prior-report.json'), 'utf8')) : null;
  if (prior) {
    assert.equal(prior.candidate, report.candidate);
    assert.equal(prior.scope.compiler_sha256, report.scope.compiler_sha256);
    assert.deepEqual(prior.scope.entries.map((e) => e.business_fingerprint), report.scope.entries.map((e) => e.business_fingerprint));
  }
  for (const surface of [entry, outside]) {
    const certificate = surface.action_id === 666;
    const expected = certificate ? '证照名称' : '制度名称';
    const baseline = await contract(surface);
    const source = baseline.formStructureContract.sourceAuthority.governance_source;
    assert.deepEqual(source.compatibilityDependencies || [], []);
    assert.deepEqual(source.configuredSections || [], []);
    assert.equal(source.resolvedActionId, surface.action_id);
    assert.equal(source.resolvedViewId, surface.view_id);
    assert(JSON.stringify(baseline.layoutContract).includes('data-sc-anchor'), 'runtime native view is stale: section anchors missing');
    await fs.writeFile(path.join(out, `contract-${surface.action_id}.json`), JSON.stringify(baseline, null, 2));
    // Visit the actual formal action collection before its create/record routes.
    await page.goto(`${base}/a/${surface.action_id}?menu_id=${surface.menu_id}`, { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle');
    assert(!page.url().includes('/login'));
    const listText = await page.locator('body').innerText();
    assert(!/无权访问|没有访问权限|加载失败/.test(listText), listText.slice(-2000));
    await page.screenshot({ path: path.join(out, `entry-${surface.action_id}.png`), fullPage: true });
    const cases = [{ id: 'new', state: 'create', width: certificate ? 1440 : 390 }];
    if (surface.samples?.length) cases.push({ id: surface.samples[0].id, state: 'readonly', width: certificate ? 390 : 1440 });
    else report.stages.defaults.push({ action: surface.action_id, state: 'readonly', status: 'not_run_no_sample' });
    for (const sample of cases) {
      const carried = prior?.stages.defaults?.find((row) => row.action === surface.action_id && row.record === sample.id && row.status === 'passed');
      if (carried) {
        assert.deepEqual(carried.source, source);
        report.stages.defaults.push({ ...carried, carried_from: 'document-prior-report.json; unchanged product/runtime inputs, observer-only correction' });
        continue;
      }
      await page.setViewportSize({ width: sample.width, height: sample.width === 390 ? 844 : 960 });
      await page.goto(`${base}/f/${surface.model}/${sample.id}?action_id=${surface.action_id}&menu_id=${surface.menu_id}`, { waitUntil: 'domcontentloaded' });
      await page.locator(`[data-field-name="${certificate ? 'certificate_name' : 'document_title'}"]`).filter({ visible: true }).first().waitFor();
      const nav = page.locator('[data-form-section-navigation]');
      const labels = await nav.locator('button').allTextContents();
      assert(!labels.some((label) => /借阅申请|公司资料存档/.test(label)), JSON.stringify(labels));
      await page.evaluate(() => { window.scrollTo(0, 0); for (const node of document.querySelectorAll('*')) if (node.scrollTop) node.scrollTop = 0; });
      const scroll = await page.evaluate(() => [...document.querySelectorAll('*')].filter((node) => node.scrollTop > 0).map((node) => ({ tag: node.tagName, top: node.scrollTop })));
      await page.screenshot({ path: path.join(out, `default-${surface.action_id}-${sample.state}.png`), fullPage: false });
      await page.locator('[data-section-tab="说明"]').last().click();
      if (sample.id === 'new') {
        const input = page.locator('[data-field-name="description"]').locator('textarea,input').filter({ visible: true }).first();
        await input.fill('UC3 临时页签切换观察，不保存');
        await page.locator('[data-section-tab="附件"]').last().click();
        await page.locator('[data-section-tab="说明"]').last().click();
        await page.locator('[data-section-tab="说明"].native-tab--active').waitFor();
        assert.equal(await input.inputValue(), 'UC3 临时页签切换观察，不保存');
        await input.fill('');
      }
      const existing = surface.samples?.find((row) => row.id === sample.id);
      const sourceFields = ['legacy_document_no', 'legacy_document_state', 'legacy_source_table', 'legacy_source_id'];
      const sourceAvailable = existing && sourceFields.some((name) => existing[name]);
      if (sample.id === 'new' || sourceAvailable) {
        await nav.getByRole('button', { name: '来源追溯', exact: true }).click();
        await page.locator('[data-field-name="legacy_source_id"]').filter({ visible: true }).first().waitFor();
      } else {
        // Native readonly presentation omits empty facts; do not invent source data.
        assert.equal(await page.getByText('来源追溯', { exact: true }).filter({ visible: true }).count(), 0);
      }
      await page.screenshot({ path: path.join(out, `source-${surface.action_id}-${sample.state}.png`), fullPage: false });
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'horizontal overflow');
      report.stages.defaults.push({ action: surface.action_id, record: sample.id, state: sample.state, viewport: sample.width,
        source, source_data: sourceAvailable ? 'present' : 'no_legacy_values_in_sample', navigation: labels, top_scroll: scroll, status: 'passed', url: page.url() });
    }
  }
  await page.setViewportSize({ width: 1440, height: 960 });
}

export async function checkEmptyDocumentSource({ page, entry, out, report }) {
  const sample = entry.samples.find((row) => !['legacy_document_no', 'legacy_document_state', 'legacy_source_table', 'legacy_source_id'].some((key) => row[key]));
  assert(sample, 'empty source readonly sample required');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${process.env.BASE_URL}/f/${entry.model}/${sample.id}?action_id=${entry.action_id}&menu_id=${entry.menu_id}`, { waitUntil: 'domcontentloaded' });
  await page.locator('[data-field-name="certificate_name"]').filter({ visible: true }).first().waitFor();
  assert.equal(await page.getByText('来源追溯', { exact: true }).filter({ visible: true }).count(), 0, 'empty source title/nav must both disappear');
  const navigation = await page.locator('[data-form-section-navigation] button').allTextContents();
  assert(!navigation.some((text) => text.includes('来源追溯')));
  await page.evaluate(() => { window.scrollTo(0, 0); for (const node of document.querySelectorAll('*')) if (node.scrollTop) node.scrollTop = 0; });
  const scroll = await page.evaluate(() => [...document.querySelectorAll('*')].filter((node) => node.scrollTop > 0).map((node) => ({ tag: node.tagName, top: node.scrollTop })));
  await page.screenshot({ path: path.join(out, 'empty-source-narrow-top.png'), fullPage: false });
  const tabs = [];
  for (const tab of ['说明', '附件']) {
    await page.locator(`[data-section-tab="${tab}"]`).last().click();
    await page.locator(`[data-section-tab="${tab}"].native-tab--active`).waitFor();
    if (tab === '说明') await page.locator('[data-field-name="description"]').filter({ visible: true }).first().waitFor();
    await page.screenshot({ path: path.join(out, `empty-source-narrow-${tab === '说明' ? 'notes' : 'attachments'}.png`), fullPage: false });
    tabs.push(tab);
  }
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'horizontal overflow');
  assert.deepEqual(report.browser_errors, []);
  report.stages.empty_source = { status: 'passed', record: sample.id, viewport: { width: 390, height: 844 }, navigation, retained_tabs: tabs, top_scroll: scroll, url: page.url(), business_writes: 0, configuration_writes: 0 };
}

// Bounded configuration-center diagnosis; no configuration or business writes.
export async function checkConfigurationEntry({ page, scope, intent, out, report }) {
  const verify = process.env.FORM_LOWCODE_CONFIG_VERIFY === '1';
  if (process.env.FORM_LOWCODE_CONFIG_SUMMARY === '1') return checkConfigurationSummary({ page, scope, intent, out, report });
  const requests = [];
  page.on('request', (request) => {
    if (!request.url().includes('/api/v1/intent')) return;
    try { requests.push(request.postDataJSON()?.intent || ''); } catch {}
  });
  const entry = scope.configuration_entry;
  assert.equal(entry.action_id, 737);
  const result = await intent('ui.contract.v2', { op: 'model', model: entry.model, action_id: entry.action_id, menu_id: entry.menu_id, view_type: 'form', render_profile: 'create' }, false);
  await fs.writeFile(path.join(out, 'configuration-form-contract.json'), JSON.stringify(result, null, 2));
  report.stages.entry = { identity: entry, contract_ok: result.ok, routes: [] };
  const routes = process.env.FORM_LOWCODE_CONFIG_RESUME === '1' ? ['/admin/business-config?menu_id=431&action_id=737'] : process.env.FORM_LOWCODE_CONFIG_NEW_ONLY === '1' ? ['/a/737?menu_id=431'] : ['/m/431', '/a/737?menu_id=431', '/f/ui.business.config.contract/new?menu_id=431&action_id=737', '/admin/business-config?menu_id=431&action_id=737'];
  for (const route of routes) {
    await page.goto(`${process.env.BASE_URL}${route}`, { waitUntil: 'networkidle' });
    if (!verify && route.startsWith('/a/') && !page.url().includes('/admin/business-config')) {
      await page.getByRole('button', { name: '新建', exact: true }).waitFor();
      await page.getByRole('button', { name: '新建', exact: true }).click();
      await page.waitForURL(/\/f\/ui.business.config.contract\/new/);
      await page.getByText('页面契约无法渲染', { exact: true }).waitFor();
    }
    if (verify) {
      await page.waitForURL(/\/admin\/business-config/);
      await page.getByRole('button', { name: '返回业务办理', exact: true }).waitFor();
    }
    const text = await page.locator('body').innerText();
    if (verify) assert(!text.includes('PROFESSIONAL_COMPONENT_FIELD_TYPE_MISMATCH'));
    const name = `entry-${report.stages.entry.routes.length}`;
    await page.screenshot({ path: path.join(out, `${name}.png`), fullPage: false });
    report.stages.entry.routes.push({ requested: route, url: page.url(), text: text.slice(0, 14000), errors: [...report.browser_errors], screenshot: `${name}.png` });
  }
  if (verify) {
    await page.getByRole('button', { name: '返回业务办理', exact: true }).click();
    await page.waitForURL((url) => !url.pathname.startsWith('/admin/business-config'));
    report.stages.return = { status: 'passed', url: page.url() };
    const business = scope.entries[0];
    await page.goto(`${process.env.BASE_URL}/f/${business.model}/new?action_id=${business.action_id}&menu_id=${business.menu_id}`, { waitUntil: 'domcontentloaded' });
    await page.getByRole('button', { name: '更多操作', exact: true }).click();
    await page.getByText('表单设置', { exact: true }).last().click();
    await page.locator('[data-bound-form-designer][data-ready="true"]').waitFor();
    assert(new URL(page.url()).pathname === `/f/${business.model}/new`);
    await page.screenshot({ path: path.join(out, 'business-form-settings.png'), fullPage: false });
    report.stages.form_settings = { status: 'passed', url: page.url() };
    assert.deepEqual(report.browser_errors, []);
    assert(!requests.some((name) => /publish|rollback|save|data\.(create|write|unlink)|change_set\.stage/.test(name)), JSON.stringify(requests));
    report.stages.readonly_requests = [...new Set(requests)];
  }
  if (process.env.FORM_LOWCODE_CONFIG_RESUME === '1') {
    const prior = JSON.parse(await fs.readFile(path.join(out, 'routes-passed-observer-rejected.json'), 'utf8'));
    assert.equal(prior.candidate, report.candidate);
    assert.equal(prior.scope.compiler_sha256, report.scope.compiler_sha256);
    assert.deepEqual(prior.scope.entries, report.scope.entries);
    assert.equal(prior.stages.entry.routes.length, 4);
    assert(prior.stages.entry.routes.every((row) => new URL(row.url).pathname === '/admin/business-config' && !row.text.includes('FIELD_TYPE_MISMATCH')));
    report.stages.entry.carried_routes = prior.stages.entry.routes;
    report.stages.entry.carry_reason = 'Routing product inputs unchanged; observer now allows existing owner-scoped draft resume, governed before/after scope verifies no changes';
  }
  report.stages.entry.product_status = verify ? 'passed' : 'diagnostic_only';
}

async function checkConfigurationSummary({ page, scope, intent, out, report }) {
  const responses = [];
  const writes = [];
  page.on('request', (request) => {
    if (!request.url().includes('/api/v1/intent')) return;
    try { const name = request.postDataJSON()?.intent || ''; if (/publish|rollback|save|change_set\.stage/.test(name)) writes.push(name); } catch {}
  });
  const surface = (await intent('ui.business_config.surface.get', {})).data;
  assert(surface.snapshot_summary.source_counts, 'new overview contract missing');
  await page.goto(`${process.env.BASE_URL}/m/431`, { waitUntil: 'domcontentloaded' });
  await page.getByText('请先选择业务页面', { exact: true }).waitFor();
  await page.locator('[data-configuration-overview]').waitFor();
  await page.getByPlaceholder('输入页面名称').waitFor();
  assert.equal(await page.getByRole('group', { name: '配置工作台页面', exact: true }).count(), 0);
  await page.screenshot({ path: path.join(out, 'overview-unselected.png'), fullPage: false });
  const cases = process.env.FORM_LOWCODE_CONFIG_SUMMARY_VISUAL === '1' ? [['证照', 191]] : [['证照', 191], ['制度', 178]];
  for (const [search, expectedId] of cases) {
    await page.getByPlaceholder('输入页面名称').fill(search);
    const row = page.locator('.scan-row').first();
    await row.waitFor();
    await row.click();
    const label = page.locator('.business-config-context__facts dd').nth(2);
    await page.waitForFunction((id) => [...document.querySelectorAll('.business-config-context__facts dd')].some((node) => node.textContent.includes(`#${id} · v`)), expectedId);
    const text = await label.innerText();
    assert(!text.includes('258'));
    assert(text.includes('使用默认配置'));
    responses.push({ search, label: text, url: page.url() });
    const scroll = await page.evaluate(async () => {
      window.scrollTo(0, 0); for (const node of document.querySelectorAll('*')) if (node.scrollTop) node.scrollTop = 0;
      await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      return [...document.querySelectorAll('*')].filter((node) => node.scrollTop > 0).map((node) => ({ tag: node.tagName, top: node.scrollTop }));
    });
    assert.deepEqual(scroll, [], 'configuration summary must be captured at actual top');
    await page.screenshot({ path: path.join(out, `overview-${expectedId}.png`), fullPage: false });
  }
  assert.deepEqual(writes, []);
  assert.deepEqual(report.browser_errors, []);
  report.stages.configuration_summary = { status: 'passed', overview: surface.snapshot_summary, selected_pages: responses, self_selection: 'excluded', writes };
}
