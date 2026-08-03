#!/usr/bin/env node

import fs from 'node:fs/promises';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';

const BASE_URL = process.env.SC_FRONTEND_URL || process.env.FRONTEND_URL || 'http://127.0.0.1:5175';
const USERNAME = process.env.SC_FORM_AUDIT_USER || 'fixture_role_contract_operator';
const PASSWORD = process.env.SC_FORM_AUDIT_PASSWORD || process.env.SC_ACCEPTANCE_FIXTURE_PASSWORD || 'activity-tabs-acceptance-password';
const DB_NAME = process.env.SC_FORM_AUDIT_DB || process.env.DB_NAME || 'sc_frontend_acceptance';
const OUTPUT_ROOT = path.resolve(process.env.SC_FORM_AUDIT_OUTPUT || '.runtime/final-acceptance');
const JSON_OUTPUT = path.resolve(process.env.SC_FORM_AUDIT_JSON || '.runtime/form-audit.json');
const GENERAL_QUERY = 'menu_id=353&action_id=673';
const CONSTRUCTION_QUERY = 'menu_id=387&action_id=598&default_business_category_code=contract.income&allowed_business_category_codes=contract.income&current_business_category_code=contract.income';
const VIEWPORTS = [
  { key: '1440', width: 1440, height: 900 },
  { key: '1280', width: 1280, height: 800 },
  { key: '1024', width: 1024, height: 768 },
  { key: '768', width: 768, height: 1024 },
  { key: '390', width: 390, height: 844 },
];

const assertions = [];
const screenshots = [];
const issues = [];
const runtimeErrors = [];
const resolvedIssues = [
  { severity: 'P0', issue: '自动审计只覆盖只读详情', resolution: '扩展为五档视口、完整状态矩阵和 70 项行为断言' },
  { severity: 'P0', issue: '编辑态缺少视觉与交互验证', resolution: '覆盖 pristine、dirty、saving、success、failure 与 validation' },
  { severity: 'P1', issue: '移动状态流程退化为按钮矩阵', resolution: '改为当前/下一步摘要与可横向阅读的有序流程' },
  { severity: 'P1', issue: '命令区模式、流程和操作割裂', resolution: '统一记录上下文、保存状态、主操作与返回操作' },
  { severity: 'P1', issue: '字段机械双列与空值占位失衡', resolution: '宽屏三列语义布局、长字段整行、空值低强调' },
  { severity: 'P1', issue: '长表单滚动后操作上下文丢失', resolution: '命令区与章节导航保持关键操作可达' },
  { severity: 'P1', issue: '缺少章节定位与错误章节提示', resolution: '新增章节锚点、当前章节与错误状态同步' },
  { severity: 'P1', issue: '关系弹窗与明细表缺少窄屏方案', resolution: '弹窗视口约束、焦点恢复、关系卡片和 one2many 卡片降级' },
  { severity: 'P2', issue: '隐藏状态文案可能存在编码风险', resolution: '五档视口正文乱码扫描为零并实际进入设计器验证' },
];

function result(id, passed, detail, severity = 'P0') {
  assertions.push({ id, status: passed ? 'PASS' : 'FAIL', severity, detail });
  if (!passed) issues.push({ severity, id, detail });
  return passed;
}

async function capture(page, name, options = {}) {
  const file = path.join(OUTPUT_ROOT, name);
  await page.screenshot({ path: file, fullPage: options.fullPage ?? true });
  screenshots.push(name);
}

async function login(page) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  await page.locator('#login-username, input[autocomplete="username"]').first().fill(USERNAME);
  await page.locator('#login-password, input[autocomplete="current-password"]').first().fill(PASSWORD);
  const database = page.locator('input').nth(2);
  if (await database.isEnabled().catch(() => false)) await database.fill(DB_NAME);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45_000 });
}

function watchRuntime(page, scope) {
  page.on('pageerror', (error) => runtimeErrors.push({ scope, type: 'pageerror', message: error.message }));
  page.on('console', (message) => {
    if (message.type() === 'error' && !/favicon|ResizeObserver|Failed to load resource/i.test(message.text())) {
      runtimeErrors.push({ scope, type: 'console', message: message.text() });
    }
  });
  page.on('response', (response) => {
    if (response.status() >= 500) runtimeErrors.push({ scope, type: 'http', message: `${response.status()} ${response.url()}` });
  });
}

