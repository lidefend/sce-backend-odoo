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
const recordId = Number(target?.record?.id || 0);
const model = 'payment.request';
const outputDir = path.resolve('artifacts/playwright/local-dev-payment-request-floorplan');

function check(value, message, details = undefined) {
  if (value) return;
  throw new Error(`${message}${details === undefined ? '' : ` ${JSON.stringify(details)}`}`);
}

function normalize(value) {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

function findKey(value, key) {
  if (!value || typeof value !== 'object') return undefined;
  if (Object.prototype.hasOwnProperty.call(value, key)) return value[key];
  for (const child of Object.values(value)) {
    const found = findKey(child, key);
    if (found !== undefined) return found;
  }
  return undefined;
}

function collectSemanticRoles(value, rows = []) {
  if (Array.isArray(value)) {
    value.forEach((item) => collectSemanticRoles(item, rows));
    return rows;
  }
  if (!value || typeof value !== 'object') return rows;
  const role = value.formStructureRole?.role || value.semanticRole || value.semantic_role;
  if (role) rows.push({
    role: String(role),
    identity: String(value.widgetId || value.containerId || value.fieldCode || value.name || value.key || ''),
  });
  Object.values(value).forEach((item) => collectSemanticRoles(item, rows));
  return rows;
}

function collectNodeKindCounts(value, counts = {}) {
  if (Array.isArray(value)) {
    value.forEach((item) => collectNodeKindCounts(item, counts));
    return counts;
  }
  if (!value || typeof value !== 'object') return counts;
  const kind = value.containerType || value.widgetType || value.nodeType;
  if (kind) counts[String(kind)] = (counts[String(kind)] || 0) + 1;
  Object.values(value).forEach((item) => collectNodeKindCounts(item, counts));
  return counts;
}

check(frontendUrl && database && password && login, 'local.dev floorplan identity is incomplete');
check(actionId > 0 && menuId > 0 && recordId > 0, 'local.dev floorplan target is invalid', target);
fs.mkdirSync(outputDir, { recursive: true });

const browser = await launchChromium({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
const page = await context.newPage();
const errors = [];
const mutations = [];
const intentBodies = new Map();
const dataListExchanges = [];

page.on('console', (message) => {
  if (message.type() === 'error' && !message.text().includes('favicon')) errors.push(message.text());
});
page.on('pageerror', (error) => errors.push(error.message));
page.on('request', (request) => {
  if (request.method() !== 'POST') return;
  let payload = {};
  try { payload = JSON.parse(request.postData() || '{}'); } catch {}
  const intent = String(payload?.intent || '');
  const method = String(payload?.params?.method || payload?.method || '');
  if (/(^|\.)(create|write|unlink|execute_button|onchange|upload)(\.|$)/.test(intent)
      || /^(create|write|unlink|web_save|action_)/.test(method)) {
    mutations.push({ url: request.url(), intent, method });
  }
});
page.on('response', async (response) => {
  if (!response.url().includes('/api/v1/intent')) return;
  let payload = {};
  try { payload = JSON.parse(response.request().postData() || '{}'); } catch {}
  const intent = String(payload?.intent || '');
  const operation = String(payload?.params?.op || payload?.op || '');
  if (intent === 'api.data' && operation === 'list') {
    try { dataListExchanges.push({ request: payload, response: await response.json() }); } catch {}
    return;
  }
  if (!['system.init', 'ui.contract.v2'].includes(intent)) return;
  try {
    const body = await response.json();
    const rows = intentBodies.get(intent) || [];
    rows.push(body);
    intentBodies.set(intent, rows);
  } catch {}
});

const report = { schemaVersion: 'payment_request_floorplan_readonly.v1', target, frontendUrl, database, pass: false };
try {
  await page.goto(`${frontendUrl}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const inputs = page.locator('input');
  await inputs.nth(0).fill(login);
  await inputs.nth(1).fill(password);
  if (await inputs.nth(2).count() && !(await inputs.nth(2).isDisabled())) await inputs.nth(2).fill(database);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 30000 });

  await page.goto(`${frontendUrl}/`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.locator('[data-role-home]').waitFor({ timeout: 45000 });
  await page.locator('.role-home-surface__link-list--quick button').first().waitFor({ timeout: 45000 });
  const homeQuickLinks = await page.locator('.role-home-surface__link-list--quick button').evaluateAll((nodes) => nodes.map((node) => ({
    label: String(node.querySelector('strong')?.textContent || '').trim(),
    detail: String(node.querySelector('small')?.textContent || '').trim(),
  })));
  report.home = { quickLinks: homeQuickLinks };
  check(!homeQuickLinks.some((item) => item.label === '工作台' && item.detail === '数据总览'),
    'workspace shortcut still pairs a directory label with a descendant target', homeQuickLinks);
  check(!homeQuickLinks.some((item) => item.label === '项目中心' && item.detail === '新项目立项'),
    'project shortcut still pairs a directory label with a different target', homeQuickLinks);
  await page.screenshot({ path: path.join(outputDir, 'workspace-home-desktop.png'), fullPage: true });

  await page.goto(`${frontendUrl}/a/${actionId}?menu_id=${menuId}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.locator('[data-product-page-mode="list"]').first().waitFor({ timeout: 45000 });
  const targetRow = page.locator('tbody tr').filter({ hasText: String(target.record.name || '') }).first();
  await targetRow.waitFor({ timeout: 45000 });
  const listSurface = page.locator('[data-product-page-mode="list"][data-list-status]').first();
  const listText = normalize(await listSurface.innerText());
  const listActions = await listSurface.locator('button:visible, a:visible')
    .allTextContents();
  const amountCellIndex = await listSurface.locator('th[data-column="request_amount_display"]').first().evaluate((node) => node.cellIndex);
  const amountCellText = normalize(await targetRow.locator('td').nth(amountCellIndex).innerText());
  const amountCellValue = Number(amountCellText.replace(/[^\d.-]/g, ''));
  const emptyAggregateFooterRows = await listSurface.locator('tfoot tr').filter({ hasText: /--/ }).count();
  report.list = {
    text: listText,
    actions: listActions.map(normalize).filter(Boolean),
    targetRow: { amountCellText, amountCellValue },
    emptyAggregateFooterRows,
    dataListExchanges,
  };
  check(report.list.actions.includes('新建'), 'authorized payment list did not expose create action', report.list.actions);
  check(Number.isFinite(amountCellValue) && Math.abs(amountCellValue - Number(target.record.amount || 0)) < 0.01,
    'list semantic amount does not match the authoritative record amount', report.list.targetRow);
  check(emptyAggregateFooterRows === 0,
    'payment list exposed aggregate rows without authoritative values', report.list);
  for (const forbidden of ['runtime_status', 'direct delivery', 'payment_entry']) {
    check(!listText.toLowerCase().includes(forbidden), `technical product text is visible in list: ${forbidden}`);
  }
  await page.screenshot({ path: path.join(outputDir, 'payment-request-list-desktop.png'), fullPage: true });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(300);
  const listMobileGeometry = await page.evaluate(() => ({
    width: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  report.list.mobile = {
    ...listMobileGeometry,
    overflow: listMobileGeometry.scrollWidth - listMobileGeometry.width,
    createActionCount: await listSurface.getByRole('button', { name: /^新建$/ }).count(),
  };
  check(report.list.mobile.overflow <= 0, '390px payment list has horizontal overflow', report.list.mobile);
  check(report.list.mobile.createActionCount === 1,
    '390px authorized payment list must expose one visible create action', report.list.mobile);
  await page.screenshot({ path: path.join(outputDir, 'payment-request-list-390-full.png'), fullPage: true });
  await page.setViewportSize({ width: 1440, height: 960 });
  await page.waitForTimeout(300);

  const listUrl = page.url();
  const searchInput = listSurface.locator('input[type="search"]:visible').first();
  await searchInput.fill('__floorplan_no_matching_payment_request__');
  await listSurface.getByRole('button', { name: /^搜索$/ }).click();
  await page.locator('[data-product-page-mode="list"][data-list-status="empty"]').waitFor({ timeout: 45000 });
  const emptySurface = page.locator('[data-product-page-mode="list"][data-list-status="empty"]').first();
  const emptyText = normalize(await emptySurface.innerText());
  const emptyCreateCount = await emptySurface.getByRole('button', { name: /^新建$/ }).count();
  report.emptyState = { text: emptyText, createActionCount: emptyCreateCount };
  check(emptyCreateCount === 1, 'authorized empty payment list must expose exactly one create action', report.emptyState);
  await page.screenshot({ path: path.join(outputDir, 'payment-request-list-empty-desktop.png'), fullPage: true });

  await emptySurface.getByRole('button', { name: /^新建$/ }).click();
  const createSurface = page.locator('[data-product-page-mode="form"]').first();
  await createSurface.waitFor({ timeout: 45000 });
  await createSurface.locator('[data-contract-form-driver]').waitFor({ timeout: 45000 });
  const createEditableFields = await createSurface.locator(
    'input:not([type="hidden"]):not(:disabled), textarea:not(:disabled), select:not(:disabled)',
  ).count();
  const createText = normalize(await createSurface.innerText());
  const createInternalIdentityPlaceholders = await createSurface.locator(
    '[data-field-state="readonly"] input, [data-field-state="readonly"] textarea',
  ).evaluateAll((nodes) => nodes
    .map((node) => String(node.value || '').trim())
    .filter((value) => ['new', '/'].includes(value.toLowerCase())));
  const createFieldOccurrences = await createSurface.locator('[data-field-name]').evaluateAll((nodes) => nodes.map((node) => ({
    name: node.getAttribute('data-field-name'),
    state: node.getAttribute('data-field-state'),
    nodeId: node.closest('[data-canonical-node-id]')?.getAttribute('data-canonical-node-id') || '',
  })));
  report.emptyState.createPath = {
    url: page.url(),
    editableFields: createEditableFields,
    text: createText,
    internalIdentityPlaceholders: createInternalIdentityPlaceholders,
    fieldOccurrences: createFieldOccurrences,
  };
  check(createEditableFields > 0, 'empty-state create action did not open an editable business form', report.emptyState.createPath);
  check(!createText.split('\n').some((line) => /^[.·•:_-]+$/.test(line.trim())),
    'create Floorplan exposed native punctuation placeholders', report.emptyState.createPath);
  check(createInternalIdentityPlaceholders.length === 0,
    'create Floorplan exposed an internal untranslated identity placeholder', report.emptyState.createPath);
  await page.screenshot({ path: path.join(outputDir, 'payment-request-create-desktop.png'), fullPage: true });

  await page.goto(listUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.locator('[data-product-page-mode="list"]').first().waitFor({ timeout: 45000 });
  await targetRow.waitFor({ timeout: 45000 });
  await targetRow.click();
  await page.waitForURL((url) => (
    url.pathname === `/r/${model}/${recordId}`
    && url.searchParams.get('action_id') === String(actionId)
    && url.searchParams.get('menu_id') === String(menuId)
  ), { timeout: 45000 });
  await page.locator('[data-object-task-page]').waitFor({ timeout: 45000 });

  const systemInit = (intentBodies.get('system.init') || []).at(-1);
  const listContract = (intentBodies.get('ui.contract.v2') || []).find((body) => ['tree', 'list'].includes(findKey(body, 'viewType')));
  const formContract = (intentBodies.get('ui.contract.v2') || [])
    .filter((body) => findKey(body, 'viewType') === 'form')
    .at(-1);
  check(systemInit, 'system.init response was not observed');
  check(findKey(systemInit, 'role_surface'), 'system.init omitted role_surface');
  check(findKey(systemInit, 'default_route'), 'system.init omitted default_route');
  check(formContract, 'form ui.contract.v2 response was not observed');
  check(listContract, 'list ui.contract.v2 response was not observed');
  const columnsSchema = findKey(listContract, 'columns_schema');
  report.list.contract = {
    traceId: findKey(listContract, 'trace_id'),
    amountColumn: Array.isArray(columnsSchema)
      ? columnsSchema.find((row) => row?.name === 'request_amount_display')
      : null,
    rows: findKey(listContract, 'rows'),
  };

  const host = page.locator('.sc-form-driver-host');
  const regions = await page.locator('[data-object-task-page] [data-floorplan-region]').evaluateAll((nodes) => (
    [...new Set(nodes.map((node) => node.getAttribute('data-floorplan-region')).filter(Boolean))]
  ));
  const desktop = await page.evaluate(() => ({ width: document.documentElement.clientWidth, scrollWidth: document.documentElement.scrollWidth }));
  const bodyText = normalize(await page.locator('[data-object-task-page]').innerText());
  const enabledPrimary = await page.locator('[data-object-task-page] [data-action-tier="primary"][data-action-enabled="true"]').count();
  const continueProcessing = await page.locator('[data-form-mode-action="edit"]:visible').count();
  const readonlyEditableControlLocator = page.locator([
    '[data-object-task-page] input:visible:not([readonly]):not([disabled])',
    '[data-object-task-page] textarea:visible:not([readonly]):not([disabled])',
    '[data-object-task-page] select:visible:not([disabled])',
    '.contract-field-group-rename input:visible:not([disabled])',
    '.field-label-editor:visible:not([disabled])',
  ].join(', '));
  const readonlyEditableControls = await readonlyEditableControlLocator.count();
  const readonlyEditableControlDetails = await readonlyEditableControlLocator.evaluateAll((nodes) => nodes.map((node) => ({
    tag: node.tagName.toLowerCase(),
    type: node.getAttribute('type') || '',
    className: String(node.className || ''),
    ariaLabel: node.getAttribute('aria-label') || '',
    field: node.closest('[data-field-name]')?.getAttribute('data-field-name') || '',
    region: node.closest('[data-floorplan-region]')?.getAttribute('data-floorplan-region') || '',
  })));
  const readonlyStatusButtons = await page.locator('.native-statusbar-track button:visible').count();
  const leakedConfigurationLabels = {};
  for (const label of ['匹配提示显示名称', '付款申请明细显示名称', '付款记录显示名称']) {
    leakedConfigurationLabels[label] = await page.locator(`[data-object-task-page] [aria-label="${label}"]`).count();
  }
  const readonlyActivityWriteActions = await page.locator(
    '[data-floorplan-region="activity"] button:visible',
  ).filter({ hasText: /记录沟通|备注|计划|上传/ }).count()
    + await page.locator('[data-floorplan-region="activity"] input[type="file"]').count();
  const emptyReadonlyControls = await page.locator([
    '[data-object-task-page] input:disabled',
    '[data-object-task-page] textarea:disabled',
    '[data-object-task-page] select:disabled',
  ].join(', ')).evaluateAll((nodes) => nodes.filter((node) => {
    if (node instanceof HTMLInputElement && ['checkbox', 'radio'].includes(node.type)) return false;
    return !String(node.value || '').trim();
  }).length);
  const emptyReadonlyRelations = await page.locator('[data-readonly-relation-empty]').count();
  const semanticTitles = (await page.locator('[data-object-task-page] h1:visible, [data-object-task-page] h2:visible, [data-object-task-page] h3:visible')
    .allTextContents()).map(normalize).filter(Boolean);
  const duplicateSemanticTitles = semanticTitles.filter((title, index) => semanticTitles.indexOf(title) !== index);
  const canonicalActions = await page.locator('[data-object-task-page] [data-action-ref]').evaluateAll((nodes) => nodes.map((node) => ({
    label: String(node.textContent || '').trim(),
    actionRef: node.getAttribute('data-action-ref'),
    tier: node.getAttribute('data-action-tier'),
    enabled: node.getAttribute('data-action-enabled'),
  })));
  report.desktop = {
    driver: await host.getAttribute('data-contract-form-driver'),
    providerKit: await page.locator('.scene-ui-provider').getAttribute('data-scene-ui-kit'),
    regions,
    enabledPrimary,
    continueProcessing,
    readonlyEditableControls,
    readonlyEditableControlDetails,
    readonlyStatusButtons,
    leakedConfigurationLabels,
    readonlyActivityWriteActions,
    emptyReadonlyControls,
    emptyReadonlyRelations,
    semanticTitles,
    duplicateSemanticTitles,
    effectivePrimaryActions: enabledPrimary + continueProcessing,
    canonicalActions,
    overflow: desktop.scrollWidth - desktop.width,
  };
  check(report.desktop.driver === 'tdesign-modern', 'readonly product driver is not TDesign', report.desktop);
  check(report.desktop.providerKit === 'tdesign-modern', 'TDesign provider did not load', report.desktop);
  for (const region of ['summary', 'current-task', 'business-context', 'relation', 'activity', 'audit']) {
    check(regions.includes(region), `floorplan region missing: ${region}`, regions);
  }
  check(enabledPrimary === 0, 'the governed blocked record exposed a false executable primary action', enabledPrimary);
  check(continueProcessing === 1, 'the governed blocked record must expose one path to complete missing facts', continueProcessing);
  check(readonlyEditableControls === 0, 'readonly product surface exposes editable field/configuration controls', readonlyEditableControls);
  check(readonlyStatusButtons === 0, 'readonly product surface renders workflow states as buttons', readonlyStatusButtons);
  check(Object.values(leakedConfigurationLabels).every((count) => count === 0),
    'readonly product surface exposes configuration display-name controls', leakedConfigurationLabels);
  check(readonlyActivityWriteActions === 0,
    'readonly activity surface exposes write actions', readonlyActivityWriteActions);
  check(emptyReadonlyControls === 0,
    'readonly product surface exposes empty disabled controls', emptyReadonlyControls);
  check(duplicateSemanticTitles.length === 0,
    'readonly product surface repeats semantic section titles', duplicateSemanticTitles);
  check(enabledPrimary + continueProcessing === 1, 'more than one product primary action is visible', { enabledPrimary, continueProcessing });
  check(canonicalActions.filter((action) => action.label === '取消').length === 1,
    'the same authoritative cancel operation appeared twice', canonicalActions);
  check(report.desktop.overflow <= 0, 'desktop has horizontal overflow', report.desktop);
  check(await page.locator('[data-contract-form-driver-chooser]').count() === 0, 'component supplier chooser reached product surface');
  check(await page.locator('.workflow-evidence-block').count() === 0,
    'legacy workflow evidence block is still competing with the decision Floorplan');
  check(await page.locator('[data-floorplan-region="summary"] input:disabled, [data-floorplan-region="summary"] textarea:disabled').count() === 0,
    'readonly summary was rendered as disabled form controls');
  const summaryLabels = await page.locator('[data-floorplan-region="summary"] .field-label').allTextContents();
  check(new Set(summaryLabels.map(normalize)).size === summaryLabels.length, 'summary contains duplicate business facts', summaryLabels);
  check(!bodyText.split('\n').some((line) => /^[.·•:_-]+$/.test(line.trim())), 'native punctuation leaked into the product floorplan');
  for (const forbidden of ['runtime_status', 'direct delivery', 'payment_entry', 'legacy_source_table', 'legacy_record_id', 'tdesign-modern', 'sc-native', 'ui5-horizon']) {
    check(!bodyText.toLowerCase().includes(forbidden), `technical product text is visible: ${forbidden}`);
  }
  check(bodyText.includes('缺少合同或结算依据'), 'authoritative blocker is not visible before the action surface', bodyText);
  const auditDisclosure = page.locator('[data-floorplan-region="audit"]').first();
  await auditDisclosure.locator('summary').click();
  await auditDisclosure.locator('[data-audit-event]').first().waitFor({ timeout: 15000 });
  const auditEvents = await auditDisclosure.locator('[data-audit-event]').evaluateAll((nodes) => nodes.map((node) => ({
    actor: String(node.querySelector('[data-audit-actor]')?.textContent || '').replace(/\s+/g, ' ').trim(),
    time: String(node.querySelector('[data-audit-time]')?.textContent || '').replace(/\s+/g, ' ').trim(),
    event: String(node.querySelector('[data-audit-event-name]')?.textContent || '').replace(/\s+/g, ' ').trim(),
    result: String(node.querySelector('[data-audit-result]')?.textContent || '').replace(/\s+/g, ' ').trim(),
  })));
  report.desktop.auditEvents = auditEvents;
  check(auditEvents.length >= 1, 'readonly audit region has no trustworthy event', auditEvents);
  check(auditEvents.every((event) => event.actor && event.time && event.event && event.result),
    'audit event must contain actor, time, event and result', auditEvents);
  check(!auditEvents.some((event) => /(^|[._:-])action_|payment_[a-z_]+/i.test(`${event.event} ${event.result}`)),
    'technical audit identifiers reached the product surface', auditEvents);
  const submitRules = (findKey(formContract, 'actionRuleList') || []).filter((rule) => (
    rule?.button?.name === 'action_submit'
  ));
  const nativeSubmit = submitRules.find((rule) => String(rule?.backendIdentity || '').startsWith('native_button:'));
  check(nativeSubmit && nativeSubmit.allowed === false && nativeSubmit.enabled === false && nativeSubmit.disabled === true,
    'runtime business unavailability did not govern the native submit occurrence', submitRules);
  check(nativeSubmit?.actionSafety?.requires_confirm === true,
    'runtime business safety did not govern the native submit occurrence', nativeSubmit);
  await page.screenshot({ path: path.join(outputDir, 'payment-request-desktop.png'), fullPage: true });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(300);
  const mobile = await page.evaluate(() => ({ width: document.documentElement.clientWidth, scrollWidth: document.documentElement.scrollWidth }));
  const mobileActionSurface = page.locator('[data-mobile-action-surface]').first();
  const mobilePrimary = mobileActionSurface.locator('[data-action-tier="primary"][data-action-enabled="true"]');
  const mobileActionMetrics = await mobileActionSurface.evaluate((node) => {
    const rect = node.getBoundingClientRect();
    const style = getComputedStyle(node);
    return {
      position: style.position,
      top: rect.top,
      right: rect.right,
      bottom: rect.bottom,
      left: rect.left,
      viewportHeight: window.innerHeight,
      viewportWidth: window.innerWidth,
    };
  });
  report.mobile = {
    ...mobile,
    overflow: mobile.scrollWidth - mobile.width,
    enabledPrimary: await mobilePrimary.count(),
    actionSurface: mobileActionMetrics,
  };
  check(report.mobile.overflow <= 0, '390px viewport has horizontal overflow', report.mobile);
  check(report.mobile.enabledPrimary === 0, '390px action surface exposed a false executable primary action', report.mobile);
  check(mobileActionMetrics.position === 'fixed', '390px action surface is not fixed to the viewport', report.mobile);
  check(mobileActionMetrics.left >= -1 && mobileActionMetrics.right <= mobileActionMetrics.viewportWidth + 1,
    '390px action surface exceeds the viewport width', report.mobile);
  check(Math.abs(mobileActionMetrics.bottom - mobileActionMetrics.viewportHeight) <= 1,
    '390px action surface is not anchored to the viewport bottom', report.mobile);
  await page.screenshot({ path: path.join(outputDir, 'payment-request-390.png') });
  await page.screenshot({ path: path.join(outputDir, 'payment-request-390-full.png'), fullPage: true });

  report.contract = {
    roleCode: findKey(systemInit, 'role_code'),
    defaultRoute: findKey(systemInit, 'default_route'),
    navigation: findKey(systemInit, 'nav'),
    traceId: findKey(formContract, 'trace_id'),
    semanticRoles: collectSemanticRoles(formContract),
    nodeKindCounts: collectNodeKindCounts(formContract),
    actionRules: findKey(formContract, 'actionRuleList'),
  };
  report.errors = errors;
  report.mutations = mutations;
  check(errors.length === 0, 'browser errors detected', errors);
  check(mutations.length === 0, 'readonly journey attempted a business mutation', mutations);
  report.pass = true;
  fs.writeFileSync(path.join(outputDir, 'summary.json'), `${JSON.stringify(report, null, 2)}\n`);
  console.log(`[local.dev.payment.floorplan] PASS regions=${regions.length} blocked_primary=${enabledPrimary} mobile_overflow=${report.mobile.overflow}`);
} catch (error) {
  report.errors = errors;
  report.mutations = mutations;
  report.failure = error instanceof Error ? error.message : String(error);
  fs.writeFileSync(path.join(outputDir, 'summary.json'), `${JSON.stringify(report, null, 2)}\n`);
  await page.screenshot({ path: path.join(outputDir, 'failure.png'), fullPage: true }).catch(() => {});
  throw error;
} finally {
  await context.close();
  await browser.close();
}
