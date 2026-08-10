#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const require = createRequire(path.join(process.cwd(), 'frontend/apps/web/package.json'));
const { chromium } = require('playwright');

const baseUrl = String(process.env.FRONTEND_URL || 'http://127.0.0.1:18081').replace(/\/$/, '');
const dbName = process.env.DB_NAME || 'sc_demo';
const login = process.env.E2E_LOGIN || 'wutao';
const password = process.env.E2E_PASSWORD || '';
const artifactDir = process.env.ARTIFACT_DIR || '/tmp/frontend-all-list-visual-audit';
const concurrency = Math.max(1, Math.min(8, Number(process.env.CONCURRENCY || 5)));
const targetActionId = Math.max(0, Number(process.env.TARGET_ACTION_ID || 0));

if (!password) throw new Error('E2E_PASSWORD is required');
fs.mkdirSync(artifactDir, { recursive: true });
fs.mkdirSync(path.join(artifactDir, 'screenshots'), { recursive: true });

function flattenNav(nodes, parents = []) {
  const rows = [];
  for (const node of nodes || []) {
    const label = String(node?.label || node?.title || '').trim();
    const labels = label ? [...parents, label] : parents;
    const meta = node?.meta || {};
    const target = meta.entry_target || {};
    const refs = target.compatibility_refs || {};
    const actionId = Number(meta.action_id || refs.action_id || 0);
    const menuId = Number(meta.menu_id || node?.menu_id || refs.menu_id || 0);
    const sceneKey = String(meta.scene_key || target.scene_key || '').trim();
    if (actionId || sceneKey) rows.push({
      label,
      menuPath: labels.join(' / '),
      actionId,
      menuId,
      sceneKey,
      entryTarget: target,
      authoritativeRoute: String(target.route || meta.route || node?.route || '').trim(),
    });
    rows.push(...flattenNav(node?.children || [], labels));
  }
  return rows;
}

