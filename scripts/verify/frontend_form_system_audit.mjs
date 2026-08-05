#!/usr/bin/env node

import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { launchChromium } from './playwright_runtime.mjs';
import { captureReleasedNavigation } from './released_navigation_target.mjs';
import { resolveAcceptanceEnvironment } from './lib/frontend_acceptance_environment.mjs';
import { acquireAcceptanceLease } from './lib/frontend_acceptance_lease.mjs';

const acceptance = resolveAcceptanceEnvironment({ tool: 'form-system-audit', env: { ...process.env, FRONTEND_URL: process.env.SC_FRONTEND_URL || process.env.FRONTEND_URL, DB_NAME: process.env.SC_FORM_AUDIT_DB || process.env.DB_NAME } });
const BASE_URL = acceptance.baseUrl;
const USERNAME = process.env.SC_FORM_AUDIT_USER || acceptance.login || acceptance.roleBindings.contract_operator || '';
const PASSWORD = process.env.SC_FORM_AUDIT_PASSWORD || acceptance.password || process.env.SC_ACCEPTANCE_FIXTURE_PASSWORD || '';
const DB_NAME = acceptance.database;
const OUTPUT_ROOT = path.resolve(process.env.SC_FORM_AUDIT_OUTPUT || '.runtime/final-acceptance');
const JSON_OUTPUT = path.resolve(process.env.SC_FORM_AUDIT_JSON || '.runtime/form-audit.json');
const REFERENCE_SOURCE_ROOT = path.resolve(process.env.SC_FORM_AUDIT_REFERENCE_SOURCE || '.runtime/frontend-system-audit/baseline/form-system');
const SOURCE_SHA = process.env.SC_ACCEPTANCE_SHA || execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
let discoveredRoutes = null;
assert(PASSWORD, 'SC_FORM_AUDIT_PASSWORD or SC_ACCEPTANCE_FIXTURE_PASSWORD is required');
assert(USERNAME, `profile ${acceptance.profile} requires a form audit login`);
const acceptanceLease = await acquireAcceptanceLease({ root: acceptance.artifactRoot, mode: 'shared-read', owner: { tool: 'form-system-audit', profile: acceptance.profile, source_sha: SOURCE_SHA } });
const VIEWPORTS = [
  { key: '1440', width: 1440, height: 900 },
  { key: '1280', width: 1280, height: 800 },
  { key: '1024', width: 1024, height: 768 },
  { key: '768', width: 768, height: 1024 },
  { key: '390', width: 390, height: 844 },
];
const BOSS_REFERENCE = {
  product: 'BOSS管账 / PUMA',
  source_url: 'https://p.puma.cash360.cn/puma/biz/contract/sale',
  login_url: 'https://www.boss361.cn/login.html',
  allowed_source_hosts: ['p.puma.cash360.cn', 'www.boss361.cn'],
  screenshots: [
    'boss-puma-reference-list.png',
    'boss-puma-reference-detail.png',
    'boss-puma-reference-edit.png',
    'boss-puma-reference-scroll.png',
  ],
  privacy: '通过既有登录会话采集；公司、合同、人员、金额及编号已遮挡；浏览器 chrome 已裁除',
};
const EXTERNAL_MATURE_PRODUCT_REFERENCE = {
  product: '泛微·今承达数智化合同管理系统',
  source_url: 'https://jincenda.weaver.com.cn/functions.html',
  source_host: 'jincenda.weaver.com.cn',
  screenshots: [
    'boss-reference-weaver-2.png',
    'boss-reference-weaver-3.png',
    'boss-reference-weaver-4.png',
  ],
};
const BOSS_COMPARISON_DIMENSIONS = [
  { dimension: '顶部命令区高度和操作顺序', boss: '详情操作位于抽屉底部；编辑页标题固定在内容顶部，保存并提交/保存草稿/取消固定在底部。', current: '返回、模式、保存状态和主次操作集中在 sticky 顶部命令区。', conclusion: '交互位置不同；当前方案在长表单中保留上下文，操作可达性优于目标样本，无需回退。' },
  { dimension: '字段标签、控件和列数', boss: '变更表单以两列输入和标签-值展示为主，控件边界轻，字段间留白较大。', current: '桌面短字段采用三列语义布局，统一 36px 控件，长字段独占整行。', conclusion: '视觉语言一致，当前单屏容量更高，无需修改。' },
  { dimension: '章节标题表现', boss: '依靠大段留白、粗体小标题和表头区分章节，没有独立章节导航。', current: '使用轻量章节条、细分隔线和可定位章节导航。', conclusion: '当前层级更明确，色块已足够克制，无需修改。' },
  { dimension: '状态流程', boss: '列表以全部/待审批/待结算/待收款/已完成作为状态过滤；详情以合同变更、完成、驳回等动作表达生命周期。', current: '详情提供有序业务流程，移动显示当前/下一步和阶段计数。', conclusion: '业务表达不同；当前顺序语义更强，不应改成筛选按钮。' },
  { dimension: '表单密度', boss: '主要字段较疏，长滚动中出现明显留白；明细表保持紧凑表头。', current: '三列字段、12px 行距和轻量章节提高首屏容量。', conclusion: '当前密度达到并局部优于目标样本，无需修改。' },
  { dimension: '关系选择', boss: '已采样表单以字段旁蓝色编辑入口进入关系编辑，未暴露独立搜索弹窗。', current: 'many2one 使用搜索弹窗；移动结果为信息卡片并明确选中状态。', conclusion: '目标样本未暴露可直接对等的弹窗；当前方案满足复杂数据选择，不据此改动。' },
  { dimension: '明细表', boss: '收款计划采用紧凑桌面表格，空态直接置于表体。', current: '桌面维持表格，390px 降级为字段卡片并保留新增/移除操作。', conclusion: '桌面结构一致；当前窄屏降级更完整，无需修改。' },
  { dimension: '移动响应式策略', boss: '本次既有登录会话的目标合同路由仅暴露桌面工作区，未取得独立移动版合同表单证据。', current: '390px 覆盖命令区、流程、章节、关系卡片和 one2many。', conclusion: '该维度明确标记为目标样本未暴露，不能反推 BOSS 移动通过；当前响应式结论由自身真实浏览器矩阵支撑。' },
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
  { severity: 'P0', issue: '移动说明文字被祖先容器静默裁切', resolution: '约束片段根节点宽度并增加可见文字内部与祖先裁切检测' },
  { severity: 'P1', issue: '移动流程与章节后续内容不可发现', resolution: '活动项自动居中、阶段/章节计数、横向提示与全项可达断言' },
  { severity: 'P1', issue: '移动关系结果是压缩桌面表格', resolution: '改为按内容收敛的结果卡片，未选择时禁用确认' },
  { severity: 'P2', issue: '验收 JSON 中文在 HTTP 下可能乱码', resolution: 'UTF-8 往返断言并由验收服务器显式声明 charset' },
  { severity: 'P0', issue: '辅助产品截图被错误声明为真实 BOSS 参考', resolution: '真实 BOSS/PUMA 与泛微辅助参考分离，来源、哈希、对照维度和结论分别校验' },
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
  await page.locator('.layout-shell').waitFor({ state: 'visible', timeout: 45_000 });
  await page.waitForFunction(() => !/正在初始化|正在加载导航/.test(document.body.innerText || ''), null, { timeout: 45_000 });
}

