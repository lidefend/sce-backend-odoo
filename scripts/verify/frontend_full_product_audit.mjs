#!/usr/bin/env node

import fs from 'node:fs/promises';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { launchAcceptanceChromium } from './playwright_runtime.mjs';
import { redactedEnvironmentEvidence, resolveAcceptanceEnvironment, verifyServedIdentity } from './lib/frontend_acceptance_environment.mjs';
import { acquireAcceptanceLease } from './lib/frontend_acceptance_lease.mjs';

const acceptance = resolveAcceptanceEnvironment({ tool: 'full-product-audit', env: { ...process.env, SC_ACCEPTANCE_FRONTEND_URL: process.env.SC_FULL_PRODUCT_URL || process.env.SC_ACCEPTANCE_FRONTEND_URL, SC_ACCEPTANCE_DATABASE: process.env.SC_FULL_PRODUCT_DB || process.env.SC_ACCEPTANCE_DATABASE } });
const BASE_URL = acceptance.baseUrl;
const DB_NAME = acceptance.database;
const PASSWORD = process.env.SC_FULL_PRODUCT_PASSWORD || acceptance.password || process.env.SC_ACCEPTANCE_FIXTURE_PASSWORD || '';
const OUTPUT_ROOT = path.resolve(process.env.SC_FULL_PRODUCT_OUTPUT || acceptance.runArtifactRoot);
const JSON_OUTPUT = path.resolve(process.env.SC_FULL_PRODUCT_JSON || path.join(OUTPUT_ROOT, 'full-product-audit.json'));
const FORM_AUDIT_INPUT = path.resolve(process.env.SC_FORM_AUDIT_JSON || path.join(OUTPUT_ROOT, 'form-audit.json'));
const SOURCE_SHA = process.env.SC_ACCEPTANCE_SHA || execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
if (!PASSWORD) throw new Error('SC_FULL_PRODUCT_PASSWORD or SC_ACCEPTANCE_FIXTURE_PASSWORD is required');
const ROLE_BINDINGS = ['finance', 'project_member', 'project_manager', 'owner'].map((role) => ({ role, login: String(acceptance.roleBindings[role] || '') }));
if (ROLE_BINDINGS.some((binding) => !binding.login)) throw new Error(`profile ${acceptance.profile} requires finance/project_member/project_manager/owner role bindings`);
const PROJECT_MANAGER_LOGIN = ROLE_BINDINGS.find((binding) => binding.role === 'project_manager').login;
const SMOKE_VIEWPORTS = [
  { key: '1440', width: 1440, height: 900 },
  { key: '390', width: 390, height: 844 },
];
const DEEP_VIEWPORTS = [
  ...SMOKE_VIEWPORTS.slice(0, 1),
  { key: '1280', width: 1280, height: 800 },
  { key: '1024', width: 1024, height: 768 },
  { key: '768', width: 768, height: 1024 },
  ...SMOKE_VIEWPORTS.slice(1),
];
const REQUIRED_REPRESENTATIVES = [
  { key: 'home', label: '首页', kind: 'shortcut', route: '/' },
  { key: 'my-work', label: '我的工作/待办', kind: 'shortcut', route: '/my-work' },
  { key: 'project-ledger', label: '项目台账', pattern: /项目台账/ },
  { key: 'general-contract', label: '一般合同', pattern: /一般合同/ },
  { key: 'construction-contract', label: '施工合同', pattern: /施工合同/ },
  { key: 'construction-diary', label: '施工日志', pattern: /施工日志/ },
  { key: 'plan-progress', label: '计划进度', pattern: /计划管理|计划进度|计划汇报/ },
];
const REQUIRED_FORM_EVIDENCE = {
  'readonly form': ['readonly.1440.no_horizontal_overflow', 'visible_text_not_clipped.390.readonly'],
  'create/edit form': ['create.1440.no_horizontal_overflow', 'edit.dirty_state'],
  'relation dialog': ['relation.1440.dialog_contained', 'relation.390.mobile_result_card'],
  one2many: ['one2many.1440.available', 'one2many.390.card_degradation', 'one2many_actions_reachable'],
  collaboration: ['collaboration.attachment_and_messages'],
  designer: ['designer.three_region_workspace', 'designer.field_selection'],
  loading: ['loading.explicit_state'],
  empty: ['empty_record.explicit_state'],
};
const FAILURE_TEXT = /无权访问|权限不足|访问被拒绝|初始化失败|加载失败|暂无导航数据|登录失败|重新登录/i;
const LOADING_TEXT = /正在加载页面|正在加载场景|正在加载列表|正在初始化|正在加载业务数据/;
const MOJIBAKE = /\uFFFD|Ã.|Â.|æ[\x80-\xBF]|ç[\x80-\xBF]|锟斤拷|鐧诲綍|娴忚/g;

