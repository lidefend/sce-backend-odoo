#!/usr/bin/env node

import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { launchAcceptanceChromium } from './playwright_runtime.mjs';
import { captureReleasedNavigation } from './released_navigation_target.mjs';
import { redactedEnvironmentEvidence, resolveAcceptanceEnvironment, verifyServedIdentity } from './lib/frontend_acceptance_environment.mjs';
import { acquireAcceptanceLease } from './lib/frontend_acceptance_lease.mjs';

const acceptance = resolveAcceptanceEnvironment({ tool: 'geometry-scroll-audit' });
const BASE_URL = acceptance.baseUrl;
const DB_NAME = acceptance.database;
const LOGIN = process.env.E2E_LOGIN || acceptance.login || acceptance.roleBindings.project_manager || '';
const PASSWORD = process.env.E2E_PASSWORD || acceptance.password || process.env.SC_ACCEPTANCE_FIXTURE_PASSWORD || '';
const OUTPUT_DIR = path.resolve(process.env.GEOMETRY_AUDIT_OUTPUT || acceptance.runArtifactRoot);
const REPORT_JSON = path.resolve(process.env.GEOMETRY_AUDIT_JSON || path.join(OUTPUT_DIR, 'geometry-scroll-audit.json'));
const REPORT_HTML = path.resolve(process.env.GEOMETRY_AUDIT_HTML || path.join(OUTPUT_DIR, 'geometry-scroll-audit.html'));
const VIEWPORTS = [
  { key: '1440', width: 1440, height: 900 },
  { key: '1280', width: 1280, height: 800 },
  { key: '1024', width: 1024, height: 768 },
  { key: '768', width: 768, height: 1024 },
  { key: '390', width: 390, height: 844 },
];
const ZOOM_LEVELS = [80, 100, 125, 150];
const SOURCE_SHA = process.env.SC_ACCEPTANCE_SHA || execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();

assert(PASSWORD, 'E2E_PASSWORD or SC_ACCEPTANCE_FIXTURE_PASSWORD is required');
await fs.mkdir(OUTPUT_DIR, { recursive: true });
const acceptanceLease = await acquireAcceptanceLease({ environment: acceptance, mode: 'shared-read', owner: { tool: 'geometry-scroll-audit', profile: acceptance.profile, source_sha: SOURCE_SHA } });

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

async function login(page, navigation) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  await page.locator('#login-username, input[autocomplete="username"]').first().fill(LOGIN);
  await page.locator('#login-password, input[autocomplete="current-password"]').first().fill(PASSWORD);
  const database = page.locator('input').nth(2);
  if (await database.isEnabled().catch(() => false)) await database.fill(DB_NAME);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45_000 });
  await page.locator('.layout-shell').waitFor({ state: 'visible', timeout: 45_000 });
  await page.waitForFunction(() => !/正在初始化|正在加载导航/.test(document.body.innerText || ''), null, { timeout: 45_000 });
  assert(navigation.nav().length, 'authenticated system.init navigation was not captured');
}