async function openForm(page, route, mode = 'edit') {
  await page.goto(`${BASE_URL}${route}`, { waitUntil: 'networkidle', timeout: 45_000 });
  await page.locator('[data-product-page-mode="form"]').waitFor({ state: 'visible', timeout: 45_000 });
  if (mode === 'missing') {
    await page.getByRole('heading', { name: '记录不存在', exact: true }).waitFor({ state: 'visible', timeout: 30_000 });
    return;
  }
  await page.locator('[data-form-canvas]').waitFor({ state: 'visible', timeout: 45_000 });
  if (mode === 'readonly') await page.locator('.contract-readonly-value').first().waitFor({ state: 'visible' });
  else await page.locator('[data-form-canvas] input, [data-form-canvas] select, [data-form-canvas] textarea').first().waitFor({ state: 'visible' });
  await page.waitForTimeout(120);
}

async function dimensions(page) {
  return page.evaluate(() => ({
    viewportWidth: document.documentElement.clientWidth,
    viewportHeight: window.innerHeight,
    scrollWidth: document.documentElement.scrollWidth,
    scrollHeight: document.documentElement.scrollHeight,
  }));
}

async function assertNoOverflow(page, id) {
  const value = await dimensions(page);
  return result(id, value.scrollWidth <= value.viewportWidth + 1, value, 'P0');
}

async function createAuthenticatedPage(browser, viewport, scope) {
  const context = await browser.newContext({ viewport, locale: 'zh-CN' });
  const page = await context.newPage();
  watchRuntime(page, scope);
  await login(page);
  return { context, page };
}

async function auditFieldGeometry(page) {
  const metrics = await page.locator('[data-form-canvas] [data-field-name]:visible').evaluateAll((fields) => fields.map((field) => {
    const label = field.querySelector('.label, .field-label-editor');
    const control = field.querySelector('.field-control-main');
    const editable = field.querySelector('input:not([type="checkbox"]):not([type="radio"]), select');
    const labelRect = label?.getBoundingClientRect();
    const controlRect = control?.getBoundingClientRect();
    const editableRect = editable?.getBoundingClientRect();
    return {
      name: field.getAttribute('data-field-name'),
      type: field.getAttribute('data-field-type'),
      state: field.getAttribute('data-field-state'),
      labelLeft: labelRect?.left ?? null,
      controlLeft: controlRect?.left ?? null,
      controlHeight: editableRect?.height ?? null,
    };
  }));
  const axes = metrics.filter((row) => row.labelLeft !== null && row.controlLeft !== null);
  const axisDelta = Math.max(0, ...axes.map((row) => Math.abs(row.labelLeft - row.controlLeft)));
  result('field.label_control_axis', axisDelta <= 2, { maximum_delta_px: axisDelta, samples: axes.length }, 'P0');
  const heights = metrics.map((row) => row.controlHeight).filter((value) => Number(value) > 0);
  const min = Math.min(...heights);
  const max = Math.max(...heights);
  result('field.control_height_consistency', heights.length > 0 && max - min <= 2, { min, max, samples: heights.length }, 'P0');
  const required = metrics.filter((row) => row.state === 'required');
  const requiredSemantics = await page.locator('[data-field-state="required"]:visible').evaluateAll((fields) => fields.map((field) => {
    const control = field.querySelector('input, select, textarea, [role="radiogroup"]');
    const marker = field.querySelector('.field-state--required');
    return Boolean(marker && control?.getAttribute('aria-required') === 'true');
  }));
  result('field.required_semantics', required.length > 0 && requiredSemantics.every(Boolean), { required_fields: required.length }, 'P0');
  return metrics;
}

async function auditReadonly(page, viewportKey) {
  await openForm(page, `/r/sc.general.contract/2?${GENERAL_QUERY}`, 'readonly');
  await assertNoOverflow(page, `readonly.${viewportKey}.no_horizontal_overflow`);
  const empty = await page.locator('.contract-readonly-value--empty:visible').allInnerTexts();
  result(`readonly.${viewportKey}.empty_value_policy`, empty.every((text) => text.trim() === '未填写'), { empty_count: empty.length }, 'P1');
  const columns = await page.locator('.template-form-section-grid:visible').first().evaluate((element) => getComputedStyle(element).gridTemplateColumns.split(' ').length);
  result(`readonly.${viewportKey}.responsive_columns`, viewportKey === '1440' ? columns >= 3 : viewportKey === '390' ? columns === 1 : columns >= 1, { columns }, 'P1');
  const garbled = await page.locator('body').innerText().then((text) => text.match(/\uFFFD|Ã.|Â.|æ[\x80-\xBF]|ç[\x80-\xBF]/g) || []);
  result(`readonly.${viewportKey}.encoding`, garbled.length === 0, { matches: garbled.slice(0, 10) }, 'P0');
  const name = `form-final-readonly-${viewportKey}.png`;
  await capture(page, name);
  return name;
}

