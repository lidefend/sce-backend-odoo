#!/usr/bin/env node

import fs from 'node:fs/promises';
import path from 'node:path';
import { launchChromium, launchAcceptanceChromium } from './playwright_runtime.mjs';
import { captureReleasedNavigation } from './released_navigation_target.mjs';
import { resolveAcceptanceEnvironment, verifyServedIdentity, redactedEnvironmentEvidence } from './lib/frontend_acceptance_environment.mjs';

const acceptance = resolveAcceptanceEnvironment({ tool: 'geometry-scroll-audit' });
import { acquireAcceptanceLease } from './lib/frontend_acceptance_lease.mjs';
import { DEFAULT_RECEIPT_PATH, assertContractPrerequisite, observedContractBinding, readContractReceipt } from './lib/acceptance_contract_receipt.mjs';
const DAILY = acceptance.profile === 'daily';
const DAILY_OBSERVATION_SCOPE = process.env.LIST_SURFACE_DAILY_OBSERVATION_SCOPE || 'all';
const DAILY_SCOPES = ['all', 'record-only', 'detail-only', 'workbench-only', 'form-profiles'];
if ((!DAILY && DAILY_OBSERVATION_SCOPE !== 'all') || !DAILY_SCOPES.includes(DAILY_OBSERVATION_SCOPE)) throw new Error('unknown daily observation scope');
// Scope variants reuse this one governed tool instead of adding a new framework:
//   all            -> declared landing + workspace home + list matrix + record read-only walk
//   workbench-only -> declared landing + workspace home only
//   form-profiles  -> declared create/edit/readonly entry + renderer consumption only
const WORKBENCH_ONLY = DAILY && DAILY_OBSERVATION_SCOPE === 'workbench-only';
const FORM_PROFILES_ONLY = DAILY && DAILY_OBSERVATION_SCOPE === 'form-profiles';
// Resolved at module scope so the failure handler can report the list execution
// state even when the run aborts before the observation scopes are reached.
// Referencing a later `const` from the handler would throw a TDZ ReferenceError
// and mask the real failure.
const LIST_MATRIX_SKIPPED = WORKBENCH_ONLY || FORM_PROFILES_ONLY || (DAILY && DAILY_OBSERVATION_SCOPE === 'detail-only');
const dailyRuntime = DAILY ? await (async () => {
  const { build } = await import('../../frontend/apps/web/node_modules/esbuild/lib/main.js');
  const bundled = await build({ stdin: { contents: "export * from './app/runtime/recordEntryContract'; export * from './app/routeQuery'; export * from './app/resolvers/sceneRegistry';", resolveDir: path.join(acceptance.root, 'frontend/apps/web/src'), loader: 'ts' }, bundle: true, platform: 'node', format: 'esm', define: { 'import.meta.env.DEV': 'false' }, write: false });
  return import(`data:text/javascript;base64,${Buffer.from(bundled.outputFiles[0].text).toString('base64')}`);
})() : null;
const BASE_URL = acceptance.baseUrl;
const DATABASE = acceptance.database;
const LOGIN = DAILY ? acceptance.login : process.env.E2E_LOGIN || acceptance.login || acceptance.roleBindings.project_manager || '';
const PASSWORD = DAILY ? acceptance.password : process.env.E2E_PASSWORD || acceptance.password || process.env.SC_ACCEPTANCE_FIXTURE_PASSWORD || '';
const BOOTSTRAP_SECRET = DAILY ? '' : process.env.SC_ACCEPTANCE_BOOTSTRAP_SECRET || '';
const PHASE = String(process.env.LIST_SURFACE_PHASE || 'full');
const COLOR_SCHEME = String(process.env.LIST_SURFACE_COLOR_SCHEME || '').trim().toLowerCase();
if (COLOR_SCHEME && !['light', 'dark'].includes(COLOR_SCHEME)) throw new Error('unknown LIST_SURFACE_COLOR_SCHEME');
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
const requestedWidths = String(process.env.LIST_SURFACE_VIEWPORTS || (DAILY ? '1440,390' : '')).split(',').filter(Boolean);
if (requestedWidths.some(width => !DEFAULT_VIEWPORTS.some(viewport => viewport.key === width))) throw new Error('unknown LIST_SURFACE_VIEWPORTS');
const VIEWPORTS = requestedWidths.length ? DEFAULT_VIEWPORTS.filter(viewport => requestedWidths.includes(viewport.key)) : DEFAULT_VIEWPORTS;
let REQUESTED_ROUTE = String(process.env.LIST_SURFACE_ROUTE || '').trim();
if (REQUESTED_ROUTE && !/^\/a\/\d+\?menu_id=\d+$/.test(REQUESTED_ROUTE)) throw new Error('LIST_SURFACE_ROUTE must identify exact action/menu');

if (!LOGIN || (!PASSWORD && !BOOTSTRAP_SECRET)) {
  throw new Error('acceptance login and password or isolated bootstrap secret are required');
}

// The list/detail probe must not assert anything about a contract the backend has
// not certified at the served revision. Validate the declared prerequisite before
// the browser is launched, i.e. before any DOM interaction or assertion.
const CONTRACT_RECEIPT_PATH = path.resolve(process.env.SC_ACCEPTANCE_CONTRACT_RECEIPT || DEFAULT_RECEIPT_PATH);
const CONTRACT_DECLARATION_PATH = path.resolve(process.env.SC_ACCEPTANCE_CONTRACT_DECLARATION || 'config/acceptance/backend_contract_instance_v1.json');
// The declared instance receipt names one exact runtime (config/acceptance/
// backend_contract_instance_v1.json: database + fixture account). The daily
// profile resolves to its own declared environment (config/frontend/
// acceptance_environments_v1.json profiles.daily), so it must never be bound to
// that receipt implicitly: a lane is contract-bound only when it explicitly
// declares the requirement and a receipt for its own runtime.
const REQUIRE_CONTRACT = ['1', 'true', 'yes'].includes(String(process.env.SC_ACCEPTANCE_REQUIRE_CONTRACT || '').toLowerCase());
const contractGate = { required: REQUIRE_CONTRACT, profile: acceptance.profile, status: REQUIRE_CONTRACT ? 'not_evaluated' : 'not_required_for_profile',
  receipt: CONTRACT_RECEIPT_PATH, declaration: CONTRACT_DECLARATION_PATH,
  approved: null, approved_request: null, approved_route: '', binding: null };
