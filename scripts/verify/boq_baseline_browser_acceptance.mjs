#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';

const baseUrl = String(process.env.FRONTEND_URL || 'http://127.0.0.1:18083').replace(/\/$/, '');
const database = process.env.DB_NAME || 'sc_clean';
const loginName = process.env.E2E_LOGIN || 'wutao';
const password = process.env.E2E_PASSWORD || '';
const projectId = Number(process.env.BOQ_PROJECT_ID || 0);
const versionId = Number(process.env.BOQ_VERSION_ID || 0);
const sourceXls = String(process.env.BOQ_SOURCE_XLS || '').trim();
const outputDir = process.env.ARTIFACTS_DIR || 'artifacts/boq-baseline-browser';
const targets = JSON.parse(process.env.BOQ_BROWSER_TARGETS_JSON || '{}');

function check(value, reason) {
  if (!value) throw new Error(reason);
}

function capture(page) {
  const state = { pageErrors: [], httpErrors: [], consoleErrors: [], contractResponses: [] };
  page.on('pageerror', (error) => state.pageErrors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') state.consoleErrors.push(message.text());
  });
  page.on('response', (response) => {
    if (response.status() >= 400) state.httpErrors.push({ status: response.status(), url: response.url() });
    const postData = response.request().postData() || '';
    if (postData.includes('ui.contract.v2')) state.contractResponses.push(response.json().catch(() => null));
  });
  return state;
}

function findHierarchyPresentation(value) {
  if (!value || typeof value !== 'object') return null;
  if (!Array.isArray(value) && ['hierarchy_browser', 'hierarchy_planner'].includes(value.semantic)) return value;
  for (const child of Array.isArray(value) ? value : Object.values(value)) {
    const found = findHierarchyPresentation(child);
    if (found) return found;
  }
  return null;
}

async function login(page) {
  await page.goto(`${baseUrl}/login`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  const inputs = page.locator('input');
  await inputs.nth(0).fill(loginName);
  await inputs.nth(1).fill(password);
  if (await inputs.nth(2).isEnabled().catch(() => false)) {
    await inputs.nth(2).fill(database);
  } else {
    check(await inputs.nth(2).inputValue() === database, 'LOGIN_DATABASE_MISMATCH');
  }
  await page.getByRole('button', { name: /^登录$/ }).click();
  try {
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45_000 });
  } catch (error) {
    await page.screenshot({ path: path.join(outputDir, 'login-failed.png'), fullPage: true });
    const body = (await page.locator('body').innerText()).replace(/\s+/g, ' ').slice(0, 800);
    throw new Error(`LOGIN_FAILED:${body}; ${error.message}`);
  }
  await page.locator('.layout-shell').waitFor({ timeout: 45_000 });
}

