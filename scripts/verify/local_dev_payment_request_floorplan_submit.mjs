import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';

const target = JSON.parse(process.env.LOCAL_DEV_PAYMENT_FLOORPLAN_JSON || '{}');
const frontendUrl = process.env.FRONTEND_URL || '';
const database = process.env.DB_NAME || '';
const password = process.env.E2E_PASSWORD || '';
const login = String(target?.user?.login || '');
const actionId = Number(target?.action?.id || 0);
const menuId = Number(target?.menu?.id || 0);
const record = target?.actionable_record || {};
const candidateInventory = Array.isArray(target?.candidate_inventory) ? target.candidate_inventory : [];
const recordId = Number(record.id || 0);
const outputDir = path.resolve('artifacts/playwright/local-dev-payment-request-floorplan-submit');
let currentStage = 'bootstrap';
let lastLocatorMatch = { label: '', count: -1 };
const mutationRequestCounts = {
  projectCreate: 0,
  paymentCreate: 0,
  paymentWrite: 0,
  executeButton: 0,
};
const relationQueryTrace = [];
const relationContextTrace = [];

function check(value, message, details = undefined) {
  if (value) return;
  throw new Error(`${message}${details === undefined ? '' : ` ${JSON.stringify(details)}`}`);
}

function enterStage(stage) {
  currentStage = stage;
}

async function runtimeDiagnostics(owner, details = {}) {
  const activeForms = await owner.locator('[data-product-page-mode="form"]').evaluateAll((nodes) => nodes.map((node) => ({
    visible: node instanceof HTMLElement && node.offsetParent !== null,
    model: String(node.getAttribute('data-form-model') || ''),
    record: String(node.getAttribute('data-form-record') || ''),
    actionId: Number(node.getAttribute('data-form-action-id') || 0),
    menuId: Number(node.getAttribute('data-form-menu-id') || 0),
  }))).catch(() => []);
  return {
    stage: currentStage,
    url: owner.url(),
    activeForms,
    visibleDialogs: await owner.locator('[role="dialog"]:visible').count().catch(() => -1),
    lastLocatorMatch,
    mutationRequestCounts: { ...mutationRequestCounts },
    relationQueryTrace: relationQueryTrace.slice(-50),
    relationContextTrace: relationContextTrace.slice(-50),
    ...details,
  };
}

async function requireUnique(owner, locator, label, options = {}) {
  const state = options.state || 'visible';
  const timeout = Number(options.timeout || 15000);
  try {
    await locator.waitFor({ state, timeout });
  } catch (error) {
    lastLocatorMatch = { label, count: await locator.count().catch(() => -1) };
    throw new Error(`${label} did not reach ${state}: ${JSON.stringify(await runtimeDiagnostics(owner, {
      cause: error instanceof Error ? error.message : String(error),
      requestCounts: options.requestCounts || {},
    }))}`);
  }
  const count = await locator.count();
  lastLocatorMatch = { label, count };
  check(count === 1, `${label} identity is not unique`, await runtimeDiagnostics(owner, {
    matchCount: count,
    requestCounts: options.requestCounts || {},
  }));
  if (state === 'visible' || options.visible === true) {
    check(await locator.isVisible(), `${label} is not visible`, await runtimeDiagnostics(owner));
  }
  if (options.enabled === true) {
    check(await locator.isEnabled(), `${label} is not enabled`, await runtimeDiagnostics(owner));
  }
  return locator;
}

async function waitForViewport(page, width) {
  await page.waitForFunction((expectedWidth) => (
    window.innerWidth === expectedWidth && document.documentElement.clientWidth === expectedWidth
  ), width, { timeout: 15000 });
}

function valuesForKey(value, key, output = []) {
  if (Array.isArray(value)) {
    value.forEach((item) => valuesForKey(item, key, output));
    return output;
  }
  if (!value || typeof value !== 'object') return output;
  for (const [itemKey, itemValue] of Object.entries(value)) {
    if (itemKey === key) output.push(itemValue);
    valuesForKey(itemValue, key, output);
  }
  return output;
}

function intentOf(response) {
  if (!response.url().includes('/api/v1/intent')) return '';
  try { return String(JSON.parse(response.request().postData() || '{}').intent || ''); } catch { return ''; }
}

function isListDataResponse(response, expectedModel = '') {
  if (intentOf(response) !== 'api.data') return false;
  try {
    const body = JSON.parse(response.request().postData() || '{}');
    return String(body?.params?.op || body?.op || '') === 'list'
      && (!expectedModel || String(body?.params?.model || '') === expectedModel);
  } catch {
    return false;
  }
}

function isPaymentWriteBody(body) {
  return String(body?.intent || '') === 'api.data'
    && String(body?.params?.op || body?.op || '') === 'write'
    && String(body?.params?.model || '') === 'payment.request';
}

function isPaymentCreateBody(body) {
  return String(body?.intent || '') === 'api.data'
    && String(body?.params?.op || body?.op || '') === 'create'
    && String(body?.params?.model || '') === 'payment.request';
}

function collectRelationAuthorities(value, output = {}) {
  if (Array.isArray(value)) {
    value.forEach((item) => collectRelationAuthorities(item, output));
    return output;
  }
  if (!value || typeof value !== 'object') return output;
  const fieldInfo = value.fieldInfo && typeof value.fieldInfo === 'object' ? value.fieldInfo : {};
  const componentConfig = value.componentConfig && typeof value.componentConfig === 'object'
    ? value.componentConfig
    : {};
  const entry = value.relation_entry || value.relationEntry
    || fieldInfo.relation_entry || fieldInfo.relationEntry
    || componentConfig.relation_entry || componentConfig.relationEntry;
  const fieldName = String(
    value.fieldCode || value.field_code || value.field || value.name
    || fieldInfo.fieldCode || fieldInfo.field_code || fieldInfo.name || '',
  ).trim();
  if (fieldName && entry && typeof entry === 'object' && !Array.isArray(entry)) {
    output[fieldName] = {
      canCreate: entry.can_create === true,
      createMode: String(entry.create_mode || '').trim(),
      actionId: Number(entry.action_id || 0),
      menuId: Number(entry.menu_id || 0),
      reasonCode: String(entry.reason_code || '').trim(),
    };
  }
  Object.values(value).forEach((item) => collectRelationAuthorities(item, output));
  return output;
}

function assertRelationCreateAuthority(metrics, authorities, label) {
  for (const capability of metrics.many2oneCapabilities) {
    const authority = authorities[capability.fieldName];
    if (!authority) continue;
    const exposesCreate = capability.actions.some((text) => /新建|新增/.test(text));
    const authorizedPageCreate = authority.canCreate
      && ['page', 'dialog'].includes(authority.createMode)
      && authority.actionId > 0;
    check(exposesCreate === authorizedPageCreate,
      `${label} create entry disagrees with Contract V2 authority`, {
        fieldName: capability.fieldName,
        actions: capability.actions,
        authority,
      });
  }
}

function relationRecordLabel(record) {
  return String(record?.display_name || record?.name || '').trim();
}

