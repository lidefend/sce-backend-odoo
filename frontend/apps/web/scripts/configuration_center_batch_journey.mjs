import assert from 'node:assert/strict';
import path from 'node:path';
import fs from 'node:fs/promises';

// Runs only through local.dev.form_lowcode.browser, with target baseline/restoration checks.
export async function checkConfigurationCenterBatch({ page, scope, intent, out, report }) {
  const base = process.env.BASE_URL;
  const [entry, outside] = scope.entries;
  const results = report.stages.configuration_center = {};
  report.browser_diagnostics = [];
  page.on('console', (event) => { if (event.type() === 'error') report.browser_diagnostics.push(event.text()); });
  page.on('pageerror', (event) => report.browser_diagnostics.push(String(event)));
  page.on('requestfailed', (request) => report.browser_diagnostics.push(`${request.method()} ${new URL(request.url()).pathname}: ${request.failure()?.errorText}`));
  const tokens = new Set();
  const cs = async (op, params = {}, ok = true) => (await intent(`ui.business_config.change_set.${op}`, { role_key: scope.role_key, ...params }, ok)).data;
  const effective = async (target = entry, extra = {}) => (await intent('ui.contract.v2', { op: 'model', model: target.model, action_id: target.action_id, view_id: target.view_id, view_type: 'form', render_profile: 'create', ...extra })).data;
  const normalize = (contract) => ({ layout: contract.layoutContract, policies: contract.statusContract, actions: contract.actionContract });
  const baseline = normalize(await effective());
  const isolated = normalize(await effective(outside));
  const capture = async (name) => {
    await page.evaluate(() => { window.scrollTo(0, 0); for (const node of document.querySelectorAll('*')) if (node.scrollTop) node.scrollTop = 0; });
    await page.screenshot({ path: path.join(out, `batch-${name}.png`), fullPage: false });
  };
  const openWorkbench = async (query = '') => {
    await page.goto(`${base}/admin/business-config?menu_id=431&root_menu_xmlid=smart_construction_core.menu_sc_root${query}`, { waitUntil: 'domcontentloaded' });
    await page.getByPlaceholder('输入页面名称').waitFor();
  };
  async function checkNarrowDesigner() {
    const panel = page.locator('[data-bound-form-designer][data-ready="true"]');
    await page.setViewportSize({ width: 390, height: 844 });
    await panel.scrollIntoViewIfNeeded();
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'designer horizontal overflow');
    await panel.getByLabel('字段显示名称', { exact: true }).fill('窄屏未保存修改');
    await panel.getByRole('button', { name: '应用字段设置', exact: true }).click();
    assert((await panel.locator('[data-bound-change-summary]').innerText()).includes('窄屏未保存修改'));
    await page.screenshot({ path: path.join(out, 'batch-designer-narrow.png'), fullPage: false });
    await page.getByRole('button', { name: '打开更多页面操作', exact: true }).click();
    await page.getByText('返回工作台', { exact: true }).filter({ visible: true }).click();
    await page.getByRole('button', { name: '放弃修改并离开', exact: true }).click();
    await page.getByPlaceholder('输入页面名称').waitFor();
    results.narrow_edit_leave = 'passed: 390px edit, summary, overflow return and discard unsaved';
  }
  try {
    if (process.env.FORM_LOWCODE_CONFIG_BATCH_NARROW_ONLY === '1') {
      const previous = JSON.parse(await fs.readFile(path.join(out, 'batch-lifecycle-passed-narrow-pending.json'), 'utf8'));
      assert.equal(previous.candidate, report.candidate);
      assert(previous.restored && previous.stages.configuration_center.invalid_preview_recovery);
      Object.assign(results, previous.stages.configuration_center);
      results.carried_lifecycle = 'batch-lifecycle-passed-narrow-pending.json; lifecycle completed through rollback/discard; only narrow overflow observer corrected';
      await page.goto(previous.failurePage.url, { waitUntil: 'domcontentloaded' });
      await page.locator('[data-bound-form-designer][data-ready="true"]').waitFor();
      await checkNarrowDesigner();
      results.lifecycle = { save_restore_preview_publish_edit_again_rollback_discard: 'passed', preview_matches_published: true, isolated_action: outside.action_id, baseline_restored: true };
      report.review = { workbench_url: `${base}/m/431`, certificate_designer_url: previous.failurePage.url };
      return;
    }
    if (process.env.FORM_LOWCODE_CONFIG_BATCH_RESOURCE_RECOVERY === '1') {
      results.environment_recovery = [];
      for (const resource of ['/src/pages/ContractFormRoute.vue', '/src/components/professional-fields/PaymentSettlementDetailCollectionControl.vue', '/src/components/template/FormSection.vue']) {
        const response = await page.request.get(`${base}${resource}`, { timeout: 10000 });
        assert.equal(response.status(), 200, `failed development module has not recovered: ${resource}`);
        assert((await response.body()).length > 100, 'empty development module');
        results.environment_recovery.push({ resource, status: response.status() });
      }
      console.log('[configuration-center] failed dynamic modules recovered: HTTP 200, non-empty content');
    }
    if (process.env.FORM_LOWCODE_CONFIG_BATCH_LIFECYCLE_ONLY === '1') {
      const previous = JSON.parse(await fs.readFile(path.join(out, 'batch-directory-passed.json'), 'utf8'));
      assert.equal(previous.candidate, report.candidate);
      assert.deepEqual(previous.scope.entries, scope.entries);
      assert(previous.stages.configuration_center.host_target);
      Object.assign(results, previous.stages.configuration_center);
      results.carried_directory = 'batch-directory-passed.json; formal catalog and routing unchanged; observer field label corrected, lifecycle resumed';
      await openWorkbench(`&model=${entry.model}&action_id=${entry.action_id}&view_id=${entry.view_id}`);
      const draftBefore = await page.locator('[data-business-config-change-set]').innerText();
      await page.locator('.scan-row--selected').click();
      assert.equal(await page.locator('[data-business-config-change-set]').innerText(), draftBefore, 'selecting current target cleared the draft');
      await page.getByRole('button', { name: '配置表单与布局', exact: true }).click();
      await page.locator('[data-bound-form-designer][data-ready="true"]').waitFor();
    } else {
    console.log('[configuration-center] directory and scope checks');
    const catalog = (await intent('ui.business_config.coverage.scan', { business_catalog: true, exclude_configuration_models: true, include_all_root_menu_actions: true, limit: 1000 })).data;
    assert(catalog.items.some((row) => row.action_id === 666));
    assert(catalog.items.some((row) => row.action_id === 862));
    assert(!catalog.items.some((row) => row.model === 'ui.business.config.contract'));
    results.catalog = { count: catalog.items.length, entries: catalog.items.map(({ name, model, action_id, module_label }) => ({ name, model, action_id, module_label })) };
    await openWorkbench();
    await page.getByText('请先选择业务页面', { exact: true }).waitFor();
    assert.equal(await page.getByRole('complementary', { name: '配置检查' }).count(), 0);
    await capture('unselected');
    for (const target of (process.env.FORM_LOWCODE_CONFIG_BATCH_SCOPE_ONLY === '1' ? [catalog.items.find((row) => row.action_id === 546)] : [entry, outside, catalog.items.find((row) => row.action_id === 546)])) {
      assert(target, 'another business model is required');
      const row = catalog.items.find((item) => item.action_id === target.action_id);
      await page.getByPlaceholder('输入页面名称').fill(row.name);
      const choice = page.locator('.scan-row').filter({ hasText: `入口 ${row.action_id}` });
      console.log(`[configuration-center] select ${row.action_id}`);
      const loaded = page.waitForResponse((response) => {
        try { const request = response.request().postDataJSON(); return request?.intent === 'ui.business_config.surface.get' && request?.params?.action_id === row.action_id; } catch { return false; }
      });
      await choice.first().click();
      await loaded;
      await page.waitForURL((url) => url.searchParams.get('action_id') === String(row.action_id));
      await page.getByRole('button', { name: '配置表单与布局', exact: true }).waitFor();
      assert.equal(new URL(page.url()).searchParams.get('action_id'), String(row.action_id));
      await page.waitForFunction(() => !document.querySelector('.loading-state'));
      console.log(`[configuration-center] refresh ${row.action_id}`);
      await page.reload({ waitUntil: 'domcontentloaded' });
      await page.getByRole('button', { name: '配置表单与布局', exact: true }).waitFor();
      assert((await page.locator('.selected-page-overview').innerText()).includes(row.name));
      await capture(`target-${row.action_id}`);
      if (row.action_id === 546) {
        await page.getByRole('button', { name: '配置表单与布局', exact: true }).click();
        await page.locator('[data-bound-form-designer][data-ready="true"]').waitFor();
        assert.equal(new URL(page.url()).searchParams.get('action_id'), '546');
        await page.getByRole('button', { name: '返回工作台', exact: true }).first().click();
        await page.getByPlaceholder('输入页面名称').waitFor();
        assert.equal(new URL(page.url()).searchParams.get('menu_id'), '431');
      }
    }
    if (process.env.FORM_LOWCODE_CONFIG_BATCH_SCOPE_ONLY === '1') { results.material_scope = 'passed'; return; }
    for (const params of [
      { model: entry.model, action_id: 737 },
      { model: 'ui.business.config.contract', action_id: 737 },
      { model: 'res.partner', action_id: entry.action_id },
      { model: entry.model, action_id: entry.action_id, company_id: scope.company_id + 100000 },
      { model: entry.model, action_id: entry.action_id, role_key: 'unavailable_role' },
    ]) {
      const rejected = await intent('ui.business_config.surface.get', { ...params, business_catalog: true }, false);
      assert.equal(rejected.ok, false, 'invalid business target accepted');
    }
    results.scope_rejections = 'passed: technical target, host action as target, mismatched model';
    await openWorkbench(`&model=${entry.model}&action_id=${entry.action_id}&view_id=${entry.view_id}`);
    await page.getByRole('button', { name: '配置表单与布局', exact: true }).click();
    const panel = page.locator('[data-bound-form-designer][data-ready="true"]');
    await panel.waitFor();
    assert.equal(new URL(page.url()).searchParams.get('menu_id'), String(entry.menu_id));
    assert.equal(new URL(page.url()).searchParams.get('config_host_menu_id'), '431');
    results.host_target = { host: 431, target_menu: entry.menu_id, target_action: entry.action_id, url: page.url() };
    }
    const panel = page.locator('[data-bound-form-designer][data-ready="true"]');
    const routedDesignerUrl = page.url();
    // Preserve existing draft 133. A fresh, explicitly named managed draft owns this journey.
    console.log('[configuration-center] lifecycle: scoped managed draft');
    const fresh = await cs('open', { fresh: true, name: '受管配置中心闭环' });
    tokens.add(fresh.token);
    const managedUrl = new URL(routedDesignerUrl); managedUrl.searchParams.set('change_set_token', fresh.token);
    const designerUrl = managedUrl.href;
    await page.goto(designerUrl, { waitUntil: 'domcontentloaded' });
    await panel.waitFor();
    await panel.getByLabel('选择字段', { exact: true }).click();
    await page.getByText(/^发证机构 ·/).last().click();
    await panel.getByLabel('字段显示名称', { exact: true }).fill('配置中心生命周期样板');
    await panel.getByRole('button', { name: '应用字段设置', exact: true }).click();
    await page.getByRole('button', { name: '返回工作台', exact: true }).first().click();
    await page.getByRole('button', { name: '继续编辑', exact: true }).click();
    assert((await panel.locator('[data-bound-change-summary]').innerText()).includes('配置中心生命周期样板'));
    await panel.getByRole('button', { name: '保存配置草稿', exact: true }).click();
    await panel.getByText('配置已保存，尚未发布', { exact: true }).waitFor();
    const diagnosticStart = report.browser_diagnostics.length;
    await page.reload({ waitUntil: 'domcontentloaded' });
    try { await panel.waitFor(); } catch (error) {
      const failedResources = report.browser_diagnostics.slice(diagnosticStart)
        .filter((item) => item.startsWith('GET /') && item.endsWith(': net::ERR_NETWORK_CHANGED'))
        .map((item) => item.slice(4, -': net::ERR_NETWORK_CHANGED'.length));
      if (!failedResources.length) throw error;
      const recovered = [];
      for (const resource of failedResources) {
        const response = await page.request.get(`${base}${resource}`, { timeout: 10000 });
        assert.equal(response.status(), 200);
        assert((await response.body()).length > 0);
        recovered.push(resource);
      }
      results.environment_reload_recovery = { failure: 'ERR_NETWORK_CHANGED', recovered, retry: 'single read-only reload after HTTP 200' };
      await page.reload({ waitUntil: 'domcontentloaded' });
      await panel.waitFor();
    }
    assert((await panel.locator('[data-bound-change-summary]').innerText()).includes('配置中心生命周期样板'));
    await panel.getByRole('button', { name: '验证并预览', exact: true }).click();
    const previewLink = panel.locator('[data-bound-preview-link]');
    await previewLink.waitFor();
    const previewUrl = await previewLink.getAttribute('href');
    const popup = page.waitForEvent('popup');
    await previewLink.click();
    const preview = await popup;
    await preview.locator('[data-configuration-preview]').waitFor();
    await preview.getByText('配置中心生命周期样板', { exact: true }).first().waitFor();
    assert.equal(await preview.getByRole('button', { name: /^(保存草稿|提交)$/ }).count(), 0);
    await preview.setViewportSize({ width: 390, height: 844 });
    await preview.screenshot({ path: path.join(out, 'batch-preview-narrow.png'), fullPage: false });
    const previewToken = new URL(previewUrl, base).searchParams.get('preview_token');
    const expected = normalize(await effective(entry, { preview_token: previewToken, preview_role_key: scope.role_key }));
    await panel.getByRole('button', { name: '发布配置', exact: true }).click();
    await panel.getByText('配置已发布，最终契约核验通过；页面行为仍需复核', { exact: true }).waitFor();
    const published = await cs('get', { change_set_token: fresh.token });
    results.publication = { state: published.state, published_content_verified: published.publish_result.published_content_verified, final_contract_verified: published.publish_result.runtime_verified, browser_preview_verified: true };
    assert.deepEqual(normalize(await effective()), expected, 'preview/published effective contract differs');
    assert.deepEqual(normalize(await effective(outside)), isolated, 'policy entry was changed');
    const revoked = preview;
    await revoked.reload({ waitUntil: 'domcontentloaded' });
    await revoked.locator('[data-configuration-preview-recovery]').waitFor();
    await revoked.locator('[data-configuration-preview-recovery]').getByText('返回设计器', { exact: true }).click();
    await revoked.locator('[data-bound-form-designer][data-ready="true"]').waitFor();
    await revoked.close();
    results.invalid_preview_recovery = 'passed: previously issued token after publication is rejected with return-to-designer';
    await panel.getByRole('button', { name: '再次编辑', exact: true }).click();
    await panel.getByText(/已加载当前配置/).waitFor();
    assert.equal(await panel.getByRole('button', { name: '应用字段设置', exact: true }).isEnabled(), true);
    // Publication mechanics are unchanged; restore through the same managed lifecycle API.
    await cs('rollback', { change_set_token: fresh.token, request_id: `batch-restore-${fresh.token}` });
    tokens.delete(fresh.token);
    assert.deepEqual(normalize(await effective()), baseline, 'rollback did not restore default');
    const discard = await cs('open', { fresh: true, name: '受管配置中心闭环' });
    tokens.add(discard.token);
    await page.goto(designerUrl.replace(fresh.token, discard.token), { waitUntil: 'domcontentloaded' });
    await panel.waitFor();
    await panel.getByLabel('字段显示名称', { exact: true }).fill('将撤销的配置');
    await panel.getByRole('button', { name: '应用字段设置', exact: true }).click();
    await panel.getByRole('button', { name: '保存配置草稿', exact: true }).click();
    await panel.getByText('配置已保存，尚未发布', { exact: true }).waitFor();
    await panel.getByRole('button', { name: '撤销配置草稿', exact: true }).click();
    await panel.getByText('配置草稿已撤销，已恢复当前生效配置', { exact: true }).waitFor();
    assert(!new URL(page.url()).searchParams.has('change_set_token'));
    assert(!(await panel.locator('[data-bound-change-summary]').innerText()).includes('将撤销的配置'));
    tokens.delete(discard.token);
    await checkNarrowDesigner();
    results.lifecycle = { save_restore_preview_publish_edit_again_rollback_discard: 'passed', preview_matches_published: true, isolated_action: outside.action_id, baseline_restored: true };
    report.review = { workbench_url: `${base}/m/431`, certificate_designer_url: designerUrl.split('&change_set_token=')[0] };
  } finally {
    for (const token of tokens) {
      const state = await cs('get', { change_set_token: token });
      if (state.state === 'published') await cs('rollback', { change_set_token: token, request_id: `recover-${token}` });
      else if (!['discarded', 'superseded'].includes(state.state)) await cs('discard', { change_set_token: token });
    }
  }
}
