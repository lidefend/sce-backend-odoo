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
