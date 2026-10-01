#!/usr/bin/env node

import fs from 'node:fs/promises';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';
import { captureReleasedNavigation } from './released_navigation_target.mjs';
import { resolveAcceptanceEnvironment } from './lib/frontend_acceptance_environment.mjs';

const acceptance = resolveAcceptanceEnvironment({ tool: 'geometry-scroll-audit' });
const BASE_URL = acceptance.baseUrl;
const DATABASE = acceptance.database;
const LOGIN = process.env.E2E_LOGIN || acceptance.login || acceptance.roleBindings.project_manager || '';
const PASSWORD = process.env.E2E_PASSWORD || acceptance.password || process.env.SC_ACCEPTANCE_FIXTURE_PASSWORD || '';
const BOOTSTRAP_SECRET = process.env.SC_ACCEPTANCE_BOOTSTRAP_SECRET || '';
const PHASE = String(process.env.LIST_SURFACE_PHASE || 'full');
const OUTPUT = path.resolve(process.env.LIST_SURFACE_OUTPUT || '.runtime/final-acceptance/list-surface-structure');
const REPORT = path.resolve(process.env.LIST_SURFACE_REPORT || '.runtime/final-acceptance/list-surface-structure.json');
const DEFAULT_VIEWPORTS = PHASE === 'current-fail'
  ? [{ key: '1440', width: 1440, height: 900 }]
  : [
      { key: '1440', width: 1440, height: 900 },
      { key: '1024', width: 1024, height: 768 },
      { key: '768', width: 768, height: 1024 },
      { key: '521', width: 521, height: 844 },
      { key: '520', width: 520, height: 844 },
      { key: '390', width: 390, height: 844 },
    ];
const requestedWidths = String(process.env.LIST_SURFACE_VIEWPORTS || '').split(',').filter(Boolean);
if (requestedWidths.some(width => !DEFAULT_VIEWPORTS.some(viewport => viewport.key === width))) throw new Error('unknown LIST_SURFACE_VIEWPORTS');
const VIEWPORTS = requestedWidths.length ? DEFAULT_VIEWPORTS.filter(viewport => requestedWidths.includes(viewport.key)) : DEFAULT_VIEWPORTS;
const REQUESTED_ROUTE = String(process.env.LIST_SURFACE_ROUTE || '').trim();
if (REQUESTED_ROUTE && !/^\/a\/\d+\?menu_id=\d+$/.test(REQUESTED_ROUTE)) throw new Error('LIST_SURFACE_ROUTE must identify exact action/menu');

if (!LOGIN || (!PASSWORD && !BOOTSTRAP_SECRET)) {
  throw new Error('acceptance login and password or isolated bootstrap secret are required');
}
await fs.mkdir(OUTPUT, { recursive: true });

function routeFor(node) {
  const meta = node?.meta && typeof node.meta === 'object' ? node.meta : {};
  const actionId = Number(node?.action_id || node?.actionId || node?.action || meta.action_id || meta.actionId || 0);
  const menuId = Number(node?.menu_id || node?.menuId || meta.menu_id || meta.menuId || 0);
  const route = String(node?.route || meta.route || '');
  if (route) return actionId > 0 && menuId > 0 && !/[?&]menu_id=/.test(route)
    ? `${route}${route.includes('?') ? '&' : '?'}menu_id=${menuId}`
    : route;
  return actionId > 0 ? `/a/${actionId}${menuId > 0 ? `?menu_id=${menuId}` : ''}` : '';
}

function actionable(nodes, parents = []) {
  const result = [];
  for (const node of Array.isArray(nodes) ? nodes : []) {
    const label = String(node?.title || node?.label || node?.name || '').trim();
    const labels = [...parents, label].filter(Boolean);
    const route = routeFor(node);
    if (route) result.push({ label: labels.join(' / '), route });
    result.push(...actionable(node?.children, labels));
  }
  return result;
}

async function login(page, navigation) {
  if (BOOTSTRAP_SECRET) {
    const response = await page.request.post(`${BASE_URL}/api/v1/intent`, {
      data: { intent: 'bootstrap', params: { db: DATABASE, login: LOGIN } },
      headers: {
        'X-Anonymous-Intent': '1',
        'X-Bootstrap-Secret': BOOTSTRAP_SECRET,
      },
    });
    const envelope = await response.json();
    const token = String(envelope?.data?.token || envelope?.result?.token || '');
    if (!response.ok() || !token) throw new Error(`isolated bootstrap failed: status=${response.status()}`);
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
    await page.evaluate(({ db, authToken }) => {
      sessionStorage.setItem(`sc_auth_token:${db}`, authToken);
      sessionStorage.setItem('sc_active_db:acceptance', db);
    }, { db: DATABASE, authToken: token });
    await page.goto(`${BASE_URL}/`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
    await page.locator('.layout-shell').waitFor({ state: 'visible', timeout: 45_000 });
    await page.waitForFunction(() => !/正在初始化|正在加载导航/.test(document.body.innerText || ''), null, { timeout: 45_000 });
    if (!navigation.nav().length) throw new Error('bootstrap navigation was not captured');
    return;
  }
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  await page.locator('#login-username, input[autocomplete="username"]').first().fill(LOGIN);
  await page.locator('#login-password, input[autocomplete="current-password"]').first().fill(PASSWORD);
  const database = page.locator('input').nth(2);
  if (await database.isEnabled().catch(() => false)) await database.fill(DATABASE);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45_000 });
  await page.locator('.layout-shell').waitFor({ state: 'visible', timeout: 45_000 });
  await page.waitForFunction(() => !/正在初始化|正在加载导航/.test(document.body.innerText || ''), null, { timeout: 45_000 });
  if (!navigation.nav().length) throw new Error('authenticated navigation was not captured');
}

