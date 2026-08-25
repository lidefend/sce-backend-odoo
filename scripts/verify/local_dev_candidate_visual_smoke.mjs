import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';

const baseUrl = String(process.env.FRONTEND_URL || '').replace(/\/$/, '');
const database = String(process.env.DB_NAME || '');
const login = String(process.env.E2E_LOGIN || '');
const password = String(process.env.E2E_PASSWORD || '');
const head = String(process.env.CANDIDATE_GIT_HEAD || '');
const routes = JSON.parse(process.env.CANDIDATE_VISUAL_ROUTES_JSON || '[]');
const outputDir = path.resolve('artifacts/playwright/local-dev-candidate-visual-smoke');

if (!baseUrl || !database || !login || !password || !/^[0-9a-f]{40}$/.test(head)) throw new Error('candidate visual identity is incomplete');
if (!Array.isArray(routes) || routes.length === 0 || routes.some((item) => !item || typeof item.name !== 'string' || !String(item.path || '').startsWith('/'))) {
  throw new Error('candidate visual routes must be a non-empty name/path array');
}

fs.mkdirSync(outputDir, { recursive: true });
const report = { head, baseUrl, database, login, mutationCount: 0, routes: [] };
const browser = await launchChromium({ headless: true });

async function loginPage(page) {
  await page.goto(`${baseUrl}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const inputs = page.locator('input');
  await inputs.nth(0).fill(login);
  await inputs.nth(1).fill(password);
  if (await inputs.nth(2).count() && !(await inputs.nth(2).isDisabled())) await inputs.nth(2).fill(database);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45000 });
  await page.locator('.layout-shell').waitFor({ timeout: 45000 });
}

async function waitForStableProductSurface(page) {
  await page.waitForFunction(() => {
    const pendingForm = document.querySelector('[data-workspace-primary-content][aria-busy="true"]');
    const pendingCollection = document.querySelector('.product-loading-shell[aria-busy="true"]');
    return !pendingForm && !pendingCollection;
  }, undefined, { timeout: 45000 });
  await page.evaluate(() => new Promise((resolve) => {
    requestAnimationFrame(() => requestAnimationFrame(resolve));
  }));
}

function isContractV2Response(response) {
  if (!response.url().includes('/api/v1/intent') || response.request().method() !== 'POST') return false;
  try {
    return JSON.parse(response.request().postData() || '{}').intent === 'ui.contract.v2';
  } catch {
    return false;
  }
}

function summarizeContractH1(payload) {
  const rows = [];
  const visit = (value) => {
    if (Array.isArray(value)) {
      value.forEach(visit);
      return;
    }
    if (!value || typeof value !== 'object') return;
    const type = String(value.type || value.kind || '').toLowerCase();
    if (type === 'h1') {
      const children = ['children', 'nodes', 'items'].flatMap((key) => Array.isArray(value[key]) ? value[key] : []);
      rows.push({
        label: String(value.string || value.label || value.title || ''),
        fields: children
          .filter((child) => child && typeof child === 'object' && String(child.type || child.kind || '').toLowerCase() === 'field')
          .map((child) => String(child.name || child.field || '')).filter(Boolean),
      });
    }
    Object.values(value).forEach(visit);
  };
  visit(payload);
  return rows.slice(0, 8);
}

function summarizeContractSelections(payload) {
  const rows = [];
  const visit = (value) => {
    if (Array.isArray(value)) {
      value.forEach(visit);
      return;
    }
    if (!value || typeof value !== 'object') return;
    if (Array.isArray(value.selection) && value.selection.length) {
      rows.push({
        name: String(value.name || value.field || value.fieldCode || ''),
        selection: value.selection.slice(0, 20),
      });
    }
    Object.values(value).forEach(visit);
  };
  visit(payload);
  return rows.slice(0, 80);
}

function summarizeContractSummaryItems(payload) {
  const rows = [];
  const visit = (value) => {
    if (Array.isArray(value)) {
      value.forEach(visit);
      return;
    }
    if (!value || typeof value !== 'object') return;
    if (Array.isArray(value.summary_items)) {
      value.summary_items.forEach((item) => {
        if (!item || typeof item !== 'object') return;
        rows.push({
          key: String(item.key || ''),
          label: String(item.label || item.key || ''),
          value: String(item.value ?? ''),
          tone: String(item.tone || 'neutral'),
        });
      });
    }
    Object.values(value).forEach(visit);
  };
  visit(payload);
  return rows;
}

function applyFirstContractSummaryFixture(payload, fixture) {
  let applied = false;
  const visit = (value) => {
    if (applied || !value || typeof value !== 'object') return;
    if (!Array.isArray(value) && Array.isArray(value.summary_items)) {
      value.summary_items = fixture;
      applied = true;
      return;
    }
    for (const child of Object.values(value)) visit(child);
  };
  visit(payload);
  return applied;
}

function normalizeSummaryTone(value) {
  const normalized = typeof value === 'string' ? value.trim() : '';
  return ['neutral', 'danger', 'warning', 'success', 'info'].includes(normalized) ? normalized : 'neutral';
}

function summarizeContractAggregates(payload) {
  const rows = [];
  const visit = (value) => {
    if (Array.isArray(value)) {
      value.forEach(visit);
      return;
    }
    if (!value || typeof value !== 'object') return;
    if (String(value.aggregate || '').toLowerCase() === 'sum') {
      rows.push({
        name: String(value.name || value.field || ''),
        valueField: String(value.value_field || value.valueField || ''),
        aggregationField: String(value.aggregation_field || value.aggregationField || ''),
      });
    }
    Object.values(value).forEach(visit);
  };
  visit(payload);
  return rows.slice(0, 40);
}

function summarizeListAggregates(payload) {
  const rows = [];
  const visit = (value) => {
    if (Array.isArray(value)) {
      value.forEach(visit);
      return;
    }
    if (!value || typeof value !== 'object') return;
    if (value.aggregates && typeof value.aggregates === 'object' && !Array.isArray(value.aggregates)) {
      for (const [field, aggregate] of Object.entries(value.aggregates)) {
        rows.push({ field, aggregate });
      }
    }
    Object.values(value).forEach(visit);
  };
  visit(payload);
  return rows.slice(0, 40);
}

function isApiDataListResponse(response) {
  if (!response.url().includes('/api/v1/intent') || response.request().method() !== 'POST') return false;
  try {
    const body = JSON.parse(response.request().postData() || '{}');
    return body.intent === 'api.data' && body?.params?.op === 'list';
  } catch {
    return false;
  }
}

try {
  for (const viewport of [{ name: 'desktop', width: 1440, height: 960 }, { name: 'mobile', width: 390, height: 844 }]) {
    const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height }, locale: 'zh-CN' });
    const page = await context.newPage();
    const errors = [];
    page.on('console', (message) => { if (message.type() === 'error' && !message.text().includes('favicon')) errors.push(`console:${message.text()}`); });
    page.on('pageerror', (error) => errors.push(`page:${error.message}`));
    page.on('response', (response) => { if (response.status() >= 400 && response.url().includes('/api/')) errors.push(`http:${response.status()}:${response.url()}`); });
    page.on('request', (request) => {
      if (request.method() !== 'POST') return;
      let body = {};
      try { body = JSON.parse(request.postData() || '{}'); } catch {}
      const intent = String(body.intent || '');
      const method = String(body?.params?.method || body.method || '');
      if (/(^|\.)(create|write|unlink|execute_button|upload)(\.|$)/.test(intent) || /^(create|write|unlink|web_save|action_)/.test(method)) report.mutationCount += 1;
    });
    const bootSummaryFixtureTarget = routes.find((target) => Array.isArray(target.summaryFixture));
    let bootSummaryFixtureApplied = false;
    let bootSummaryItems = [];
    const bootContractRoutePattern = '**/api/v1/intent';
    const bootContractRouteHandler = async (route) => {
      const request = route.request();
      if (request.method() !== 'POST' || bootSummaryFixtureApplied) {
        await route.continue();
        return;
      }
      const response = await route.fetch();
      try {
        const payload = await response.json();
        bootSummaryFixtureApplied = applyFirstContractSummaryFixture(payload, bootSummaryFixtureTarget.summaryFixture);
        bootSummaryItems = summarizeContractSummaryItems(payload);
        await route.fulfill({ response, json: payload });
      } catch {
        await route.fulfill({ response });
      }
    };
    if (bootSummaryFixtureTarget) await page.route(bootContractRoutePattern, bootContractRouteHandler);
    await loginPage(page);
    if (bootSummaryFixtureTarget) await page.unroute(bootContractRoutePattern, bootContractRouteHandler);
    if (viewport.name === 'desktop') {
      const companyTrigger = page.getByRole('button', { name: '公司空间：切换公司' });
      await companyTrigger.click();
      const companySearchRoot = page.locator('[data-semantic-component="ScInput"][data-semantic-layer="primitive"][aria-label="搜索公司"]');
      const companySearch = page.locator('input[data-semantic-component="ScInput"][data-semantic-layer="primitive"][aria-label="搜索公司"], [data-semantic-component="ScInput"][data-semantic-layer="primitive"][aria-label="搜索公司"] input');
      await companySearch.waitFor({ state: 'visible', timeout: 15000 });
      await companySearch.fill('__primitive_adapter_probe__');
      const inputContract = {
        rootCount: await companySearchRoot.count(),
        inputCount: await companySearch.count(),
        value: await companySearch.inputValue(),
      };
      report.routes.push({ viewport: viewport.name, primitiveInputContract: inputContract });
      await companySearch.fill('');
    }
    for (const target of routes) {
      const summaryFixture = Array.isArray(target.summaryFixture) ? target.summaryFixture : null;
      let contractH1Nodes = [];
      let contractSelections = [];
      let contractAggregates = [];
      let contractSummaryItems = [];
      let listAggregates = [];
      const contractResponse = /^\/(?:a|r|f)\//.test(target.path)
        ? page.waitForResponse(isContractV2Response, { timeout: 45000 })
        : null;
      const listDataResponse = target.captureCollectionAggregate === true
        ? page.waitForResponse(isApiDataListResponse, { timeout: 45000 })
        : null;
      await page.goto(`${baseUrl}${target.path}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
      if (contractResponse) {
        const response = await contractResponse;
        if (!response.ok()) throw new Error(`contract request failed: ${response.status()} ${target.path}`);
        const contractPayload = await response.json();
        contractH1Nodes = summarizeContractH1(contractPayload);
        contractSelections = summarizeContractSelections(contractPayload);
        contractAggregates = summarizeContractAggregates(contractPayload);
        contractSummaryItems = summarizeContractSummaryItems(contractPayload);
      }
      if (summaryFixture && bootSummaryFixtureTarget === target) contractSummaryItems = bootSummaryItems;
      if (listDataResponse) {
        const response = await listDataResponse;
        if (!response.ok()) throw new Error(`list data request failed: ${response.status()} ${target.path}`);
        listAggregates = summarizeListAggregates(await response.json());
      }
      await page.locator('.layout-shell').waitFor({ timeout: 45000 });
      await page.locator('[data-product-page-mode], main').first().waitFor({ timeout: 45000 });
      await waitForStableProductSurface(page);
      const result = await page.evaluate(() => {
        const root = document.documentElement;
        const style = getComputedStyle(root);
        return {
          h1: document.querySelectorAll('h1').length,
          pageHeaders: document.querySelectorAll('.template-page-header, [data-product-page-header]').length,
          primaryActions: document.querySelectorAll('[data-primary-action]:not([hidden]), .sc-btn-primary:not([hidden])').length,
          overflow: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - window.innerWidth,
          tokenLoaded: Boolean(style.getPropertyValue('--sc-semantic-surface-interactive').trim()),
          nativeTitle: document.querySelector('.native-title-text')?.textContent?.trim() || '',
          visibleActions: [...document.querySelectorAll('main button, [data-workspace-primary-content] button')]
            .filter((element) => element instanceof HTMLElement && element.offsetParent !== null)
            .map((element) => ({
              label: element.textContent?.replace(/\s+/g, ' ').trim() || '',
              actionKey: element.getAttribute('data-action-key') || '',
              actionRef: element.getAttribute('data-action-ref') || '',
              backendIdentity: element.getAttribute('data-backend-identity') || '',
            }))
            .filter((entry) => entry.label)
            .slice(0, 80),
        };
      });
      const initialFinalUrl = page.url();
      await page.screenshot({ path: path.join(outputDir, `${viewport.name}-${target.name.replace(/[^a-zA-Z0-9_-]/g, '_')}.png`), fullPage: false });
      let collectionSelectionEvidence = null;
      let collectionSummaryEvidence = null;
      if (target.captureCollectionSummary === true) {
        const owners = page.locator('[data-semantic-component="CollectionSummaryStrip"]');
        const items = owners.locator('[data-summary-key]');
        const domItems = await items.evaluateAll((nodes) => nodes.map((node) => ({
          key: node.getAttribute('data-summary-key') || '',
          label: node.querySelector('.collection-summary-strip__label')?.textContent?.trim() || '',
          value: node.querySelector('.collection-summary-strip__value')?.textContent?.trim() || '',
          tone: node.getAttribute('data-summary-tone') || '',
        })));
        const expectedItems = contractSummaryItems.map((item) => ({
          key: item.key,
          label: item.label,
          value: item.value,
          tone: normalizeSummaryTone(item.tone),
        }));
        const ownerCount = await owners.count();
        collectionSummaryEvidence = {
          authorityItems: contractSummaryItems,
          expectedItems,
          ownerCount,
          domItems,
          fixtureApplied: summaryFixture ? bootSummaryFixtureApplied : null,
          pass: JSON.stringify(domItems) === JSON.stringify(expectedItems)
            && (contractSummaryItems.length > 0 ? ownerCount === 1 : ownerCount === 0)
            && (!summaryFixture || bootSummaryFixtureApplied),
        };
      }
      if (target.exerciseCollectionSelection === true) {
        const controls = page.locator('[data-semantic-component="CollectionSelectionControl"]:visible');
        const controlCount = await controls.count();
        if (controlCount < 1) throw new Error(`${target.name}: collection selection control is missing`);
        const rowControl = page.locator('[data-semantic-component="CollectionSelectionControl"][data-selection-scope="row"]:visible').first();
        if (await rowControl.count() !== 1) throw new Error(`${target.name}: collection row selection control is missing`);
        const rowInput = rowControl.locator('input[type="checkbox"]');
        const initialRowState = await rowControl.getAttribute('data-selection-state');
        const ariaLabel = await rowInput.getAttribute('aria-label');
        const touchTarget = await rowControl.boundingBox();
        await rowInput.focus();
        const focusContained = await rowControl.evaluate((node) => node.contains(document.activeElement));
        await rowControl.click();
        await page.waitForFunction(
          ({ label, state }) => [...document.querySelectorAll('[data-semantic-component="CollectionSelectionControl"]')]
            .some((node) => node instanceof HTMLElement && node.offsetParent !== null
              && node.querySelector('input')?.getAttribute('aria-label') === label
              && node.getAttribute('data-selection-state') === state),
          { label: ariaLabel, state: 'checked' },
          { timeout: 15000 },
        );
        const selectedRowState = await rowControl.getAttribute('data-selection-state');
        let selectedHeaderState = null;
        let headerIndeterminate = null;
        const headerControl = page.locator('[data-semantic-component="CollectionSelectionControl"]:visible:not([data-selection-scope="row"])').first();
        if (viewport.name === 'desktop' && await headerControl.count() === 1) {
          selectedHeaderState = await headerControl.getAttribute('data-selection-state');
          headerIndeterminate = await headerControl.locator('input[type="checkbox"]').evaluate((input) => input.indeterminate);
        }
        await rowControl.click();
        await page.waitForFunction(
          ({ label, state }) => [...document.querySelectorAll('[data-semantic-component="CollectionSelectionControl"]')]
            .some((node) => node instanceof HTMLElement && node.offsetParent !== null
              && node.querySelector('input')?.getAttribute('aria-label') === label
              && node.getAttribute('data-selection-state') === state),
          { label: ariaLabel, state: 'unchecked' },
          { timeout: 15000 },
        );
        const restoredRowState = await rowControl.getAttribute('data-selection-state');
        const restoredHeaderState = viewport.name === 'desktop' && await headerControl.count() === 1
          ? await headerControl.getAttribute('data-selection-state')
          : null;
        collectionSelectionEvidence = {
          controlCount, ariaLabel, touchTarget, focusContained, initialRowState, selectedRowState,
          selectedHeaderState, headerIndeterminate, restoredRowState, restoredHeaderState,
          pass: Boolean(ariaLabel) && focusContained && initialRowState === 'unchecked'
            && selectedRowState === 'checked' && restoredRowState === 'unchecked'
            && (viewport.name !== 'mobile' || (Number(touchTarget?.width || 0) >= 44 && Number(touchTarget?.height || 0) >= 44))
            && (viewport.name !== 'desktop' || (selectedHeaderState === 'mixed' && headerIndeterminate === true && restoredHeaderState === 'unchecked')),
        };
        if (!collectionSelectionEvidence.pass) throw new Error(`${target.name}: collection selection state contract failed`);
      }
      let collectionAggregateEvidence = null;
      if (target.exerciseCollectionAggregate === true) {
        const footers = page.locator('[data-semantic-component="CollectionAggregateFooter"]:visible');
        const footerCount = await footers.count();
        if (footerCount < 1) throw new Error(`${target.name}: collection aggregate footer is missing`);
        const contexts = await footers.evaluateAll((nodes) => nodes.map((node) => node.getAttribute('data-aggregate-context') || ''));
        const rows = footers.locator('[data-aggregate-scope]');
        const rowCount = await rows.count();
        const scopes = await rows.evaluateAll((nodes) => nodes.map((node) => node.getAttribute('data-aggregate-scope') || ''));
        const rowHeaderCount = await rows.locator('th[scope="row"], [data-aggregate-row-label]').count();
        const numericCells = rows.locator('.collection-aggregate-number');
        const numericCellCount = await numericCells.count();
        const misalignedNumericCells = await numericCells.evaluateAll((nodes) => nodes.filter((node) => getComputedStyle(node).textAlign !== 'right').length);
        const expectedContext = target.aggregateContext === 'group' ? 'group' : 'flat';
        collectionAggregateEvidence = {
          footerCount, contexts, rowCount, scopes, rowHeaderCount, numericCellCount, misalignedNumericCells,
          pass: footerCount >= 1
            && contexts.every((context) => context === expectedContext)
            && rowCount >= footerCount
            && scopes.every((scope) => scope === 'page' || scope === 'total')
            && rowHeaderCount === rowCount
            && numericCellCount > 0
            && misalignedNumericCells === 0,
        };
        if (!collectionAggregateEvidence.pass) throw new Error(`${target.name}: collection aggregate presentation contract failed`);
      }
      let collectionGroupHeaderEvidence = null;
      if (target.exerciseCollectionGroupHeader === true) {
        const headers = page.locator('[data-semantic-component="CollectionGroupHeader"]:visible');
        const headerCount = await headers.count();
        if (headerCount < 1) throw new Error(`${target.name}: collection group header is missing`);
        const header = headers.first();
        const groupKey = await header.getAttribute('data-group-key');
        const initialState = await header.getAttribute('data-group-state');
        const toggle = header.locator('.collection-group-header__toggle');
        const togglePrimitive = await toggle.getAttribute('data-semantic-component');
        const initialExpanded = await toggle.getAttribute('aria-expanded');
        const touchTarget = await toggle.boundingBox();
        await toggle.focus();
        const focusContained = await header.evaluate((node) => node.contains(document.activeElement));
        await toggle.click();
        const toggledState = initialState === 'collapsed' ? 'expanded' : 'collapsed';
        await page.waitForFunction(
          ({ key, state }) => [...document.querySelectorAll('[data-semantic-component="CollectionGroupHeader"]')]
            .some((node) => node.getAttribute('data-group-key') === key && node.getAttribute('data-group-state') === state),
          { key: groupKey, state: toggledState },
          { timeout: 15000 },
        );
        const toggledExpanded = await toggle.getAttribute('aria-expanded');
        await toggle.click();
        await page.waitForFunction(
          ({ key, state }) => [...document.querySelectorAll('[data-semantic-component="CollectionGroupHeader"]')]
            .some((node) => node.getAttribute('data-group-key') === key && node.getAttribute('data-group-state') === state),
          { key: groupKey, state: initialState },
          { timeout: 15000 },
        );
        const restoredExpanded = await toggle.getAttribute('aria-expanded');
        const openActions = header.locator('.collection-group-header__open');
        const openActionCount = await openActions.count();
        const openActionPrimitiveCount = await openActions.evaluateAll((nodes) =>
          nodes.filter((node) => node.getAttribute('data-semantic-component') === 'ScButton').length,
        );
        collectionGroupHeaderEvidence = {
          headerCount, groupKey, initialState, toggledState, togglePrimitive, initialExpanded,
          toggledExpanded, restoredExpanded, focusContained, touchTarget, openActionCount, openActionPrimitiveCount,
          pass: Boolean(groupKey)
            && (initialState === 'collapsed' || initialState === 'expanded')
            && togglePrimitive === 'ScButton'
            && toggledExpanded !== initialExpanded
            && restoredExpanded === initialExpanded
            && focusContained
            && openActionPrimitiveCount === openActionCount
            && (viewport.name !== 'mobile' || (Number(touchTarget?.width || 0) >= 44 && Number(touchTarget?.height || 0) >= 44)),
        };
        if (!collectionGroupHeaderEvidence.pass) throw new Error(`${target.name}: collection group header interaction contract failed`);
      }
      let mobileOverflowEvidence = null;
      if (viewport.name === 'mobile' && target.exerciseMobileOverflow === true) {
        const disclosure = page.locator('.form-header-mobile-actions');
        await disclosure.waitFor({ state: 'visible', timeout: 15000 });
        const expectedCount = Number(await disclosure.getAttribute('data-mobile-action-count') || 0);
        const expectedKeys = String(await disclosure.getAttribute('data-mobile-action-keys') || '').split(',').filter(Boolean);
        await disclosure.locator('summary').click();
        const panel = disclosure.locator('.form-header-mobile-actions__panel');
        await panel.waitFor({ state: 'visible', timeout: 15000 });
        const buttons = panel.locator('button[data-mobile-action-key]');
        const actualCount = await buttons.count();
        const actions = await buttons.evaluateAll((nodes) => nodes.map((node) => ({
          key: node.getAttribute('data-mobile-action-key') || '',
          label: node.textContent?.replace(/\s+/g, ' ').trim() || '',
          disabled: node instanceof HTMLButtonElement ? node.disabled : true,
          actionKey: node.getAttribute('data-action-key') || '',
          actionRef: node.getAttribute('data-action-ref') || '',
        })));
        await page.screenshot({ path: path.join(outputDir, `mobile-${target.name.replace(/[^a-zA-Z0-9_-]/g, '_')}-overflow-open.png`), fullPage: false });
        const beforeExit = page.url();
        const back = panel.locator('button[data-mobile-action-key="back:form.back"]');
        const backReachable = await back.count() === 1 && !(await back.isDisabled());
        if (backReachable) {
          await back.click();
          await page.waitForURL((url) => url.href !== beforeExit, { timeout: 15000 });
        }
        mobileOverflowEvidence = {
          expectedCount,
          actualCount,
          expectedKeys,
          actualKeys: actions.map((action) => action.key),
          actions,
          backReachable,
          exitUrl: page.url(),
          pass: expectedCount > 0 && actualCount === expectedCount
            && JSON.stringify(actions.map((action) => action.key)) === JSON.stringify(expectedKeys)
            && backReachable && page.url() !== beforeExit,
        };
      }
      let dialogLifecycleEvidence = null;
      if (viewport.name === 'desktop' && target.exerciseDialog === true) {
        const trigger = page.getByRole('button', { name: /^创建 API Key$/ }).first();
        await trigger.waitFor({ state: 'visible', timeout: 15000 });
        await trigger.focus();
        await trigger.click();
        const dialog = page.getByRole('dialog', { name: '创建机器 API Key' });
        await dialog.waitFor({ state: 'visible', timeout: 15000 });
        const focusContained = await dialog.evaluate((node) => node === document.activeElement || node.contains(document.activeElement));
        await page.screenshot({ path: path.join(outputDir, `desktop-${target.name.replace(/[^a-zA-Z0-9_-]/g, '_')}-dialog-open.png`), fullPage: false });
        await page.keyboard.press('Escape');
        await dialog.waitFor({ state: 'hidden', timeout: 15000 });
        const openerRestored = await trigger.evaluate((node) => node === document.activeElement);
        dialogLifecycleEvidence = { focusContained, openerRestored, closedByEscape: true, pass: focusContained && openerRestored };
      }
      let collectionToolbarEvidence = null;
      if (target.exerciseCollectionToolbar === true) {
        const toolbar = page.locator('[data-semantic-component="CollectionActionToolbar"]');
        await toolbar.waitFor({ state: 'visible', timeout: 15000 });
        const searchToggle = toolbar.getByRole('button', { name: /展开搜索菜单/ });
        await searchToggle.click();
        const searchLayer = toolbar.locator('[data-collection-toolbar-layer="search"]');
        await searchLayer.waitFor({ state: 'visible', timeout: 15000 });
        const searchFocusContained = await searchLayer.evaluate((node) => node.contains(document.activeElement));
        await page.keyboard.press('Escape');
        await searchLayer.waitFor({ state: 'hidden', timeout: 15000 });
        const searchFocusRestored = await searchToggle.evaluate((node) => node === document.activeElement);
        const rowCheckbox = viewport.name === 'mobile'
          ? page.locator('[data-mobile-record-select] input[type="checkbox"]').first()
          : page.locator('.desktop-record-table tbody input[type="checkbox"]').first();
        await rowCheckbox.check();
        const batchBar = page.locator('[data-semantic-component="CollectionBatchActionBar"]');
        await batchBar.waitFor({ state: 'visible', timeout: 15000 });
        const actionCount = Number(await batchBar.getAttribute('data-action-count') || 0);
        const directKeys = String(await batchBar.getAttribute('data-direct-action-keys') || '').split(',').filter(Boolean);
        const overflowKeys = String(await batchBar.getAttribute('data-overflow-action-keys') || '').split(',').filter(Boolean);
        const projectedKeys = await batchBar.locator('button[data-action-key]').evaluateAll((nodes) => nodes.map((node) => node.getAttribute('data-action-key') || '').filter(Boolean));
        let batchFocusContained = true;
        let batchFocusRestored = true;
        if (overflowKeys.length) {
          const batchToggle = batchBar.getByRole('button', { name: /更多批量操作/ });
          await batchToggle.click();
          const batchLayer = batchBar.locator('[data-collection-batch-layer="overflow"]');
          await batchLayer.waitFor({ state: 'visible', timeout: 15000 });
          batchFocusContained = await batchLayer.evaluate((node) => node.contains(document.activeElement));
          await page.keyboard.press('Escape');
          await batchLayer.waitFor({ state: 'hidden', timeout: 15000 });
          batchFocusRestored = await batchToggle.evaluate((node) => node === document.activeElement);
        }
        const uniqueKeys = [...new Set([...directKeys, ...overflowKeys])];
        collectionToolbarEvidence = {
          actionCount, directKeys, overflowKeys, projectedKeys,
          searchFocusContained, searchFocusRestored, batchFocusContained, batchFocusRestored,
          pass: searchFocusContained && searchFocusRestored && batchFocusContained && batchFocusRestored
            && directKeys.length <= 1
            && actionCount === directKeys.length + overflowKeys.length
            && uniqueKeys.length === actionCount
            && projectedKeys.length === directKeys.length,
        };
      }
      let collectionNavigationEvidence = null;
      if (target.exerciseCollectionNavigation === true) {
        const footer = page.locator('[data-semantic-component="CollectionPaginationFooter"]');
        await footer.waitFor({ state: 'visible', timeout: 15000 });
        const footerCount = await footer.count();
        const paginationMode = String(await footer.getAttribute('data-pagination-mode') || '');
        const columnHeaders = page.locator('[data-semantic-component="CollectionColumnHeaderControl"]');
        const columnHeaderCount = await columnHeaders.count();
        const invalidColumnRoots = await columnHeaders.evaluateAll((nodes) => nodes.filter((node) => node.tagName !== 'TH').length);
        const missingDragLabels = await columnHeaders.locator('.column-drag-handle:not([aria-label])').count();
        const missingResizeLabels = await columnHeaders.locator('.column-resize-handle:not([aria-label])').count();
        const groupingToolbarCount = await page.locator('[data-semantic-component="CollectionGroupingToolbar"]').count();
        const groupPageControlsCount = await page.locator('[data-semantic-component="CollectionGroupPageControls"]').count();
        collectionNavigationEvidence = {
          footerCount,
          paginationMode,
          columnHeaderCount,
          invalidColumnRoots,
          missingDragLabels,
          missingResizeLabels,
          groupingToolbarCount,
          groupPageControlsCount,
          pass: footerCount === 1
            && ['count', 'grouped', 'paged'].includes(paginationMode)
            && columnHeaderCount > 0
            && invalidColumnRoots === 0
            && missingDragLabels === 0
            && missingResizeLabels === 0,
        };
      }
      report.routes.push({ name: target.name, path: target.path, viewport: viewport.name, finalUrl: initialFinalUrl, contractH1Nodes, contractSelections, contractAggregates, contractSummaryItems, listAggregates, collectionSummaryEvidence, collectionSelectionEvidence, collectionAggregateEvidence, collectionGroupHeaderEvidence, mobileOverflowEvidence, dialogLifecycleEvidence, collectionToolbarEvidence, collectionNavigationEvidence, ...result });
    }
    report.routes.push({ viewport: viewport.name, errors });
    await context.close();
  }
} finally {
  await browser.close();
}