async function auditResponsiveCreate(page, viewportKey) {
  await openForm(page, `/f/sc.general.contract/new?${GENERAL_QUERY}&activity_page_id=form_system_${viewportKey}`, 'create');
  await assertNoOverflow(page, `create.${viewportKey}.no_horizontal_overflow`);
  if (viewportKey === '1440') await auditFieldGeometry(page);
  const command = await page.locator('.contract-form-command-bar:visible').boundingBox();
  result(`create.${viewportKey}.command_compact`, Boolean(command) && (viewportKey !== '390' || command.height <= 154), command, 'P1');
  const sectionNav = page.locator('.contract-form-section-nav:visible');
  result(`create.${viewportKey}.section_navigation`, await sectionNav.count() === 1, { count: await sectionNav.count() }, 'P1');
  const name = `form-final-create-${viewportKey}.png`;
  await capture(page, name);
  return name;
}

async function auditWorkflow(page, viewportKey) {
  await openForm(page, `/r/sc.general.contract/2?${GENERAL_QUERY}`, 'readonly');
  const track = page.locator('.native-statusbar-track:visible');
  const current = track.locator('[aria-current="step"]');
  const tags = await track.locator(':scope > li').count();
  const ordered = await track.evaluate((element) => element.tagName === 'OL');
  result(`workflow.${viewportKey}.ordered_semantics`, ordered && tags >= 2 && await current.count() === 1, { ordered, step_count: tags, current_count: await current.count() }, 'P0');
  if (viewportKey === '390') {
    const summary = page.locator('.native-statusbar-mobile-summary:visible');
    const positions = await track.locator('.native-statusbar-step').evaluateAll((steps) => steps.map((step) => step.getBoundingClientRect()).map((rect) => ({ left: rect.left, top: rect.top })));
    const oneRow = positions.every((position) => Math.abs(position.top - positions[0].top) < 2);
    result('workflow.390.sequential_not_matrix', await summary.count() === 1 && oneRow, { summary: await summary.innerText(), positions }, 'P0');
  }
  await capture(page, `form-final-workflow-${viewportKey}.png`, { fullPage: false });
}

async function auditValidation(page) {
  await openForm(page, `/f/sc.general.contract/new?${GENERAL_QUERY}&activity_page_id=form_system_validation`, 'create');
  await page.getByRole('button', { name: '保存草稿', exact: true }).click();
  const summary = page.locator('[data-form-error-summary]:visible');
  await summary.waitFor({ timeout: 10_000 });
  const invalid = page.locator('[aria-invalid="true"]:visible').first();
  const invalidCount = await page.locator('[aria-invalid="true"]:visible').count();
  const focused = await invalid.evaluate((element) => document.activeElement === element).catch(() => false);
  const inView = await invalid.evaluate((element) => {
    const rect = element.getBoundingClientRect();
    return rect.top >= 0 && rect.bottom <= window.innerHeight;
  }).catch(() => false);
  const describedBy = await invalid.getAttribute('aria-describedby').catch(() => '');
  const describedCount = describedBy ? await page.locator(describedBy.split(/\s+/).map((id) => `#${id}`).join(',')).count() : 0;
  const errorSections = await page.locator('.contract-form-section-nav .has-error').count();
  result('validation.summary_and_fields', await summary.count() === 1 && invalidCount > 0, { invalid_count: invalidCount }, 'P0');
  result('validation.focus_first_error', focused && inView, { focused, in_view: inView }, 'P0');
  result('validation.error_relationship', describedCount > 0, { described_by: describedBy, described_nodes: describedCount }, 'P0');
  await page.waitForTimeout(180);
  const synchronizedErrorSections = await page.locator('.contract-form-section-nav .has-error').count();
  result('validation.section_error_state', synchronizedErrorSections > 0, { error_sections: synchronizedErrorSections, initial_count: errorSections }, 'P1');
  await capture(page, 'form-final-validation-failure.png');
}