async function waitForList(page) {
  await page.locator('[data-list-query-action-bar]').waitFor({ state: 'visible', timeout: 45_000 });
  await page.locator('.product-loading-shell').waitFor({ state: 'detached', timeout: 45_000 }).catch(() => {});
  await page.waitForFunction(() => !document.querySelector('[data-list-query-action-bar][aria-busy="true"]'), null, { timeout: 45_000 }).catch(() => {});
  await page.waitForTimeout(200);
}

const MOBILE_RECORD_ROW = '.mobile-record-list .collection-mobile-record-row';
const MOBILE_RECORD_CARD = `${MOBILE_RECORD_ROW} .collection-mobile-record-row__card`;
const ROW_SELECTION_CONTROL = '.collection-selection-control[data-selection-scope="row"]';
const DESKTOP_ROW_SELECTION_CONTROL = `.table tbody ${ROW_SELECTION_CONTROL}`;
const MOBILE_ROW_SELECTION_CONTROL = `${MOBILE_RECORD_ROW} ${ROW_SELECTION_CONTROL}`;
// Declared list-surface search contract. The released toolbar renders the official
// collection search control; the fallback header renders the declared search form.
// The declared search affordances are the control's own submit/clear buttons: the
// primitive consumes Enter before the declared keydown handler can run, so a key
// press is not a reproducible submission and must not be used as the probe.
const SEARCH_INPUT = '[data-list-query-action-bar] .collection-search-control input[type="search"], [data-list-query-action-bar] form.product-list-header__search input[type="search"]';
const SEARCH_SUBMIT = '[data-list-query-action-bar] .collection-search-control button.toolbar-search-submit, [data-list-query-action-bar] form.product-list-header__search button[type="submit"]';
const SEARCH_CLEAR = '[data-list-query-action-bar] .collection-search-control button.toolbar-search-clear';
const EMPTY_STATE = '[data-semantic-component="ScEmptyState"][data-state="empty"], .sc-empty, .list-empty-state';
// page.evaluate callbacks run in the browser, so they must inline these literals.

async function submitDeclaredSearch(page, value) {
  const input = page.locator(SEARCH_INPUT).first();
  await input.waitFor({ state: 'visible', timeout: 15_000 });
  await input.fill(value);
  const clear = page.locator(SEARCH_CLEAR).first();
  if (!value && await clear.count() && await clear.isVisible()) await clear.click();
  else await page.locator(SEARCH_SUBMIT).first().click();
  await waitForList(page);
}