async function inspectGeometry(page) {
  return page.evaluate(() => {
    const selectorFor = (element) => {
      if (element.id) return `#${CSS.escape(element.id)}`;
      const classes = Array.from(element.classList).slice(0, 3).map((name) => `.${CSS.escape(name)}`).join('');
      return `${element.tagName.toLowerCase()}${classes}`;
    };
    const visible = (element) => {
      const rect = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      return rect.width > 1 && rect.height > 1 && style.display !== 'none' && style.visibility !== 'hidden' && Number(style.opacity) !== 0;
    };
    const measure = (element) => {
      if (!element || !visible(element)) return null;
      const rect = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      return {
        selector: selectorFor(element),
        bounding_box: { x: rect.x, y: rect.y, width: rect.width, height: rect.height, top: rect.top, right: rect.right, bottom: rect.bottom, left: rect.left },
        client_width: element.clientWidth,
        client_height: element.clientHeight,
        scroll_width: element.scrollWidth,
        scroll_height: element.scrollHeight,
        overflow_x: style.overflowX,
        overflow_y: style.overflowY,
        position: style.position,
        sticky_offset: style.position === 'sticky' ? style.top : null,
        visible_ratio: Math.max(0, Math.min(rect.right, innerWidth) - Math.max(rect.left, 0)) * Math.max(0, Math.min(rect.bottom, innerHeight) - Math.max(rect.top, 0)) / Math.max(1, rect.width * rect.height),
      };
    };
    const namedSelectors = {
      viewport_shell: '.layout-shell',
      navigation: '#primary-sidebar',
      content: '.content',
      header: '.topbar',
      tabs: '.activity-tabs',
      main: '#main-content',
      page: '#main-content > :is(.sc-page-frame, .sc-product-page-frame)',
      toolbar: '#main-content :is(.list-command-surface, .product-list-header, .sc-action-bar, .form-command-bar)',
      table: '#main-content :is(.sc-table-shell, .native-list-scroll, .table-scroll, table)',
      form: '#main-content :is([data-product-page-mode="form"], .contract-form-document)',
      dialog: ':is(.sc-dialog, .sc-drawer, [role="dialog"])',
    };
    const containers = Object.fromEntries(Object.entries(namedSelectors).map(([name, selector]) => [name, measure(document.querySelector(selector))]));
    const scrollOwners = Array.from(document.body.querySelectorAll('*')).filter((element) => {
      if (!visible(element)) return false;
      const style = getComputedStyle(element);
      return ['auto', 'scroll'].includes(style.overflowY) && element.scrollHeight > element.clientHeight + 2;
    }).map(measure).filter(Boolean);
    const silentTextClips = [];
    for (const element of document.body.querySelectorAll('button, a, label, th, td, p, h1, h2, h3, span, input, textarea')) {
      if (!visible(element)) continue;
      const style = getComputedStyle(element);
      const text = String(element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement ? element.value || element.placeholder : element.textContent || '').trim().replace(/\s+/g, ' ');
      if (!text || element.scrollWidth <= element.clientWidth + 1 || ['auto', 'scroll'].includes(style.overflowX)) continue;
      const explained = style.textOverflow === 'ellipsis' && Boolean(element.closest('[title]:not([title=""]), [aria-label]:not([aria-label=""])'));
      if (!explained && ['hidden', 'clip'].includes(style.overflowX)) silentTextClips.push({ selector: selectorFor(element), text: text.slice(0, 80), client_width: element.clientWidth, scroll_width: element.scrollWidth });
    }
    const ancestorClips = [];
    const unreachableControls = [];
    for (const element of document.body.querySelectorAll('button, a[href], input, select, textarea, [role="button"], [tabindex]:not([tabindex="-1"])')) {
      if (!visible(element)) continue;
      const rect = element.getBoundingClientRect();
      let ancestor = element.parentElement;
      let clipped = false;
      let reachableByScroll = false;
      while (ancestor && ancestor !== document.body) {
        const style = getComputedStyle(ancestor);
        const bounds = ancestor.getBoundingClientRect();
        if (['auto', 'scroll'].includes(style.overflowX)) reachableByScroll = true;
        if (!reachableByScroll && ['hidden', 'clip'].includes(style.overflowX) && (rect.left < bounds.left - 1 || rect.right > bounds.right + 1)) {
          ancestorClips.push({ selector: selectorFor(element), ancestor: selectorFor(ancestor) });
          clipped = true;
          break;
        }
        ancestor = ancestor.parentElement;
      }
      if (!clipped && !reachableByScroll && (rect.left < -1 || rect.right > innerWidth + 1)) {
        unreachableControls.push({ selector: selectorFor(element), left: rect.left, right: rect.right });
      }
    }
    const stickyObstructions = [];
    const sticky = Array.from(document.body.querySelectorAll('*')).filter((element) => visible(element) && getComputedStyle(element).position === 'sticky');
    for (const upper of sticky) {
      const a = upper.getBoundingClientRect();
      for (const lower of sticky) {
        if (upper === lower || upper.contains(lower) || lower.contains(upper)) continue;
        if (upper.closest('table') && upper.closest('table') === lower.closest('table')) continue;
        const b = lower.getBoundingClientRect();
        if (a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top) stickyObstructions.push([selectorFor(upper), selectorFor(lower)]);
      }
    }
    const page = containers.page;
    const main = containers.main;
    return {
      viewport: { width: innerWidth, height: innerHeight, device_pixel_ratio: devicePixelRatio },
      document: { client_width: document.documentElement.clientWidth, scroll_width: document.documentElement.scrollWidth, client_height: document.documentElement.clientHeight, scroll_height: document.documentElement.scrollHeight },
      containers,
      scroll_owners: scrollOwners,
      silent_text_clips: silentTextClips.slice(0, 40),
      ancestor_clips: ancestorClips.slice(0, 40),
      unreachable_controls: unreachableControls.slice(0, 40),
      sticky_obstructions: stickyObstructions.slice(0, 20),
      core_canvas_utilization: page && main ? page.bounding_box.width / Math.max(1, main.client_width) : null,
    };
  });
}