function uniqueEntries(rows) {
  const seen = new Set();
  return rows.filter((row) => {
    const key = row.actionId ? `a:${row.actionId}:${row.menuId}` : `s:${row.sceneKey}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function safeName(value) {
  return String(value || '').replace(/[^a-zA-Z0-9\u4e00-\u9fff_-]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 80) || 'page';
}

async function loginAndDiscover(page) {
  await page.goto(`${baseUrl}/login?db=${encodeURIComponent(dbName)}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.locator('input[autocomplete="username"]').fill(login);
  await page.locator('input[autocomplete="current-password"]').fill(password);
  const dbInput = page.locator('input').nth(2);
  if (await dbInput.isEditable().catch(() => false)) await dbInput.fill(dbName);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45000 });
  const sessionEntries = await page.evaluate(() => Object.fromEntries(Object.entries(sessionStorage)));
  const init = await page.evaluate(async ({ dbName }) => {
    const tokenKey = Object.keys(sessionStorage).find((key) => key.startsWith('sc_auth_token')) || '';
    const token = tokenKey ? sessionStorage.getItem(tokenKey) : '';
    const response = await fetch(`/api/v1/intent?db=${encodeURIComponent(dbName)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Odoo-DB': dbName, Authorization: `Bearer ${token}` },
      body: JSON.stringify({ intent: 'system.init', params: { with_preload: false, with: ['workspace_home'], root_xmlid: 'smart_construction_core.menu_sc_root' }, meta: { startup_chain_bypass: true } }),
    });
    const body = await response.json();
    if (!response.ok || body.ok === false) throw new Error(JSON.stringify(body.error || body));
    return body.data || body;
  }, { dbName });
  return { entries: uniqueEntries(flattenNav(init.nav || [])), sessionEntries };
}

async function collectVisualFacts(page) {
  return page.evaluate(() => {
    const visible = (element) => element instanceof HTMLElement && element.offsetParent !== null;
    const styleOf = (element) => {
      const style = getComputedStyle(element);
      return {
        radius: style.borderRadius,
        background: style.backgroundColor,
        border: style.borderColor,
        color: style.color,
        height: Math.round(element.getBoundingClientRect().height),
      };
    };
    const visibleMains = Array.from(document.querySelectorAll('main')).filter(visible);
    const main = visibleMains.at(-1) || document.querySelector('main');
    const table = main ? Array.from(main.querySelectorAll('table')).find(visible) || null : null;
    const headers = table ? Array.from(table.querySelectorAll('thead th')).map((node) => node.textContent?.trim()).filter(Boolean) : [];
    const rendererHost = document.querySelector('.action-surface-renderer-host');
    const listRoot = document.querySelector('.hierarchy-browser, .action-list-surface, main [data-product-page-mode="list"]');
    const rows = table ? table.querySelectorAll('tbody tr').length : 0;
    const bodyText = String(main?.textContent || '').replace(/\s+/g, ' ').trim();
    const isLoading = /加载中|正在加载|正在载入|Loading/.test(bodyText);
    const listLike = !isLoading && (Boolean(document.querySelector('.hierarchy-browser, .action-list-surface'))
      || Boolean(table && (headers.length || rows))
      || Boolean(listRoot && /暂无数据|暂无记录|共\s*\d+\s*条/.test(bodyText)));
    const toolbarFamilies = [
      ['product-list-query', '[data-list-query-action-bar]'],
      ['action-surface', '.action-surface-toolbar'],
      ['list-header', '.list-surface-header'],
      ['legacy-page-actions', '.page-actions'],
      ['contract-block', '.contract-block'],
    ].filter(([, selector]) => Array.from(document.querySelectorAll(selector)).some(visible)).map(([name]) => name);
    const buttons = Array.from(main?.querySelectorAll('button') || []).filter(visible).slice(0, 12).map((element) => ({
      text: String(element.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 40),
      classes: element.className,
      style: styleOf(element),
    }));
    const searchInput = Array.from(main?.querySelectorAll('input[type="search"]') || []).find(visible) || null;
    const search = searchInput?.closest('.native-searchbox') || searchInput;
    const toolbarActionButtons = Array.from(document.querySelectorAll('[data-list-query-action-bar] .sc-btn')).filter(visible);
    const toolbarActionViolations = toolbarActionButtons.flatMap((element) => {
      const style = styleOf(element);
      const reasons = [];
      if (style.radius !== '8px') reasons.push(`radius=${style.radius}`);
      if (![36, 40].includes(style.height)) reasons.push(`height=${style.height}`);
      return reasons.length ? [{ text: String(element.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 40), reasons }] : [];
    });
    const viewSwitchButtons = Array.from(document.querySelectorAll('.view-switch .contract-chip')).filter(visible);
    const viewSwitchViolations = viewSwitchButtons.flatMap((element) => {
      const style = styleOf(element);
      const reasons = [];
      if (style.radius !== '8px') reasons.push(`radius=${style.radius}`);
      if (style.height !== 36) reasons.push(`height=${style.height}`);
      return reasons.length ? [{ text: String(element.textContent || '').trim(), reasons }] : [];
    });
    const primaryActionCount = Array.from(document.querySelectorAll('[data-list-query-action-bar] .sc-btn-primary')).filter(visible).length;
    const activeTabTitle = String(document.querySelector('.activity-tab.active .activity-tab-main span')?.textContent || '').replace(/\s+/g, ' ').trim();
    const englishEmptyCopy = /\bNo data\b|No records returned|No cards returned/i.test(bodyText);
    const nativeFileEnglish = /\bChoose File\b|\bNo file chosen\b/i.test(bodyText);
    const transientListIdentity = /[·]\s*(?:加载中|暂无数据)$/.test(activeTabTitle);
    const formCommandBar = Array.from(document.querySelectorAll('.contract-form-command-bar')).find(visible) || null;
    const formCommandBarStyle = formCommandBar ? styleOf(formCommandBar) : null;
    return {
      listLike,
      renderer: rendererHost ? {
        semantic: rendererHost.getAttribute('data-surface-semantic') || '',
        requested: rendererHost.getAttribute('data-requested-renderer') || '',
        active: rendererHost.getAttribute('data-active-renderer') || '',
        status: rendererHost.getAttribute('data-renderer-status') || '',
      } : null,
      toolbarFamilies,
      tableShellCount: Array.from(main?.querySelectorAll('.sc-table-shell') || []).filter(visible).length,
      tableCount: Array.from(main?.querySelectorAll('table') || []).filter(visible).length,
      headers,
      rowCount: rows,
      buttons,
      toolbarActionCount: toolbarActionButtons.length,
      toolbarActionViolations,
      viewSwitchCount: viewSwitchButtons.length,
      viewSwitchViolations,
      primaryActionCount,
      activeTabTitle,
      englishEmptyCopy,
      nativeFileEnglish,
      transientListIdentity,
      formCommandBar: formCommandBarStyle,
      excessiveFormCommandBar: Number(formCommandBarStyle?.height || 0) > 96,
      search: search ? styleOf(search) : null,
      paginationKinds: [
        document.querySelector('.pager') ? 'hierarchy-pager' : '',
        document.querySelector('.pagination-footer, .pagination-bar, .list-pagination, .sc-pagination') ? 'standard-pagination' : '',
      ].filter(Boolean),
      isLoading,
      hasError: /页面渲染失败|页面加载失败|系统异常|Traceback|Cannot read/i.test(bodyText),
      bodySample: bodyText.slice(0, 240),
    };
  });
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const discoveryContext = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'zh-CN' });
  const loginPage = await discoveryContext.newPage();
  const discovered = await loginAndDiscover(loginPage);
  const discoveredCount = discovered.entries.length;
  const entries = targetActionId ? discovered.entries.filter((entry) => entry.actionId === targetActionId) : discovered.entries;
  const { sessionEntries } = discovered;
  if (targetActionId && !entries.length) throw new Error(`target action not found: ${targetActionId}`);
  await discoveryContext.close();

  const results = new Array(entries.length);
  let cursor = 0;
  let completed = 0;
  async function worker() {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'zh-CN' });
    await context.addInitScript((values) => {
      for (const [key, value] of Object.entries(values)) sessionStorage.setItem(key, String(value));
    }, sessionEntries);
    const page = await context.newPage();
    const runtimeErrors = [];
    page.on('pageerror', (error) => runtimeErrors.push(error.message));
    while (true) {
      const index = cursor;
      cursor += 1;
      if (index >= entries.length) break;
      const entry = entries[index];
      const routeBase = entry.authoritativeRoute.startsWith('/')
        ? entry.authoritativeRoute
        : entry.actionId
        ? `/a/${entry.actionId}`
        : `/s/${encodeURIComponent(entry.sceneKey)}`;
      const routeUrl = new URL(routeBase, baseUrl);
      if (!routeUrl.searchParams.has('db')) routeUrl.searchParams.set('db', dbName);
      if (entry.menuId && !routeUrl.searchParams.has('menu_id')) routeUrl.searchParams.set('menu_id', String(entry.menuId));
      const route = `${routeUrl.pathname}${routeUrl.search}${routeUrl.hash}`;
      runtimeErrors.length = 0;
      const started = Date.now();
      try {
        await page.goto(`${baseUrl}${route}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
        await page.locator('main').last().waitFor({ state: 'visible', timeout: 15000 });
        await page.waitForFunction(() => {
          const mains = Array.from(document.querySelectorAll('main'));
          const main = mains.filter((element) => element instanceof HTMLElement && element.offsetParent !== null).at(-1) || mains[0];
          const text = String(main?.textContent || '');
          return text.trim().length > 0 && !/加载中|正在加载|正在载入|Loading/.test(text);
        }, null, { timeout: 10000 }).catch(() => {});
        await page.waitForTimeout(1000);
        if (/\/(?:f|r)\//.test(new URL(page.url()).pathname)) {
          await page.waitForFunction(() => {
            const visibleMain = Array.from(document.querySelectorAll('main')).filter((element) => element instanceof HTMLElement && element.offsetParent !== null).at(-1);
            const text = String(visibleMain?.textContent || '');
            return /填写业务信息|查看业务信息/.test(text)
              && !/当前视图使用可读降级渲染/.test(text);
          }, null, { timeout: 15000 });
        }
        const facts = await collectVisualFacts(page);
        let screenshot = '';
        if (facts.listLike || targetActionId) {
          screenshot = path.join(artifactDir, 'screenshots', `${String(index + 1).padStart(3, '0')}-${safeName(entry.label)}.png`);
          await page.screenshot({ path: screenshot, fullPage: false });
        }
        results[index] = { index, ...entry, route, url: page.url(), elapsedMs: Date.now() - started, screenshot, runtimeErrors: [...runtimeErrors], ...facts };
      } catch (error) {
        results[index] = {
          index,
          ...entry,
          route,
          url: page.url(),
          elapsedMs: Date.now() - started,
          listLike: false,
          probeError: error instanceof Error ? error.message : String(error),
          runtimeErrors: [...runtimeErrors],
          bodySample: await page.locator('body').innerText({ timeout: 1000 }).catch(() => '').then((text) => String(text).replace(/\s+/g, ' ').trim().slice(0, 240)),
        };
      }
      completed += 1;
      if (completed % 10 === 0 || completed === entries.length) process.stdout.write(`[all-list-visual] ${completed}/${entries.length}\n`);
    }
    await context.close();
  }
  await Promise.all(Array.from({ length: concurrency }, () => worker()));
  await browser.close();

  const lists = results.filter((row) => row?.listLike);
  const signatures = {};
  for (const row of lists) {
    const signature = JSON.stringify({
      renderer: row.renderer?.active || '',
      toolbarFamilies: row.toolbarFamilies,
      tableShellCount: row.tableShellCount,
      buttonClasses: row.buttons?.map((button) => String(button.classes || '').split(/\s+/).filter((name) => /^(sc-btn|contract-chip|clear-btn|secondary|primary)/.test(name))).flat().sort(),
      buttonRadii: [...new Set(row.buttons?.map((button) => button.style.radius) || [])].sort(),
      searchRadius: row.search?.radius || '',
      paginationKinds: row.paginationKinds,
    });
    if (!signatures[signature]) signatures[signature] = [];
    signatures[signature].push(row.index);
  }
  const report = {
    schemaVersion: 'frontend_all_list_visual_audit.v1',
    baseUrl,
    dbName,
    discoveredCount,
    auditedCount: entries.length,
    listCount: lists.length,
    nonListCount: results.length - lists.length,
    errorCount: results.filter((row) => row?.probeError || row?.hasError || row?.runtimeErrors?.length).length,
    toolbarViolationCount: lists.reduce((total, row) => total + Number(row.toolbarActionViolations?.length || 0), 0),
    coordinationViolationCount: lists.reduce((total, row) => total
      + Number(row.viewSwitchViolations?.length || 0)
      + Number(row.englishEmptyCopy ? 1 : 0)
      + Number(row.transientListIdentity ? 1 : 0)
      + Number(Number(row.primaryActionCount || 0) > 1 ? 1 : 0), 0)
      + results.reduce((total, row) => total
        + Number(row?.nativeFileEnglish ? 1 : 0)
        + Number(row?.excessiveFormCommandBar ? 1 : 0), 0),
    signatureCount: Object.keys(signatures).length,
    signatures,
    results,
  };
  fs.writeFileSync(path.join(artifactDir, 'report.json'), `${JSON.stringify(report, null, 2)}\n`);
  process.stdout.write(`${JSON.stringify({ artifactDir, discoveredCount: report.discoveredCount, listCount: report.listCount, errorCount: report.errorCount, signatureCount: report.signatureCount, toolbarViolationCount: report.toolbarViolationCount, coordinationViolationCount: report.coordinationViolationCount })}\n`);
}

main().catch((error) => {
  console.error(`[frontend-all-list-visual-audit] ${error.stack || error.message}`);
  process.exitCode = 1;
});
