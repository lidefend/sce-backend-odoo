import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { launchChromium } from './playwright_runtime.mjs';

const target = JSON.parse(process.env.FRONTEND_MATERIAL_DOMAIN_TARGET || '{}');
const frontendUrl = process.env.FRONTEND_URL || '';
const database = process.env.DB_NAME || '';
const password = process.env.E2E_PASSWORD || '';
const outputDir = path.resolve(process.env.FRONTEND_MATERIAL_DOMAIN_OUTPUT_DIR || 'artifacts/playwright/phase10-material-domain');
const sampleReview = process.env.FRONTEND_MATERIAL_SAMPLE_REVIEW === '1';
const evidenceCaptureReview = process.env.FRONTEND_MATERIAL_EVIDENCE_CAPTURE === '1';
const handlingReview = process.env.FRONTEND_MATERIAL_HANDLING_REVIEW === '1';
const sharedRegressionReview = process.env.FRONTEND_MATERIAL_SHARED_REGRESSION === '1';
const sampleViewports = (process.env.FRONTEND_MATERIAL_SAMPLE_VIEWPORTS || '1440x960,1088x960')
  .split(',')
  .map((value) => value.trim().match(/^(\d+)x(\d+)$/))
  .filter(Boolean)
  .map((match) => ({ width: Number(match[1]), height: Number(match[2]) }));
const handlingViewports = (process.env.FRONTEND_MATERIAL_HANDLING_VIEWPORTS || '1440x960,390x844')
  .split(',')
  .map((value) => value.trim().match(/^(\d+)x(\d+)$/))
  .filter(Boolean)
  .map((match) => ({ width: Number(match[1]), height: Number(match[2]) }));
const handlingThemes = (process.env.FRONTEND_MATERIAL_HANDLING_THEMES || 'light')
  .split(',')
  .map((value) => value.trim())
  .filter((value) => value === 'light' || value === 'dark');

const handlingEntrySpecs = Object.freeze({
  inbound: {
    identityToken: '入库', detailTitle: '入库明细', tabs: ['入库明细', '说明与附件', '来源追溯'],
    nativeTitles: ['入库主信息', '项目与供应商', '入库明细', '说明与附件', '来源追溯'],
    sourceFields: ['stock_picking_id', 'source_transfer_outbound_id', 'legacy_fact_model', 'source_created_by', 'source_created_at'],
    buttons: ['action_submit', 'action_receive', 'action_reset_draft', 'action_cancel', 'action_load_acceptance_lines'],
    facts: ['project_id', 'inbound_date', 'supplier_id', 'warehouse_id', 'dest_location_id'],
    viewId: 1428,
  },
  outbound: {
    identityToken: '出库', detailTitle: '材料明细', tabs: ['材料明细', '说明与附件', '来源追溯'],
    nativeTitles: ['出退库主信息', '材料明细', '说明与附件', '来源追溯'],
    sourceFields: ['stock_picking_id', 'transfer_inbound_id', 'legacy_fact_model', 'source_created_by', 'source_created_at'],
    buttons: ['action_submit', 'action_issue', 'action_reset_draft', 'action_cancel'],
    facts: ['project_id', 'outbound_date', 'warehouse_id', 'source_location_id', 'receiver_id'],
    viewId: 1431,
  },
  return: {
    identityToken: '退库', detailTitle: '材料明细', tabs: ['材料明细', '说明与附件', '来源追溯'],
    nativeTitles: ['出退库主信息', '材料明细', '说明与附件', '来源追溯'],
    sourceFields: ['stock_picking_id', 'transfer_inbound_id', 'legacy_fact_model', 'source_created_by', 'source_created_at'],
    buttons: ['action_submit', 'action_issue', 'action_reset_draft', 'action_cancel'],
    facts: ['project_id', 'outbound_date', 'warehouse_id', 'source_location_id', 'receiver_id'],
    viewId: 1431,
  },
});
const sharedEntrySpecs = Object.freeze({
  project_profile: {
    identityToken: '项目',
    ordinaryFields: ['name', 'project_code', 'project_type_id', 'operation_strategy', 'location'],
  },
  personnel_profile: {
    identityToken: '人员',
    ordinaryFields: ['name', 'phone', 'email', 'sc_personnel_department_id', 'sc_personnel_job_id'],
  },
  payment_request: {
    identityToken: '付款',
    ordinaryFields: ['name', 'project_id', 'partner_id', 'request_date', 'amount'],
  },
});