async function findPopulatedList(page, navigation) {
  const routes = actionable(navigation.nav());
  const preferred = routes.filter((row) => /一般合同|项目台账|施工合同/.test(row.label));
  if (REQUESTED_ROUTE && !routes.some(row => row.route === REQUESTED_ROUTE)) throw new Error('requested list route is not in captured released navigation');
  const candidates = REQUESTED_ROUTE ? routes.filter(row => row.route === REQUESTED_ROUTE) : [...preferred, ...routes.filter((row) => !preferred.includes(row))];
  for (const target of candidates) {
    await page.goto(`${BASE_URL}${target.route}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
    const toolbar = page.locator('[data-list-query-action-bar]');
    if (!await toolbar.waitFor({ state: 'visible', timeout: 8_000 }).then(() => true).catch(() => false)) continue;
    await waitForList(page);
    if (await page.locator(`.table tbody tr, ${MOBILE_RECORD_ROW}`).count()) return target;
  }
  throw new Error('no populated runtime list was discovered');
}

async function measure(page, viewport, state = 'normal', interaction = {}) {
  return page.evaluate(({ width, expectedState, selectionSource, selectionNavigationStable }) => {
    const visible = (element) => {
      if (!(element instanceof HTMLElement)) return false;
      const rect = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      return rect.width > 1 && rect.height > 1 && style.display !== 'none' && style.visibility !== 'hidden';
    };
    const toolbar = document.querySelector('[data-list-query-action-bar]');
    const contextualToolbar = document.querySelector('.list-surface-contextual-toolbar');
    const headerRect = toolbar?.getBoundingClientRect();
    const withinHeader = (control) => {
      const rect = control.getBoundingClientRect();
      return Boolean(headerRect && rect.left >= headerRect.left - 1 && rect.right <= headerRect.right + 1
        && rect.top >= headerRect.top - 1 && rect.bottom <= headerRect.bottom + 1);
    };
    const contentFollowsHeader = (content) => visible(content) && Boolean(headerRect)
      && content.getBoundingClientRect().top >= headerRect.bottom - 1
      && content.getBoundingClientRect().top < innerHeight;
    const geometry = () => {
      const controls = Array.from(toolbar?.querySelectorAll('input, button, select') || []).filter(element => visible(element) && !element.closest('.search-dropdown, .list-surface-column-menu'));
      const rects = controls.map(control => control.getBoundingClientRect());
      const overlap = rects.some((a, i) => rects.some((b, j) => j > i && Math.min(a.right, b.right) - Math.max(a.left, b.left) > 1 && Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > 1));
      const search = Array.from(toolbar?.querySelectorAll('input[type="search"]') || []).filter(visible);
      const columns = Array.from(toolbar?.querySelectorAll('.list-surface-column-button') || []).filter(visible);
      const leading = toolbar?.querySelector('.product-list-header__leading')?.getBoundingClientRect();
      const query = toolbar?.querySelector('.product-list-header__query, .product-list-header__search')?.getBoundingClientRect();
      return {
        toolbar_controls_within_header: controls.every(withinHeader),
        toolbar_controls_not_overlapping: !overlap,
        toolbar_controls_in_viewport: rects.every(rect => rect.left >= -1 && rect.right <= innerWidth + 1),
        mobile_touch_targets: width > 760 || controls.filter(control => control.tagName === 'BUTTON').every(control => { const rect = control.getBoundingClientRect(); return rect.width >= 44 && rect.height >= 44; }),
        search_implementation_count: search.length === 1,
        column_settings_unique: columns.length === 1,
        desktop_actions_query_aligned: width < 1440 || expectedState === 'batch' || Boolean(leading && query && leading.width > 0 && query.width > 0 && leading.right <= query.left + 1 && Math.min(leading.bottom, query.bottom) > Math.max(leading.top, query.top)),
      };
    };
    const mobileCards = Array.from(document.querySelectorAll('.mobile-record-list .collection-mobile-record-row')).filter(visible);
    const mobileMode = mobileCards.length > 0;
    const visibleMobileSelectionControls = Array.from(document.querySelectorAll('.mobile-record-list .collection-mobile-record-row .collection-selection-control[data-selection-scope="row"]')).filter(visible);
    const mobileSelectionTargetSizes = visibleMobileSelectionControls.map((target) => {
      const rect = target.getBoundingClientRect();
      return { width: rect.width, height: rect.height };
    });
    const mobileSelectionTargetsMeetSize = mobileSelectionTargetSizes.every((size) => size.width >= 44 && size.height >= 44);
    const selectedMobileCards = mobileCards.filter((card) => card.getAttribute('aria-selected') === 'true');
    const decisionSurface = document.querySelector('[data-column-decision-trace]');
    let columnDecisionTrace = null;
    try { columnDecisionTrace = JSON.parse(decisionSurface?.getAttribute('data-column-decision-trace') || 'null'); } catch {}
    const traceComplete = Boolean(
      columnDecisionTrace
      && Array.isArray(columnDecisionTrace.authoritativeColumns)
      && Array.isArray(columnDecisionTrace.enabledColumns)
      && Array.isArray(columnDecisionTrace.criticalColumns)
      && columnDecisionTrace.explicitVisibility
      && typeof columnDecisionTrace.explicitVisibility === 'object'
      && columnDecisionTrace.defaultVisibility
      && typeof columnDecisionTrace.defaultVisibility === 'object'
      && Array.isArray(columnDecisionTrace.desktop?.visibleColumns)
      && Array.isArray(columnDecisionTrace.mobile?.visibleColumns),
    );
    if (expectedState === 'batch') {
      const controls = Array.from(toolbar?.querySelectorAll('button, input, select') || []).filter(visible);
      const rowCenters = [];
      for (const control of controls) {
        const center = control.getBoundingClientRect().top + control.getBoundingClientRect().height / 2;
        if (!rowCenters.some((value) => Math.abs(value - center) <= 6)) rowCenters.push(center);
      }
      const tableContent = Array.from(document.querySelectorAll('[data-collection-presentation="table"], .grouped-table')).find(visible);
      const cardContent = Array.from(document.querySelectorAll('.mobile-record-list .collection-mobile-record-row .collection-mobile-record-row__card')).find(visible);
      const firstContent = tableContent || cardContent;
      const firstContentY = visible(firstContent) ? firstContent.getBoundingClientRect().top : null;
      return {
        checks: {
          ...geometry(),
          toolbar_present: visible(contextualToolbar),
          batch_query_coexists: visible(contextualToolbar) && visible(toolbar) && toolbar.querySelectorAll('input[type="search"]').length === 1,
          toolbar_controls_within_header: controls.every(withinHeader),
          first_business_content_order: contentFollowsHeader(firstContent),
          visible_mobile_selection_control: !mobileMode || (visibleMobileSelectionControls.length > 0 && mobileSelectionTargetsMeetSize),
          selected_mobile_card_identifiable: !mobileMode || (selectedMobileCards.length > 0 && visibleMobileSelectionControls.some((control) => control.getAttribute('data-selection-state') === 'checked')),
          mobile_batch_created_without_hidden_desktop_control: !mobileMode || selectionSource === 'visible_mobile',
          mobile_selection_does_not_open_detail: !mobileMode || selectionNavigationStable,
          selected_mobile_card_detail_reachable: !mobileMode || selectedMobileCards.some((card) => visible(card.querySelector('.collection-mobile-record-row__card'))),
          decision_trace_complete: expectedState === 'empty' || traceComplete,
        },
        metrics: {
          viewport_width: width,
          contextual_control_count: controls.length,
          toolbar_visual_row_count: rowCenters.length,
          first_business_content_y: firstContentY,
          mobile_mode: mobileMode,
          visible_mobile_selection_control_count: visibleMobileSelectionControls.length,
          mobile_selection_target_sizes: mobileSelectionTargetSizes,
          selected_mobile_card_count: selectedMobileCards.length,
          selection_source: selectionSource,
          column_decision_trace: columnDecisionTrace,
        },
      };
    }
    if (!(toolbar instanceof HTMLElement)) return { checks: { toolbar_present: false } };
    const actionBars = Array.from(toolbar.querySelectorAll('.sc-design-action-bar')).filter(visible);
    const searches = Array.from(toolbar.querySelectorAll('input[type="search"]')).filter(visible);
    const controls = Array.from(toolbar.querySelectorAll('input, button, select')).filter((element) => (
      visible(element) && !element.closest('.search-dropdown, .list-surface-column-menu')
    ));
    const rowCenters = [];
    for (const control of controls) {
      const center = control.getBoundingClientRect().top + control.getBoundingClientRect().height / 2;
      if (!rowCenters.some((value) => Math.abs(value - center) <= 6)) rowCenters.push(center);
    }
    // The column-settings control is judged inside the declared list-surface
    // header layout region, never by free-floating vertical-center proximity
    // between arbitrary controls. The declared narrow layout keeps the query
    // track at `flex-basis: calc(100% - 60px)` and the column settings in the
    // auxiliary track of that same declared flex row, while the query track is
    // itself a taller multi-row region, so equal centers are not the declared
    // contract for "same row".
    const columnButton = toolbar.querySelector('.list-surface-column-button');
    const declaredLayout = toolbar.querySelector('.product-list-header__layout')
      || toolbar.querySelector('.product-list-header__tools')
      || toolbar;
    const declaredCells = Array.from(declaredLayout.children).filter(visible);
    const columnCell = visible(columnButton)
      ? (columnButton.closest('.product-list-header__auxiliary, .product-list-header__actions') || columnButton)
      : null;
    const columnCellRect = columnCell ? columnCell.getBoundingClientRect() : null;
    const columnRowPeers = columnCellRect
      ? declaredCells.filter((cell) => {
        if (cell === columnCell) return false;
        const rect = cell.getBoundingClientRect();
        return Math.min(columnCellRect.bottom, rect.bottom) - Math.max(columnCellRect.top, rect.top) > 1;
      })
      : [];
    const table = Array.from(document.querySelectorAll('[data-collection-presentation="table"], .grouped-table')).find(visible);
    const firstCard = Array.from(document.querySelectorAll('.mobile-record-list .collection-mobile-record-row .collection-mobile-record-row__card')).find(visible);
    const emptyState = document.querySelector('[data-semantic-component="ScEmptyState"][data-state="empty"], .sc-empty, .list-empty-state');
    const firstContent = expectedState === 'empty' ? emptyState : table || firstCard;
    const firstContentY = visible(firstContent) ? firstContent.getBoundingClientRect().top : null;
    const sidebarSubtitle = String(document.querySelector('#primary-sidebar .brand .subtitle')?.textContent || '').trim();
    const topbarActions = document.querySelector('.topbar-actions');
    const visiblyReadableText = (element) => {
      if (!visible(element)) return false;
      const rect = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      const clip = String(style.clip || '').replace(/\s+/g, '').toLowerCase();
      return rect.width > 2 && rect.height > 2 && clip !== 'rect(0px,0px,0px,0px)' && clip !== 'rect(0,0,0,0)';
    };
    const topbarTextSources = [];
    let declaredContextTextSourcesExcluded = 0;
    if (topbarActions) {
      const walker = document.createTreeWalker(topbarActions, NodeFilter.SHOW_TEXT);
      for (let node = walker.nextNode(); node; node = walker.nextNode()) {
        const text = String(node.nodeValue || '').replace(/\s+/g, ' ').trim();
        const parent = node.parentElement;
        if (!text || !parent) continue;
        // The formally declared workspace context indicator legitimately shows
        // the current company/record label in the topbar. Only undeclared
        // duplication of sidebar context is a defect, so the declared indicator
        // is excluded rather than counted as a duplicate.
        if (parent.closest('[data-semantic-component="WorkspaceContextIndicator"]')) {
          declaredContextTextSourcesExcluded += 1;
          continue;
        }
        let readable = true;
        for (let current = parent; current && current !== topbarActions; current = current.parentElement) {
          if (!visiblyReadableText(current)) {
            readable = false;
            break;
          }
        }
        if (!readable) continue;
        const range = document.createRange();
        range.selectNodeContents(node);
        const rect = range.getBoundingClientRect();
        if (rect.width <= 2 || rect.height <= 2) continue;
        topbarTextSources.push({
          tag: parent.tagName.toLowerCase(),
          class_name: String(parent.className || ''),
          text,
          width: rect.width,
          height: rect.height,
          clip: String(getComputedStyle(parent).clip || ''),
        });
      }
    }
    const topbarText = topbarTextSources.map((item) => item.text).join(' ');
    const contextTokens = sidebarSubtitle.split('·').map((item) => item.trim()).filter(Boolean);
    const repeatedContext = contextTokens.filter((token) => token.length > 1 && topbarText.includes(token));
    const visibleHomeHeader = Array.from(document.querySelectorAll('.role-home-surface__header, [data-home-title-canvas]')).some(visible);
    const clearActions = Array.from(document.querySelectorAll('button')).filter((button) => {
      if (!visible(button)) return false;
      return ['清除', '清除全部', '清除查询条件'].includes(String(button.textContent || '').replace(/\s+/g, '').trim());
    });
    const columnCountHint = toolbar.querySelector('.list-surface-column-count');
    const visibleColumnCountText = visible(columnButton)
      && /\b\d+\s*\/\s*\d+\b/.test(String(columnButton.textContent || ''));
    const searchInsideSingleActionBar = actionBars.length === 1
      && searches.length === 1
      && actionBars[0].contains(searches[0]);
    const toolbarRect = toolbar.getBoundingClientRect();
    const controlRects = controls.map((control) => {
      const rect = control.getBoundingClientRect();
      return { tag: control.tagName.toLowerCase(), type: control.getAttribute('type') || '', className: String(control.className || '').slice(0, 160), ariaLabel: control.getAttribute('aria-label') || '', left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom, width: rect.width, height: rect.height };
    });
    const controlsOverlap = controlRects.some((left, leftIndex) => controlRects.some((right, rightIndex) => (
      rightIndex > leftIndex
      && Math.min(left.right, right.right) - Math.max(left.left, right.left) > 1
      && Math.min(left.bottom, right.bottom) - Math.max(left.top, right.top) > 1
    )));
    const controlsInViewport = controlRects.every((rect) => rect.left >= -1 && rect.right <= innerWidth + 1);
    const mobileTouchTargetsPass = !mobileMode || controlRects.filter((rect) => rect.tag === 'button').every((rect) => rect.width >= 44 && rect.height >= 44);
    // The declared search control owns the usable touch box; the raw primitive input
    // is only its inner text line and must not be used as the control measurement.
    const searchControl = searches[0]?.closest('.collection-search-control, .product-list-header__search') || searches[0];
    const searchInputRect = searchControl?.getBoundingClientRect();
    const checks = {
      ...geometry(),
      toolbar_present: true,
      search_implementation_count: searches.length === 1,
      single_action_formatting_context: actionBars.length === 1,
      search_inside_single_action_bar: searchInsideSingleActionBar,
      toolbar_controls_within_header: controls.every(withinHeader),
      column_settings_standalone: !visible(columnButton) || (Boolean(columnCellRect) && columnRowPeers.length > 0),
      first_business_content_order: contentFollowsHeader(firstContent),
      visible_mobile_selection_control: expectedState !== 'normal' || !mobileMode || (visibleMobileSelectionControls.length > 0 && mobileSelectionTargetsMeetSize),
      decision_trace_complete: expectedState === 'empty' || traceComplete,
      column_count_not_visible: !visible(columnCountHint) && !visibleColumnCountText,
      empty_clear_semantics_unique: expectedState !== 'empty' || clearActions.length === 1,
      toolbar_no_horizontal_overflow: toolbar.scrollWidth <= toolbar.clientWidth + 1 && toolbarRect.right <= innerWidth + 1,
      toolbar_controls_in_viewport: controlsInViewport,
      toolbar_controls_not_overlapping: !controlsOverlap,
      mobile_touch_targets: mobileTouchTargetsPass,
      search_input_usable: Boolean(searchInputRect && searchInputRect.width >= 72 && searchInputRect.height >= 28),
    };
    return {
      checks,
      metrics: {
        viewport_width: width,
        action_bar_count: actionBars.length,
        search_implementation_count: searches.length,
        toolbar_visual_row_count: rowCenters.length,
        column_peer_count: columnRowPeers.length,
        column_declared_region_cells: declaredCells.length,
        declared_context_text_sources_excluded: declaredContextTextSourcesExcluded,
        first_business_content_y: firstContentY,
        repeated_context_tokens: repeatedContext,
        visible_topbar_text_sources: topbarTextSources,
        visible_home_title_canvas: visibleHomeHeader,
        clear_action_labels: clearActions.map((button) => String(button.textContent || '').replace(/\s+/g, '').trim()),
        mobile_mode: mobileMode,
        visible_mobile_selection_control_count: visibleMobileSelectionControls.length,
        mobile_selection_target_sizes: mobileSelectionTargetSizes,
        toolbar_client_width: toolbar.clientWidth,
        toolbar_scroll_width: toolbar.scrollWidth,
        toolbar_rect: { left: toolbarRect.left, right: toolbarRect.right, width: toolbarRect.width },
        toolbar_control_rects: controlRects,
        search_input_rect: searchInputRect ? { left: searchInputRect.left, right: searchInputRect.right, width: searchInputRect.width, height: searchInputRect.height } : null,
        column_decision_trace: columnDecisionTrace,
      },
      observations: {
        desktop_context_text_duplicated: width > 960 && repeatedContext.length > 0,
        visible_home_title_canvas: visibleHomeHeader,
      },
    };
  }, {
    width: viewport.width,
    expectedState: state,
    selectionSource: interaction.selectionSource || 'none',
    selectionNavigationStable: interaction.selectionNavigationStable !== false,
  });
}

async function hasVisibleHomeTitleCanvas(page) {
  return page.evaluate(() => {
    const visible = (element) => {
      if (!(element instanceof HTMLElement)) return false;
      const rect = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      return rect.width > 1 && rect.height > 1 && style.display !== 'none' && style.visibility !== 'hidden';
    };
    return Array.from(document.querySelectorAll('.role-home-surface__header, [data-home-title-canvas]')).some(visible);
  });
}

async function productionComponentProof(page) {
  const surface = page.locator('[data-list-query-action-bar]:visible').first();
  const proof = await surface.evaluate((host) => {
    const toolbar = host.querySelector('[data-list-query-action-bar]');
    const root = toolbar || host;
    const actionBars = Array.from(root.querySelectorAll('.sc-design-action-bar'));
    const searches = Array.from(root.querySelectorAll('input[type="search"]'));
    return {
      fixture: 'runtime_product_list_header_release_surface',
      action_bar_count: actionBars.length,
      search_implementation_count: searches.length,
      search_inside_single_action_bar: actionBars.length === 1 && searches.length === 1 && actionBars[0].contains(searches[0]),
      root_direct_formatting_children: root.children.length,
    };
  });
  await surface.screenshot({ path: path.join(OUTPUT, 'production-component-release-surface.png') });
  return proof;
}

async function negativeProofs(page, viewport) {
  const results = [];
  // A negative fixture only demonstrates that the declared check can fail when
  // the un-injected baseline for that same check is proven normal first. The
  // baseline is recorded per fixture so a dirty baseline is reported as a
  // distinct probe-state defect instead of being credited as detection.
  const baseline = await measure(page, viewport);
  const baselineWithinHeader = baseline.checks.toolbar_controls_within_header === true;
  const baselineAligned = baseline.checks.desktop_actions_query_aligned === true;
  const baselineContextClean = baseline.observations.desktop_context_text_duplicated === false;
  const twoRows = await page.addStyleTag({ content: `
    [data-list-query-action-bar] { position: relative !important; }
    [data-list-query-action-bar] .list-surface-column-manager { transform: translateY(200vh) !important; }
  ` });
  const brokenRows = await measure(page, viewport);
  results.push({
    fixture: 'displaced_controls_outside_shared_header',
    baseline_ok: baselineWithinHeader,
    baseline_metrics: { toolbar_controls_within_header: baseline.checks.toolbar_controls_within_header },
    detected: baselineWithinHeader && brokenRows.checks.toolbar_controls_within_header === false,
    metrics: brokenRows.metrics,
  });
  await twoRows.evaluate((element) => element.remove());

  if (viewport.width >= 1440) {
    const stacked = await page.addStyleTag({ content: '[data-list-query-action-bar] .product-list-header__layout { flex-direction: column !important; align-items: stretch !important; }' });
    const brokenAlignment = await measure(page, viewport);
    results.push({
      fixture: 'desktop_operations_query_stacked',
      baseline_ok: baselineAligned,
      baseline_metrics: { desktop_actions_query_aligned: baseline.checks.desktop_actions_query_aligned },
      detected: baselineAligned && brokenAlignment.checks.desktop_actions_query_aligned === false,
      metrics: brokenAlignment.metrics,
    });
    await stacked.evaluate(element => element.remove());
  }
  const contextDetected = await page.evaluate(() => {
    const subtitle = document.querySelector('#primary-sidebar .brand .subtitle');
    const target = document.querySelector('.topbar-actions');
    if (!subtitle || !target) return false;
    const clone = document.createElement('span');
    clone.dataset.negativeDuplicateContext = 'true';
    clone.textContent = subtitle.textContent || '';
    target.append(clone);
    return true;
  });
  const brokenContext = await measure(page, viewport);
  results.push({
    fixture: 'duplicated_sidebar_context_in_topbar',
    baseline_ok: baselineContextClean,
    baseline_metrics: { desktop_context_text_duplicated: baseline.observations.desktop_context_text_duplicated },
    detected: baselineContextClean && contextDetected && brokenContext.observations.desktop_context_text_duplicated === true,
    metrics: brokenContext.metrics,
  });
  await page.locator('[data-negative-duplicate-context]').evaluateAll((rows) => rows.forEach((row) => row.remove()));

  const hiddenContextInserted = await page.evaluate(() => {
    const subtitle = document.querySelector('#primary-sidebar .brand .subtitle');
    const target = document.querySelector('.topbar-actions');
    if (!subtitle || !target) return false;
    const clone = document.createElement('span');
    clone.dataset.negativeHiddenDuplicateContext = 'true';
    clone.hidden = true;
    clone.textContent = subtitle.textContent || '';
    target.append(clone);
    return true;
  });
  const hiddenContext = await measure(page, viewport);
  results.push({
    fixture: 'hidden_context_text_is_not_visible_duplication',
    baseline_ok: baselineContextClean,
    baseline_metrics: { desktop_context_text_duplicated: baseline.observations.desktop_context_text_duplicated },
    detected: baselineContextClean && hiddenContextInserted && hiddenContext.observations.desktop_context_text_duplicated === false,
    metrics: hiddenContext.metrics,
  });
  await page.locator('[data-negative-hidden-duplicate-context]').evaluateAll((rows) => rows.forEach((row) => row.remove()));

  await page.goto(`${BASE_URL}/`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  await page.locator('[data-role-home]').waitFor({ state: 'visible', timeout: 45_000 });
  const baselineHomeTitleCanvas = await hasVisibleHomeTitleCanvas(page);
  await page.evaluate(() => {
    const home = document.querySelector('[data-role-home]');
    if (!home) return;
    const header = document.createElement('header');
    header.dataset.homeTitleCanvas = 'negative';
    header.style.cssText = 'display:block;min-height:64px;padding:16px';
    header.textContent = '角色首页 / 查看当前账号可处理的事项和可用入口';
    home.prepend(header);
  });
  const brokenHomeDetected = await hasVisibleHomeTitleCanvas(page);
  results.push({
    fixture: 'visible_home_title_canvas',
    baseline_ok: baselineHomeTitleCanvas === false,
    baseline_metrics: { visible_home_title_canvas: baselineHomeTitleCanvas },
    detected: baselineHomeTitleCanvas === false && brokenHomeDetected === true,
  });
  await page.locator('[data-home-title-canvas]').evaluateAll((rows) => rows.forEach((row) => row.remove()));
  return results;
}

async function captureState(page, target, viewport, state) {
  await page.goto(`${BASE_URL}${target.route}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  await waitForList(page);
  if (state !== 'empty') {
    const activeSearch = page.locator(SEARCH_INPUT).first();
    if (await activeSearch.count() && await activeSearch.inputValue()) {
      await submitDeclaredSearch(page, '');
    }
  }
  let selectionSource = 'none';
  let selectionNavigationStable = true;
  if (state === 'empty') {
    await submitDeclaredSearch(page, `structure-empty-${Date.now()}`);
    await page.locator(EMPTY_STATE).first().waitFor({ state: 'visible', timeout: 45_000 });
  } else if (state === 'batch') {
    const mobileMode = await page.locator(`${MOBILE_RECORD_ROW}:visible`).count() > 0;
    // The official selection control is a label wrapping a hidden native input;
    // clicking the input is intercepted, so drive the declared visible control.
    const selectionControl = page.locator(`${mobileMode ? MOBILE_ROW_SELECTION_CONTROL : DESKTOP_ROW_SELECTION_CONTROL}:visible`).first();
    if (await selectionControl.count()) {
      const pathBeforeSelection = page.url();
      await selectionControl.click();
      selectionNavigationStable = page.url() === pathBeforeSelection;
      const toolbarVisible = await page.locator('.list-surface-contextual-toolbar')
        .waitFor({ state: 'visible', timeout: 10_000 }).then(() => true).catch(() => false);
      const selectionState = toolbarVisible ? await selectionControl.getAttribute('data-selection-state') : null;
      selectionSource = selectionState === 'checked'
        ? (mobileMode ? 'visible_mobile' : 'visible_desktop')
        : (mobileMode ? 'missing_visible_mobile' : 'missing_visible_desktop');
    } else {
      selectionSource = mobileMode ? 'missing_visible_mobile' : 'missing_visible_desktop';
    }
  }
  const measurement = await measure(page, viewport, state, { selectionSource, selectionNavigationStable });
  const screenshot = path.join(OUTPUT, `${state}-${viewport.key}.png`);
  await page.screenshot({ path: screenshot, fullPage: true });
  return { state, viewport, measurement, screenshot, selection_source: selectionSource };
}

const browser = await launchChromium({ headless: true });
const context = await browser.newContext({ viewport: VIEWPORTS[0] });
const page = await context.newPage();
const navigation = captureReleasedNavigation(page);
const runtime = { console_errors: [], page_errors: [], failed_responses: [] };
page.on('console', (message) => { if (message.type() === 'error' && !/favicon|ResizeObserver/i.test(message.text())) runtime.console_errors.push(message.text()); });
page.on('pageerror', (error) => runtime.page_errors.push(error.message));
page.on('response', (response) => { if (response.status() >= 400) runtime.failed_responses.push({ status: response.status(), url: response.url() }); });

try {
  await login(page, navigation);
  const target = await findPopulatedList(page, navigation);
  const rows = [];
  for (const viewport of VIEWPORTS) {
    await page.setViewportSize(viewport);
    const states = PHASE === 'current-fail' ? ['normal'] : ['normal', 'batch', 'empty'];
    for (const state of states) rows.push(await captureState(page, target, viewport, state));
  }
  await page.setViewportSize(VIEWPORTS[0]);
  await page.goto(`${BASE_URL}${target.route}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  await waitForList(page);
  const componentProof = await productionComponentProof(page);
  const negativeFixtures = await negativeProofs(page, VIEWPORTS[0]);
  const gatedChecks = new Set([
    'desktop_actions_query_aligned',
    'column_settings_unique',
    'toolbar_present',
    'search_implementation_count',
    'single_action_formatting_context',
    'search_inside_single_action_bar',
    'toolbar_controls_within_header',
    'column_settings_standalone',
    'first_business_content_order',
    'batch_query_coexists',
    'visible_mobile_selection_control',
    'selected_mobile_card_identifiable',
    'mobile_batch_created_without_hidden_desktop_control',
    'mobile_selection_does_not_open_detail',
    'selected_mobile_card_detail_reachable',
    'decision_trace_complete',
    'column_count_not_visible',
    'empty_clear_semantics_unique',
    'toolbar_no_horizontal_overflow',
    'toolbar_controls_in_viewport',
    'toolbar_controls_not_overlapping',
    'mobile_touch_targets',
    'search_input_usable',
  ]);
  const failures = rows.flatMap((row) => Object.entries(row.measurement.checks)
    .filter(([check, passed]) => gatedChecks.has(check) && !passed)
    .map(([check]) => ({ state: row.state, viewport: row.viewport, check, metrics: row.measurement.metrics })));
  for (const fixture of negativeFixtures) {
    if (fixture.baseline_ok === false) {
      failures.push({ state: 'negative-fixture', viewport: VIEWPORTS[0], check: `negative_fixture_baseline_dirty:${fixture.fixture}`, metrics: fixture.baseline_metrics || fixture.metrics });
    }
    if (!fixture.detected) failures.push({ state: 'negative-fixture', viewport: VIEWPORTS[0], check: `negative_fixture_not_detected:${fixture.fixture}` });
  }
  if (!componentProof.search_inside_single_action_bar) {
    failures.push({ state: 'production-component-fixture', viewport: VIEWPORTS[0], check: 'plain_search_inside_single_action_bar', metrics: componentProof });
  }
  const normalRows = rows.filter((row) => row.state === 'normal');
  const factKeys = ['authoritativeColumns', 'enabledColumns', 'explicitVisibility', 'criticalColumns'];
  const baselineTrace = normalRows[0]?.measurement.metrics.column_decision_trace || null;
  const columnAuthorityConsistent = Boolean(baselineTrace) && normalRows.every((row) => {
    const trace = row.measurement.metrics.column_decision_trace;
    return factKeys.every((key) => JSON.stringify(trace?.[key] ?? null) === JSON.stringify(baselineTrace?.[key] ?? null));
  });
  const criticalColumnsReachable = normalRows.every((row) => {
    const trace = row.measurement.metrics.column_decision_trace;
    if (!trace) return false;
    const visibleColumns = row.measurement.metrics.mobile_mode ? trace.mobile?.visibleColumns : trace.desktop?.visibleColumns;
    return Array.isArray(visibleColumns) && (trace.criticalColumns || []).every((field) => visibleColumns.includes(field));
  });
  const aggregateChecks = {
    column_authority_consistent_across_viewports: columnAuthorityConsistent,
    critical_columns_reachable: criticalColumnsReachable,
    decision_trace_complete: normalRows.every((row) => row.measurement.checks.decision_trace_complete === true),
  };
  for (const [check, passed] of Object.entries(aggregateChecks)) {
    if (!passed) failures.push({ state: 'cross-viewport', viewport: null, check, metrics: normalRows.map((row) => ({ viewport: row.viewport.key, trace: row.measurement.metrics.column_decision_trace })) });
  }
  const observations = rows.flatMap((row) => Object.entries(row.measurement.observations || {})
    .filter(([, observed]) => observed)
    .map(([code]) => ({ state: row.state, viewport: row.viewport.key, code, metrics: row.measurement.metrics })));
  const gatedTotal = rows.reduce((total, row) => total + Object.keys(row.measurement.checks).filter((check) => gatedChecks.has(check)).length, 0)
    + Object.keys(aggregateChecks).length + 1;
  const gatedFailed = failures.filter((failure) => failure.state !== 'negative-fixture').length;
  const passed = failures.length === 0 && !runtime.console_errors.length && !runtime.page_errors.length && !runtime.failed_responses.length;
  const report = {
    schema: 'frontend_list_surface_structure_browser.v1',
    phase: PHASE,
    source: { base_url: BASE_URL, database: DATABASE, login: LOGIN, target },
    geometry_contract: 'controls contained by shared header; content follows header within viewport',
    rows,
    production_component_proof: componentProof,
    negative_fixtures: negativeFixtures,
    runtime,
    aggregate_checks: aggregateChecks,
    observations,
    summary: {
      gated: { passed: gatedTotal - gatedFailed, total: gatedTotal, failed: gatedFailed },
      observations: observations.length,
      negative_fixtures: { detected: negativeFixtures.filter((fixture) => fixture.detected).length, total: negativeFixtures.length },
      runtime_errors: runtime.console_errors.length + runtime.page_errors.length + runtime.failed_responses.length,
    },
    failures,
    passed,
  };
  await fs.writeFile(REPORT, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  process.stdout.write(`[frontend_list_surface_structure_browser] ${passed ? 'PASS' : 'FAIL'} phase=${PHASE} rows=${rows.length} failures=${failures.length}\n`);
  if (!passed) process.exitCode = 1;
} finally {
  await context.close();
  await browser.close();
}
