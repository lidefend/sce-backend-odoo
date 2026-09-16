import assert from 'node:assert/strict';
import path from 'node:path';

export async function runDesignerJourney({ page, entry, baseline, outsideBaseline, outside, contract, effective, out, report, pending, cs, drafts, documentTopic = false, invoiceTopic = false }) {
  const fieldName = documentTopic ? 'issue_authority' : invoiceTopic ? 'invoice_no' : 'keeper_id';
  const hiddenName = documentTopic ? 'result_note' : invoiceTopic ? 'note_display' : 'line_note_summary';
  const configuredLabel = documentTopic ? '配置发证单位' : invoiceTopic ? '受管发票号码' : '设计器保管员';
  const groupLabel = documentTopic ? '配置发证信息' : invoiceTopic ? '受管开票信息' : '设计器保管信息';
  const walk = function* (nodes) { for (const node of nodes || []) { yield node; yield* walk(node.children); } };
  const nodes = [...walk(baseline.layoutContract.containerTree)];
  const keeper = nodes.find((node) => node.type === 'field' && node.name === fieldName);
  const optional = nodes.find((node) => node.type === 'field' && node.name === hiddenName);
  const requests = [];
  let staged;
  const saves = [];
  page.on('request', (request) => {
    if (!new URL(request.url()).pathname.replace(/\/$/, '').endsWith('/api/v1/intent')) return;
    try { const body = request.postDataJSON(); requests.push(body.intent); if (body.intent === 'ui.business_config.change_set.stage') saves.push(body.params); } catch {}
  });
  const base = process.env.BASE_URL;
  await page.goto(`${base}/f/${entry.model}/new?menu_id=${entry.menu_id}&action_id=${entry.action_id}`, { waitUntil: 'domcontentloaded' });
  await page.getByRole('button', { name: '更多操作', exact: true }).click();
  // Enter through the same product action an administrator uses.
  const config = page.getByText('表单设置', { exact: true });
  await config.last().click();
  const panel = page.locator('[data-bound-form-designer]');
  await panel.waitFor({ state: 'visible' });
  await page.locator('[data-bound-form-designer][data-ready="true"]').waitFor();
  async function editSample() {
  await panel.getByLabel('选择字段', { exact: true }).click();
  await page.getByText(new RegExp(`^${keeper.label || keeper.name} ·`)).last().click();
  await panel.getByLabel('字段显示名称', { exact: true }).fill(configuredLabel);
  await panel.getByRole('button', { name: '应用字段设置', exact: true }).click();
  await panel.getByRole('button', { name: '上移字段', exact: true }).click();
  await panel.getByRole('button', { name: '上移字段', exact: true }).click();
  await panel.getByLabel('新分组名称', { exact: true }).fill(groupLabel);
  await panel.getByRole('button', { name: '加入新分组', exact: true }).click();
  await panel.getByLabel('选择字段', { exact: true }).click();
  await page.getByText(new RegExp(`^${optional.label || optional.name} ·`)).last().click();
  await panel.getByLabel('字段显示', { exact: true }).click();
  await page.getByText('隐藏', { exact: true }).last().click();
  await panel.getByRole('button', { name: '应用字段设置', exact: true }).click();
  }
  await editSample();
  const stageResponse = page.waitForResponse((response) => response.request().postDataJSON()?.intent === 'ui.business_config.change_set.stage');
  const openResponse = page.waitForResponse((response) => response.request().postDataJSON()?.intent === 'ui.business_config.change_set.open');
  await panel.getByRole('button', { name: '保存配置草稿', exact: true }).click();
  const opened = await (await openResponse).json();
  assert.equal(opened.ok, true, JSON.stringify(opened.error));
  drafts.add(opened.data.token);
  const stageBody = await (await stageResponse).json();
  assert.equal(stageBody.ok, true, JSON.stringify(stageBody.error));
  staged = stageBody.data;
  drafts.add(staged.token);
  report.change_set_id = staged.id;
  assert.equal(saves.length, 1);
  const patches = saves[0].draft_payload.view_orchestration.views.form.node_patches;
  assert(patches.length >= 3 && patches.every((patch) => patch.target && patch.expected), 'designer did not author stable targets');
  assert.equal(saves[0].action_id, entry.action_id);
  assert.equal(saves[0].view_id, entry.view_id);
  report.authored_patches = patches;
  const previewResponse = page.waitForResponse((response) => response.request().postDataJSON()?.intent === 'ui.business_config.change_set.preview');
  await panel.getByRole('button', { name: '验证并预览', exact: true }).click();
  const previewResult = await (await previewResponse).json();
  assert.equal(previewResult.ok, true, JSON.stringify(previewResult.error));
  await panel.locator('[data-bound-preview-link]').waitFor();
  await page.screenshot({ path: path.join(out, 'designer-draft.png'), fullPage: true });
  const previewPromise = page.waitForEvent('popup');
  await panel.locator('[data-bound-preview-link]').click();
  const preview = await previewPromise;
  await preview.getByText(configuredLabel, { exact: true }).first().waitFor({ state: 'visible' });
  await preview.getByText(configuredLabel, { exact: true }).first().scrollIntoViewIfNeeded();
  await preview.screenshot({ path: path.join(out, 'designer-preview.png'), fullPage: true });
  const previewUrl = new URL(preview.url());
  const previewContract = await contract(entry, { preview_token: previewUrl.searchParams.get('preview_token'), preview_role_key: previewUrl.searchParams.get('preview_role_key') });
  const groupPatch = patches.find((patch) => patch.group);
  const configuredParent = [...walk(previewContract.layoutContract.containerTree)].find((node) => node.nativeLocator === groupPatch.target);
  report.preview_structure = { parent: configuredParent.containerId,
    children: configuredParent.children.map((node) => ({ id: node.containerId, locator: node.nativeLocator, name: node.name })) };
  if (documentTopic) {
    await preview.locator('[data-form-section-navigation]').getByRole('button', { name: '证照信息', exact: true }).click();
    await preview.getByText(configuredLabel, { exact: true }).first().waitFor({ state: 'visible' });
    const boxes = await Promise.all(['certificate_name', 'issue_authority', 'certificate_no'].map((name) =>
      preview.locator(`[data-field-name="${name}"]`).filter({ visible: true }).first().boundingBox()));
    assert(boxes.every(Boolean) && boxes[0].y < boxes[1].y && boxes[1].y < boxes[2].y, 'configured group/field visual sequence differs');
    report.visual_order = { status: 'passed', certificate_name_y: boxes[0].y, issue_authority_y: boxes[1].y, certificate_no_y: boxes[2].y };
  } else if (invoiceTopic) {
    // The configured field moves into a new managed group above the untouched
    // tax fields.  The authored facts to assert are: the renamed field renders
    // inside the new managed group, it sits above the untouched fields, and
    // those untouched neighbours keep their default shared-column row.
    await preview.locator('[data-form-section-navigation]').getByRole('button', { name: '受管开票信息', exact: true }).click();
    await preview.getByText(configuredLabel, { exact: true }).first().waitFor({ state: 'visible' });
    const [noBox, codeBox, typeBox] = await Promise.all(['invoice_no', 'invoice_code', 'invoice_type'].map((name) =>
      preview.locator(`[data-field-name="${name}"]`).filter({ visible: true }).first().boundingBox()));
    assert(noBox && codeBox && typeBox, 'configured managed group did not render its fields');
    assert(noBox.y < codeBox.y, 'configured field did not move above the untouched tax fields');
    assert(Math.abs(codeBox.y - typeBox.y) < 2 && codeBox.x < typeBox.x,
      'untouched tax fields lost their shared-column row');
    report.visual_order = { status: 'passed', invoice_no_y: noBox.y, invoice_code_y: codeBox.y, invoice_type_y: typeBox.y,
      untouched_columns: 'shared' };
  } else {
  const configuredField = await preview.locator('[data-field-name="keeper_id"]').filter({ visible: true }).first().boundingBox();
  const followingField = await preview.locator('[data-field-name="dest_location_id"]').filter({ visible: true }).first().boundingBox();
  assert(configuredField && followingField && configuredField.y < followingField.y, 'rendered field/group sequence differs from final tree');
  const adjacentField = await preview.locator('[data-field-name="warehouse_id"]').filter({ visible: true }).first().boundingBox();
  assert(adjacentField && Math.abs(adjacentField.y - followingField.y) < 2 && adjacentField.x < followingField.x, 'adjacent fields lost their shared columns');
  report.visual_order = { keeper_y: configuredField.y, warehouse_y: adjacentField.y, location_y: followingField.y, status: 'passed' };
  }
  await preview.close();
  const publicationResponse = page.waitForResponse((response) => response.request().postDataJSON()?.intent === 'ui.business_config.change_set.publish');
  await panel.getByRole('button', { name: '发布配置', exact: true }).click();
  const published = await (await publicationResponse).json();
  assert.equal(published.ok, true, JSON.stringify(published.error));
  pending.push(staged.token);
  drafts.delete(staged.token);
  assert.equal(published.data.publish_result.published_content_verified, true);
  assert.equal(published.data.publish_result.runtime_verified, true);
  assert.deepEqual(effective(await contract()), effective(previewContract));
  assert.deepEqual(effective(await contract(outside)), effective(outsideBaseline));
  const businessPromise = page.waitForEvent('popup');
  await panel.getByRole('link', { name: '打开业务页面', exact: true }).click();
  const business = await businessPromise;
  await business.reload({ waitUntil: 'domcontentloaded' });
  await business.getByText(configuredLabel, { exact: true }).first().waitFor({ state: 'visible' });
  if (documentTopic) {
    await business.locator('[data-section-tab="说明"]').last().click();
    assert.equal(await business.locator('[data-field-name="result_note"]').filter({ visible: true }).count(), 0);
    await business.locator('[data-section-tab="附件"]').last().click();
    await business.locator('[data-form-section-navigation]').getByRole('button', { name: '证照信息', exact: true }).click();
  } else if (invoiceTopic) {
    // The hidden field is the readonly note display inside the notes group;
    // the editable note and the managed group must stay usable.
    await business.locator('[data-form-section-navigation]').getByRole('button', { name: '办理说明', exact: true }).click();
    assert.equal(await business.locator('[data-field-name="note_display"]').filter({ visible: true }).count(), 0);
    await business.locator('[data-field-name="note"]').filter({ visible: true }).first().waitFor();
    await business.locator('[data-form-section-navigation]').getByRole('button', { name: '受管开票信息', exact: true }).click();
  } else {
  await business.locator('[data-section-tab="说明与附件"]').last().click();
  assert.equal(await business.getByText('备注', { exact: true }).count(), 0);
  await business.locator('[data-section-tab="来源追溯"]').last().click();
  await business.locator('[data-form-section-navigation]').getByRole('button', { name: '入库明细', exact: true }).click();
  await business.locator('[data-section-tab="入库明细"].native-tab--active').waitFor({ state: 'visible' });
  }
  await business.getByText(configuredLabel, { exact: true }).first().scrollIntoViewIfNeeded();
  await business.screenshot({ path: path.join(out, 'designer-published.png'), fullPage: true });
  report.stages.publication = { published_content: 'passed', final_contract: 'passed', browser: 'passed', isolation: 'passed' };
  await panel.getByRole('button', { name: '回滚本次发布', exact: true }).click();
  await panel.getByText('本次发布已回滚，请刷新业务页面核对', { exact: true }).waitFor();
  pending.splice(pending.indexOf(staged.token), 1);
  assert.deepEqual(effective(await contract()), effective(baseline));
  await business.reload({ waitUntil: 'domcontentloaded' });
  await business.waitForLoadState('networkidle');
  report.rollback_page = { url: business.url(), text: (await business.locator('body').innerText()).slice(0, 8000) };
  await business.screenshot({ path: path.join(out, 'designer-rollback.png'), fullPage: true });
  await business.getByText(keeper.label || keeper.name, { exact: true }).filter({ visible: true }).first().waitFor({ state: 'visible' });
  assert.equal(await business.getByText(configuredLabel, { exact: true }).count(), 0);
  await business.close();
  // Verify same-screen reuse after rollback and leave an unpublished review
  // draft authored by the ordinary designer; the effective baseline stays put.
  await editSample();
  const reviewOpenResponse = page.waitForResponse((response) => response.request().postDataJSON()?.intent === 'ui.business_config.change_set.open');
  const reviewStageResponse = page.waitForResponse((response) => response.request().postDataJSON()?.intent === 'ui.business_config.change_set.stage');
  await panel.getByRole('button', { name: '保存配置草稿', exact: true }).click();
  const reviewOpen = await (await reviewOpenResponse).json();
  assert.equal(reviewOpen.ok, true, JSON.stringify(reviewOpen.error));
  drafts.add(reviewOpen.data.token);
  const reviewStage = await (await reviewStageResponse).json();
  assert.equal(reviewStage.ok, true, JSON.stringify(reviewStage.error));
  const reviewPreviewResponse = page.waitForResponse((response) => response.request().postDataJSON()?.intent === 'ui.business_config.change_set.preview');
  await panel.getByRole('button', { name: '验证并预览', exact: true }).click();
  const reviewPreview = await (await reviewPreviewResponse).json();
  assert.equal(reviewPreview.ok, true, JSON.stringify(reviewPreview.error));
  await panel.locator('[data-bound-preview-link]').waitFor();
  assert.deepEqual(effective(await contract()), effective(baseline));
  report.review = { draft_id: reviewStage.data.id, login: process.env.E2E_LOGIN,
    designer_url: page.url(), preview_url: await panel.locator('[data-bound-preview-link]').getAttribute('href'),
    expires_at: reviewPreview.data.preview.expires_at, published: false, same_screen_reuse: 'passed' };
  await page.goto(`${base}/f/${outside.model}/new?menu_id=${outside.menu_id}&action_id=${outside.action_id}`, { waitUntil: 'domcontentloaded' });
  // The invoice outside scope is 787: its create-profile policy trims the
  // output-business group, so anchor on the always-rendered editable note
  // instead of a section title.
  if (invoiceTopic) {
    await page.locator('[data-field-name="note"]').filter({ visible: true }).first().waitFor();
  } else {
    await page.getByText(documentTopic ? '制度名称' : '出库日期', { exact: true }).filter({ visible: true }).first().waitFor();
  }
  assert.equal(await page.getByText(configuredLabel, { exact: true }).count(), 0);
  await page.screenshot({ path: path.join(out, 'designer-outside-scope.png'), fullPage: true });
  report.stages.outside_page = { action_id: outside.action_id, status: 'passed' };
  drafts.delete(reviewOpen.data.token);
  assert(!requests.some((name) => name === 'ui.form_field_policy.set' || name === 'ui.business_config.lowcode.apply'), 'designer used a second policy writer');
  report.stages.designer = { status: 'passed', publication: 'passed', final_contract: 'passed', browser: 'passed',
    workflow: 'formal action -> designer -> preview -> publish -> refresh -> rollback', source_patches: patches,
    business_url: `${base}/f/${entry.model}/new?menu_id=${entry.menu_id}&action_id=${entry.action_id}` };
  report.restored = true;
  report.ok = true;
}