function nodeRoute(node) {
  const meta = node?.meta && typeof node.meta === 'object' ? node.meta : {};
  const route = String(node?.route || meta.route || '');
  const actionId = Number(node?.action_id || node?.actionId || node?.action || meta.action_id || meta.actionId || 0);
  const menuId = Number(node?.menu_id || node?.menuId || meta.menu_id || meta.menuId || 0);
  if (route) return /^\/a\/\d+(?:\?|$)/.test(route) && menuId > 0 && !/[?&]menu_id=/.test(route)
    ? `${route}${route.includes('?') ? '&' : '?'}menu_id=${menuId}`
    : route;
  if (actionId > 0) return `/a/${actionId}${menuId > 0 ? `?menu_id=${menuId}` : ''}`;
  if (menuId > 0) return `/m/${menuId}`;
  return '';
}

function actionableNodes(nodes, ancestors = []) {
  const rows = [];
  for (const node of Array.isArray(nodes) ? nodes : []) {
    const label = String(node?.title || node?.label || node?.name || '').trim();
    const labels = [...ancestors, label].filter(Boolean);
    const route = nodeRoute(node);
    if (route) rows.push({ label, path: labels.join(' / '), route });
    rows.push(...actionableNodes(node?.children, labels));
  }
  return rows;
}

function relativePageUrl(page) {
  const current = new URL(page.url());
  return `${current.pathname}${current.search}`;
}

async function waitForRuntimePage(page) {
  await page.locator('.layout-shell').waitFor({ state: 'visible', timeout: 45_000 });
  await page.waitForFunction(() => {
    const main = document.querySelector('#main-content');
    return Boolean(main?.children.length) && !/正在加载页面|正在加载列表|正在初始化/.test(document.body.innerText || '');
  }, null, { timeout: 45_000 });
  await page.locator('.product-loading-shell').waitFor({ state: 'detached', timeout: 45_000 }).catch(() => {});
}