async function chooseUniqueRelationOption(
  page,
  surface,
  { fieldName, relationModel, query, expectedLabel },
) {
  enterStage(`relation-select:${fieldName}`);
  const field = await requireUnique(page, surface.locator(`[data-field-name="${fieldName}"]`), `${fieldName} field`);
  const input = await requireUnique(page, field.locator('input'), `${fieldName} input`, { enabled: true });
  const initialValue = String(await input.inputValue()).trim();
  if (initialValue) {
    check(initialValue === expectedLabel, `${fieldName} has an unexpected preselected relation`, {
      relationModel,
      expectedLabel,
      initialValue,
    });
    return;
  }
  const fieldType = String(await field.getAttribute('data-field-type') || '').toLowerCase();
  if (fieldType === 'selection') {
    await input.click();
    const option = await requireUnique(
      page,
      page.locator('.t-select-option:visible').filter({ hasText: query }),
      `${fieldName} selection option ${query}`,
      { enabled: true, timeout: 30000 },
    );
    await option.click();
    return;
  }
  check(fieldType === 'many2one', 'relation acceptance field has an unexpected canonical type', { fieldName, fieldType });
  await input.click();
  const urlBeforeInput = page.url();
  const traceIdentity = `${fieldName}:${relationModel}:${query}:${relationQueryTrace.length}`;
  const traceRequest = (request) => {
    if (request.method() !== 'POST' || !request.url().includes('/api/v1/intent')) return;
    let body = {};
    try { body = JSON.parse(request.postData() || '{}'); } catch {}
    if (String(body?.intent || '') !== 'api.data'
      || String(body?.params?.op || body?.op || '') !== 'list') return;
    relationQueryTrace.push({
      traceIdentity,
      phase: 'request',
      fieldName,
      model: String(body?.params?.model || ''),
      searchTerm: String(body?.params?.search_term || ''),
      url: page.url(),
    });
  };
  const traceResponse = (response) => {
    if (!isListDataResponse(response)) return;
    let body = {};
    try { body = JSON.parse(response.request().postData() || '{}'); } catch {}
    void response.json().then((payload) => {
      const recordArrays = valuesForKey(payload, 'records').filter(Array.isArray);
      relationQueryTrace.push({
        traceIdentity,
        phase: 'response',
        fieldName,
        model: String(body?.params?.model || ''),
        searchTerm: String(body?.params?.search_term || ''),
        status: response.status(),
        candidates: recordArrays.flat().map((record) => ({
          id: Number(record?.id || 0),
          label: relationRecordLabel(record),
        })),
        url: page.url(),
      });
    }).catch((error) => {
      relationQueryTrace.push({
        traceIdentity,
        phase: 'response_decode_failed',
        fieldName,
        model: String(body?.params?.model || ''),
        searchTerm: String(body?.params?.search_term || ''),
        status: response.status(),
        error: error instanceof Error ? error.message : String(error),
        url: page.url(),
      });
    });
  };
  page.on('request', traceRequest);
  page.on('response', traceResponse);
  relationContextTrace.push({ traceIdentity, phase: 'before_fill', url: urlBeforeInput });
  const optionResponsePromise = page.waitForResponse((response) => {
    if (!isListDataResponse(response, relationModel)) return false;
    try {
      const body = JSON.parse(response.request().postData() || '{}');
      return String(body?.params?.search_term || '') === query;
    } catch {
      return false;
    }
  }, { timeout: 30000 });
  let optionResponse;
  try {
    await input.fill(query);
    relationContextTrace.push({ traceIdentity, phase: 'after_fill', url: page.url() });
    optionResponse = await optionResponsePromise;
    relationContextTrace.push({ traceIdentity, phase: 'matched_response', url: page.url() });
  } catch (error) {
    throw new Error(`${fieldName} relation query did not reach its exact response: ${JSON.stringify(await runtimeDiagnostics(page, {
      cause: error instanceof Error ? error.message : String(error),
      expected: { fieldName, relationModel, query, expectedLabel },
      traceIdentity,
    }))}`);
  } finally {
    page.off('request', traceRequest);
    page.off('response', traceResponse);
  }
  let optionRequest = {};
  try { optionRequest = JSON.parse(optionResponse.request().postData() || '{}'); } catch {}
  check(page.url() === urlBeforeInput, `${fieldName} changed route or business context before option selection`, {
    query,
    relationModel,
    before: urlBeforeInput,
    after: page.url(),
    request: optionRequest?.params || {},
  });
  check(optionResponse.status() === 200, `${fieldName} relation query failed`, {
    query,
    status: optionResponse.status(),
    body: await optionResponse.text(),
  });
  const optionPayload = await optionResponse.json();
  const recordArrays = valuesForKey(optionPayload, 'records').filter(Array.isArray);
  check(recordArrays.length === 1, `${fieldName} relation response has no unique records carrier`, {
    query,
    relationModel,
    recordsCarriers: recordArrays.length,
  });
  const matchingRecords = recordArrays[0].filter((record) => relationRecordLabel(record) === expectedLabel);
  check(matchingRecords.length === 1, `${fieldName} relation response target is not unique`, {
    query,
    relationModel,
    expectedLabel,
    matches: matchingRecords.map((record) => ({ id: record?.id, label: relationRecordLabel(record) })),
    candidates: recordArrays[0].map((record) => ({ id: record?.id, label: relationRecordLabel(record) })),
  });
  const targetId = Number(matchingRecords[0]?.id || 0);
  check(Number.isInteger(targetId) && targetId > 0, `${fieldName} relation target has no positive integer id`, {
    query,
    relationModel,
    expectedLabel,
    targetId,
  });
  const optionPanel = await requireUnique(
    page,
    field.locator('.many2one-option-panel:visible'),
    `${fieldName} option panel`,
    { timeout: 15000 },
  );
  const option = await requireUnique(
    page,
    optionPanel.getByRole('option', { name: expectedLabel, exact: true }),
    `${fieldName} relation option ${expectedLabel}#${targetId}`,
    {
      enabled: true,
      timeout: 15000,
      requestCounts: {
        relationModel: String(optionRequest?.params?.model || ''),
        searchTerm: String(optionRequest?.params?.search_term || ''),
      },
    },
  );
  check((await option.innerText()).trim() === expectedLabel,
    `${fieldName} relation option label disagrees with the response record`, {
      expectedLabel,
      actualLabel: (await option.innerText()).trim(),
      targetId,
    });
  await option.click();
  await page.waitForFunction(({ expectedField, expectedValue }) => {
    const activeInputs = [...document.querySelectorAll(`[data-product-page-mode="form"] [data-field-name="${expectedField}"] input`)]
      .filter((node) => node instanceof HTMLInputElement && node.offsetParent !== null);
    return activeInputs.length === 1 && activeInputs[0].value === expectedValue;
  }, { expectedField: fieldName, expectedValue: expectedLabel }, { timeout: 30000 });
}

async function collectSaveButtonInventory(page) {
  return page.locator('[data-action-ref="form.save"]').evaluateAll((nodes) => nodes.map((node, index) => {
    const form = node.closest('[data-product-page-mode="form"]');
    return {
      index,
      text: String(node.textContent || '').replace(/\s+/g, ' ').trim(),
      visible: node instanceof HTMLElement && node.offsetParent !== null,
      disabled: node instanceof HTMLButtonElement ? node.disabled : false,
      tier: String(node.getAttribute('data-action-tier') || ''),
      model: String(form?.getAttribute('data-form-model') || ''),
      record: String(form?.getAttribute('data-form-record') || ''),
      actionId: Number(form?.getAttribute('data-form-action-id') || 0),
      menuId: Number(form?.getAttribute('data-form-menu-id') || 0),
    };
  }));
}