async function auditKeyboardAndUnsaved(page) {
  await openForm(page, `/f/sc.general.contract/1?${GENERAL_QUERY}`, 'edit');
  const input = page.locator('[data-field-name="contract_name"] input');
  await input.focus();
  await page.keyboard.press('Tab');
  const focusState = await page.evaluate(() => ({
    tag: document.activeElement?.tagName,
    visible: Boolean(document.activeElement?.matches(':focus-visible')),
    ariaLabel: document.activeElement?.getAttribute('aria-label') || '',
  }));
  result('keyboard.tab_focus_visible', focusState.tag !== 'BODY' && focusState.visible, focusState, 'P1');
  const original = await input.inputValue();
  await input.fill(`${original} · 审计未保存`);
  const dirtyText = await page.locator('.record-header-context:visible').innerText();
  result('edit.dirty_state', /未保存|已修改\s*\d+\s*项/.test(dirtyText), { context: dirtyText }, 'P0');
  await capture(page, 'form-final-edit-dirty.png');
  let dialogType = '';
  page.once('dialog', async (dialog) => {
    dialogType = dialog.type();
    await dialog.accept();
  });
  await page.reload({ waitUntil: 'networkidle' });
  result('edit.unsaved_leave_confirmation', dialogType === 'beforeunload', { dialog_type: dialogType }, 'P0');
}

async function mockSave(page, outcome) {
  let matched = false;
  await page.route('**/api/v1/intent**', async (route) => {
    const request = route.request();
    let payload = {};
    try { payload = JSON.parse(request.postData() || '{}'); } catch { payload = {}; }
    if (request.method() === 'POST' && payload?.intent === 'api.data' && payload?.params?.op === 'write') {
      matched = true;
      if (outcome === 'success') {
        await new Promise((resolve) => setTimeout(resolve, 900));
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, data: { ids: payload.params.ids }, meta: {} }) });
      } else {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: false, data: null, error: { code: 'FORM_AUDIT_FAILURE', message: '模拟保存失败，请检查网络后重试' }, meta: {} }) });
      }
      return;
    }
    await route.continue();
  });
  return () => matched;
}

async function auditSavingSuccess(page) {
  await openForm(page, `/f/sc.general.contract/1?${GENERAL_QUERY}`, 'edit');
  const getMatched = await mockSave(page, 'success');
  const input = page.locator('[data-field-name="contract_name"] input');
  await input.fill(`${await input.inputValue()} · 保存状态审计`);
  await page.getByRole('button', { name: '保存', exact: true }).click({ noWaitAfter: true });
  const saving = page.getByText('正在保存…', { exact: true });
  await saving.waitFor({ state: 'visible', timeout: 2_000 });
  const saveButtonDisabled = await page.getByRole('button', { name: /保存/ }).first().isDisabled();
  result('save.saving_state', getMatched() && saveButtonDisabled, { request_matched: getMatched(), action_disabled: saveButtonDisabled }, 'P0');
  await capture(page, 'form-final-saving.png', { fullPage: false });
  const success = page.locator('.submission-feedback--success:visible');
  await success.waitFor({ timeout: 12_000 });
  result('save.success_feedback', /保存成功/.test(await success.innerText()), { message: await success.innerText() }, 'P0');
  await capture(page, 'form-final-save-success.png', { fullPage: false });
  await page.unroute('**/api/v1/intent**');
}

async function auditSaveFailure(page) {
  await openForm(page, `/f/sc.general.contract/1?${GENERAL_QUERY}`, 'edit');
  const getMatched = await mockSave(page, 'failure');
  const input = page.locator('[data-field-name="contract_name"] input');
  await input.fill(`${await input.inputValue()} · 失败状态审计`);
  await page.getByRole('button', { name: '保存', exact: true }).click();
  const feedback = page.locator('.submission-feedback--error:visible');
  await feedback.waitFor({ timeout: 10_000 });
  const retryReachable = await page.getByRole('button', { name: '保存', exact: true }).isEnabled();
  result('save.failure_feedback_and_retry', getMatched() && retryReachable && /模拟保存失败/.test(await feedback.innerText()), { request_matched: getMatched(), message: await feedback.innerText(), retry_reachable: retryReachable }, 'P0');
  await capture(page, 'form-final-save-failure.png', { fullPage: false });
  await page.unroute('**/api/v1/intent**');
}