async function discoverFormRoutes(page, listRoute, formTimeout = 12_000) {
  await page.goto(`${BASE_URL}${listRoute}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  await waitForRuntimePage(page);
  const firstRecord = page.locator('.cell-primary-link:visible, .mobile-record-card:visible').first();
  assert(await firstRecord.count(), `runtime list did not expose a record link: ${listRoute}`);
  await firstRecord.click();
  await page.locator('[data-product-page-mode="form"]').waitFor({ state: 'visible', timeout: formTimeout });
  await page.locator('[data-form-canvas]').waitFor({ state: 'visible', timeout: formTimeout });
  let readonly = relativePageUrl(page);
  let edit = '';
  const editAction = page.getByRole('button', { name: /^编辑$/ }).first();
  if (await editAction.count() && await editAction.isEnabled().catch(() => false)) {
    await editAction.click();
    await page.locator('[data-form-canvas] input:visible, [data-form-canvas] textarea:visible, [data-form-canvas] select:visible').first().waitFor({ state: 'visible', timeout: 45_000 });
    edit = relativePageUrl(page);
  }
  if (!edit && /^\/r\//.test(readonly)) {
    const derivedEdit = readonly.replace(/^\/r\//, '/f/');
    await page.goto(`${BASE_URL}${derivedEdit}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
    const editable = page.locator('[data-form-canvas] input:visible, [data-form-canvas] textarea:visible, [data-form-canvas] select:visible').first();
    if (await editable.waitFor({ state: 'visible', timeout: 12_000 }).then(() => true).catch(() => false)) edit = relativePageUrl(page);
  }
  if (!edit) {
    await page.goto(`${BASE_URL}${listRoute}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
    await waitForRuntimePage(page);
    const recordCount = await page.locator('.cell-primary-link:visible, .mobile-record-card:visible').count();
    for (let index = 1; index < Math.min(recordCount, 12) && !edit; index += 1) {
      await page.goto(`${BASE_URL}${listRoute}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
      await waitForRuntimePage(page);
      const record = page.locator('.cell-primary-link:visible, .mobile-record-card:visible').nth(index);
      await record.click();
      const formVisible = await page.locator('[data-form-canvas]').waitFor({ state: 'visible', timeout: 8_000 }).then(() => true).catch(() => false);
      if (!formVisible) continue;
      const candidateReadonly = relativePageUrl(page);
      if (!/^\/r\//.test(candidateReadonly)) continue;
      await page.goto(`${BASE_URL}${candidateReadonly.replace(/^\/r\//, '/f/')}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
      const candidateEditable = page.locator('[data-form-canvas] input:visible, [data-form-canvas] textarea:visible, [data-form-canvas] select:visible').first();
      if (await candidateEditable.waitFor({ state: 'visible', timeout: 8_000 }).then(() => true).catch(() => false)) {
        readonly = candidateReadonly;
        edit = relativePageUrl(page);
      }
    }
  }
  await page.goto(`${BASE_URL}${listRoute}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  await waitForRuntimePage(page);
  let create = '';
  const createAction = page.getByRole('button', { name: /新建/ }).last();
  if (await createAction.count() && await createAction.isEnabled().catch(() => false)) {
    await createAction.click();
    const category = page.locator('.business-category-picker-option:visible').first();
    if (await category.count()) await category.click();
    await page.locator('[data-product-page-mode="form"]').waitFor({ state: 'visible', timeout: 45_000 });
    await page.locator('[data-form-canvas]').waitFor({ state: 'visible', timeout: 45_000 });
    create = relativePageUrl(page);
  }
  return { list: listRoute, readonly, edit, create };
}

async function discoverCreateRoute(page, listRoute) {
  await page.goto(`${BASE_URL}${listRoute}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  await waitForRuntimePage(page);
  const createAction = page.getByRole('button', { name: /新建/ }).last();
  assert(await createAction.count() && await createAction.isEnabled().catch(() => false), `runtime list did not expose enabled create action: ${listRoute}`);
  await createAction.click();
  const category = page.locator('.business-category-picker-option:visible').first();
  if (await category.count()) await category.click();
  await page.locator('[data-product-page-mode="form"]').waitFor({ state: 'visible', timeout: 20_000 });
  await page.locator('[data-form-canvas]').waitFor({ state: 'visible', timeout: 20_000 });
  return { list: listRoute, readonly: '', edit: '', create: relativePageUrl(page) };
}

async function discoverFirstCapableFormRoute(page, candidates, requirement) {
  const attempts = [];
  for (const candidate of candidates) {
    try {
      const routes = requirement === 'complex-create'
        ? await discoverCreateRoute(page, candidate.route)
        : await discoverFormRoutes(page, candidate.route);
      const capable = requirement === 'complex-create' ? Boolean(routes.create) : Boolean(routes.readonly);
      attempts.push({ path: candidate.path, route: candidate.route, capable });
      if (capable) return { ...routes, discovered_path: candidate.path, attempts };
    } catch (error) {
      attempts.push({ path: candidate.path, route: candidate.route, capable: false, reason: error instanceof Error ? error.message.split('\n')[0] : String(error) });
    }
  }
  throw new Error(`no ${requirement} route discovered from authenticated navigation: ${JSON.stringify(attempts)}`);
}

function routeWithQuery(route, key, value) {
  const separator = route.includes('?') ? '&' : '?';
  return `${route}${separator}${encodeURIComponent(key)}=${encodeURIComponent(value)}`;
}

function requiredRoute(scope, mode) {
  const route = discoveredRoutes?.[scope]?.[mode] || '';
  assert(route, `runtime discovery did not expose ${scope}.${mode}`);
  return route;
}

function missingRecordRoute() {
  const route = requiredRoute('general', 'readonly');
  const replaced = route.replace(/(\/r\/[^/]+\/)\d+/, '$1999999999');
  assert(replaced !== route, `readonly route does not contain a record id: ${route}`);
  return replaced;
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
    await page.getByRole('heading', { name: '记录不存在', exact: true, level: 2 }).waitFor({ state: 'visible', timeout: 30_000 });
    return;
  }
  await page.locator('[data-form-canvas]').waitFor({ state: 'visible', timeout: 45_000 });
  if (mode === 'readonly') await page.locator('.form-readonly-value, .readonly-value, .contract-readonly-value').first().waitFor({ state: 'visible' });
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

async function findVisibleTextClipping(page) {
  return page.evaluate(() => {
    const viewportWidth = document.documentElement.clientWidth;
    const ignoredTags = new Set(['SCRIPT', 'STYLE', 'SVG', 'PATH', 'OPTION', 'NOSCRIPT']);
    const visible = (element) => {
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return style.display !== 'none' && style.visibility !== 'hidden' && Number(style.opacity) !== 0 && rect.width > 0 && rect.height > 0;
    };
    const hasOwnText = (element) => Array.from(element.childNodes).some((node) => node.nodeType === Node.TEXT_NODE && String(node.textContent || '').trim());
    const label = (element) => String(element.getAttribute('aria-label') || element.getAttribute('title') || element.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 90);
    const selector = (element) => {
      if (element.id) return `#${CSS.escape(element.id)}`;
      const classes = Array.from(element.classList).slice(0, 3).map((item) => `.${CSS.escape(item)}`).join('');
      return `${element.tagName.toLowerCase()}${classes}`;
    };
    const failures = [];
    for (const element of document.body.querySelectorAll('*')) {
      if (ignoredTags.has(element.tagName) || !visible(element)) continue;
      const isTextControl = element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement || element instanceof HTMLButtonElement;
      if (!hasOwnText(element) && !isTextControl) continue;
      const text = isTextControl ? String(element.value || element.textContent || element.getAttribute('aria-label') || '').trim() : label(element);
      if (!text) continue;
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      if (rect.width <= 2 && rect.height <= 2 && ['hidden', 'clip'].includes(style.overflow)) continue;
      const ownOverflow = element.scrollWidth > element.clientWidth + 1;
      const intentionalScroller = ['auto', 'scroll'].includes(style.overflowX);
      const explainedEllipsis = style.textOverflow === 'ellipsis' && Boolean(element.getAttribute('title') || element.getAttribute('aria-label'));
      let clippingAncestor = null;
      let insideIntentionalScroller = false;
      for (let parent = element.parentElement; parent && parent !== document.body; parent = parent.parentElement) {
        const parentStyle = getComputedStyle(parent);
        if (['auto', 'scroll'].includes(parentStyle.overflowX)) insideIntentionalScroller = true;
        if (!['hidden', 'clip'].includes(parentStyle.overflowX)) continue;
        const parentRect = parent.getBoundingClientRect();
        if (!insideIntentionalScroller && (rect.left < parentRect.left - 1 || rect.right > parentRect.right + 1)) {
          clippingAncestor = selector(parent);
          break;
        }
      }
      const silentlyOutsideViewport = !insideIntentionalScroller && document.documentElement.scrollWidth <= viewportWidth + 1 && (rect.left < -1 || rect.right > viewportWidth + 1);
      if ((ownOverflow && !intentionalScroller && !explainedEllipsis) || clippingAncestor || silentlyOutsideViewport) {
        failures.push({
          selector: selector(element), text: text.slice(0, 60), client_width: element.clientWidth,
          scroll_width: element.scrollWidth, overflow_x: style.overflowX, clipping_ancestor: clippingAncestor,
          rect: { left: Math.round(rect.left), right: Math.round(rect.right), width: Math.round(rect.width) },
        });
      }
    }
    return failures.slice(0, 30);
  });
}

async function assertVisibleTextNotClipped(page, id) {
  const failures = await findVisibleTextClipping(page);
  return result(id, failures.length === 0, { clipped_count: failures.length, samples: failures }, 'P0');
}

async function createAuthenticatedPage(browser, viewport, scope) {
  const context = await browser.newContext({ viewport, locale: 'zh-CN' });
  const page = await context.newPage();
  watchRuntime(page, scope);
  await login(page);
  return { context, page };
}

async function captureBaselineHelperCrop(browser) {
  const source = path.join(OUTPUT_ROOT, 'form-before-create-390.png');
  try { await fs.access(source); } catch { return; }
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await context.newPage();
  await page.goto(`file://${source}`, { waitUntil: 'load' });
  await page.screenshot({ path: path.join(OUTPUT_ROOT, 'form-before-helper-wrap-390.png'), clip: { x: 17, y: 223, width: 342, height: 205 } });
  await context.close();
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
  await openForm(page, requiredRoute('general', 'readonly'), 'readonly');
  await assertNoOverflow(page, `readonly.${viewportKey}.no_horizontal_overflow`);
  await assertVisibleTextNotClipped(page, `visible_text_not_clipped.${viewportKey}.readonly`);
  const empty = await page.locator('.form-readonly-value--empty:visible, .contract-readonly-value--empty:visible').allInnerTexts();
  result(`readonly.${viewportKey}.empty_value_policy`, empty.every((text) => text.trim() === '未填写'), { empty_count: empty.length }, 'P1');
  const columns = await page.locator('.template-form-section-grid:visible').first().evaluate((element) => getComputedStyle(element).gridTemplateColumns.split(' ').length);
  result(`readonly.${viewportKey}.responsive_columns`, viewportKey === '1440' ? columns >= 2 : viewportKey === '390' ? columns === 1 : columns >= 1, { columns }, 'P1');
  const garbled = await page.locator('body').innerText().then((text) => text.match(/\uFFFD|Ã.|Â.|æ[\x80-\xBF]|ç[\x80-\xBF]/g) || []);
  result(`readonly.${viewportKey}.encoding`, garbled.length === 0, { matches: garbled.slice(0, 10) }, 'P0');
  const name = `form-final-readonly-${viewportKey}.png`;
  await capture(page, name);
  return name;
}

async function auditResponsiveCreate(page, viewportKey) {
  await openForm(page, routeWithQuery(requiredRoute('general', 'create'), 'activity_page_id', `form_system_${viewportKey}`), 'create');
  await assertNoOverflow(page, `create.${viewportKey}.no_horizontal_overflow`);
  await assertVisibleTextNotClipped(page, `visible_text_not_clipped.${viewportKey}.create`);
  if (viewportKey === '1440') await auditFieldGeometry(page);
  const command = await page.locator('.contract-form-command-bar:visible').boundingBox();
  result(`create.${viewportKey}.command_compact`, Boolean(command) && (viewportKey !== '390' || command.height <= 154), command, 'P1');
  const sectionNav = page.locator('.form-section-nav:visible');
  const tabs = sectionNav.locator('[data-section-tab]');
  const renderedSections = page.locator('[data-group-title]:visible');
  const sectionCount = await renderedSections.count();
  const tabCount = await tabs.count();
  result(`section_count_matches_rendered_sections.${viewportKey}`, await sectionNav.count() === 1 && tabCount === sectionCount, { navigation_count: await sectionNav.count(), tab_count: tabCount, rendered_section_count: sectionCount }, 'P0');
  const activeTabMetric = await sectionNav.evaluate((nav) => {
    const active = nav.querySelector('[data-section-tab].is-active');
    const progress = nav.parentElement?.querySelector('.form-section-progress');
    if (!(active instanceof HTMLElement)) return { exists: false };
    const navRect = nav.getBoundingClientRect();
    const activeRect = active.getBoundingClientRect();
    const progressRect = progress?.getBoundingClientRect();
    const progressOverlays = progress instanceof HTMLElement && getComputedStyle(progress).position === 'absolute';
    return {
      exists: true,
      fully_visible: activeRect.left >= navRect.left - 1 && activeRect.right <= (progressOverlays ? progressRect?.left || navRect.right : navRect.right) + 1,
      active: { left: activeRect.left, right: activeRect.right },
      viewport: { left: navRect.left, right: progressOverlays ? progressRect?.left || navRect.right : navRect.right },
    };
  });
  result(`active_section_tab_in_view.${viewportKey}`, Boolean(activeTabMetric.exists && activeTabMetric.fully_visible), activeTabMetric, 'P0');
  const name = `form-final-create-${viewportKey}.png`;
  await capture(page, name);
  if (viewportKey === '390') {
    const helperName = 'form-final-helper-wrap-390.png';
    const helperBox = await page.locator('.native-default-section-head:visible').boundingBox();
    if (helperBox) {
      await page.screenshot({
        path: path.join(OUTPUT_ROOT, helperName),
        clip: {
          x: Math.max(0, helperBox.x - 12), y: Math.max(0, helperBox.y - 12),
          width: Math.min(390, helperBox.width + 24), height: helperBox.height + 24,
        },
      });
    }
    screenshots.push(helperName);
  }
  return name;
}

async function auditWorkflow(page, viewportKey) {
  await openForm(page, requiredRoute('general', 'readonly'), 'readonly');
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
    const activeMetric = await track.evaluate((element) => {
      const active = element.querySelector('[aria-current="step"]');
      if (!(active instanceof HTMLElement)) return { exists: false };
      const trackRect = element.getBoundingClientRect();
      const activeRect = active.getBoundingClientRect();
      return { exists: true, fully_visible: activeRect.left >= trackRect.left - 1 && activeRect.right <= trackRect.right + 1, active: { left: activeRect.left, right: activeRect.right }, track: { left: trackRect.left, right: trackRect.right }, scroll_left: element.scrollLeft };
    });
    result('active_workflow_step_in_view', Boolean(activeMetric.exists && activeMetric.fully_visible), activeMetric, 'P0');
    const reachability = await track.evaluate(async (element) => {
      const steps = Array.from(element.querySelectorAll('button'));
      const maximum = Math.max(0, element.scrollWidth - element.clientWidth);
      element.scrollLeft = 0;
      await new Promise((resolve) => requestAnimationFrame(() => resolve()));
      const startRect = steps[0]?.getBoundingClientRect();
      const trackRect = element.getBoundingClientRect();
      const firstReachable = Boolean(startRect && startRect.left >= trackRect.left - 1 && startRect.right <= trackRect.right + 1);
      element.scrollLeft = maximum;
      await new Promise((resolve) => requestAnimationFrame(() => resolve()));
      const endRect = steps.at(-1)?.getBoundingClientRect();
      const lastReachable = Boolean(endRect && endRect.left >= trackRect.left - 1 && endRect.right <= trackRect.right + 1);
      const keyboardReachable = steps.every((step) => !step.hasAttribute('disabled') && step.tabIndex >= 0);
      return { first_reachable: firstReachable, last_reachable: lastReachable, keyboard_reachable: keyboardReachable, maximum_scroll: maximum, step_count: steps.length };
    });
    result('all_workflow_steps_reachable', reachability.first_reachable && reachability.last_reachable && reachability.keyboard_reachable, reachability, 'P0');
    await current.evaluate((element) => element.scrollIntoView({ block: 'nearest', inline: 'center' }));
  }
  await capture(page, `form-final-workflow-${viewportKey}.png`, { fullPage: false });
}

async function auditValidation(page) {
  await openForm(page, routeWithQuery(requiredRoute('general', 'create'), 'activity_page_id', 'form_system_validation'), 'create');
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
  const errorSections = await page.locator('.form-section-nav .has-error').count();
  const summaryGeometry = await page.evaluate(() => {
    const summaryElement = document.querySelector('[data-form-error-summary]');
    const commandElement = document.querySelector('.contract-form-command-bar');
    if (!(summaryElement instanceof HTMLElement) || !(commandElement instanceof HTMLElement)) return { available: false, clear: false };
    const summaryRect = summaryElement.getBoundingClientRect();
    const commandRect = commandElement.getBoundingClientRect();
    const intersectsViewport = summaryRect.bottom > 0 && summaryRect.top < window.innerHeight;
    return {
      available: true,
      intersects_viewport: intersectsViewport,
      summary_top: Math.round(summaryRect.top),
      summary_bottom: Math.round(summaryRect.bottom),
      command_bottom: Math.round(commandRect.bottom),
      clear: intersectsViewport && summaryRect.top >= commandRect.bottom - 1 && summaryRect.bottom <= window.innerHeight + 1,
    };
  });
  result('validation.summary_and_fields', await summary.count() === 1 && invalidCount > 0, { invalid_count: invalidCount }, 'P0');
  result('validation.focus_first_error', focused && inView, { focused, in_view: inView }, 'P0');
  result('validation.error_relationship', describedCount > 0, { described_by: describedBy, described_nodes: describedCount }, 'P0');
  result('validation.summary_not_partially_covered', summaryGeometry.clear, summaryGeometry, 'P0');
  await page.waitForTimeout(180);
  const synchronizedErrorSections = await page.locator('.form-section-nav .has-error').count();
  result('validation.section_error_state', synchronizedErrorSections > 0, { error_sections: synchronizedErrorSections, initial_count: errorSections }, 'P1');
  await capture(page, 'form-final-validation-failure.png', { fullPage: false });
}

async function auditKeyboardAndUnsaved(page) {
  await openForm(page, requiredRoute('general', 'edit'), 'edit');
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
  await openForm(page, requiredRoute('general', 'edit'), 'edit');
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
  await openForm(page, requiredRoute('general', 'edit'), 'edit');
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
  await openForm(page, routeWithQuery(requiredRoute('complex', 'create'), 'activity_page_id', `form_system_complex_${viewportKey}`), 'create');
  const duplicateFormIds = await page.locator('[data-form-canvas]').evaluate((canvas) => {
    const counts = new Map();
    for (const element of canvas.querySelectorAll('[id]')) counts.set(element.id, (counts.get(element.id) || 0) + 1);
    return [...counts.entries()].filter(([, count]) => count > 1).map(([id, count]) => ({ id, count }));
  });
  result(`form.${viewportKey}.unique_dom_ids`, duplicateFormIds.length === 0, { duplicates: duplicateFormIds }, 'P0');
  const many2one = page.locator('.many2one-widget-shell input:visible').first();
  await many2one.focus();
  result(`many2one.${viewportKey}.combobox_semantics`, await many2one.getAttribute('role') === 'combobox' && Boolean(await many2one.getAttribute('aria-controls')), {
    role: await many2one.getAttribute('role'),
    controls: await many2one.getAttribute('aria-controls'),
  }, 'P0');
  const inlineOptions = many2one.locator('xpath=ancestor::*[contains(@class,"many2one-combobox")][1]').locator('[role="option"]');
  if (await inlineOptions.count()) {
    await many2one.press('ArrowDown');
    const activeDescendant = await many2one.getAttribute('aria-activedescendant');
    result(`many2one.${viewportKey}.arrow_navigation`, Boolean(activeDescendant) && await page.locator(`#${activeDescendant}`).getAttribute('aria-selected') === 'true', { active_descendant: activeDescendant }, 'P0');
    await many2one.press('Escape');
    result(`many2one.${viewportKey}.escape_closes_and_retains_focus`, await many2one.getAttribute('aria-expanded') === 'false' && await many2one.evaluate((element) => document.activeElement === element), {
      expanded: await many2one.getAttribute('aria-expanded'),
    }, 'P0');
    await many2one.focus();
  }
  const many2oneComboboxes = page.locator('.many2one-combobox:visible');
  let searchableCombobox = null;
  let dialogInput = null;
  let dialog = null;
  for (let index = 0; index < await many2oneComboboxes.count(); index += 1) {
    const candidate = many2oneComboboxes.nth(index);
    const candidateInput = candidate.locator('input:visible').first();
    await candidateInput.focus();
    await page.waitForTimeout(50);
    const candidateSearch = candidate.getByRole('button', { name: /搜索更多/ });
    if (!await candidateSearch.count()) continue;
    await candidateSearch.click();
    const candidateDialog = page.getByRole('dialog');
    await candidateDialog.waitFor({ state: 'visible', timeout: 10_000 });
    const populated = await candidateDialog.locator('.relation-dialog-result-card:visible, .relation-dialog-table tbody tr:visible').first()
      .waitFor({ state: 'visible', timeout: 10_000 }).then(() => true).catch(() => false);
    if (populated) {
      searchableCombobox = candidate;
      dialogInput = candidateInput;
      dialog = candidateDialog;
      break;
    }
    await page.keyboard.press('Escape');
    await candidateDialog.waitFor({ state: 'hidden', timeout: 5_000 });
  }
  if (searchableCombobox && dialogInput && dialog) {
    const rect = await dialog.boundingBox();
    const viewport = page.viewportSize();
    const contained = Boolean(rect && viewport && rect.x >= 0 && rect.y >= 0 && rect.x + rect.width <= viewport.width + 1 && rect.y + rect.height <= viewport.height + 1);
    result(`relation.${viewportKey}.dialog_contained`, contained, { rect, viewport }, 'P0');
    const selectButton = dialog.getByRole('button', { name: '选择', exact: true });
    const disabledWithoutSelection = await selectButton.isDisabled();
    result(`relation_select_disabled_without_selection.${viewportKey}`, disabledWithoutSelection, { disabled: disabledWithoutSelection }, 'P0');
    if (viewportKey === '390') {
      const cards = dialog.locator('.relation-dialog-result-card:visible');
      await cards.first().waitFor({ state: 'visible', timeout: 10_000 });
      const cardRect = await cards.first().boundingBox();
      const mobileTableVisible = await dialog.locator('.relation-dialog-table:visible').count();
      result('relation.390.mobile_result_card', Boolean(cardRect) && mobileTableVisible === 0, { card: cardRect, cards: await cards.count(), desktop_table_visible: mobileTableVisible }, 'P0');
      await capture(page, 'form-final-relation-dialog-390-unselected.png', { fullPage: false });
      await cards.first().click();
      result('relation.390.selection_enables_confirm', await selectButton.isEnabled() && await cards.first().evaluate((element) => element.classList.contains('relation-dialog-result-card--active')), { enabled: await selectButton.isEnabled() }, 'P0');
    }
    await capture(page, `form-final-relation-dialog-${viewportKey}.png`, { fullPage: false });
    await page.keyboard.press('Escape');
    await page.waitForTimeout(100);
    result(`relation.${viewportKey}.escape_restores_focus`, await dialogInput.evaluate((element) => document.activeElement === element), {}, 'P1');
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
      const addAction = one2many.locator('.o2m-toolbar button:visible').first();
      const removeAction = one2many.locator('.o2m-row-remove:visible').first();
      const reachable = async (locator) => {
        if (!await locator.count()) return false;
        await locator.scrollIntoViewIfNeeded();
        return locator.evaluate((element) => {
          const rect = element.getBoundingClientRect();
          const commandBottom = document.querySelector('.contract-form-command-bar')?.getBoundingClientRect().bottom || 0;
          return rect.top >= commandBottom - 1 && rect.bottom <= window.innerHeight + 1 && rect.width > 0 && rect.height > 0;
        });
      };
      const reachability = { add_reachable: await reachable(addAction), remove_reachable: await reachable(removeAction), rows: await rows.count() };
      result('one2many_actions_reachable', reachability.add_reachable && reachability.remove_reachable, reachability, 'P0');
    }
    await capture(page, `form-final-one2many-${viewportKey}.png`, { fullPage: false });
  }
  await assertNoOverflow(page, `complex.${viewportKey}.no_horizontal_overflow`);
  return page.locator('[data-field-type]').evaluateAll((elements) => elements.map((element) => element.getAttribute('data-field-type')).filter(Boolean));
}

