import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { launchChromium } from './playwright_runtime.mjs';

const ROOT = process.cwd();
const BASE = process.env.DEV_ACCEPTANCE_BASE_URL || 'http://127.0.0.1:18081';
const ACTOR = process.env.DEV_ACCEPTANCE_ACTOR || 'demo_full';
const PASSWORD = process.env.SC_DEMO_USER_PASSWORD || '';
const OUTPUT = process.env.DEV_ACCEPTANCE_OUTPUT
  ? path.resolve(ROOT, process.env.DEV_ACCEPTANCE_OUTPUT)
  : path.join(
    ROOT,
    '.runtime/dev-acceptance-20261115b-remediation/browser-report.json',
  );

const technicalTitles = new Set(['enterprise.department', 'portal.notifications']);
const affectedHeadings = ['消息通知', '材料出库', '施工日志', '项目台账', '安全检查', '部门管理'];
const RECORD_READY_SELECTOR = '[data-product-page-mode="form"][data-form-model="payment.request"][data-state="ok"]';
const runtimeState = {
  navigation: [],
  scenarioSurface: null,
  roleSurface: null,
  user: null,
  sourceRevision: '',
  initIntent: '',
  dataKeys: [],
  navigationKeys: [],
};

function clean(value) {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

function safeRequestShape(payload) {
  const params = payload?.params || {};
  return {
    intent: clean(payload?.intent),
    action_id: Number.isSafeInteger(params.action_id) ? params.action_id : null,
    model: /^[a-zA-Z0-9_.]{1,100}$/.test(String(params.model || '')) ? String(params.model) : null,
    preference_key: /^[a-zA-Z0-9_.]{1,100}$/.test(String(params.preference_key || ''))
      ? String(params.preference_key)
      : null,
    projection: /^[a-zA-Z0-9_.]{1,100}$/.test(String(params.projection || ''))
      ? String(params.projection)
      : null,
  };
}

async function attachNetworkCapture(page, sink, startedAt = performance.now()) {
  const startedRequests = new Map();
  const requestHandler = request => {
    let payload = null;
    try {
      payload = request.postDataJSON();
    } catch {
      // Non-JSON requests are still recorded when they are page resources.
    }
    startedRequests.set(request, {
      ...safeRequestShape(payload),
      request_start_ms: Math.round(performance.now() - startedAt),
      method: request.method(),
      resource_type: request.resourceType(),
      resource_url: request.url(),
    });
  };
  const handler = async response => {
    const request = response.request();
    const started = startedRequests.get(request);
    if (!response.url().includes('/api/v1/intent')) {
      if (!started || !['document', 'script', 'stylesheet'].includes(started.resource_type)) return;
      sink.push({
        intent: '',
        status: response.status(),
        resource_type: started.resource_type,
        resource_url: started.resource_url,
        request_start_ms: started.request_start_ms,
        response_end_ms: Math.round(performance.now() - startedAt),
      });
      return;
    }
    let payload;
    try {
      payload = request.postDataJSON();
    } catch {
      return;
    }
    const row = {
      ...safeRequestShape(payload),
      status: response.status(),
      url: response.url(),
      request_start_ms: started?.request_start_ms ?? null,
      response_end_ms: Math.round(performance.now() - startedAt),
      duration_ms: started
        ? Math.round(performance.now() - startedAt) - started.request_start_ms
        : null,
    };
    if (response.status() >= 400) {
      try {
        row.response_body = clean((await response.text()).slice(0, 1000));
      } catch {
        row.response_body = '';
      }
    } else if (payload?.intent === 'system.init' || payload?.intent === 'app.init') {
      try {
        const body = await response.json();
        const data = body?.data || body?.result?.data || body?.result || {};
        runtimeState.initIntent = String(payload.intent);
        runtimeState.dataKeys = Object.keys(data || {}).sort();
        runtimeState.navigationKeys = Object.keys(data?.navigation || {}).sort();
        if (Array.isArray(data?.navigation?.nav)) runtimeState.navigation = data.navigation.nav;
        if (data?.navigation?.scenario_surface && typeof data.navigation.scenario_surface === 'object') {
          runtimeState.scenarioSurface = data.navigation.scenario_surface;
        }
        if (data?.role_surface && typeof data.role_surface === 'object') runtimeState.roleSurface = data.role_surface;
        if (data?.user && typeof data.user === 'object') runtimeState.user = data.user;
        if (data?.source_revision) runtimeState.sourceRevision = String(data.source_revision);
      } catch {
        // The mandatory runtime state remains absent and the navigation check fails closed.
      }
    }
    sink.push(row);
  };
  page.on('request', requestHandler);
  page.on('response', handler);
  return () => {
    page.off('request', requestHandler);
    page.off('response', handler);
  };
}

function findNavigationTarget(nodes, label) {
  for (const node of Array.isArray(nodes) ? nodes : []) {
    const nodeLabel = clean(node?.label || node?.title || node?.name);
    if (nodeLabel === label) {
      const meta = node?.meta && typeof node.meta === 'object' ? node.meta : {};
      const entryTarget = node?.entry_target && typeof node.entry_target === 'object'
        ? node.entry_target
        : meta.entry_target && typeof meta.entry_target === 'object'
          ? meta.entry_target
          : {};
      return {
        route: clean(node?.route || meta.route || entryTarget.route),
        menu_id: Number(node?.menu_id || meta.menu_id || entryTarget?.compatibility_refs?.menu_id || 0),
        action_id: Number(node?.action_id || meta.action_id || entryTarget?.compatibility_refs?.action_id || 0),
      };
    }
    const nested = findNavigationTarget(node?.children, label);
    if (nested) return nested;
  }
  return null;
}

function findScenarioTarget(surface, label) {
  const centers = Array.isArray(surface?.tree?.centers)
    ? surface.tree.centers
    : Array.isArray(surface?.centers) ? surface.centers : [];
  for (const center of centers) {
    const groups = [center?.entries, ...(Array.isArray(center?.scenarios) ? center.scenarios.map(item => item?.entries) : [])];
    for (const entries of groups) {
      for (const entry of Array.isArray(entries) ? entries : []) {
        if (clean(entry?.label) !== label) continue;
        return {
          route: clean(entry?.route || entry?.entry_target?.route),
          menu_id: Number(entry?.menu_id || entry?.entry_target?.compatibility_refs?.menu_id || 0),
          action_id: Number(entry?.action_id || entry?.entry_target?.compatibility_refs?.action_id || 0),
        };
      }
    }
  }
  return null;
}

function scenarioEntryLabels(surface) {
  const centers = Array.isArray(surface?.tree?.centers) ? surface.tree.centers : [];
  const labels = [];
  for (const center of centers) {
    const groups = [center?.entries, ...(Array.isArray(center?.scenarios) ? center.scenarios.map(item => item?.entries) : [])];
    for (const entries of groups) {
      for (const entry of Array.isArray(entries) ? entries : []) {
        const label = clean(entry?.label);
        if (label) labels.push(label);
      }
    }
  }
  return [...new Set(labels)];
}

async function login(page) {
  assert.ok(PASSWORD, 'governed demo password missing');
  await page.goto(`${BASE}/t/demo/login`, { waitUntil: 'domcontentloaded' });
  await page.locator('#login-username, input[autocomplete="username"]').first().fill(ACTOR);
  await page.locator('#login-password, input[autocomplete="current-password"]').first().fill(PASSWORD);
  const database = page.locator('#login-database, input[name="database"]');
  if (await database.count() && await database.isEnabled().catch(() => false)) {
    await database.fill(process.env.DB_NAME || 'sc_dev_demo');
  }
  await page.getByRole('button', { name: /^登录$/ }).click();
  try {
    await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 30000 });
  } catch (error) {
    const body = await page.locator('body').innerText().catch(() => '');
    throw new Error(`login did not complete for ${ACTOR}: ${clean(body).slice(0, 800)}`, { cause: error });
  }
  await page.locator('[data-role-home][data-state="ready"]').waitFor({
    state: 'visible',
    timeout: 30000,
  });
  try {
    await page.locator('[data-navigation-node="canonical"]').first().waitFor({
      state: 'attached',
      timeout: 30000,
    });
  } catch (error) {
    const body = await page.locator('body').innerText().catch(() => '');
    throw new Error(`navigation shell did not publish nodes: ${clean(body).slice(0, 800)}`, { cause: error });
  }
}

