import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import { chromium } from 'playwright';

export async function runFormalFormLoop() {
  const scope = JSON.parse(process.env.FORM_LOWCODE_SCOPE || '{}');
  assert.equal(scope.database, 'sc_dev_demo');
  const [entry, outside] = scope.entries;
  assert.equal(entry.action_id, 546);
  assert.equal(outside.action_id, 547);
  const base = process.env.BASE_URL;
  const out = path.resolve('../../../artifacts/lowcode-form-loop/browser');
  await fs.mkdir(out, { recursive: true });
  const report = { candidate: process.env.CANDIDATE_GIT_HEAD, dirty: true, scope, stages: {}, restored: false, ok: false };
  const navigationOnly = process.env.FORM_LOWCODE_NAV_ONLY === '1';
  const observeOnly = process.env.FORM_LOWCODE_PREVIEW_OBSERVE === '1';
  const closureOnly = process.env.FORM_LOWCODE_PREVIEW_CLOSURE === '1' || observeOnly;
  const designerOnly = process.env.FORM_LOWCODE_DESIGNER === '1';
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 960 } });
  const page = await context.newPage();
  report.browser_errors = [];
  context.on('page', (opened) => opened.on('pageerror', (error) => report.browser_errors.push(error.message)));
  page.on('pageerror', (error) => report.browser_errors.push(error.message));
  page.setDefaultTimeout(15000);
  const pending = [];
  const drafts = new Set();
  let baseline;
  const walk = function* (rows) {
    for (const node of rows || []) {
      if (!node || typeof node !== 'object') continue;
      yield node;
      for (const key of ['children', 'tabs', 'pages', 'nodes', 'items']) if (Array.isArray(node[key])) yield* walk(node[key]);
    }
  };
  const tree = (contract) => contract.layoutContract.containerTree;
  const effective = (contract) => ({ layout: contract.layoutContract, policies: contract.statusContract, actions: contract.actionContract });
  async function intent(name, params = {}, ok = true) {
    const response = await page.evaluate(async ({ name, params, db }) => {
      const token = Object.entries(sessionStorage).find(([key]) => key.startsWith('sc_auth_token:'))?.[1];
      const res = await fetch('/api/v1/intent', { method: 'POST', headers: { Authorization: `Bearer ${token || ''}`, 'Content-Type': 'application/json', 'X-Odoo-DB': db }, body: JSON.stringify({ intent: name, params }) });
      return { status: res.status, body: await res.json() };
    }, { name, params, db: scope.database });
    if (ok) assert.equal(response.body.ok, true, `${name}: ${JSON.stringify(response.body.error || response.body.message || response.body)}`);
    return response.body;
  }
  const cs = (name, params = {}, ok = true) => intent(`ui.business_config.change_set.${name}`, { role_key: scope.role_key, ...params }, ok);
  const contract = async (surface = entry, extra = {}) => (await intent('ui.contract.v2', { op: 'model', model: surface.model, action_id: surface.action_id, menu_id: surface.menu_id, view_id: surface.view_id, view_type: 'form', render_profile: 'create', ...extra })).data;
  const url = (extra = {}) => `${base}/f/${entry.model}/new?${new URLSearchParams({ menu_id: String(entry.menu_id), action_id: String(entry.action_id), ...extra })}`;
  async function observe(name, expected, extra = {}) {
    await page.goto(url(extra), { waitUntil: 'domcontentloaded', timeout: 30000 });
    if (expected) await page.getByText(expected, { exact: true }).first().waitFor({ state: 'visible' });
    else await page.getByText('入库日期', { exact: true }).first().waitFor({ state: 'visible' });
    await page.evaluate(() => { window.scrollTo(0, 0); for (const node of document.querySelectorAll('*')) if (node.scrollTop) node.scrollTop = 0; });
    await page.screenshot({ path: path.join(out, `${name}.png`), fullPage: true });
    return { url: page.url(), screenshot: `${name}.png`, text: (await page.locator('body').innerText()).slice(0, 6000) };
  }
  const binding = (node, extra) => ({ target: node.nativeLocator, expected: { type: node.type, name: node.name ?? null, occurrence_index: node.occurrenceIndex }, ...extra });
  async function rollback(token) {
    const result = (await cs('rollback', { change_set_token: token, request_id: `restore-${token}` })).data;
    assert.equal(result.publish_result.runtime_verified, true);
    pending.splice(pending.indexOf(token), 1);
    return result;
  }
  try {
    const health = await page.request.get(`${base}/`, { timeout: 5000 });
    assert(health.ok(), 'frontend health failed');
    await page.goto(`${base}/login`, { waitUntil: 'domcontentloaded', timeout: 15000 });
    const inputs = page.locator('input');
    await inputs.nth(0).fill(process.env.E2E_LOGIN);
    await inputs.nth(1).fill(process.env.E2E_PASSWORD);
    if (await inputs.count() > 2 && await inputs.nth(2).isEnabled()) await inputs.nth(2).fill(scope.database);
    await page.getByRole('button', { name: /^登录$/ }).click();
    await page.waitForURL((target) => !target.pathname.includes('/login'), { timeout: 30000 });
    if (process.env.FORM_LOWCODE_READ_FAILURE === '1') {
      const previous = JSON.parse(await fs.readFile(path.join(out, 'designer-report.json'), 'utf8'));
      const token = new URL(previous.failurePage.url).searchParams.get('change_set_token');
      assert(token, 'no failed designer draft to read');
      const result = (await cs('get', { change_set_token: token })).data;
      console.log(JSON.stringify({ id: result.id, state: result.state, failure: result.failure_message, items: result.items }));
      return;
    }
    baseline = await contract();
    const otherBaseline = await contract(outside);
    await fs.writeFile(path.join(out, 'baseline.json'), JSON.stringify({ entry: baseline, outside: otherBaseline }, null, 2));
    if (!navigationOnly && !designerOnly && !closureOnly) report.stages.default = await observe('default');
    if (observeOnly) {
      const previous = JSON.parse(await fs.readFile(path.join(out, 'closure-report.json'), 'utf8'));
      await page.goto(previous.review.preview_url, { waitUntil: 'domcontentloaded' });
      await page.locator('[data-configuration-preview]').waitFor();
      await page.getByText('设计器保管员', { exact: true }).first().waitFor();
      await page.screenshot({ path: path.join(out, 'closure-preview-desktop.png'), fullPage: true });
      await page.setViewportSize({ width: 390, height: 844 });
      await page.screenshot({ path: path.join(out, 'closure-preview-narrow.png'), fullPage: true });
      await page.locator('[data-section-tab="入库明细"]').last().scrollIntoViewIfNeeded();
      const banner = await page.locator('[data-configuration-preview]').boundingBox();
      assert(banner && banner.y >= 0 && banner.y + banner.height <= 844, 'preview marker is not persistent');
      const unobscured = await page.locator('[data-configuration-preview]').evaluate((node) => {
        const box = node.getBoundingClientRect();
        const hit = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2);
        return node.contains(hit);
      });
      assert(unobscured, 'preview marker is occluded');
      report.banner_after_scroll = { ...banner, unobscured };
      await page.screenshot({ path: path.join(out, 'closure-preview-narrow-scrolled.png'), fullPage: true });
      await page.goto(previous.review.designer_url, { waitUntil: 'domcontentloaded' });
      const summary = page.locator('[data-bound-change-summary]');
      await summary.getByText(/^顺序：/).waitFor();
      await summary.scrollIntoViewIfNeeded();
      await page.screenshot({ path: path.join(out, 'closure-summary-narrow.png'), fullPage: true });
      const bounds = await summary.boundingBox();
      assert(bounds && bounds.x >= 0 && bounds.x + bounds.width <= 391, 'summary overflow');
      report.stages.observation = { persistent_preview_marker: 'passed', narrow_summary: 'passed' };
      report.ok = true; report.restored = true;
    } else if (closureOnly) {
      const previous = JSON.parse(await fs.readFile(path.join(out, 'designer-report.json'), 'utf8'));
      await page.goto(previous.review.designer_url, { waitUntil: 'domcontentloaded' });
      const panel = page.locator('[data-bound-form-designer]');
      await panel.getByRole('button', { name: '验证并预览', exact: true }).waitFor();
      assert.equal(await panel.locator('select').count(), 0, 'native select remains');
      assert.equal(await panel.locator('[data-semantic-component="ScSelect"]').count(), 2);
      const summary = panel.locator('[data-bound-change-summary]');
      for (const text of ['标签：', '顺序：', '分组：', '显隐：']) await summary.getByText(new RegExp(text)).waitFor();
      // Exercise the actual design-system selector without saving changes.
      await panel.getByLabel('字段显示', { exact: true }).click();
      await page.getByText('保持原规则', { exact: true }).last().click();
      await panel.getByRole('heading', { name: '当前页面字段配置' }).click();
      await page.screenshot({ path: path.join(out, 'closure-designer-desktop.png'), fullPage: true });
      await panel.getByRole('button', { name: '验证并预览', exact: true }).click();
      await panel.locator('[data-bound-preview-link]').waitFor();
      const popup = page.waitForEvent('popup');
      await panel.locator('[data-bound-preview-link]').click();
      const preview = await popup;
      await preview.locator('[data-configuration-preview]').waitFor();
      try { await preview.getByText('设计器保管员', { exact: true }).first().waitFor(); } catch (error) { report.preview_failure = await preview.locator('body').innerText(); throw error; }
      for (const text of ['保存草稿', '提交', '上传附件']) assert.equal(await preview.getByRole('button', { name: text, exact: true }).filter({ visible: true }).count(), 0, text);
      await preview.getByRole('link', { name: '返回设计器', exact: true }).waitFor();
      const blocked = await preview.evaluate(async () => {
        const { intentRequest } = await import('/src/api/intents.ts');
        try { await intentRequest({ intent: 'api.data', params: { model: 'sc.material.inbound', op: 'create', values: { __preview_invalid_field__: true } } }); return 'unexpected_success'; }
        catch (error) { return `${error.reasonCode}: ${error.message}`; }
      });
      assert(blocked.includes('CONFIG_PREVIEW_READ_ONLY'), blocked);
      await preview.screenshot({ path: path.join(out, 'closure-preview-desktop.png'), fullPage: true });
      await page.setViewportSize({ width: 390, height: 844 });
      await preview.setViewportSize({ width: 390, height: 844 });
      await page.screenshot({ path: path.join(out, 'closure-designer-narrow.png'), fullPage: true });
      await preview.screenshot({ path: path.join(out, 'closure-preview-narrow.png'), fullPage: true });
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'designer horizontal overflow');
      assert(await preview.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'preview horizontal overflow');
      report.review = { designer_url: page.url(), preview_url: preview.url(), login: scope.login };
      await preview.getByRole('link', { name: '返回设计器', exact: true }).click();
      await preview.locator('[data-bound-form-designer]').waitFor();
      assert(!new URL(preview.url()).searchParams.has('preview_token'));
      assert(new URL(preview.url()).searchParams.get('change_set_token'));
      assert.deepEqual(effective(await contract()), effective(baseline));
      assert.deepEqual(effective(await contract(outside)), effective(otherBaseline));
      report.stages.closure = { preview_readonly: 'passed', write_rejected: blocked, designer_components: 'passed', summary: 'passed', desktop: 'passed', narrow: 'passed', return_to_designer: 'passed' };
      report.ok = true; report.restored = true;
    } else if (designerOnly) {
      const { runDesignerJourney } = await import('./formal_form_designer_journey.mjs');
      await runDesignerJourney({ page, entry, baseline, outsideBaseline: otherBaseline, outside, contract, effective, out, report, pending, cs, drafts });
    } else {
    const nodes = [...walk(tree(baseline))];
    const field = nodes.find((node) => node.type === 'field' && node.name === 'keeper_id');
    const hidden = nodes.find((node) => node.type === 'field' && node.name === 'line_note_summary');
    const parent = nodes.find((node) => node.children?.includes(field));
    assert(field?.nativeLocator && hidden?.nativeLocator && parent?.nativeLocator, 'missing authoritative node bindings');
    const key = `view_orchestration:formal_material_loop:${Date.now()}`;
    async function stage(patches, targetKey = key) {
      let opened = (await cs('open', { name: '正式表单受管配置验证' })).data;
      assert(opened.name === '正式表单受管配置验证' && opened.items.every((item) => item.target_key.startsWith('view_orchestration:formal_material_loop:')),
        'an unrelated administrator draft is active; preserve it');
      if (opened.items.length) {
        await cs('discard', { change_set_token: opened.token });
        opened = (await cs('open', { name: '正式表单受管配置验证' })).data;
      }
      drafts.add(opened.token);
      await cs('stage', { change_set_token: opened.token, config_type: 'form', target_key: targetKey,
        model: entry.model, view_type: 'form', action_id: entry.action_id, view_id: entry.view_id,
        draft_payload: { view_orchestration: { views: { form: { node_patches: patches } } } } });
      return opened;
    }
    async function publish(label) {
      const opened = await stage([
        binding(field, { set: { label } }), binding(hidden, { set: { visible: false } }),
        binding(parent, { order: [...parent.children].reverse().map((node) => node.nativeLocator),
          group: { key: 'custody', label: '保管配置', members: [field.nativeLocator] } }),
      ]);
      const preview = (await cs('preview', { change_set_token: opened.token })).data;
      const previewParams = { preview_token: preview.preview.token, preview_role_key: scope.role_key };
      const previewContract = await contract(entry, previewParams);
      report.stages[`preview-${label}`] = await observe(`preview-${label}`, label, previewParams);
      const published = (await cs('publish', { change_set_token: opened.token, request_id: `publish-${opened.token}` })).data;
      pending.push(opened.token);
      drafts.delete(opened.token);
      assert.equal(published.publish_result.published_content_verified, true);
      assert.equal(published.publish_result.runtime_verified, true);
      assert.equal(published.publish_result.page_behavior_verification, 'not_run');
      const final = await contract();
      assert.deepEqual(effective(final), effective(previewContract), 'preview and published effective contract differ');
      assert.deepEqual(effective(await contract(outside)), effective(otherBaseline), 'configuration leaked to action 547');
      const observation = await observe(`published-${label}`, label);
      report.stages[label] = { publication: 'passed', final_contract: 'passed', browser: 'passed', ...observation };
      return { opened, final };
    }
    if (navigationOnly) {
      const opened = await stage([
        binding(field, { set: { label: '保管员 A' } }), binding(hidden, { set: { visible: false } }),
        binding(parent, { order: [...parent.children].reverse().map((node) => node.nativeLocator),
          group: { key: 'custody', label: '保管配置', members: [field.nativeLocator] } }),
      ]);
      const preview = (await cs('preview', { change_set_token: opened.token })).data;
      const previewParams = { preview_token: preview.preview.token, preview_role_key: scope.role_key };
      report.stages.preview = await observe('navigation-preview', '保管员 A', previewParams);
      const nav = page.locator('[data-form-section-navigation]');
      await nav.getByRole('button', { name: '保管配置', exact: true }).click();
      await page.getByText('保管员 A', { exact: true }).first().scrollIntoViewIfNeeded();
      await page.screenshot({ path: path.join(out, 'configured-field.png'), fullPage: true });
      await page.locator('[data-section-tab="说明与附件"]').last().click();
      assert.equal(await page.getByText('备注', { exact: true }).count(), 0, 'hidden optional field remained visible');
      await page.locator('[data-section-tab="来源追溯"]').last().click();
      await nav.getByRole('button', { name: '入库明细', exact: true }).click();
      await page.locator('[data-section-tab="入库明细"].native-tab--active').waitFor({ state: 'visible' });
      await page.getByText('添加入库明细', { exact: true }).waitFor({ state: 'visible' });
      await page.screenshot({ path: path.join(out, 'configured-detail-navigation.png'), fullPage: true });
      report.stages.navigation = { status: 'passed', labels: await nav.locator('[data-section-link]').allTextContents(),
        scroll: await page.evaluate(() => [...document.querySelectorAll('*')].filter((node) => node.scrollTop > 0)
          .map((node) => ({ tag: node.tagName, class: node.className, scrollTop: node.scrollTop }))) };
      assert.deepEqual(effective(await contract()), effective(baseline), 'preview changed published baseline');
      assert.deepEqual(effective(await contract(outside)), effective(otherBaseline), 'preview changed outside scope');
      report.review = { url: url(previewParams), expires_at: preview.preview.expires_at, account: scope.login,
        state: 'saved preview only; published baseline restored', change_set_id: opened.id };
      drafts.delete(opened.token); // Preserve only this expiring, creator-scoped preview for product review.
      report.restored = true;
      report.ok = true;
    } else {
    const a = await publish('保管员 A');
    const b = await publish('保管员 B');
    await rollback(b.opened.token);
    assert.deepEqual(effective(await contract()), effective(a.final), 'rollback B did not restore A');
    report.stages.rollbackA = await observe('rollback-A', '保管员 A');
    const readonly = nodes.find((node) => node.name === 'amount_total');
    const required = nodes.find((node) => node.name === 'project_id');
    report.rejections = {};
    for (const [name, patch, reason] of [
      ['readonly', binding(readonly, { set: { readonly: false } }), 'CONFIG_BUSINESS_CONSTRAINT_RELAXED'],
      ['required', binding(required, { set: { visible: false } }), 'CONFIG_REQUIRED_FIELD_HIDDEN'],
      ['stale', { ...binding(field, { set: { label: '失效目标' } }), target: '/removed/node' }, 'CONFIG_TARGET_STALE'],
    ]) {
      const opened = await stage([patch]);
      const rejected = await cs('preview', { change_set_token: opened.token }, false);
      assert.equal(rejected.ok, false, `${name} should be rejected`);
      assert(JSON.stringify(rejected).includes(reason), `${name} missing explicit diagnostic`);
      report.rejections[name] = reason;
      await cs('discard', { change_set_token: opened.token });
      drafts.delete(opened.token);
    }
    const conflict = await stage([binding(field, { set: { label: '同级冲突' } })], `${key}:conflict`);
    const rejected = await cs('preview', { change_set_token: conflict.token }, false);
    assert.equal(rejected.ok, false);
    assert(JSON.stringify(rejected).includes('CONFIG_SAME_PRIORITY_CONFLICT'));
    report.rejections.conflict = 'CONFIG_SAME_PRIORITY_CONFLICT';
    await cs('discard', { change_set_token: conflict.token });
    drafts.delete(conflict.token);
    await rollback(a.opened.token);
    assert.deepEqual(effective(await contract()), effective(baseline), 'baseline restoration failed');
    report.stages.restoredDefault = await observe('restored-default');
    report.restored = true;
    report.ok = true;
    }
    }
  } catch (error) {
    report.failure = error.stack || String(error);
    report.failurePage = { url: page.url(), text: (await page.locator('body').innerText().catch(() => '')).slice(0, 8000) };
    await page.screenshot({ path: path.join(out, 'failure.png'), fullPage: true }).catch(() => {});
  } finally {
    report.recovery = [];
    for (const token of drafts) {
      try { await cs('discard', { change_set_token: token }); }
      catch (error) { report.recovery.push({ status: 'draft_discard_failed', error: String(error) }); }
    }
    for (const token of [...pending].reverse()) {
      try { await rollback(token); report.recovery.push({ status: 'restored' }); }
      catch (error) { report.recovery.push({ status: 'failed', error: String(error) }); }
    }
    if (baseline && !report.restored) {
      try { assert.deepEqual(effective(await contract()), effective(baseline)); report.restored = true; }
      catch (error) { report.recovery.push({ status: 'baseline_readback_failed', error: String(error) }); }
    }
    if (process.env.FORM_LOWCODE_READ_FAILURE !== '1') await fs.writeFile(path.join(out, observeOnly ? 'closure-observation.json' : closureOnly ? 'closure-report.json' : designerOnly ? 'designer-report.json' : navigationOnly ? 'navigation-report.json' : 'report.json'), JSON.stringify(report, null, 2));
    await browser.close();
  }
  assert(report.ok && report.restored, report.failure || 'journey/restoration incomplete');
  console.log(closureOnly ? '[formal_form_lowcode_loop] PASS preview/designer closure; no publication' : designerOnly ? '[formal_form_lowcode_loop] PASS formal designer journey' : navigationOnly ? '[formal_form_lowcode_loop] PASS configured navigation; published baseline unchanged' : '[formal_form_lowcode_loop] PASS default -> preview -> A -> B -> A -> default');
}
