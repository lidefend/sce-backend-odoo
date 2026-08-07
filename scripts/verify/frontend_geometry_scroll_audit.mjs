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
const SPACING_REPORT_JSON = path.resolve(process.env.SPACING_GEOMETRY_AUDIT_JSON || path.join(OUTPUT_DIR, 'spacing-geometry-audit.json'));
const SPACING_REPORT_HTML = path.resolve(process.env.SPACING_GEOMETRY_AUDIT_HTML || path.join(OUTPUT_DIR, 'spacing-geometry-audit.html'));
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
    const mainElement = document.querySelector('#main-content');
    const mainRect = mainElement?.getBoundingClientRect();
    const descendantElements = mainElement ? Array.from(mainElement.querySelectorAll('*')).filter(visible) : [];
    const descendantExtent = mainElement && mainRect
      ? descendantElements.reduce((bottom, element) => Math.max(
        bottom,
        element.getBoundingClientRect().bottom - mainRect.top + mainElement.scrollTop,
      ), 0)
      : 0;
    const relativeBottom = (element) => element && mainElement && mainRect
      ? element.getBoundingClientRect().bottom - mainRect.top + mainElement.scrollTop
      : null;
    const lastListRow = document.querySelector('.table tbody tr:last-child, .mobile-record-card:last-child');
    const pagination = document.querySelector('.pagination-footer:last-of-type, .pagination-bar:last-of-type');
    const primaryVerticalScrollOwners = scrollOwners.filter((owner) => (
      !/menu|sidebar|navigation|dialog|drawer|designer/i.test(owner.selector)
    ));
    const tableShell = document.querySelector('.table > .sc-table-shell, .table > .grouped-table');
    let columnDecision = {};
    try {
      columnDecision = JSON.parse(document.querySelector('[data-column-decision-trace]')?.getAttribute('data-column-decision-trace') || '{}');
    } catch {
      columnDecision = {};
    }
    const explicitVisibleColumns = Array.isArray(columnDecision?.desktop?.trace)
      ? columnDecision.desktop.trace.filter((row) => row?.visible && row?.reasonCode === 'explicit_visible').map((row) => row.field)
      : [];
    const visibleHeaderClips = Array.from(document.querySelectorAll('.table thead th[data-column]')).flatMap((header) => {
      if (!visible(header)) return [];
      const label = header.querySelector('.column-sort-btn > span:first-child');
      if (!(label instanceof HTMLElement)) return [];
      const clipped = label.scrollWidth > label.clientWidth + 1 || label.scrollHeight > label.clientHeight + 1;
      return clipped ? [{
        field: header.getAttribute('data-column') || '',
        label: String(label.textContent || '').trim(),
        client_width: label.clientWidth,
        scroll_width: label.scrollWidth,
        client_height: label.clientHeight,
        scroll_height: label.scrollHeight,
      }] : [];
    });
    const semanticHeading = document.querySelector('#main-content h1.sc-visually-hidden');
    const headingRect = semanticHeading?.getBoundingClientRect();
    const headingStyle = semanticHeading ? getComputedStyle(semanticHeading) : null;
    const accessibleHiddenHeading = !semanticHeading || Boolean(
      headingRect && headingStyle
      && headingRect.width <= 1.5 && headingRect.height <= 1.5
      && headingStyle.position === 'absolute'
      && (headingStyle.overflow === 'hidden' || headingStyle.clipPath !== 'none')
    );
    const firstBusinessContent = document.querySelector('.table thead, .mobile-record-card, .sc-empty-state');
    const numberPx = (value) => {
      const parsed = Number.parseFloat(value || '0');
      return Number.isFinite(parsed) ? parsed : 0;
    };
    const spacingSurfaceSelectors = [
      '.list-toolbar', '.table', '.pagination-footer', '.mobile-record-list', '.mobile-record-card',
      '.contract-form-native-shell', '.contract-form-command-bar', '.contract-form-canvas-shell',
      '.native-form-tree', '.native-container--group', '.template-form-section',
      '.relation-dialog', '.relation-dialog-search', '.relation-dialog-footer',
      '[data-spacing-audit-target]',
    ];
    const spacingSurfaces = spacingSurfaceSelectors.flatMap((selector) => Array.from(document.querySelectorAll(selector)))
      .filter((element, index, rows) => visible(element) && rows.indexOf(element) === index)
      .map((element) => {
        const style = getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        const paddingRight = numberPx(style.paddingRight);
        const touchTarget = numberPx(getComputedStyle(document.documentElement).getPropertyValue('--sc-touch-target-min'));
        const spaceXs = numberPx(getComputedStyle(document.documentElement).getPropertyValue('--sc-space-xs'));
        const compositeContracts = element.matches('.mobile-record-card')
          && element.closest('.mobile-record-row')?.querySelector('.mobile-record-select')
          && Math.abs(paddingRight - touchTarget - spaceXs) <= 1
          ? [{ property: 'padding-right', reason_code: 'visible_touch_target_reservation', components_px: [touchTarget, spaceXs] }]
          : [];
        return {
          selector: selectorFor(element),
          bounding_box: { left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom, width: rect.width, height: rect.height },
          padding: {
            top: numberPx(style.paddingTop), right: paddingRight,
            bottom: numberPx(style.paddingBottom), left: numberPx(style.paddingLeft),
          },
          gap: { row: numberPx(style.rowGap), column: numberPx(style.columnGap) },
          composite_spacing_contracts: compositeContracts,
        };
      });
    const listToolbar = document.querySelector('.list-toolbar');
    const listTable = document.querySelector('.table');
    const listPagination = document.querySelector('.pagination-footer');
    const rectOf = (element) => element && visible(element) ? element.getBoundingClientRect() : null;
    const toolbarRect = rectOf(listToolbar);
    const tableRect = rectOf(listTable);
    const paginationRect = rectOf(listPagination);
    const mobileCards = Array.from(document.querySelectorAll('.mobile-record-card')).filter(visible);
    const actualCardGaps = mobileCards.slice(1).map((card, index) => {
      const previous = mobileCards[index].getBoundingClientRect();
      const current = card.getBoundingClientRect();
      return current.top >= previous.bottom - 1 ? current.top - previous.bottom : current.left - previous.right;
    }).filter((value) => value >= -1);
    const mainBounds = mainElement?.getBoundingClientRect();
    const horizontalAxis = mainBounds ? {
      toolbar_left: toolbarRect?.left ?? null,
      table_left: tableRect?.left ?? null,
      pagination_left: paginationRect?.left ?? null,
      toolbar_right: toolbarRect?.right ?? null,
      table_right: tableRect?.right ?? null,
      pagination_right: paginationRect?.right ?? null,
      main_left: mainBounds.left,
      main_right: mainBounds.right,
    } : null;
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
      descendant_extent: descendantExtent,
      descendant_extent_reachable: !mainElement || descendantExtent <= mainElement.scrollHeight + 2,
      list_last_row_bottom: relativeBottom(lastListRow),
      list_last_row_reachable: !lastListRow || relativeBottom(lastListRow) <= mainElement.scrollHeight + 2,
      pagination_bottom: relativeBottom(pagination),
      pagination_reachable: !pagination || relativeBottom(pagination) <= mainElement.scrollHeight + 2,
      primary_vertical_scroll_owners: primaryVerticalScrollOwners,
      single_vertical_scroll_owner: primaryVerticalScrollOwners.length <= 1
        && (!mainElement || descendantExtent <= mainElement.clientHeight + 2 || primaryVerticalScrollOwners.some((owner) => owner.selector === '#main-content')),
      table_horizontal_overflow: tableShell instanceof HTMLElement ? Math.max(0, tableShell.scrollWidth - tableShell.clientWidth) : 0,
      explicit_visible_columns: explicitVisibleColumns,
      default_table_horizontal_overflow: explicitVisibleColumns.length
        ? null
        : (tableShell instanceof HTMLElement ? Math.max(0, tableShell.scrollWidth - tableShell.clientWidth) : 0),
      visible_header_clips: visibleHeaderClips,
      accessible_hidden_h1: accessibleHiddenHeading,
      first_business_content_y: firstBusinessContent?.getBoundingClientRect().top ?? null,
      standalone_column_meta_rows: document.querySelectorAll('.table-utility-row, .column-summary-row, [data-column-summary-row]').length,
      spacing: {
        scale: [0, 4, 8, 12, 16, 24, 32],
        surfaces: spacingSurfaces,
        horizontal_axis: horizontalAxis,
        toolbar_table_gap: toolbarRect && tableRect ? Math.max(0, tableRect.top - toolbarRect.bottom) : null,
        table_pagination_gap: tableRect && paginationRect ? Math.max(0, paginationRect.top - tableRect.bottom) : null,
        card_gaps: actualCardGaps,
      },
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
    core_canvas_available: geometry.core_canvas_utilization === null || geometry.core_canvas_utilization >= 0.93,
    descendant_extent_reachable: geometry.descendant_extent_reachable,
    list_last_row_reachable: geometry.list_last_row_reachable,
    pagination_reachable: geometry.pagination_reachable,
    single_vertical_scroll_owner: geometry.single_vertical_scroll_owner,
    default_table_horizontal_overflow: geometry.default_table_horizontal_overflow === null || geometry.default_table_horizontal_overflow <= 1,
    visible_table_headers_unclipped: geometry.visible_header_clips.length === 0,
    accessible_hidden_h1: geometry.accessible_hidden_h1,
    standalone_column_meta_row: geometry.standalone_column_meta_rows === 0,
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

