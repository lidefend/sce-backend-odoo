#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const require = createRequire(path.join(process.cwd(), 'frontend/apps/web/package.json'));
const { chromium } = require('playwright');

const baseUrl = String(process.env.FRONTEND_URL || 'http://127.0.0.1:18081').replace(/\/$/, '');
const db = process.env.DB_NAME || 'sc_demo';
const login = process.env.E2E_LOGIN || 'wutao';
const password = process.env.E2E_PASSWORD || '';
const actionId = Number(process.env.NORM_ACTION_ID || 852);
const menuId = Number(process.env.NORM_MENU_ID || 620);
const artifactDir = process.env.ARTIFACT_DIR || '/tmp/hierarchy-browser-layout-acceptance';

if (!password) throw new Error('E2E_PASSWORD is required');
fs.mkdirSync(artifactDir, { recursive: true });

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function box(locator, name) {
  const value = await locator.boundingBox();
  if (!value) throw new Error(`${name} has no bounding box`);
  return value;
}

function adjoining(left, right, tolerance = 1.5) {
  return Math.abs(left.x + left.width - right.x) <= tolerance;
}

function verticallyAdjoining(top, bottom, tolerance = 1.5) {
  return Math.abs(top.y + top.height - bottom.y) <= tolerance;
}

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1680, height: 960 }, deviceScaleFactor: 1 });
const consoleErrors = [];
const contractResponses = [];
page.on('console', (message) => { if (message.type() === 'error') consoleErrors.push(message.text()); });
page.on('pageerror', (error) => consoleErrors.push(error.message));
page.on('response', (response) => {
  const postData = response.request().postData() || '';
  if (postData.includes('ui.contract.v2')) contractResponses.push(response.json().catch(() => null));
});

function findHierarchyPresentation(value) {
  if (!value || typeof value !== 'object') return null;
  if (!Array.isArray(value) && value.semantic === 'hierarchy_browser') return value;
  for (const child of Array.isArray(value) ? value : Object.values(value)) {
    const found = findHierarchyPresentation(child);
    if (found) return found;
  }
  return null;
}