async function activeHeadingTexts(page) {
  return page.evaluate(() => Array.from(document.querySelectorAll('h1'))
    .filter((node) => {
      const element = node;
      const style = window.getComputedStyle(element);
      return style.display !== 'none'
        && style.visibility !== 'hidden'
        && (element.offsetWidth > 0 || element.offsetHeight > 0);
    })
    .map(node => String(node.textContent || '').replace(/\s+/g, ' ').trim())
    .filter(Boolean));
}

async function openMenu(page, label) {
  const releasedTarget = findNavigationTarget(runtimeState.navigation, label)
    || findScenarioTarget(runtimeState.scenarioSurface, label);
  if (releasedTarget?.route && process.env.DEV_ACCEPTANCE_SWITCH_MODE !== 'ui') {
    const route = releasedTarget.route.startsWith('http')
      ? releasedTarget.route
      : `${BASE}/t/demo${releasedTarget.route.startsWith('/') ? '' : '/'}${releasedTarget.route}`;
    await page.goto(route, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForFunction(
      expected => Array.from(document.querySelectorAll('h1'))
        .some(node => String(node.textContent || '').replace(/\s+/g, ' ').trim() === expected),
      label,
      { timeout: 30000 },
    ).catch(() => {});
    return releasedTarget;
  }
  const scenarioSearch = page.getByRole('searchbox', { name: '搜索业务入口', exact: true });
  const canonicalSearch = page.getByRole('searchbox', { name: '搜索菜单', exact: true });
  const usesScenarioSurface = await scenarioSearch.isVisible().catch(() => false);
  if (usesScenarioSurface) {
    await scenarioSearch.fill(label);
  } else {
    await canonicalSearch.fill(label);
  }
  const target = usesScenarioSurface
    ? page.locator(`.scenario-entry__label[title="${label}"]:visible`).first()
    : page.locator(
      `[data-navigation-node="canonical"][data-navigation-label="${label}"]:visible`,
    ).first();
  try {
    await target.waitFor({ state: 'visible', timeout: 15000 });
  } catch (error) {
    const labels = await page.locator(usesScenarioSurface ? '.scenario-entry__label' : '[data-navigation-node="canonical"]').evaluateAll(nodes => nodes
      .map(node => ({
        label: node.getAttribute('title') || node.getAttribute('data-navigation-label'),
        text: String(node.textContent || '').replace(/\s+/g, ' ').trim(),
      }))
      .filter(row => row.label || row.text)
      .slice(0, 80));
    throw new Error(`navigation target not visible: ${label}; visible nodes=${JSON.stringify(labels)}`, { cause: error });
  }
  await target.click();
  await page.locator('[data-shell-loading="true"], [aria-busy="true"]').waitFor({
    state: 'detached',
    timeout: 30000,
  }).catch(() => {});
  await page.waitForFunction(
    expected => Array.from(document.querySelectorAll('h1'))
      .some(node => String(node.textContent || '').replace(/\s+/g, ' ').trim() === expected),
    label,
    { timeout: 30000 },
  ).catch(() => {});
  return null;
}

async function selectScenarioMenu(page, label) {
  const scenarioSearch = page.getByRole('searchbox', { name: '搜索业务入口', exact: true });
  const usesScenarioSurface = await scenarioSearch.isVisible().catch(() => false);
  const search = usesScenarioSurface
    ? scenarioSearch
    : page.getByRole('searchbox', { name: '搜索菜单', exact: true });
  await search.fill(label);
  const target = usesScenarioSurface
    ? page.locator(`.scenario-entry__label[title="${label}"]:visible`).first()
    : page.locator(`[data-navigation-node="canonical"][data-navigation-label="${label}"]:visible`).first();
  await target.waitFor({ state: 'visible', timeout: 15000 });
  await target.click();
}

async function tabTitles(page) {
  return page.locator('[data-navigation-control="activity-page-title"]')
    .allTextContents()
    .then(rows => rows.map(clean).filter(Boolean));
}

async function recordPageSnapshot(page) {
  return page.evaluate(selector => {
    const cleanText = value => String(value || '').replace(/\s+/g, ' ').trim();
    const visible = node => {
      if (!node) return false;
      const style = window.getComputedStyle(node);
      return style.display !== 'none' && style.visibility !== 'hidden'
        && (node.offsetWidth > 0 || node.offsetHeight > 0);
    };
    const form = document.querySelector('[data-product-page-mode="form"][data-form-model="payment.request"]');
    const skeleton = document.querySelector('[data-loading-progress]');
    const shellLoading = document.querySelector('[data-shell-loading="true"], [aria-busy="true"]');
    const bodyText = cleanText(document.body?.innerText);
    const main = document.querySelector('main');
    const mainText = cleanText(main?.innerText);
    const readyForm = document.querySelector(selector);
    return {
      url: window.location.href,
      title: document.title,
      body_text_length: bodyText.length,
      main_text_length: mainText.length,
      body_text: bodyText.slice(0, 600),
      main_text: mainText.slice(0, 600),
      form_present: visible(form),
      form_state: form?.getAttribute('data-state') || null,
      form_ready: visible(readyForm),
      skeleton_present: visible(skeleton),
      shell_loading: visible(shellLoading),
      headings: Array.from(document.querySelectorAll('h1'))
        .filter(visible)
        .map(node => cleanText(node.textContent))
        .filter(Boolean),
    };
  }, RECORD_READY_SELECTOR);
}

async function observeRecordPage(page, startedAt) {
  const snapshots = [];
  const screenshots = [];
  const screenshotDir = path.join(
    ROOT,
    '.runtime/dev-acceptance-20261115b-remediation',
  );
  fs.mkdirSync(screenshotDir, { recursive: true });
  let captured5s = false;
  let captured17s = false;
  while (performance.now() - startedAt < 45000) {
    const elapsedMs = Math.round(performance.now() - startedAt);
    const snapshot = await recordPageSnapshot(page);
    snapshots.push({ elapsed_ms: elapsedMs, ...snapshot });
    if (!captured5s && elapsedMs >= 5000) {
      captured5s = true;
      const screenshot = path.join(screenshotDir, 'record-deep-link-5s.png');
      await page.screenshot({ path: screenshot, fullPage: true });
      screenshots.push({ elapsed_ms: elapsedMs, screenshot });
    }
    if (!captured17s && elapsedMs >= 17000) {
      captured17s = true;
      const screenshot = path.join(screenshotDir, 'record-deep-link-17s.png');
      await page.screenshot({ path: screenshot, fullPage: true });
      screenshots.push({ elapsed_ms: elapsedMs, screenshot });
    }
    if (snapshot.form_ready) {
      const screenshot = path.join(screenshotDir, 'record-deep-link-ready.png');
      await page.screenshot({ path: screenshot, fullPage: true });
      screenshots.push({ elapsed_ms: elapsedMs, screenshot });
      return { elapsedMs, snapshots, screenshots, ready: true };
    }
    await page.waitForTimeout(1000);
  }
  const screenshot = path.join(screenshotDir, 'record-deep-link-timeout.png');
  await page.screenshot({ path: screenshot, fullPage: true });
  screenshots.push({
    elapsed_ms: Math.round(performance.now() - startedAt),
    screenshot,
  });
  return {
    elapsedMs: Math.round(performance.now() - startedAt),
    snapshots,
    screenshots,
    ready: false,
  };
}

async function installRecordDiagnostics(page) {
  await page.addInitScript(() => {
    const diagnostics = {
      installed_at: performance.now(),
      long_tasks: [],
      paints: [],
    };
    window.__scRecordDiagnostics = diagnostics;
    try {
      new PerformanceObserver(list => {
        diagnostics.long_tasks.push(...list.getEntries().map(entry => ({
          start_ms: Math.round(entry.startTime),
          duration_ms: Math.round(entry.duration),
          name: entry.name,
        })));
      }).observe({ type: 'longtask', buffered: true });
    } catch {
      // Older Chromium builds may not expose long-task entries.
    }
    try {
      new PerformanceObserver(list => {
        diagnostics.paints.push(...list.getEntries().map(entry => ({
          name: entry.name,
          start_ms: Math.round(entry.startTime),
        })));
      }).observe({ type: 'paint', buffered: true });
    } catch {
      // Paint timing is optional diagnostic detail.
    }
  });
}

async function readRecordDiagnostics(page) {
  return page.evaluate(() => {
    const diagnostics = window.__scRecordDiagnostics || {};
    const navigation = performance.getEntriesByType('navigation')[0];
    return {
      long_tasks: diagnostics.long_tasks || [],
      paints: diagnostics.paints || [],
      navigation: navigation ? {
        dom_content_loaded_ms: Math.round(navigation.domContentLoadedEventEnd),
        load_event_ms: Math.round(navigation.loadEventEnd),
        response_start_ms: Math.round(navigation.responseStart),
      } : null,
    };
  });
}

async function locatePaymentRecordHref(page) {
  await openMenu(page, '付款申请');
  const queryInput = page.locator('[data-list-query-action-bar] input[type="search"]:visible').first();
  await queryInput.fill('PRQ2600050');
  await page.locator('[data-list-query-action-bar]')
    .getByRole('button', { name: '搜索', exact: true })
    .click();
  const row = page.locator('a[href*="/r/payment.request/"]:visible')
    .filter({ hasText: 'PRQ2600050' })
    .first();
  await row.waitFor({ state: 'visible', timeout: 30000 });
  const href = await row.getAttribute('href');
  assert.ok(href, 'payment record href missing');
  return new URL(href, BASE).href;
}

async function main() {
  const report = {
    schema: 'dev-acceptance-remediation-browser/v1',
    status: 'running',
    observed_at: new Date().toISOString(),
    actor: ACTOR,
    database: process.env.DB_NAME,
    project: process.env.COMPOSE_PROJECT_NAME,
    base_url: BASE,
    rapid_switch: null,
    technical_tab_titles: null,
    headings: {},
    record_deep_link: null,
  };
  let browser;
  let context;
  try {
    browser = await launchChromium({ headless: true });
    report.browser_version = browser.version();
    context = await browser.newContext({ viewport: { width: 1440, height: 960 } });
    const page = await context.newPage();
    page.setDefaultTimeout(30000);
    const network = [];
    const detachNetwork = await attachNetworkCapture(page, network);

    await login(page);
    report.login = { status: 'passed' };
    if (process.env.DEV_ACCEPTANCE_NAV_ONLY === '1') {
      report.scenario_labels = scenarioEntryLabels(runtimeState.scenarioSurface);
      report.status = 'passed';
      return;
    }
    if (process.env.DEV_ACCEPTANCE_DIRECT_URL) {
      await page.goto(process.env.DEV_ACCEPTANCE_DIRECT_URL, {
        waitUntil: 'domcontentloaded',
        timeout: 45000,
      });
      await page.waitForTimeout(5000);
      const screenshot = path.join(ROOT, '.runtime/dev-acceptance-20261115b-remediation/direct-page.png');
      fs.mkdirSync(path.dirname(screenshot), { recursive: true });
      await page.screenshot({ path: screenshot, fullPage: true });
      report.direct_page = {
        url: page.url(),
        headings: await activeHeadingTexts(page),
        tabs: await tabTitles(page),
        screenshot,
      };
      report.status = 'passed';
      return;
    }
    report.runtime_navigation = {
      count: runtimeState.navigation.length,
      scenario_center_count: Array.isArray(runtimeState.scenarioSurface?.tree?.centers)
        ? runtimeState.scenarioSurface.tree.centers.length
        : null,
      init_intent: runtimeState.initIntent,
      data_keys: runtimeState.dataKeys,
      navigation_keys: runtimeState.navigationKeys,
      target: findNavigationTarget(runtimeState.navigation, '劳务成本登记')
        || findScenarioTarget(runtimeState.scenarioSurface, '劳务成本登记'),
    };
    report.navigation_labels = await page.locator('[data-navigation-node="canonical"]').evaluateAll(nodes => nodes
      .map(node => ({
        label: node.getAttribute('data-navigation-label'),
        key: node.getAttribute('data-navigation-key'),
        depth: node.getAttribute('data-navigation-depth'),
      }))
      .filter(row => row.label)
      .slice(0, 300));

    if (process.env.DEV_ACCEPTANCE_ONLY === 'record') {
      const href = process.env.DEV_ACCEPTANCE_RECORD_URL
        || await locatePaymentRecordHref(page);
      detachNetwork();
      const recordPage = process.env.DEV_ACCEPTANCE_RECORD_URL
        ? page
        : await context.newPage();
      const recordNetwork = [];
      const pageErrors = [];
      const consoleErrors = [];
      recordPage.on('pageerror', error => pageErrors.push(clean(error?.message || error)));
      recordPage.on('console', message => {
        if (message.type() === 'error') consoleErrors.push(clean(message.text()));
      });
      const started = performance.now();
      const detachRecordNetwork = await attachNetworkCapture(recordPage, recordNetwork, started);
      await installRecordDiagnostics(recordPage);
      await recordPage.goto(href, { waitUntil: 'domcontentloaded', timeout: 45000 });
      const observation = await observeRecordPage(recordPage, started);
      const diagnostics = await readRecordDiagnostics(recordPage);
      detachRecordNetwork();
      report.record_deep_link = {
        href,
        elapsed_ms: observation.elapsedMs,
        ready: observation.ready,
        headings: await activeHeadingTexts(recordPage),
        errors: recordNetwork.filter(row => row.status >= 400),
        requests: recordNetwork,
        snapshots: observation.snapshots,
        screenshots: observation.screenshots,
        page_errors: pageErrors,
        console_errors: consoleErrors,
        source_revision: runtimeState.sourceRevision,
        diagnostics,
      };
      report.findings = [];
      if (report.record_deep_link.errors.length) report.findings.push('record_deep_link_http_error');
      if (!observation.ready) report.findings.push('record_deep_link_not_ready');
      if (pageErrors.length) report.findings.push('record_deep_link_page_error');
      report.status = report.findings.length ? 'failed' : 'passed';
      if (report.findings.length) process.exitCode = 1;
      return;
    }

    network.length = 0;
    await openMenu(page, '劳务成本登记');
    if (process.env.DEV_ACCEPTANCE_ONLY === 'rapid-switch' && process.env.DEV_ACCEPTANCE_SWITCH_MODE === 'ui') {
      await selectScenarioMenu(page, '劳务扣款明细');
      await page.waitForTimeout(30);
      await selectScenarioMenu(page, '机械台班登记');
      await page.waitForTimeout(2500);
    } else {
      await openMenu(page, '劳务扣款明细');
      await openMenu(page, '机械台班登记');
    }
    const rapidErrors = network.filter(row => row.status >= 400);
    report.rapid_switch = {
      sequence: ['劳务成本登记', '劳务扣款明细', '机械台班登记'],
      errors: rapidErrors,
      error_count: rapidErrors.length,
      requests: network,
      active_headings: await activeHeadingTexts(page),
    };
    if (process.env.DEV_ACCEPTANCE_ONLY === 'rapid-switch') {
      const screenshot = path.join(ROOT, '.runtime/dev-acceptance-20261115b-remediation/rapid-switch.png');
      fs.mkdirSync(path.dirname(screenshot), { recursive: true });
      await page.screenshot({ path: screenshot, fullPage: true });
      report.rapid_switch.screenshot = screenshot;
      report.findings = rapidErrors.length ? ['rapid_switch_http_error'] : [];
      report.status = report.findings.length ? 'failed' : 'passed';
      if (report.findings.length) process.exitCode = 1;
      return;
    }

    await openMenu(page, '部门管理');
    const departmentTabs = await tabTitles(page);
    await openMenu(page, '消息通知');
    const notificationTabs = await tabTitles(page);
    report.technical_tab_titles = {
      department_tabs: departmentTabs,
      notification_tabs: notificationTabs,
      leaked: [...departmentTabs, ...notificationTabs].filter(title => technicalTitles.has(title)),
    };

    for (const label of affectedHeadings) {
      await openMenu(page, label);
      report.headings[label] = await activeHeadingTexts(page);
    }
    if (process.env.DEV_ACCEPTANCE_ONLY === 'ui-semantics') {
      const screenshot = path.join(ROOT, '.runtime/dev-acceptance-20261115b-remediation/ui-semantics.png');
      fs.mkdirSync(path.dirname(screenshot), { recursive: true });
      await page.screenshot({ path: screenshot, fullPage: true });
      const findings = [];
      if (report.technical_tab_titles.leaked.length) findings.push('technical_tab_title');
      for (const [label, headings] of Object.entries(report.headings)) {
        if (!headings.includes(label)) findings.push(`heading_missing:${label}`);
      }
      report.ui_semantics_screenshot = screenshot;
      report.findings = findings;
      report.status = findings.length ? 'failed' : 'passed';
      if (findings.length) process.exitCode = 1;
      return;
    }

    detachNetwork();
    const href = await locatePaymentRecordHref(page);
    const recordPage = await context.newPage();
    const recordNetwork = [];
    const detachRecordNetwork = await attachNetworkCapture(recordPage, recordNetwork);
    const started = performance.now();
    await recordPage.goto(href, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await recordPage.locator(
      '[data-product-page-mode="form"][data-form-model="payment.request"][data-state="ok"]:visible',
    ).waitFor({ state: 'visible', timeout: 45000 });
    const elapsedMs = Math.round(performance.now() - started);
    const recordHeadings = await activeHeadingTexts(recordPage);
    report.record_deep_link = {
      href,
      elapsed_ms: elapsedMs,
      headings: recordHeadings,
      errors: recordNetwork.filter(row => row.status >= 400),
      requests: recordNetwork,
    };
    detachRecordNetwork();

    const findings = [];
    if (report.rapid_switch.error_count > 0) findings.push('rapid_switch_http_error');
    if (report.technical_tab_titles.leaked.length) findings.push('technical_tab_title');
    for (const [label, headings] of Object.entries(report.headings)) {
      if (headings.length !== 1) findings.push(`heading_count:${label}:${headings.length}`);
    }
    if (!report.record_deep_link.headings.includes('PRQ2600050')) {
      findings.push('record_deep_link_identity');
    }
    report.findings = findings;
    report.status = findings.length ? 'failed' : 'passed';
    if (findings.length) process.exitCode = 1;
  } catch (error) {
    report.status = 'failed';
    report.error = clean(error?.message || error).replaceAll(PASSWORD || '\0', '[redacted]');
    process.exitCode = 1;
  } finally {
    for (const resource of [context, browser].filter(Boolean)) {
      try {
        await resource.close();
      } catch (error) {
        report.cleanup_errors ||= [];
        report.cleanup_errors.push(clean(error?.message || error).replaceAll(PASSWORD || '\0', '[redacted]'));
      }
    }
    fs.mkdirSync(path.dirname(OUTPUT), { recursive: true });
    fs.writeFileSync(OUTPUT, `${JSON.stringify(report, null, 2)}\n`);
    console.log(JSON.stringify({
      status: report.status,
      findings: report.findings || [],
      rapid_switch_errors: report.rapid_switch?.error_count ?? null,
      technical_titles: report.technical_tab_titles?.leaked ?? null,
      headings: Object.fromEntries(Object.entries(report.headings || {}).map(([key, value]) => [key, value.length])),
      record_deep_link_ms: report.record_deep_link?.elapsed_ms ?? null,
      record_source_revision: report.record_deep_link?.source_revision || null,
      output: OUTPUT,
    }));
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch(error => {
    console.error(clean(error?.message || error).replaceAll(PASSWORD || '\0', '[redacted]'));
    process.exitCode = 1;
  });
}