function check(value, message, details) {
  if (!value) throw new Error(`${message}${details === undefined ? '' : ` ${JSON.stringify(details)}`}`);
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

function screenshotEvidence() {
  return fs.readdirSync(outputDir)
    .filter((name) => name.endsWith('.png'))
    .sort()
    .map((name) => ({
      path: name,
      sha256: createHash('sha256').update(fs.readFileSync(path.join(outputDir, name))).digest('hex'),
    }));
}

async function login(page, loginName) {
  await page.goto(`${frontendUrl}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const inputs = page.locator('input');
  await inputs.nth(0).fill(loginName);
  await inputs.nth(1).fill(password);
  if (await inputs.nth(2).count() && !(await inputs.nth(2).isDisabled())) await inputs.nth(2).fill(database);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 30000 });
  await page.locator('[data-semantic-component="ProductAppShell"]:visible').first().waitFor({ timeout: 45000 });
}

function observe(page, evidence) {
  page.on('console', (message) => {
    if (message.type() === 'error' && !message.text().includes('favicon')) evidence.errors.push(message.text());
  });
  page.on('pageerror', (error) => evidence.errors.push(error.message));
  page.on('response', (response) => {
    if (response.status() >= 400) evidence.errors.push(`http ${response.status()} ${response.url()}`);
  });
  page.on('request', (request) => {
    if (request.method() !== 'POST') return;
    let body = {};
    try { body = JSON.parse(request.postData() || '{}'); } catch {}
    const intent = String(body?.intent || '');
    const method = String(body?.params?.method || body?.method || '');
    if (/(^|\.)(create|write|unlink|execute_button|upload)(\.|$)/.test(intent)
      || /^(create|write|unlink|web_save|action_)/.test(method)) {
      evidence.mutations.push({ intent, method, url: request.url() });
    }
  });
  page.on('response', async (response) => {
    if (!response.url().includes('/api/v1/intent')) return;
    let requestBody = {};
    try { requestBody = JSON.parse(response.request().postData() || '{}'); } catch {}
    if (requestBody?.intent === 'ui.contract.v2') {
      try { evidence.contracts.push(await response.json()); } catch {}
    }
  });
}

check(frontendUrl && database && password, 'material domain browser identity is incomplete');
check(target?.user?.login && target?.security_user?.login, 'material domain users are missing', target);
check(Number(target?.action?.id) > 0 && Number(target?.menu?.id) > 0, 'material domain entry is missing', target);
check(Number(target?.record?.id) > 0, 'material domain record is missing', target);
if (handlingReview) {
  for (const key of Object.keys(handlingEntrySpecs)) {
    const entry = target?.entries?.[key];
    check(entry?.model && Number(entry?.action?.id) > 0 && Number(entry?.menu?.id) > 0,
      `material handling entry is missing: ${key}`, entry);
  }
}
if (sharedRegressionReview) {
  for (const key of Object.keys(sharedEntrySpecs)) {
    const entry = target?.shared_entries?.[key];
    check(entry?.model && entry?.record && Number(entry?.action?.id) > 0 && Number(entry?.menu?.id) > 0,
      `material shared regression entry is missing: ${key}`, entry);
  }
}
fs.mkdirSync(outputDir, { recursive: true });

const browser = await launchChromium({ headless: true });
const report = {
  schemaVersion: 'frontend_material_domain_browser.v1',
  head: process.env.CANDIDATE_HEAD || '',
  worktreeFingerprint: process.env.CANDIDATE_WORKTREE_FINGERPRINT || '',
  startedAt: new Date().toISOString(),
  completedAt: '',
  reviewMode: sharedRegressionReview
    ? 'material_shared_renderer_regression'
    : handlingReview
    ? 'material_handling_affected_regions'
    : evidenceCaptureReview
    ? 'inbound_evidence_capture_only'
    : sampleReview ? 'inbound_sample_affected_regions' : 'full_material_domain',
  target: { user: target.user, securityUser: target.security_user, action: target.action, menu: target.menu, record: target.record },
  primary: { errors: [], mutations: [], contracts: [] },
  security: { errors: [], mutations: [], contracts: [] },
  pass: false,
};

async function absoluteTop(locator) {
  return locator.evaluate((element) => element.getBoundingClientRect().top + window.scrollY);
}

async function selectNativeMaterialTab(form, label) {
  const trigger = form.locator(`[data-section-tab="${label}"]:visible`).first();
  await trigger.waitFor({ timeout: 15000 });
  await trigger.click();
  await form.locator('.native-tab-panel:visible').first().waitFor({ timeout: 15000 });
}

async function selectedNativeMaterialTab(form) {
  return (await form.locator('[data-section-tab].native-tab--active:visible').first().innerText()).trim();
}

async function scrollPosition(page, form) {
  return page.evaluate((formElement) => {
    const routerHost = formElement.closest('.router-host') || document.querySelector('.router-host');
    const scrollingElement = document.scrollingElement;
    return {
      owner: routerHost instanceof HTMLElement ? '.router-host' : 'window',
      routerHost: routerHost instanceof HTMLElement ? {
        scrollTop: routerHost.scrollTop,
        clientHeight: routerHost.clientHeight,
        scrollHeight: routerHost.scrollHeight,
      } : null,
      document: {
        scrollTop: scrollingElement?.scrollTop || 0,
        clientHeight: scrollingElement?.clientHeight || 0,
        scrollHeight: scrollingElement?.scrollHeight || 0,
      },
      formTop: formElement.getBoundingClientRect().top,
      headingTop: formElement.querySelector('h1')?.getBoundingClientRect().top ?? null,
    };
  }, await form.elementHandle());
}

async function resetActualScrollTop(page, form) {
  await page.evaluate((formElement) => {
    const routerHost = formElement.closest('.router-host') || document.querySelector('.router-host');
    if (routerHost instanceof HTMLElement) routerHost.scrollTop = 0;
    window.scrollTo(0, 0);
  }, await form.elementHandle());
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  const position = await scrollPosition(page, form);
  check(position.routerHost?.scrollTop === 0 && position.document.scrollTop === 0,
    'material evidence top capture did not reset the actual scroll owners', position);
  return position;
}

async function captureInboundEvidencePage(page, mode, viewport) {
  const actionId = Number(target.action.id);
  const menuId = Number(target.menu.id);
  const recordId = Number(target.record.id);
  const route = mode === 'readonly'
    ? `/f/sc.material.inbound/${recordId}?menu_id=${menuId}&action_id=${actionId}`
    : `/f/sc.material.inbound/new?menu_id=${menuId}&action_id=${actionId}`;
  const contractStart = report.primary.contracts.length;
  await page.goto(`${frontendUrl}${route}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const form = page.locator('[data-product-page-mode="form"]:visible').first();
  await form.locator('[data-contract-form-driver]:visible').first().waitFor({ timeout: 45000 });
  const contract = report.primary.contracts.slice(contractStart)
    .find((body) => findKey(body, 'model') === 'sc.material.inbound' && findKey(body, 'viewType') === 'form');
  const nativeContract = requireInboundNativeContract(contract, actionId, mode);
  const suffix = `${viewport.width}x${viewport.height}-${mode}`;

  const top = await resetActualScrollTop(page, form);
  const topSelectedTab = await selectedNativeMaterialTab(form);
  await page.screenshot({
    path: path.join(outputDir, `material-inbound-${suffix}-actual-top.png`),
    fullPage: false,
    animations: 'disabled',
  });

  await selectNativeMaterialTab(form, '入库明细');
  const detailTab = form.locator('[data-section-tab="入库明细"]:visible').first();
  await detailTab.scrollIntoViewIfNeeded();
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(resolve)));
  const detail = {
    selectedTab: await selectedNativeMaterialTab(form),
    scroll: await scrollPosition(page, form),
    relationVisible: await form.locator('[data-field-name="line_ids"]:visible').count() === 1,
  };
  check(detail.selectedTab === '入库明细' && detail.relationVisible,
    'material detail tab was not stably selected for evidence capture', detail);
  await page.screenshot({
    path: path.join(outputDir, `material-inbound-${suffix}-detail-selected.png`),
    fullPage: false,
    animations: 'disabled',
  });

  await selectNativeMaterialTab(form, '来源追溯');
  const sourceTab = form.locator('[data-section-tab="来源追溯"]:visible').first();
  await sourceTab.scrollIntoViewIfNeeded();
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(resolve)));
  const source = {
    selectedTab: await selectedNativeMaterialTab(form),
    scroll: await scrollPosition(page, form),
    sourceFieldsVisible: await form.locator([
      '[data-field-name="stock_picking_id"]:visible',
      '[data-field-name="source_transfer_outbound_id"]:visible',
      '[data-field-name="legacy_fact_model"]:visible',
      '[data-field-name="source_created_by"]:visible',
      '[data-field-name="source_created_at"]:visible',
    ].join(', ')).count(),
  };
  check(source.selectedTab === '来源追溯',
    'material source tab was not stably selected for evidence capture', source);
  await page.screenshot({
    path: path.join(outputDir, `material-inbound-${suffix}-source-selected.png`),
    fullPage: false,
    animations: 'disabled',
  });

  const topNavigation = form.locator('[data-form-section-navigation]:visible').first();
  const topDetailLink = topNavigation.getByRole('button', { name: '入库明细', exact: true });
  const topDetailLinkAvailable = await topDetailLink.count() === 1;
  const navigationBehavior = {
    available: topDetailLinkAvailable,
    beforeSelectedTab: await selectedNativeMaterialTab(form),
    beforeScroll: await scrollPosition(page, form),
    targetSelector: topDetailLinkAvailable ? await topDetailLink.getAttribute('data-section-target') : null,
    targetVisibleBefore: 0,
    afterSelectedTab: '',
    afterScroll: null,
    activatedNotebookTab: false,
  };
  if (navigationBehavior.available && navigationBehavior.targetSelector) {
    navigationBehavior.targetVisibleBefore = await form.locator(`${navigationBehavior.targetSelector}:visible`).count();
    await topDetailLink.click();
    await page.waitForTimeout(450);
    navigationBehavior.afterSelectedTab = await selectedNativeMaterialTab(form);
    navigationBehavior.afterScroll = await scrollPosition(page, form);
    navigationBehavior.activatedNotebookTab = navigationBehavior.afterSelectedTab === '入库明细';
  }

  return {
    mode,
    viewport,
    route,
    nativeContract,
    top: { ...top, selectedTab: topSelectedTab },
    detail,
    source,
    navigationBehavior,
  };
}