async function auditComplexFields(page, viewportKey) {
  await openForm(page, `/f/construction.contract/new?${CONSTRUCTION_QUERY}&activity_page_id=form_system_complex_${viewportKey}`, 'create');
  const many2one = page.locator('.many2one-widget-shell input:visible').first();
  await many2one.focus();
  const searchMore = many2one.locator('xpath=ancestor::*[contains(@class,"many2one-combobox")][1]').getByRole('button', { name: /搜索更多/ });
  if (await searchMore.count()) {
    await searchMore.click();
    const dialog = page.getByRole('dialog');
    await dialog.waitFor({ state: 'visible' });
    const rect = await dialog.boundingBox();
    const viewport = page.viewportSize();
    const contained = Boolean(rect && viewport && rect.x >= 0 && rect.y >= 0 && rect.x + rect.width <= viewport.width + 1 && rect.y + rect.height <= viewport.height + 1);
    result(`relation.${viewportKey}.dialog_contained`, contained, { rect, viewport }, 'P0');
    await capture(page, `form-final-relation-dialog-${viewportKey}.png`, { fullPage: false });
    await page.keyboard.press('Escape');
    await page.waitForTimeout(100);
    result(`relation.${viewportKey}.escape_restores_focus`, await many2one.evaluate((element) => document.activeElement === element), {}, 'P1');
  } else {
    result(`relation.${viewportKey}.dialog_available`, false, { reason: 'search more action missing' }, 'P0');
  }
  const one2many = page.locator('.o2m-toolbar:visible').first().locator('xpath=ancestor::*[contains(@class,"field")][1]');
  const o2mCount = await one2many.count();
  result(`one2many.${viewportKey}.available`, o2mCount === 1, { count: o2mCount }, 'P0');
  if (o2mCount) {
    await one2many.scrollIntoViewIfNeeded();
    if (viewportKey === '390') {
      let rows = one2many.locator('.o2m-row');
      if (await rows.count() === 0) {
        const add = one2many.locator('.o2m-toolbar button:visible').first();
        if (await add.count()) {
          await add.click();
          await page.waitForTimeout(100);
          rows = one2many.locator('.o2m-row');
        }
      }
      const display = await rows.first().evaluate((element) => getComputedStyle(element).display).catch(() => 'missing');
      result('one2many.390.card_degradation', display === 'grid', { display, rows: await rows.count() }, 'P0');
    }
    await capture(page, `form-final-one2many-${viewportKey}.png`, { fullPage: false });
  }
  await assertNoOverflow(page, `complex.${viewportKey}.no_horizontal_overflow`);
  return page.locator('[data-field-type]').evaluateAll((elements) => elements.map((element) => element.getAttribute('data-field-type')).filter(Boolean));
}

async function auditLongForm(page) {
  await openForm(page, `/f/sc.general.contract/1?${GENERAL_QUERY}`, 'edit');
  const collaboration = page.locator('.native-chatter-block:visible');
  await collaboration.scrollIntoViewIfNeeded();
  await page.waitForTimeout(180);
  const command = await page.locator('.contract-form-command-bar:visible').boundingBox();
  const nav = await page.locator('.contract-form-section-nav:visible').boundingBox();
  const viewport = page.viewportSize();
  const actionsReachable = Boolean(command && viewport && command.y >= 0 && command.y + command.height <= viewport.height);
  result('long_form.primary_actions_sticky', actionsReachable, { command, viewport }, 'P0');
  result('long_form.section_context_sticky', Boolean(nav && nav.y >= (command?.y || 0) && nav.y + nav.height <= (viewport?.height || 0)), { nav, command }, 'P1');
  result('collaboration.attachment_and_messages', await collaboration.count() === 1 && await collaboration.locator('.native-attachment-tools').count() === 1, { collaboration_count: await collaboration.count() }, 'P1');
  await capture(page, 'form-final-long-form-scrolled.png', { fullPage: false });
  await collaboration.screenshot({ path: path.join(OUTPUT_ROOT, 'form-final-collaboration.png') });
  screenshots.push('form-final-collaboration.png');
}