async function waitForPage(page) {
  await page.locator('.layout-shell').waitFor({ state: 'visible', timeout: 45_000 });
  await page.waitForFunction(() => {
    const main = document.querySelector('#main-content');
    return Boolean(main?.children.length) && !/正在加载页面|正在加载列表|正在初始化/.test(document.body.innerText || '');
  }, null, { timeout: 45_000 });
  await page.locator('.product-loading-shell').waitFor({ state: 'detached', timeout: 45_000 }).catch(() => {});
  await page.waitForFunction(() => !Array.from(document.querySelectorAll('#main-content [aria-busy="true"]')).some((element) => {
    const rect = element.getBoundingClientRect();
    return rect.width > 1 && rect.height > 1;
  }), null, { timeout: 45_000 }).catch(() => {});
  await page.waitForTimeout(250);
}

function relativePageUrl(page) {
  const current = new URL(page.url());
  return `${current.pathname}${current.search}`;
}

async function discoverFormRoutes(page, listRoute) {
  await page.goto(`${BASE_URL}${listRoute}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  await waitForPage(page);
  const firstRecord = page.locator('.cell-primary-link:visible, .mobile-record-card:visible').first();
  assert(await firstRecord.count(), 'runtime list did not expose a record link for form discovery');
  await firstRecord.click();
  await page.locator('[data-product-page-mode="form"]').waitFor({ state: 'visible', timeout: 45_000 });
  await page.locator('.product-form-loading-skeleton').waitFor({ state: 'detached', timeout: 45_000 }).catch(() => {});
  await page.locator('[data-form-canvas]').waitFor({ state: 'visible', timeout: 45_000 });
  const readonly = relativePageUrl(page);
  let edit = '';
  const editAction = page.getByRole('button', { name: /^编辑$/ }).first();
  if (await editAction.count() && await editAction.isEnabled().catch(() => false)) {
    await editAction.click();
    await page.locator('[data-product-page-mode="form"] input:visible, [data-product-page-mode="form"] textarea:visible, [data-product-page-mode="form"] select:visible').first().waitFor({ state: 'visible', timeout: 45_000 });
    edit = relativePageUrl(page);
  }
  await page.goto(`${BASE_URL}${listRoute}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  await waitForPage(page);
  const createAction = page.getByRole('button', { name: /新建/ }).last();
  let create = '';
  if (await createAction.count() && await createAction.isEnabled().catch(() => false)) {
    await createAction.click();
    const category = page.locator('.business-category-picker-option:visible').first();
    if (await category.count()) await category.click();
    await page.locator('[data-product-page-mode="form"]').waitFor({ state: 'visible', timeout: 45_000 });
    await page.locator('.product-form-loading-skeleton').waitFor({ state: 'detached', timeout: 45_000 }).catch(() => {});
    await page.locator('[data-form-canvas]').waitFor({ state: 'visible', timeout: 45_000 });
    create = relativePageUrl(page);
  }
  return { readonly, edit, create };
}

function checksFor(geometry) {
  const rootOverflow = geometry.document.scroll_width - geometry.document.client_width;
  const unexpectedNested = geometry.scroll_owners.filter((owner) => owner.selector !== '#main-content' && !/(^|\.)menu($|\.)|sidebar|navigation|sc-table-shell|native-list-scroll|table-scroll|dialog|drawer|designer/i.test(owner.selector));
  return {
    root_horizontal_overflow: rootOverflow <= 1,
    silent_text_clipping: geometry.silent_text_clips.length === 0,
    ancestor_clipping: geometry.ancestor_clips.length === 0,
    interactive_controls_reachable: geometry.unreachable_controls.length === 0,
    sticky_obstruction: geometry.sticky_obstructions.length === 0,
    unexpected_nested_vertical_scroll: unexpectedNested.length === 0,
    core_canvas_available: geometry.core_canvas_utilization === null || geometry.core_canvas_utilization >= 0.95,
  };
}

async function negativeFixtureProof(page) {
  await page.evaluate(() => {
    const fixture = document.createElement('div');
    fixture.id = 'geometry-negative-fixture';
    fixture.style.cssText = 'width:140vw;position:relative';
    const clipped = document.createElement('button');
    clipped.id = 'geometry-negative-clipped-control';
    clipped.style.cssText = 'display:block;width:80px;overflow:hidden;white-space:nowrap';
    clipped.textContent = '故意制造的静默裁切负向夹具'.repeat(10);
    fixture.append(clipped);
    const ancestor = document.createElement('div');
    ancestor.id = 'geometry-negative-clipping-ancestor';
    ancestor.style.cssText = 'width:60px;overflow:hidden';
    const hiddenControl = document.createElement('button');
    hiddenControl.id = 'geometry-negative-ancestor-control';
    hiddenControl.style.cssText = 'display:block;width:180px';
    hiddenControl.textContent = 'ancestor clip';
    ancestor.append(hiddenControl);
    fixture.append(ancestor);
    document.body.append(fixture);
  });
  const broken = await inspectGeometry(page);
  const detected = broken.document.scroll_width > broken.document.client_width + 1
    && broken.silent_text_clips.some((row) => row.selector === '#geometry-negative-clipped-control')
    && broken.ancestor_clips.some((row) => row.selector === '#geometry-negative-ancestor-control');
  await page.locator('#geometry-negative-fixture').evaluate((element) => element.remove());
  assert(detected, 'negative geometry fixture did not trigger root overflow and silent clipping detectors');
  return { fixture: 'root-overflow-silent-text-and-ancestor-clip', detected };
}

async function nativeTableStickyProof(page) {
  return page.evaluate(async () => {
    const shell = document.querySelector('.table > .sc-table-shell');
    const header = shell?.querySelector('thead th');
    if (!(shell instanceof HTMLElement) || !(header instanceof HTMLElement)) return { available: false, passed: false };
    const original = shell.getAttribute('style');
    shell.style.height = '72px';
    shell.style.maxHeight = '72px';
    shell.style.overflow = 'auto';
    shell.scrollTop = Math.min(36, Math.max(0, shell.scrollHeight - shell.clientHeight));
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    const shellRect = shell.getBoundingClientRect();
    const headerRect = header.getBoundingClientRect();
    const computed = getComputedStyle(header);
    const result = {
      available: true,
      passed: shell.scrollTop > 0 && computed.position === 'sticky' && computed.transform === 'none' && Math.abs(headerRect.top - shellRect.top) <= 2,
      scroll_top: shell.scrollTop,
      shell_top: shellRect.top,
      header_top: headerRect.top,
      position: computed.position,
      transform: computed.transform,
    };
    if (original === null) shell.removeAttribute('style'); else shell.setAttribute('style', original);
    return result;
  });
}

async function negativeStickyFixtureProof(page) {
  const style = await page.addStyleTag({ content: '.table thead th { position: static !important; }' });
  const broken = await nativeTableStickyProof(page);
  await style.evaluate((element) => element.remove());
  assert(broken.available && !broken.passed, 'negative sticky fixture did not make the native sticky proof fail');
  return { fixture: 'table-header-position-static', detected: true };
}

const servedIdentity = await verifyServedIdentity(acceptance, acceptance.provenance.expectedSha);
const browser = await launchAcceptanceChromium(acceptance, { headless: true });
const context = await browser.newContext({ viewport: VIEWPORTS[0] });
const page = await context.newPage();
const navigation = captureReleasedNavigation(page);
const runtime = { console_errors: [], page_errors: [], failed_responses: [] };
page.on('console', (message) => { if (message.type() === 'error' && !/favicon|ResizeObserver/i.test(message.text())) runtime.console_errors.push(message.text()); });
page.on('pageerror', (error) => runtime.page_errors.push(error.message));
page.on('response', (response) => { if (response.status() >= 400) runtime.failed_responses.push({ status: response.status(), url: response.url() }); });

try {
  await login(page, navigation);
  const discovered = actionableNodes(navigation.nav());
  const representative = discovered.find((row) => /一般合同/.test(row.path))
    || discovered.find((row) => /施工合同/.test(row.path))
    || discovered.find((row) => /项目台账/.test(row.path))
    || discovered[0];
  assert(representative?.route, 'no actionable route discovered from current system.init navigation');
  const formRoutes = await discoverFormRoutes(page, representative.route);
  const targets = [
    { key: 'home', label: '首页', route: '/' },
    { key: 'runtime-list', label: representative.path, route: representative.route },
    { key: 'runtime-form-readonly', label: `${representative.path} / 查看`, route: formRoutes.readonly },
    ...(formRoutes.create ? [{ key: 'runtime-form-create', label: `${representative.path} / 新建`, route: formRoutes.create }] : []),
    ...(formRoutes.edit ? [{ key: 'runtime-form-edit', label: `${representative.path} / 编辑`, route: formRoutes.edit }] : []),
  ];
  const discoveredRouteTargets = [...new Map(discovered.map((row) => [row.route, row])).values()]
    .filter((row) => row.route && !targets.some((target) => target.route === row.route))
    .map((row, index) => ({ key: `discovered-route-${index + 1}`, label: row.path, route: row.route }));
  const rows = [];
  for (const viewport of VIEWPORTS) {
    await page.setViewportSize(viewport);
    for (const target of targets) {
      await page.goto(`${BASE_URL}${target.route}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
      await waitForPage(page);
      const geometry = await inspectGeometry(page);
      const stickyProof = target.key === 'runtime-list' && viewport.width >= 961 ? await nativeTableStickyProof(page) : null;
      const screenshot = path.join(OUTPUT_DIR, `${target.key}-${viewport.key}.png`);
      await page.screenshot({ path: screenshot, fullPage: true });
      rows.push({ target, viewport, geometry, sticky_proof: stickyProof, checks: { ...checksFor(geometry), ...(stickyProof ? { native_table_header_sticky: stickyProof.passed } : {}) }, screenshot });
    }
    if ([1440, 390].includes(viewport.width)) {
      for (const target of discoveredRouteTargets) {
        await page.goto(`${BASE_URL}${target.route}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
        await waitForPage(page);
        const geometry = await inspectGeometry(page);
        rows.push({ target, viewport, geometry, checks: checksFor(geometry), screenshot: null });
      }
    }
    if (viewport.width >= 961) {
      await page.goto(`${BASE_URL}/`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
      await waitForPage(page);
      const expanded = await inspectGeometry(page);
      await page.locator('.sidebar-toggle').click();
      await page.waitForTimeout(200);
      const collapsed = await inspectGeometry(page);
      const shellWidth = collapsed.containers.viewport_shell?.client_width || 0;
      const mainWidth = collapsed.containers.main?.client_width || 0;
      const mainBorderBoxWidth = collapsed.containers.main?.bounding_box.width || 0;
      rows.push({
        target: { key: 'sidebar-toggle', label: '桌面侧栏隐藏态', route: '/' },
        viewport,
        geometry: collapsed,
        expanded_main_width: expanded.containers.main?.client_width || 0,
        checks: {
          sidebar_removed: collapsed.containers.navigation === null,
          dead_sidebar_track_removed: shellWidth - mainBorderBoxWidth <= 1,
          main_expands_after_hide: mainWidth > (expanded.containers.main?.client_width || 0) + 250,
        },
      });
      await page.locator('.sidebar-toggle').click();
      await page.waitForTimeout(100);
    }
  }
  for (const zoom of ZOOM_LEVELS) {
    const viewport = {
      key: `zoom-${zoom}`,
      width: Math.round(1440 / (zoom / 100)),
      height: Math.round(900 / (zoom / 100)),
      physical_width: 1440,
      physical_height: 900,
      browser_zoom_percent: zoom,
    };
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    for (const target of targets.filter((item) => ['home', 'runtime-list', 'runtime-form-readonly'].includes(item.key))) {
      await page.goto(`${BASE_URL}${target.route}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
      await waitForPage(page);
      const geometry = await inspectGeometry(page);
      const screenshot = path.join(OUTPUT_DIR, `${target.key}-${viewport.key}.png`);
      await page.screenshot({ path: screenshot, fullPage: true });
      rows.push({
        target: { ...target, label: `${target.label} / 浏览器缩放 ${zoom}%` },
        viewport,
        geometry,
        checks: checksFor(geometry),
        screenshot,
      });
    }
  }
  await page.goto(`${BASE_URL}/`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  await waitForPage(page);
  const negativeFixtures = [await negativeFixtureProof(page)];
  await page.goto(`${BASE_URL}${representative.route}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  await waitForPage(page);
  negativeFixtures.push(await negativeStickyFixtureProof(page));
  const failures = rows.flatMap((row) => Object.entries(row.checks).filter(([, passed]) => !passed).map(([check]) => ({ target: row.target, viewport: row.viewport, check, geometry: row.geometry })));
  const report = {
    schema: 'frontend_geometry_scroll_audit.v1',
    source_sha: SOURCE_SHA,
    generated_at: new Date().toISOString(),
    source: { environment: redactedEnvironmentEvidence(acceptance), served_identity: servedIdentity, navigation: 'authenticated system.init', discovered_actionable_routes: discovered.length, audited_discovered_routes: discoveredRouteTargets.length + 1, discovered_form_routes: formRoutes },
    rows,
    negative_fixtures: negativeFixtures,
    runtime,
    failures,
    passed: failures.length === 0 && !runtime.console_errors.length && !runtime.page_errors.length && !runtime.failed_responses.length,
  };
  await fs.writeFile(REPORT_JSON, `${JSON.stringify(report, null, 2)}\n`);
  const html = `<!doctype html><meta charset="utf-8"><title>SCE 几何与滚动审计</title><style>body{font:14px system-ui;margin:32px;color:#172033}table{border-collapse:collapse;width:100%}th,td{border:1px solid #d8dee8;padding:8px;text-align:left;vertical-align:top}.pass{color:#087443}.fail{color:#b42318}code{white-space:pre-wrap}</style><h1>SCE 几何与滚动审计</h1><p>来源：当前角色 authenticated system.init；数据库：${DB_NAME}；结果：<strong class="${report.passed ? 'pass' : 'fail'}">${report.passed ? 'PASS' : 'FAIL'}</strong></p><table><thead><tr><th>页面</th><th>视口</th><th>检查</th><th>画布利用率</th><th>滚动所有者</th></tr></thead><tbody>${rows.map((row) => `<tr><td>${row.target.label}</td><td>${row.viewport.width}×${row.viewport.height}</td><td><code>${Object.entries(row.checks).map(([key, value]) => `${value ? 'PASS' : 'FAIL'} ${key}`).join('\n')}</code></td><td>${row.geometry.core_canvas_utilization === null ? '-' : (row.geometry.core_canvas_utilization * 100).toFixed(1) + '%'}</td><td>${row.geometry.scroll_owners.map((owner) => owner.selector).join(', ') || '-'}</td></tr>`).join('')}</tbody></table>`;
  await fs.writeFile(REPORT_HTML, html);
  process.stdout.write(`[frontend_geometry_scroll_audit] ${report.passed ? 'PASS' : 'FAIL'} rows=${rows.length} failures=${failures.length} routes=${discovered.length}\n`);
  if (!report.passed) process.exitCode = 1;
} finally {
  await context.close();
  await browser.close();
  await acceptanceLease.release();
}