async function inspectInboundEvidenceCapture() {
  check(sampleViewports.length > 0, 'material evidence capture viewport list is empty');
  report.primary.evidenceCaptures = [];
  for (const viewport of sampleViewports) {
    const context = await browser.newContext({ viewport, locale: 'zh-CN', hasTouch: viewport.width <= 390 });
    const page = await context.newPage();
    observe(page, report.primary);
    await login(page, target.user.login);
    report.primary.evidenceCaptures.push(await captureInboundEvidencePage(page, 'readonly', viewport));
    report.primary.evidenceCaptures.push(await captureInboundEvidencePage(page, 'create', viewport));
    await context.close();
  }
  check(report.primary.errors.length === 0, 'material evidence capture has browser errors', report.primary.errors);
  check(report.primary.mutations.length === 0, 'material evidence capture mutated business data', report.primary.mutations);
  report.primary.contracts = report.primary.contracts.map(inboundNativeContract);
  report.security.result = { skipped: true, reason: 'capture_only_reuses_prior_business_acceptance' };
}

function inboundNativeContract(contract) {
  const structure = findKey(contract, 'formStructureContract') || {};
  const governance = structure?.sourceAuthority?.governance_source || {};
  const titles = [];
  const fieldNames = [];
  const buttonNames = [];
  const walk = (value) => {
    if (Array.isArray(value)) return value.forEach(walk);
    if (!value || typeof value !== 'object') return;
    if (['group', 'page'].includes(String(value.type || ''))) {
      const title = String(value.label || value.title || value.attributes?.string || '').trim();
      if (title) titles.push(title);
    }
    if (String(value.type || '') === 'field' && String(value.name || '')) fieldNames.push(String(value.name));
    if (String(value.type || '') === 'button' && String(value.name || '')) buttonNames.push(String(value.name));
    Object.values(value).forEach(walk);
  };
  walk(findKey(contract, 'containerTree') || []);
  return {
    model: findKey(contract, 'model'),
    viewType: findKey(contract, 'viewType'),
    effectiveRenderProfile: findKey(contract, 'effectiveRenderProfile'),
    effectiveRecordCapabilities: findKey(contract, 'effectiveRecordCapabilities'),
    layoutPolicy: structure.layoutPolicy || '',
    authority: {
      resolvedActionId: Number(governance.resolvedActionId || 0),
      resolvedViewId: Number(governance.resolvedViewId || 0),
      formStructureAuthority: String(governance.formStructureAuthority || ''),
      compatibilityDependencies: governance.compatibilityDependencies || [],
    },
    titles,
    fieldNames: [...new Set(fieldNames)],
    buttonNames: [...new Set(buttonNames)],
  };
}

function requireInboundNativeContract(contract, actionId, profile) {
  const identity = inboundNativeContract(contract);
  check(identity.model === 'sc.material.inbound' && identity.viewType === 'form',
    'material inbound main form contract is missing', identity);
  check(identity.layoutPolicy === 'container_tree_authority'
    && identity.authority.formStructureAuthority === 'native_authority'
    && identity.authority.compatibilityDependencies.length === 0,
  'material inbound still depends on compatibility structure', identity);
  check(identity.authority.resolvedActionId === actionId && identity.authority.resolvedViewId === 1428,
    'material inbound native source identity drifted', identity);
  check(identity.effectiveRenderProfile === profile,
    'material inbound render profile drifted', identity);
  for (const title of ['入库主信息', '项目与供应商', '入库明细', '说明与附件', '来源追溯']) {
    check(identity.titles.includes(title), `material inbound native chapter is missing: ${title}`, identity);
  }
  for (const fieldName of ['stock_picking_id', 'source_transfer_outbound_id', 'legacy_fact_model', 'source_created_by', 'source_created_at']) {
    check(identity.fieldNames.includes(fieldName), `material inbound source field is missing: ${fieldName}`, identity);
  }
  check(identity.buttonNames.includes('action_load_acceptance_lines'),
    'material inbound load-acceptance operation is missing from the native contract', identity);
  return identity;
}

