import { launchChromium } from './playwright_runtime.mjs';

const target = JSON.parse(process.env.LOCAL_DEV_PROJECT_CREATE_SCOPE_JSON || '{}');
const frontendUrl = String(process.env.FRONTEND_URL || '');
const password = String(process.env.E2E_PASSWORD || '');
const database = String(target.database || '');
const login = String(target.login || '');
if (!frontendUrl || !password || !database || !login || !target.action_id || !target.menu_id) {
  throw new Error('local.dev project driver probe identity is incomplete');
}

const browser = await launchChromium({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
const mutations = [];
const executeRequests = [];
const contractActions = [];
const contractPresentations = [];
const browserErrors = [];
const followerUpdates = [];
const followerListResponses = [];
const attachmentMutations = [];
const messageMutations = [];
const activityMutations = [];
const userSearchRequests = [];
const intentFailures = [];
// The collaboration chips render before the backend authorization/enabled
// projection settles, so a single isDisabled() sample races the declared state.
// Wait for the declared enabled state instead of sampling once.
async function expectActionEnabled(locator, label, timeout = 15000) {
  const deadline = Date.now() + timeout;
  let lastDisabled = null;
  for (;;) {
    lastDisabled = await locator.isDisabled().catch(() => null);
    if (lastDisabled === false) return;
    if (Date.now() >= deadline) {
      throw new Error(`${label} is not backend-authorized (disabled=${lastDisabled})`);
    }
    await page.waitForTimeout(200);
  }
}
async function captureHeaderPresentation(surface) {
  const header = surface.locator('.contract-form-command-bar');
  await header.waitFor({ state: 'visible', timeout: 45000 });
  return {
    commandBars: await header.count(),
    scButtons: await header.locator('[data-semantic-component="ScButton"]').count(),
    primaryActions: await header.locator('[data-product-primary-action]:visible:not(:disabled)').count(),
    rawButtons: await header.locator('button:not([data-semantic-component="ScButton"])').count(),
    rawButtonsOutsideWorkflow: await header.locator('button:not([data-semantic-component="ScButton"]):not(.native-statusbar-step)').count(),
    mobileActionKeys: await header.locator('[data-mobile-action-keys]').evaluateAll((nodes) => (
      nodes.flatMap((node) => String(node.getAttribute('data-mobile-action-keys') || '').split(','))
        .map((key) => key.trim()).filter(Boolean)
    )),
    mobileDisclosures: await header.locator('.form-header-mobile-actions[data-mobile-action-count]').count(),
    horizontalOverflow: await header.evaluate((node) => node.scrollWidth > node.clientWidth + 1),
  };
}
// Only an authoritative successful list response counts as live authority; a
// failed or truncated envelope must never be read as "not following".
async function waitForFollowerListResponse(model, recordId, timeout = 15000) {
  const deadline = Date.now() + timeout;
  for (;;) {
    const found = [...followerListResponses].reverse().find((row) => (
      row.model === model && String(row.recordId) === String(recordId)
      && row.ok === true && row.count >= 0
    ));
    if (found) return found;
    if (Date.now() > deadline) return null;
    await page.waitForTimeout(100);
  }
}
async function verifyFollowerMutation(surface, model) {
  // The journey is anchored on the contract declaration (governed intents and
  // action labels) plus the live list authority the product itself consumed.
  // It never trusts a follower snapshot captured before the browser ran, since
  // follow state is per current user and may have moved in between.
  const declared = (target.follower_declaration || []).find((row) => row.model === model);
  if (!declared) throw new Error(`missing follower declaration for ${model}`);
  if (declared.list_intent !== 'chatter.followers.list'
    || declared.update_intent !== 'chatter.followers.update'
    || declared.follow_enabled !== true || declared.unfollow_enabled !== true
    || !declared.follow_label || !declared.unfollow_label
    || declared.follow_label === declared.unfollow_label) {
    throw new Error(`follower declaration is not governed for ${model}: ${JSON.stringify(declared)}`);
  }
  const manager = surface.locator('[data-professional-collaboration-component="followers"]');
  const followButton = manager.getByRole('button', { name: declared.follow_label, exact: true });
  const unfollowButton = manager.getByRole('button', { name: declared.unfollow_label, exact: true });

  // The followers component reports data-state="ready" from the first mount, so
  // the journey must wait for the live list-intent response the product itself
  // consumed before it may judge the offered action.
  const liveList = await waitForFollowerListResponse(model, declared.record_id);
  if (!liveList) {
    throw new Error(`no authoritative live follower list response for ${model}:${declared.record_id}: ${
      JSON.stringify(followerListResponses)}`);
  }
  if (liveList.canFollow === liveList.canUnfollow) {
    throw new Error(`follower list response did not declare a single action for ${model}: ${JSON.stringify(liveList)}`);
  }
  const declaredFollowing = liveList.canUnfollow === true;

  // Exactly one declared action must settle, and it must mirror the live list
  // authority: following <=> unfollow offered, not following <=> follow
  // offered. Neither or both actions offered is a defect.
  const settleDeadline = Date.now() + 15000;
  let followCount = await followButton.count();
  let unfollowCount = await unfollowButton.count();
  while (followCount + unfollowCount !== 1) {
    if (Date.now() > settleDeadline) {
      throw new Error(`follower manager did not declare exactly one action for ${model}: ${JSON.stringify({
        declared,
        liveList,
        followButtons: followCount,
        unfollowButtons: unfollowCount,
        text: String(await manager.textContent() || '').replace(/\s+/g, ' ').trim(),
      })}`);
    }
    await page.waitForTimeout(100);
    followCount = await followButton.count();
    unfollowCount = await unfollowButton.count();
  }
  if (declaredFollowing !== (unfollowCount === 1)) {
    throw new Error(`follower action did not mirror the live list authority for ${model}: ${JSON.stringify({
      liveList, followButtons: followCount, unfollowButtons: unfollowCount,
    })}`);
  }

  const firstAction = declaredFollowing ? 'unfollow' : 'follow';
  const firstLabel = declaredFollowing ? declared.unfollow_label : declared.follow_label;
  const restoreLabel = declaredFollowing ? declared.follow_label : declared.unfollow_label;
  const updatesBefore = followerUpdates.filter((row) => row.model === model).length;

  await manager.getByRole('button', { name: firstLabel, exact: true }).click();
  await manager.getByRole('button', { name: restoreLabel, exact: true })
    .waitFor({ state: 'visible', timeout: 15000 });
  const changedText = String(await manager.textContent() || '').replace(/\s+/g, ' ').trim();
  await manager.getByRole('button', { name: restoreLabel, exact: true }).click();
  await manager.getByRole('button', { name: firstLabel, exact: true })
    .waitFor({ state: 'visible', timeout: 15000 });
  const restoredText = String(await manager.textContent() || '').replace(/\s+/g, ' ').trim();

  // The round-trip must issue exactly the declared update intents, in order, on
  // the declared record.
  const issuedRows = followerUpdates.filter((row) => row.model === model).slice(updatesBefore);
  const issuedActions = issuedRows.map((row) => row.action);
  const expectedActions = [firstAction, firstAction === 'follow' ? 'unfollow' : 'follow'];
  if (issuedRows.length !== 2 || issuedActions.join(',') !== expectedActions.join(',')) {
    throw new Error(`follower journey did not issue the declared intents for ${model}: ${JSON.stringify({
      issuedActions, expectedActions, issuedRows,
    })}`);
  }
  if (issuedRows.some((row) => String(row.recordId) !== String(declared.record_id))) {
    throw new Error(`follower journey targeted an undeclared record for ${model}: ${JSON.stringify(issuedRows)}`);
  }
  return {
    declaredFollowing,
    firstAction,
    issuedActions,
    liveList,
    changedText,
    restoredText,
  };
}
async function verifyAttachmentDeleteJourney(surface, model) {
  const expected = (target.attachment_delete_journeys || []).find((row) => row.model === model);
  if (!expected?.name || !expected?.attachment_id) throw new Error(`missing attachment delete fixture authority for ${model}`);
  const fileName = String(expected.name);
  const timelineEntry = surface.locator('.native-chatter-entry:visible').filter({ hasText: fileName });
  const timeline = surface.locator('[data-professional-collaboration-component="timeline"]');
  for (let pageIndex = 0; pageIndex < 3 && await timelineEntry.count() === 0; pageIndex += 1) {
    const loadMore = timeline.getByRole('button', { name: '加载更多', exact: true });
    if (await loadMore.count() === 0) break;
    await loadMore.click();
    await page.waitForTimeout(750);
  }
  await timelineEntry.waitFor({ state: 'visible', timeout: 30000 });
  const downloadButton = timelineEntry.locator('.native-attachment-download');
  await downloadButton.waitFor({ state: 'visible', timeout: 15000 });
  await downloadButton.click();
  const viewer = page.locator('[data-semantic-component="ScDialog"][data-state="open"]').filter({ hasText: fileName });
  await viewer.waitFor({ state: 'visible', timeout: 30000 });
  await viewer.getByRole('button', { name: '关闭附件', exact: true }).click();
  await viewer.waitFor({ state: 'detached', timeout: 15000 });
  const deleteButton = timelineEntry.getByRole('button', { name: '删除', exact: true });
  await deleteButton.waitFor({ state: 'visible', timeout: 15000 });
  await deleteButton.click();
  const confirmation = page.locator('[data-professional-workflow-component="confirm-dialog"][data-state="open"]');
  await confirmation.waitFor({ state: 'visible', timeout: 15000 });
  if (!String(await confirmation.textContent() || '').includes(fileName)) throw new Error(`attachment delete confirmation omitted target identity for ${model}`);
  await confirmation.getByRole('button', { name: '取消', exact: true }).click();
  await confirmation.waitFor({ state: 'detached', timeout: 15000 });
  if (await timelineEntry.count() !== 1) throw new Error(`attachment delete cancellation did not preserve ${model} entry`);
  await deleteButton.click();
  await confirmation.waitFor({ state: 'visible', timeout: 15000 });
  await confirmation.getByRole('button', { name: '确认删除附件', exact: true }).click();
  await timelineEntry.waitFor({ state: 'detached', timeout: 30000 });
  return { attachmentId: expected.attachment_id, fileName, downloaded: true, cancelPreserved: true, confirmed: true, deleted: true, remainingEntries: await timelineEntry.count() };
}
async function verifyAttachmentUploadJourney(surface, model) {
  const fileName = `codex-upload-journey-${model.replaceAll('.', '-')}-${Date.now()}.txt`;
  const manager = surface.locator('[data-professional-collaboration-component="attachments"][data-attachment-readiness="ready"]');
  await manager.waitFor({ state: 'visible', timeout: 15000 });
  await manager.locator('input[type="file"]').setInputFiles({
    name: fileName,
    mimeType: 'text/plain',
    buffer: Buffer.from(`governed upload journey for ${model}`, 'utf8'),
  });
  const timeline = surface.locator('[data-professional-collaboration-component="timeline"]');
  const timelineEntry = surface.locator('.native-chatter-entry:visible').filter({ hasText: fileName });
  await timelineEntry.waitFor({ state: 'visible', timeout: 30000 });
  const deleteButton = timelineEntry.getByRole('button', { name: '删除', exact: true });
  await deleteButton.click();
  const confirmation = page.locator('[data-professional-workflow-component="confirm-dialog"][data-state="open"]');
  await confirmation.waitFor({ state: 'visible', timeout: 15000 });
  await confirmation.getByRole('button', { name: '确认删除附件', exact: true }).click();
  await timelineEntry.waitFor({ state: 'detached', timeout: 30000 });
  return { fileName, uploaded: true, deleted: true, timelineReady: await timeline.count() === 1 };
}
async function verifyMessageDeleteJourney(surface, model) {
  const expected = (target.message_delete_journeys || []).find((row) => row.model === model);
  if (!expected?.body || !expected?.message_id) throw new Error(`missing message delete fixture authority for ${model}`);
  const body = String(expected.body);
  const timelineEntry = surface.locator('.native-chatter-entry:visible').filter({
    hasText: body,
    hasNotText: String(expected.reply_body || `${body}-reply`),
  });
  const timeline = surface.locator('[data-professional-collaboration-component="timeline"]');
  for (let pageIndex = 0; pageIndex < 3 && await timelineEntry.count() === 0; pageIndex += 1) {
    const loadMore = timeline.getByRole('button', { name: '加载更多', exact: true });
    if (await loadMore.count() === 0) break;
    await loadMore.click();
    await page.waitForTimeout(750);
  }
  await timelineEntry.waitFor({ state: 'visible', timeout: 30000 });
  const deleteButton = timelineEntry.getByRole('button', { name: '删除', exact: true });
  await deleteButton.waitFor({ state: 'visible', timeout: 15000 });
  await deleteButton.click();
  const confirmation = page.locator('[data-professional-workflow-component="confirm-dialog"][data-state="open"]');
  await confirmation.waitFor({ state: 'visible', timeout: 15000 });
  if (!String(await confirmation.textContent() || '').includes(body.slice(0, 36))) {
    throw new Error(`message delete confirmation omitted target identity for ${model}`);
  }
  await confirmation.getByRole('button', { name: '取消', exact: true }).click();
  await confirmation.waitFor({ state: 'detached', timeout: 15000 });
  if (await timelineEntry.count() !== 1) throw new Error(`message delete cancellation did not preserve ${model} entry`);
  await deleteButton.click();
  await confirmation.waitFor({ state: 'visible', timeout: 15000 });
  await confirmation.getByRole('button', { name: '确认删除消息', exact: true }).click();
  await timelineEntry.waitFor({ state: 'detached', timeout: 30000 });
  return { messageId: expected.message_id, body, cancelPreserved: true, confirmed: true, deleted: true };
}
async function verifyMessageReplyJourney(surface, model) {
  const expected = (target.message_delete_journeys || []).find((row) => row.model === model);
  if (!expected?.body || !expected?.message_id || !expected?.reply_body) {
    throw new Error(`missing message reply fixture authority for ${model}`);
  }
  const timeline = surface.locator('[data-professional-collaboration-component="timeline"]');
  const timelineEntry = surface.locator('.native-chatter-entry:visible').filter({ hasText: String(expected.body) });
  for (let pageIndex = 0; pageIndex < 3 && await timelineEntry.count() === 0; pageIndex += 1) {
    const loadMore = timeline.getByRole('button', { name: '加载更多', exact: true });
    if (await loadMore.count() === 0) break;
    await loadMore.click();
    await page.waitForTimeout(750);
  }
  await timelineEntry.waitFor({ state: 'visible', timeout: 30000 });
  await timelineEntry.getByRole('button', { name: '回复', exact: true }).click();
  const composer = surface.locator('[data-professional-collaboration-component="composer"]');
  await composer.waitFor({ state: 'visible', timeout: 15000 });
  const replyTarget = composer.locator('.native-chatter-reply-target');
  await replyTarget.waitFor({ state: 'visible', timeout: 15000 });
  if (!String(await replyTarget.textContent() || '').includes(String(expected.body))) {
    throw new Error(`message reply composer omitted parent identity for ${model}`);
  }
  await composer.locator('textarea').fill(String(expected.reply_body));
  await composer.locator('.native-chatter-compose-actions button').first().click();
  const replyEntry = surface.locator('.native-chatter-entry:visible').filter({ hasText: String(expected.reply_body) });
  await replyEntry.waitFor({ state: 'visible', timeout: 30000 });
  return { messageId: expected.message_id, body: expected.body, replyBody: expected.reply_body, parentId: expected.message_id };
}
async function verifyCreateActionJourney(surface, model) {
  const token = `${model.replaceAll('.', '-')}-${Date.now()}`;
  const results = {};
  for (const mode of ['message', 'note']) {
    const body = `codex-create-action-journey-${mode}-${token}`;
    const action = surface.locator('.chips').getByTitle(mode, { exact: true });
    await action.waitFor({ state: 'visible', timeout: 15000 });
    await expectActionEnabled(action, `${model} ${mode} create action`);
    await action.click();
    const composer = surface.locator('[data-professional-collaboration-component="composer"]');
    await composer.waitFor({ state: 'visible', timeout: 15000 });
    let mentionSelected = false;
    if (mode === 'message') {
      const mentionChoice = composer.locator('.native-collab-options button:visible').first();
      await mentionChoice.waitFor({ state: 'visible', timeout: 30000 });
      await mentionChoice.click();
      await composer.locator('.native-collab-selected button:visible').first().waitFor({ state: 'visible', timeout: 15000 });
      mentionSelected = true;
    }
    await composer.locator('textarea').fill(body);
    await composer.locator('.native-chatter-compose-actions button').first().click();
    const entry = surface.locator('.native-chatter-entry:visible').filter({ hasText: body });
    await entry.waitFor({ state: 'visible', timeout: 30000 });
    await entry.getByRole('button', { name: '删除', exact: true }).click();
    const confirmation = page.locator('[data-professional-workflow-component="confirm-dialog"][data-state="open"]');
    await confirmation.waitFor({ state: 'visible', timeout: 15000 });
    await confirmation.getByRole('button', { name: '确认删除消息', exact: true }).click();
    await entry.waitFor({ state: 'detached', timeout: 30000 });
    results[mode] = { body, mentionSelected, posted: true, deleted: true };
  }
  const summary = `codex-create-action-journey-activity-${token}`;
  const activityAction = surface.locator('.chips').getByTitle('activity', { exact: true });
  await activityAction.waitFor({ state: 'visible', timeout: 15000 });
  await expectActionEnabled(activityAction, `${model} activity create action`);
  await activityAction.click();
  const activityComposer = surface.locator('[data-professional-collaboration-component="composer"]');
  await activityComposer.waitFor({ state: 'visible', timeout: 15000 });
  const assigneeSelect = activityComposer.locator('[data-semantic-component="ScSelect"]');
  await assigneeSelect.waitFor({ state: 'visible', timeout: 30000 });
  await assigneeSelect.click();
  const assigneeOption = page.locator('.t-select-option:visible').first();
  await assigneeOption.waitFor({ state: 'visible', timeout: 15000 });
  await assigneeOption.click();
  await activityComposer.locator('label').filter({ hasText: '摘要' }).locator('input').fill(summary);
  await activityComposer.locator('.native-chatter-compose-actions button').first().click();
  const activityEntry = surface.locator('.native-chatter-entry:visible').filter({ hasText: summary });
  await activityEntry.waitFor({ state: 'visible', timeout: 30000 });
  await activityEntry.getByRole('button', { name: '取消', exact: true }).click();
  const confirmation = page.locator('[data-professional-workflow-component="confirm-dialog"][data-state="open"]');
  await confirmation.waitFor({ state: 'visible', timeout: 15000 });
  await confirmation.getByRole('button', { name: '确认取消计划', exact: true }).click();
  await activityEntry.waitFor({ state: 'detached', timeout: 30000 });
  results.activity = { summary, assigneeSelected: true, scheduled: true, cancelled: true };
  return results;
}
async function verifyActivityCancelJourney(surface, model) {
  const expected = (target.activity_cancel_journeys || []).find((row) => row.model === model);
  if (!expected?.summary || !expected?.activity_id) throw new Error(`missing activity cancel fixture authority for ${model}`);
  const summary = String(expected.summary);
  const timelineEntry = surface.locator('.native-chatter-entry:visible').filter({ hasText: summary });
  const timeline = surface.locator('[data-professional-collaboration-component="timeline"]');
  for (let pageIndex = 0; pageIndex < 3 && await timelineEntry.count() === 0; pageIndex += 1) {
    const loadMore = timeline.getByRole('button', { name: '加载更多', exact: true });
    if (await loadMore.count() === 0) break;
    await loadMore.click();
    await page.waitForTimeout(750);
  }
  await timelineEntry.waitFor({ state: 'visible', timeout: 30000 });
  const cancelButton = timelineEntry.getByRole('button', { name: '取消', exact: true });
  await cancelButton.waitFor({ state: 'visible', timeout: 15000 });
  await cancelButton.click();
  const confirmation = page.locator('[data-professional-workflow-component="confirm-dialog"][data-state="open"]');
  await confirmation.waitFor({ state: 'visible', timeout: 15000 });
  if (!String(await confirmation.textContent() || '').includes(summary)) {
    throw new Error(`activity cancel confirmation omitted target identity for ${model}`);
  }
  await confirmation.getByRole('button', { name: '取消', exact: true }).click();
  await confirmation.waitFor({ state: 'detached', timeout: 15000 });
  if (await timelineEntry.count() !== 1) throw new Error(`activity cancellation dialog did not preserve ${model} entry`);
  await cancelButton.click();
  await confirmation.waitFor({ state: 'visible', timeout: 15000 });
  await confirmation.getByRole('button', { name: '确认取消计划', exact: true }).click();
  await timelineEntry.waitFor({ state: 'detached', timeout: 30000 });
  return { activityId: expected.activity_id, summary, cancelPreserved: true, confirmed: true, removed: true };
}
page.on('console', (message) => {
  if (message.type() === 'error') browserErrors.push(`console:${message.text()}`);
});
page.on('pageerror', (error) => browserErrors.push(`pageerror:${error.message}`));
page.on('request', (request) => {
  if (request.method() !== 'POST') return;
  let payload = {};
  try { payload = JSON.parse(request.postData() || '{}'); } catch {}
  const intent = String(payload.intent || '');
  const op = String(payload?.params?.op || payload.op || '');
  if (intent === 'execute_button') executeRequests.push({
    model: payload?.params?.model,
    recordId: payload?.params?.res_id,
    button: payload?.params?.button,
  });
  if (intent === 'chatter.followers.update') followerUpdates.push({
    model: payload?.params?.model,
    recordId: payload?.params?.res_id,
    action: payload?.params?.action,
  });
  if (intent === 'file.upload' || intent === 'file.download' || intent === 'chatter.attachment.delete') attachmentMutations.push({
    intent,
    model: payload?.params?.model,
    recordId: payload?.params?.res_id,
    attachmentId: payload?.params?.attachment_id,
    name: payload?.params?.name,
  });
  if (intent === 'chatter.message.delete' || intent === 'chatter.post') messageMutations.push({
    intent,
    model: payload?.params?.model,
    recordId: payload?.params?.res_id,
    messageId: payload?.params?.message_id,
    parentId: payload?.params?.parent_id,
    body: payload?.params?.body,
    mentionUserIds: payload?.params?.mention_user_ids,
  });
  if (intent === 'chatter.activity.update' || intent === 'chatter.activity.schedule') activityMutations.push({
    intent,
    model: payload?.params?.model,
    recordId: payload?.params?.res_id,
    activityId: payload?.params?.activity_id,
    action: payload?.params?.action,
    summary: payload?.params?.summary,
    userId: payload?.params?.user_id,
  });
  if (intent === 'collaboration.users.search') userSearchRequests.push({
    query: payload?.params?.query,
    limit: payload?.params?.limit,
  });
  if (['create', 'write', 'unlink'].includes(op)) mutations.push({ intent, op });
});
page.on('response', async (response) => {
  if (!response.url().includes('/api/v1/intent')) return;
  let request = {};
  try { request = JSON.parse(response.request().postData() || '{}'); } catch {}
  if (response.status() >= 400) {
    let responseText = '';
    try { responseText = (await response.text()).slice(0, 1200); } catch {}
    intentFailures.push({ status: response.status(), intent: String(request.intent || ''), responseText });
  }
  if (String(request.intent || '') === 'chatter.followers.list') {
    let listBody = {};
    try { listBody = await response.json(); } catch {}
    const listData = listBody?.data && typeof listBody.data === 'object' ? listBody.data : {};
    const listParams = request?.params && typeof request.params === 'object' ? request.params : {};
    followerListResponses.push({
      status: response.status(),
      ok: listBody?.ok === true,
      model: String(listParams.model ?? request.model ?? ''),
      recordId: String(listParams.res_id ?? listParams.record_id ?? request.res_id ?? ''),
      count: Number(listData.count ?? -1),
      isFollowing: listData.is_following === true,
      canFollow: listData.can_follow === true,
      canUnfollow: listData.can_unfollow === true,
    });
  }
  if (String(request.intent || '') !== 'ui.contract.v2') return;
  let body = {};
  try { body = await response.json(); } catch {}
  const data = body?.data && typeof body.data === 'object' ? body.data : {};
  const params = request?.params && typeof request.params === 'object' ? request.params : {};
  const structure = data?.formStructureContract && typeof data.formStructureContract === 'object'
    ? data.formStructureContract
    : {};
  contractPresentations.push({
    actionId: String(params.action_id ?? request.action_id ?? ''),
    menuId: String(params.menu_id ?? request.menu_id ?? ''),
    model: String(params.model ?? request.model ?? ''),
    recordId: String(params.record_id ?? request.record_id ?? ''),
    structureVersion: structure.structureVersion,
    presentationMode: structure.presentationMode,
  });
  const rules = Array.isArray(data?.actionContract?.actionRuleList)
    ? data.actionContract.actionRuleList
    : [];
  const statuses = Array.isArray(data?.statusContract?.buttonStatus)
    ? data.statusContract.buttonStatus
    : [];
  contractActions.push(...rules.filter((row) => {
    const source = String(row?.sourceWidgetId || '');
    return String(row?.sourceChannel || '') === 'bound_model_action'
      || source.startsWith('mode.')
      || String(row?.actionId || '') === 'action.payment_submit'
      || String(row?.backendIdentity || '').includes('action_submit');
  }).map((row) => ({
    actionId: row.actionId,
    actionKey: row.actionKey,
    backendIdentity: row.backendIdentity,
    sourceChannel: row.sourceChannel,
    sourceWidgetId: row.sourceWidgetId,
    targetScope: row.targetScope,
    visibleProfiles: row.visibleProfiles,
    allowed: row.allowed,
    enabled: row.enabled,
    disabled: row.disabled,
    entitlementEvaluated: row.entitlementEvaluated,
    triggerType: row.triggerType,
    button: row.button,
    target: row.target,
    visible: row.visible,
    invisible: row.invisible,
    modifiers: row.modifiers,
    status: statuses.filter((status) => (
      String(status?.backendIdentity || '') === String(row?.backendIdentity || '')
    )).map((status) => ({
      btnId: status.btnId,
      backendIdentity: status.backendIdentity,
      visible: status.visible,
      disabled: status.disabled,
      reasonCode: status.reasonCode,
    })),
  })));
});

try {
  await page.goto(`${frontendUrl}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.locator('#login-username').fill(login);
  await page.locator('#login-password').fill(password);
  const databaseInput = page.getByLabel('数据库');
  if (await databaseInput.count()) {
    if (await databaseInput.isEnabled()) await databaseInput.fill(database);
  }
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 30000 });
  const projectCreateRoute = `${frontendUrl}/f/project.project/new?menu_id=${target.menu_id}&action_id=${target.action_id}`;
  await page.goto(projectCreateRoute, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const surface = page.locator(
    `[data-product-page-mode="form"][data-form-model="project.project"][data-form-record="new"]`
    + `[data-form-action-id="${target.action_id}"][data-form-menu-id="${target.menu_id}"]`,
  );
  await surface.waitFor({ state: 'visible', timeout: 45000 });
  await page.waitForFunction(() => (
    document.querySelectorAll('[data-contract-form-driver]').length
    + document.querySelectorAll('[data-contract-form-driver-error]').length === 1
  ), undefined, { timeout: 45000 });
  const drivers = await surface.locator('[data-contract-form-driver]').count();
  const errors = await surface.locator('[data-contract-form-driver-error]').allTextContents();
  if (drivers !== 1 || errors.length !== 0) {
    throw new Error(`project create canonical driver did not load: ${JSON.stringify({ drivers, errors, contractActions })}`);
  }
  if (contractActions.some((row) => String(row.actionId || '').includes('project_share')
    || String(row.actionId || '').includes('send_mail')
    || String(row.actionId || '').includes('sms_composer'))) {
    throw new Error(`project create contract exposed record-bound action: ${JSON.stringify(contractActions)}`);
  }
  if (contractActions.some((row) => String(row.sourceWidgetId || '').startsWith('mode.')
    && String(row.targetScope || '') !== 'runtime')) {
    throw new Error(`mode-local action escaped runtime scope: ${JSON.stringify(contractActions)}`);
  }
  const projectResult = {
    url: page.url(),
    drivers,
    errors,
    taskPage: await surface.locator('[data-object-task-page]').count(),
    nativeStructure: await surface.locator('[data-native-contract-structure]').count(),
    riskRegions: await surface.locator('[data-floorplan-region="risk"]').count(),
    nativeSections: await surface.locator('section.native-container--group').evaluateAll((nodes) => nodes.map((node) => ({
      heading: (node.querySelector(':scope > header h3')?.textContent || '').trim(),
      fields: [...node.querySelectorAll('[data-field-name]')]
        .map((field) => field.getAttribute('data-field-name')),
    }))),
    contractActions: [...contractActions],
    header: await captureHeaderPresentation(surface),
  };
  const projectPresentation = contractPresentations
    .filter((row) => row.actionId === String(target.action_id))
    .at(-1);
  if (projectPresentation?.structureVersion !== '1.1' || projectPresentation?.presentationMode !== 'task') {
    throw new Error(`project initiation did not resolve task presentation: ${JSON.stringify(projectPresentation)}`);
  }
  // U-C4 G12 retired the entry-level structure declaration, so the resolved
  // native view owns field placement: the create surface must render the
  // declared native structure and must not bring the retired floorplan regions
  // back. The declared business groups (current_task / intake_risk, projected by
  // the contract into intake_semantic_contract) must carry their declared
  // fields, so the check binds the declaration to the rendered structure
  // instead of asserting a heading string on its own.
  const declaredFieldAnchors = (target.intake_semantic_contract || {}).anchor_groups || {};
  const declaredAnchorLabels = (target.intake_semantic_contract || {}).anchor_sections || {};
  const declaredSections = Object.entries(declaredFieldAnchors).map(([field, anchor]) => ({
    field,
    anchor,
    label: String(declaredAnchorLabels[anchor] || ''),
  }));
  if (!declaredSections.length || declaredSections.some((row) => !row.label)) {
    throw new Error(`project create declaration is incomplete: ${JSON.stringify({
      declaredFieldAnchors, declaredAnchorLabels,
    })}`);
  }
  if (projectResult.nativeStructure !== 1
    || projectResult.taskPage !== 0 || projectResult.riskRegions !== 0) {
    throw new Error(`project initiation did not render the declared native structure: ${JSON.stringify(projectResult)}`);
  }
  const unplacedSections = declaredSections.filter((row) => !projectResult.nativeSections.some(
    (section) => section.heading === row.label && section.fields.includes(row.field),
  ));
  if (unplacedSections.length) {
    throw new Error(`project initiation native sections are incomplete: ${JSON.stringify({
      unplacedSections, nativeSections: projectResult.nativeSections,
    })}`);
  }
  if (projectResult.header.commandBars !== 1 || projectResult.header.scButtons < 1
    || projectResult.header.primaryActions > 1 || projectResult.header.rawButtonsOutsideWorkflow !== 0) {
    throw new Error(`project initiation header primitive boundary failed: ${JSON.stringify(projectResult.header)}`);
  }

  contractActions.length = 0;
  const workspaceRoute = `${frontendUrl}/r/project.project/${target.project_record_id}`
    + `?menu_id=${target.workspace_menu_id}&action_id=${target.workspace_action_id}`;
  await page.goto(workspaceRoute, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const workspaceSurface = page.locator(
    `[data-product-page-mode="form"][data-form-model="project.project"]`
    + `[data-form-record="${target.project_record_id}"]`
    + `[data-form-action-id="${target.workspace_action_id}"][data-form-menu-id="${target.workspace_menu_id}"]`,
  );
  await workspaceSurface.waitFor({ state: 'visible', timeout: 45000 });
  await page.waitForFunction(() => (
    document.querySelectorAll('[data-contract-form-driver]').length
    + document.querySelectorAll('[data-contract-form-driver-error]').length === 1
  ), undefined, { timeout: 45000 });
  await workspaceSurface.locator('[data-readonly-relation]').first().waitFor({ state: 'visible', timeout: 45000 });
  await page.waitForFunction(() => (
    document.querySelectorAll('[data-readonly-relation-loading]').length === 0
    && document.querySelectorAll('.o2m-readonly-row, .relation-readonly-empty').length > 0
  ), undefined, { timeout: 45000 });
  await workspaceSurface.locator('[data-professional-collaboration-component="followers"][data-state="ready"]')
    .waitFor({ state: 'visible', timeout: 45000 });
  const workspaceFollowerJourney = await verifyFollowerMutation(workspaceSurface, 'project.project');
  const workspaceAttachmentUploadJourney = await verifyAttachmentUploadJourney(workspaceSurface, 'project.project');
  const workspaceAttachmentDeleteJourney = await verifyAttachmentDeleteJourney(workspaceSurface, 'project.project');
  const workspaceMessageReplyJourney = await verifyMessageReplyJourney(workspaceSurface, 'project.project');
  const workspaceCreateActionJourney = await verifyCreateActionJourney(workspaceSurface, 'project.project');
  const workspaceMessageDeleteJourney = await verifyMessageDeleteJourney(workspaceSurface, 'project.project');
  const workspaceActivityCancelJourney = await verifyActivityCancelJourney(workspaceSurface, 'project.project');
  const workspaceResult = {
    url: page.url(),
    drivers: await workspaceSurface.locator('[data-contract-form-driver]').count(),
    errors: await workspaceSurface.locator('[data-contract-form-driver-error]').allTextContents(),
    taskPage: await workspaceSurface.locator('[data-object-task-page]').count(),
    nativeStructure: await workspaceSurface.locator('[data-native-contract-structure]').count(),
    nativeSections: await workspaceSurface.locator('.native-container--group').evaluateAll((nodes) => nodes.map((node) => ({
      tag: node.tagName,
      title: String(node.getAttribute('data-group-title') || '').trim(),
      heading: (node.querySelector(':scope > header h3, :scope > header button, .t-card__title')?.textContent || '').trim(),
      fields: [...node.querySelectorAll('[data-field-name]')].map((field) => field.getAttribute('data-field-name')),
    }))),
    notebookPages: await workspaceSurface.locator('[data-native-contract-structure] .native-tabs .native-tab')
      .evaluateAll((nodes) => nodes.map((node) => (node.textContent || '').trim())),
    readonlyRelationFacts: await workspaceSurface.locator('.o2m-readonly-fact dd').allTextContents(),
    readonlyRelationRows: await workspaceSurface.locator('.o2m-readonly-row').evaluateAll((rows) => rows.map((row) => (
      [...row.querySelectorAll('.o2m-readonly-fact dd')].map((node) => (node.textContent || '').trim())
    ))),
    readonlyRelationEmptyLabels: await workspaceSurface.locator('.relation-readonly-empty').allTextContents(),
    header: await captureHeaderPresentation(workspaceSurface),
    followers: await workspaceSurface.locator('[data-professional-collaboration-component="followers"]').evaluateAll((nodes) => nodes.map((node) => ({
      state: node.getAttribute('data-state'),
      text: String(node.textContent || '').replace(/\s+/g, ' ').trim(),
    }))),
    followerReadiness: await workspaceSurface.locator('[data-professional-collaboration-component="panel"]').getAttribute('data-follower-readiness'),
    followerJourney: workspaceFollowerJourney,
    attachmentUploadJourney: workspaceAttachmentUploadJourney,
    attachmentDeleteJourney: workspaceAttachmentDeleteJourney,
    messageReplyJourney: workspaceMessageReplyJourney,
    createActionJourney: workspaceCreateActionJourney,
    messageDeleteJourney: workspaceMessageDeleteJourney,
  };
  const workspacePresentation = contractPresentations
    .filter((row) => row.actionId === String(target.workspace_action_id))
    .at(-1);
  if (workspacePresentation?.structureVersion !== '1.1' || workspacePresentation?.presentationMode !== 'workspace') {
    throw new Error(`project workspace did not resolve workspace presentation: ${JSON.stringify(workspacePresentation)}`);
  }
  // The 项目台账 record surface is the unified single-page native overview
  // declaration (view_project_overview_form). Its contract owns the section
  // identity, so the render binding asserts the declared sections and fields
  // (and a notebook tab count only when the declaration declares tabs) instead
  // of the retired 11-page default project form tab count.
  const workspaceDeclaration = target.workspace_structure_contract || {};
  const declaredNotebookTabs = (workspaceDeclaration.notebook_tabs || []).map((label) => String(label));
  const declaredWorkspaceSections = (workspaceDeclaration.sections || []).map((row) => ({
    title: String(row.title || ''),
    fields: (row.fields || []).map((field) => String(field.name || field)),
    mustRenderFields: (row.must_render_fields || []).map((field) => String(field)),
  }));
  if (!declaredWorkspaceSections.length
    || declaredWorkspaceSections.some((row) => !row.title || !row.fields.length)) {
    throw new Error(`project workspace declaration is incomplete: ${JSON.stringify(workspaceDeclaration)}`);
  }
  if (
    workspaceResult.drivers !== 1
    || workspaceResult.errors.length !== 0
    || workspaceResult.taskPage !== 0
    || workspaceResult.nativeStructure !== 1
    || workspaceResult.notebookPages.length !== declaredNotebookTabs.length
  ) {
    throw new Error(`project workspace did not render the declared native structure: ${JSON.stringify(workspaceResult)}`);
  }
  const declaredTitles = declaredWorkspaceSections.map((row) => row.title);
  const renderedByTitle = new Map(
    workspaceResult.nativeSections.map((section) => [section.heading, section.fields]),
  );
  // A declared section that must show a visible fact has to be rendered under
  // its declared heading and carry that fact; a declaration that places no
  // visible fact (every field empty or hidden by the declaration) may be
  // omitted, but never replaced by an undeclared section.
  const missingWorkspaceSections = declaredWorkspaceSections.filter((row) => (
    row.mustRenderFields.length > 0 && !renderedByTitle.has(row.title)
  ));
  const unplacedWorkspaceFields = declaredWorkspaceSections.flatMap((row) => {
    const rendered = renderedByTitle.get(row.title);
    if (!rendered) return [];
    return row.mustRenderFields.filter((field) => !rendered.includes(field)).map((field) => `${row.title}:${field}`);
  });
  const undeclaredSections = workspaceResult.nativeSections
    .map((section) => section.heading)
    .filter((heading) => heading && !declaredTitles.includes(heading));
  const unplacedRenderedFields = declaredWorkspaceSections.flatMap((row) => {
    const rendered = renderedByTitle.get(row.title);
    if (!rendered) return [];
    return rendered.filter((field) => !row.fields.includes(field)).map((field) => `${row.title}:${field}`);
  });
  if (missingWorkspaceSections.length || unplacedWorkspaceFields.length
    || undeclaredSections.length || unplacedRenderedFields.length) {
    throw new Error(`project workspace native sections are incomplete: ${JSON.stringify({
      missingWorkspaceSections, unplacedWorkspaceFields, undeclaredSections, unplacedRenderedFields,
      nativeSections: workspaceResult.nativeSections,
    })}`);
  }
  if (declaredNotebookTabs.length) {
    const renderedTabs = workspaceResult.notebookPages.map((label) => label.replace(/\s+/g, ''));
    const missingTabs = declaredNotebookTabs.filter((label) => !renderedTabs.includes(label.replace(/\s+/g, '')));
    if (missingTabs.length) {
      throw new Error(`project workspace notebook tabs are incomplete: ${JSON.stringify({ missingTabs, renderedTabs })}`);
    }
  }
  if (workspaceResult.header.commandBars !== 1 || workspaceResult.header.scButtons < 1
    || workspaceResult.header.primaryActions > 1 || workspaceResult.header.rawButtonsOutsideWorkflow !== 0) {
    throw new Error(`project workspace header primitive boundary failed: ${JSON.stringify(workspaceResult.header)}`);
  }
  if (workspaceResult.followers.length !== 1 || workspaceResult.followerReadiness !== 'ready'
    || workspaceResult.followers[0].state !== 'ready') {
    throw new Error(`project follower component is not backend-authoritative: ${JSON.stringify(workspaceResult)}`);
  }
  if (workspaceResult.readonlyRelationFacts.some((value) => /^\s*\d+\s*,\s+\D/.test(value) || /^#\d+$/.test(value))) {
    throw new Error(`project workspace leaked raw relation ids: ${JSON.stringify(workspaceResult.readonlyRelationFacts)}`);
  }
  if (workspaceResult.readonlyRelationFacts.some((value) => /^\d{4,}(?:\.\d+)?$/.test(value) || /^\d{4}-\d{2}-\d{2}T/.test(value))) {
    throw new Error(`project workspace leaked machine-formatted relation facts: ${JSON.stringify(workspaceResult.readonlyRelationFacts)}`);
  }
  if (workspaceResult.readonlyRelationRows.some((values) => values.every((value) => !value || value === '—'))) {
    throw new Error(`project workspace rendered empty readonly relation rows: ${JSON.stringify(workspaceResult.readonlyRelationRows)}`);
  }
  if (workspaceResult.readonlyRelationRows.length > 0 && workspaceResult.readonlyRelationEmptyLabels.length > 0) {
    throw new Error(`project workspace mixed hydrated relation rows with an empty state: ${JSON.stringify(workspaceResult)}`);
  }
  if (workspaceResult.readonlyRelationRows.length === 0
    && (workspaceResult.readonlyRelationEmptyLabels.length === 0
      || workspaceResult.readonlyRelationEmptyLabels.some((value) => !value.includes('暂无可展示记录')))) {
    throw new Error(`project workspace relation empty state is misleading: ${JSON.stringify(workspaceResult.readonlyRelationEmptyLabels)}`);
  }

  contractActions.length = 0;
  const paymentRoute = `${frontendUrl}/f/payment.request/${target.payment_record_id}`
    + `?menu_id=${target.payment_menu_id}&action_id=${target.payment_action_id}`;
  await page.goto(paymentRoute, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const paymentSurface = page.locator(
    `[data-product-page-mode="form"][data-form-model="payment.request"]`
    + `[data-form-record="${target.payment_record_id}"]`
    + `[data-form-action-id="${target.payment_action_id}"][data-form-menu-id="${target.payment_menu_id}"]`,
  );
  await paymentSurface.waitFor({ state: 'visible', timeout: 45000 });
  await page.waitForFunction(() => (
    document.querySelectorAll('[data-contract-form-driver]').length
    + document.querySelectorAll('[data-contract-form-driver-error]').length === 1
  ), undefined, { timeout: 45000 });
  await paymentSurface.locator('[data-professional-collaboration-component="followers"][data-state="ready"]')
    .waitFor({ state: 'visible', timeout: 45000 });
  const paymentFollowerJourney = await verifyFollowerMutation(paymentSurface, 'payment.request');
  const paymentAttachmentUploadJourney = await verifyAttachmentUploadJourney(paymentSurface, 'payment.request');
  const paymentAttachmentDeleteJourney = await verifyAttachmentDeleteJourney(paymentSurface, 'payment.request');
  const paymentMessageReplyJourney = await verifyMessageReplyJourney(paymentSurface, 'payment.request');
  const paymentCreateActionJourney = await verifyCreateActionJourney(paymentSurface, 'payment.request');
  const paymentMessageDeleteJourney = await verifyMessageDeleteJourney(paymentSurface, 'payment.request');
  const paymentActivityCancelJourney = await verifyActivityCancelJourney(paymentSurface, 'payment.request');
  const paymentDrivers = await paymentSurface.locator('[data-contract-form-driver]').count();
  const paymentErrors = await paymentSurface.locator('[data-contract-form-driver-error]').allTextContents();
  const paymentResult = {
    url: page.url(),
    drivers: paymentDrivers,
    errors: paymentErrors,
    contractActions: [...contractActions],
    visibleFieldNames: await paymentSurface
      .locator('[data-field-name]')
      .evaluateAll((nodes) => nodes.map((node) => node.getAttribute('data-field-name')).filter(Boolean)),
    emptyReadonlyRelations: await paymentSurface.locator('[data-readonly-relation-empty]').count(),
    retiredRelationRegionCount: await paymentSurface.locator('[data-floorplan-region="relation"]').count(),
    relationFields: await paymentSurface.locator('[data-field-name][data-component-key]').evaluateAll((nodes) => nodes.map((node) => ({
      field: node.getAttribute('data-field-name'),
      componentKey: node.getAttribute('data-component-key'),
      renderer: node.getAttribute('data-component-renderer'),
      widgetType: node.getAttribute('data-widget-type'),
      auth: node.getAttribute('data-field-auth'),
    }))),
    detailCollections: await paymentSurface
      .locator('[data-semantic-component="ProfessionalDetailCollectionControl"]')
      .evaluateAll((nodes) => nodes.map((node) => ({
        relationModel: node.getAttribute('data-relation-model'),
        rowCount: node.getAttribute('data-row-count'),
        columnCount: node.getAttribute('data-column-count'),
        canCreate: node.getAttribute('data-can-create'),
        canInlineEdit: node.getAttribute('data-can-inline-edit'),
        controlState: node.getAttribute('data-control-state'),
      }))),
    attachmentEditors: await paymentSurface.locator('[data-semantic-component="RelationAttachmentEditor"]').evaluateAll((nodes) => nodes.map((node) => ({
      state: String(node.getAttribute('data-control-state') || ''),
      uploads: node.querySelectorAll('input[type="file"]').length,
      removes: [...node.querySelectorAll('button')].filter((button) => (button.textContent || '').trim() === '移除').length,
    }))),
    header: await captureHeaderPresentation(paymentSurface),
    followers: await paymentSurface.locator('[data-professional-collaboration-component="followers"]').evaluateAll((nodes) => nodes.map((node) => ({
      state: node.getAttribute('data-state'),
      text: String(node.textContent || '').replace(/\s+/g, ' ').trim(),
    }))),
    followerReadiness: await paymentSurface.locator('[data-professional-collaboration-component="panel"]').getAttribute('data-follower-readiness'),
    followerJourney: paymentFollowerJourney,
    attachmentUploadJourney: paymentAttachmentUploadJourney,
    attachmentDeleteJourney: paymentAttachmentDeleteJourney,
    messageReplyJourney: paymentMessageReplyJourney,
    createActionJourney: paymentCreateActionJourney,
    messageDeleteJourney: paymentMessageDeleteJourney,
  };
  if (paymentDrivers !== 1 || paymentErrors.length !== 0) {
    throw new Error(`payment record canonical driver did not load: ${JSON.stringify(paymentResult)}`);
  }
  if (paymentResult.header.commandBars !== 1 || paymentResult.header.scButtons < 1
    || paymentResult.header.primaryActions !== 1 || paymentResult.header.rawButtonsOutsideWorkflow !== 0) {
    throw new Error(`payment task header primitive boundary failed: ${JSON.stringify(paymentResult.header)}`);
  }
  if (paymentResult.followers.length !== 1 || paymentResult.followerReadiness !== 'ready'
    || paymentResult.followers[0].state !== 'ready') {
    throw new Error(`payment follower component is not backend-authoritative: ${JSON.stringify(paymentResult)}`);
  }
  if (paymentResult.visibleFieldNames.length === 0
    || new Set(paymentResult.visibleFieldNames).size !== paymentResult.visibleFieldNames.length) {
    throw new Error(`payment page repeated canonical facts: ${JSON.stringify(paymentResult.visibleFieldNames)}`);
  }
  // The record relation area is bound to the contract declaration, not to the
  // retired floorplan relation region: the declared relation field must render
  // the declared component, the declared detail collection must be present
  // exactly once and its capability projection plus column count must mirror
  // the declaration. This replaces the retired region selector assertion
  // without weakening it: an editable declaration must render an editable
  // collection and must not fall back to a readonly empty placeholder.
  const declaredDetail = (target.payment_detail_declaration || [])[0];
  if (!declaredDetail || !declaredDetail.component_key || !declaredDetail.relation_model) {
    throw new Error(`payment detail declaration is missing: ${JSON.stringify(target.payment_detail_declaration)}`);
  }
  const declaredRelationFields = paymentResult.relationFields.filter((row) => (
    row.field === declaredDetail.field && row.componentKey === declaredDetail.component_key
  ));
  if (declaredRelationFields.length !== 1 || !declaredRelationFields[0].renderer) {
    throw new Error(`payment relation field did not consume the declared component: ${JSON.stringify({
      declaredDetail, relationFields: paymentResult.relationFields,
    })}`);
  }
  const declaredCollections = paymentResult.detailCollections.filter(
    (row) => row.relationModel === declaredDetail.relation_model,
  );
  if (declaredCollections.length !== 1) {
    throw new Error(`payment relation area did not render the declared detail collection: ${JSON.stringify({
      declaredDetail, detailCollections: paymentResult.detailCollections,
    })}`);
  }
  const renderedCollection = declaredCollections[0];
  const declaredControlState = declaredDetail.readonly ? 'readonly' : 'editable';
  if (renderedCollection.canCreate !== String(declaredDetail.can_create)
    || renderedCollection.canInlineEdit !== String(declaredDetail.can_inline_edit)
    || Number(renderedCollection.columnCount) !== declaredDetail.column_count
    || renderedCollection.controlState !== declaredControlState) {
    throw new Error(`payment relation capability projection drifted from the declaration: ${JSON.stringify({
      declaredDetail, renderedCollection,
    })}`);
  }
  if (paymentResult.retiredRelationRegionCount !== 0) {
    throw new Error(`payment relation area brought the retired floorplan region back: ${JSON.stringify(paymentResult.retiredRelationRegionCount)}`);
  }
  if (!declaredDetail.readonly && paymentResult.emptyReadonlyRelations !== 0) {
    throw new Error(`payment relation area rendered a readonly empty placeholder for an editable declaration: ${JSON.stringify(paymentResult.emptyReadonlyRelations)}`);
  }
  if (paymentResult.attachmentEditors.some((editor) => (
    (editor.state === 'readonly' && (editor.uploads > 0 || editor.removes > 0))
    || (editor.state === 'editable' && editor.uploads !== 1)
  ))) {
    throw new Error(`payment attachment authority projection failed: ${JSON.stringify(paymentResult.attachmentEditors)}`);
  }
  const activityTabLabels = page.locator('.activity-page-tab-label');
  const activityTabKeys = await activityTabLabels.evaluateAll((nodes) => nodes.map((node) => ({
    key: String(node.getAttribute('data-activity-page-key') || ''),
    title: String(node.textContent || '').trim(),
  })));
  const projectActivityIndex = activityTabKeys.findIndex((item) => (
    item.key.includes(`record:project.project:${target.project_record_id}`)
  ));
  const projectCreateActivityIndex = activityTabKeys.findIndex((item) => item.key.startsWith('new:project.project:'));
  const paymentActivityIndex = activityTabKeys.findIndex((item) => (
    item.key.includes(`record:payment.request:${target.payment_record_id}`)
  ));
  if (activityTabKeys.length < 2 || projectActivityIndex < 0 || projectCreateActivityIndex < 0 || paymentActivityIndex < 0) {
    throw new Error(`cross-model activity pages are incomplete: ${JSON.stringify(activityTabKeys)}`);
  }
  const projectActivityKey = activityTabKeys[projectActivityIndex].key;
  const projectCreateActivityKey = activityTabKeys[projectCreateActivityIndex].key;
  const paymentActivityKey = activityTabKeys[paymentActivityIndex].key;
  await page.locator(`[data-activity-page-key="${projectActivityKey}"]`).click();
  await page.waitForURL((url) => url.pathname === `/r/project.project/${target.project_record_id}`, { timeout: 15000 });
  const retainedAfterProjectActivation = await activityTabLabels.count();
  await page.locator(`[data-activity-page-key="${paymentActivityKey}"]`).click();
  await page.waitForURL((url) => url.pathname === new URL(paymentRoute).pathname, { timeout: 15000 });
  const retainedAfterPaymentActivation = await activityTabLabels.count();
  const activityTabJourney = {
    pages: activityTabKeys,
    projectUrl: `${frontendUrl}/r/project.project/${target.project_record_id}`,
    paymentUrl: paymentRoute,
    retainedAfterProjectActivation,
    retainedAfterPaymentActivation,
  };
  if (retainedAfterProjectActivation !== activityTabKeys.length
    || retainedAfterPaymentActivation !== activityTabKeys.length) {
    throw new Error(`activity page activation collapsed independent pages: ${JSON.stringify(activityTabJourney)}`);
  }
  const unsavedProjectName = '活动页签未保存草稿保留验证';
  await page.locator(`[data-activity-page-key="${projectCreateActivityKey}"]`).click();
  await page.waitForURL((url) => url.pathname === new URL(projectCreateRoute).pathname, { timeout: 15000 });
  const projectNameInput = page.locator('[data-field-name="name"] input').first();
  await projectNameInput.fill(unsavedProjectName);
  await page.locator(`[data-activity-page-key="${paymentActivityKey}"]`).click();
  await page.waitForURL((url) => url.pathname === new URL(paymentRoute).pathname, { timeout: 15000 });
  await page.locator(`[data-activity-page-key="${projectCreateActivityKey}"]`).click();
  await page.waitForURL((url) => url.pathname === new URL(projectCreateRoute).pathname, { timeout: 15000 });
  const retainedUnsavedProjectName = await projectNameInput.inputValue();
  const retainedAfterDraftRoundtrip = await activityTabLabels.count();
  const activityDraftJourney = {
    projectCreateActivityKey,
    unsavedProjectName,
    retainedUnsavedProjectName,
    retainedAfterDraftRoundtrip,
  };
  if (retainedUnsavedProjectName !== unsavedProjectName
    || retainedAfterDraftRoundtrip !== activityTabKeys.length) {
    throw new Error(`activity page lost its unsaved business draft: ${JSON.stringify(activityDraftJourney)}`);
  }
  await page.locator(`[data-activity-page-key="${projectCreateActivityKey}"] .activity-page-tab-close`).click();
  const dirtyCloseDialog = page.getByRole('dialog').filter({ hasText: '确认关闭页面' });
  await dirtyCloseDialog.waitFor({ state: 'visible', timeout: 10000 });
  const dirtyCloseDialogText = String(await dirtyCloseDialog.textContent() || '').trim();
  if (!dirtyCloseDialogText.includes('存在未保存修改') || !dirtyCloseDialogText.includes('关闭后这些修改将丢失')) {
    throw new Error(`dirty activity page close warning is incomplete: ${dirtyCloseDialogText}`);
  }
  await dirtyCloseDialog.getByRole('button', { name: '取消', exact: true }).click();
  await dirtyCloseDialog.waitFor({ state: 'hidden', timeout: 10000 });
  const retainedAfterDirtyCloseCancel = await activityTabLabels.count();
  const retainedAfterDirtyCloseCancelName = await projectNameInput.inputValue();
  const activityDirtyCloseJourney = {
    warning: dirtyCloseDialogText,
    retainedAfterDirtyCloseCancel,
    retainedAfterDirtyCloseCancelName,
    urlAfterCancel: page.url(),
  };
  if (retainedAfterDirtyCloseCancel !== activityTabKeys.length
    || retainedAfterDirtyCloseCancelName !== unsavedProjectName
    || new URL(page.url()).pathname !== new URL(projectCreateRoute).pathname) {
    throw new Error(`cancelling dirty activity page close lost page state: ${JSON.stringify(activityDirtyCloseJourney)}`);
  }
  await page.locator(`[data-activity-page-key="${projectActivityKey}"] .activity-page-tab-close`).click();
  await page.waitForFunction((expectedKey) => (
    !document.querySelector(`[data-activity-page-key="${expectedKey}"]`)
  ), projectActivityKey, { timeout: 10000 });
  const retainedAfterInactiveCleanClose = await activityTabLabels.count();
  const retainedAfterInactiveCleanCloseName = await projectNameInput.inputValue();
  const activityIndependentCloseJourney = {
    closedActivityKey: projectActivityKey,
    retainedAfterInactiveCleanClose,
    retainedAfterInactiveCleanCloseName,
    activeUrl: page.url(),
  };
  if (retainedAfterInactiveCleanClose !== activityTabKeys.length - 1
    || retainedAfterInactiveCleanCloseName !== unsavedProjectName
    || new URL(page.url()).pathname !== new URL(projectCreateRoute).pathname) {
    throw new Error(`closing inactive clean activity page polluted active draft: ${JSON.stringify(activityIndependentCloseJourney)}`);
  }
  await page.locator(`[data-activity-page-key="${paymentActivityKey}"]`).click();
  await page.waitForURL((url) => url.pathname === new URL(paymentRoute).pathname, { timeout: 15000 });
  await page.setViewportSize({ width: 390, height: 844 });
  const mobileResults = {};
  for (const [key, currentRoute, selector] of [
    ['projectCreate', projectCreateRoute, `[data-product-page-mode="form"][data-form-model="project.project"][data-form-record="new"]`],
    ['workspace', workspaceRoute, `[data-product-page-mode="form"][data-form-model="project.project"][data-form-record="${target.project_record_id}"]`],
    ['payment', paymentRoute, `[data-product-page-mode="form"][data-form-model="payment.request"][data-form-record="${target.payment_record_id}"]`],
  ]) {
    await page.goto(currentRoute, { waitUntil: 'domcontentloaded', timeout: 45000 });
    const mobileSurface = page.locator(selector);
    await mobileSurface.waitFor({ state: 'visible', timeout: 45000 });
    await page.waitForFunction(() => (
      document.querySelectorAll('[data-contract-form-driver]').length
      + document.querySelectorAll('[data-contract-form-driver-error]').length === 1
    ), undefined, { timeout: 45000 });
    mobileResults[key] = await captureHeaderPresentation(mobileSurface);
    if (mobileResults[key].commandBars !== 1 || mobileResults[key].scButtons < 1
      || mobileResults[key].primaryActions > 1 || mobileResults[key].rawButtonsOutsideWorkflow !== 0
      || mobileResults[key].mobileDisclosures > 1
      || (mobileResults[key].mobileDisclosures === 1 && mobileResults[key].mobileActionKeys.length === 0)
      || mobileResults[key].horizontalOverflow) {
      throw new Error(`${key} mobile header boundary failed: ${JSON.stringify(mobileResults[key])}`);
    }
  }
  console.log('LOCAL_DEV_CONTRACT_DRIVER_JSON=' + JSON.stringify({
    project: projectResult,
    workspace: workspaceResult,
    payment: paymentResult,
    activityTabJourney,
    activityDraftJourney,
    activityDirtyCloseJourney,
    activityIndependentCloseJourney,
    mobile: mobileResults,
    contractPresentations,
    mutations,
    executeRequests,
    followerUpdates,
    followerListResponses,
    attachmentMutations,
    messageMutations,
    activityMutations,
    userSearchRequests,
    activityCancelJourneys: [workspaceActivityCancelJourney, paymentActivityCancelJourney],
    intentFailures,
    browserErrors,
  }));
  if (mutations.length) throw new Error('read-only project create driver probe observed mutation');
  if (executeRequests.length) throw new Error(`read-only browser driver probe observed execute request: ${executeRequests.length}`);
  if (attachmentMutations.filter((row) => row.intent === 'file.upload').length !== 2
    || attachmentMutations.filter((row) => row.intent === 'file.download').length !== 2
    || attachmentMutations.filter((row) => row.intent === 'chatter.attachment.delete').length !== 4) {
    throw new Error(`attachment lifecycle journey did not preserve dual-model mutation symmetry: ${JSON.stringify(attachmentMutations)}`);
  }
  if (messageMutations.filter((row) => row.intent === 'chatter.message.delete').length !== 6) {
    throw new Error(`message delete journey did not preserve dual-model mutation symmetry: ${JSON.stringify(messageMutations)}`);
  }
  const replyMutations = messageMutations.filter((row) => row.intent === 'chatter.post');
  if (replyMutations.length !== 6
    || replyMutations.filter((row) => Number(row.parentId)).length !== 2
    || replyMutations.filter((row) => !Number(row.parentId)).length !== 4) {
    throw new Error(`message reply journey did not preserve dual-model parent authority: ${JSON.stringify(messageMutations)}`);
  }
  const mentionedCreateMessages = replyMutations.filter((row) => (
    String(row.body || '').includes('codex-create-action-journey-message-')
    && Array.isArray(row.mentionUserIds)
    && row.mentionUserIds.some((id) => Number(id) > 0)
  ));
  if (mentionedCreateMessages.length !== 2) {
    throw new Error(`message mention journey did not preserve dual-model user identity: ${JSON.stringify(messageMutations)}`);
  }
  if (activityMutations.filter((row) => row.intent === 'chatter.activity.schedule').length !== 2
    || activityMutations.filter((row) => row.intent === 'chatter.activity.update' && row.action === 'cancel').length !== 4) {
    throw new Error(`activity cancel journey did not preserve dual-model mutation symmetry: ${JSON.stringify(activityMutations)}`);
  }
  if (activityMutations.filter((row) => row.intent === 'chatter.activity.schedule' && Number(row.userId) > 0).length !== 2) {
    throw new Error(`activity assignee journey did not preserve dual-model user identity: ${JSON.stringify(activityMutations)}`);
  }
  if (userSearchRequests.length < 2 || userSearchRequests.some((row) => Number(row.limit) !== 20)) {
    throw new Error(`collaboration user search did not use the governed dual-model boundary: ${JSON.stringify(userSearchRequests)}`);
  }
  if (browserErrors.length) throw new Error(`browser errors observed: ${JSON.stringify(browserErrors)}`);
} catch (error) {
  const diagnostics = {
    url: page.url(),
    surfaces: await page.locator('[data-product-page-mode], [data-contract-form-driver-error]').evaluateAll((nodes) => (
      nodes.map((node) => ({
        tag: node.tagName,
        text: (node.textContent || '').trim().slice(0, 300),
        attributes: Object.fromEntries([...node.attributes].map((attribute) => [attribute.name, attribute.value])),
      }))
    )).catch(() => []),
    collaboration: await page.locator('[data-professional-collaboration-component="panel"]').evaluateAll((nodes) => (
      nodes.map((node) => ({
        attrs: Object.fromEntries([...node.attributes].map((attribute) => [attribute.name, attribute.value])),
        chips: [...node.querySelectorAll('.chips button')].map((button) => ({
          text: (button.textContent || '').trim(), title: button.getAttribute('title'), disabled: button.disabled,
        })),
        composers: node.querySelectorAll('[data-professional-collaboration-component="composer"]').length,
        submitDisabled: [...node.querySelectorAll('.native-chatter-compose-actions button')].map((button) => button.disabled),
      }))
    )).catch(() => []),
    followers: await page.locator('[data-professional-collaboration-component="followers"]').evaluateAll((nodes) => (
      nodes.map((node) => ({
        attrs: Object.fromEntries([...node.attributes].map((attribute) => [attribute.name, attribute.value])),
        text: String(node.textContent || '').replace(/\s+/g, ' ').trim(),
        buttons: [...node.querySelectorAll('button')].map((button) => (button.textContent || '').trim()),
      }))
    )).catch(() => []),
    followerListResponses,
    browserErrors,
    intentFailures,
    executeRequests,
    mutations,
  };
  console.error('LOCAL_DEV_CONTRACT_DRIVER_FAILURE=' + JSON.stringify(diagnostics));
  throw error;
} finally {
  await browser.close();
}
