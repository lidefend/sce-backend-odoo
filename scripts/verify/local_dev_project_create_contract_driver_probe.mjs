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
  if (['create', 'write', 'unlink'].includes(op)) mutations.push({ intent, op });
});
page.on('response', async (response) => {
  if (!response.url().includes('/api/v1/intent')) return;
  let request = {};
  try { request = JSON.parse(response.request().postData() || '{}'); } catch {}
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
    currentTaskText: await surface.locator('[data-floorplan-region="current-task"]').allTextContents(),
    riskRegions: await surface.locator('[data-floorplan-region="risk"]').count(),
    contractActions: [...contractActions],
    header: await captureHeaderPresentation(surface),
  };
  const projectPresentation = contractPresentations
    .filter((row) => row.actionId === String(target.action_id))
    .at(-1);
  if (projectPresentation?.structureVersion !== '1.1' || projectPresentation?.presentationMode !== 'task') {
    throw new Error(`project initiation did not resolve task presentation: ${JSON.stringify(projectPresentation)}`);
  }
  if (projectResult.taskPage !== 1 || projectResult.nativeStructure !== 0) {
    throw new Error(`project initiation did not render Floorplan: ${JSON.stringify(projectResult)}`);
  }
  if (projectResult.currentTaskText.length !== 1 || projectResult.riskRegions !== 1
    || !projectResult.currentTaskText[0].includes('补齐立项必填信息')) {
    throw new Error(`project initiation task and risk guidance is incomplete: ${JSON.stringify(projectResult)}`);
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
  const workspaceResult = {
    url: page.url(),
    drivers: await workspaceSurface.locator('[data-contract-form-driver]').count(),
    errors: await workspaceSurface.locator('[data-contract-form-driver-error]').allTextContents(),
    taskPage: await workspaceSurface.locator('[data-object-task-page]').count(),
    nativeStructure: await workspaceSurface.locator('[data-native-contract-structure]').count(),
    notebookPages: await workspaceSurface.locator('[data-native-contract-structure] .native-tabs .native-tab').count(),
    readonlyRelationFacts: await workspaceSurface.locator('.o2m-readonly-fact dd').allTextContents(),
    readonlyRelationRows: await workspaceSurface.locator('.o2m-readonly-row').evaluateAll((rows) => rows.map((row) => (
      [...row.querySelectorAll('.o2m-readonly-fact dd')].map((node) => (node.textContent || '').trim())
    ))),
    readonlyRelationEmptyLabels: await workspaceSurface.locator('.relation-readonly-empty').allTextContents(),
    header: await captureHeaderPresentation(workspaceSurface),
  };
  const workspacePresentation = contractPresentations
    .filter((row) => row.actionId === String(target.workspace_action_id))
    .at(-1);
  if (workspacePresentation?.structureVersion !== '1.1' || workspacePresentation?.presentationMode !== 'workspace') {
    throw new Error(`project workspace did not resolve workspace presentation: ${JSON.stringify(workspacePresentation)}`);
  }
  if (
    workspaceResult.drivers !== 1
    || workspaceResult.errors.length !== 0
    || workspaceResult.taskPage !== 0
    || workspaceResult.nativeStructure !== 1
    || workspaceResult.notebookPages !== 11
  ) {
    throw new Error(`project workspace did not preserve native notebook structure: ${JSON.stringify(workspaceResult)}`);
  }
  if (workspaceResult.header.commandBars !== 1 || workspaceResult.header.scButtons < 1
    || workspaceResult.header.primaryActions > 1 || workspaceResult.header.rawButtonsOutsideWorkflow !== 0) {
    throw new Error(`project workspace header primitive boundary failed: ${JSON.stringify(workspaceResult.header)}`);
  }
  if (workspaceResult.readonlyRelationFacts.some((value) => /^\s*\d+\s*,/.test(value) || /^#\d+$/.test(value))) {
    throw new Error(`project workspace leaked raw relation ids: ${JSON.stringify(workspaceResult.readonlyRelationFacts)}`);
  }
  if (workspaceResult.readonlyRelationRows.some((values) => values.every((value) => !value || value === '—'))) {
    throw new Error(`project workspace rendered empty readonly relation rows: ${JSON.stringify(workspaceResult.readonlyRelationRows)}`);
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
    relationInteractionCount: await paymentSurface.locator(
      '[data-floorplan-region="relation"] input[type="file"], [data-floorplan-region="relation"] button:visible',
    ).count(),
    header: await captureHeaderPresentation(paymentSurface),
  };
  if (paymentDrivers !== 1 || paymentErrors.length !== 0) {
    throw new Error(`payment record canonical driver did not load: ${JSON.stringify(paymentResult)}`);
  }
  if (paymentResult.header.commandBars !== 1 || paymentResult.header.scButtons < 1
    || paymentResult.header.primaryActions !== 1 || paymentResult.header.rawButtonsOutsideWorkflow !== 0) {
    throw new Error(`payment task header primitive boundary failed: ${JSON.stringify(paymentResult.header)}`);
  }
  if (paymentResult.visibleFieldNames.length === 0
    || new Set(paymentResult.visibleFieldNames).size !== paymentResult.visibleFieldNames.length) {
    throw new Error(`payment page repeated canonical facts: ${JSON.stringify(paymentResult.visibleFieldNames)}`);
  }
  if (paymentResult.emptyReadonlyRelations !== 0 || paymentResult.relationInteractionCount < 1) {
    throw new Error(`payment relation information efficiency is incomplete: ${JSON.stringify(paymentResult)}`);
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
    browserErrors,
  }));
  if (mutations.length) throw new Error('read-only project create driver probe observed mutation');
  if (executeRequests.length) throw new Error(`read-only browser driver probe observed execute request: ${executeRequests.length}`);
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
    browserErrors,
    executeRequests,
    mutations,
  };
  console.error('LOCAL_DEV_CONTRACT_DRIVER_FAILURE=' + JSON.stringify(diagnostics));
  throw error;
} finally {
  await browser.close();
}