async function inspectInboundSampleViewport(viewport) {
  const context = await browser.newContext({ viewport, locale: 'zh-CN' });
  const page = await context.newPage();
  observe(page, report.primary);
  await login(page, target.user.login);
  const actionId = Number(target.action.id);
  const menuId = Number(target.menu.id);
  const recordId = Number(target.record.id);
  const suffix = String(viewport.width);
  const expectedTabs = ['入库明细', '说明与附件', '来源追溯'];
  const readonlyContractStart = report.primary.contracts.length;

  await page.goto(
    `${frontendUrl}/f/sc.material.inbound/${recordId}?menu_id=${menuId}&action_id=${actionId}`,
    { waitUntil: 'domcontentloaded', timeout: 45000 },
  );
  const readonlyForm = page.locator('[data-product-page-mode="form"]:visible').first();
  await readonlyForm.locator('[data-contract-form-driver]:visible').first().waitFor({ timeout: 45000 });
  const readonlyContract = report.primary.contracts.slice(readonlyContractStart)
    .find((body) => findKey(body, 'model') === 'sc.material.inbound' && findKey(body, 'viewType') === 'form');
  const readonlyNative = requireInboundNativeContract(readonlyContract, actionId, 'readonly');
  const readonlyTabs = (await readonlyForm.locator('[data-section-tab]').allInnerTexts()).map((value) => value.trim());
  check(JSON.stringify(readonlyTabs) === JSON.stringify(expectedTabs),
    'readonly native chapters differ from the source view', readonlyTabs);
  await selectNativeMaterialTab(readonlyForm, '入库明细');
  const readonlyRelation = readonlyForm.locator('[data-field-name="line_ids"]:visible').first();
  await readonlyRelation.waitFor({ timeout: 45000 });
  if (viewport.width <= 390) {
    const disclosure = readonlyRelation.locator('[data-disclosure-trigger]:visible').first();
    if (await disclosure.count()) await disclosure.click();
  }
  const sourceValue = readonlyRelation.getByText('S80-MA-001', { exact: false }).filter({ visible: true }).first();
  await sourceValue.waitFor({ timeout: 45000 });
  const sourceRow = sourceValue.locator(viewport.width <= 390 ? 'xpath=ancestor::article[1]' : 'xpath=ancestor::tr[1]');
  const readonlyStatusFields = await readonlyForm.locator('[data-field-name="state"]:visible').count();
  const readonlySaveActions = await readonlyForm.locator('[data-action-ref="form.save"]:visible').count();
  const detailTitleLocator = readonlyRelation.getByText('入库明细', { exact: true });
  const detailTitleCount = await detailTitleLocator.count();
  const detailTitleOwners = await detailTitleLocator.evaluateAll((elements) => elements.map((element) => ({
    tag: element.tagName,
    className: element.getAttribute('class') || '',
    dataFieldName: element.closest('[data-field-name]')?.getAttribute('data-field-name') || '',
    dataFloorplanRegion: element.closest('[data-floorplan-region]')?.getAttribute('data-floorplan-region') || '',
  })));
  const sourceTitle = (await sourceValue.innerText()).trim();
  const sourceRowHeight = (await sourceRow.boundingBox())?.height ?? null;
  await selectNativeMaterialTab(readonlyForm, '来源追溯');
  const readonlySourceFields = await readonlyForm.locator([
    '[data-field-name="stock_picking_id"]:visible',
    '[data-field-name="source_transfer_outbound_id"]:visible',
    '[data-field-name="legacy_fact_model"]:visible',
    '[data-field-name="source_created_by"]:visible',
    '[data-field-name="source_created_at"]:visible',
  ].join(', ')).count();
  const readonlyResult = {
    url: page.url(), readonlyStatusFields, readonlySaveActions, detailTitleCount, detailTitleOwners,
    sourceTitle, sourceRowHeight, tabs: readonlyTabs, sourceFieldCount: readonlySourceFields,
    nativeContract: readonlyNative,
  };
  check(readonlyStatusFields === 0, 'header-owned status remains duplicated in the readonly body', readonlyResult);
  check(readonlySaveActions === 0 && readonlyNative.effectiveRecordCapabilities?.write === false,
    'terminal inbound sample exposed a write operation', readonlyResult);
  check(detailTitleCount === 1, 'readonly detail title is not owned by exactly one layer', readonlyResult);
  check(Boolean(sourceTitle?.includes('S80-MA-001')), 'readonly source name is not fully accessible', readonlyResult);
  check(viewport.width <= 390 || (sourceRowHeight !== null && sourceRowHeight <= 96),
    'readonly source column still expands a detail row excessively', readonlyResult);
  check(readonlySourceFields >= 1, 'readonly sample exposes no populated source trace fact', readonlyResult);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: path.join(outputDir, `material-inbound-refinement-${suffix}-readonly-top.png`) });
  await selectNativeMaterialTab(readonlyForm, '入库明细');
  await readonlyRelation.screenshot({ path: path.join(outputDir, `material-inbound-refinement-${suffix}-readonly-detail.png`) });
  await selectNativeMaterialTab(readonlyForm, '来源追溯');
  await page.screenshot({ path: path.join(outputDir, `material-inbound-refinement-${suffix}-readonly-source.png`) });

  const createContractStart = report.primary.contracts.length;
  await page.goto(
    `${frontendUrl}/f/sc.material.inbound/new?menu_id=${menuId}&action_id=${actionId}`,
    { waitUntil: 'domcontentloaded', timeout: 45000 },
  );
  const createForm = page.locator('[data-product-page-mode="form"]:visible').first();
  await createForm.locator('[data-contract-form-driver]:visible').first().waitFor({ timeout: 45000 });
  const createContract = report.primary.contracts.slice(createContractStart)
    .find((body) => findKey(body, 'model') === 'sc.material.inbound' && findKey(body, 'viewType') === 'form');
  const createNative = requireInboundNativeContract(createContract, actionId, 'create');
  const createTabs = (await createForm.locator('[data-section-tab]').allInnerTexts()).map((value) => value.trim());
  check(JSON.stringify(createTabs) === JSON.stringify(expectedTabs),
    'create native chapters differ from the source view', createTabs);
  await selectNativeMaterialTab(createForm, '入库明细');
  const createRelation = createForm.locator('[data-field-name="line_ids"]:visible').first();
  await createRelation.waitFor({ timeout: 45000 });
  const factNames = ['project_id', 'inbound_date', 'supplier_id', 'warehouse_id', 'dest_location_id'];
  const factTops = {};
  for (const fieldName of factNames) {
    const field = createForm.locator(`[data-field-name="${fieldName}"]:visible`).first();
    await field.waitFor({ timeout: 45000 });
    factTops[fieldName] = await absoluteTop(field);
  }
  const relationTop = await absoluteTop(createRelation);
  await selectNativeMaterialTab(createForm, '说明与附件');
  const noteInPost = await createForm.locator('[data-field-name="note"]:visible').count();
  const attachmentsInPost = await createForm.locator('[data-field-name="attachment_ids"]:visible').count();
  await selectNativeMaterialTab(createForm, '来源追溯');
  const sourceFieldCount = await createForm.locator([
    '[data-field-name="stock_picking_id"]:visible',
    '[data-field-name="source_transfer_outbound_id"]:visible',
    '[data-field-name="legacy_fact_model"]:visible',
    '[data-field-name="source_created_by"]:visible',
    '[data-field-name="source_created_at"]:visible',
  ].join(', ')).count();
  const createStatusFields = await createForm.locator('[data-field-name="state"]:visible').count();
  const createBodyStatusFields = await createForm.locator('.sc-native-contract-tree [data-field-name="state"]:visible').count();
  const createHeaderStatusbars = await createForm.locator('[data-professional-workflow-component="statusbar"]:visible').count();
  const createSaveActions = await createForm.locator('[data-action-ref="form.save"][data-action-enabled="true"]:visible').count();
  const loadAcceptanceActions = await createForm.getByRole('button', { name: '带入验收明细', exact: true }).count();
  const createResult = {
    url: page.url(), factTops, relationTop, noteInPost, attachmentsInPost, createStatusFields,
    createBodyStatusFields, createHeaderStatusbars, createSaveActions, loadAcceptanceActions,
    sourceFieldCount, tabs: createTabs, nativeContract: createNative,
  };
  check(Object.values(factTops).every((top) => top < relationTop),
    'create key facts are not all before the detail collection', createResult);
  check(noteInPost === 1 && attachmentsInPost === 1,
    'create supplementary section does not own note and attachments', createResult);
  check(createBodyStatusFields + createHeaderStatusbars === 1,
    'material create status does not have exactly one visible owner', createResult);
  check(createSaveActions === 1 && createNative.effectiveRecordCapabilities?.create === true,
    'material create operation capability is unavailable', createResult);
  check(JSON.stringify(readonlyNative.authority) === JSON.stringify(createNative.authority),
    'readonly and create chapters do not share one native source authority', { readonlyNative, createNative });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: path.join(outputDir, `material-inbound-refinement-${suffix}-create-top.png`) });
  await selectNativeMaterialTab(createForm, '入库明细');
  await createRelation.screenshot({ path: path.join(outputDir, `material-inbound-refinement-${suffix}-create-detail.png`) });
  await selectNativeMaterialTab(createForm, '来源追溯');
  await page.screenshot({ path: path.join(outputDir, `material-inbound-refinement-${suffix}-create-source.png`) });
  await context.close();
  return { viewport, readonly: readonlyResult, create: createResult };
}

function contractSectionIdentity(contract) {
  const structure = findKey(contract, 'formStructureContract');
  const policy = findKey(contract, 'formPolicy');
  return {
    presentationMode: findKey(contract, 'presentationMode'),
    effectiveRenderProfile: findKey(contract, 'effectiveRenderProfile'),
    formStructureContract: structure || null,
    formPolicy: policy || null,
  };
}

async function applyReviewTheme(context, theme) {
  await context.addInitScript((nextTheme) => {
    localStorage.setItem('sc_theme', nextTheme);
  }, theme);
}