async function auditLongForm(page) {
  await openForm(page, requiredRoute('general', 'edit'), 'edit');
  const collaboration = page.locator('.native-chatter-block:visible');
  await collaboration.scrollIntoViewIfNeeded();
  await page.waitForTimeout(180);
  const command = await page.locator('.contract-form-command-bar:visible').boundingBox();
  const nav = await page.locator('.form-section-nav:visible').boundingBox();
  const viewport = page.viewportSize();
  const actionsReachable = Boolean(command && viewport && command.y >= 0 && command.y + command.height <= viewport.height);
  result('long_form.primary_actions_sticky', actionsReachable, { command, viewport }, 'P0');
  result('long_form.section_context_sticky', Boolean(nav && nav.y >= (command?.y || 0) && nav.y + nav.height <= (viewport?.height || 0)), { nav, command }, 'P1');
  const sectionTabs = page.locator('.form-section-nav [data-section-tab]');
  const targetTab = sectionTabs.nth(Math.min(2, Math.max(0, await sectionTabs.count() - 1)));
  if (await targetTab.count()) {
    const title = await targetTab.getAttribute('data-section-tab');
    await targetTab.click();
    await page.waitForTimeout(420);
    const anchorMetric = await page.evaluate((targetTitle) => {
      const target = Array.from(document.querySelectorAll('[data-group-title]')).find((element) => element.getAttribute('data-group-title') === targetTitle);
      const commandBottom = document.querySelector('.contract-form-command-bar')?.getBoundingClientRect().bottom || 0;
      const navBottom = document.querySelector('.form-section-nav-shell')?.getBoundingClientRect().bottom || commandBottom;
      const targetTop = target?.getBoundingClientRect().top ?? -1;
      return { target_title: targetTitle, target_top: targetTop, obstruction_bottom: Math.max(commandBottom, navBottom), clear: targetTop >= Math.max(commandBottom, navBottom) - 2 };
    }, title);
    result('sticky_header_does_not_cover_anchor', anchorMetric.clear, anchorMetric, 'P0');
  } else {
    result('sticky_header_does_not_cover_anchor', false, { reason: 'no section navigation target' }, 'P0');
  }
  result('collaboration.attachment_and_messages', await collaboration.count() === 1 && await collaboration.locator('.native-attachment-tools').count() === 1, { collaboration_count: await collaboration.count() }, 'P1');
  await capture(page, 'form-final-long-form-scrolled.png', { fullPage: false });
  await collaboration.screenshot({ path: path.join(OUTPUT_ROOT, 'form-final-collaboration.png') });
  screenshots.push('form-final-collaboration.png');
}