if (REQUIRE_CONTRACT) {
  let declaration;
  try {
    declaration = JSON.parse(await fs.readFile(CONTRACT_DECLARATION_PATH, 'utf8'));
  } catch (error) {
    throw new Error(`contract prerequisite failed: contract_declaration_unavailable (${CONTRACT_DECLARATION_PATH})`);
  }
  const account = declaration?.account && typeof declaration.account === 'object' ? declaration.account : {};
  const { receipt, error: receiptError } = readContractReceipt(CONTRACT_RECEIPT_PATH);
  const verdict = assertContractPrerequisite({
    receipt, loadError: receiptError,
    expectedSha: String(acceptance.provenance?.expectedSha || ''),
    database: DATABASE, login: String(account.login || LOGIN || '').trim(),
    roleCode: String(account.role_code || '').trim(), companyName: String(account.company_name || '').trim(),
  });
  contractGate.status = 'accepted';
  // The prerequisite verdict is the object shape the shared binding check reads
  // (schemaSha256 / definition / authority / approved / approvedSemanticSha256).
  // Keep the verdict itself so the live replay is compared against the exact
  // approved contract rather than a re-keyed subset of it.
  contractGate.verdict = verdict;
  contractGate.approved = verdict.approved;
  contractGate.approved_request = verdict.approvedRequest;
  contractGate.approved_semantic_sha256 = verdict.approvedSemanticSha256;
  contractGate.approved_route = verdict.approved.route;
  contractGate.schema_sha256 = verdict.schemaSha256;
  contractGate.identity = verdict.identity;
  if (!verdict.identity.login || String(LOGIN || '').trim() !== verdict.identity.login) {
    throw new Error(`contract prerequisite failed: contract_receipt_actor_mismatch ${JSON.stringify({ receipt: verdict.identity.login, runtime: String(LOGIN || '').trim() })}`);
  }
  // The approved record is opened through the declared list authority; the probe
  // must not drift to another list or to the first row of whatever renders.
  if (REQUESTED_ROUTE && REQUESTED_ROUTE !== contractGate.approved_route) {
    throw new Error(`LIST_SURFACE_ROUTE ${REQUESTED_ROUTE} does not match the approved contract target ${contractGate.approved_route}`);
  }
  REQUESTED_ROUTE = contractGate.approved_route;
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
// Declared record openers. Desktop rows expose the primary-link cell; mobile rows
// expose the explicit `open-record` action. The mobile card body is the selection
// surface, not a declared opener, so it must not be used as the detail entry.
const DESKTOP_RECORD_OPENER = '.cell-primary-link:visible';
const MOBILE_RECORD_OPENER = '[data-semantic-action="open-record"]:visible';
const DECLARED_RECORD_OPENER = `${DESKTOP_RECORD_OPENER}, ${MOBILE_RECORD_OPENER}`;
const ROW_SELECTION_CONTROL = '.collection-selection-control[data-selection-scope="row"]';
// Declared semantic identity contract (scripts/verify/frontend_primitive_adapter_guard.py):
// `data-semantic-component` names the component that OWNS the node, so a consumer
// declaration on a primitive root wins; the primitive itself is published
// unconditionally as `data-semantic-primitive`. "A product card was rendered" is
// therefore the declared primitive marker, never the owning-component name.
const CARD_PRIMITIVE_SELECTOR = '[data-semantic-primitive="ScCard"]';
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
  // The declared daily target is an external deployment reached over the
  // network: its first navigation loads the released bundle and menu tree, so
  // the list toolbar can take well over the loopback tuning used for local
  // runs. Only three candidates are probed on daily, so each one gets a
  // realistic budget instead of being abandoned before the surface renders.
  const toolbarTimeout = REQUESTED_ROUTE ? 45_000 : (DAILY ? 30_000 : 8_000);
  for (const target of (DAILY ? candidates.slice(0, 3) : candidates)) {
    await page.goto(`${BASE_URL}${target.route}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
    const toolbar = page.locator('[data-list-query-action-bar]');
    if (!await toolbar.waitFor({ state: 'visible', timeout: toolbarTimeout }).then(() => true).catch(() => false)) continue;
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

function dailyReadonlyRequest(method, pathname, body) {
  if (['GET', 'HEAD', 'OPTIONS'].includes(method)) return true;
  if (method !== 'POST') return false;
  if (pathname === '/web/session/authenticate') return true;
  if (pathname !== '/api/v1/intent') return false;
  if (!body || typeof body !== 'object' || Array.isArray(body)) return false;
  if (body.intent === 'api.data') {
    const readOps = ['list', 'read', 'search', 'search_read', 'query', 'name_search', 'fields_get', 'default_get'];
    const op = body.params?.op || body.params?.operation;
    if (!readOps.includes(op)) return false;
    const carriers = [body, body.params];
    for (let index = 0; index < carriers.length; index += 1) {
      const carrier = carriers[index];
      if (!carrier || typeof carrier !== 'object' || Array.isArray(carrier)) continue;
      if (['op', 'operation'].some(key => carrier[key] !== undefined && carrier[key] !== op)) return false;
      for (const key of ['payload', 'params', 'data', 'args', '_params', '_payload']) {
        if (carrier[key] && typeof carrier[key] === 'object') carriers.push(carrier[key]);
      }
      if (carriers.length > 32) return false;
    }
    return true;
  }
  return ['login', 'auth.login', 'system.init', 'ui.contract', 'ui.contract.v2', 'my.work.summary', 'load_view', 'load_contract', 'action.view', 'app.init', 'session.info', 'session.bootstrap', 'sys.intents', 'route.authority.validate', 'record.context.search', 'user.view.preference.get', 'chatter.timeline', 'chatter.followers.list', 'global.message.conversations', 'global.message.inbox', 'file.download', 'telemetry.track', 'usage.track'].includes(body.intent);
}

function dailyDeclaredLanding(init) {
  if (init?.scene_ready_contract?.scenes?.length) dailyRuntime.setSceneRegistryFromSceneReadyContract(init.scene_ready_contract);
  else dailyRuntime.setSceneRegistry(Array.isArray(init?.scenes) ? init.scenes : []);
  const availablePath = raw => {
    const route = dailyRuntime.normalizeLegacyWorkbenchPath(String(raw || '').trim());
    if (!route.startsWith('/') || route.startsWith('//')) return '';
    const match = route.match(/^\/s\/([^/?#]+)/);
    return !match || dailyRuntime.getSceneByKey(decodeURIComponent(match[1])) ? route : '';
  };
  const scenePath = raw => {
    const key = String(raw || '').trim();
    const scene = dailyRuntime.getSceneByKey(key);
    return scene ? availablePath(scene.target?.route || scene.route || `/s/${key}`) || `/s/${key}` : '';
  };
  const role = init?.role_surface || {};
  const fallback = init?.default_route || {};
  const choices = [
    ['role_surface.landing_path', availablePath(role.landing_path)],
    ['role_surface.landing_scene_key', scenePath(role.landing_scene_key)],
    ['default_route.route', /^\/(a|f|r)\//.test(String(fallback.route || '')) ? '' : availablePath(fallback.route)],
    ['default_route.scene_key', scenePath(fallback.scene_key)],
  ];
  const [owner, route] = choices.find(([, candidate]) => candidate) || ['minimum_workspace_fallback', '/'];
  const sceneKey = route.match(/^\/s\/([^/?#]+)/)?.[1];
  return { route, scene_key: sceneKey ? decodeURIComponent(sceneKey) : route.split('?')[0] === '/' ? 'workspace.home' : '', owner };
}

function dailyRecordEntry(snapshot, row, source) {
  const action = snapshot?.actionContract?.actionRuleList?.find(rule => rule.sourceWidgetId === 'page.row');
  if (!action) throw new Error('list contract has no declared row opener');
  const materialize = value => typeof value === 'string' ? value.replace(/\$\{([A-Za-z_][A-Za-z0-9_]*)\}/g, (_, key) => String(row[key] ?? ''))
    : Array.isArray(value) ? value.map(materialize)
      : value && typeof value === 'object' ? Object.fromEntries(Object.entries(value).map(([key, item]) => [key, materialize(item)])) : value;
  const target = materialize(action.target || {});
  const formal = dailyRuntime.decodeFormalRecordEntry(target.record_entry);
  if (!formal && (Object.values(target).some(value => value && typeof value === 'object') || target.route)) throw new Error('unsupported non-record row target');
  const entry = formal || dailyRuntime.recordEntryFromModelRights({ model: snapshot.pageInfo.model, recordId: row.id,
    modelRights: snapshot.statusContract?.globalStatus?.modelRights, actionId: source.actionId, menuId: source.menuId });
  const resolved = dailyRuntime.resolveRecordOpenTarget({ ...entry, actionId: entry.actionId || source.actionId,
    menuId: entry.menuId || source.menuId, carryQuery: { action_id: source.actionId, menu_id: source.menuId } });
  if (!resolved) throw new Error('invalid declared record entry');
  return { model: entry.model, recordId: Number(entry.recordId), actionId: Number(resolved.query.action_id),
    menuId: Number(resolved.query.menu_id), path: resolved.path, modelWriteAuthority: entry.modelWriteAuthority, entryIntent: entry.entryIntent };
}

function dailyLandingMatches(currentUrl, defaultRoute, baseUrl) {
  if (!defaultRoute || typeof defaultRoute.route !== 'string' || !defaultRoute.route.startsWith('/') || defaultRoute.route.startsWith('//')) return false;
  const expected = new URL(defaultRoute.route, baseUrl);
  const current = new URL(currentUrl, baseUrl);
  return current.origin === expected.origin && current.pathname === expected.pathname
    && [...expected.searchParams].every(([key, value]) => current.searchParams.get(key) === value);
}

function dailyHomeSummaryMatches(row) {
  return row.intent === 'my.work.summary' && row.params?.product_workspace === true
    && row.params?.limit === 12 && row.params?.limit_each === 4 && row.params?.page_size === 12
    && row.params?.page === 1 && row.params?.sort_by === 'priority' && row.params?.sort_dir === 'desc'
    && (row.response?.ok === true || row.response?.result?.ok === true);
}

function dailyDetailContractMatches(row, expected) {
  const envelope = row.response?.result?.ok !== undefined ? row.response.result : row.response;
  return row.intent === 'ui.contract.v2' && envelope?.ok === true
    && envelope.data?.pageInfo?.model === expected.model
    && envelope.data?.pageInfo?.viewType === 'form'
    && Number(envelope.data?.dataContract?.mainData?.id) === expected.recordId
    && Number(row.params?.record_id) === expected.recordId
    && Number(row.params?.action_id) === expected.actionId
    && Number(row.params?.menu_id) === expected.menuId;
}

// ContractFormPage's ordinary renderer is ContractFormDriverHost. The native
// canvas is a configuration/designer branch, not the record-page ready marker.
function dailyActorContext(init) {
  const positiveId = value => Number.isSafeInteger(value) && value > 0 ? value : null;
  return { source: 'captured_system_init', user_id: positiveId(init?.user?.id),
    role_codes: Array.isArray(init?.role_surface?.role_codes) ? init.role_surface.role_codes.filter(role => typeof role === 'string') : [],
    company_id: positiveId(init?.record_context?.company_id) };
}

function dailyContractEvidenceRef(contracts, row) {
  const index = contracts.indexOf(row);
  if (index < 0) throw new Error('contract evidence reference is not captured');
  const envelope = row.response?.result?.ok !== undefined ? row.response.result : row.response;
  return { response_index: index, intent: row.intent,
    trace_id: typeof envelope?.meta?.trace_id === 'string' ? envelope.meta.trace_id : null,
    contract_version: envelope?.data?.meta?.contract_version ?? envelope?.meta?.contract_version ?? null };
}

function dailyRecordPresentation(contract, expected) {
  const profile = contract?.statusContract?.globalStatus?.effectiveRenderProfile;
  if (!['readonly', 'edit', 'create'].includes(profile)) throw new Error('unsupported declared record profile');
  if (contract?.pageInfo?.model !== expected.model || contract?.pageInfo?.viewType !== 'form') throw new Error('record presentation identity mismatch');
  const isNew = expected.path === `/f/${expected.model}/new`;
  if (isNew ? profile !== 'create' : (profile === 'create' || Number(contract?.dataContract?.mainData?.id) !== expected.recordId)) throw new Error('record profile does not match record identity');
  if (!isNew && ![`/f/${expected.model}/${expected.recordId}`, `/r/${expected.model}/${expected.recordId}`].includes(expected.path)) throw new Error('unexpected record route');
  if (expected.path.startsWith('/r/') && profile !== 'readonly') throw new Error('readonly route cannot render an editable profile');
  return { profile, record: isNew ? 'new' : String(expected.recordId),
    rootSelector: '[data-product-page-mode="form"][data-form-model]',
    driverSelector: '[data-contract-form-driver]',
    patternSelector: `[data-product-page-pattern="workspace-form"][data-render-profile="${profile}"], [data-product-page-pattern="task-form"][data-render-profile="${profile}"]` };
}

function dailyRecordDomMatches(observed, declaration, expected) {
  return observed.model === expected.model && observed.record === declaration.record
    && Number(observed.action) === expected.actionId && Number(observed.menu) === expected.menuId
    && observed.driverCount === 1 && observed.patternCount === 1 && observed.driverErrorCount === 0
    && observed.profile === declaration.profile && observed.cards > 0
    && (declaration.profile !== 'readonly' || observed.detailAdopted !== 'true' || observed.detailCards > 0);
}

function dailyRecordCheckSummary(checks, viewports, contractStatus = 'accepted', scope = 'all') {
  // The expected record-walk shape follows the scope that actually ran, never a
  // single hard-coded form:
  //   form-profiles -> declared create/edit entry + their consumed form contract
  //                    + the rendered profile
  //   workbench-only -> there is no record walk at all, so the summary must not
  //                    demand record steps (the workbench block asserts itself)
  //   other scopes  -> the record walk, with the approved-contract-binding step
  //                    only when the lane runs under an accepted sealed contract
  const stepsByScope = {
    'form-profiles': ['declared_create_entry', 'create_contract', 'create_renderer',
      'declared_edit_entry', 'edit_contract', 'edit_renderer'],
  };
  const recordSteps = contractStatus === 'accepted'
    ? ['declared_entry_route', 'exact_record_contract', 'approved_contract_binding', 'declared_renderer', 'return_to_source']
    : ['declared_entry_route', 'exact_record_contract', 'declared_renderer', 'return_to_source'];
  const steps = scope === 'workbench-only' ? [] : (stepsByScope[scope] || recordSteps);
  const expected = viewports.flatMap(viewport => steps.map(check => `${viewport.key}:${check}`));
  // A step is satisfied only by its own row. An explicitly not-applicable row
  // (declared authority absent) is the only accepted alternative, so a missing
  // row still fails and an empty expected set is reported as zero coverage.
  const satisfied = checks.filter(row => row.passed === true || row.not_applicable === true)
    .map(row => `${row.viewport}:${row.check}`);
  const complete = steps.length === 0
    ? checks.length === 0
    : viewports.length > 0 && expected.every(key => satisfied.filter(value => value === key).length === 1) && satisfied.length === expected.length;
  return { passed: satisfied.length, total: expected.length, complete, expected };
}

// The declared create entry is a route: ActionView.openCreateRecord pushes
// /f/<model>/new and the entry capability is consumed from the list contract.
// Bind the assertion to the declared model + consumed contract, not to a
// rendered control, so a renamed button cannot pass or fail the check.
function dailyCreateContractMatches(row, expected) {
  const envelope = row.response?.result?.ok !== undefined ? row.response.result : row.response;
  return row.intent === 'ui.contract.v2' && envelope?.ok === true
    && envelope.data?.pageInfo?.model === expected.model
    && envelope.data?.pageInfo?.viewType === 'form';
}

function dailyCreateDomMatches(observed, expected) {
  return observed.model === expected.model && observed.record === 'new'
    && observed.driverCount === 1 && observed.patternCount === 1 && observed.driverErrorCount === 0
    && observed.profile === 'create' && observed.cards > 0;
}

// One shared capture of the declared record renderer, used by the record walk
// and the create/edit profile walk. It asserts the declared root, driver and
// render-profile marker are actually rendered before reading their data.
async function captureRecordPresentation(page, declaration) {
  const root = page.locator(declaration.rootSelector).filter({ has: page.locator(declaration.driverSelector) });
  await root.waitFor({ state: 'visible', timeout: 30_000 });
  await root.locator(declaration.patternSelector).waitFor({ state: 'visible', timeout: 30_000 });
  return root.evaluate((node, declared) => {
    const visible = item => Boolean(item && item.getBoundingClientRect().width > 0 && item.getBoundingClientRect().height > 0);
    const patterns = [...node.querySelectorAll(declared.patternSelector)].filter(visible);
    return { model: node.dataset.formModel, record: node.dataset.formRecord,
      action: node.dataset.formActionId, menu: node.dataset.formMenuId,
      driverCount: [...node.querySelectorAll(declared.driverSelector)].filter(visible).length,
      patternCount: patterns.length, profile: patterns[0]?.dataset.renderProfile,
      driverErrorCount: node.querySelectorAll('[data-contract-form-driver-error]').length,
      detailAdopted: node.dataset.detailCompositionAdopted,
      // Public-surface equivalents of the card class selectors; the
      // ScCard semantic marker covers every rendered product card.
      detailCards: [...node.querySelectorAll('[data-semantic-component="ScCard"][data-detail-card], [data-detail-card] > [data-semantic-component="ScCard"]')].filter(visible).length,
      cards: [...node.querySelectorAll('[data-semantic-component="ScCard"]')].filter(visible).length };
  }, declaration);
}

function safeFailedResponse(status, url, request, response, secrets = []) {
  const safeUrl = new URL(url);
  const result = { status, url: safeUrl.origin + safeUrl.pathname };
  if (safeUrl.pathname !== '/api/v1/intent') return result;
  const clean = value => typeof value === 'string' ? secrets.filter(Boolean).reduce((text, secret) => text.split(secret).join('[redacted]'), value)
    .replace(/(?:password|token|secret|authorization)\s*[=:]\s*[^\s,;]+/gi, '[redacted]').slice(0, 320) : undefined;
  const intent = clean(request?.intent);
  if (intent) result.intent = intent;
  // Never copy request bodies/context/login parameters or arbitrary error data.
  if (intent !== 'login') {
    const params = request?.params || {};
    for (const key of ['op', 'model']) if (typeof params[key] === 'string') result[key] = clean(params[key]);
    for (const key of ['record_id', 'res_id', 'action_id', 'menu_id', 'id']) {
      if (/^[1-9]\d*$/.test(String(params[key] ?? '')) && Number.isSafeInteger(Number(params[key]))) result[key] = Number(params[key]);
    }
  }
  const envelope = response?.result?.error ? response.result : response;
  const error = envelope?.error;
  if (error && typeof error === 'object') {
    result.error = {};
    for (const key of ['code', 'reason_code', 'message', 'trace_id']) {
      if (typeof error[key] === 'string') result.error[key] = clean(error[key]);
      else if (typeof error[key] === 'number') result.error[key] = error[key];
    }
    if (typeof envelope?.meta?.trace_id === 'string') result.error.trace_id = clean(envelope.meta.trace_id);
  }
  return result;
}

let browser, context, page, lease, servedIdentity;
const runtime = { console_errors: [], page_errors: [], failed_responses: [], denied_requests: [], operational_tracking: [], contracts: [] };
const dailyObservations = [];
const acceptanceScope = { authority: 'actual captured account/company contract consumption',
  not_run: ['other_roles_or_companies', 'per_button_authorization', 'backend_rejection_of_forbidden_write', 'submit_approval_lifecycle'],
  policy_boundary: 'DOM contract consistency is not independent proof of authorization policy correctness' };
const rows = [];
const recordChecks = [];
let target = null;
let actorContext = null;
const responseTasks = new Set();
try {
  if (DAILY) {
    if (acceptance.operation !== 'readonly' || acceptance.target.mode !== 'external' || acceptance.apiUrl !== BASE_URL || !LOGIN || !PASSWORD) throw new Error('daily scope requires exact external readonly target and credentials');
    servedIdentity = await verifyServedIdentity(acceptance);
    if (servedIdentity.servedDatabase !== DATABASE) throw new Error('daily served database identity is required and must match');
    lease = await acquireAcceptanceLease({ environment: acceptance, mode: 'shared-read', owner: { tool: 'geometry-scroll-audit' } });
  }
  browser = DAILY ? await launchAcceptanceChromium(acceptance, { headless: true }) : await launchChromium({ headless: true });
  context = await browser.newContext({ viewport: VIEWPORTS[0], ...(COLOR_SCHEME ? { colorScheme: COLOR_SCHEME } : {}) });
  if (DAILY) await context.route('**/*', async route => {
    const request = route.request();
    const url = new URL(request.url());
    let body; try { body = request.postDataJSON(); } catch {}
    const sameOrigin = url.origin === new URL(BASE_URL).origin;
    if (!sameOrigin || !dailyReadonlyRequest(request.method(), url.pathname, body)) {
      runtime.denied_requests.push({ method: request.method(), path: url.pathname, intent: body?.intent || '' });
      return route.abort('blockedbyclient');
    }
    if (['telemetry.track', 'usage.track'].includes(body?.intent)) runtime.operational_tracking.push({ intent: body.intent, classification: 'runtime_telemetry_not_business_write' });
    return route.continue();
  });
  page = await context.newPage();
  const navigation = captureReleasedNavigation(page);
  page.on('console', message => { if (message.type() === 'error' && !/favicon|ResizeObserver/i.test(message.text())) runtime.console_errors.push(message.text()); });
  page.on('pageerror', error => runtime.page_errors.push(error.message));
  page.on('response', response => {
    const task = (async () => {
      let request, envelope;
      const isIntent = new URL(response.url()).pathname === '/api/v1/intent';
      if (isIntent) {
        try { request = response.request().postDataJSON(); } catch {}
        try { envelope = await response.json(); } catch {}
      }
      if (response.status() >= 400) runtime.failed_responses.push(safeFailedResponse(response.status(), response.url(), request, envelope, [PASSWORD, BOOTSTRAP_SECRET]));
      if (DAILY && isIntent && ['ui.contract', 'ui.contract.v2', 'load_contract', 'action.view', 'my.work.summary'].includes(request?.intent)) runtime.contracts.push({ intent: request.intent, params: request.params, response: envelope });
    })();
    responseTasks.add(task);
    task.finally(() => responseTasks.delete(task)).catch(() => {});
  });
  await login(page, navigation);
  if (contractGate.status === 'accepted') {
    // Replay the backend-approved request through this real session. The approved
    // contract must be reproducible at the served revision under the live actor;
    // anything else is not the contract the acceptance claim was made about.
    const approvedPayload = contractGate.approved_request;
    // The released SPA authenticates intent calls with the session bearer token
    // (`sc_auth_token:<db>`) and deliberately omits Odoo session cookies, so a
    // cookie-only replay can never carry the live session authority. Replay under
    // the same token authority the application actually uses.
    const replay = await page.evaluate(async ({ url, payload, db }) => {
      const bearer = sessionStorage.getItem(`sc_auth_token:${db}`) || '';
      const response = await fetch(url, { method: 'POST', credentials: 'omit',
        headers: { 'Content-Type': 'application/json', 'X-Odoo-DB': db, Authorization: bearer ? `Bearer ${bearer}` : '' },
        body: JSON.stringify(payload) });
      return { status: response.status, text: await response.text() };
    }, { url: `${BASE_URL}/api/v1/intent?db=${DATABASE}`, payload: approvedPayload, db: DATABASE });
    let replayEnvelope = {};
    try { replayEnvelope = JSON.parse(replay.text); } catch {}
    const binding = observedContractBinding({ envelope: replayEnvelope, receiptRequest: approvedPayload.params,
      approved: contractGate.verdict, requestParams: approvedPayload.params });
    contractGate.binding = { replay_http_status: replay.status, ...binding };
    if (replay.status !== 200 || !binding.ok) {
      throw new Error(`approved contract replay did not bind: status=${replay.status} ${binding.ok ? '' : `${binding.code} ${JSON.stringify(binding.detail || {})}`}`);
    }
  }
  if (DAILY) {
    actorContext = dailyActorContext(navigation.payload());
    if (!actorContext.user_id || !actorContext.company_id || !actorContext.role_codes.length) throw new Error('actual bootstrap actor context missing');
  }
  if (COLOR_SCHEME) {
    // Declared theme mechanism: documentElement theme attributes backed by the
    // stored preference. A dark run must actually resolve dark before any detail
    // observation; the rendered detail page is captured on top of this, so the
    // attribute is a prerequisite, not the proof of the visual effect.
    const resolved = () => page.evaluate(() => document.documentElement.getAttribute('data-sc-theme-resolved'));
    if (await resolved() !== COLOR_SCHEME) {
      await page.waitForFunction(scheme => document.documentElement.getAttribute('data-sc-theme-resolved') === scheme, COLOR_SCHEME, { timeout: 30_000 }).catch(async () => {
        await page.locator('.theme-switch:visible').first().click();
        await page.waitForFunction(scheme => document.documentElement.getAttribute('data-sc-theme-resolved') === scheme, COLOR_SCHEME, { timeout: 15_000 });
      });
    }
    if (await resolved() !== COLOR_SCHEME) throw new Error(`declared theme ${COLOR_SCHEME} did not resolve`);
    dailyObservations.push({ surface: 'declared-theme', requested: COLOR_SCHEME, resolved: await resolved(), mode: await page.evaluate(() => document.documentElement.getAttribute('data-sc-theme-mode')), url: page.url(), viewport: VIEWPORTS[0].key });
  }
  if (DAILY && (DAILY_OBSERVATION_SCOPE === 'all' || WORKBENCH_ONLY)) {
    const defaultRoute = dailyDeclaredLanding(navigation.payload());
    const landing = page.url();
    if (!dailyLandingMatches(landing, defaultRoute, BASE_URL)) throw new Error('daily landing does not match declared default_route');
    // Public-surface equivalent: the declared landing must render a product
    // card. The card primitive marker is consumed, not the owning-component
    // name, so a surface that legitimately claims ownership of its card root
    // still proves the card rendered.
    await page.locator(`${CARD_PRIMITIVE_SELECTOR}:visible`).first().waitFor({ state: 'visible', timeout: 30_000 });
    let landingContracts = [];
    for (let attempt = 0; attempt < 60; attempt += 1) {
      landingContracts = runtime.contracts.filter(row => row.intent === 'ui.contract.v2' && row.response?.ok === true
        && row.params?.scene_key === defaultRoute.scene_key && row.response?.data?.pageInfo);
      if (landingContracts.length) break;
      await page.waitForTimeout(50);
    }
    if (!landingContracts.length) throw new Error('daily declared landing contract was not captured');
    for (const viewport of VIEWPORTS) {
      await page.setViewportSize(viewport);
      const screenshot = path.join(OUTPUT, `daily-landing-${viewport.key}.png`);
      await page.screenshot({ path: screenshot, fullPage: true });
      dailyObservations.push({ surface: 'declared-default-landing', url: landing, defaultRoute,
        contractResponses: landingContracts.length, viewport: viewport.key, screenshot });
    }
    // Router declares '/' as HomeView(workspace.home); it is independent of
    // the account's authenticated default_route and the menu's data overview.
    const homeStart = runtime.contracts.length;
    await page.goto(`${BASE_URL}/`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
    await page.locator('[data-role-home][data-state="ready"]').waitFor({ state: 'visible', timeout: 30_000 });
    let homeResponses = [];
    for (let attempt = 0; attempt < 60; attempt += 1) {
      homeResponses = runtime.contracts.slice(homeStart).filter(dailyHomeSummaryMatches);
      if (homeResponses.length) break;
      await page.waitForTimeout(50);
    }
    if (!homeResponses.length) throw new Error('current daily home summary response missing');
    const home = page.url();
    for (const viewport of VIEWPORTS) {
      await page.setViewportSize(viewport);
      const officialCards = await page.locator(`[data-role-home] ${CARD_PRIMITIVE_SELECTOR}:visible`).count();
      if (!officialCards) throw new Error('daily workspace home has no visible official Card');
      const screenshot = path.join(OUTPUT, `daily-home-${viewport.key}.png`);
      await page.screenshot({ path: screenshot, fullPage: true });
      dailyObservations.push({ surface: 'router-workspace-home', summaryResponses: homeResponses.length, url: home, viewport: viewport.key, officialCards, screenshot });
    }
    await page.setViewportSize(VIEWPORTS[0]);
  }
  if (FORM_PROFILES_ONLY) {
    // Scope: the declared create/edit entries and the forms they consume. The
    // authority asserted is the list contract's own effective capability; the
    // evidence is the form contract the browser actually rendered, never the
    // presence of a button label or a hard-coded pixel value.
    target = await findPopulatedList(page, navigation);
    for (const viewport of VIEWPORTS) {
      await page.setViewportSize(viewport);
      await page.goto(`${BASE_URL}${target.route}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
      await waitForList(page);
      const targetUrl = new URL(target.route, BASE_URL);
      const source = { actionId: Number(targetUrl.pathname.split('/')[2]), menuId: Number(targetUrl.searchParams.get('menu_id')) };
      const listContract = [...runtime.contracts].reverse().find(row => row.intent === 'ui.contract.v2' && row.response?.ok === true && Number(row.params?.action_id) === source.actionId && Number(row.params?.menu_id) === source.menuId && ['list', 'tree'].includes(row.response?.data?.pageInfo?.viewType));
      if (!listContract) throw new Error('current list authority contract missing');
      const listData = listContract.response.data;
      const model = String(listData.pageInfo.model || '');
      const listRef = dailyContractEvidenceRef(runtime.contracts, listContract);
      const declaredCreate = listData.statusContract?.globalStatus?.effectiveRecordCapabilities?.create === true;

      // Create: the declared capability must be consumed -- a rendered control
      // exists iff the contract allows create, and clicking it opens the
      // declared create route whose form contract declares the create profile.
      const createControl = page.locator('[data-list-surface-header] .sc-btn-primary').first();
      const createVisible = (await createControl.count()) > 0 && await createControl.isVisible().catch(() => false);
      if (declaredCreate !== createVisible) throw new Error(`declared create authority=${declaredCreate} does not match rendered create control=${createVisible}`);
      if (!declaredCreate) {
        for (const check of ['declared_create_entry', 'create_contract', 'create_renderer']) {
          recordChecks.push({ viewport: viewport.key, check, passed: false, not_applicable: true,
            reason: 'create authority is not declared for this list', contract_evidence_ref: listRef });
        }
      } else {
        recordChecks.push({ viewport: viewport.key, check: 'declared_create_entry', passed: true, model,
          route: `/f/${model}/new`, contract_evidence_ref: listRef });
        const createStart = runtime.contracts.length;
        await createControl.click();
        await page.waitForURL(url => url.pathname === `/f/${model}/new`, { timeout: 30_000 });
        const expectedCreate = { model, recordId: 'new', actionId: source.actionId, menuId: source.menuId, path: `/f/${model}/new` };
        let createRows = [];
        for (let attempt = 0; attempt < 600; attempt += 1) {
          createRows = runtime.contracts.slice(createStart).filter(row => dailyCreateContractMatches(row, expectedCreate));
          if (createRows.length) break;
          await page.waitForTimeout(50);
        }
        if (!createRows.length) throw new Error('create form contract response was not captured');
        const createRow = createRows[createRows.length - 1];
        const createRef = dailyContractEvidenceRef(runtime.contracts, createRow);
        recordChecks.push({ viewport: viewport.key, check: 'create_contract', passed: true, contract_evidence_ref: createRef });
        const createDeclaration = dailyRecordPresentation(createRow.response.data, expectedCreate);
        const createPresentation = await captureRecordPresentation(page, createDeclaration);
        if (!dailyCreateDomMatches(createPresentation, expectedCreate)) throw new Error(`create renderer declaration mismatch: ${JSON.stringify(createPresentation)}`);
        recordChecks.push({ viewport: viewport.key, check: 'create_renderer', passed: true, contract_evidence_ref: createRef, presentation: createPresentation });
        dailyObservations.push({ surface: 'create-form-observation-without-save', url: page.url(),
          renderProfile: createDeclaration.profile, presentation: createPresentation, viewport: viewport.key });
        await page.goBack({ waitUntil: 'domcontentloaded' });
        await waitForList(page);
      }

      // Edit: open one declared row and require the profile its own record
      // contract declares. A record that denies write renders a readonly
      // profile; that is recorded as not-applicable, never as a passing edit.
      const declaredRow = page.locator('[data-record-key]').filter({ has: page.locator(DECLARED_RECORD_OPENER) }).first();
      if (!await declaredRow.count()) throw new Error('daily list contains no declared record opener');
      const rowId = await declaredRow.getAttribute('data-record-key');
      if (!rowId || !/^[1-9]\d*$/.test(rowId)) throw new Error('declared visible row identity missing');
      const expectedEdit = dailyRecordEntry(listData, { id: Number(rowId), model }, source);
      const editStart = runtime.contracts.length;
      await declaredRow.locator(DECLARED_RECORD_OPENER).first().click();
      await page.waitForURL(url => url.pathname === expectedEdit.path, { timeout: 30_000 });
      recordChecks.push({ viewport: viewport.key, check: 'declared_edit_entry', passed: true, entry: expectedEdit, contract_evidence_ref: listRef });
      let editRows = [];
      for (let attempt = 0; attempt < 600; attempt += 1) {
        editRows = runtime.contracts.slice(editStart).filter(row => dailyDetailContractMatches(row, expectedEdit));
        if (editRows.length) break;
        await page.waitForTimeout(50);
      }
      if (!editRows.length) throw new Error('edit form contract response was not captured');
      const editRow = editRows[editRows.length - 1];
      const editRef = dailyContractEvidenceRef(runtime.contracts, editRow);
      const editDeclaration = dailyRecordPresentation(editRow.response.data, expectedEdit);
      if (editDeclaration.profile === 'edit') {
        recordChecks.push({ viewport: viewport.key, check: 'edit_contract', passed: true, contract_evidence_ref: editRef });
        const editPresentation = await captureRecordPresentation(page, editDeclaration);
        if (!dailyRecordDomMatches(editPresentation, editDeclaration, expectedEdit)) throw new Error(`edit renderer declaration mismatch: ${JSON.stringify(editPresentation)}`);
        recordChecks.push({ viewport: viewport.key, check: 'edit_renderer', passed: true, contract_evidence_ref: editRef, presentation: editPresentation });
        dailyObservations.push({ surface: 'edit-form-observation-without-save', declaredEntry: expectedEdit,
          renderProfile: editDeclaration.profile, presentation: editPresentation, url: page.url(), viewport: viewport.key });
      } else {
        for (const check of ['edit_contract', 'edit_renderer']) {
          recordChecks.push({ viewport: viewport.key, check, passed: false, not_applicable: true,
            reason: `record contract declares '${editDeclaration.profile}' rather than an editable profile`,
            contract_evidence_ref: editRef });
        }
      }
      await page.goBack({ waitUntil: 'domcontentloaded' });
      await waitForList(page);
      if (new URL(page.url()).pathname + new URL(page.url()).search !== target.route) throw new Error('form-profiles return did not restore source list');
    }
    await page.setViewportSize(VIEWPORTS[0]);
  }
  if (!WORKBENCH_ONLY && !FORM_PROFILES_ONLY) target = await findPopulatedList(page, navigation);
  for (const viewport of LIST_MATRIX_SKIPPED ? [] : VIEWPORTS) {
    await page.setViewportSize(viewport);
    const states = PHASE === 'current-fail' ? ['normal'] : ['normal', 'batch', 'empty'];
    for (const state of states) rows.push(await captureState(page, target, viewport, state));
  }
  if (!LIST_MATRIX_SKIPPED) {
  await page.setViewportSize(VIEWPORTS[0]);
  await page.goto(`${BASE_URL}${target.route}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  await waitForList(page);
  }
  if (DAILY && !WORKBENCH_ONLY && !FORM_PROFILES_ONLY) {
    for (const viewport of VIEWPORTS) {
      await page.setViewportSize(viewport);
      await page.goto(`${BASE_URL}${target.route}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
      await waitForList(page);
      const targetUrl = new URL(target.route, BASE_URL);
      const source = { actionId: Number(targetUrl.pathname.split('/')[2]), menuId: Number(targetUrl.searchParams.get('menu_id')) };
      const listContract = [...runtime.contracts].reverse().find(row => row.intent === 'ui.contract.v2' && row.response?.ok === true && Number(row.params?.action_id) === source.actionId && Number(row.params?.menu_id) === source.menuId && ['list', 'tree'].includes(row.response?.data?.pageInfo?.viewType));
      if (!listContract) throw new Error('current list authority contract missing');
      // Open the contract-approved record through the row authority the list
      // contract declares; never the first row that happens to render.
      const approvedRecordId = contractGate.status === 'accepted' ? Number(contractGate.approved.record_id) : null;
      const approvedRow = approvedRecordId
        ? page.locator(`[data-record-key="${approvedRecordId}"]`).filter({ has: page.locator(DECLARED_RECORD_OPENER) }).first()
        : page.locator('[data-record-key]').filter({ has: page.locator(DECLARED_RECORD_OPENER) }).first();
      if (!await approvedRow.count()) {
        throw new Error(approvedRecordId
          ? `approved record ${approvedRecordId} is not reachable through the approved list authority`
          : 'daily list contains no declared record opener');
      }
      const firstRecord = approvedRow.locator(DECLARED_RECORD_OPENER).first();
      if (!await firstRecord.count()) throw new Error('daily list contains no declared record opener');
      const rowId = await approvedRow.getAttribute('data-record-key') || await firstRecord.evaluate(node => node.closest('[data-record-key]')?.getAttribute('data-record-key'));
      if (!rowId || !/^[1-9]\d*$/.test(rowId)) throw new Error('declared visible row identity missing');
      if (approvedRecordId && Number(rowId) !== approvedRecordId) throw new Error(`opened row ${rowId} is not the approved record ${approvedRecordId}`);
      const expectedDetail = dailyRecordEntry(listContract.response.data, { id: Number(rowId), model: listContract.response.data.pageInfo.model }, source);
      const contractStart = runtime.contracts.length;
      await firstRecord.click();
      await page.waitForURL(url => url.pathname === expectedDetail.path, { timeout: 30_000 });
      recordChecks.push({ viewport: viewport.key, check: 'declared_entry_route', passed: true, entry: expectedDetail, contract_evidence_ref: dailyContractEvidenceRef(runtime.contracts, listContract) });
      let newContracts = [];
      for (let attempt = 0; attempt < 600; attempt += 1) {
        newContracts = runtime.contracts.slice(contractStart).filter(row => dailyDetailContractMatches(row, expectedDetail));
        if (newContracts.length) break;
        await page.waitForTimeout(50);
      }
      if (!newContracts.length) throw new Error('daily detail contract response was not captured');
      const contractEvidenceRef = dailyContractEvidenceRef(runtime.contracts, newContracts[newContracts.length - 1]);
      recordChecks.push({ viewport: viewport.key, check: 'exact_record_contract', passed: true, contract_evidence_ref: contractEvidenceRef });
      const observedDetail = newContracts[newContracts.length - 1];
      const detailContract = observedDetail.response.data;
      if (contractGate.status === 'accepted') {
        // The contract the browser actually executed must still be the approved one.
        const appBinding = observedContractBinding({ envelope: observedDetail.response, receiptRequest: contractGate.approved_request.params,
          approved: contractGate.verdict, requestParams: observedDetail.params || {} });
        contractGate.app_viewport_bindings = [...(contractGate.app_viewport_bindings || []), { viewport: viewport.key, ...appBinding }];
        if (!appBinding.ok) throw new Error(`observed detail contract is not the approved contract: ${appBinding.code} ${JSON.stringify(appBinding.detail || {})}`);
        // The contract the browser actually rendered must be reproducible from the
        // request that produced it, under the same real session authority.
        const observedPayload = { intent: observedDetail.intent, params: observedDetail.params };
        const observedReplay = await page.evaluate(async ({ url, payload, db }) => {
          const bearer = sessionStorage.getItem(`sc_auth_token:${db}`) || '';
          const response = await fetch(url, { method: 'POST', credentials: 'omit',
            headers: { 'Content-Type': 'application/json', 'X-Odoo-DB': db, Authorization: bearer ? `Bearer ${bearer}` : '' },
            body: JSON.stringify(payload) });
          return { status: response.status, text: await response.text() };
        }, { url: `${BASE_URL}/api/v1/intent?db=${DATABASE}`, payload: observedPayload, db: DATABASE });
        let observedEnvelope = {};
        try { observedEnvelope = JSON.parse(observedReplay.text); } catch {}
        const observedDigest = observedEnvelope?.data?.meta?.lifecycle?.integrity?.contractSha256;
        if (observedReplay.status !== 200 || observedDigest !== appBinding.observedSemanticSha256) {
          throw new Error(`observed detail contract is not reproducible: status=${observedReplay.status} original=${appBinding.observedSemanticSha256} replay=${observedDigest}`);
        }
        recordChecks.push({ viewport: viewport.key, check: 'approved_contract_binding', passed: true, contract_evidence_ref: contractEvidenceRef,
          approved_semantic_sha256: contractGate.approved_semantic_sha256, observed_semantic_sha256: appBinding.observedSemanticSha256,
          exact_approved_request: appBinding.exact_approved_request, extra_request_params: appBinding.extra_request_params,
          missing_request_params: appBinding.missing_request_params, reproducible: true });
      }
      const declaration = dailyRecordPresentation(detailContract, expectedDetail);
      const profile = declaration.profile;
      const presentation = await captureRecordPresentation(page, declaration);
      if (!dailyRecordDomMatches(presentation, declaration, expectedDetail)) throw new Error(`record renderer declaration mismatch: ${JSON.stringify(presentation)}`);
      recordChecks.push({ viewport: viewport.key, check: 'declared_renderer', passed: true, contract_evidence_ref: contractEvidenceRef, presentation });
      const cards = presentation.cards;
      const screenshot = path.join(OUTPUT, `daily-detail-${viewport.key}.png`);
      await page.screenshot({ path: screenshot, fullPage: true });
      dailyObservations.push({ surface: profile === 'readonly' ? 'readonly-detail' : 'edit-form-observation-without-save', declaredEntry: expectedDetail, renderProfile: profile, presentation, contractResponses: newContracts.length, url: page.url(), viewport: viewport.key, cards, screenshot });
      await page.goBack({ waitUntil: 'domcontentloaded' });
      await waitForList(page);
      if (new URL(page.url()).pathname + new URL(page.url()).search !== target.route) throw new Error('daily detail return did not restore source list');
      recordChecks.push({ viewport: viewport.key, check: 'return_to_source', passed: true, contract_evidence_ref: dailyContractEvidenceRef(runtime.contracts, listContract) });
    }
    await page.setViewportSize(VIEWPORTS[0]);
  }
  const componentProof = LIST_MATRIX_SKIPPED ? null : await productionComponentProof(page);
  const negativeFixtures = LIST_MATRIX_SKIPPED ? [] : await negativeProofs(page, VIEWPORTS[0]);
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
  if (componentProof && !componentProof.search_inside_single_action_bar) {
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
  const aggregateChecks = LIST_MATRIX_SKIPPED ? {} : {
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
    + Object.keys(aggregateChecks).length + (componentProof ? 1 : 0);
  const gatedFailed = failures.filter((failure) => failure.state !== 'negative-fixture').length;
  await Promise.allSettled([...responseTasks]);
  const recordSummary = dailyRecordCheckSummary(recordChecks, VIEWPORTS, contractGate.status, DAILY_OBSERVATION_SCOPE);
  const passed = (!DAILY || recordSummary.complete) && failures.length === 0 && !runtime.console_errors.length && !runtime.page_errors.length && !runtime.failed_responses.length && !runtime.denied_requests.length;
  const report = {
    schema: 'frontend_list_surface_structure_browser.v1',
    phase: PHASE,
    source: { base_url: BASE_URL, database: DATABASE, login: LOGIN, target, acceptance: redactedEnvironmentEvidence(acceptance), servedIdentity },
    contract_prerequisite: contractGate,
    acceptance_scope: acceptanceScope,
    actor_context: actorContext,
    daily_observations: dailyObservations,
    daily_observation_scope: DAILY_OBSERVATION_SCOPE,
    list_execution: LIST_MATRIX_SKIPPED ? 'not_run' : 'completed',
    record_checks: recordChecks,
    geometry_contract: 'controls contained by shared header; content follows header within viewport',
    rows,
    production_component_proof: componentProof,
    negative_fixtures: negativeFixtures,
    runtime,
    aggregate_checks: aggregateChecks,
    observations,
    summary: {
      records: DAILY ? recordSummary : { status: 'not_run' },
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
} catch (error) {
  process.stderr.write(`[frontend_list_surface_structure_browser] failure: ${String(error?.stack || error)}\n`);
  await Promise.allSettled([...responseTasks]);
  const screenshot = path.join(OUTPUT, 'failure.png');
  await page?.screenshot({ path: screenshot, fullPage: true }).catch(() => {});
  await fs.mkdir(path.dirname(REPORT), { recursive: true });
  await fs.writeFile(REPORT, JSON.stringify({ schema: 'frontend_list_surface_structure_browser.v1', passed: false,
    failure: String(error?.message || error), screenshot, rows, acceptance_scope: acceptanceScope, actor_context: actorContext, record_checks: recordChecks, record_summary: dailyRecordCheckSummary(recordChecks, VIEWPORTS, contractGate.status, DAILY_OBSERVATION_SCOPE), list_execution: LIST_MATRIX_SKIPPED ? 'not_run' : 'partial_or_completed_before_failure', runtime, daily_observations: dailyObservations, daily_observation_scope: DAILY_OBSERVATION_SCOPE,
    contract_prerequisite: contractGate,
    source: { target, acceptance: redactedEnvironmentEvidence(acceptance), servedIdentity } }, null, 2));
  process.exitCode = 1;
} finally {
  try { await context?.close(); } finally { try { await browser?.close(); } finally { await lease?.release(); } }
}