function requireHandlingNativeContract(contract, entryKey, spec, actionId, profile) {
  const identity = inboundNativeContract(contract);
  const expectedModel = entryKey === 'inbound' ? 'sc.material.inbound' : 'sc.material.outbound';
  check(identity.model === expectedModel && identity.viewType === 'form',
    `material handling form contract is missing: ${entryKey}`, identity);
  check(identity.layoutPolicy === 'container_tree_authority'
    && identity.authority.formStructureAuthority === 'native_authority'
    && identity.authority.compatibilityDependencies.length === 0,
  `material handling entry still depends on compatibility structure: ${entryKey}`, identity);
  check(identity.authority.resolvedActionId === actionId
    && identity.authority.resolvedViewId === spec.viewId,
  `material handling native source identity drifted: ${entryKey}`, identity);
  check(identity.effectiveRenderProfile === profile,
    `material handling render profile drifted: ${entryKey}`, identity);
  for (const title of spec.nativeTitles) {
    check(identity.titles.includes(title), `material native chapter is missing: ${entryKey}/${title}`, identity);
  }
  for (const fieldName of [...spec.facts, ...spec.sourceFields, 'line_ids', 'note', 'attachment_ids']) {
    check(identity.fieldNames.includes(fieldName), `material native field is missing: ${entryKey}/${fieldName}`, identity);
  }
  for (const buttonName of spec.buttons) {
    check(identity.buttonNames.includes(buttonName), `material native operation is missing: ${entryKey}/${buttonName}`, identity);
  }
  return identity;
}

async function draftNoteRetention(form, spec, entryKey, mode) {
  if (!['create', 'edit'].includes(mode)) return { skipped: true, reason: 'readonly_existing_state' };
  await selectNativeMaterialTab(form, '说明与附件');
  const note = form.locator('[data-field-name="note"]:visible textarea, [data-field-name="note"]:visible input').first();
  await note.waitFor({ timeout: 15000 });
  const original = await note.inputValue();
  const probe = `UC2-${entryKey}-${mode}-unsaved`;
  await note.fill(probe);
  await selectNativeMaterialTab(form, '来源追溯');
  await selectNativeMaterialTab(form, '说明与附件');
  const retained = await note.inputValue();
  check(retained === probe, 'material draft value was lost while switching native tabs',
    { entryKey, mode, original, retained });
  return { original, probe, retained, saved: false };
}

async function inspectHandlingForm(page, entryKey, entry, spec, mode, viewport, theme) {
  const record = mode === 'edit' ? entry.editable_record : entry.record;
  const recordPath = mode === 'create' ? 'new' : String(record.id);
  const contractStart = report.primary.contracts.length;
  await page.goto(
    `${frontendUrl}/f/${entry.model}/${recordPath}?menu_id=${entry.menu.id}&action_id=${entry.action.id}`,
    { waitUntil: 'domcontentloaded', timeout: 45000 },
  );
  const form = page.locator('[data-product-page-mode="form"]:visible').first();
  await form.locator('[data-contract-form-driver]:visible').first().waitFor({ timeout: 45000 });
  const contract = report.primary.contracts.slice(contractStart)
    .filter((body) => findKey(body, 'viewType') === 'form' && findKey(body, 'model') === entry.model)
    .at(-1);
  const observedProfile = String(findKey(contract, 'effectiveRenderProfile') || '');
  const expectedProfile = mode === 'create' ? 'create' : mode === 'edit' ? 'edit' : observedProfile;
  const nativeContract = requireHandlingNativeContract(
    contract, entryKey, spec, Number(entry.action.id), expectedProfile,
  );
  if (mode === 'edit') {
    check(observedProfile === 'edit' && nativeContract.effectiveRecordCapabilities?.write === true,
      `governed draft sample is not editable: ${entryKey}`, nativeContract);
  }
  if (mode === 'existing' && record.state !== 'draft') {
    check(observedProfile === 'readonly' && nativeContract.effectiveRecordCapabilities?.write === false,
      `non-draft material sample is not readonly: ${entryKey}`, { record, nativeContract });
  }

  const heading = (await form.locator('h1:visible').first().innerText()).trim();
  check(heading.includes(spec.identityToken), 'material handling page identity is inconsistent',
    { entryKey, heading, expected: spec.identityToken });
  const tabs = (await form.locator('[data-section-tab]:visible').allInnerTexts()).map((value) => value.trim());
  check(JSON.stringify(tabs) === JSON.stringify(spec.tabs),
    `material handling native tabs drifted: ${entryKey}`, tabs);

  for (const fieldName of spec.facts) {
    if (mode === 'existing') continue;
    await form.locator(`[data-field-name="${fieldName}"]:visible`).first().waitFor({ timeout: 15000 });
  }
  if (entryKey !== 'inbound') {
    const typeText = (await form.locator('[data-field-name="outbound_type"]:visible').first().innerText()).trim();
    const expectedType = entryKey === 'return' ? '退库' : '领用出库';
    check(typeText.includes(expectedType), 'material action category/default identity drifted',
      { entryKey, typeText, expectedType });
  }

  const top = await resetActualScrollTop(page, form);
  const suffix = `${entryKey}-${mode}-${viewport.width}x${viewport.height}-${theme}`;
  await page.screenshot({
    path: path.join(outputDir, `uc2-material-${suffix}-actual-top.png`),
    fullPage: false,
    animations: 'disabled',
  });

  await selectNativeMaterialTab(form, spec.detailTitle);
  const relation = form.locator('[data-field-name="line_ids"]:visible').first();
  await relation.waitFor({ timeout: 15000 });
  const detailOperations = {
    addButtons: await relation.getByRole('button', { name: /添加|新增/ }).count(),
    readonly: await relation.getAttribute('data-field-state'),
  };
  await relation.scrollIntoViewIfNeeded();
  await page.screenshot({
    path: path.join(outputDir, `uc2-material-${suffix}-detail.png`),
    fullPage: false,
    animations: 'disabled',
  });

  const draftRetention = await draftNoteRetention(form, spec, entryKey, mode);
  await selectNativeMaterialTab(form, '来源追溯');
  const visibleSourceFields = await form.locator(
    spec.sourceFields.map((name) => `[data-field-name="${name}"]:visible`).join(', '),
  ).count();
  await page.screenshot({
    path: path.join(outputDir, `uc2-material-${suffix}-source.png`),
    fullPage: false,
    animations: 'disabled',
  });

  const navigation = form.locator('[data-form-section-navigation]:visible').first();
  const detailLink = navigation.getByRole('button', { name: spec.detailTitle, exact: true });
  await detailLink.waitFor({ timeout: 15000 });
  const targetSelector = await detailLink.getAttribute('data-section-target');
  const beforeSelectedTab = await selectedNativeMaterialTab(form);
  const targetVisibleBefore = targetSelector
    ? await form.locator(`${targetSelector}:visible`).count()
    : 0;
  await detailLink.click();
  await form.locator(`[data-section-tab="${spec.detailTitle}"].native-tab--active:visible`).first()
    .waitFor({ timeout: 15000 });
  const targetVisibleAfter = targetSelector
    ? await form.locator(`${targetSelector}:visible`).count()
    : 0;
  const afterSelectedTab = await selectedNativeMaterialTab(form);
  const activeNavigation = await detailLink.getAttribute('aria-current');
  check(beforeSelectedTab === '来源追溯'
    && targetVisibleBefore === 0
    && afterSelectedTab === spec.detailTitle
    && targetVisibleAfter === 1
    && activeNavigation === 'location',
  'top navigation did not reveal, locate, and highlight the notebook-owned target', {
    entryKey, beforeSelectedTab, targetVisibleBefore, afterSelectedTab, targetVisibleAfter, activeNavigation,
  });

  const deadNavigationLinks = await navigation.locator('[data-section-link]').evaluateAll((links, root) => {
    const formRoot = root;
    return links.map((link) => {
      const selector = link.getAttribute('data-section-target') || '';
      const key = link.getAttribute('data-section-link') || '';
      const target = selector ? formRoot.querySelector(selector) : null;
      const reveal = [...formRoot.querySelectorAll('[data-section-reveal-targets]')].some((control) => {
        try {
          return JSON.parse(control.getAttribute('data-section-reveal-targets') || '[]').includes(key);
        } catch {
          return false;
        }
      });
      return { key, reachable: Boolean(target || reveal) };
    }).filter((item) => !item.reachable);
  }, await form.elementHandle());
  check(deadNavigationLinks.length === 0,
    'hidden or absent material targets leaked into section navigation', deadNavigationLinks);

  return {
    entryKey,
    mode,
    viewport,
    theme,
    route: new URL(page.url()).pathname,
    record: mode === 'create' ? null : record,
    heading,
    tabs,
    nativeContract,
    top,
    detailOperations,
    visibleSourceFields,
    draftRetention,
    navigationBehavior: {
      targetSelector,
      beforeSelectedTab,
      targetVisibleBefore,
      afterSelectedTab,
      targetVisibleAfter,
      activeNavigation,
    },
  };
}