async function unlinkRecords(page, model, ids, authHeaders) {
  if (!ids.length || !authHeaders.authorization) return { status: 0, body: { ok: false, skipped: true } };
  return page.evaluate(async ({ recordModel, recordIds, headers }) => {
    const db = String(headers['x-odoo-db'] || '');
    const response = await fetch(`/api/v1/intent${db ? `?db=${encodeURIComponent(db)}` : ''}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: String(headers.authorization || ''),
        'X-Odoo-DB': db,
        'x-tenant': String(headers['x-tenant'] || ''),
      },
      body: JSON.stringify({
        intent: 'api.data.unlink',
        params: { model: recordModel, ids: recordIds },
      }),
    });
    return { status: response.status, body: await response.json() };
  }, { recordModel: model, recordIds: ids, headers: authHeaders });
}

async function verifyAuthorizedProjectRelationCreate(browser) {
  const projectUser = target?.project_create_user || {};
  const projectEntry = target?.project_create_entry || {};
  check(projectUser.login && projectUser.can_create_project === true,
    'governed project-create user authority is missing', projectUser);
  check(Number(projectEntry.action_id || 0) > 0 && Number(projectEntry.menu_id || 0) > 0,
    'governed project-create action authority is missing', projectEntry);
  const projectContext = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
  const projectPage = await projectContext.newPage();
  const projectErrors = [];
  const projectCreates = [];
  const parentPaymentCreates = [];
  const projectObservedRequests = [];
  const projectContractResponses = [];
  const paymentAuthorityTasks = [];
  const paymentAuthoritySnapshots = [];
  let projectAuthHeaders = {};
  let projectCreatedId = 0;
  let parentPaymentId = 0;
  let cleanup = {};
  projectPage.on('console', (message) => {
    if (message.type() === 'error' && !message.text().includes('favicon')) projectErrors.push(message.text());
  });
  projectPage.on('pageerror', (error) => projectErrors.push(error.message));
  projectPage.on('response', (response) => {
    if (intentOf(response) !== 'ui.contract.v2') return;
    let requestBody = {};
    try { requestBody = JSON.parse(response.request().postData() || '{}'); } catch {}
    const contractModel = String(requestBody?.params?.model || '');
    if (contractModel === 'project.project') {
      void response.json().then((body) => projectContractResponses.push(body)).catch(() => undefined);
      return;
    }
    if (contractModel === 'payment.request') {
      const task = response.json().then((body) => {
        const authorities = collectRelationAuthorities(body);
        if (authorities.project_id) paymentAuthoritySnapshots.push(authorities.project_id);
      }).catch(() => undefined);
      paymentAuthorityTasks.push(task);
    }
  });
  projectPage.on('request', (request) => {
    if (request.method() !== 'POST' || !request.url().includes('/api/v1/intent')) return;
    let body = {};
    try { body = JSON.parse(request.postData() || '{}'); } catch {}
    projectObservedRequests.push({ intent: String(body?.intent || ''), params: body?.params || {} });
    if (String(body?.intent || '') !== 'api.data' || String(body?.params?.op || body?.op || '') !== 'create') return;
    const modelName = String(body?.params?.model || '');
    if (modelName === 'project.project') {
      mutationRequestCounts.projectCreate += 1;
      projectCreates.push({ intent: body.intent, params: body.params });
    }
    if (modelName === 'payment.request') {
      mutationRequestCounts.paymentCreate += 1;
      parentPaymentCreates.push({ intent: body.intent, params: body.params });
    }
    const headers = request.headers();
    projectAuthHeaders = Object.fromEntries(
      ['authorization', 'x-odoo-db', 'x-tenant']
        .filter((key) => headers[key])
        .map((key) => [key, headers[key]]),
    );
  });
  try {
    enterStage('project-dialog:login');
    await projectPage.goto(`${frontendUrl}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
    const usernameInput = await requireUnique(projectPage, projectPage.locator('#login-username'), 'project login username', { enabled: true });
    const passwordInput = await requireUnique(projectPage, projectPage.locator('#login-password'), 'project login password', { enabled: true });
    const databaseInput = await requireUnique(projectPage, projectPage.getByLabel(/数据库/), 'project login database');
    await usernameInput.fill(String(projectUser.login));
    await passwordInput.fill(password);
    if (!(await databaseInput.isDisabled())) await databaseInput.fill(database);
    const projectLogin = await requireUnique(
      projectPage,
      projectPage.getByRole('button', { name: /^登录$/ }),
      'project login action',
      { enabled: true },
    );
    await projectLogin.click();
    await projectPage.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 30000 });
    enterStage('project-dialog:parent-payment-create');
    await projectPage.goto(`${frontendUrl}/f/payment.request/new?menu_id=${menuId}&action_id=${actionId}`, {
      waitUntil: 'domcontentloaded', timeout: 45000,
    });
    const paymentSurface = await requireUnique(
      projectPage,
      projectPage.locator(
        `[data-product-page-mode="form"][data-form-model="payment.request"][data-form-record="new"]`
        + `[data-form-action-id="${actionId}"][data-form-menu-id="${menuId}"]:visible`,
      ),
      'dialog journey parent payment form',
      { timeout: 45000 },
    );
    await paymentSurface.locator('[data-contract-form-driver]').waitFor({ timeout: 45000 });
    await paymentSurface.locator('.product-form-loading').waitFor({ state: 'detached', timeout: 45000 });
    await projectPage.waitForFunction((expectedLabel) => (
      new URL(window.location.href).searchParams.get('default_business_category_label') === expectedLabel
    ), '付款申请', { timeout: 30000 });
    await chooseUniqueRelationOption(projectPage, paymentSurface, {
      fieldName: 'business_category_id',
      relationModel: 'sc.business.category',
      query: '付款申请',
      expectedLabel: '付款申请',
    });
    await projectPage.waitForFunction(() => (
      new URL(window.location.href).searchParams.get('current_business_category_code') === 'finance.payment.apply.pay'
    ), undefined, { timeout: 30000 });
    await paymentSurface.locator('.product-form-loading').waitFor({ state: 'detached', timeout: 45000 });
    await Promise.all(paymentAuthorityTasks);
    const projectRelationAuthority = paymentAuthoritySnapshots.at(-1);
    check(projectRelationAuthority?.canCreate === true
      && projectRelationAuthority.createMode === 'dialog'
      && projectRelationAuthority.actionId === Number(projectEntry.action_id)
      && projectRelationAuthority.menuId === Number(projectEntry.menu_id),
    'project relation Contract V2 authority is incomplete or disagrees with the native override', {
      projectRelationAuthority,
      expected: projectEntry,
    });
    await chooseUniqueRelationOption(projectPage, paymentSurface, {
      fieldName: 'partner_id',
      relationModel: 'res.partner',
      query: '德阳',
      expectedLabel: '德阳智能制造产教融合项目',
    });
    const parentAmountInput = await requireUnique(
      projectPage,
      paymentSurface.locator('[data-field-name="amount"] input'),
      'parent payment amount input',
      { enabled: true },
    );
    await parentAmountInput.fill('37.25');
    const parentPartnerInput = await requireUnique(
      projectPage,
      paymentSurface.locator('[data-field-name="partner_id"] input'),
      'parent payment partner input',
      { enabled: true },
    );
    const parentPartnerBeforeDialog = await parentPartnerInput.inputValue();
    check(Boolean(String(parentPartnerBeforeDialog || '').trim()),
      'parent partner fixture did not resolve before opening the relation dialog');
    const projectField = await requireUnique(
      projectPage,
      paymentSurface.locator('[data-field-name="project_id"]'),
      'parent payment project field',
    );
    const parentUrlBeforeDialog = projectPage.url();

    // Exercise the nested cancel lifecycle before the successful create path:
    // search -> create dialog -> child cancel -> restored search context.
    const projectRelationInput = await requireUnique(
      projectPage,
      projectField.locator('input'),
      'parent payment project input',
      { enabled: true },
    );
    await projectRelationInput.click();
    enterStage('project-dialog:cancel-search');
    const searchEntry = await requireUnique(
      projectPage,
      projectField.locator('.many2one-action').filter({ hasText: /搜索/ }),
      'project search-more action',
      { enabled: true },
    );
    await searchEntry.click();
    const restoredSearchDialog = await requireUnique(
      projectPage,
      projectPage.locator('.relation-dialog[role="dialog"]:visible'),
      'project relation search dialog',
    );
    const searchKeywordInput = await requireUnique(
      projectPage,
      restoredSearchDialog.locator('.relation-dialog-search input'),
      'project relation search keyword',
      { enabled: true },
    );
    const cancelSearchKeyword = 'S69';
    await searchKeywordInput.fill(cancelSearchKeyword);
    const cancelSearchResponsePromise = projectPage.waitForResponse((response) => {
      if (!isListDataResponse(response)) return false;
      try {
        const body = JSON.parse(response.request().postData() || '{}');
        return String(body?.params?.model || '') === 'project.project'
          && String(body?.params?.search_term || '') === cancelSearchKeyword;
      } catch {
        return false;
      }
    }, { timeout: 30000 });
    const searchAction = await requireUnique(
      projectPage,
      restoredSearchDialog.getByRole('button', { name: /^搜索$/ }),
      'project relation search action',
      { enabled: true },
    );
    await searchAction.click();
    const cancelSearchResponse = await cancelSearchResponsePromise;
    check(cancelSearchResponse.status() === 200,
      'project relation search failed before the cancel lifecycle', await cancelSearchResponse.text());
    const searchResultRow = await requireUnique(
      projectPage,
      restoredSearchDialog.locator('.relation-dialog-table tbody tr:visible'),
      `project relation search result ${cancelSearchKeyword}`,
      { enabled: true },
    );
    await searchResultRow.click();
    const selectedSearchRowText = (await searchResultRow.innerText()).replace(/\s+/g, ' ').trim();
    const selectedSearchRowBeforeCreate = restoredSearchDialog.locator('.relation-dialog-row--active');
    await selectedSearchRowBeforeCreate.waitFor({ state: 'visible', timeout: 5000 });
    check(await selectedSearchRowBeforeCreate.count() === 1
      && (await selectedSearchRowBeforeCreate.innerText()).replace(/\s+/g, ' ').trim() === selectedSearchRowText,
    'project relation row selection was not established before opening the create dialog');
    const projectCreatesBeforeCancel = projectCreates.length;
    const searchCreateAction = await requireUnique(
      projectPage,
      restoredSearchDialog.getByRole('button', { name: /^(新建|新增)$/ }),
      'project relation search create action',
      { enabled: true },
    );
    await searchCreateAction.click();
    enterStage('project-dialog:cancel-child');
    const cancelDialogFrameElement = await requireUnique(
      projectPage,
      projectPage.locator('[data-relation-create-form]:visible'),
      'managed project cancel iframe',
      { timeout: 30000 },
    );
    const cancelDialogFrameHandle = await cancelDialogFrameElement.elementHandle();
    const cancelProjectFrame = await cancelDialogFrameHandle?.contentFrame();
    check(cancelProjectFrame, 'project relation cancel dialog iframe is unavailable');
    const cancelProjectSurface = await requireUnique(
      cancelProjectFrame,
      cancelProjectFrame.locator(
        `[data-product-page-mode="form"][data-form-model="project.project"][data-form-record="new"]`
        + `[data-form-action-id="${Number(projectEntry.action_id)}"]`
        + `[data-form-menu-id="${Number(projectEntry.menu_id)}"]:visible`,
      ),
      'managed cancel project form',
      { timeout: 45000 },
    );
    await cancelProjectSurface.locator('[data-contract-form-driver]').waitFor({ timeout: 45000 });
    await cancelProjectSurface.locator('.product-form-loading').waitFor({ state: 'detached', timeout: 45000 });
    const cancelAction = await requireUnique(
      cancelProjectFrame,
      cancelProjectSurface.locator('[data-form-secondary-action="cancel-edit"]'),
      'managed project cancel action',
      { enabled: true },
    );
    await cancelAction.click();
    await cancelDialogFrameElement.waitFor({ state: 'detached', timeout: 30000 });
    await restoredSearchDialog.waitFor({ state: 'visible', timeout: 15000 });
    check(projectPage.url() === parentUrlBeforeDialog,
      'project relation cancel changed the parent route', {
        before: parentUrlBeforeDialog,
        after: projectPage.url(),
      });
    check(await searchKeywordInput.inputValue() === cancelSearchKeyword,
      'project relation cancel did not restore the search keyword');
    const restoredSelectedRow = await requireUnique(
      projectPage,
      restoredSearchDialog.locator('.relation-dialog-row--active'),
      'restored selected project row',
    );
    check((await restoredSelectedRow.innerText())
      .replace(/\s+/g, ' ').trim() === selectedSearchRowText,
    'project relation cancel did not restore the selected search row');
    check(projectCreates.length === projectCreatesBeforeCancel,
      'project relation cancel emitted an unexpected create mutation', projectCreates);
    check(await paymentSurface.locator('[data-field-name="partner_id"] input').inputValue() === parentPartnerBeforeDialog
      && Number(await paymentSurface.locator('[data-field-name="amount"] input').inputValue()) === 37.25,
    'project relation cancel changed the parent unsaved form state');
    const restoredSearchCancel = await requireUnique(
      projectPage,
      restoredSearchDialog.getByRole('button', { name: /^取消$/ }),
      'restored project search cancel action',
      { enabled: true },
    );
    await restoredSearchCancel.click();
    await restoredSearchDialog.waitFor({ state: 'hidden', timeout: 15000 });

    await projectRelationInput.click();
    enterStage('project-dialog:success-child');
    const createEntry = await requireUnique(
      projectPage,
      projectField.locator('.many2one-action').filter({ hasText: /新建|新增/ }),
      'project create action',
      { enabled: true },
    );
    const createLabel = (await createEntry.innerText()).replace(/\s+/g, ' ').trim();
    await createEntry.click();
    const dialogFrameElement = await requireUnique(
      projectPage,
      projectPage.locator('[data-relation-create-form]:visible'),
      'managed project create iframe',
      { timeout: 30000 },
    );
    const dialogFrameHandle = await dialogFrameElement.elementHandle();
    const projectFrame = await dialogFrameHandle?.contentFrame();
    check(projectFrame, 'project relation dialog iframe is unavailable');
    await projectFrame.waitForURL((url) => url.pathname === '/f/project.project/new', { timeout: 30000 });
    const genericProjectSurface = projectFrame.locator(
      '[data-product-page-mode="form"][data-form-model="project.project"][data-form-record="new"]',
    );
    await genericProjectSurface.waitFor({ state: 'attached', timeout: 45000 });
    check(projectPage.url() === parentUrlBeforeDialog,
      'relation dialog must not navigate the parent payment form', {
        before: parentUrlBeforeDialog,
        after: projectPage.url(),
      });
    const projectSurfaceLocator = projectFrame.locator(
      `[data-product-page-mode="form"][data-form-model="project.project"][data-form-record="new"]`
      + `[data-form-action-id="${Number(projectEntry.action_id)}"]`
      + `[data-form-menu-id="${Number(projectEntry.menu_id)}"]:visible`,
    );
    const projectFormIdentities = await genericProjectSurface.evaluateAll((nodes) => nodes.map((node) => ({
      model: String(node.getAttribute('data-form-model') || ''),
      record: String(node.getAttribute('data-form-record') || ''),
      actionId: Number(node.getAttribute('data-form-action-id') || 0),
      menuId: Number(node.getAttribute('data-form-menu-id') || 0),
    })));
    const projectSurface = await requireUnique(
      projectFrame,
      projectSurfaceLocator,
      'active managed project create form',
      {
        timeout: 45000,
        requestCounts: { projectContractResponses: projectContractResponses.length },
      },
    );
    check(projectFormIdentities.length >= 1, 'project form identity inventory is empty', projectFormIdentities);
    await projectSurface.locator('[data-contract-form-driver]').waitFor({ timeout: 45000 });
    await projectSurface.locator('.product-form-loading').waitFor({ state: 'detached', timeout: 45000 });
    const bodyText = (await projectFrame.locator('body').innerText()).replace(/\s+/g, ' ').trim();
    const route = new URL(projectFrame.url());
    const editableControls = await projectSurface.locator(
      'input:not([type="hidden"]):not(:disabled), textarea:not(:disabled), select:not(:disabled)',
    ).count();
    check(!/无权访问|权限不足|Access Denied/i.test(bodyText),
      'authorized project create entry opened an access-denied surface', { url: projectFrame.url(), bodyText });
    check(Number(route.searchParams.get('action_id') || 0) === Number(projectEntry.action_id),
      'project relation create did not use the governed initiation action', {
        url: projectFrame.url(), expected: projectEntry,
      });
    check(Number(route.searchParams.get('menu_id') || 0) === Number(projectEntry.menu_id),
      'project relation create did not use the governed initiation menu', {
        url: projectFrame.url(), expected: projectEntry,
      });
    check(route.searchParams.get('relation_create_mode') === 'dialog'
      && route.searchParams.get('relation_return_field') === 'project_id'
      && route.searchParams.get('relation_return_model') === 'payment.request'
      && Boolean(route.searchParams.get('relation_dialog_nonce')),
    'project relation dialog lost its scoped return authority', projectFrame.url());
    check(editableControls > 0, 'authorized project create surface is not editable', { editableControls, bodyText });
    await projectPage.screenshot({ path: path.join(outputDir, 'authorized-project-relation-create.png'), fullPage: true });
    const projectName = `级联项目验收 ${Date.now()}`;
    const nameInput = await requireUnique(
      projectFrame,
      projectSurface.locator('[data-field-name="name"] input'),
      'project name input',
      { enabled: true },
    );
    const projectNameOnchangePromise = projectPage.waitForResponse((response) => {
      if (intentOf(response) !== 'api.onchange') return false;
      try {
        const body = JSON.parse(response.request().postData() || '{}');
        return String(body?.params?.model || '') === 'project.project'
          && Array.isArray(body?.params?.changed_fields)
          && body.params.changed_fields.includes('name');
      } catch { return false; }
    }, { timeout: 15000 });
    await nameInput.fill(projectName);
    await nameInput.press('Tab');
    const projectNameOnchangeResponse = await projectNameOnchangePromise;
    check(projectNameOnchangeResponse.status() === 200,
      'project name onchange failed before save', await projectNameOnchangeResponse.text());
    await projectFrame.waitForFunction(() => /已修改|有未保存修改/.test(
      String(document.querySelector('[data-product-page-mode="form"]')?.textContent || ''),
    ), undefined, { timeout: 5000 });
    let projectCreateResponse;
    let postClickStatus = '';
    const saveButtonInventory = await collectSaveButtonInventory(projectFrame);
    const activeProjectSaveButtons = saveButtonInventory.filter((button) => (
      button.model === 'project.project'
      && button.record === 'new'
      && button.actionId === Number(projectEntry.action_id)
      && button.menuId === Number(projectEntry.menu_id)
    ));
    check(activeProjectSaveButtons.length === 1
      && activeProjectSaveButtons[0].visible
      && !activeProjectSaveButtons[0].disabled,
    'active project create form must expose one visible enabled save action', saveButtonInventory);
    const projectSaveAction = await requireUnique(
      projectFrame,
      projectSurface.locator('[data-action-ref="form.save"]'),
      'active managed project save action',
      { enabled: true },
    );
    try {
      const responsePromise = projectPage.waitForResponse((response) => {
          if (!response.url().includes('/api/v1/intent')) return false;
          try {
            const body = JSON.parse(response.request().postData() || '{}');
            return String(body?.intent || '') === 'api.data'
              && String(body?.params?.op || body?.op || '') === 'create'
              && String(body?.params?.model || '') === 'project.project';
          } catch { return false; }
        }, { timeout: 8000 }).catch(() => null);
      await projectSaveAction.click();
      postClickStatus = (await projectSurface.innerText())
        .replace(/\s+/g, ' ').trim().slice(0, 500);
      projectCreateResponse = await responsePromise;
      if (!projectCreateResponse) throw new Error('project create response timeout');
    } catch (error) {
      const projectContract = projectContractResponses.at(-1) || {};
      fs.writeFileSync(path.join(outputDir, 'authorized-project-contract.json'), `${JSON.stringify(projectContract, null, 2)}\n`);
      const requiredValues = await projectSurface.locator('[data-field-state="required"]').evaluateAll((nodes) => nodes.map((node) => ({
        field: String(node.getAttribute('data-field-name') || ''),
        value: String(node.querySelector('input, textarea, select')?.value || ''),
      })));
      const validation = await projectFrame.locator('[data-form-error-summary]:visible').allInnerTexts();
      const saveActions = await projectSurface.locator('[data-action-ref="form.save"]').evaluateAll((nodes) => nodes.map((node) => ({
        text: String(node.textContent || '').replace(/\s+/g, ' ').trim(),
        visible: node instanceof HTMLElement && node.offsetParent !== null,
        disabled: node instanceof HTMLButtonElement ? node.disabled : false,
      })));
      throw new Error(`project create emitted no mutation ${JSON.stringify({
        cause: error instanceof Error ? error.message : String(error), requiredValues, validation, saveActions,
        postClickStatus, saveButtonInventory,
        observedRequests: projectObservedRequests.slice(-20),
        effectiveRecordCapabilities: valuesForKey(projectContract, 'effectiveRecordCapabilities'),
        renderProfiles: valuesForKey(projectContract, 'renderProfile'),
      })}`);
    }
    const projectCreatePayload = await projectCreateResponse.json();
    check(projectCreateResponse.status() === 200, 'project relation create mutation failed', projectCreatePayload);
    projectCreatedId = valuesForKey(projectCreatePayload, 'id')
      .map((value) => Number(value || 0))
      .find((value) => Number.isFinite(value) && value > 0) || 0;
    check(projectCreatedId > 0, 'project create response did not expose a real record id', projectCreatePayload);
    await dialogFrameElement.waitFor({ state: 'detached', timeout: 30000 });
    check(projectPage.url() === parentUrlBeforeDialog,
      'project dialog completion changed the parent route', projectPage.url());
    check(projectCreates.length === 1, 'project relation create emitted an unexpected number of mutations', projectCreates);
    const returnedPaymentSurface = await requireUnique(
      projectPage,
      projectPage.locator(
        `[data-product-page-mode="form"][data-form-model="payment.request"][data-form-record="new"]`
        + `[data-form-action-id="${actionId}"][data-form-menu-id="${menuId}"]:visible`,
      ),
      'returned parent payment form',
      { timeout: 45000 },
    );
    await returnedPaymentSurface.locator('[data-contract-form-driver]').waitFor({ timeout: 45000 });
    await returnedPaymentSurface.locator('.product-form-loading').waitFor({ state: 'detached', timeout: 45000 });
    const returnedProjectInput = await requireUnique(
      projectPage,
      returnedPaymentSurface.locator('[data-field-name="project_id"] input'),
      'returned parent project input',
      { enabled: true },
    );
    await projectPage.waitForFunction(({ expectedProject }) => {
      const inputs = [...document.querySelectorAll('[data-product-page-mode="form"] [data-field-name="project_id"] input')]
        .filter((node) => node instanceof HTMLInputElement && node.offsetParent !== null);
      return inputs.length === 1 && inputs[0].value.includes(expectedProject);
    }, { expectedProject: projectName }, { timeout: 30000 });
    check((await returnedProjectInput.inputValue()).includes(projectName),
      'returned parent project field did not retain the created record identity');
    const returnedCategoryInput = await requireUnique(
      projectPage,
      returnedPaymentSurface.locator('[data-field-name="business_category_id"] input'),
      'returned parent business category input',
      { enabled: true },
    );
    check(/付款申请/.test(await returnedCategoryInput.inputValue()),
      'parent business category was not retained across relation create');
    const returnedPartnerInput = await requireUnique(
      projectPage,
      returnedPaymentSurface.locator('[data-field-name="partner_id"] input'),
      'returned parent partner input',
      { enabled: true },
    );
    const returnedAmountInput = await requireUnique(
      projectPage,
      returnedPaymentSurface.locator('[data-field-name="amount"] input'),
      'returned parent amount input',
      { enabled: true },
    );
    const returnedPartner = await returnedPartnerInput.inputValue();
    const returnedAmount = await returnedAmountInput.inputValue();
    check(returnedPartner === parentPartnerBeforeDialog && Number(returnedAmount) === 37.25,
      'parent unsaved relation and amount facts were not retained across relation create', {
        parentPartnerBeforeDialog, returnedPartner, returnedAmount, url: projectPage.url(),
      });
    check(Boolean(await returnedPaymentSurface.locator('[data-field-name="date_request"] input').inputValue()),
      'returned payment create date default is missing');
    const parentCreateResponsePromise = projectPage.waitForResponse((response) => {
      if (!response.url().includes('/api/v1/intent')) return false;
      try { return isPaymentCreateBody(JSON.parse(response.request().postData() || '{}')); } catch { return false; }
    }, { timeout: 30000 });
    const returnedParentSave = await requireUnique(
      projectPage,
      returnedPaymentSurface.locator('[data-action-ref="form.save"][data-action-tier="primary"]'),
      'returned parent payment save action',
      { enabled: true },
    );
    await returnedParentSave.click();
    const parentCreateResponse = await parentCreateResponsePromise;
    check(parentCreateResponse.status() === 200, 'parent payment create mutation failed', await parentCreateResponse.text());
    await projectPage.waitForURL((url) => /^\/f\/payment\.request\/\d+$/.test(url.pathname), { timeout: 45000 });
    parentPaymentId = Number(projectPage.url().match(/\/f\/payment\.request\/(\d+)/)?.[1] || 0);
    check(parentPaymentId > 0 && parentPaymentCreates.length === 1,
      'parent payment must emit exactly one create mutation and leave the /new route', {
        parentPaymentId, parentPaymentCreates, url: projectPage.url(),
      });
    check(projectErrors.length === 0, 'authorized project create journey emitted browser errors', projectErrors);
    await projectPage.screenshot({ path: path.join(outputDir, 'authorized-project-returned-parent.png'), fullPage: true });
    cleanup.payment = await unlinkRecords(projectPage, 'payment.request', [parentPaymentId], projectAuthHeaders);
    check(cleanup.payment.status === 200 && cleanup.payment.body?.ok === true,
      'cascaded parent payment cleanup failed', cleanup.payment);
    parentPaymentId = 0;
    cleanup.project = await unlinkRecords(projectPage, 'project.project', [projectCreatedId], projectAuthHeaders);
    check(cleanup.project.status === 200 && cleanup.project.body?.ok === true,
      'cascaded project cleanup failed', cleanup.project);
    projectCreatedId = 0;
    return {
      login: projectUser.login,
      createLabel,
      createUrl: route.toString(),
      actionId: Number(route.searchParams.get('action_id') || 0),
      menuId: Number(route.searchParams.get('menu_id') || 0),
      createMode: route.searchParams.get('relation_create_mode'),
      returnField: route.searchParams.get('relation_return_field'),
      returnModel: route.searchParams.get('relation_return_model'),
      editableControls,
      relationAuthority: projectRelationAuthority,
      saveButtonInventory,
      projectName,
      projectMutations: projectCreates.length,
      parentPaymentMutations: parentPaymentCreates.length,
      returnedProjectBackfill: true,
      parentPartnerPreserved: returnedPartner,
      parentAmountPreserved: returnedAmount,
      parentRoutePreserved: parentUrlBeforeDialog,
      parentRouteAfterSave: projectPage.url(),
      cleanup,
      errors: projectErrors,
    };
  } catch (error) {
    throw new Error(`authorized project relation journey failed: ${JSON.stringify(await runtimeDiagnostics(projectPage, {
      cause: error instanceof Error ? error.message : String(error),
      requestCounts: {
        projectCreates: projectCreates.length,
        parentPaymentCreates: parentPaymentCreates.length,
        observedRequests: projectObservedRequests.length,
      },
    }))}`);
  } finally {
    if (parentPaymentId > 0) {
      await unlinkRecords(projectPage, 'payment.request', [parentPaymentId], projectAuthHeaders).catch(() => undefined);
    }
    if (projectCreatedId > 0) {
      await unlinkRecords(projectPage, 'project.project', [projectCreatedId], projectAuthHeaders).catch(() => undefined);
    }
    await projectContext.close();
  }
}