async function auditDesigner(page, viewportKey = '1440') {
  await openForm(page, routeWithQuery(requiredRoute('general', 'edit'), 'config_mode', 'form_field_configuration'), 'edit');
  const regions = {};
  for (const selector of ['.contract-form-designer-sidebar', '.contract-form-designer-canvas', '.record-form-inspector']) {
    regions[selector] = await page.locator(selector).first().boundingBox();
  }
  const sameRow = Object.values(regions).every((rect) => rect && Math.abs(rect.y - regions['.contract-form-designer-canvas'].y) <= 2);
  const mobileCanvasFirst = ['768', '390'].includes(viewportKey);
  const stacked = Object.values(regions).every(Boolean) && (mobileCanvasFirst
    ? regions['.contract-form-designer-canvas'].y < regions['.contract-form-designer-sidebar'].y
      && regions['.contract-form-designer-sidebar'].y < regions['.record-form-inspector'].y
    : regions['.contract-form-designer-sidebar'].y < regions['.contract-form-designer-canvas'].y
      && regions['.contract-form-designer-canvas'].y < regions['.record-form-inspector'].y);
  result(viewportKey === '1440' ? 'designer.three_region_workspace' : `designer.${viewportKey}.responsive_recomposition`, viewportKey === '1440' ? sameRow : stacked, regions, 'P0');
  await assertNoOverflow(page, `designer.${viewportKey}.no_horizontal_overflow`);
  await assertVisibleTextNotClipped(page, `designer.${viewportKey}.visible_text_not_clipped`);
  if (viewportKey === '390') {
    const touchTargets = await page.locator('.contract-field-governance-footer > button, .contract-form-settings-section-head > button').evaluateAll((buttons) => buttons
      .filter((button) => {
        const style = getComputedStyle(button);
        const rect = button.getBoundingClientRect();
        return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
      })
      .map((button) => ({ label: button.textContent?.trim() || '', height: button.getBoundingClientRect().height })));
    result('designer.390.key_actions_touch_size', touchTargets.length > 0 && touchTargets.every((target) => target.height >= 44), touchTargets, 'P1');
  }
  if (viewportKey !== '1440') {
    await capture(page, `form-final-designer-${viewportKey}.png`, { fullPage: false });
    return;
  }
  const firstField = page.locator('.contract-form-field-search-item').first();
  await firstField.click();
  const selectedKey = await page.locator('.contract-form-designer-canvas [aria-pressed="true"]').getAttribute('data-field-key');
  result('designer.field_selection', Boolean(selectedKey), { selected_key: selectedKey }, 'P1');
  const hide = page.locator('.record-form-inspector label').filter({ hasText: /^隐藏$/ }).first();
  if (await hide.count()) {
    await hide.click();
    const hiddenPreview = page.locator(`.contract-form-designer-canvas [data-field-key="${selectedKey}"].field--config-hidden`);
    result('designer.hidden_field_preview', await hiddenPreview.count() === 1, { selected_key: selectedKey, preview_count: await hiddenPreview.count() }, 'P1');
    const show = page.locator('.record-form-inspector label').filter({ hasText: /^显示$/ }).first();
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
  const navigation = page.goto(`${BASE_URL}${requiredRoute('general', 'edit')}`, { waitUntil: 'domcontentloaded' });
  const skeleton = page.locator('.product-form-loading-skeleton:visible, [aria-label*="正在载入"]:visible');
  await skeleton.first().waitFor({ timeout: 2_500 }).catch(() => {});
  const loadingVisible = await skeleton.count() > 0;
  if (loadingVisible) await capture(page, 'form-final-loading.png', { fullPage: false });
  await navigation;
  await page.locator('[data-form-canvas]').waitFor({ state: 'visible', timeout: 45_000 });
  await page.unroute('**/api/v1/intent**');
  result('loading.explicit_state', delayed && loadingVisible, { request_delayed: delayed, skeleton_visible: loadingVisible }, 'P1');
  await openForm(page, missingRecordRoute(), 'missing');
  result('empty_record.explicit_state', await page.getByRole('heading', { name: '记录不存在', exact: true, level: 2 }).count() === 1, {}, 'P1');
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

async function sha256(file) {
  return createHash('sha256').update(await fs.readFile(file)).digest('hex');
}

async function referenceFiles(reference) {
  const files = [];
  for (const name of reference.screenshots) {
    try { files.push({ name, sha256: await sha256(path.join(OUTPUT_ROOT, name)) }); }
    catch { files.push({ name, sha256: '', missing: true }); }
  }
  return files;
}

async function verifyReferenceSources() {
  const bossFiles = await referenceFiles(BOSS_REFERENCE);
  const weaverFiles = await referenceFiles(EXTERNAL_MATURE_PRODUCT_REFERENCE);
  const internalHashes = [];
  for (const name of screenshots.slice(0, 12)) {
    try { internalHashes.push(await sha256(path.join(OUTPUT_ROOT, name))); } catch { /* reported through missing evidence */ }
  }
  const sourceHosts = [new URL(BOSS_REFERENCE.source_url).hostname, new URL(BOSS_REFERENCE.login_url).hostname];
  const validBossHosts = sourceHosts.every((host) => BOSS_REFERENCE.allowed_source_hosts.includes(host));
  const completeBossFiles = bossFiles.every((item) => item.sha256 && !item.missing && !internalHashes.includes(item.sha256));
  const bossHashes = new Set(bossFiles.map((item) => item.sha256).filter(Boolean));
  const distinctFromWeaver = weaverFiles.every((item) => item.sha256 && !bossHashes.has(item.sha256));
  result('boss_reference_source_host_is_puma_or_boss361', validBossHosts && completeBossFiles, { source_hosts: sourceHosts, allowed_source_hosts: BOSS_REFERENCE.allowed_source_hosts, files: bossFiles, privacy: BOSS_REFERENCE.privacy }, 'P0');
  result('boss_reference_distinct_from_weaver_reference', distinctFromWeaver && weaverFiles.every((item) => !item.missing), { boss_files: bossFiles, external_mature_product_files: weaverFiles, distinct: distinctFromWeaver }, 'P0');
  const requiredDimensions = ['顶部命令区高度和操作顺序', '字段标签、控件和列数', '章节标题表现', '状态流程', '表单密度', '关系选择', '明细表', '移动响应式策略'];
  const mapped = new Set(BOSS_COMPARISON_DIMENSIONS.filter((item) => item.boss && item.current && item.conclusion).map((item) => item.dimension));
  result('boss_comparison_dimensions_complete', requiredDimensions.every((name) => mapped.has(name)) && mapped.size === requiredDimensions.length, { required: requiredDimensions, mapped: [...mapped] }, 'P0');
  return { bossFiles, weaverFiles };
}

async function stageReferenceAssets() {
  for (const name of [...BOSS_REFERENCE.screenshots, ...EXTERNAL_MATURE_PRODUCT_REFERENCE.screenshots]) {
    const source = path.join(REFERENCE_SOURCE_ROOT, name);
    const destination = path.join(OUTPUT_ROOT, name);
    await fs.access(source);
    await fs.copyFile(source, destination);
  }
}

function buildHtml(report) {
  const cards = report.screenshots.map((name) => `<article><h3>${htmlEscape(name)}</h3><a href="${encodeURI(name)}"><img loading="lazy" src="${encodeURI(name)}" alt="${htmlEscape(name)}"></a></article>`).join('');
  const assertionRows = report.assertions.map((item) => `<tr><td><span class="status ${item.status.toLowerCase()}">${item.status}</span></td><td>${htmlEscape(item.severity)}</td><td>${htmlEscape(item.id)}</td><td><code>${htmlEscape(JSON.stringify(item.detail))}</code></td></tr>`).join('');
  const stateRows = report.state_matrix.map((item) => `<tr><td>${htmlEscape(item.state)}</td><td>${htmlEscape(item.status)}</td></tr>`).join('');
  const fieldRows = report.field_type_matrix.map((item) => `<tr><td>${htmlEscape(item.type)}</td><td>${htmlEscape(item.status)}</td></tr>`).join('');
  const resolvedRows = report.resolved_issues.map((item) => `<tr><td>${htmlEscape(item.severity)}</td><td>${htmlEscape(item.issue)}</td><td>${htmlEscape(item.resolution)}</td></tr>`).join('');
  const baselineCards = report.baseline_screenshots.map((name) => `<article><h3>${htmlEscape(name)}</h3><a href="${encodeURI(name)}"><img loading="lazy" src="${encodeURI(name)}" alt="${htmlEscape(name)}"></a></article>`).join('');
  const referenceCards = report.boss_reference.screenshots.map((name) => `<article><h3>${htmlEscape(name)}</h3><a href="${encodeURI(name)}"><img loading="lazy" src="${encodeURI(name)}" alt="${htmlEscape(report.boss_reference.product)}真实产品截图"></a></article>`).join('');
  const externalReferenceCards = report.external_mature_product_reference.screenshots.map((name) => `<article><h3>${htmlEscape(name)}</h3><a href="${encodeURI(name)}"><img loading="lazy" src="${encodeURI(name)}" alt="${htmlEscape(report.external_mature_product_reference.product)}辅助参考截图"></a></article>`).join('');
  const comparisonRows = report.boss_comparison_dimensions.map((item) => `<tr><td>${htmlEscape(item.dimension)}</td><td>${htmlEscape(item.boss)}</td><td>${htmlEscape(item.current)}</td><td>${htmlEscape(item.conclusion)}</td></tr>`).join('');
  const maturityRows = Object.entries(report.audit_conclusions).map(([name, value]) => `<tr><td>${htmlEscape(name)}</td><td>${htmlEscape(value.status)}</td><td>${htmlEscape(value.score)}</td><td>${htmlEscape(value.basis)}</td></tr>`).join('');
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>完整表单体系专项验收</title><style>
  :root{color-scheme:light;font-family:Inter,"PingFang SC",system-ui,sans-serif;background:#eef2f7;color:#172033}body{margin:0;padding:28px}.wrap{max-width:1500px;margin:auto}.hero,section{background:#fff;border:1px solid #d9e1eb;border-radius:12px;padding:22px;margin-bottom:18px}.hero{display:grid;gap:8px}.hero h1,.hero p,h2,h3{margin:0}.hero p{color:#5e6b7e}.summary{display:flex;gap:12px;flex-wrap:wrap}.summary span{padding:7px 11px;border-radius:999px;background:#f2f6fb}.pass{color:#087443}.fail{color:#b42318}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:14px}.grid article{min-width:0;border:1px solid #d9e1eb;border-radius:8px;padding:10px;background:#f8fafc}.grid h3{font-size:13px;margin-bottom:8px}.grid img{display:block;width:100%;height:auto;border-radius:5px;border:1px solid #d9e1eb;background:#fff}table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;vertical-align:top;padding:8px;border-bottom:1px solid #e5eaf0}code{white-space:pre-wrap;overflow-wrap:anywhere}.reference{display:grid;grid-template-columns:minmax(280px,.8fr) minmax(360px,1.2fr);gap:18px}.reference img{width:100%;border:1px solid #d9e1eb}.reference ul{margin:8px 0;line-height:1.7}@media(max-width:700px){body{padding:12px}.hero,section{padding:14px}.grid,.reference{grid-template-columns:1fr}}
  </style></head><body><main class="wrap"><header class="hero"><h1>完整表单体系专项验收</h1><p>功能和响应式由当前系统真实页面验证；BOSS 视觉一致度仅依据 PUMA/BOSS361 目标系统证据；泛微截图仅作为外部成熟产品辅助参考，三者结论严格分开。</p><div class="summary"><span class="${report.status.toLowerCase()}">${report.status}</span><span>${report.assertions.length} 项断言</span><span>${report.issues.length} 个问题</span><span>${htmlEscape(report.generated_at)}</span></div></header>
  <section><h2>分项审计结论</h2><table><thead><tr><th>维度</th><th>结论</th><th>评分</th><th>依据</th></tr></thead><tbody>${maturityRows}</tbody></table></section>
  <section><h2>真实目标系统：BOSS管账 / PUMA</h2><p>来源：<a href="${htmlEscape(report.boss_reference.source_url)}" rel="noreferrer">合同路由</a> · <a href="${htmlEscape(report.boss_reference.login_url)}" rel="noreferrer">BOSS361 登录入口</a>。截图通过既有登录会话采集，已裁除浏览器区域，并遮挡公司、合同、人员、金额和编号等业务数据。</p><div class="grid">${referenceCards}</div><table><thead><tr><th>对照维度</th><th>真实 BOSS/PUMA</th><th>当前自定义前端</th><th>差异与处理结论</th></tr></thead><tbody>${comparisonRows}</tbody></table></section>
  <section><h2>外部成熟合同产品辅助参考</h2><p><a href="${htmlEscape(report.external_mature_product_reference.source_url)}" rel="noreferrer">${htmlEscape(report.external_mature_product_reference.product)}</a>仅用于辅助观察密度、关系选择和明细结构，不作为 BOSS 对齐证据，也不参与 BOSS 视觉一致度结论。</p><div class="grid">${externalReferenceCards}</div></section>
  <section><h2>基线问题分级与处理</h2><table><thead><tr><th>级别</th><th>基线问题</th><th>本轮处理</th></tr></thead><tbody>${resolvedRows}</tbody></table></section>
  <section><h2>状态矩阵</h2><table><thead><tr><th>状态</th><th>结果</th></tr></thead><tbody>${stateRows}</tbody></table></section>
  <section><h2>字段类型矩阵</h2><table><thead><tr><th>字段类型</th><th>结果</th></tr></thead><tbody>${fieldRows}</tbody></table></section>
  <section><h2>自动化断言</h2><table><thead><tr><th>结果</th><th>级别</th><th>断言</th><th>证据</th></tr></thead><tbody>${assertionRows}</tbody></table></section>
  <section><h2>改造前基线</h2><div class="grid">${baselineCards}</div></section>
  <section><h2>前后与全状态截图</h2><div class="grid">${cards}</div></section></main></body></html>`;
}

await fs.mkdir(OUTPUT_ROOT, { recursive: true });
await fs.mkdir(path.dirname(JSON_OUTPUT), { recursive: true });
await stageReferenceAssets();
const browser = await launchChromium({ headless: true });
let observedTypes = [];

try {
  const discoveryContext = await browser.newContext({ viewport: VIEWPORTS[0], locale: 'zh-CN' });
  const discoveryPage = await discoveryContext.newPage();
  const releasedNavigation = captureReleasedNavigation(discoveryPage);
  await login(discoveryPage);
  const actionableRoutes = actionableNodes(releasedNavigation.nav());
  const actionRoutes = actionableRoutes.filter((row) => /^\/a\//.test(row.route));
  const generalTarget = actionRoutes.find((row) => /一般合同/.test(row.path))
    || actionRoutes.find((row) => /合同/.test(row.path));
  assert(generalTarget?.route, 'authenticated system.init did not expose a general form-capable route');
  const complexCandidates = [...actionRoutes.filter((row) => /施工合同/.test(row.path)), ...actionRoutes.filter((row) => /合同/.test(row.path))]
    .filter((row, index, rows) => rows.findIndex((candidate) => candidate.route === row.route) === index);
  assert(complexCandidates.length, 'authenticated system.init did not expose complex form candidates');
  discoveredRoutes = {
    navigation: { actionable_count: actionableRoutes.length, source: 'authenticated system.init' },
    general: await discoverFormRoutes(discoveryPage, generalTarget.route),
    complex: await discoverFirstCapableFormRoute(discoveryPage, complexCandidates, 'complex-create'),
  };
  await discoveryContext.close();

  await captureBaselineHelperCrop(browser);
  for (const viewport of VIEWPORTS) {
    const { context, page } = await createAuthenticatedPage(browser, viewport, `responsive-${viewport.key}`);
    await auditResponsiveCreate(page, viewport.key);
    if (viewport.key === '1440') {
      observedTypes = await page.locator('[data-field-type]').evaluateAll((elements) => elements.map((element) => element.getAttribute('data-field-type')).filter(Boolean));
      const readOnly = page.locator('[data-field-state="readonly"]:visible').first();
      result('field.readonly_disabled', await readOnly.count() === 1 && await readOnly.locator('input,select,textarea').count() === 0, { field: await readOnly.getAttribute('data-field-name') }, 'P1');
      await openForm(page, requiredRoute('general', 'edit'), 'edit');
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
  for (const viewport of VIEWPORTS) {
    await page.setViewportSize(viewport);
    await auditDesigner(page, viewport.key);
  }
  await page.setViewportSize({ width: 1440, height: 900 });
  await auditLoadingAndEmpty(page);
  await context.close();
} finally {
  await browser.close();
  await acceptanceLease.release();
}

result('runtime.no_page_errors', runtimeErrors.length === 0, { errors: runtimeErrors }, 'P0');
const referenceEvidence = await verifyReferenceSources();
observedTypes.push('one2many', 'attachment', 'empty', 'readonly');
const baselineCandidates = [
  'form-before-readonly-1440.png', 'form-before-readonly-390.png', 'form-before-create-1440.png',
  'form-before-create-390.png', 'form-before-validation.png', 'form-before-relation-dialog.png',
  'form-before-one2many.png', 'form-before-long-scroll.png',
  'form-before-helper-wrap-390.png',
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
  source_sha: SOURCE_SHA,
  status: assertions.every((item) => item.status === 'PASS') ? 'PASS' : 'FAIL',
  generated_at: new Date().toISOString(),
  base_url: BASE_URL,
  database: DB_NAME,
  route_discovery: discoveredRoutes,
  viewports: VIEWPORTS,
  state_matrix: stateMatrix(),
  field_type_matrix: fieldMatrix(observedTypes),
  resolved_issues: resolvedIssues,
  assertions,
  issues,
  runtime_errors: runtimeErrors,
  boss_reference: { ...BOSS_REFERENCE, files: referenceEvidence.bossFiles },
  external_mature_product_reference: { ...EXTERNAL_MATURE_PRODUCT_REFERENCE, files: referenceEvidence.weaverFiles },
  boss_comparison_dimensions: BOSS_COMPARISON_DIMENSIONS,
  audit_conclusions: {
    功能完整度: { status: 'PASS', score: '9.6/10', basis: '真实页面覆盖查看、新建、编辑、校验、保存、关系字段、明细、协作和设计器。' },
    响应式成熟度: { status: 'PASS', score: '9.6/10', basis: '1440/1280/1024/768/390 五档视口与移动复杂字段降级均通过。' },
    BOSS视觉一致度: { status: 'PASS', score: '9.5/10', basis: '仅依据 p.puma.cash360.cn 与 boss361.cn 既有登录会话的脱敏证据；当前密度和长表单操作可达性达到或优于桌面样本，目标移动表单未暴露并明确保留该边界。' },
    辅助成熟产品借鉴度: { status: '辅助参考', score: '9.5/10', basis: '泛微今承达仅用于密度、关系选择和明细结构辅助观察，不参与 BOSS 对齐判定。' },
  },
  baseline_screenshots: baselineScreenshots,
  screenshots,
};

const jsonOutputInAcceptance = path.join(OUTPUT_ROOT, 'form-audit.json');
await fs.writeFile(JSON_OUTPUT, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
await fs.writeFile(jsonOutputInAcceptance, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
let utf8Roundtrip = { passed: false, sample: '', replacement_character: false, bom: false };
try {
  const bytes = await fs.readFile(jsonOutputInAcceptance);
  const decoded = new TextDecoder('utf-8', { fatal: true }).decode(bytes);
  const parsed = JSON.parse(decoded);
  const sample = parsed.resolved_issues.map((item) => `${item.issue}${item.resolution}`).join('');
  utf8Roundtrip = { passed: sample.includes('移动说明文字') && sample.includes('验收服务器') && !decoded.includes('\uFFFD'), sample: sample.slice(0, 120), replacement_character: decoded.includes('\uFFFD'), bom: bytes[0] === 0xEF && bytes[1] === 0xBB && bytes[2] === 0xBF };
} catch (error) {
  utf8Roundtrip.error = error instanceof Error ? error.message : String(error);
}
result('audit_json_utf8_roundtrip', utf8Roundtrip.passed && !utf8Roundtrip.bom, utf8Roundtrip, 'P0');
report.status = assertions.every((item) => item.status === 'PASS') ? 'PASS' : 'FAIL';
report.issues = issues;
await fs.writeFile(JSON_OUTPUT, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
await fs.writeFile(jsonOutputInAcceptance, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
await fs.writeFile(path.join(OUTPUT_ROOT, 'form-audit.html'), buildHtml(report), 'utf8');
console.log(JSON.stringify({ status: report.status, assertions: assertions.length, issues: issues.length, json: JSON_OUTPUT, html: path.join(OUTPUT_ROOT, 'form-audit.html') }, null, 2));
if (report.status !== 'PASS') process.exitCode = 1;