async function inspectNonMaterialNavigationCounterexample() {
  const entry = target.shared_entries.project_profile;
  const context = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
  const page = await context.newPage();
  observe(page, report.primary);
  await login(page, entry.user.login);
  await page.goto(
    `${frontendUrl}/f/${entry.model}/${entry.record.id}?menu_id=${entry.menu.id}&action_id=${entry.action.id}`,
    { waitUntil: 'domcontentloaded', timeout: 45000 },
  );
  const form = page.locator('[data-product-page-mode="form"]:visible').first();
  await form.locator('[data-contract-form-driver]:visible').first().waitFor({ timeout: 45000 });
  const links = form.locator('[data-form-section-navigation]:visible [data-section-link]');
  check(await links.count() > 0, 'non-material counterexample has no native section navigation');
  const link = links.last();
  const selector = await link.getAttribute('data-section-target');
  await link.click();
  check(Boolean(selector) && await form.locator(`${selector}:visible`).count() === 1,
    'non-material navigation target is not visible after activation', { selector });
  check(await link.getAttribute('aria-current') === 'location',
    'non-material navigation highlight did not follow the selected content', { selector });
  await page.screenshot({
    path: path.join(outputDir, 'uc2-non-material-project-navigation-1440x960.png'),
    fullPage: false,
    animations: 'disabled',
  });
  const result = { entry: 'project_profile', selector, active: true };
  await context.close();
  return result;
}

async function inspectMaterialHandlingReview() {
  check(handlingViewports.length > 0, 'material handling review viewport list is empty');
  check(handlingThemes.length > 0, 'material handling review theme list is empty');
  report.primary.handlingReviews = [];
  for (const theme of handlingThemes) {
    for (const viewport of handlingViewports) {
      for (const [entryKey, spec] of Object.entries(handlingEntrySpecs)) {
        const entry = target.entries[entryKey];
        const context = await browser.newContext({
          viewport,
          locale: 'zh-CN',
          hasTouch: viewport.width <= 390,
        });
        await applyReviewTheme(context, theme);
        const page = await context.newPage();
        observe(page, report.primary);
        await login(page, target.user.login);
        if (entry.record) {
          report.primary.handlingReviews.push(
            await inspectHandlingForm(page, entryKey, entry, spec, 'existing', viewport, theme),
          );
        }
        report.primary.handlingReviews.push(
          await inspectHandlingForm(page, entryKey, entry, spec, 'create', viewport, theme),
        );
        if (entry.editable_record && viewport.width > 390) {
          report.primary.handlingReviews.push(
            await inspectHandlingForm(page, entryKey, entry, spec, 'edit', viewport, theme),
          );
        }
        await context.close();
      }
    }
  }
  report.primary.nonMaterialNavigationCounterexample = await inspectNonMaterialNavigationCounterexample();
  check(report.primary.errors.length === 0, 'material handling review has browser errors', report.primary.errors);
  check(report.primary.mutations.length === 0, 'material handling review mutated business data', report.primary.mutations);
  report.security.result = { skipped: true, reason: 'uc2_readonly_existing_and_uncommitted_create_edit_review' };
}

async function inspectSharedRendererRegression() {
  report.primary.sharedReviews = [];
  for (const [entryKey, spec] of Object.entries(sharedEntrySpecs)) {
    const entry = target.shared_entries[entryKey];
    const contractStart = report.primary.contracts.length;
    const context = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
    const page = await context.newPage();
    observe(page, report.primary);
    await login(page, entry.user.login);
    await page.goto(
      `${frontendUrl}/f/${entry.model}/${entry.record.id}?menu_id=${entry.menu.id}&action_id=${entry.action.id}`,
      { waitUntil: 'domcontentloaded', timeout: 45000 },
    );
    const form = page.locator('[data-product-page-mode="form"]:visible').first();
    await form.locator('[data-contract-form-driver]:visible').first().waitFor({ timeout: 45000 });
    const heading = (await form.locator('h1:visible').first().innerText()).trim();
    const sectionTitles = await form.locator('[data-floorplan-region]:visible').evaluateAll((nodes) => nodes.map((node) => ({
      region: node.getAttribute('data-floorplan-region') || '',
      title: node.getAttribute('data-section-title') || '',
    })));
    const ordinaryFieldRegions = await form.locator(
      spec.ordinaryFields.map((name) => `[data-field-name="${name}"]:visible`).join(', '),
    ).evaluateAll((nodes) => nodes.map((node) => ({
      field: node.getAttribute('data-field-name') || '',
      region: node.closest('[data-floorplan-region]')?.getAttribute('data-floorplan-region') || '',
    })));
    const semanticTitles = (await form.locator('h2:visible, h3:visible').allInnerTexts())
      .map((value) => value.trim()).filter(Boolean);
    const duplicateSemanticTitles = semanticTitles
      .filter((title, index) => semanticTitles.indexOf(title) !== index);
    const contract = report.primary.contracts.slice(contractStart)
      .filter((body) => (
        findKey(body, 'viewType') === 'form' && findKey(body, 'model') === entry.model
      )).at(-1);
    const presentationMode = findKey(contract, 'presentationMode');
    const result = {
      entryKey,
      url: page.url(),
      heading,
      sectionTitles,
      ordinaryFieldRegions,
      semanticTitles,
      duplicateSemanticTitles,
      presentationMode,
      contract: contractSectionIdentity(contract),
    };
    check(heading.includes(spec.identityToken) || heading === entry.record.name,
      'shared regression page identity is inconsistent', result);
    check(contract, 'shared regression form contract was not observed', result);
    check(ordinaryFieldRegions.length > 0,
      'shared regression ordinary facts are not visible', result);
    check(ordinaryFieldRegions.every((field) => field.region !== 'relation'),
      'shared renderer moved ordinary facts into relation details', result);
    check(!sectionTitles.some((section) => section.title === '关系明细' && section.region !== 'relation'),
      'shared renderer labeled an ordinary section as relation details', result);
    if (presentationMode === 'task') {
      check(duplicateSemanticTitles.length === 0,
        'task Floorplan duplicated a semantic section title', result);
    } else {
      check(sectionTitles.every((section) => section.region === 'audit'),
        'workspace form was incorrectly projected through the task Floorplan', result);
    }
    report.primary.sharedReviews.push(result);
    await page.screenshot({
      path: path.join(outputDir, `shared-regression-${entryKey}-1440x960.png`),
      fullPage: true,
    });
    await context.close();
  }
  check(report.primary.errors.length === 0, 'shared renderer regression has browser errors', report.primary.errors);
  check(report.primary.mutations.length === 0, 'shared renderer regression mutated business data', report.primary.mutations);
  report.security.result = { skipped: true, reason: 'shared_renderer_readonly_regression' };
}