async function openList(page, key, target, expectedText, surface = 'list') {
  check(Number(target?.action_id) > 0 && Number(target?.menu_id) > 0, `${key}:TARGET_MISSING`);
  const route = `/a/${target.action_id}?menu_id=${target.menu_id}&action_id=${target.action_id}`;
  await page.goto(`${baseUrl}${route}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  const surfaceSelector = surface === 'hierarchy'
    ? '.hierarchy-browser'
    : surface === 'planner'
      ? '.hierarchy-planner'
    : surface === 'worksheet'
      ? '.worksheet'
    : '[data-product-page-mode="list"]';
  try {
    await page.locator(surfaceSelector).first().waitFor({ timeout: 45_000 });
  } catch (error) {
    await page.screenshot({ path: path.join(outputDir, `${key}-failed.png`), fullPage: true });
    const body = (await page.locator('body').innerText()).replace(/\s+/g, ' ').slice(0, 1200);
    throw new Error(`${key}:LIST_UNAVAILABLE:url=${page.url()}:body=${body}; ${error.message}`);
  }
  await page.waitForFunction((expectedSurface) => {
    const text = document.body.innerText || '';
    const selector = expectedSurface === 'hierarchy'
      ? '.hierarchy-list table tbody tr, .hierarchy-list .sc-empty, .hierarchy-error'
      : expectedSurface === 'planner'
        ? '.planner-grid tbody tr, .planner-state, .planner-error'
      : expectedSurface === 'worksheet'
        ? '.worksheet-table-scroll tbody tr, .worksheet-state, .worksheet-error'
      : 'table tbody tr, .desktop-record-table tbody tr, .sc-empty, .sc-state-panel, [data-list-state="empty"], [data-list-state="error"]';
    const settled = document.querySelector(selector);
    return Boolean(settled) && !/加载中|正在载入数据|正在加载列表|正在加载/.test(text);
  }, surface, { timeout: 45_000 });
  const body = await page.locator('body').innerText();
  check(!/无权访问|访问受限|NAVIGATION_AUTHORITY_DENIED/.test(body), `${key}:NAVIGATION_DENIED`);
  if (!body.includes(expectedText)) {
    await page.screenshot({ path: path.join(outputDir, `${key}-content-missing.png`), fullPage: true });
    throw new Error(`${key}:EXPECTED_TEXT_MISSING:${expectedText}:body=${body.replace(/\s+/g, ' ').slice(0, 1600)}`);
  }
  const screenshot = path.join(outputDir, `${key}.png`);
  await page.screenshot({ path: screenshot, fullPage: true, animations: 'disabled' });
  return { key, route, screenshot, title: await page.title() };
}

async function verifyBoqWorksheet(page, actionId) {
  const surface = page.locator('.worksheet');
  const renderer = page.locator('.action-surface-renderer-host');
  check(await renderer.getAttribute('data-surface-semantic') === 'hierarchical_worksheet', 'BOQ_WORKSHEET_SEMANTIC_INVALID');
  check(await renderer.getAttribute('data-requested-renderer') === 'core.hierarchical_worksheet', 'BOQ_WORKSHEET_RENDERER_NOT_REQUESTED');
  check(await renderer.getAttribute('data-active-renderer') === 'core.hierarchical_worksheet', 'BOQ_WORKSHEET_RENDERER_NOT_ACTIVE');
  check(await renderer.getAttribute('data-renderer-status') === 'ready', 'BOQ_WORKSHEET_RENDERER_NOT_READY');
  await surface.getByText('共 108 条', { exact: true }).waitFor({ timeout: 30_000 });
  const headers = await surface.locator('thead th').allTextContents();
  for (const expected of ['序号', '项目编码', '项目名称', '项目特征', '单位', '工程量', '综合单价', '源文件合价', '系统计算合价']) {
    check(headers.includes(expected), `BOQ_WORKSHEET_COLUMN_MISSING:${expected}:${headers.join('|')}`);
  }
  check(!headers.includes('差异'), `BOQ_AUDIT_VARIANCE_LEAKED_TO_DEFAULT_WORKSHEET:${headers.join('|')}`);
  check(!headers.includes('Created by') && !headers.includes('Created on'), `BOQ_WORKSHEET_AUDIT_COLUMNS_LEAKED:${headers.join('|')}`);
  const firstOrdinals = await surface.locator('tbody tr.item-row td:first-child').evaluateAll((cells) => cells.slice(0, 3).map((cell) => cell.textContent?.trim()));
  check(JSON.stringify(firstOrdinals) === JSON.stringify(['1', '2', '3']), `BOQ_WORKSHEET_ORDINALS_INVALID:${JSON.stringify(firstOrdinals)}`);
  const headingCount = await surface.locator('tbody tr.heading-row').count();
  const summaryCount = await surface.locator('tbody tr.summary-row').count();
  const recordCount = await surface.locator('tbody tr.item-row').count();
  check(headingCount === 13, `BOQ_WORKSHEET_HEADING_ROWS_INVALID:${headingCount}`);
  check(summaryCount === 14, `BOQ_WORKSHEET_SUMMARY_ROWS_INVALID:${summaryCount}`);
  check(recordCount === 108, `BOQ_WORKSHEET_RECORD_COUNT_INVALID:${recordCount}`);
  for (const tab of ['项目特征', '计量计价', '清单结构', '执行分配', '来源与诊断']) {
    check(await surface.getByRole('button', { name: tab, exact: true }).count() === 1, `BOQ_WORKSHEET_TAB_MISSING:${tab}`);
  }
  check(await surface.getByRole('button', { name: '导入清单', exact: true }).count() === 1, 'BOQ_IMPORT_ACTION_MISSING');
  const summaryText = (await surface.locator('tbody tr.summary-row').allInnerTexts()).join('\n');
  check(summaryText.includes('3,031,841.76'), `BOQ_WORKSHEET_SOURCE_TOTAL_MISSING:${summaryText}`);
  check(summaryText.includes('3,031,841.74'), `BOQ_WORKSHEET_CALCULATED_TOTAL_MISSING:${summaryText}`);
  check(await surface.getByRole('button', { name: '全部折叠', exact: true }).count() === 0, 'BOQ_SOURCE_ORDER_SHOULD_NOT_COLLAPSE');
  const defaultScreenshot = path.join(outputDir, 'boq-worksheet-default.png');
  await page.screenshot({ path: defaultScreenshot, fullPage: true, animations: 'disabled' });
  const comparisonRow = surface.locator('tbody tr.summary-row').filter({ hasText: '3,031,841.76' }).first();
  await comparisonRow.scrollIntoViewIfNeeded();
  await surface.locator('.worksheet-table-scroll').evaluate((element) => { element.scrollLeft = element.scrollWidth; });
  const comparisonScreenshot = path.join(outputDir, 'boq-source-calculation-comparison.png');
  await page.screenshot({ path: comparisonScreenshot, fullPage: true, animations: 'disabled' });

  const navigation = surface.locator('.worksheet-navigation');
  const detail = surface.locator('.worksheet-detail');
  const navigationHandle = surface.locator('.worksheet-resizer-navigation');
  const detailHandle = surface.locator('.worksheet-resizer-detail');
  const navigationBefore = await navigation.boundingBox();
  const detailBefore = await detail.boundingBox();
  const navigationHandleBox = await navigationHandle.boundingBox();
  const detailHandleBox = await detailHandle.boundingBox();
  check(navigationBefore && detailBefore && navigationHandleBox && detailHandleBox, 'BOQ_WORKSHEET_LAYOUT_MISSING');
  await page.mouse.move(navigationHandleBox.x, navigationHandleBox.y + 100);
  await page.mouse.down();
  await page.mouse.move(navigationHandleBox.x + 44, navigationHandleBox.y + 100, { steps: 4 });
  await page.mouse.up();
  const navigationAfter = await navigation.boundingBox();
  check(navigationAfter && Math.abs(navigationAfter.width - navigationBefore.width - 44) <= 2, `BOQ_NAVIGATION_RESIZE_FAILED:${navigationBefore.width}:${navigationAfter?.width}`);

  const currentDetailHandleBox = await detailHandle.boundingBox();
  check(currentDetailHandleBox, 'BOQ_DETAIL_RESIZER_MISSING');
  await page.mouse.move(currentDetailHandleBox.x + 120, currentDetailHandleBox.y);
  await page.mouse.down();
  await page.mouse.move(currentDetailHandleBox.x + 120, currentDetailHandleBox.y - 36, { steps: 4 });
  await page.mouse.up();
  const detailAfter = await detail.boundingBox();
  check(detailAfter && Math.abs(detailAfter.height - detailBefore.height - 36) <= 2, `BOQ_DETAIL_RESIZE_FAILED:${detailBefore.height}:${detailAfter?.height}`);
  const stored = await page.evaluate((key) => window.localStorage.getItem(key), `sc:hierarchical-worksheet:${actionId}:layout`);
  check(stored && stored.includes('navigationWidth') && stored.includes('detailHeight'), 'BOQ_WORKSHEET_LAYOUT_NOT_PERSISTED');
  const screenshot = path.join(outputDir, 'boq-worksheet-verified.png');
  await page.screenshot({ path: screenshot, fullPage: true, animations: 'disabled' });
  return { semantic: 'hierarchical_worksheet', renderer: 'core.hierarchical_worksheet', itemCount: recordCount, headingCount, summaryCount, headers, layoutPersisted: true, defaultScreenshot, comparisonScreenshot, screenshot };
}

async function verifyBoqImportEntry(page) {
  await page.locator('.worksheet').getByRole('button', { name: '导入清单', exact: true }).click();
  await page.waitForURL(/\/(?:f|r)\/project\.boq\.import\.wizard\/new(?:\?|$)/, { timeout: 30_000 });
  await page.locator('[data-product-page-mode="form"]').first().waitFor({ timeout: 30_000 });
  await page.locator('.product-form-loading').waitFor({ state: 'detached', timeout: 30_000 });
  const screenshot = path.join(outputDir, 'boq-import-wizard-entry.png');
  await page.screenshot({ path: screenshot, fullPage: true, animations: 'disabled' });
  const body = await page.locator('body').innerText();
  const projectInputCount = await page.locator('[data-field-name="project_id"] input').count();
  const fileInputCount = await page.locator('[data-field-name="file"] input[type="file"]').count();
  check(body.includes('工程量清单导入'), 'BOQ_IMPORT_WIZARD_TITLE_MISSING');
  check(body.includes('预检'), 'BOQ_IMPORT_PREFLIGHT_ACTION_MISSING');
  check(!body.includes('<li>'), 'BOQ_IMPORT_HTML_LEAKED');
  const versionCode = await page.locator('[data-field-name="version_code"] input').inputValue();
  check(/^V1-\d{8}$/.test(versionCode), `BOQ_IMPORT_VERSION_DATE_SUFFIX_MISSING:${versionCode}`);
  check(projectInputCount === 1, `BOQ_IMPORT_PROJECT_NOT_EDITABLE:${projectInputCount}`);
  check(fileInputCount === 1, `BOQ_IMPORT_FILE_NOT_EDITABLE:${fileInputCount}`);
  check(sourceXls && fs.existsSync(sourceXls), `BOQ_IMPORT_SOURCE_XLS_MISSING:${sourceXls}`);

  const projectInput = page.locator('[data-field-name="project_id"] input');
  await projectInput.fill('德阳市旌阳区');
  const projectOption = page.locator('[data-field-name="project_id"] .many2one-option').first();
  await projectOption.waitFor({ timeout: 30_000 });
  await projectOption.click();
  await page.locator('[data-field-name="file"] input[type="file"]').setInputFiles(sourceXls);
  await page.getByRole('button', { name: '预检', exact: true }).click();
  await page.waitForURL(/\/r\/project\.boq\.import\.wizard\/\d+(?:\?|$)/, { timeout: 45_000 });
  await page.locator('.product-form-loading').waitFor({ state: 'detached', timeout: 45_000 });
  const preflightDebugScreenshot = path.join(outputDir, 'boq-import-preflight-debug.png');
  await page.screenshot({ path: preflightDebugScreenshot, fullPage: true, animations: 'disabled' });
  const preflightBody = await page.locator('body').innerText();
  check(
    preflightBody.includes('识别 135 行，其中清单项 108 行、结构标题 13 行、页内小计/合计 14 行。'),
    `BOQ_IMPORT_PREFLIGHT_SUMMARY_MISSING:${preflightBody.replace(/\s+/g, ' ').slice(0, 1800)}`,
  );
  check(preflightBody.includes('另忽略 4 行空白或无业务含义的辅助行。'), 'BOQ_IMPORT_EXCLUDED_ROWS_EXPLANATION_INVALID');
  check(preflightBody.includes('预检合价 3478851.81。'), 'BOQ_IMPORT_PREFLIGHT_AMOUNT_INVALID');
  check(preflightBody.includes('凯江大回湾景区融合提升项目'), 'BOQ_IMPORT_ENGINEERING_HEADER_MISSING');
  check(preflightBody.includes('源 XLS 容器存在兼容性提示'), 'BOQ_IMPORT_SOURCE_DIAGNOSTIC_MISSING');
  check(preflightBody.includes('确认导入'), 'BOQ_IMPORT_CONFIRM_ACTION_MISSING');
  const preflightScreenshot = path.join(outputDir, 'boq-import-preflight-verified.png');
  await page.screenshot({ path: preflightScreenshot, fullPage: true, animations: 'disabled' });
  return {
    opened: true,
    preflightAvailable: true,
    fileHelpRendered: true,
    editable: true,
    preflight: { rows: 135, items: 108, headings: 13, summaries: 14, ignored: 4, amount: 3478851.81, sourceDiagnostic: true },
    screenshot,
    preflightScreenshot,
  };
}

async function verifyWbsHierarchy(page, actionId, state) {
  const surface = page.locator('.hierarchy-planner');
  const renderer = page.locator('.action-surface-renderer-host');
  check(await renderer.getAttribute('data-surface-semantic') === 'hierarchy_planner', 'WBS_SURFACE_SEMANTIC_INVALID');
  check(await renderer.getAttribute('data-requested-renderer') === 'core.hierarchy_planner', 'WBS_RENDERER_NOT_REQUESTED');
  check(await renderer.getAttribute('data-active-renderer') === 'core.hierarchy_planner', 'WBS_RENDERER_NOT_ACTIVE');
  check(await renderer.getAttribute('data-renderer-status') === 'ready', 'WBS_RENDERER_NOT_READY');
  await surface.locator('.planner-grid tbody tr').first().waitFor({ timeout: 30_000 });
  const contractPayloads = (await Promise.all(state.contractResponses)).filter(Boolean);
  const presentation = contractPayloads.map(findHierarchyPresentation).filter(Boolean).at(-1);
  const contractColumns = presentation?.config?.list?.columns || [];
  const contractColumnFields = contractColumns.map((row) => row.field);
  for (const field of ['code', 'name', 'status', 'manager_id', 'level_type', 'boq_line_count', 'boq_amount_total']) {
    check(contractColumnFields.includes(field), `WBS_CONTRACT_COLUMN_MISSING:${field}:${JSON.stringify(contractColumns)}`);
  }

  const rows = surface.locator('.planner-grid tbody tr');
  const expandedNodeCount = await rows.count();
  check(expandedNodeCount >= 4, `WBS_OUTLINE_ROWS_MISSING:${expandedNodeCount}`);
  check(await surface.locator('.outline-cell').count() >= expandedNodeCount, 'WBS_OUTLINE_COLUMN_MISSING');
  check(await surface.locator('.outline-toggle').count() > 0, 'WBS_OUTLINE_NESTING_MISSING');
  for (const actionLabel of ['新增同级 WBS', '新增下级 WBS', '缩进为下级', '提升一级', '打开', '节点详情']) {
    check(await surface.getByRole('button', { name: actionLabel, exact: true }).isDisabled(), `WBS_UNSELECTED_COMMAND_NOT_DISABLED:${actionLabel}`);
  }
  await rows.first().click();
  for (const actionLabel of ['新增顶层 WBS', '新增同级 WBS', '新增下级 WBS', '缩进为下级', '提升一级']) {
    check(await surface.getByRole('button', { name: actionLabel, exact: true }).count() === 1, `WBS_BACKEND_COMMAND_MISSING:${actionLabel}`);
  }
  check(await surface.getByRole('button', { name: '缩进为下级', exact: true }).isDisabled(), 'WBS_ROOT_INDENT_NOT_DISABLED');
  check(await surface.getByRole('button', { name: '提升一级', exact: true }).isDisabled(), 'WBS_ROOT_OUTDENT_NOT_DISABLED');
  const outlineCodes = async () => surface.locator('.planner-grid tbody tr td:first-child').allTextContents();
  const movableRow = surface.getByText('WBS-01.01', { exact: true }).locator('xpath=ancestor::tr');
  await movableRow.click();
  check(await surface.getByRole('button', { name: '缩进为下级', exact: true }).isDisabled(), 'WBS_FIRST_SIBLING_INDENT_NOT_DISABLED');
  check(!(await surface.getByRole('button', { name: '提升一级', exact: true }).isDisabled()), 'WBS_CHILD_OUTDENT_NOT_ENABLED');
  const beforeMove = await outlineCodes();
  await surface.getByRole('button', { name: '更多', exact: true }).click();
  for (const actionLabel of ['上移', '下移']) {
    check(await surface.getByRole('button', { name: actionLabel, exact: true }).count() === 1, `WBS_BACKEND_OVERFLOW_COMMAND_MISSING:${actionLabel}`);
  }
  check(await surface.getByRole('button', { name: '上移', exact: true }).isDisabled(), 'WBS_FIRST_SIBLING_MOVE_UP_NOT_DISABLED');
  check(!(await surface.getByRole('button', { name: '下移', exact: true }).isDisabled()), 'WBS_FIRST_SIBLING_MOVE_DOWN_NOT_ENABLED');
  await surface.getByRole('button', { name: '下移', exact: true }).click();
  await page.waitForFunction(() => {
    const codes = [...document.querySelectorAll('.hierarchy-planner tbody tr td:first-child')].map((node) => node.textContent?.trim());
    return codes.findIndex((code) => code?.endsWith('WBS-01.02')) < codes.findIndex((code) => code?.endsWith('WBS-01.01'));
  }, undefined, { timeout: 15_000 });
  await surface.getByRole('button', { name: '更多', exact: true }).click();
  await surface.getByRole('button', { name: '上移', exact: true }).click();
  await page.waitForFunction(() => {
    const codes = [...document.querySelectorAll('.hierarchy-planner tbody tr td:first-child')].map((node) => node.textContent?.trim());
    return codes.findIndex((code) => code?.endsWith('WBS-01.01')) < codes.findIndex((code) => code?.endsWith('WBS-01.02'));
  }, undefined, { timeout: 15_000 });
  await surface.getByRole('status').filter({ hasText: '上移：操作完成' }).waitFor({ timeout: 10_000 });
  check(JSON.stringify(await outlineCodes()) === JSON.stringify(beforeMove), 'WBS_MOVE_COMMAND_NOT_REVERSIBLE');
  check(await surface.getByRole('button', { name: '更多', exact: true }).getAttribute('aria-expanded') === 'false', 'WBS_MORE_MENU_NOT_CLOSED_AFTER_COMMAND');
  await surface.getByRole('button', { name: '视图', exact: true }).click();
  check(await surface.getByRole('button', { name: '视图', exact: true }).getAttribute('aria-expanded') === 'true', 'WBS_VIEW_MENU_NOT_OPEN');
  await surface.locator('.planner-grid').click({ position: { x: 8, y: 8 } });
  check(await surface.getByRole('button', { name: '视图', exact: true }).getAttribute('aria-expanded') === 'false', 'WBS_VIEW_MENU_NOT_CLOSED_OUTSIDE');
  await surface.getByRole('button', { name: '节点详情', exact: true }).click();
  await surface.locator('.planner-drawer').waitFor({ timeout: 10_000 });
  const detailScreenshot = path.join(outputDir, 'cost-wbs-planner-detail.png');
  await page.screenshot({ path: detailScreenshot, fullPage: true, animations: 'disabled' });
  await surface.locator('.planner-drawer').getByRole('button', { name: '×', exact: true }).click();
  const gridText = await surface.locator('.planner-grid').innerText();
  check(/2/.test(gridText), `WBS_ALLOCATION_COUNT_MISSING:${gridText}`);
  check(/36,398\.87/.test(gridText), `WBS_ALLOCATION_AMOUNT_MISSING:${gridText}`);
  const screenshot = path.join(outputDir, 'cost-wbs-planner-verified.png');
  await page.screenshot({ path: screenshot, fullPage: true, animations: 'disabled' });
  return {
    semantic: 'hierarchy_planner',
    renderer: 'core.hierarchy_planner',
    total: 4,
    expandedNodeCount,
    moveCommandsVerified: true,
    commandAvailabilityVerified: true,
    operationFeedbackVerified: true,
    contractColumnFields,
    detailScreenshot,
    screenshot,
  };
}

async function main() {
  check(password, 'E2E_PASSWORD_REQUIRED');
  check(projectId > 0 && versionId > 0, 'BOQ_RECORD_IDS_REQUIRED');
  fs.mkdirSync(outputDir, { recursive: true });
  const browser = await launchChromium({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'zh-CN' });
  const page = await context.newPage();
  const state = capture(page);
  const pages = [];
  try {
    await login(page);
    if (String(process.env.BOQ_BROWSER_SCOPE || '') === 'wbs') {
      pages.push(await openList(page, 'cost-wbs-list', targets.cost_wbs, '凯江大回湾', 'planner'));
      const wbsHierarchy = await verifyWbsHierarchy(page, Number(targets.cost_wbs.action_id), state);
      const result = { status: 'PASS', database, login: loginName, projectId, versionId, pages, wbsHierarchy, runtime: state };
      delete result.runtime.contractResponses;
      fs.writeFileSync(path.join(outputDir, 'wbs-result.json'), `${JSON.stringify(result, null, 2)}\n`);
      console.log(JSON.stringify(result));
      return;
    }
    pages.push(await openList(page, 'boq-version-list', targets.boq_version, 'V1-20260809'));
    const versionRow = page.locator('.desktop-record-table tbody tr, table tbody tr').filter({ hasText: 'V1-20260809' }).first();
    await versionRow.click();
    await page.waitForURL((url) => url.pathname.startsWith('/f/') || url.pathname.startsWith('/r/'), { timeout: 45_000 });
    await page.locator('[data-product-page-mode="form"]').first().waitFor({ timeout: 45_000 });
    await page.waitForFunction(() => !/加载中|正在载入/.test(document.body.innerText || ''), undefined, { timeout: 45_000 });
    const versionBody = await page.locator('body').innerText();
    if (!versionBody.includes('V1-20260809') || !/3,478,851\.81|3478851\.81/.test(versionBody)) {
      await page.screenshot({ path: path.join(outputDir, 'boq-version-form-failed.png'), fullPage: true });
      throw new Error(`boq-version-form:CONTENT_MISSING:body=${versionBody.replace(/\s+/g, ' ').slice(0, 1600)}`);
    }
    await page.screenshot({ path: path.join(outputDir, 'boq-version-form.png'), fullPage: true, animations: 'disabled' });
    pages.push(await openList(page, 'boq-line-list', targets.boq_line, '凯江大回湾', 'worksheet'));
    const boqWorksheet = await verifyBoqWorksheet(page, Number(targets.boq_line.action_id));
    const boqImportEntry = await verifyBoqImportEntry(page);
    pages.push(await openList(page, 'cost-wbs-list', targets.cost_wbs, '凯江大回湾', 'planner'));
    const wbsHierarchy = await verifyWbsHierarchy(page, Number(targets.cost_wbs.action_id), state);
    pages.push(await openList(page, 'location-lbs-list', targets.location_lbs, '空间位置 LBS', 'hierarchy'));
    check(await page.locator('.hierarchy-browser').getByRole('button', { name: '新增位置', exact: true }).count() === 1, 'LBS_CREATE_ACTION_MISSING');
    await page.locator('.hierarchy-browser').getByRole('button', { name: '新增位置', exact: true }).click();
    await page.waitForURL(/\/f\/construction\.location\.breakdown\/new(?:\?|$)/, { timeout: 30_000 });
    await page.locator('[data-product-page-mode="form"]').first().waitFor({ timeout: 30_000 });
    await page.locator('.product-form-loading').waitFor({ state: 'detached', timeout: 30_000 });
    check(await page.locator('[data-field-name="project_id"] input').count() === 1, 'LBS_CREATE_FORM_PROJECT_MISSING');
    check(await page.locator('[data-field-name="location_type"]').count() >= 1, 'LBS_CREATE_FORM_TYPE_MISSING');
    await page.screenshot({ path: path.join(outputDir, 'location-lbs-create-form.png'), fullPage: true, animations: 'disabled' });
    pages.push(await openList(page, 'contract-section-list', targets.contract_section, '标段结构', 'hierarchy'));
    check(await page.locator('.hierarchy-browser').getByRole('button', { name: '新增标段', exact: true }).count() === 1, 'CONTRACT_SECTION_CREATE_ACTION_MISSING');
    pages.push(await openList(page, 'execution-scope-list', targets.execution_scope, '凯江大回湾'));
    pages.push(await openList(page, 'boq-allocation-list', targets.boq_allocation, '按比例'));
    const allocationBody = await page.locator('body').innerText();
    for (const expected of ['分配方式', '分配工程量', '分配金额', '分配比例(%)']) {
      check(allocationBody.includes(expected), `BOQ_ALLOCATION_COLUMN_MISSING:${expected}`);
    }
    check(state.pageErrors.length === 0, `PAGE_ERRORS:${JSON.stringify(state.pageErrors)}`);
    check(state.httpErrors.length === 0, `HTTP_ERRORS:${JSON.stringify(state.httpErrors)}`);
    check(state.consoleErrors.length === 0, `CONSOLE_ERRORS:${JSON.stringify(state.consoleErrors)}`);
    delete state.contractResponses;
    const result = { status: 'PASS', database, login: loginName, projectId, versionId, pages, boqWorksheet, boqImportEntry, wbsHierarchy, runtime: state };
    fs.writeFileSync(path.join(outputDir, 'result.json'), `${JSON.stringify(result, null, 2)}\n`);
    console.log(JSON.stringify(result));
  } finally {
    await context.close();
    await browser.close();
  }
}

main().catch((error) => {
  console.error(`BOQ_BASELINE_BROWSER=FAIL ${error.stack || error.message}`);
  process.exitCode = 2;
});