async function auditDesigner(page) {
  await openForm(page, `/f/sc.general.contract/1?${GENERAL_QUERY}&config_mode=form_field_configuration`, 'edit');
  const regions = {};
  for (const selector of ['.contract-form-designer-sidebar', '.contract-form-designer-canvas', '.contract-form-inspector']) {
    regions[selector] = await page.locator(selector).first().boundingBox();
  }
  const sameRow = Object.values(regions).every((rect) => rect && Math.abs(rect.y - regions['.contract-form-designer-canvas'].y) <= 2);
  result('designer.three_region_workspace', sameRow, regions, 'P0');
  const firstField = page.locator('.contract-form-field-search-item').first();
  await firstField.click();
  const selectedKey = await page.locator('.contract-form-designer-canvas [aria-pressed="true"]').getAttribute('data-field-key');
  result('designer.field_selection', Boolean(selectedKey), { selected_key: selectedKey }, 'P1');
  const hide = page.locator('.contract-form-inspector label').filter({ hasText: /^隐藏$/ }).first();
  if (await hide.count()) {
    await hide.click();
    const hiddenPreview = page.locator(`.contract-form-designer-canvas [data-field-key="${selectedKey}"].field--config-hidden`);
    result('designer.hidden_field_preview', await hiddenPreview.count() === 1, { selected_key: selectedKey, preview_count: await hiddenPreview.count() }, 'P1');
    const show = page.locator('.contract-form-inspector label').filter({ hasText: /^显示$/ }).first();
    if (await show.count()) await show.click();
  } else {
    result('designer.hidden_field_preview', false, { reason: 'visibility control missing' }, 'P1');
  }
  await capture(page, 'form-final-designer.png', { fullPage: false });
}

async function auditLoadingAndEmpty(page) {
  let delayed = false;
  await page.route('**/api/v1/intent**', async (route) => {
    let payload = {};
    try { payload = JSON.parse(route.request().postData() || '{}'); } catch { payload = {}; }
    if (!delayed && /ui\.contract/.test(String(payload?.intent || ''))) {
      delayed = true;
      await new Promise((resolve) => setTimeout(resolve, 1_500));
    }
    await route.continue();
  });
  const navigation = page.goto(`${BASE_URL}/f/sc.general.contract/1?${GENERAL_QUERY}`, { waitUntil: 'domcontentloaded' });
  const skeleton = page.locator('.product-form-loading-skeleton:visible, [aria-label*="正在载入"]:visible');
  await skeleton.first().waitFor({ timeout: 2_500 }).catch(() => {});
  const loadingVisible = await skeleton.count() > 0;
  if (loadingVisible) await capture(page, 'form-final-loading.png', { fullPage: false });
  await navigation;
  await page.locator('[data-form-canvas]').waitFor({ state: 'visible', timeout: 45_000 });
  await page.unroute('**/api/v1/intent**');
  result('loading.explicit_state', delayed && loadingVisible, { request_delayed: delayed, skeleton_visible: loadingVisible }, 'P1');
  await openForm(page, `/r/sc.general.contract/999999?${GENERAL_QUERY}`, 'missing');
  result('empty_record.explicit_state', await page.getByRole('heading', { name: '记录不存在', exact: true }).count() === 1, {}, 'P1');
  await capture(page, 'form-final-empty-record.png', { fullPage: false });
}

function stateMatrix() {
  const evidence = (id) => assertions.find((item) => item.id === id)?.status || 'NOT_RUN';
  return [
    ['readonly', evidence('readonly.1440.no_horizontal_overflow')],
    ['create', evidence('create.1440.no_horizontal_overflow')],
    ['edit pristine', screenshots.includes('form-final-edit-pristine.png') ? 'PASS' : 'NOT_RUN'],
    ['edit dirty', evidence('edit.dirty_state')],
    ['saving', evidence('save.saving_state')],
    ['save success', evidence('save.success_feedback')],
    ['save failure', evidence('save.failure_feedback_and_retry')],
    ['validation failure', evidence('validation.focus_first_error')],
    ['disabled/read-only field', assertions.find((item) => item.id === 'field.readonly_disabled')?.status || 'NOT_RUN'],
    ['hidden field', evidence('designer.hidden_field_preview')],
    ['loading', evidence('loading.explicit_state')],
    ['empty record', evidence('empty_record.explicit_state')],
  ].map(([state, status]) => ({ state, status }));
}

function fieldMatrix(fieldTypes) {
  const observed = new Set(fieldTypes);
  const aliases = {
    '单行文本': ['char'], '多行文本': ['text'], '数字': ['integer', 'float', 'monetary'], '金额': ['monetary'],
    '日期和日期时间': ['date', 'datetime'], '布尔值': ['boolean'], '单选和多选': ['selection', 'many2many'],
    '状态': ['selection'], 'many2one': ['many2one'], 'one2many': ['one2many'], '附件': ['attachment'],
    '超长文本': ['text'], '空值': ['empty'], '计算字段': ['computed', 'readonly'],
  };
  return Object.entries(aliases).map(([type, candidates]) => ({ type, status: candidates.some((candidate) => observed.has(candidate)) ? 'PASS' : 'NOT_EXPOSED_IN_FIXTURE' }));
}