if (sharedRegressionReview) {
  try {
    await inspectSharedRendererRegression();
    report.pass = true;
  } finally {
    report.completedAt = new Date().toISOString();
    report.screenshots = screenshotEvidence();
    fs.writeFileSync(path.join(outputDir, 'summary.json'), `${JSON.stringify(report, null, 2)}\n`);
    await browser.close();
  }
  console.log(JSON.stringify({ pass: report.pass, sharedReviews: report.primary.sharedReviews }));
  process.exit(0);
}

if (handlingReview) {
  try {
    await inspectMaterialHandlingReview();
    report.pass = true;
  } finally {
    report.completedAt = new Date().toISOString();
    report.screenshots = screenshotEvidence();
    fs.writeFileSync(path.join(outputDir, 'summary.json'), `${JSON.stringify(report, null, 2)}\n`);
    await browser.close();
  }
  console.log(JSON.stringify({ pass: report.pass, handlingReviews: report.primary.handlingReviews }));
  process.exit(0);
}

if (evidenceCaptureReview) {
  try {
    await inspectInboundEvidenceCapture();
    report.pass = true;
  } finally {
    report.completedAt = new Date().toISOString();
    report.screenshots = screenshotEvidence();
    fs.writeFileSync(path.join(outputDir, 'capture-summary.json'), `${JSON.stringify(report, null, 2)}\n`);
    await browser.close();
  }
  console.log(JSON.stringify({ pass: report.pass, evidenceCaptures: report.primary.evidenceCaptures }));
  process.exit(0);
}

if (sampleReview) {
  check(sampleViewports.length > 0, 'material sample review viewport list is empty');
  try {
    report.primary.sampleReviews = [];
    for (const viewport of sampleViewports) {
      report.primary.sampleReviews.push(await inspectInboundSampleViewport(viewport));
    }
    check(report.primary.errors.length === 0, 'material sample review has browser errors', report.primary.errors);
    check(report.primary.mutations.length === 0, 'material sample review mutated business data', report.primary.mutations);
    report.security.result = { skipped: true, reason: 'inbound_sample_affected_regions_only' };
    report.pass = true;
  } finally {
    report.completedAt = new Date().toISOString();
    report.screenshots = screenshotEvidence();
    fs.writeFileSync(path.join(outputDir, 'summary.json'), `${JSON.stringify(report, null, 2)}\n`);
    await browser.close();
  }
  console.log(JSON.stringify({ pass: report.pass, sampleReviews: report.primary.sampleReviews }));
  process.exit(0);
}

