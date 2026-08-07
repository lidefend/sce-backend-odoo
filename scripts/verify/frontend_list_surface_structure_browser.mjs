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
const VIEWPORTS = PHASE === 'current-fail'
  ? [{ key: '1440', width: 1440, height: 900 }]
  : [
      { key: '1440', width: 1440, height: 900 },
      { key: '1024', width: 1024, height: 768 },
      { key: '768', width: 768, height: 1024 },
      { key: '521', width: 521, height: 844 },
      { key: '520', width: 520, height: 844 },
      { key: '390', width: 390, height: 844 },
    ];
const FIRST_CONTENT_LIMITS = { 1440: 165, 1024: 160, 768: 200, 521: 160, 520: 160, 390: 160 };

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

async function findPopulatedList(page, navigation) {
  const routes = actionable(navigation.nav());
  const preferred = routes.filter((row) => /一般合同|项目台账|施工合同/.test(row.label));
  const candidates = [...preferred, ...routes.filter((row) => !preferred.includes(row))];
  for (const target of candidates) {
    await page.goto(`${BASE_URL}${target.route}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
    const toolbar = page.locator('[data-list-query-action-bar]');
    if (!await toolbar.waitFor({ state: 'visible', timeout: 8_000 }).then(() => true).catch(() => false)) continue;
    await waitForList(page);
    if (await page.locator('.table tbody tr, .mobile-record-card').count()) return target;
  }
  throw new Error('no populated runtime list was discovered');
}

async function measure(page, viewport, state = 'normal', interaction = {}) {
  return page.evaluate(({ width, firstContentLimit, expectedState, selectionSource, selectionNavigationStable }) => {
    const visible = (element) => {
      if (!(element instanceof HTMLElement)) return false;
      const rect = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      return rect.width > 1 && rect.height > 1 && style.display !== 'none' && style.visibility !== 'hidden';
    };
    const toolbar = document.querySelector('[data-list-query-action-bar]');
    const contextualToolbar = document.querySelector('.list-surface-contextual-toolbar');
    const mobileCards = Array.from(document.querySelectorAll('[data-mobile-record-row], .mobile-record-card')).filter(visible);
    const mobileMode = mobileCards.length > 0;
    const visibleMobileSelectors = Array.from(document.querySelectorAll('[data-mobile-record-select] input[type="checkbox"]')).filter(visible);
    const visibleMobileSelectionTargets = visibleMobileSelectors
      .map((control) => control.closest('[data-mobile-record-select]'))
      .filter(visible);
    const mobileSelectionTargetSizes = visibleMobileSelectionTargets.map((target) => {
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
      const controls = Array.from(contextualToolbar?.querySelectorAll('button, input, select') || []).filter(visible);
      const rowCenters = [];
      for (const control of controls) {
        const center = control.getBoundingClientRect().top + control.getBoundingClientRect().height / 2;
        if (!rowCenters.some((value) => Math.abs(value - center) <= 6)) rowCenters.push(center);
      }
      const tableContent = Array.from(document.querySelectorAll('.table > .sc-table-shell, .table > .grouped-table')).find(visible);
      const cardContent = Array.from(document.querySelectorAll('.mobile-record-card')).find(visible);
      const firstContent = tableContent || cardContent;
      const firstContentY = visible(firstContent) ? firstContent.getBoundingClientRect().top : null;
      return {
        checks: {
          toolbar_present: visible(contextualToolbar),
          batch_toolbar_replaces_normal: visible(contextualToolbar) && !visible(toolbar),
          toolbar_visual_row_count: rowCenters.length === 1,
          first_business_content_y: firstContentY !== null && firstContentY <= firstContentLimit,
          visible_mobile_selection_control: !mobileMode || (visibleMobileSelectors.length > 0 && mobileSelectionTargetsMeetSize),
          selected_mobile_card_identifiable: !mobileMode || (selectedMobileCards.length > 0 && visibleMobileSelectors.some((control) => control.checked)),
          mobile_batch_created_without_hidden_desktop_control: !mobileMode || selectionSource === 'visible_mobile',
          mobile_selection_does_not_open_detail: !mobileMode || selectionNavigationStable,
          selected_mobile_card_detail_reachable: !mobileMode || selectedMobileCards.some((card) => visible(card.querySelector('.mobile-record-card'))),
          decision_trace_complete: expectedState === 'empty' || traceComplete,
        },
        metrics: {
          viewport_width: width,
          contextual_control_count: controls.length,
          toolbar_visual_row_count: rowCenters.length,
          first_business_content_y: firstContentY,
          first_business_content_limit: firstContentLimit,
          mobile_mode: mobileMode,
          visible_mobile_selection_control_count: visibleMobileSelectors.length,
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
    const columnButton = toolbar.querySelector('.list-surface-column-button');
    const columnCenter = visible(columnButton)
      ? columnButton.getBoundingClientRect().top + columnButton.getBoundingClientRect().height / 2
      : null;
    const columnPeers = columnCenter === null ? [] : controls.filter((control) => (
      control !== columnButton
      && Math.abs(control.getBoundingClientRect().top + control.getBoundingClientRect().height / 2 - columnCenter) <= 6
    ));
    const table = Array.from(document.querySelectorAll('.table > .sc-table-shell, .table > .grouped-table')).find(visible);
    const firstCard = Array.from(document.querySelectorAll('.mobile-record-card')).find(visible);
    const emptyState = document.querySelector('.sc-empty, .list-empty-state');
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
    if (topbarActions) {
      const walker = document.createTreeWalker(topbarActions, NodeFilter.SHOW_TEXT);
      for (let node = walker.nextNode(); node; node = walker.nextNode()) {
        const text = String(node.nodeValue || '').replace(/\s+/g, ' ').trim();
        const parent = node.parentElement;
        if (!text || !parent) continue;
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
    const searchInputRect = searches[0]?.getBoundingClientRect();
    const checks = {
      toolbar_present: true,
      search_implementation_count: searches.length === 1,
      single_action_formatting_context: actionBars.length === 1,
      search_inside_single_action_bar: searchInsideSingleActionBar,
      toolbar_visual_row_count: rowCenters.length === 1,
      column_settings_standalone: !visible(columnButton) || columnPeers.length > 0,
      first_business_content_y: firstContentY !== null && firstContentY <= firstContentLimit,
      visible_mobile_selection_control: expectedState !== 'normal' || !mobileMode || (visibleMobileSelectors.length > 0 && mobileSelectionTargetsMeetSize),
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
        column_peer_count: columnPeers.length,
        first_business_content_y: firstContentY,
        first_business_content_limit: firstContentLimit,
        repeated_context_tokens: repeatedContext,
        visible_topbar_text_sources: topbarTextSources,
        visible_home_title_canvas: visibleHomeHeader,
        clear_action_labels: clearActions.map((button) => String(button.textContent || '').replace(/\s+/g, '').trim()),
        mobile_mode: mobileMode,
        visible_mobile_selection_control_count: visibleMobileSelectors.length,
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
    firstContentLimit: FIRST_CONTENT_LIMITS[viewport.width],
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
  const twoRows = await page.addStyleTag({ content: `
    [data-list-query-action-bar] { min-height: 100px !important; }
    [data-list-query-action-bar] .list-surface-column-manager { transform: translateY(52px) !important; }
  ` });
  const brokenRows = await measure(page, viewport);
  results.push({ fixture: 'forced_second_row_and_standalone_column_settings', detected: !brokenRows.checks.toolbar_visual_row_count && !brokenRows.checks.column_settings_standalone, metrics: brokenRows.metrics });
  await twoRows.evaluate((element) => element.remove());

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
  results.push({ fixture: 'duplicated_sidebar_context_in_topbar', detected: contextDetected && brokenContext.observations.desktop_context_text_duplicated, metrics: brokenContext.metrics });
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
  results.push({ fixture: 'hidden_context_text_is_not_visible_duplication', detected: hiddenContextInserted && !hiddenContext.observations.desktop_context_text_duplicated, metrics: hiddenContext.metrics });
  await page.locator('[data-negative-hidden-duplicate-context]').evaluateAll((rows) => rows.forEach((row) => row.remove()));

  await page.goto(`${BASE_URL}/`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  await page.locator('[data-role-home]').waitFor({ state: 'visible', timeout: 45_000 });
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
  results.push({ fixture: 'visible_home_title_canvas', detected: brokenHomeDetected });
  await page.locator('[data-home-title-canvas]').evaluateAll((rows) => rows.forEach((row) => row.remove()));
  return results;
}

async function captureState(page, target, viewport, state) {
  await page.goto(`${BASE_URL}${target.route}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  await waitForList(page);
  if (state !== 'empty') {
    const activeSearch = page.locator('[data-list-query-action-bar] input[type="search"]:visible').first();
    if (await activeSearch.count() && await activeSearch.inputValue()) {
      await activeSearch.fill('');
      await activeSearch.press('Enter');
      await waitForList(page);
    }
  }
  let selectionSource = 'none';
  let selectionNavigationStable = true;
  if (state === 'empty') {
    const search = page.locator('[data-list-query-action-bar] input[type="search"]:visible').first();
    await search.fill(`structure-empty-${Date.now()}`);
    await search.press('Enter');
    await page.locator('.sc-empty, .list-empty-state').first().waitFor({ state: 'visible', timeout: 45_000 });
  } else if (state === 'batch') {
    const mobileMode = await page.locator('[data-mobile-record-row]:visible, .mobile-record-card:visible').count() > 0;
    const checkbox = mobileMode
      ? page.locator('[data-mobile-record-select] input[type="checkbox"]:visible').first()
      : page.locator('.table tbody input[type="checkbox"]:visible').first();
    if (await checkbox.count()) {
      const pathBeforeSelection = page.url();
      await checkbox.check();
      selectionNavigationStable = page.url() === pathBeforeSelection;
      selectionSource = mobileMode ? 'visible_mobile' : 'visible_desktop';
      await page.locator('.list-surface-contextual-toolbar').waitFor({ state: 'visible', timeout: 10_000 });
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
    'toolbar_present',
    'search_implementation_count',
    'single_action_formatting_context',
    'search_inside_single_action_bar',
    'toolbar_visual_row_count',
    'column_settings_standalone',
    'first_business_content_y',
    'batch_toolbar_replaces_normal',
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
    thresholds: { first_business_content_y: FIRST_CONTENT_LIMITS },
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