async function listSelectionProof(page) {
  const desktopRows = page.locator('.desktop-record-table:visible tbody .cell-select input[type="checkbox"]:visible');
  const mobileRows = page.locator('.mobile-record-list:visible [data-mobile-record-select] input[type="checkbox"]:visible');
  const rows = await desktopRows.count() ? desktopRows : mobileRows;
  const rowCount = await rows.count();
  if (!rowCount) return { available: false, passed: false, row_count: 0 };
  const first = rows.first();
  await first.check();
  const selectedBar = page.locator('.batch-bar:visible');
  const selectedText = String(await selectedBar.textContent().catch(() => '') || '').trim();
  const exportAction = selectedBar.getByRole('button', { name: '导出所选' });
  const selectionPassed = await first.isChecked() && await selectedBar.count() > 0 && /已选\s*1\s*条/.test(selectedText);
  const downloadPromise = page.waitForEvent('download');
  await exportAction.click();
  const download = await downloadPromise;
  const exportPassed = /\.csv$/i.test(download.suggestedFilename());
  if (await first.isChecked().catch(() => false)) await first.uncheck();
  return { available: true, passed: selectionPassed && exportPassed, row_count: rowCount, selected_text: selectedText, export_file: download.suggestedFilename() };
}

async function negativeStickyFixtureProof(page) {
  const style = await page.addStyleTag({ content: '.table thead th { position: static !important; }' });
  const broken = await nativeTableStickyProof(page);
  await style.evaluate((element) => element.remove());
  assert(broken.available && !broken.passed, 'negative sticky fixture did not make the native sticky proof fail');
  return { fixture: 'table-header-position-static', detected: true };
}

