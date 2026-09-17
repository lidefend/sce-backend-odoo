import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {
  isDraftOperationAllowed,
  resolveChangeSetOpenResponse,
  resolveDesignerDraftOwnership,
  resolvePreexistingDraftProbe,
  resolvePreWriteDraftGate,
  resolveResumedDraftDecision,
} from './designer_draft_ownership.mjs';
import { resolvePopupReadiness } from './designer_popup_readiness.mjs';

export async function runDesignerJourney({ page, entry, baseline, outsideBaseline, outside, contract, effective, out, report, pending, cs, drafts, draftPolicy, documentTopic = false, invoiceTopic = false }) {
  const fieldName = documentTopic ? 'issue_authority' : invoiceTopic ? 'invoice_no' : 'keeper_id';
  const hiddenName = documentTopic ? 'result_note' : invoiceTopic ? 'invoice_flow_label' : 'line_note_summary';
  const configuredLabel = documentTopic ? '配置发证单位' : invoiceTopic ? '受管发票号码' : '设计器保管员';
  const groupLabel = documentTopic ? '配置发证信息' : invoiceTopic ? '受管开票信息' : '设计器保管信息';
  const walk = function* (nodes) { for (const node of nodes || []) { yield node; yield* walk(node.children); } };
  const nodes = [...walk(baseline.layoutContract.containerTree)];
  const keeper = nodes.find((node) => node.type === 'field' && node.name === fieldName);
  const optional = nodes.find((node) => node.type === 'field' && node.name === hiddenName);
  const requests = [];
  let staged;
  const saves = [];
  const openResponses = [];
  page.on('response', (response) => {
    try {
      if (response.request().postDataJSON()?.intent === 'ui.business_config.change_set.open') openResponses.push(response);
    } catch {}
  });
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
  // The product resolves a resumable draft with its own scope rule. Ask it read-only
  // (`resume_only` never creates) under both rules it accepts, so a draft that appeared
  // after the inventory is refused *before* this run writes anything.
  const roleKey = draftPolicy?.roleKey || '';
  const probeParams = { role_key: roleKey, resume_only: true };
  const scopeProbe = resolveChangeSetOpenResponse({ body: await cs('open', { ...probeParams, target_model: entry.model, target_action_id: entry.action_id }), intent: 'open:probe_scope_rule' });
  const targetProbe = resolveChangeSetOpenResponse({ body: await cs('open', { ...probeParams, target_key: `view_orchestration:${entry.model}:form:action:${entry.action_id}:view:${entry.view_id}:role:${roleKey}` }), intent: 'open:probe_target_key' });
  for (const result of [scopeProbe, targetProbe]) if (result.error) throw new Error(result.error);
  const existingIds = [scopeProbe.draft?.id, targetProbe.draft?.id].filter(Boolean);
  const probe = resolvePreexistingDraftProbe({ existingIds, inventoryIds: draftPolicy?.inventoryIds || [] });
  report.designer_draft_probe = { resumed_by_scope_rule: scopeProbe.draft?.id || null, resumed_by_target_key: targetProbe.draft?.id || null,
    probe_shapes: [scopeProbe.shape, targetProbe.shape], decision: probe.decision, reason: probe.reason };
  if (probe.decision === 'fail_closed') throw new Error(probe.reason);
  // The save stages into whichever draft the product already holds, so the operation has
  // to be authorized *before* the click. Checking afterwards would already have written.
  const preWrite = resolvePreWriteDraftGate({ probedIds: probe.ids, policy: draftPolicy });
  report.designer_pre_write_gate = { decision: preWrite.decision, reason: preWrite.reason, ids: preWrite.ids };
  if (preWrite.decision === 'fail_closed') throw new Error(preWrite.reason);
  const assertDraftOperation = (id, operation) => {
    if (!(draftPolicy?.inventoryIds || []).includes(id)) return;
    if (!isDraftOperationAllowed({ policy: draftPolicy, changeSetId: id, operation })) {
      throw new Error(`draft_operation_not_authorized:${id}:${operation}`);
    }
  };
  const stageResponse = page.waitForResponse((response) => response.request().postDataJSON()?.intent === 'ui.business_config.change_set.stage');
  const intentsBeforeSave = requests.length;
  const opensBeforeSave = openResponses.length;
  await panel.getByRole('button', { name: '保存配置草稿', exact: true }).click();
  const stageBody = await (await stageResponse).json();
  assert.equal(stageBody.ok, true, JSON.stringify(stageBody.error));
  staged = stageBody.data;
  report.change_set_id = staged.id;
  // The product opens a new change set only when the scope has no reusable draft; a
  // resumed draft saves through `stage` alone. The acceptance fact is that the save
  // succeeded and the authored patches were recorded, not which product path ran.
  // Mount-time resume also emits `open`, so only intents sent *after* the click
  // may decide which save path the product took.
  report.save_path = requests.slice(intentsBeforeSave).includes('ui.business_config.change_set.open')
    ? 'opened_new_change_set' : 'resumed_existing_draft';
  // Ownership needs the product's own creation credential: it asked for `fresh` and the
  // handler reports `created`. Being absent from the inventory is a consistency check,
  // not the proof. A resumed draft is never released and must have been probed.
  const saveOpenResponse = openResponses.slice(opensBeforeSave).pop() || null;
  const saveOpenParams = saveOpenResponse ? (() => { try { return saveOpenResponse.request().postDataJSON()?.params || {}; } catch { return {}; } })() : {};
  const saveOpenBody = saveOpenResponse ? await saveOpenResponse.json() : null;
  const saveOpenDraft = saveOpenBody ? resolveChangeSetOpenResponse({ body: saveOpenBody, intent: 'open:save' }) : null;
  if (saveOpenDraft?.error) throw new Error(saveOpenDraft.error);
  if (saveOpenDraft?.draft) assert.equal(saveOpenDraft.draft.id, staged.id, 'save-time open and stage resolved different drafts');
  const ownership = resolveDesignerDraftOwnership({
    changeSetId: staged.id,
    inventoryIds: draftPolicy?.inventoryIds || [],
    created: saveOpenBody?.data?.created === true,
    freshRequested: saveOpenParams.fresh === true,
  });
  report.draft_ownership = ownership;
  report.save_open = { requested_fresh: saveOpenParams.fresh === true, reported_created: saveOpenBody?.data?.created ?? null };
  if (ownership.release) drafts.set(staged.token, staged.id);
  else {
    const resumed = resolveResumedDraftDecision({ changeSetId: staged.id, probedIds: probe.ids, policy: draftPolicy });
    report.resumed_authorized_draft = { id: staged.id, operations: draftPolicy?.allowed?.[staged.id] || [],
      decision: resumed.decision, reason: resumed.reason };
    if (resumed.decision === 'fail_closed') throw new Error(resumed.reason);
    report.preserved_draft = { id: staged.id, reason: ownership.reason };
  }
  assert.equal(saves.length, 1);
  const requestedPatches = saves[0].draft_payload.view_orchestration.views.form.node_patches;
  const savedItem = staged.items.find((item) => item.action_id === entry.action_id && item.view_id === entry.view_id);
  assert(savedItem, 'staged change set does not carry the designed entry');
  const patches = savedItem.draft_payload.view_orchestration.views.form.node_patches;
  assert.deepEqual(patches, requestedPatches, 'persisted draft differs from the authored request');
  assert(patches.length >= 3 && patches.every((patch) => patch.target && patch.expected), 'designer did not author stable targets');
  assert.equal(saves[0].action_id, entry.action_id);
  assert.equal(saves[0].view_id, entry.view_id);
  report.authored_patches = patches;
  assertDraftOperation(staged.id, 'preview');
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
    // `invoice_tax_details` is a flat two-column flow group, so the product opens
    // a resumed draft with its earlier patches already applied.  Where the new
    // managed group lands in that flow, and therefore how the untouched fields
    // re-pair, depends on the authored order of *this* run.  The durable product
    // facts are independent of that: the renamed field renders in its managed
    // group above the untouched fields, the untouched fields keep their native
    // relative order, and the group keeps its shared-column flow instead of
    // collapsing into one field per row.
    await preview.locator('[data-form-section-navigation]').getByRole('button', { name: '受管开票信息', exact: true }).click();
    await preview.getByText(configuredLabel, { exact: true }).first().waitFor({ state: 'visible' });
    const [noBox, codeBox, typeBox] = await Promise.all(['invoice_no', 'invoice_code', 'invoice_type'].map((name) =>
      preview.locator(`[data-field-name="${name}"]`).filter({ visible: true }).first().boundingBox()));
    assert(noBox && codeBox && typeBox, 'configured managed group did not render its fields');
    assert(noBox.y < codeBox.y, 'configured field did not move above the untouched tax fields');
    const precedes = (a, b) => (Math.abs(a.y - b.y) < 2 ? a.x < b.x : a.y < b.y);
    assert(precedes(codeBox, typeBox), 'untouched tax fields lost their native order');
    const rowPeers = ['invoice_state', 'invoice_date', 'recognition_date', 'invoice_code', 'invoice_type', 'tax_rate'];
    const rows = new Map();
    const peers = [];
    for (const peer of rowPeers) {
      const box = await preview.locator(`[data-field-name="${peer}"]`).filter({ visible: true }).first().boundingBox();
      if (!box) continue;
      peers.push(peer);
      rows.set(Math.round(box.y), [...(rows.get(Math.round(box.y)) || []), peer]);
    }
    const shared = [...rows.values()].filter((names) => names.length >= 2);
    assert(peers.length >= 5 && shared.length >= 1,
      `untouched tax group lost its shared-column flow: ${JSON.stringify([...rows.values()])}`);
    report.visual_order = { status: 'passed', invoice_no_y: noBox.y, invoice_code_y: codeBox.y, invoice_type_y: typeBox.y,
      untouched_columns: 'shared', untouched_rows: [...rows.values()], authored_group_order: (patches.find((patch) => patch.group) || {}).order };
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
  assertDraftOperation(staged.id, 'publish');
  await panel.getByRole('button', { name: '发布配置', exact: true }).click();
  const published = await (await publicationResponse).json();
  assert.equal(published.ok, true, JSON.stringify(published.error));
  pending.push(staged.token);
  drafts.delete(staged.token);
  assert.equal(published.data.publish_result.published_content_verified, true);
  assert.equal(published.data.publish_result.runtime_verified, true);
  assert.deepEqual(effective(await contract()), effective(previewContract));
  assert.deepEqual(effective(await contract(outside)), effective(outsideBaseline));
  // The business page arrives as a popup, and asserting the published label right
  // after the reload collapses three different facts into one locator timeout: the
  // popup never finished loading (transport), it landed on a different route/shell
  // than the designer opened, or the label really is absent from a mounted body.
  // Instrument this page from creation and prove the app shell mounted *before* the
  // label assertion, so a break is attributed from the popup's own URL/DOM/signals
  // instead of being inferred from the opener. The label assertion stays strict.
  const popupSignals = new Map();
  const instrumentPopup = (popup) => {
    // A page stuck on its loading state is not the same fact as a page whose request
    // failed: a hung request never reaches `requestfailed`, so failure-only capture
    // cannot tell "transport hang" from "app never asked". Track the intent lifecycle
    // so the break can be read from started/answered/pending instead of guessed.
    const signal = { pageerrors: [], console: [], failed_requests: [], api: [], abandoned: [], inflight: new Map() };
    popupSignals.set(popup, signal);
    popup.on('request', (request) => {
      const path = new URL(request.url()).pathname.replace(/\/$/, '');
      if (!path.endsWith('/api/v1/intent')) return;
      let intent = null;
      try { intent = request.postDataJSON()?.intent || null; } catch {}
      signal.inflight.set(request, { intent, method: request.method(), path, started_at: Date.now() });
    });
    popup.on('response', (response) => {
      const record = signal.inflight.get(response.request());
      if (!record) return;
      signal.inflight.delete(response.request());
      if (signal.api.length < 40) signal.api.push({ ...record, state: 'answered', status: response.status(), elapsed_ms: Date.now() - record.started_at });
    });
    popup.on('pageerror', (error) => signal.pageerrors.push(String(error.message).slice(0, 300)));
    popup.on('console', (message) => {
      if (message.type() === 'error' && signal.console.length < 20) signal.console.push(String(message.text()).slice(0, 300));
    });
    popup.on('requestfailed', (request) => {
      if (signal.failed_requests.length < 20) signal.failed_requests.push({ path: new URL(request.url()).pathname, error: request.failure()?.errorText });
      const record = signal.inflight.get(request);
      if (record) {
        signal.inflight.delete(request);
        if (signal.api.length < 40) signal.api.push({ ...record, state: 'failed', error: request.failure()?.errorText, elapsed_ms: Date.now() - record.started_at });
      }
    });
  };
  const signalSnapshot = (signal) => ({ pageerrors: signal.pageerrors, console: signal.console,
    failed_requests: signal.failed_requests, api: signal.api, api_abandoned: signal.abandoned,
    api_pending: [...signal.inflight.values()].map((record) => ({ ...record, elapsed_ms: Date.now() - record.started_at })) });
  const popupContext = page.context();
  popupContext.on('page', instrumentPopup);
  const businessPromise = page.waitForEvent('popup');
  await panel.getByRole('link', { name: '打开业务页面', exact: true }).click();
  const business = await businessPromise;
  popupContext.off('page', instrumentPopup);
  const businessSignals = popupSignals.get(business) || { pageerrors: [], console: [], failed_requests: [], api: [], abandoned: [], inflight: new Map() };
  const readPopupState = () => business.evaluate(() => {
    const app = document.querySelector('#app');
    return { ready_state: document.readyState, app_mounted: Boolean(app && app.children.length > 0),
      app_shell_children: app ? app.children.length : 0, field_nodes: document.querySelectorAll('[data-field-name]').length,
      loading_title: /加载中/.test(document.title) };
  }).catch(() => null);
  const popupEvidence = async (state) => {
    const url = business.url();
    return { url, path: new URL(url).pathname, route_matches_entry: new URL(url).pathname.includes(`/f/${entry.model}/`),
      ready_state: state?.ready_state || null, app_mounted: Boolean(state && state.app_mounted),
      app_shell_children: state?.app_shell_children ?? 0, field_nodes: state?.field_nodes ?? 0,
      page_title: await business.title().catch(() => null), loading_title: Boolean(state?.loading_title),
      body_text: (await business.locator('body').innerText().catch(() => '')).slice(0, 600),
      signals: signalSnapshot(businessSignals) };
  };
  // The product's popup starts loading its own module graph the moment it opens. Reloading
  // into that window cancels the first document's in-flight requests - the `ERR_ABORTED`
  // module entries in the failure evidence - which is noise this run creates for itself and
  // a second full module fetch on an already interrupted network. Let the first document
  // settle (bounded, never a substitute for the assertion) before the deliberate fresh
  // reload that proves a newly published configuration renders from a cold load.
  await business.waitForLoadState('load', { timeout: 10000 }).catch(() => null);
  // That reload discards the popup's first document, and a request left in flight by it is
  // abandoned by navigation rather than hung. Move those aside at the reload boundary so a
  // later "still pending" reading describes the current document only.
  for (const record of businessSignals.inflight.values()) {
    businessSignals.abandoned.push({ ...record, reason: 'abandoned_by_reload', elapsed_ms: Date.now() - record.started_at });
  }
  businessSignals.inflight.clear();
  await business.reload({ waitUntil: 'domcontentloaded' });
  // Bounded readiness probe (never a longer timeout on the label locator): wait for the
  // shell to mount *and* for the page's own loading title to clear. A page can mount its
  // shell while its record request is still in flight, so shell-only readiness reads the
  // state one render tick early; the probe records that instead of asserting it.
  const readyWaitStart = Date.now();
  let popupState = await readPopupState();
  for (let attempt = 0; attempt < 60 && !(popupState && popupState.app_mounted && !popupState.loading_title); attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 250));
    popupState = await readPopupState();
  }
  report.designer_popup = { ...(await popupEvidence(popupState)), ready_wait_ms: Date.now() - readyWaitStart };
  const readiness = resolvePopupReadiness({ state: popupState, url: report.designer_popup.url, entryModel: entry.model,
    closed: business.isClosed() });
  report.designer_popup.verdict = readiness.verdict;
  report.designer_popup.blocking = readiness.blocking;
  if (readiness.blocking) {
    // Only proven failure states interrupt: a route the product itself marked as
    // login/denied, or a popup it actually closed. A merely slow or not-yet-readable page
    // falls through to the strict assertion below, so this diagnostic can never turn a
    // passing run into a failure.
    const dom = await business.content().catch(() => '');
    await fs.writeFile(path.join(out, 'failure-designer-popup-dom.html'), dom).catch(() => {});
    await business.screenshot({ path: path.join(out, 'failure-designer-popup.png'), fullPage: true }).catch(() => {});
    throw new Error(`designer business popup unusable for the label assertion: verdict=${readiness.verdict} `
      + `url=${business.url()} ready_state=${report.designer_popup.ready_state ?? 'unknown'} `
      + `pageerrors=${JSON.stringify(businessSignals.pageerrors)} failed_requests=${JSON.stringify(businessSignals.failed_requests)} `
      + `api=${JSON.stringify(report.designer_popup.signals.api)} api_pending=${JSON.stringify(report.designer_popup.signals.api_pending)} `
      + `body=${report.designer_popup.body_text.slice(0, 300)}`);
  }
  try {
    await business.getByText(configuredLabel, { exact: true }).first().waitFor({ state: 'visible' });
  } catch (error) {
    // Keep the assertion strict; capture the popup's own state at the moment it failed so
    // the break is attributable to this page rather than to the opener's signals.
    report.designer_popup.verdict = 'popup_label_not_visible';
    report.designer_popup.at_assertion_failure = await popupEvidence(await readPopupState());
    const dom = await business.content().catch(() => '');
    await fs.writeFile(path.join(out, 'failure-designer-popup-dom.html'), dom).catch(() => {});
    await business.screenshot({ path: path.join(out, 'failure-designer-popup.png'), fullPage: true }).catch(() => {});
    throw error;
  }
  if (documentTopic) {
    await business.locator('[data-section-tab="说明"]').last().click();
    assert.equal(await business.locator('[data-field-name="result_note"]').filter({ visible: true }).count(), 0);
    await business.locator('[data-section-tab="附件"]').last().click();
    await business.locator('[data-form-section-navigation]').getByRole('button', { name: '证照信息', exact: true }).click();
  } else if (invoiceTopic) {
    // The hidden target is the readonly flow label of the first section, so the
    // check is meaningful without switching tabs.  The notes section keeps the
    // editable note and the attachment surface as the single presenters.
    assert.equal(await business.locator('[data-field-name="invoice_flow_label"]').filter({ visible: true }).count(), 0,
      'hidden readonly flow label must not render on the business page');
    assert(await business.locator('[data-field-name="invoice_flow_label"]').count() === 0,
      'hidden field must not remain in the business page DOM');
    await business.locator('[data-form-section-navigation]').getByRole('button', { name: '办理说明', exact: true }).click();
    await business.locator('[data-field-name="note"]').filter({ visible: true }).first().waitFor();
    assert.equal(await business.locator('[data-field-name="note_display"]').count(), 0,
      'note must not be presented twice in the form body');
    assert.equal(await business.locator('[data-field-name="invoice_attachment_text"]').count(), 0,
      'attachments must not be presented twice in the form body');
    await business.locator('[data-field-name="attachment_ids"]').first().waitFor();
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
  assertDraftOperation(staged.id, 'rollback');
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
  const reviewOpensBefore = openResponses.length;
  const reviewStageResponse = page.waitForResponse((response) => response.request().postDataJSON()?.intent === 'ui.business_config.change_set.stage');
  await panel.getByRole('button', { name: '保存配置草稿', exact: true }).click();
  const reviewStage = await (await reviewStageResponse).json();
  assert.equal(reviewStage.ok, true, JSON.stringify(reviewStage.error));
  // The product awaits `open` before it stages, so the save-time open response is
  // already recorded once the stage response has arrived.
  const reviewOpenResponse = openResponses.slice(reviewOpensBefore).pop() || null;
  const reviewOpen = reviewOpenResponse ? await reviewOpenResponse.json() : null;
  assert(reviewOpen && reviewOpen.ok === true, `review save did not open a draft: ${JSON.stringify(reviewOpen?.error)}`);
  const reviewFresh = reviewOpenResponse.request().postDataJSON()?.params?.fresh === true;
  const reviewOwnership = resolveDesignerDraftOwnership({
    changeSetId: reviewOpen.data.id,
    inventoryIds: draftPolicy?.inventoryIds || [],
    created: reviewOpen.data.created === true,
    freshRequested: reviewFresh,
  });
  report.review_draft_ownership = reviewOwnership;
  if (reviewOwnership.release) drafts.set(reviewOpen.data.token, reviewOpen.data.id);
  else drafts.delete(reviewOpen.data.token); // never released, never discarded
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