const routeRows = [];
const screenshots = [];
const runtimeIssues = [];
const uncovered = [];

await fs.mkdir(OUTPUT_ROOT, { recursive: true });
const acceptanceLease = await acquireAcceptanceLease({ environment: acceptance, mode: 'shared-read', owner: { tool: 'full-product-audit', profile: acceptance.profile, source_sha: SOURCE_SHA } });

function nodeMeta(node) {
  return node?.meta && typeof node.meta === 'object' ? node.meta : {};
}

function resolveNodeRoute(node) {
  const meta = nodeMeta(node);
  const actionId = Number(node?.action_id || node?.actionId || node?.action || meta.action_id || meta.actionId || 0);
  const menuId = Number(node?.menu_id || node?.menuId || meta.menu_id || meta.menuId || 0);
  const route = String(node?.route || meta.route || '');
  if (route) {
    if (/^\/a\/\d+(?:\?|$)/.test(route) && menuId > 0 && !/[?&]menu_id=/.test(route)) {
      return `${route}${route.includes('?') ? '&' : '?'}menu_id=${menuId}`;
    }
    return route;
  }
  const scene = node?.scene_key || node?.sceneKey || meta.scene_key || meta.sceneKey;
  if (scene) return `/s/${encodeURIComponent(String(scene))}`;
  if (actionId > 0) return `/a/${actionId}${menuId > 0 ? `?menu_id=${menuId}` : ''}`;
  if (menuId > 0) return `/m/${menuId}`;
  return '';
}

function flattenLeaves(nodes, ancestors = []) {
  const rows = [];
  for (const node of Array.isArray(nodes) ? nodes : []) {
    const meta = nodeMeta(node);
    const label = String(node?.title || node?.label || node?.name || '').trim();
    const pathLabels = [...ancestors, label].filter(Boolean);
    const children = Array.isArray(node?.children) ? node.children : [];
    if (children.length) {
      rows.push(...flattenLeaves(children, pathLabels));
      continue;
    }
    rows.push({
      label,
      navigation_path: pathLabels.join(' / '),
      route: resolveNodeRoute(node),
      menu_id: Number(node?.menu_id || node?.menuId || meta.menu_id || meta.menuId || 0),
      action_id: Number(node?.action_id || node?.actionId || node?.action || meta.action_id || meta.actionId || 0),
      menu_xmlid: String(node?.xml_id || node?.xmlid || node?.menu_xmlid || meta.menu_xmlid || ''),
      action_xmlid: String(node?.action_xmlid || meta.action_xmlid || ''),
      model: String(node?.model || meta.model || meta.res_model || ''),
    });
  }
  return rows;
}

function navigationFromPayload(payload) {
  const values = [payload, payload?.result, payload?.data, payload?.result?.data];
  for (const value of values) {
    for (const key of ['release_navigation_v1', 'delivery_engine_v1']) {
      if (Array.isArray(value?.[key]?.nav)) return value[key].nav;
      if (Array.isArray(value?.[key])) return value[key];
    }
  }
  return null;
}

function attachRuntimeCapture(page) {
  const capture = { navigation: null, console: [], page: [], http: [], scope: 'login' };
  capture.reset = (scope) => {
    capture.scope = scope;
    capture.console = [];
    capture.page = [];
    capture.http = [];
  };
  page.on('console', (message) => {
    if (message.type() === 'error' && !/favicon|ResizeObserver|Failed to load resource/i.test(message.text())) {
      capture.console.push(message.text());
    }
  });
  page.on('pageerror', (error) => capture.page.push(error.message));
  page.on('response', async (response) => {
    if (response.status() >= 500) capture.http.push(`${response.status()} ${response.url()}`);
    if (!response.url().includes('/api/v1/intent')) return;
    try {
      const payload = await response.json();
      const navigation = navigationFromPayload(payload);
      if (navigation) capture.navigation = navigation;
    } catch { /* non-json response is handled by the page checks */ }
  });
  return capture;
}

async function login(page, loginName, capture) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  await page.locator('#login-username, input[autocomplete="username"]').first().fill(loginName);
  await page.locator('#login-password, input[autocomplete="current-password"]').first().fill(PASSWORD);
  const database = page.locator('input').nth(2);
  if (await database.isEnabled().catch(() => false)) await database.fill(DB_NAME);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45_000 });
  await page.locator('.layout-shell').waitFor({ state: 'visible', timeout: 45_000 });
  await page.waitForFunction(() => !/正在初始化|正在加载导航/.test(document.body.innerText || ''), null, { timeout: 45_000 });
  if (!Array.isArray(capture.navigation)) throw new Error(`权威导航缺失：${loginName}`);
}