try {
  const primaryContext = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
  const primaryPage = await primaryContext.newPage();
  observe(primaryPage, report.primary);
  await login(primaryPage, target.user.login);
  const actionId = Number(target.action.id);
  const menuId = Number(target.menu.id);
  const recordId = Number(target.record.id);
  await primaryPage.goto(`${frontendUrl}/a/${actionId}?menu_id=${menuId}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  report.primary.entry = {
    url: primaryPage.url(),
    accessDenied: await primaryPage.locator('[data-semantic-component="ScErrorState"][role="alert"]:visible').count(),
    listMarkers: await primaryPage.locator('[data-product-page-mode="list"]:visible').count(),
    bodyText: (await primaryPage.locator('body').innerText()).slice(0, 1000),
  };
  await primaryPage.screenshot({ path: path.join(outputDir, 'material-entry-diagnostic.png'), fullPage: true });
  const list = primaryPage.locator('[data-product-page-mode="list"]:visible').first();
  await list.waitFor({ timeout: 45000 });
  const row = list.locator('tbody tr').filter({ hasText: String(target.record.name || '') }).first();
  await row.waitFor({ timeout: 45000 });
  const navigationSequence = [];
  primaryPage.on('framenavigated', (frame) => {
    if (frame === primaryPage.mainFrame()) navigationSequence.push(frame.url());
  });
  await row.click();
  await primaryPage.waitForURL((url) => (
    url.pathname === `/f/sc.material.inbound/${recordId}`
      && url.searchParams.get('action_id') === String(actionId)
      && url.searchParams.get('menu_id') === String(menuId)
  ), { timeout: 45000 });
  const form = primaryPage.locator('[data-product-page-mode="form"]:visible').first();
  await form.locator('[data-contract-form-driver]:visible').first().waitFor({ timeout: 45000 });
  const listContract = report.primary.contracts.filter((body) => findKey(body, 'viewType') === 'list').at(-1);
  const formContract = report.primary.contracts.filter((body) => findKey(body, 'viewType') === 'form').at(-1);
  const editableFields = await form.locator(
    '[data-field-state]:not([data-field-state="readonly"]) input:not([type="hidden"]):not(:disabled), '
      + '[data-field-state]:not([data-field-state="readonly"]) textarea:not(:disabled), '
      + '[data-field-state]:not([data-field-state="readonly"]) select:not(:disabled)',
  ).count();
  const saveActions = await primaryPage.locator('[data-action-ref="form.save"][data-action-enabled="true"]:visible').count();
  const editTransitions = await form.locator('[data-form-mode-action="edit"]:visible').count();
  const h1 = await form.locator('h1:visible').count();
  const headers = await form.locator('[data-product-page-header]:visible').count();
  const businessNavigationSequence = navigationSequence.filter((value) => {
    const pathname = new URL(value).pathname;
    return pathname.startsWith('/r/sc.material.inbound/') || pathname.startsWith('/f/sc.material.inbound/');
  });
  report.primary.result = {
    firstUrl: primaryPage.url(), businessNavigationSequence,
    modelRights: findKey(listContract, 'modelRights'),
    effectiveRecordCapabilities: findKey(formContract, 'effectiveRecordCapabilities'),
    effectiveRenderProfile: findKey(formContract, 'effectiveRenderProfile'),
    presentationMode: findKey(formContract, 'presentationMode'),
    editableFields, saveActions, editTransitions, h1, headers,
  };
  check(listContract && formContract, 'material list/form contract pair was not observed');
  check(findKey(listContract, 'modelRights')?.write === true, 'material list model write authority is not true', report.primary.result);
  check(findKey(formContract, 'effectiveRecordCapabilities')?.write === false, 'terminal material record did not deny write', report.primary.result);
  check(findKey(formContract, 'effectiveRenderProfile') === 'readonly', 'terminal material record did not downgrade to readonly', report.primary.result);
  check(findKey(formContract, 'presentationMode') === 'task', 'material inbound did not resolve task presentation', report.primary.result);
  check(businessNavigationSequence.length > 0
    && new URL(businessNavigationSequence[0]).pathname === `/f/sc.material.inbound/${recordId}`,
  'material inbound did not use /f as its first business route', report.primary.result);
  check(!businessNavigationSequence.some((value) => new URL(value).pathname.startsWith('/r/sc.material.inbound/')),
    'material inbound passed through a readonly business route', report.primary.result);
  check(editableFields === 0, 'terminal material form exposed editable business fields', report.primary.result);
  check(saveActions === 0, 'terminal material form exposed a save action', report.primary.result);
  check(editTransitions === 0, 'material form exposed a readonly-to-edit transition', report.primary.result);
  check(h1 === 1 && headers === 1, 'material form page identity is not unique', report.primary.result);
  check(report.primary.errors.length === 0, 'material primary journey has browser errors', report.primary.errors);
  check(report.primary.mutations.length === 0, 'material primary journey mutated business data', report.primary.mutations);
  await primaryPage.evaluate(() => window.scrollTo(0, 0));
  await primaryPage.screenshot({ path: path.join(outputDir, 'material-inbound-terminal-readonly-top.png') });
  const readonlyDetail = form.locator('[data-readonly-relation]').first();
  await readonlyDetail.scrollIntoViewIfNeeded();
  await Promise.race([
    readonlyDetail.locator('tbody tr').first().waitFor({ state: 'visible', timeout: 45000 }),
    readonlyDetail.locator('[data-readonly-relation-empty]').first().waitFor({ state: 'visible', timeout: 45000 }),
  ]);
  const readonlyDetailHeaders = await readonlyDetail.locator('thead').innerText();
  const readonlyDetailText = await readonlyDetail.innerText();
  const expectedDetailHeaders = ['材料档案', '规格型号', '单位', '入库数量', '单价', '金额', '来源验收明细'];
  const missingDetailHeaders = expectedDetailHeaders.filter((label) => !readonlyDetailHeaders.includes(label));
  report.primary.result.readonlyDetail = {
    headers: readonlyDetailHeaders.split('\n').map((value) => value.trim()).filter(Boolean),
    missingDetailHeaders,
    hasRowChangeColumn: readonlyDetailHeaders.includes('行变更'),
    hasTechnicalRelationLabel: readonlyDetailText.includes('sc.material.acceptance.line,'),
    hasBusinessSourceLabel: readonlyDetailText.includes('S80-MA-001'),
  };
  check(missingDetailHeaders.length === 0, 'material readonly detail loses business-first column order', report.primary.result.readonlyDetail);
  check(!report.primary.result.readonlyDetail.hasRowChangeColumn,
    'material readonly detail exposes draft row-change status', report.primary.result.readonlyDetail);
  check(!report.primary.result.readonlyDetail.hasTechnicalRelationLabel
    && report.primary.result.readonlyDetail.hasBusinessSourceLabel,
  'material readonly detail exposes a technical relation label', report.primary.result.readonlyDetail);
  await primaryPage.screenshot({ path: path.join(outputDir, 'material-inbound-terminal-readonly-detail.png') });
  const bottomRegion = form.locator('[data-floorplan-region="activity"], [data-floorplan-region="audit"]').last();
  if (await bottomRegion.count()) await bottomRegion.scrollIntoViewIfNeeded();
  else await primaryPage.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await primaryPage.screenshot({ path: path.join(outputDir, 'material-inbound-terminal-readonly-bottom.png') });
  await primaryPage.screenshot({ path: path.join(outputDir, 'material-inbound-terminal-readonly.png'), fullPage: true });

  await primaryPage.goto(
    `${frontendUrl}/f/sc.material.inbound/new?menu_id=${menuId}&action_id=${actionId}`,
    { waitUntil: 'domcontentloaded', timeout: 45000 },
  );
  const createForm = primaryPage.locator('[data-product-page-mode="form"]:visible').first();
  await createForm.locator('[data-contract-form-driver]:visible').first().waitFor({ timeout: 45000 });
  const createFieldCodes = await createForm.locator('[data-field-name]:visible').evaluateAll((nodes) => (
    nodes.map((node) => node.getAttribute('data-field-name')).filter(Boolean)
  ));
  const requiredCreateFacts = ['project_id', 'inbound_date', 'supplier_id', 'warehouse_id', 'dest_location_id'];
  const missingCreateFacts = requiredCreateFacts.filter((fieldName) => !createFieldCodes.includes(fieldName));
  const createFactStates = {};
  const createFactTop = {};
  for (const fieldName of requiredCreateFacts) {
    const field = createForm.locator(`[data-field-name="${fieldName}"]:visible`).first();
    createFactStates[fieldName] = await field.getAttribute('data-field-state');
    createFactTop[fieldName] = (await field.boundingBox())?.y ?? null;
  }
  const readonlyCreateFacts = requiredCreateFacts.filter((fieldName) => createFactStates[fieldName] === 'readonly');
  const createDetailLocator = createForm.locator('[data-o2m-empty], [data-detail-collection-heading]').first();
  const createDetailEntry = await createForm.locator('[data-o2m-empty], [data-detail-collection-heading]').count();
  const createDetailTop = (await createDetailLocator.boundingBox())?.y ?? null;
  const factsAfterDetail = requiredCreateFacts.filter((fieldName) => (
    createFactTop[fieldName] === null || createDetailTop === null || createFactTop[fieldName] >= createDetailTop
  ));
  report.primary.create = {
    url: primaryPage.url(), createFieldCodes, missingCreateFacts, createFactStates,
    readonlyCreateFacts, createDetailEntry, createDetailTop, createFactTop, factsAfterDetail,
  };
  check(missingCreateFacts.length === 0, 'material create form hides required first-read facts', report.primary.create);
  check(readonlyCreateFacts.length === 0, 'material create form makes native editable facts readonly', report.primary.create);
  check(factsAfterDetail.length === 0, 'material create form places first-read facts after relation details', report.primary.create);
  check(createDetailEntry > 0, 'material create form has no reachable detail entry', report.primary.create);
  check(report.primary.errors.length === 0, 'material create journey has browser errors', report.primary.errors);
  check(report.primary.mutations.length === 0, 'material create journey mutated business data', report.primary.mutations);
  await primaryPage.evaluate(() => window.scrollTo(0, 0));
  await primaryPage.screenshot({ path: path.join(outputDir, 'material-inbound-create-top.png') });
  await primaryContext.close();

  const securityContext = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
  const securityPage = await securityContext.newPage();
  observe(securityPage, report.security);
  await login(securityPage, target.security_user.login);
  await securityPage.goto(`${frontendUrl}/a/${actionId}?menu_id=${menuId}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await securityPage.waitForURL((url) => url.pathname === '/access-denied', { timeout: 45000 });
  const denial = securityPage.locator('[data-semantic-component="ScErrorState"][role="alert"]:visible').first();
  await denial.waitFor({ timeout: 45000 });
  report.security.result = {
    url: securityPage.url(), denialVisible: (await denial.innerText()).includes('访问受限'),
    businessForms: await securityPage.locator('[data-product-page-mode="form"]').count(),
    saveActions: await securityPage.locator('[data-action-ref="form.save"]').count(),
  };
  check(report.security.result.denialVisible, 'unauthorized material entry did not fail closed', report.security.result);
  check(report.security.result.businessForms === 0 && report.security.result.saveActions === 0,
    'unauthorized material entry exposed business form controls', report.security.result);
  check(report.security.errors.length === 0, 'material security journey has browser errors', report.security.errors);
  check(report.security.mutations.length === 0, 'material security journey mutated business data', report.security.mutations);
  await securityPage.screenshot({ path: path.join(outputDir, 'material-entry-project-role-denied.png'), fullPage: true });
  await securityContext.close();
  report.pass = true;
} finally {
  report.completedAt = new Date().toISOString();
  report.screenshots = screenshotEvidence();
  fs.writeFileSync(path.join(outputDir, 'summary.json'), `${JSON.stringify(report, null, 2)}\n`);
  await browser.close();
}

console.log(JSON.stringify({ pass: report.pass, primary: report.primary.result, security: report.security.result }));