const errors = report.routes.flatMap((item) => item.errors || []);
const failures = report.routes.filter((item) => item.path && (!item.tokenLoaded || item.h1 !== 1 || item.overflow > 0));
for (const item of report.routes) {
  if (item.mobileOverflowEvidence && !item.mobileOverflowEvidence.pass) failures.push({ name: item.name, mobileOverflowEvidence: item.mobileOverflowEvidence });
  if (item.collectionSelectionEvidence && !item.collectionSelectionEvidence.pass) failures.push({ name: item.name, collectionSelectionEvidence: item.collectionSelectionEvidence });
  if (item.collectionSummaryEvidence && !item.collectionSummaryEvidence.pass) failures.push({ name: item.name, collectionSummaryEvidence: item.collectionSummaryEvidence });
  if (item.collectionAggregateEvidence && !item.collectionAggregateEvidence.pass) failures.push({ name: item.name, collectionAggregateEvidence: item.collectionAggregateEvidence });
  if (item.collectionGroupHeaderEvidence && !item.collectionGroupHeaderEvidence.pass) failures.push({ name: item.name, collectionGroupHeaderEvidence: item.collectionGroupHeaderEvidence });
  if (item.dialogLifecycleEvidence && !item.dialogLifecycleEvidence.pass) failures.push({ name: item.name, dialogLifecycleEvidence: item.dialogLifecycleEvidence });
  if (item.collectionToolbarEvidence && !item.collectionToolbarEvidence.pass) failures.push({ name: item.name, collectionToolbarEvidence: item.collectionToolbarEvidence });
  if (item.collectionNavigationEvidence && !item.collectionNavigationEvidence.pass) failures.push({ name: item.name, collectionNavigationEvidence: item.collectionNavigationEvidence });
}
const primitiveInput = report.routes.find((item) => item.primitiveInputContract)?.primitiveInputContract;
if (!primitiveInput || primitiveInput.rootCount !== 1 || primitiveInput.inputCount !== 1 || primitiveInput.value !== '__primitive_adapter_probe__') {
  failures.push({ primitiveInputContract: primitiveInput || null });
}
report.pass = errors.length === 0 && report.mutationCount === 0 && failures.length === 0;
report.errors = errors;
report.failures = failures;
fs.writeFileSync(path.join(outputDir, 'summary.json'), `${JSON.stringify(report, null, 2)}\n`);
console.log(JSON.stringify({ pass: report.pass, mutationCount: report.mutationCount, errors, failures }, null, 2));
if (!report.pass) process.exit(1);