function nearestSpacingToken(value) {
  const scale = [0, 4, 8, 12, 16, 24, 32];
  return scale.reduce((best, token) => Math.abs(token - value) < Math.abs(best - value) ? token : best, scale[0]);
}

function spacingFindings(rows) {
  const findings = [];
  for (const row of rows) {
    const spacing = row.geometry?.spacing;
    if (!spacing) continue;
    for (const surface of spacing.surfaces || []) {
      for (const [side, value] of Object.entries(surface.padding || {})) {
        if ((surface.composite_spacing_contracts || []).some((contract) => contract.property === `padding-${side}`)) continue;
        const nearest = nearestSpacingToken(value);
        if (Math.abs(value - nearest) > 1) findings.push({ target: row.target, viewport: row.viewport, selector: surface.selector, property: `padding-${side}`, value, nearest_token: nearest });
      }
      for (const [axis, value] of Object.entries(surface.gap || {})) {
        const nearest = nearestSpacingToken(value);
        if (Math.abs(value - nearest) > 1) findings.push({ target: row.target, viewport: row.viewport, selector: surface.selector, property: `${axis}-gap`, value, nearest_token: nearest });
      }
    }
  }
  return findings;
}

async function negativeSpacingFixtureProof(page) {
  await page.evaluate(() => {
    const fixture = document.createElement('div');
    fixture.id = 'spacing-negative-fixture';
    fixture.dataset.spacingAuditTarget = 'true';
    fixture.style.cssText = 'display:block;padding:18px;gap:20px;width:40px;height:40px';
    document.querySelector('#main-content')?.append(fixture);
  });
  const broken = await inspectGeometry(page);
  const fixtureSurface = broken.spacing.surfaces.find((surface) => surface.selector === '#spacing-negative-fixture');
  await page.locator('#spacing-negative-fixture').evaluate((element) => element.remove());
  const detected = fixtureSurface?.padding?.left === 18 && fixtureSurface?.gap?.row === 20;
  assert(detected, 'negative spacing fixture did not expose rogue computed spacing');
  return { fixture: 'rogue-computed-spacing-18-20', detected };
}