async function unlinkPaymentRequests(page, ids, authHeaders) {
  return unlinkRecords(page, 'payment.request', ids, authHeaders);
}

async function collectWriteFloorplanMetrics(page, surface) {
  const fieldOccurrences = await surface.locator('[data-object-task-page] [data-field-name]').evaluateAll((nodes) => (
    nodes.map((node) => String(node.getAttribute('data-field-name') || '')).filter(Boolean)
  ));
  const duplicateFields = [...new Set(fieldOccurrences.filter((field, index) => fieldOccurrences.indexOf(field) !== index))];
  const regionFields = {};
  for (const region of ['core-input', 'condition-input', 'pre-execution-input', 'supplementary-input', 'relation']) {
    regionFields[region] = await surface.locator(`[data-floorplan-region="${region}"] [data-field-name]`).evaluateAll((nodes) => (
      nodes.map((node) => String(node.getAttribute('data-field-name') || '')).filter(Boolean)
    ));
  }
  const groupTitles = await surface.locator('[data-object-task-page] [data-group-title]').evaluateAll((nodes) => (
    nodes.map((node) => String(node.getAttribute('data-group-title') || '').trim()).filter(Boolean)
  ));
  const duplicateGroupTitles = [...new Set(groupTitles.filter((title, index) => groupTitles.indexOf(title) !== index))];
  const many2oneCapabilities = await surface.locator(
    '[data-object-task-page] [data-field-type="many2one"]',
  ).evaluateAll((nodes) => nodes.map((node) => ({
    fieldName: String(node.getAttribute('data-field-name') || ''),
    fieldState: String(node.getAttribute('data-field-state') || ''),
    actions: [...node.querySelectorAll('.many2one-action')]
      .map((action) => String(action.textContent || '').replace(/\s+/g, ' ').trim())
      .filter(Boolean),
  })));
  const geometry = await page.evaluate(() => ({
    width: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  return {
    driver: await surface.locator('[data-contract-form-driver]').getAttribute('data-contract-form-driver'),
    h1: await surface.locator('h1').count(),
    statusButtons: await surface.locator('.native-statusbar-track button:visible').count(),
    duplicateFields,
    fieldOccurrences,
    regionFields,
    groupTitles,
    duplicateGroupTitles,
    many2oneCapabilities,
    readonlyControls: await surface.locator([
      '[data-object-task-page] [data-field-state="readonly"] input',
      '[data-object-task-page] [data-field-state="readonly"] textarea',
      '[data-object-task-page] [data-field-state="readonly"] select',
    ].join(', ')).count(),
    emptyDisabledControls: await surface.locator([
      '[data-object-task-page] input:disabled',
      '[data-object-task-page] textarea:disabled',
      '[data-object-task-page] select:disabled',
    ].join(', ')).evaluateAll((nodes) => nodes.filter((node) => (
      !(node instanceof HTMLInputElement && ['checkbox', 'radio'].includes(node.type))
      && !String(node.value || '').trim()
    )).length),
    enabledPrimary: await surface.locator('[data-object-task-page] [data-action-tier="primary"][data-action-enabled="true"]').count(),
    disabledBusinessActions: await surface.locator('[data-object-task-page] [data-action-ref][data-action-enabled="false"]:visible').count(),
    nativeStructure: await surface.locator('[data-native-contract-structure]').count(),
    overflow: geometry.scrollWidth - geometry.width,
  };
}

function assertWriteFloorplanMetrics(metrics, label) {
  check(metrics.driver === 'tdesign-modern', `${label} is not using the TDesign Product Floorplan`, metrics);
  check(metrics.h1 === 1, `${label} must expose exactly one H1`, metrics);
  check(metrics.statusButtons === 0, `${label} renders workflow states as buttons`, metrics);
  check(metrics.duplicateFields.length === 0, `${label} repeats canonical field identities`, metrics);
  check(metrics.duplicateGroupTitles.length === 0, `${label} repeats canonical group titles`, metrics);
  check(metrics.readonlyControls === 0, `${label} renders readonly facts as form controls`, metrics);
  check(metrics.emptyDisabledControls === 0, `${label} exposes empty disabled controls`, metrics);
  check(metrics.disabledBusinessActions === 0, `${label} exposes meaningless disabled business actions`, metrics);
  check(metrics.nativeStructure === 0, `${label} fell back to a full Native form tree`, metrics);
  check(metrics.overflow <= 0, `${label} has horizontal overflow`, metrics);
}

check(frontendUrl && database && password && login, 'local.dev submit identity is incomplete');
check(actionId > 0 && menuId > 0 && recordId > 0 && record.state === 'draft', 'submit-ready target is invalid', record);
fs.mkdirSync(outputDir, { recursive: true });

const browser = await launchChromium({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
const page = await context.newPage();
const errors = [];
const mutations = [];
const recordWrites = [];
const recordCreates = [];
const observedIntents = [];
const contractResponseTasks = [];
const paymentRelationAuthoritySnapshots = [];
let createdId = 0;
let createdRecordCleaned = false;
let intentAuthHeaders = {};
page.on('console', (message) => {
  if (message.type() === 'error' && !message.text().includes('favicon')) errors.push(message.text());
});
page.on('pageerror', (error) => errors.push(error.message));
page.on('request', (request) => {
  if (request.method() !== 'POST') return;
  let body = {};
  try { body = JSON.parse(request.postData() || '{}'); } catch {}
  const intent = String(body?.intent || '');
  if (intent) observedIntents.push(intent);
  if (intent === 'execute_button') {
    mutationRequestCounts.executeButton += 1;
    mutations.push({ intent, params: body.params });
  }
  if (isPaymentWriteBody(body)) {
    mutationRequestCounts.paymentWrite += 1;
    recordWrites.push({ intent, params: body.params });
  }
  if (isPaymentCreateBody(body)) {
    mutationRequestCounts.paymentCreate += 1;
    recordCreates.push({ intent, params: body.params });
    const headers = request.headers();
    intentAuthHeaders = Object.fromEntries(
      ['authorization', 'x-odoo-db', 'x-tenant']
        .filter((key) => headers[key])
        .map((key) => [key, headers[key]]),
    );
  }
});
page.on('response', (response) => {
  if (intentOf(response) !== 'ui.contract.v2') return;
  let requestBody = {};
  try { requestBody = JSON.parse(response.request().postData() || '{}'); } catch {}
  if (String(requestBody?.params?.model || '') !== 'payment.request') return;
  const task = response.json().then((body) => {
    const authorities = collectRelationAuthorities(body);
    if (Object.keys(authorities).length) paymentRelationAuthoritySnapshots.push(authorities);
  }).catch(() => undefined);
  contractResponseTasks.push(task);
});

const report = { schemaVersion: 'payment_request_floorplan_submit.v1', target: record, pass: false };
try {
  enterStage('main:project-relation-journey');
  report.projectRelationCreate = await verifyAuthorizedProjectRelationCreate(browser);
  enterStage('main:login');
  await page.goto(`${frontendUrl}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const usernameInput = await requireUnique(page, page.locator('#login-username'), 'payment login username', { enabled: true });
  const passwordInput = await requireUnique(page, page.locator('#login-password'), 'payment login password', { enabled: true });
  const databaseInput = await requireUnique(page, page.getByLabel(/数据库/), 'payment login database');
  await usernameInput.fill(login);
  await passwordInput.fill(password);
  if (!(await databaseInput.isDisabled())) await databaseInput.fill(database);
  const loginAction = await requireUnique(
    page,
    page.getByRole('button', { name: /^登录$/ }),
    'payment login action',
    { enabled: true },
  );
  await loginAction.click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 30000 });

  enterStage('main:home-before');
  await page.goto(`${frontendUrl}/`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const homeSurface = await requireUnique(page, page.locator('[data-role-home]:visible'), 'active role home', { timeout: 45000 });
  await homeSurface.locator('.role-home-surface__tasks .role-home-surface__state, .role-home-surface__task-list').waitFor({ timeout: 45000 });
  const homeBefore = {
    tasks: await homeSurface.locator('.role-home-surface__task-list article').allTextContents(),
    summaries: await homeSurface.locator('.role-home-surface__summary-list article').allTextContents(),
  };

  enterStage('main:list-before');
  const listUrl = `${frontendUrl}/a/${actionId}?menu_id=${menuId}`;
  await page.goto(listUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const listSurface = await requireUnique(
    page,
    page.locator('[data-product-page-mode="list"]:visible'),
    'active payment list',
    { timeout: 45000 },
  );
  const actionableRow = await requireUnique(
    page,
    listSurface.locator('tbody tr:visible').filter({ hasText: record.name }),
    `payment list row ${record.name}#${recordId}`,
    { enabled: true, timeout: 45000 },
  );
  const listRowBefore = (await actionableRow.innerText()).replace(/\s+/g, ' ').trim();
  const newPaymentAction = await requireUnique(
    page,
    listSurface.getByRole('button', { name: /^新建$/ }),
    'payment list create action',
    { enabled: true },
  );
  await newPaymentAction.click();
  enterStage('main:payment-create');
  const createSurface = await requireUnique(
    page,
    page.locator(
      `[data-product-page-mode="form"][data-form-model="payment.request"][data-form-record="new"]`
      + `[data-form-action-id="${actionId}"][data-form-menu-id="${menuId}"]:visible`,
    ),
    'active payment create form',
    { timeout: 45000 },
  );
  await createSurface.locator('.product-form-loading').waitFor({ state: 'detached', timeout: 45000 });
  await createSurface.locator('[data-contract-form-driver]').waitFor({ timeout: 45000 });
  const createEditableFieldLocator = createSurface.locator(
    'input:not([type="hidden"]):not(:disabled), textarea:not(:disabled), select:not(:disabled)',
  );
  const createEditableFields = await createEditableFieldLocator.count();
  check(createEditableFields > 0, 'payment create entry did not open an editable form', createEditableFields);
  const createMetrics = await collectWriteFloorplanMetrics(page, createSurface);
  await Promise.all(contractResponseTasks);
  const createRelationAuthorities = paymentRelationAuthoritySnapshots.at(-1) || {};
  assertWriteFloorplanMetrics(createMetrics, 'payment create surface');
  check(Object.keys(createRelationAuthorities).length > 0,
    'payment create Contract V2 relation authority was not observed');
  assertRelationCreateAuthority(createMetrics, createRelationAuthorities, 'payment create surface');
  check(createMetrics.enabledPrimary === 1, 'payment create surface must expose one save primary action', createMetrics);
  check(JSON.stringify(createMetrics.regionFields['core-input']) === JSON.stringify([
    'business_category_id', 'project_id', 'partner_id', 'date_request', 'amount',
  ]), 'payment create core-input region must contain only backend-required application facts', createMetrics);
  check(createMetrics.regionFields['condition-input'].length === 0,
    'payment create surface inferred current conditions without structured backend authority', createMetrics);
  check(createMetrics.regionFields['pre-execution-input'].length === 0,
    'payment create surface inferred a later-stage requirement without structured backend authority', createMetrics);
  for (const field of [
    'contract_id', 'settlement_id', 'material_settlement_id', 'accepted_amount_uppercase', 'actual_payee_unit',
    'payment_account_name', 'payment_bank_name', 'payment_account_no', 'payer_unit', 'note', 'attachment_ids',
  ]) {
    check(createMetrics.regionFields['supplementary-input'].includes(field),
      `payment create supplementary region does not expose optional field ${field}`, createMetrics);
  }
  check(!createMetrics.regionFields.relation.includes('attachment_ids'),
    'attachment capability was duplicated into the business relation region', createMetrics);
  for (const fieldName of ['business_category_id', 'project_id', 'partner_id']) {
    const capability = createMetrics.many2oneCapabilities.find((item) => item.fieldName === fieldName);
    check(capability?.fieldState === 'required',
      `required many2one field ${fieldName} lost its required authority`, createMetrics.many2oneCapabilities);
    check(capability.actions.some((label) => /搜索/.test(label)),
      `required many2one field ${fieldName} lost its backend-authorized search entry`, capability);
  }
  await page.screenshot({ path: path.join(outputDir, 'create-product-floorplan-desktop.png'), fullPage: true });
  await page.waitForFunction((expectedLabel) => (
    new URL(window.location.href).searchParams.get('default_business_category_label') === expectedLabel
  ), '付款申请', { timeout: 30000 });
  await chooseUniqueRelationOption(page, createSurface, {
    fieldName: 'business_category_id',
    relationModel: 'sc.business.category',
    query: '付款申请',
    expectedLabel: '付款申请',
  });
  await page.waitForFunction(() => (
    new URL(window.location.href).searchParams.get('current_business_category_code') === 'finance.payment.apply.pay'
  ), undefined, { timeout: 30000 });
  check(await page.locator('dialog.intent-confirmation[open]').count() === 0,
    'internal business category context switch triggered the unsaved-leave confirmation');
  await createSurface.locator('.product-form-loading').waitFor({ state: 'detached', timeout: 45000 });
  await createSurface.locator('[data-contract-form-driver]').waitFor({ timeout: 45000 });
  check(/付款申请/.test(await createSurface.locator('[data-field-name="business_category_id"] input').inputValue()),
    'business category selection was cleared by the internal context switch');
  const projectField = await requireUnique(page, createSurface.locator('[data-field-name="project_id"]'), 'payment create project field');
  const createProjectInput = await requireUnique(
    page,
    projectField.locator('input'),
    'payment create project input',
    { enabled: true },
  );
  await createProjectInput.click();
  const searchMore = await requireUnique(
    page,
    projectField.locator('.many2one-action').filter({ hasText: /搜索/ }),
    'payment create project search action',
    { enabled: true },
  );
  await searchMore.click();
  const relationDialog = await requireUnique(
    page,
    page.locator('.relation-dialog[role="dialog"]:visible'),
    'payment create project search dialog',
  );
  const relationDialogCancel = await requireUnique(
    page,
    relationDialog.getByRole('button', { name: /^取消$/ }),
    'payment create relation dialog cancel action',
    { enabled: true },
  );
  await relationDialogCancel.click();
  await relationDialog.waitFor({ state: 'hidden', timeout: 15000 });
  await chooseUniqueRelationOption(page, createSurface, {
    fieldName: 'project_id',
    relationModel: 'project.project',
    query: 'S69',
    expectedLabel: 'S69 支付台账演示项目',
  });
  await chooseUniqueRelationOption(page, createSurface, {
    fieldName: 'partner_id',
    relationModel: 'res.partner',
    query: '德阳',
    expectedLabel: '德阳智能制造产教融合项目',
  });
  check(Boolean(await createSurface.locator('[data-field-name="date_request"] input').inputValue()),
    'payment create date default is missing');
  const createAmountInput = await requireUnique(
    page,
    createSurface.locator('[data-field-name="amount"] input'),
    'payment create amount input',
    { enabled: true },
  );
  await createAmountInput.fill('1');
  const createResponsePromise = page.waitForResponse((response) => {
    if (!response.url().includes('/api/v1/intent')) return false;
    try { return isPaymentCreateBody(JSON.parse(response.request().postData() || '{}')); } catch { return false; }
  }, { timeout: 30000 });
  const createSaveAction = await requireUnique(
    page,
    createSurface.locator('[data-action-ref="form.save"][data-action-tier="primary"]'),
    'payment create save action',
    { enabled: true },
  );
  await createSaveAction.click();
  const createResponse = await createResponsePromise;
  check(createResponse.status() === 200, 'payment create save failed', await createResponse.text());
  await page.waitForURL((url) => /^\/f\/payment\.request\/\d+$/.test(url.pathname), { timeout: 45000 });
  createdId = Number(page.url().match(/\/f\/payment\.request\/(\d+)/)?.[1] || 0);
  check(createdId > 0 && recordCreates.length === 1,
    'payment create must emit exactly one create mutation and leave the /new route', {
      createdId, recordCreates, url: page.url(),
    });
  await page.goto(listUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await requireUnique(page, page.locator('[data-product-page-mode="list"]:visible'), 'payment list after create', { timeout: 45000 });

  const blocked = candidateInventory.find((item) => item.state === 'draft' && item.submit_enabled === false);
  const terminal = candidateInventory.find((item) => ['done', 'paid'].includes(item.state)
    || /已足额付款|已完成/.test(String(item.legal_next_action || '')));
  check(blocked?.id && terminal?.id, 'payment state variant fixtures are incomplete', candidateInventory);
  const stateVariants = {};
  for (const [kind, item] of [['blocked', blocked], ['terminal', terminal]]) {
    enterStage(`main:${kind}-readonly`);
    await page.goto(`${frontendUrl}/r/payment.request/${item.id}?menu_id=${menuId}&action_id=${actionId}`, {
      waitUntil: 'domcontentloaded', timeout: 45000,
    });
    const variantReadonlySurface = await requireUnique(
      page,
      page.locator(
        `[data-product-page-mode="form"][data-form-model="payment.request"][data-form-record="${Number(item.id)}"]`
        + `[data-form-action-id="${actionId}"][data-form-menu-id="${menuId}"]:visible`,
      ),
      `${kind} payment readonly form`,
      { timeout: 45000 },
    );
    await variantReadonlySurface.locator('[data-object-task-page]').waitFor({ timeout: 45000 });
    const enabledPrimaryCount = await variantReadonlySurface.locator(
      '[data-object-task-page] [data-action-tier="primary"][data-action-enabled="true"]',
    ).count();
    const taskText = (await variantReadonlySurface.locator('[data-floorplan-region="current-task"]').innerText()).replace(/\s+/g, ' ').trim();
    stateVariants[kind] = { id: item.id, name: item.name, enabledPrimaryCount, taskText };
    check(enabledPrimaryCount === 0, `${kind} payment record exposed a misleading primary action`, stateVariants[kind]);
    if (kind === 'blocked') {
      check(/缺少|请补充|请维护/.test(taskText), 'blocked payment has no repair path', stateVariants[kind]);
      const editAction = await requireUnique(
        page,
        variantReadonlySurface.locator('[data-form-mode-action="edit"]'),
        'blocked payment remediation edit action',
        { enabled: true },
      );
      await editAction.click();
      const variantEditSurface = await requireUnique(
        page,
        page.locator(
          `[data-product-page-mode="form"][data-form-model="payment.request"][data-form-record="${Number(item.id)}"]`
          + `[data-form-action-id="${actionId}"][data-form-menu-id="${menuId}"]:visible`,
        ),
        `${kind} payment edit form`,
        { timeout: 45000 },
      );
      const editableFields = variantEditSurface.locator(
        'input:not([type="hidden"]):not(:disabled), textarea:not(:disabled), select:not(:disabled)',
      );
      stateVariants[kind].editableFields = await editableFields.count();
      check(stateVariants[kind].editableFields > 0, 'blocked remediation path did not enter edit mode');
      stateVariants[kind].editMetrics = await collectWriteFloorplanMetrics(page, variantEditSurface);
      assertWriteFloorplanMetrics(stateVariants[kind].editMetrics, 'blocked payment edit surface');
      check(stateVariants[kind].editMetrics.enabledPrimary === 0,
        'blocked payment edit surface exposed a false enabled primary action', stateVariants[kind].editMetrics);
      check(JSON.stringify(stateVariants[kind].editMetrics.regionFields['core-input']) === JSON.stringify([
        'project_id', 'partner_id', 'business_category_id', 'date_request', 'amount',
      ]), 'blocked payment core-input region must contain only backend-required facts', stateVariants[kind].editMetrics);
      check(stateVariants[kind].editMetrics.regionFields['condition-input'].length === 0
        && stateVariants[kind].editMetrics.regionFields['pre-execution-input'].length === 0,
      'blocked payment edit inferred structured requirements that Contract V2 does not provide', stateVariants[kind].editMetrics);
      await page.setViewportSize({ width: 390, height: 844 });
      await waitForViewport(page, 390);
      stateVariants[kind].editMobile = await collectWriteFloorplanMetrics(page, variantEditSurface);
      check(stateVariants[kind].editMobile.overflow <= 0, '390px blocked edit surface has horizontal overflow', stateVariants[kind].editMobile);
      await page.screenshot({ path: path.join(outputDir, 'blocked-edit-product-floorplan-390.png'), fullPage: true });
      await page.setViewportSize({ width: 1440, height: 960 });
    }
  }

  enterStage('main:actionable-edit');
  await page.goto(listUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const journeyList = await requireUnique(page, page.locator('[data-product-page-mode="list"]:visible'), 'actionable payment list', { timeout: 45000 });
  const journeyRow = await requireUnique(
    page,
    journeyList.locator('tbody tr:visible').filter({ hasText: record.name }),
    `actionable payment row ${record.name}#${recordId}`,
    { enabled: true, timeout: 45000 },
  );
  await journeyRow.click();
  await page.waitForURL((url) => url.pathname === `/r/payment.request/${recordId}`, { timeout: 45000 });
  await page.goto(`${frontendUrl}/f/payment.request/${recordId}?menu_id=${menuId}&action_id=${actionId}`, {
    waitUntil: 'domcontentloaded', timeout: 45000,
  });
  const editSurface = await requireUnique(
    page,
    page.locator(
      `[data-product-page-mode="form"][data-form-model="payment.request"][data-form-record="${recordId}"]`
      + `[data-form-action-id="${actionId}"][data-form-menu-id="${menuId}"]:visible`,
    ),
    `active payment edit form ${recordId}`,
    { timeout: 45000 },
  );
  await editSurface.locator('[data-object-task-page]').waitFor({ timeout: 45000 });
  const cleanEditMetrics = await collectWriteFloorplanMetrics(page, editSurface);
  assertWriteFloorplanMetrics(cleanEditMetrics, 'actionable payment edit surface');
  const supplementaryDetails = await requireUnique(
    page,
    editSurface.locator('[data-floorplan-region="supplementary-input"]'),
    'payment supplementary input region',
  );
  const supplementaryDisclosure = await requireUnique(
    page,
    supplementaryDetails.locator('summary'),
    'payment supplementary disclosure',
    { enabled: true },
  );
  await supplementaryDisclosure.click();
  const note = await requireUnique(
    page,
    editSurface.locator('[data-field-name="note"] textarea, [data-field-name="note"] input'),
    'payment note input',
    { enabled: true },
  );
  const editedNote = `产品化保存验证 ${recordId}`;
  await note.fill(editedNote);
  const editReturn = await requireUnique(page, editSurface.getByRole('button', { name: /^返回列表$/ }), 'payment edit return action', { enabled: true });
  await editReturn.click();
  const leaveDialog = await requireUnique(page, page.locator('dialog.intent-confirmation[open]'), 'unsaved leave confirmation');
  check(/尚未保存/.test(await leaveDialog.innerText()), 'ordinary unsaved-leave protection did not warn');
  const leaveCancel = await requireUnique(
    page,
    leaveDialog.getByRole('button', { name: /^取消$/ }),
    'unsaved leave cancel action',
    { enabled: true },
  );
  await leaveCancel.click();
  check(await note.inputValue() === editedNote, 'cancelling ordinary leave discarded the current edit');
  const leaveProtection = { warned: true, cancelRetainedInput: true };
  const dirtyPrimary = await requireUnique(
    page,
    editSurface.locator('[data-action-ref="form.save"][data-action-tier="primary"][data-action-enabled="true"]'),
    'dirty payment save action',
    { enabled: true },
  );
  const writePromise = page.waitForResponse((response) => {
    if (!response.url().includes('/api/v1/intent')) return false;
    try { return isPaymentWriteBody(JSON.parse(response.request().postData() || '{}')); } catch { return false; }
  }, { timeout: 30000 });
  await dirtyPrimary.click();
  const writeResponse = await writePromise;
  check(writeResponse.status() === 200, 'payment edit save failed', await writeResponse.text());
  await page.waitForFunction(() => {
    const actions = [...document.querySelectorAll(
      '[data-product-page-mode="form"] [data-action-tier="primary"][data-action-enabled="true"]',
    )].filter((node) => node instanceof HTMLElement && node.offsetParent !== null);
    return actions.length === 1 && String(actions[0]?.textContent || '').trim() === '提交审批';
  }, undefined, { timeout: 45000 });
  const afterSavePrimary = editSurface.locator('[data-action-tier="primary"][data-action-enabled="true"]');
  check(await afterSavePrimary.count() === 1 && (await afterSavePrimary.innerText()).trim() === '提交审批',
    'saved edit did not switch to the backend-authoritative submit action');
  check(Boolean(await afterSavePrimary.getAttribute('data-action-ref'))
    && Boolean(await afterSavePrimary.getAttribute('data-backend-identity')),
  'saved edit primary action is missing backend authority identity');
  check(recordWrites.length === 1, 'edit save emitted an unexpected number of record mutations', recordWrites);
  report.edit = { before: cleanEditMetrics, recordWrites: [...recordWrites], afterSavePrimary: await afterSavePrimary.innerText() };
  await page.screenshot({ path: path.join(outputDir, 'edit-after-save-desktop.png'), fullPage: true });
  enterStage('main:post-save-list');
  await page.goto(listUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const postSaveList = await requireUnique(page, page.locator('[data-product-page-mode="list"]:visible'), 'post-save payment list', { timeout: 45000 });
  const postSaveRow = await requireUnique(
    page,
    postSaveList.locator('tbody tr:visible').filter({ hasText: record.name }),
    `post-save payment row ${record.name}#${recordId}`,
    { enabled: true, timeout: 45000 },
  );
  await postSaveRow.click();
  await page.waitForURL((url) => url.pathname === `/r/payment.request/${recordId}`, { timeout: 45000 });
  await page.setViewportSize({ width: 390, height: 844 });
  await waitForViewport(page, 390);
  const readonlyRecordSurface = await requireUnique(
    page,
    page.locator(
      `[data-product-page-mode="form"][data-form-model="payment.request"][data-form-record="${recordId}"]`
      + `[data-form-action-id="${actionId}"][data-form-menu-id="${menuId}"]:visible`,
    ),
    `active payment readonly form ${recordId}`,
    { timeout: 45000 },
  );
  await readonlyRecordSurface.locator('[data-object-task-page]').waitFor({ timeout: 45000 });
  check(page.url().includes(`/r/payment.request/${recordId}`), 'list row did not open the actionable payment detail', page.url());
  const surface = await requireUnique(page, readonlyRecordSurface.locator('[data-mobile-action-surface]'), 'payment mobile action surface');
  const primary = await requireUnique(
    page,
    surface.locator('[data-action-tier="primary"][data-action-enabled="true"]'),
    'submit-ready payment primary action',
    { enabled: true },
  );
  check((await primary.innerText()).trim() === '提交审批', 'unexpected primary action label', await primary.innerText());
  const metrics = await surface.evaluate((node) => {
    const rect = node.getBoundingClientRect();
    const style = getComputedStyle(node);
    return {
      position: style.position,
      bottom: rect.bottom,
      viewportHeight: innerHeight,
      overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    };
  });
  check(metrics.position === 'fixed' && Math.abs(metrics.bottom - metrics.viewportHeight) <= 1 && metrics.overflow <= 0,
    'mobile primary action surface is not fixed and contained', metrics);
  const beforeTaskText = (await readonlyRecordSurface.locator('[data-floorplan-region="current-task"]').innerText()).replace(/\s+/g, ' ').trim();
  await page.screenshot({ path: path.join(outputDir, 'before-submit-390.png') });

  await primary.click();
  const dialog = await requireUnique(page, page.locator('dialog.intent-confirmation[open]'), 'submit confirmation dialog', { timeout: 5000 });
  const confirmationText = (await dialog.innerText()).replace(/\s+/g, ' ').trim();
  check(confirmationText.includes('确认提交审批'), 'business confirmation title is missing', confirmationText);
  check(confirmationText.includes('系统将重新读取付款申请及上下游金额状态'), 'authoritative confirmation message is missing', confirmationText);
  await page.screenshot({ path: path.join(outputDir, 'confirmation-390.png') });

  const executePromise = page.waitForResponse((response) => intentOf(response) === 'execute_button', { timeout: 30000 });
  const submitConfirm = await requireUnique(
    page,
    dialog.getByRole('button', { name: /^确认提交审批$/ }),
    'payment submit confirmation action',
    { enabled: true },
  );
  await submitConfirm.click();
  const executeResponse = await executePromise;
  const executeBody = await executeResponse.json();
  report.execute = { status: executeResponse.status(), body: executeBody };
  check(executeResponse.status() === 200 && executeBody?.ok === true, 'submit execution failed', executeBody);
  enterStage('main:post-submit-refresh');
  const statusSummary = await requireUnique(
    page,
    readonlyRecordSurface.locator('.native-statusbar-summary--readonly'),
    `payment ${recordId} readonly status summary`,
    { timeout: 45000 },
  );
  const currentStateLocator = await requireUnique(page, statusSummary.locator('strong'), 'payment current status fact');
  await readonlyRecordSurface.locator('[data-object-task-page]').waitFor({ state: 'visible', timeout: 45000 });
  const currentState = (await currentStateLocator.innerText()).trim();
  const statusSummaryText = (await statusSummary.innerText()).replace(/\s+/g, ' ').trim();
  const currentTaskText = (await readonlyRecordSurface.locator('[data-floorplan-region="current-task"]').innerText()).replace(/\s+/g, ' ').trim();
  const currentPageText = (await page.locator('body').innerText()).replace(/\s+/g, ' ').trim();
  check(!currentPageText.includes('无权访问'), 'successful submit navigated to an access-denied product surface', {
    executeBody, observedIntents, url: page.url(), currentPageText,
  });
  check(currentState === '提交', 'page did not refresh to the submitted business state', {
    currentState, observedIntents, url: page.url(), currentPageText,
  });
  check(currentTaskText.includes('下一步办理') && currentTaskText.includes('审批处理'),
    'post-submit next step was not refreshed from authoritative facts', currentTaskText);
  check(currentTaskText !== beforeTaskText, 'post-submit task and blocker projection did not refresh', {
    beforeTaskText, currentTaskText,
  });
  const executeIntentIndex = observedIntents.lastIndexOf('execute_button');
  const refreshIntents = executeIntentIndex >= 0 ? observedIntents.slice(executeIntentIndex + 1) : [];
  check(refreshIntents.includes('ui.contract.v2') && refreshIntents.includes('api.data'),
    'post-submit contract and record were not refreshed', refreshIntents);

  const submittedRecordSurface = await requireUnique(
    page,
    page.locator(
      `[data-product-page-mode="form"][data-form-model="payment.request"][data-form-record="${recordId}"]`
      + `[data-form-action-id="${actionId}"][data-form-menu-id="${menuId}"]:visible`,
    ),
    `submitted payment form ${recordId}`,
    { timeout: 45000 },
  );
  const regions = await submittedRecordSurface.locator('[data-object-task-page] [data-floorplan-region]').evaluateAll((nodes) => (
    [...new Set(nodes.map((node) => node.getAttribute('data-floorplan-region')).filter(Boolean))]
  ));
  for (const region of ['summary', 'current-task', 'relation', 'activity', 'audit']) {
    check(regions.includes(region), `post-submit Floorplan region missing: ${region}`, regions);
  }
  const auditRegion = await requireUnique(
    page,
    submittedRecordSurface.locator('[data-floorplan-region="audit"]'),
    `payment ${recordId} audit region`,
  );
  const auditDisclosure = await requireUnique(
    page,
    auditRegion.locator('summary'),
    `payment ${recordId} audit disclosure`,
    { enabled: true },
  );
  await auditDisclosure.click();
  await page.waitForFunction(({ recordSelector }) => (
    document.querySelectorAll(`${recordSelector} [data-floorplan-region="audit"] [data-audit-event]`).length >= 1
  ), {
    recordSelector: `[data-product-page-mode="form"][data-form-model="payment.request"][data-form-record="${recordId}"]`,
  }, { timeout: 15000 });
  const auditEvents = await auditRegion.locator('[data-audit-event]').evaluateAll((nodes) => nodes.map((node) => ({
    actor: String(node.querySelector('[data-audit-actor]')?.textContent || '').replace(/\s+/g, ' ').trim(),
    time: String(node.querySelector('[data-audit-time]')?.textContent || '').replace(/\s+/g, ' ').trim(),
    event: String(node.querySelector('[data-audit-event-name]')?.textContent || '').replace(/\s+/g, ' ').trim(),
    result: String(node.querySelector('[data-audit-result]')?.textContent || '').replace(/\s+/g, ' ').trim(),
  })));
  check(auditEvents.length >= 1 && auditEvents.every((event) => event.actor && event.time && event.event && event.result),
    'post-submit audit region has no trustworthy event', auditEvents);
  check(mutations.length === 1 && mutations[0].params?.button?.name === 'action_submit', 'journey emitted unexpected mutations', mutations);
  check(errors.length === 0, 'browser errors detected', errors);
  await page.screenshot({ path: path.join(outputDir, 'after-submit-390-full.png'), fullPage: true });
  await page.setViewportSize({ width: 1440, height: 960 });
  await waitForViewport(page, 1440);
  enterStage('main:list-after-submit');
  const listRefreshResponse = page.waitForResponse((response) => isListDataResponse(response, 'payment.request'), { timeout: 45000 });
  const readonlyReturn = await requireUnique(page, submittedRecordSurface.getByRole('button', { name: /^返回列表$/ }), 'submitted payment return action', { enabled: true });
  await readonlyReturn.click();
  const refreshedList = await requireUnique(page, page.locator('[data-product-page-mode="list"]:visible'), 'refreshed payment list', { timeout: 45000 });
  await listRefreshResponse;
  await page.waitForFunction(
    ({ name, before }) => {
      const row = [...document.querySelectorAll('[data-product-page-mode="list"] tbody tr')]
        .find((node) => String(node.textContent || '').includes(name));
      return row && String(row.textContent || '').replace(/\s+/g, ' ').trim() !== before;
    },
    { name: record.name, before: listRowBefore },
    { timeout: 45000 },
  );
  const refreshedRow = await requireUnique(
    page,
    refreshedList.locator('tbody tr:visible').filter({ hasText: record.name }),
    `refreshed payment row ${record.name}#${recordId}`,
    { enabled: true, timeout: 45000 },
  );
  const listRowAfter = (await refreshedRow.innerText()).replace(/\s+/g, ' ').trim();
  check(/提交|待审批/.test(listRowAfter) && listRowAfter !== listRowBefore,
    'payment list retained the pre-submit state', { listRowBefore, listRowAfter });
  await page.screenshot({ path: path.join(outputDir, 'after-submit-list-desktop.png'), fullPage: true });

  enterStage('main:home-after-submit');
  await page.goto(`${frontendUrl}/`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const refreshedHome = await requireUnique(page, page.locator('[data-role-home]:visible'), 'refreshed role home', { timeout: 45000 });
  await refreshedHome.locator('.role-home-surface__tasks .role-home-surface__state, .role-home-surface__task-list').waitFor({ timeout: 45000 });
  const homeAfter = {
    tasks: await refreshedHome.locator('.role-home-surface__task-list article').allTextContents(),
    summaries: await refreshedHome.locator('.role-home-surface__summary-list article').allTextContents(),
  };
  const staleHomeTask = homeAfter.tasks.find((text) => text.includes(record.name) && /草稿/.test(text));
  check(!staleHomeTask, 'home todo retained the pre-submit payment state', { homeBefore, homeAfter });
  const executeIntentIndexForHome = observedIntents.lastIndexOf('execute_button');
  check(observedIntents.slice(executeIntentIndexForHome + 1).includes('my.work.summary'),
    'home todo was not reloaded after the payment transition', observedIntents);
  await page.screenshot({ path: path.join(outputDir, 'after-submit-home-desktop.png'), fullPage: true });
  const cleanupIds = [createdId];
  const cleanup = await unlinkPaymentRequests(page, cleanupIds, intentAuthHeaders);
  check(cleanup.status === 200 && cleanup.body?.ok === true,
    'payment create acceptance cleanup failed', { cleanupIds, cleanup });
  createdRecordCleaned = true;
  report.regions = regions;
  report.statusSummary = statusSummaryText;
  report.currentTask = currentTaskText;
  report.auditEvents = auditEvents;
  report.mutations = mutations;
  report.errors = errors;
  report.observedIntents = observedIntents;
  report.stateVariants = stateVariants;
  report.list = { before: listRowBefore, after: listRowAfter };
  report.leaveProtection = leaveProtection;
  report.relationQueryTrace = relationQueryTrace;
  report.relationContextTrace = relationContextTrace;
  report.create = {
    editableFields: createEditableFields,
    metrics: createMetrics,
    mutations: recordCreates,
    createdId,
    routeAfterSave: `/f/payment.request/${createdId}`,
    relationAuthorities: createRelationAuthorities,
    cleanup: { ids: cleanupIds, ...cleanup },
    authorityGaps: [
      'payment basis alternative constraint is not structured in Contract V2',
      'payment account completion stage is not structured in Contract V2',
    ],
  };
  report.home = { before: homeBefore, after: homeAfter };
  report.pass = true;
  fs.writeFileSync(path.join(outputDir, 'summary.json'), `${JSON.stringify(report, null, 2)}\n`);
  console.log(`[local.dev.payment.floorplan.submit] PASS record=${recordId} transition=draft->submit mutations=${mutations.length}`);
} catch (error) {
  report.failure = error instanceof Error ? error.message : String(error);
  report.failureDiagnostics = await runtimeDiagnostics(page, {
    requestCounts: {
      executeMutations: mutations.length,
      paymentWrites: recordWrites.length,
      paymentCreates: recordCreates.length,
      observedIntents: observedIntents.length,
    },
  }).catch((diagnosticError) => ({
    stage: currentStage,
    url: page.url(),
    diagnosticFailure: diagnosticError instanceof Error ? diagnosticError.message : String(diagnosticError),
  }));
  report.mutations = mutations;
  report.recordWrites = recordWrites;
  report.recordCreates = recordCreates;
  report.errors = errors;
  report.observedIntents = observedIntents;
  fs.writeFileSync(path.join(outputDir, 'summary.json'), `${JSON.stringify(report, null, 2)}\n`);
  await page.screenshot({ path: path.join(outputDir, 'failure.png'), fullPage: true }).catch(() => {});
  throw error;
} finally {
  if (createdId > 0 && !createdRecordCleaned) {
    await unlinkPaymentRequests(page, [createdId], intentAuthHeaders).catch(() => undefined);
  }
  await context.close();
  await browser.close();
}