async function visibleTextClipping(page) {
  return page.evaluate(() => {
    const failures = [];
    const ignored = new Set(['SCRIPT', 'STYLE', 'SVG', 'PATH', 'OPTION', 'NOSCRIPT']);
    const visible = (element) => {
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return style.display !== 'none' && style.visibility !== 'hidden' && Number(style.opacity) !== 0 && rect.width > 2 && rect.height > 2;
    };
    const selector = (element) => element.id ? `#${CSS.escape(element.id)}` : `${element.tagName.toLowerCase()}${Array.from(element.classList).slice(0, 2).map((name) => `.${CSS.escape(name)}`).join('')}`;
    for (const element of document.body.querySelectorAll('*')) {
      if (ignored.has(element.tagName) || !visible(element)) continue;
      const ownText = Array.from(element.childNodes).some((node) => node.nodeType === Node.TEXT_NODE && String(node.textContent || '').trim());
      const control = element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement || element instanceof HTMLButtonElement;
      if (!ownText && !control) continue;
      const text = String(control ? element.value || element.textContent || element.getAttribute('aria-label') || '' : element.textContent || '').trim().replace(/\s+/g, ' ');
      if (!text) continue;
      const style = getComputedStyle(element);
      const intentionalScroller = ['auto', 'scroll'].includes(style.overflowX);
      const semanticContainer = element.closest('[title]:not([title=""]), [aria-label]:not([aria-label=""])');
      const explainedEllipsis = style.textOverflow === 'ellipsis' && Boolean(semanticContainer);
      const ownClip = element.scrollWidth > element.clientWidth + 1 && !intentionalScroller && !explainedEllipsis && ['hidden', 'clip'].includes(style.overflowX);
      let ancestorClip = '';
      const rect = element.getBoundingClientRect();
      for (let parent = element.parentElement; parent && parent !== document.body; parent = parent.parentElement) {
        const parentStyle = getComputedStyle(parent);
        if (['auto', 'scroll'].includes(parentStyle.overflowX)) break;
        if (!['hidden', 'clip'].includes(parentStyle.overflowX)) continue;
        const parentRect = parent.getBoundingClientRect();
        if (rect.left < parentRect.left - 1 || rect.right > parentRect.right + 1) ancestorClip = selector(parent);
        break;
      }
      if (ownClip || ancestorClip) failures.push({ selector: selector(element), text: text.slice(0, 70), client_width: element.clientWidth, scroll_width: element.scrollWidth, ancestor: ancestorClip });
    }
    return failures.slice(0, 20);
  });
}