const servedIdentity = await verifyServedIdentity(acceptance, acceptance.provenance.expectedSha);
let browser;
let context;
let page;
let navigation;
const runtime = { console_errors: [], page_errors: [], failed_responses: [] };

async function startBrowserSession(viewport) {
  await context?.close().catch(() => {});
  await browser?.close().catch(() => {});
  browser = await launchAcceptanceChromium(acceptance, { headless: true });
  context = await browser.newContext({ viewport });
  page = await context.newPage();
  navigation = captureReleasedNavigation(page);
  page.on('console', (message) => { if (message.type() === 'error' && !/favicon|ResizeObserver/i.test(message.text())) runtime.console_errors.push(message.text()); });
  page.on('pageerror', (error) => runtime.page_errors.push(error.message));
  page.on('response', (response) => { if (response.status() >= 400) runtime.failed_responses.push({ status: response.status(), url: response.url() }); });
  await login(page, navigation);
}

try {
  await startBrowserSession(VIEWPORTS[0]);
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
  for (const [viewportIndex, viewport] of VIEWPORTS.entries()) {
    if (viewportIndex > 0) await startBrowserSession(viewport);
    for (const target of targets) {
      process.stdout.write(`[geometry] ${viewport.key} ${target.key}\n`);
      await page.goto(`${BASE_URL}${target.route}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
      await waitForPage(page);
      const geometry = await inspectGeometry(page);
      const desktopTableVisible = target.key === 'runtime-list'
        ? await page.locator('.desktop-record-table').isVisible().catch(() => false)
        : false;
      const stickyProof = desktopTableVisible ? await nativeTableStickyProof(page) : null;
      const screenshot = path.join(OUTPUT_DIR, `${target.key}-${viewport.key}.png`);
      await page.screenshot({ path: screenshot, fullPage: true });
      const selectionProof = target.key === 'runtime-list' ? await listSelectionProof(page) : null;
      rows.push({ target, viewport, geometry, sticky_proof: stickyProof, selection_proof: selectionProof, checks: { ...checksFor(geometry), ...(stickyProof ? { native_table_header_sticky: stickyProof.passed } : {}), ...(selectionProof ? { list_selection_operable: selectionProof.passed } : {}) }, screenshot });
    }
    if ([1440, 390].includes(viewport.width)) {
      for (const [routeIndex, target] of discoveredRouteTargets.entries()) {
        if (routeIndex > 0 && routeIndex % 5 === 0) await startBrowserSession(viewport);
        process.stdout.write(`[geometry] ${viewport.key} ${target.key} ${target.route}\n`);
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
      const expandedNavigationWidth = expanded.containers.navigation?.bounding_box.width || 0;
      rows.push({
        target: { key: 'sidebar-toggle', label: '桌面侧栏隐藏态', route: '/' },
        viewport,
        geometry: collapsed,
        expanded_main_width: expanded.containers.main?.client_width || 0,
        expanded_navigation_width: expandedNavigationWidth,
        checks: {
          sidebar_removed: collapsed.containers.navigation === null,
          dead_sidebar_track_removed: shellWidth - mainBorderBoxWidth <= 1,
          main_expands_after_hide: mainWidth >= (expanded.containers.main?.client_width || 0) + Math.max(0, expandedNavigationWidth - 1),
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
    await startBrowserSession({ width: viewport.width, height: viewport.height });
    for (const target of targets.filter((item) => ['home', 'runtime-list', 'runtime-form-readonly'].includes(item.key))) {
      process.stdout.write(`[geometry] ${viewport.key} ${target.key}\n`);
      await page.goto(`${BASE_URL}${target.route}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
      await waitForPage(page);
      const geometry = await inspectGeometry(page);
      const screenshot = path.join(OUTPUT_DIR, `${target.key}-${viewport.key}.png`);
      await page.screenshot({ path: screenshot, fullPage: true });
      const selectionProof = target.key === 'runtime-list' ? await listSelectionProof(page) : null;
      rows.push({
        target: { ...target, label: `${target.label} / 浏览器缩放 ${zoom}%` },
        viewport,
        geometry,
        selection_proof: selectionProof,
        checks: { ...checksFor(geometry), ...(selectionProof ? { list_selection_operable: selectionProof.passed } : {}) },
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
  negativeFixtures.push(await negativeSpacingFixtureProof(page));
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
  const spacingRogueValues = spacingFindings(rows);
  const spacingRows = rows.filter((row) => row.geometry?.spacing).map((row) => {
    const spacing = row.geometry.spacing;
    const axisValues = spacing.horizontal_axis
      ? [spacing.horizontal_axis.toolbar_left, spacing.horizontal_axis.table_left, spacing.horizontal_axis.pagination_left].filter(Number.isFinite)
      : [];
    const axisDelta = axisValues.length > 1 ? Math.max(...axisValues) - Math.min(...axisValues) : 0;
    const cardGaps = spacing.card_gaps || [];
    const cardGapConsistent = cardGaps.length < 2 || Math.max(...cardGaps) - Math.min(...cardGaps) <= 1;
    return {
      target: row.target,
      viewport: row.viewport,
      measurements: spacing,
      checks: {
        shared_horizontal_axis_delta: axisDelta <= 1,
        normal_list_toolbar_table_gap: spacing.toolbar_table_gap === null || spacing.toolbar_table_gap <= 1,
        table_pagination_gap: spacing.table_pagination_gap === null || spacing.table_pagination_gap <= 1,
        card_gap_consistent: cardGapConsistent,
      },
      shared_horizontal_axis_delta_px: axisDelta,
    };
  });
  const spacingFailures = [
    ...spacingRows.flatMap((row) => Object.entries(row.checks).filter(([, passed]) => !passed).map(([check]) => ({ target: row.target, viewport: row.viewport, check }))),
    ...spacingRogueValues.map((finding) => ({ check: 'rogue_spacing_value_on_target_surfaces', ...finding })),
  ];
  const spacingReport = {
    schema: 'frontend_spacing_geometry_audit.v1',
    source_sha: SOURCE_SHA,
    generated_at: new Date().toISOString(),
    source: report.source,
    token_scale_px: [0, 4, 8, 12, 16, 24, 32],
    measurement_method: 'Playwright bounding boxes plus browser computed padding/row-gap/column-gap',
    rows: spacingRows,
    negative_fixtures: negativeFixtures.filter((fixture) => fixture.fixture.includes('spacing')),
    rogue_values: spacingRogueValues,
    failures: spacingFailures,
    passed: spacingFailures.length === 0,
  };
  await fs.writeFile(SPACING_REPORT_JSON, `${JSON.stringify(spacingReport, null, 2)}\n`);
  const spacingHtml = `<!doctype html><meta charset="utf-8"><title>SCE 空间几何审计</title><style>body{font:14px system-ui;margin:32px;color:#172033}table{border-collapse:collapse;width:100%}th,td{border:1px solid #d8dee8;padding:8px;text-align:left;vertical-align:top}.pass{color:#087443}.fail{color:#b42318}code{white-space:pre-wrap}</style><h1>SCE 空间几何审计</h1><p>测量：真实浏览器 bounding boxes + computed padding/gap；结果：<strong class="${spacingReport.passed ? 'pass' : 'fail'}">${spacingReport.passed ? 'PASS' : 'FAIL'}</strong></p><table><thead><tr><th>页面</th><th>视口</th><th>轴线偏差</th><th>工具栏→内容</th><th>检查</th></tr></thead><tbody>${spacingRows.map((row) => `<tr><td>${row.target.label}</td><td>${row.viewport.width}×${row.viewport.height}</td><td>${row.shared_horizontal_axis_delta_px.toFixed(1)}px</td><td>${row.measurements.toolbar_table_gap ?? '-'}</td><td><code>${Object.entries(row.checks).map(([key, value]) => `${value ? 'PASS' : 'FAIL'} ${key}`).join('\n')}</code></td></tr>`).join('')}</tbody></table>`;
  await fs.writeFile(SPACING_REPORT_HTML, spacingHtml);
  process.stdout.write(`[frontend_geometry_scroll_audit] ${report.passed ? 'PASS' : 'FAIL'} rows=${rows.length} failures=${failures.length} routes=${discovered.length}\n`);
  process.stdout.write(`[frontend_spacing_geometry_audit] ${spacingReport.passed ? 'PASS' : 'FAIL'} rows=${spacingRows.length} failures=${spacingFailures.length}\n`);
  if (!report.passed || !spacingReport.passed) process.exitCode = 1;
} finally {
  await context.close().catch(() => {});
  await browser.close().catch(() => {});
  await acceptanceLease.release();
}