try {
  await page.goto(`${baseUrl}/login?db=${encodeURIComponent(db)}`, { waitUntil: 'networkidle', timeout: 45000 });
  await page.locator('input[autocomplete="username"]').fill(login);
  await page.locator('input[autocomplete="current-password"]').fill(password);
  const dbInput = page.locator('input[autocomplete="off"]');
  if (await dbInput.isEditable().catch(() => false)) await dbInput.fill(db);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForFunction(() => !window.location.pathname.includes('/login'), null, { timeout: 45000 });
  await page.evaluate((key) => window.localStorage.removeItem(key), `sc:hierarchy-browser:${actionId}:columns`);
  await page.goto(`${baseUrl}/a/${actionId}?menu_id=${menuId}`, { waitUntil: 'networkidle', timeout: 45000 });

  const browserSurface = page.locator('.hierarchy-browser');
  await browserSurface.waitFor({ timeout: 30000 });
  await browserSurface.getByText('共 35254 条', { exact: true }).waitFor({ timeout: 30000 });
  const rendererHost = page.locator('.action-surface-renderer-host');
  assert(await rendererHost.getAttribute('data-surface-semantic') === 'hierarchy_browser', 'surface semantic did not pass through the renderer registry');
  assert(await rendererHost.getAttribute('data-requested-renderer') === 'core.hierarchy_browser', 'hierarchy renderer was not requested through the registry');
  assert(await rendererHost.getAttribute('data-active-renderer') === 'core.hierarchy_browser', 'hierarchy renderer was not activated through the registry');
  assert(await rendererHost.getAttribute('data-renderer-status') === 'ready', 'hierarchy renderer is not marked ready');

  const toolbar = browserSurface.locator('.hierarchy-head');
  const layout = browserSurface.locator('.hierarchy-layout');
  const search = browserSurface.locator('.product-list-header__search');
  const tools = browserSurface.locator('.product-list-header__actions');
  const tree = browserSurface.locator('.hierarchy-tree');
  const list = browserSurface.locator('.hierarchy-list');
  const detail = browserSurface.locator('.hierarchy-detail');
  const leftHandle = browserSurface.locator('.hierarchy-resizer-left');
  const rightHandle = browserSurface.locator('.hierarchy-resizer-right');
  const detailHead = browserSurface.locator('.detail-head');
  const detailScroll = browserSurface.locator('.hierarchy-detail-scroll');
  const importButton = tools.getByRole('button', { name: '导入定额', exact: true });

  const controlStyles = await page.evaluate(() => {
    const read = (selector) => {
      const element = document.querySelector(selector);
      if (!(element instanceof HTMLElement)) throw new Error(`missing visual control: ${selector}`);
      const style = window.getComputedStyle(element);
      return {
        borderRadius: style.borderRadius,
        backgroundColor: style.backgroundColor,
        borderColor: style.borderColor,
        color: style.color,
        height: element.getBoundingClientRect().height,
      };
    };
    return {
      input: read('.hierarchy-browser .product-list-header__search input'),
      search: read('.hierarchy-browser .product-list-header__search button'),
      primary: read('.hierarchy-browser .product-list-header__actions .sc-btn-primary'),
      secondary: read('.hierarchy-browser .detail-head .sc-btn-secondary'),
    };
  });
  for (const [name, style] of Object.entries(controlStyles)) {
    assert(Number.parseFloat(style.borderRadius) >= 6, `${name} control did not receive the shared rounded shape: ${style.borderRadius}`);
  }
  assert(controlStyles.primary.backgroundColor !== 'rgba(0, 0, 0, 0)', 'primary action has no semantic background color');
  assert(controlStyles.primary.backgroundColor !== controlStyles.secondary.backgroundColor, 'primary and secondary action hierarchy is visually indistinguishable');
  assert(Math.abs(controlStyles.input.height - controlStyles.search.height) <= 1, 'search input and action height are not aligned');

  const initial = {
    toolbar: await box(toolbar, 'toolbar'),
    layout: await box(layout, 'layout'),
    search: await box(search, 'search'),
    tools: await box(tools, 'tools'),
    tree: await box(tree, 'tree'),
    leftHandle: await box(leftHandle, 'left handle'),
    list: await box(list, 'list'),
    rightHandle: await box(rightHandle, 'right handle'),
    detail: await box(detail, 'detail'),
    importButton: await box(importButton, 'import button'),
  };

  assert(initial.search.x >= initial.list.x - 2, 'search is not aligned to the middle column');
  assert(initial.search.x + initial.search.width <= initial.list.x + initial.list.width + 2, 'search exceeds the middle column');
  assert(initial.importButton.x >= initial.detail.x - 2, 'import action is not in the right column');
  assert(adjoining(initial.tree, initial.leftHandle), 'tree and left divider contain a gap');
  assert(adjoining(initial.leftHandle, initial.list), 'left divider and list contain a gap');
  assert(adjoining(initial.list, initial.rightHandle), 'list and right divider contain a gap');
  assert(adjoining(initial.rightHandle, initial.detail), 'right divider and detail contain a gap');
  assert(verticallyAdjoining(initial.toolbar, initial.layout), 'toolbar and three-pane workspace contain a vertical gap');
  const toolbarShadow = await toolbar.evaluate((element) => window.getComputedStyle(element).boxShadow);
  assert(toolbarShadow === 'none', `toolbar still has a local shadow: ${toolbarShadow}`);
  assert(initial.leftHandle.width <= 1.5 && initial.rightHandle.width <= 1.5, 'pane separators are not single-line dividers');

  const tableScroll = browserSurface.locator('.table-scroll');
  const pageScrollBefore = await page.evaluate(() => window.scrollY);
  const detailBeforeListScroll = await box(detail, 'detail before list scroll');
  await tableScroll.evaluate((element) => { element.scrollTop = 600; });
  await page.waitForTimeout(100);
  const listScrollTop = await tableScroll.evaluate((element) => element.scrollTop);
  const detailAfterListScroll = await box(detail, 'detail after list scroll');
  const pageScrollAfter = await page.evaluate(() => window.scrollY);
  assert(listScrollTop >= 590, `middle list did not scroll independently: ${listScrollTop}`);
  assert(Math.abs(detailAfterListScroll.y - detailBeforeListScroll.y) <= 1, 'detail pane moved out of the viewport with the list');
  assert(Math.abs(pageScrollAfter - pageScrollBefore) <= 1, 'page scrolled instead of the middle list');
  await page.screenshot({ path: path.join(artifactDir, 'hierarchy-layout-list-scrolled.png'), fullPage: true });
  await tableScroll.evaluate((element) => { element.scrollTop = 0; });
  await page.screenshot({ path: path.join(artifactDir, 'hierarchy-layout-default.png'), fullPage: true });

  const detailHeadBefore = await box(detailHead, 'detail header before detail scroll');
  const detailScrollBefore = await box(detailScroll, 'detail scroll body');
  assert(detailHeadBefore.y + detailHeadBefore.height <= detailScrollBefore.y + 1, 'detail header overlaps the detail scroll body');
  await detailScroll.evaluate((element) => { element.scrollTop = 500; });
  await page.waitForTimeout(100);
  const detailScrollTop = await detailScroll.evaluate((element) => element.scrollTop);
  const detailHeadAfter = await box(detailHead, 'detail header after detail scroll');
  assert(detailScrollTop > 0, 'detail body did not scroll independently');
  assert(Math.abs(detailHeadAfter.y - detailHeadBefore.y) <= 1, 'detail header moved with its scroll body');
  assert(detailHeadAfter.y + detailHeadAfter.height <= detailScrollBefore.y + 1, 'detail header obscures the scrolled detail body');
  await page.screenshot({ path: path.join(artifactDir, 'hierarchy-layout-detail-scrolled.png'), fullPage: true });
  await detailScroll.evaluate((element) => { element.scrollTop = 0; });

  await page.mouse.move(initial.leftHandle.x + initial.leftHandle.width / 2, initial.leftHandle.y + 120);
  await page.mouse.down();
  await page.mouse.move(initial.leftHandle.x + initial.leftHandle.width / 2 + 80, initial.leftHandle.y + 120, { steps: 5 });
  await page.mouse.up();

  const leftResized = await box(tree, 'resized tree');
  assert(Math.abs(leftResized.width - initial.tree.width - 80) <= 2, `left drag delta mismatch: ${initial.tree.width} -> ${leftResized.width}`);

  const rightBefore = await box(detail, 'detail before right drag');
  const rightHandleBefore = await box(rightHandle, 'right handle before drag');
  await page.mouse.move(rightHandleBefore.x + rightHandleBefore.width / 2, rightHandleBefore.y + 120);
  await page.mouse.down();
  await page.mouse.move(rightHandleBefore.x + rightHandleBefore.width / 2 - 60, rightHandleBefore.y + 120, { steps: 5 });
  await page.mouse.up();

  const rightResized = await box(detail, 'resized detail');
  assert(Math.abs(rightResized.width - rightBefore.width - 60) <= 2, `right drag delta mismatch: ${rightBefore.width} -> ${rightResized.width}`);
  const resizedList = await box(list, 'resized list');
  const resizedSearch = await box(search, 'resized search');
  assert(resizedSearch.x >= resizedList.x - 2 && resizedSearch.x + resizedSearch.width <= resizedList.x + resizedList.width + 2, 'resized search left the middle column');
  const stored = await page.evaluate(() => window.localStorage.getItem('sc:hierarchy-browser:852:columns'));
  assert(stored && stored.includes('left') && stored.includes('right'), 'resized widths were not persisted');
  await page.screenshot({ path: path.join(artifactDir, 'hierarchy-layout-resized.png'), fullPage: true });

  await page.reload({ waitUntil: 'networkidle', timeout: 45000 });
  await browserSurface.getByText('共 35254 条', { exact: true }).waitFor({ timeout: 30000 });
  const persistedTree = await box(tree, 'persisted tree');
  const persistedDetail = await box(detail, 'persisted detail');
  assert(Math.abs(persistedTree.width - leftResized.width) <= 2, 'left width was not restored after reload');
  assert(Math.abs(persistedDetail.width - rightResized.width) <= 2, 'right width was not restored after reload');

  const contractPayloads = (await Promise.all(contractResponses)).filter(Boolean);
  const presentation = contractPayloads.map(findHierarchyPresentation).find(Boolean);
  assert(presentation?.source === 'native_view_derived', 'browser did not receive the native-view-derived hierarchy contract');
  assert(presentation?.enabled === true, 'browser hierarchy contract is not enabled');
  assert(Array.isArray(presentation?.config?.tree?.levels) && presentation.config.tree.levels.length === 3, 'browser hierarchy contract does not contain three model-derived levels');

  await browserSurface.getByRole('button', { name: '打开', exact: true }).click();
  await page.waitForURL(/\/(?:f|r)\/sc\.norm\.item\/\d+(?:\?|$)/, { timeout: 30000 });
  await page.goBack({ waitUntil: 'networkidle', timeout: 45000 });
  await browserSurface.getByText('共 35254 条', { exact: true }).waitFor({ timeout: 30000 });
  await browserSurface.getByRole('button', { name: '导入定额', exact: true }).click();
  await page.waitForURL(/\/f\/sc\.norm\.import\.wizard\/new(?:\?|$)/, { timeout: 30000 });
  assert(consoleErrors.length === 0, `browser console errors: ${consoleErrors.join(' | ')}`);

  const report = { ok: true, contract: { source: presentation.source, enabled: presentation.enabled, levelCount: presentation.config.tree.levels.length }, renderer: { requested: 'core.hierarchy_browser', active: 'core.hierarchy_browser', status: 'ready' }, controlStyles, initial, resized: { tree: leftResized, list: resizedList, search: resizedSearch, detail: rightResized }, persisted: { tree: persistedTree, detail: persistedDetail }, stored };
  fs.writeFileSync(path.join(artifactDir, 'layout-report.json'), JSON.stringify(report, null, 2));
  process.stdout.write(`${JSON.stringify({ ok: true, artifactDir, initialTreeWidth: initial.tree.width, resizedTreeWidth: leftResized.width, initialDetailWidth: rightBefore.width, resizedDetailWidth: rightResized.width })}\n`);
} catch (error) {
  await page.screenshot({ path: path.join(artifactDir, 'acceptance-failure.png'), fullPage: true }).catch(() => {});
  throw error;
} finally {
  await browser.close();
}