async function inspectRoute(page, capture, role, viewport, leaf, options = {}) {
  const scope = `${role}:${viewport.key}:${leaf.navigation_path}`;
  capture.reset(scope);
  let navigationError = '';
  const started = Date.now();
  try {
    await page.goto(`${BASE_URL}${leaf.route}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
    await page.locator('.layout-shell').waitFor({ state: 'visible', timeout: 45_000 });
    await page.waitForFunction(({ source, allowWorkspace }) => {
      const shell = document.querySelector('.layout-shell');
      const title = String(shell?.getAttribute('data-page-identity-title') || '');
      const main = document.querySelector('#main-content');
      return Boolean(title)
        && !/加载中|正在加载/.test(title)
        && !new RegExp(source).test(document.body.innerText || '')
        && (allowWorkspace ? Boolean(main?.children.length) : Boolean(document.querySelector('#main-content .page, #main-content [data-product-page-mode]')));
    }, { source: LOADING_TEXT.source, allowWorkspace: leaf.route === '/' || leaf.route === '/my-work' }, { timeout: 45_000 });
    await page.waitForTimeout(120);
    await page.evaluate(() => {
      window.scrollTo(0, 0);
      const main = document.querySelector('#main-content');
      if (main) main.scrollTop = 0;
    });
    await page.waitForTimeout(40);
  } catch (error) {
    navigationError = error.message;
  }
  const body = await page.locator('body').innerText().catch(() => '');
  const mainText = await page.locator('#main-content').innerText().catch(() => '');
  const shellTitle = String(await page.locator('.layout-shell').getAttribute('data-page-identity-title').catch(() => '') || '').trim();
  const documentTitle = await page.title().catch(() => '');
  const mode = String(await page.locator('[data-product-page-mode]').first().getAttribute('data-product-page-mode').catch(() => '') || 'workspace');
  const dimensions = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
  const clipping = await visibleTextClipping(page).catch(() => [{ selector: 'audit', text: '裁切检查执行失败' }]);
  const mojibake = body.match(MOJIBAKE) || [];
  const sidebarWasClosed = await page.locator('#primary-sidebar').count() === 0;
  if (sidebarWasClosed && viewport.width <= 768) {
    await page.locator('.sidebar-toggle').click();
    await page.locator('#primary-sidebar').waitFor({ state: 'visible', timeout: 5_000 });
  }
  const iconMetrics = await page.locator('.primary-navigation .node').evaluateAll((nodes) => ({ nodes: nodes.length, missing: nodes.filter((node) => !node.querySelector('.node-icon svg.sc-icon')).map((node) => node.textContent?.trim().slice(0, 50)) })).catch(() => ({ nodes: 0, missing: ['navigation missing'] }));
  const activeMenu = await page.locator('.primary-navigation .node.active').allInnerTexts().catch(() => []);
  if (sidebarWasClosed && viewport.width <= 768) {
    await page.locator('.mobile-sidebar-close').click();
    await page.locator('#primary-sidebar').waitFor({ state: 'detached', timeout: 5_000 });
  }
  const activeTab = await page.locator('.activity-tab.active').allInnerTexts().catch(() => []);
  const visibleActions = await page.locator('#main-content button:visible:not(:disabled), #main-content a:visible[href]').count().catch(() => 0);
  const mobileToolbar = await page.evaluate(() => {
    if (document.documentElement.clientWidth > 520) return { applicable: false };
    const toolbar = document.querySelector('.product-list-header__tools .action-toolbar:not(.action-toolbar--without-view)');
    const search = toolbar?.querySelector('.native-search');
    if (!(toolbar instanceof HTMLElement) || !(search instanceof HTMLElement)) return { applicable: false };
    const visible = (element) => {
      if (!(element instanceof HTMLElement)) return false;
      const rect = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      return rect.width > 1 && rect.height > 1 && style.display !== 'none' && style.visibility !== 'hidden';
    };
    const controls = Array.from(toolbar.querySelectorAll('input, button, select')).filter((element) => (
      visible(element) && !element.closest('.search-dropdown, .list-surface-column-menu, .toolbar-overflow-menu')
    ));
    const rects = controls.map((element) => {
      const rect = element.getBoundingClientRect();
      return { tag: element.tagName.toLowerCase(), left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom, width: rect.width, height: rect.height };
    });
    const rowCenters = [];
    for (const rect of rects) {
      const center = rect.top + rect.height / 2;
      if (!rowCenters.some((value) => Math.abs(value - center) <= 6)) rowCenters.push(center);
    }
    const searchInput = search.querySelector('input[type="search"]');
    const searchInputRect = visible(searchInput) ? searchInput.getBoundingClientRect() : null;
    const toolbarRect = toolbar.getBoundingClientRect();
    const overlaps = rects.some((left, index) => rects.slice(index + 1).some((right) => (
      Math.min(left.right, right.right) - Math.max(left.left, right.left) > 1
      && Math.min(left.bottom, right.bottom) - Math.max(left.top, right.top) > 1
    )));
    return {
      applicable: true,
      search_width: Math.round(search.getBoundingClientRect().width),
      search_input_width: Math.round(searchInputRect?.width || 0),
      visual_row_count: rowCenters.length,
      toolbar_client_width: toolbar.clientWidth,
      toolbar_scroll_width: toolbar.scrollWidth,
      controls_in_viewport: rects.every((rect) => rect.left >= -1 && rect.right <= document.documentElement.clientWidth + 1),
      controls_not_overlapping: !overlaps,
      touch_targets: rects.filter((rect) => rect.tag === 'button').every((rect) => rect.width >= 44 && rect.height >= 44),
      toolbar_in_viewport: toolbarRect.top >= -1 && toolbarRect.bottom <= window.innerHeight + 1,
    };
  }).catch(() => ({ applicable: false }));
  const expectedPath = new URL(`${BASE_URL}${leaf.route}`).pathname;
  const actualUrl = new URL(page.url());
  const checks = {
    loaded: !navigationError && actualUrl.pathname === expectedPath,
    no_runtime_errors: capture.console.length === 0 && capture.page.length === 0 && capture.http.length === 0,
    not_blank: mainText.trim().length >= 8,
    no_horizontal_overflow: dimensions.scroll <= dimensions.viewport + 1,
    visible_text_not_clipped: clipping.length === 0,
    utf8_text: mojibake.length === 0,
    navigation_icons_complete: iconMetrics.nodes > 0 && iconMetrics.missing.length === 0,
    identity_present: Boolean(shellTitle) && documentTitle === `${shellTitle} - 智能施工企业管理平台`,
    active_menu_correct: leaf.menu_id <= 0 || activeMenu.some((text) => text.includes(leaf.label)),
    active_tab_correct: leaf.route === '/' ? activeTab.length === 0 : viewport.width < 760 || activeTab.length === 1,
    primary_action_reachable: visibleActions > 0 || ['workspace', 'home'].includes(mode),
    mobile_list_toolbar_usable: !mobileToolbar.applicable || (
      mobileToolbar.search_input_width >= 96
      && mobileToolbar.visual_row_count === 1
      && mobileToolbar.toolbar_scroll_width <= mobileToolbar.toolbar_client_width + 1
      && mobileToolbar.controls_in_viewport
      && mobileToolbar.controls_not_overlapping
      && mobileToolbar.touch_targets
      && mobileToolbar.toolbar_in_viewport
    ),
    no_auth_or_permission_redirect: !actualUrl.pathname.includes('/login') && !FAILURE_TEXT.test(mainText),
  };
  const failures = Object.entries(checks).filter(([, passed]) => !passed).map(([name]) => name);
  const row = {
    role,
    viewport: `${viewport.width}x${viewport.height}`,
    ...leaf,
    final_url: page.url(),
    page_type: leaf.route === '/' ? 'role home' : leaf.route === '/my-work' ? 'my work' : mode,
    title: shellTitle,
    checks,
    result: failures.length ? 'FAIL' : 'PASS',
    failures,
    diagnostics: { navigation_error: navigationError, console_errors: capture.console, page_errors: capture.page, http_errors: capture.http, clipping, mojibake: mojibake.slice(0, 10), icon_metrics: iconMetrics, active_menu: activeMenu, active_tab: activeTab, visible_actions: visibleActions, mobile_toolbar: mobileToolbar, dimensions },
    load_ms: Date.now() - started,
  };
  if (failures.length || options.capture) {
    const safeName = `${options.prefix || 'route'}-${role}-${leaf.menu_id || leaf.label.replace(/[^a-z0-9]+/gi, '-')}-${viewport.key}.png`;
    await page.screenshot({ path: path.join(OUTPUT_ROOT, safeName), fullPage: failures.length > 0, animations: 'disabled' }).catch(() => {});
    row.screenshot = safeName;
    screenshots.push(safeName);
  }
  if (failures.length) runtimeIssues.push({ severity: failures.some((item) => ['loaded', 'no_runtime_errors', 'not_blank', 'no_auth_or_permission_redirect'].includes(item)) ? 'P0' : 'P1', route: leaf.route, role, viewport: viewport.key, failures, screenshot: row.screenshot });
  return row;
}

function chooseRepresentatives(leaves) {
  return REQUIRED_REPRESENTATIVES.map((required) => {
    if (required.route) return { ...required, leaf: { label: required.label, navigation_path: required.label, route: required.route, menu_id: 0, action_id: 0, menu_xmlid: `shortcut.${required.key}`, action_xmlid: '', model: '' } };
    const candidates = leaves.filter((leaf) => required.pattern.test(`${leaf.label} ${leaf.navigation_path}`));
    const preferred = candidates.find((leaf) => leaf.role === 'project_manager') || candidates[0];
    return { ...required, leaf: preferred || null };
  });
}

function percent(value, total) {
  return total ? Number(((value / total) * 100).toFixed(2)) : 0;
}

function htmlEscape(value) {
  return String(value ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
}

function buildHtml(report) {
  const coverageRows = Object.entries(report.coverage).map(([key, value]) => `<tr><td>${htmlEscape(key)}</td><td>${value.passed}/${value.total}</td><td>${value.rate}%</td><td class="${value.rate === 100 ? 'pass' : 'fail'}">${value.rate === 100 ? 'PASS' : 'FAIL'}</td></tr>`).join('');
  const routeFailureRows = report.failures.length ? report.failures.map((item) => `<tr><td>${htmlEscape(item.severity)}</td><td><code>${htmlEscape(item.route)}</code></td><td>${htmlEscape(item.role)} / ${htmlEscape(item.viewport)}</td><td>${htmlEscape(item.failures.join(', '))}</td><td>${item.screenshot ? `<a href="${encodeURI(item.screenshot)}">截图</a>` : '-'}</td></tr>`).join('') : '<tr><td colspan="5" class="pass">无 P0/P1 问题</td></tr>';
  const representativeRows = report.representatives.map((item) => `<tr><td>${htmlEscape(item.label)}</td><td>${htmlEscape(item.route || '-')}</td><td>${item.viewports_passed}/${item.viewports_total}</td><td class="${item.status === 'PASS' ? 'pass' : 'fail'}">${item.status}</td></tr>`).join('');
  const templateRows = report.templates.map((item) => `<tr><td>${htmlEscape(item.template)}</td><td>${htmlEscape(item.source)}</td><td>${htmlEscape(item.evidence.join(', '))}</td><td class="${item.status === 'PASS' ? 'pass' : 'fail'}">${item.status}</td></tr>`).join('');
  const cards = report.screenshots.map((name) => `<article><h3>${htmlEscape(name)}</h3><a href="${encodeURI(name)}"><img loading="lazy" src="${encodeURI(name)}" alt="${htmlEscape(name)}"></a></article>`).join('');
  const uncoveredRows = report.uncovered.length ? report.uncovered.map((item) => `<tr><td>${htmlEscape(item.surface)}</td><td>${htmlEscape(item.reason)}</td></tr>`).join('') : '<tr><td colspan="2" class="pass">无未覆盖页面</td></tr>';
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>全产品前端覆盖验收</title><style>
  :root{color-scheme:light;font-family:Inter,"PingFang SC",system-ui,sans-serif;background:#eef2f7;color:#172033}body{margin:0;padding:28px}.wrap{max-width:1500px;margin:auto}.hero,section{background:#fff;border:1px solid #d9e1eb;border-radius:12px;padding:22px;margin-bottom:18px}.hero{display:grid;gap:8px}.hero h1,.hero p,h2,h3{margin:0}.hero p{color:#5e6b7e}.summary{display:flex;gap:12px;flex-wrap:wrap}.summary span{padding:7px 11px;border-radius:999px;background:#f2f6fb}.pass{color:#087443}.fail{color:#b42318}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px}.grid article{min-width:0;border:1px solid #d9e1eb;border-radius:8px;padding:10px;background:#f8fafc}.grid h3{font-size:13px;margin-bottom:8px}.grid img{display:block;width:100%;height:auto;border-radius:5px;border:1px solid #d9e1eb;background:#fff}table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;vertical-align:top;padding:8px;border-bottom:1px solid #e5eaf0}code{white-space:pre-wrap;overflow-wrap:anywhere}@media(max-width:700px){body{padding:12px}.hero,section{padding:14px}}
  </style></head><body><main class="wrap"><header class="hero"><h1>全产品前端覆盖验收</h1><p>权威菜单自动发现；全部叶子路由执行 1440×900 与 390×844 只读冒烟；代表业务页面执行五档视口深检。复杂表单模板复用同一提交下的真实合同专项证据。</p><div class="summary"><span class="${report.status === 'PASS' ? 'pass' : 'fail'}">${report.status}</span><span>${report.route_rows.length} 次路由检查</span><span>${report.failures.length} 个 P0/P1 问题</span><span>${htmlEscape(report.generated_at)}</span></div></header>
  <section><h2>覆盖率</h2><table><thead><tr><th>维度</th><th>通过/总数</th><th>覆盖率</th><th>结论</th></tr></thead><tbody>${coverageRows}</tbody></table></section>
  <section><h2>代表业务五视口</h2><table><thead><tr><th>业务页面</th><th>自动发现路由</th><th>通过视口</th><th>结论</th></tr></thead><tbody>${representativeRows}</tbody></table></section>
  <section><h2>页面模板</h2><table><thead><tr><th>模板</th><th>证据来源</th><th>断言</th><th>结论</th></tr></thead><tbody>${templateRows}</tbody></table></section>
  <section><h2>失败清单</h2><table><thead><tr><th>级别</th><th>路由</th><th>角色/视口</th><th>原因</th><th>证据</th></tr></thead><tbody>${routeFailureRows}</tbody></table></section>
  <section><h2>未覆盖页面及原因</h2><table><thead><tr><th>页面</th><th>原因</th></tr></thead><tbody>${uncoveredRows}</tbody></table></section>
  <section><h2>桌面/移动关键截图</h2><div class="grid">${cards}</div></section>
  </main></body></html>`;
}

async function loadFormTemplateEvidence() {
  try {
    const report = JSON.parse(await fs.readFile(FORM_AUDIT_INPUT, 'utf8'));
    const byId = new Map((report.assertions || []).map((item) => [item.id, item.status]));
    return Object.entries(REQUIRED_FORM_EVIDENCE).map(([template, evidence]) => ({
      template,
      source: '当前提交真实合同表单专项 form-audit.json',
      evidence,
      status: report.status === 'PASS' && evidence.every((id) => byId.get(id) === 'PASS') ? 'PASS' : 'FAIL',
    }));
  } catch (error) {
    return Object.entries(REQUIRED_FORM_EVIDENCE).map(([template, evidence]) => ({ template, source: `表单专项证据不可读：${error.message}`, evidence, status: 'FAIL' }));
  }
}

const servedIdentity = await verifyServedIdentity(acceptance, acceptance.provenance.expectedSha);
const browser = await launchAcceptanceChromium(acceptance, { headless: true });
const discovered = [];
try {
  for (const binding of ROLE_BINDINGS) {
    let roleLeaves = null;
    for (const viewport of SMOKE_VIEWPORTS) {
      const context = await browser.newContext({ viewport, locale: 'zh-CN' });
      const page = await context.newPage();
      const capture = attachRuntimeCapture(page);
      await login(page, binding.login, capture);
      const leaves = flattenLeaves(capture.navigation).map((leaf) => ({ ...leaf, role: binding.role, login: binding.login }));
      if (!roleLeaves) {
        roleLeaves = leaves;
        discovered.push(...leaves);
      } else {
        const expected = roleLeaves.map((leaf) => `${leaf.menu_xmlid}|${leaf.action_xmlid}|${leaf.model}`).sort();
        const actual = leaves.map((leaf) => `${leaf.menu_xmlid}|${leaf.action_xmlid}|${leaf.model}`).sort();
        if (JSON.stringify(expected) !== JSON.stringify(actual)) runtimeIssues.push({ severity: 'P0', route: 'navigation', role: binding.role, viewport: viewport.key, failures: ['desktop_mobile_navigation_mismatch'] });
      }
      for (const [index, leaf] of leaves.entries()) {
        process.stdout.write(`[full-product-audit] ${binding.role} ${viewport.key} ${index + 1}/${leaves.length}\r`);
        routeRows.push(await inspectRoute(page, capture, binding.role, viewport, leaf));
      }
      await context.close();
    }
  }

  const representatives = chooseRepresentatives(discovered);
  for (const representative of representatives.filter((item) => !item.leaf)) {
    uncovered.push({ surface: representative.label, reason: '当前角色权威导航中未发现匹配入口' });
  }
  for (const viewport of DEEP_VIEWPORTS) {
    const context = await browser.newContext({ viewport, locale: 'zh-CN' });
    const page = await context.newPage();
    const capture = attachRuntimeCapture(page);
    await login(page, PROJECT_MANAGER_LOGIN, capture);
    for (const representative of representatives.filter((item) => item.leaf)) {
      process.stdout.write(`[full-product-audit] representative ${viewport.key} ${representative.label}\r`);
      const existing = routeRows.find((row) => row.route === representative.leaf.route && row.viewport === `${viewport.width}x${viewport.height}` && (representative.leaf.role ? row.role === representative.leaf.role : true));
      if (existing) {
        if (!existing.screenshot) {
          const row = await inspectRoute(page, capture, representative.leaf.role || 'project_manager', viewport, representative.leaf, { capture: true, prefix: `representative-${representative.key}` });
          existing.screenshot = row.screenshot;
          if (row.result !== 'PASS') routeRows.push(row);
        }
        continue;
      }
      routeRows.push(await inspectRoute(page, capture, representative.leaf.role || 'project_manager', viewport, representative.leaf, { capture: true, prefix: `representative-${representative.key}` }));
    }
    await context.close();
  }

  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'zh-CN' });
  const page = await context.newPage();
  const capture = attachRuntimeCapture(page);
  await login(page, PROJECT_MANAGER_LOGIN, capture);
  const notFound = { label: '不存在页面', navigation_path: '错误/禁止态', route: '/__full_product_audit_not_found__', menu_id: 0, action_id: 0, menu_xmlid: 'audit.not_found', action_xmlid: '', model: '' };
  capture.reset('not-found');
  await page.goto(`${BASE_URL}${notFound.route}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  await page.locator('.layout-shell').waitFor({ state: 'visible', timeout: 45_000 });
  const notFoundText = await page.locator('#main-content').innerText().catch(() => '');
  const notFoundPass = /不存在|未找到|404/.test(notFoundText) && !page.url().includes('/login');
  if (!notFoundPass) runtimeIssues.push({ severity: 'P1', route: notFound.route, role: 'project_manager', viewport: '1440', failures: ['error_forbidden_template_missing'] });
  const notFoundScreenshot = 'template-error-forbidden-1440.png';
  await page.screenshot({ path: path.join(OUTPUT_ROOT, notFoundScreenshot), fullPage: false, animations: 'disabled' });
  screenshots.push(notFoundScreenshot);
  await context.close();
} finally {
  await browser.close();
  await acceptanceLease.release();
  process.stdout.write('\n');
}

const formTemplates = await loadFormTemplateEvidence();
const runtimeTemplates = [
  { template: 'role home', source: '本轮真实浏览器', evidence: ['/'], status: routeRows.some((row) => row.route === '/' && row.result === 'PASS') ? 'PASS' : 'FAIL' },
  { template: 'list', source: '本轮全路由与代表业务浏览器检查', evidence: ['data-product-page-mode=list'], status: routeRows.some((row) => row.page_type === 'list' && row.result === 'PASS') ? 'PASS' : 'FAIL' },
  { template: 'error/forbidden', source: '本轮只读不存在路由检查', evidence: ['/__full_product_audit_not_found__'], status: runtimeIssues.some((item) => item.failures.includes('error_forbidden_template_missing')) ? 'FAIL' : 'PASS' },
];
const templates = [...runtimeTemplates, ...formTemplates];
for (const template of templates.filter((item) => item.status !== 'PASS')) runtimeIssues.push({ severity: 'P1', route: 'template', role: 'all', viewport: 'all', failures: [`template_not_covered:${template.template}`] });

const smokeRows = routeRows.filter((row) => SMOKE_VIEWPORTS.some((viewport) => row.viewport === `${viewport.width}x${viewport.height}`) && row.menu_id > 0);
const menuKeys = [...new Set(discovered.map((leaf) => `${leaf.role}:${leaf.menu_xmlid || leaf.menu_id}`))];
const menuPassed = menuKeys.filter((key) => {
  const [role, identity] = key.split(':');
  const leaf = discovered.find((item) => item.role === role && String(item.menu_xmlid || item.menu_id) === identity);
  return leaf && SMOKE_VIEWPORTS.every((viewport) => smokeRows.some((row) => row.role === role && row.menu_id === leaf.menu_id && row.viewport === `${viewport.width}x${viewport.height}` && row.result === 'PASS'));
}).length;
const representatives = chooseRepresentatives(discovered).map((item) => {
  const rows = item.leaf ? DEEP_VIEWPORTS.map((viewport) => routeRows.find((row) => row.route === item.leaf.route && row.viewport === `${viewport.width}x${viewport.height}` && (!item.leaf.role || row.role === item.leaf.role))).filter(Boolean) : [];
  return { key: item.key, label: item.label, route: item.leaf?.route || '', viewports_passed: rows.filter((row) => row.result === 'PASS').length, viewports_total: DEEP_VIEWPORTS.length, status: rows.length === DEEP_VIEWPORTS.length && rows.every((row) => row.result === 'PASS') ? 'PASS' : 'FAIL' };
});
const coverage = {
  '菜单可访问路由': { passed: menuPassed, total: menuKeys.length, rate: percent(menuPassed, menuKeys.length) },
  '全路由双视口检查': { passed: smokeRows.filter((row) => row.result === 'PASS').length, total: smokeRows.length, rate: percent(smokeRows.filter((row) => row.result === 'PASS').length, smokeRows.length) },
  '页面模板': { passed: templates.filter((item) => item.status === 'PASS').length, total: templates.length, rate: percent(templates.filter((item) => item.status === 'PASS').length, templates.length) },
  '代表业务模块': { passed: representatives.filter((item) => item.status === 'PASS').length, total: representatives.length, rate: percent(representatives.filter((item) => item.status === 'PASS').length, representatives.length) },
};
const failures = runtimeIssues.filter((item) => ['P0', 'P1'].includes(item.severity));
const status = Object.values(coverage).every((item) => item.rate === 100) && failures.length === 0 ? 'PASS' : 'FAIL';
const report = {
  schema_version: 'frontend-full-product-audit/v1',
  generated_at: new Date().toISOString(),
  source_sha: SOURCE_SHA,
  status,
  baseline: '2ae5dd9ff99f54db66e80bf1e9855a3d59ee090e',
  environment: redactedEnvironmentEvidence(acceptance),
  served_identity: servedIdentity,
  discovery: { source: 'authenticated release_navigation_v1/delivery_engine_v1', roles: ROLE_BINDINGS, menu_leaves: discovered.length, smoke_viewports: SMOKE_VIEWPORTS, deep_viewports: DEEP_VIEWPORTS },
  coverage,
  representatives,
  templates,
  failures,
  uncovered,
  screenshots: [...new Set(screenshots)],
  route_rows: routeRows,
};
await fs.writeFile(JSON_OUTPUT, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
await fs.writeFile(path.join(OUTPUT_ROOT, 'full-product-audit.json'), `${JSON.stringify(report, null, 2)}\n`, 'utf8');
await fs.writeFile(path.join(OUTPUT_ROOT, 'full-product-audit.html'), buildHtml(report), 'utf8');
console.log(JSON.stringify({ status, routes: smokeRows.length, menu_leaves: menuKeys.length, templates: `${coverage['页面模板'].passed}/${coverage['页面模板'].total}`, representatives: `${coverage['代表业务模块'].passed}/${coverage['代表业务模块'].total}`, issues: failures.length, json: JSON_OUTPUT, html: path.join(OUTPUT_ROOT, 'full-product-audit.html') }, null, 2));
if (status !== 'PASS') process.exitCode = 2;