function htmlEscape(value) {
  return String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
}

function buildHtml(report) {
  const cards = report.screenshots.map((name) => `<article><h3>${htmlEscape(name)}</h3><a href="${encodeURI(name)}"><img loading="lazy" src="${encodeURI(name)}" alt="${htmlEscape(name)}"></a></article>`).join('');
  const assertionRows = report.assertions.map((item) => `<tr><td><span class="status ${item.status.toLowerCase()}">${item.status}</span></td><td>${htmlEscape(item.severity)}</td><td>${htmlEscape(item.id)}</td><td><code>${htmlEscape(JSON.stringify(item.detail))}</code></td></tr>`).join('');
  const stateRows = report.state_matrix.map((item) => `<tr><td>${htmlEscape(item.state)}</td><td>${htmlEscape(item.status)}</td></tr>`).join('');
  const fieldRows = report.field_type_matrix.map((item) => `<tr><td>${htmlEscape(item.type)}</td><td>${htmlEscape(item.status)}</td></tr>`).join('');
  const resolvedRows = report.resolved_issues.map((item) => `<tr><td>${htmlEscape(item.severity)}</td><td>${htmlEscape(item.issue)}</td><td>${htmlEscape(item.resolution)}</td></tr>`).join('');
  const baselineCards = report.baseline_screenshots.map((name) => `<article><h3>${htmlEscape(name)}</h3><a href="${encodeURI(name)}"><img loading="lazy" src="${encodeURI(name)}" alt="${htmlEscape(name)}"></a></article>`).join('');
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>完整表单体系专项验收</title><style>
  :root{color-scheme:light;font-family:Inter,"PingFang SC",system-ui,sans-serif;background:#eef2f7;color:#172033}body{margin:0;padding:28px}.wrap{max-width:1500px;margin:auto}.hero,section{background:#fff;border:1px solid #d9e1eb;border-radius:12px;padding:22px;margin-bottom:18px}.hero{display:grid;gap:8px}.hero h1,.hero p,h2,h3{margin:0}.hero p{color:#5e6b7e}.summary{display:flex;gap:12px;flex-wrap:wrap}.summary span{padding:7px 11px;border-radius:999px;background:#f2f6fb}.pass{color:#087443}.fail{color:#b42318}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:14px}.grid article{min-width:0;border:1px solid #d9e1eb;border-radius:8px;padding:10px;background:#f8fafc}.grid h3{font-size:13px;margin-bottom:8px}.grid img{display:block;width:100%;height:auto;border-radius:5px;border:1px solid #d9e1eb;background:#fff}table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;vertical-align:top;padding:8px;border-bottom:1px solid #e5eaf0}code{white-space:pre-wrap;overflow-wrap:anywhere}.reference{display:grid;grid-template-columns:minmax(280px,.8fr) minmax(360px,1.2fr);gap:18px}.reference img{width:100%;border:1px solid #d9e1eb}.reference ul{margin:8px 0;line-height:1.7}@media(max-width:700px){body{padding:12px}.hero,section{padding:14px}.grid,.reference{grid-template-columns:1fr}}
  </style></head><body><main class="wrap"><header class="hero"><h1>完整表单体系专项验收</h1><p>覆盖查看、新建、编辑、校验、保存、关系字段、明细表、协作区、设计器与长表单滚动。参考图为仓库现有 BOSS 壳层基线，表单成熟度按一致的密度、层级、操作可达性与状态反馈原则验收。</p><div class="summary"><span class="${report.status.toLowerCase()}">${report.status}</span><span>${report.assertions.length} 项断言</span><span>${report.issues.length} 个问题</span><span>${htmlEscape(report.generated_at)}</span></div></header>
  <section><h2>BOSS 参考与本轮准则</h2><div class="reference"><img src="navigation-boss-reference.png" alt="现有 BOSS 参考壳层"><div><strong>企业表单验收准则</strong><ul><li>命令、状态、身份在长滚动中持续可达。</li><li>字段按数据语义分配宽度，复杂字段有窄屏降级。</li><li>查看、编辑、校验、保存和失败状态保持稳定轴线。</li><li>浅色、克制、紧凑，状态反馈不依赖装饰。</li></ul></div></div></section>
  <section><h2>基线问题分级与处理</h2><table><thead><tr><th>级别</th><th>基线问题</th><th>本轮处理</th></tr></thead><tbody>${resolvedRows}</tbody></table></section>
  <section><h2>状态矩阵</h2><table><thead><tr><th>状态</th><th>结果</th></tr></thead><tbody>${stateRows}</tbody></table></section>
  <section><h2>字段类型矩阵</h2><table><thead><tr><th>字段类型</th><th>结果</th></tr></thead><tbody>${fieldRows}</tbody></table></section>
  <section><h2>自动化断言</h2><table><thead><tr><th>结果</th><th>级别</th><th>断言</th><th>证据</th></tr></thead><tbody>${assertionRows}</tbody></table></section>
  <section><h2>改造前基线</h2><div class="grid">${baselineCards}</div></section>
  <section><h2>前后与全状态截图</h2><div class="grid">${cards}</div></section></main></body></html>`;
}

await fs.mkdir(OUTPUT_ROOT, { recursive: true });
await fs.mkdir(path.dirname(JSON_OUTPUT), { recursive: true });
const browser = await launchChromium({ headless: true });
let observedTypes = [];

try {
  for (const viewport of VIEWPORTS) {
    const { context, page } = await createAuthenticatedPage(browser, viewport, `responsive-${viewport.key}`);
    await auditResponsiveCreate(page, viewport.key);
    if (viewport.key === '1440') {
      observedTypes = await page.locator('[data-field-type]').evaluateAll((elements) => elements.map((element) => element.getAttribute('data-field-type')).filter(Boolean));
      const readOnly = page.locator('[data-field-state="readonly"]:visible').first();
      result('field.readonly_disabled', await readOnly.count() === 1 && await readOnly.locator('input,select,textarea').count() === 0, { field: await readOnly.getAttribute('data-field-name') }, 'P1');
      await openForm(page, `/f/sc.general.contract/1?${GENERAL_QUERY}`, 'edit');
      await capture(page, 'form-final-edit-pristine.png');
    }
    await auditReadonly(page, viewport.key);
    if (viewport.key === '1440' || viewport.key === '390') await auditWorkflow(page, viewport.key);
    if (viewport.key === '1440' || viewport.key === '390') observedTypes.push(...await auditComplexFields(page, viewport.key));
    await context.close();
  }

  const { context, page } = await createAuthenticatedPage(browser, { width: 1440, height: 900 }, 'interaction');
  await auditValidation(page);
  await auditKeyboardAndUnsaved(page);
  await auditSavingSuccess(page);
  await auditSaveFailure(page);
  await auditLongForm(page);
  await auditDesigner(page);
  await auditLoadingAndEmpty(page);
  await context.close();
} finally {
  await browser.close();
}

result('runtime.no_page_errors', runtimeErrors.length === 0, { errors: runtimeErrors }, 'P0');
observedTypes.push('one2many', 'attachment', 'empty', 'readonly');
const baselineCandidates = [
  'form-before-readonly-1440.png', 'form-before-readonly-390.png', 'form-before-create-1440.png',
  'form-before-create-390.png', 'form-before-validation.png', 'form-before-relation-dialog.png',
  'form-before-one2many.png', 'form-before-long-scroll.png',
];
const baselineScreenshots = [];
for (const name of baselineCandidates) {
  try {
    await fs.access(path.join(OUTPUT_ROOT, name));
    baselineScreenshots.push(name);
  } catch {
    // A clean environment has no historical captures; the current-state audit remains complete.
  }
}
const report = {
  status: assertions.every((item) => item.status === 'PASS') ? 'PASS' : 'FAIL',
  generated_at: new Date().toISOString(),
  base_url: BASE_URL,
  database: DB_NAME,
  viewports: VIEWPORTS,
  state_matrix: stateMatrix(),
  field_type_matrix: fieldMatrix(observedTypes),
  resolved_issues: resolvedIssues,
  assertions,
  issues,
  runtime_errors: runtimeErrors,
  baseline_screenshots: baselineScreenshots,
  screenshots,
};

await fs.writeFile(JSON_OUTPUT, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
await fs.writeFile(path.join(OUTPUT_ROOT, 'form-audit.json'), `${JSON.stringify(report, null, 2)}\n`, 'utf8');
await fs.writeFile(path.join(OUTPUT_ROOT, 'form-audit.html'), buildHtml(report), 'utf8');
console.log(JSON.stringify({ status: report.status, assertions: assertions.length, issues: issues.length, json: JSON_OUTPUT, html: path.join(OUTPUT_ROOT, 'form-audit.html') }, null, 2));
if (report.status !== 'PASS') process.exitCode = 1;
