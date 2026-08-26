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

function applyFirstContractSummaryFixture(payload, fixture, sceneKey) {
  let applied = false;
  const visit = (value) => {
    if (applied || !value || typeof value !== 'object') return;
    const sceneReady = !Array.isArray(value) && value.scene_ready_contract && typeof value.scene_ready_contract === 'object'
      ? value.scene_ready_contract
      : null;
    if (sceneReady && Array.isArray(sceneReady.scenes) && sceneKey) {
      const scene = sceneReady.scenes.find((item) => {
        if (!item || typeof item !== 'object') return false;
        return String(item.scene?.key || item.page?.scene_key || '').trim() === sceneKey;
      });
      if (scene) {
        const projection = scene.projection && typeof scene.projection === 'object' && !Array.isArray(scene.projection)
          ? scene.projection
          : {};
        scene.projection = { ...projection, summary_items: fixture };
        applied = true;
        return;
      }
    }
    if (!Array.isArray(value) && Array.isArray(value.summary_items)) {
      value.summary_items = fixture;
      applied = true;
      return;
    }
    if (!Array.isArray(value) && Array.isArray(value.scenes) && sceneKey) {
      const scene = value.scenes.find((item) => {
        if (!item || typeof item !== 'object') return false;
        return String(item.scene?.key || item.page?.scene_key || item.key || item.scene_key || item.code || '').trim() === sceneKey;
      });
      if (scene) {
        const projection = scene.projection && typeof scene.projection === 'object' && !Array.isArray(scene.projection)
          ? scene.projection
          : {};
        scene.projection = { ...projection, summary_items: fixture };
        applied = true;
        return;
      }
    }
    if (!Array.isArray(value) && value.projection && typeof value.projection === 'object' && !Array.isArray(value.projection)) {
      value.projection.summary_items = fixture;
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

function applyActionSceneIdentityFixture(payload, actionId, sceneKey) {
  let applied = 0;
  const visit = (value) => {
    if (Array.isArray(value)) {
      value.forEach(visit);
      return;
    }
    if (!value || typeof value !== 'object') return;
    if (Number(value.action_id || 0) === actionId) {
      value.scene_key = sceneKey;
      applied += 1;
    }
    Object.values(value).forEach(visit);
  };
  visit(payload);
  return applied;
}

function collectSummaryCarrierPaths(payload) {
  const paths = [];
  const visit = (value, pathParts) => {
    if (!value || typeof value !== 'object' || paths.length >= 80) return;
    for (const [key, child] of Object.entries(value)) {
      const next = [...pathParts, key];
      if (['scene_ready_contract', 'scenes', 'projection', 'summary_items'].includes(key)) paths.push(next.join('.'));
      visit(child, next);
    }
  };
  visit(payload, []);
  return paths;
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
    let bootSummaryActionIdentityApplied = 0;
    let bootSummaryItems = [];
    const bootSummaryCarrierPaths = new Set();
    let bootSummaryRoutesInFlight = 0;
    const bootContractRoutePattern = '**/api/v1/**';
    const bootContractRouteHandler = async (route) => {
      const request = route.request();
      if (request.method() !== 'POST') {
        await route.continue();
        return;
      }
      try {
        bootSummaryRoutesInFlight += 1;
        const response = await route.fetch();
        let payload = null;
        try {
          payload = await response.json();
          collectSummaryCarrierPaths(payload).forEach((path) => bootSummaryCarrierPaths.add(path));
        } catch {
          await route.fulfill({ response });
        }
        if (!payload) return;
        const summaryApplied = applyFirstContractSummaryFixture(
          payload,
          bootSummaryFixtureTarget.summaryFixture,
          String(bootSummaryFixtureTarget.summaryFixtureSceneKey || '').trim(),
        );
        bootSummaryFixtureApplied = bootSummaryFixtureApplied || summaryApplied;
        const fixtureActionId = Number(bootSummaryFixtureTarget.summaryFixtureActionId || 0);
        if (fixtureActionId > 0) {
          bootSummaryActionIdentityApplied += applyActionSceneIdentityFixture(
            payload,
            fixtureActionId,
            String(bootSummaryFixtureTarget.summaryFixtureSceneKey || '').trim(),
          );
        }
        const responseSummaryItems = summarizeContractSummaryItems(payload);
        if (responseSummaryItems.length) bootSummaryItems = responseSummaryItems;
        await route.fulfill({ response, json: payload });
      } finally {
        bootSummaryRoutesInFlight -= 1;
      }
    };
    if (bootSummaryFixtureTarget) await page.route(bootContractRoutePattern, bootContractRouteHandler);
    await loginPage(page);
    if (viewport.name === 'desktop') {
      const revealSidebar = page.getByRole('button', { name: '显示侧边栏', exact: true });
      if (await revealSidebar.count() === 1) {
        await revealSidebar.click();
        await page.locator('#primary-sidebar').waitFor({ state: 'visible', timeout: 15000 });
      }
      const navigationSearchRoot = page.locator('#primary-sidebar [data-semantic-component="ScInput"][data-semantic-layer="primitive"]').filter({ visible: true }).first();
      const navigationSearch = navigationSearchRoot.locator('input').first();
      await navigationSearch.waitFor({ state: 'visible', timeout: 15000 });
      await navigationSearch.fill('__primitive_adapter_probe__');
      const inputContract = {
        rootCount: await navigationSearchRoot.count(),
        inputCount: await navigationSearch.count(),
        value: await navigationSearch.inputValue(),
      };
      report.routes.push({ viewport: viewport.name, primitiveInputContract: inputContract });
      await navigationSearch.fill('');
    }
    for (const target of routes) {
      const summaryFixture = Array.isArray(target.summaryFixture) ? target.summaryFixture : null;
      let contractH1Nodes = [];
      let contractSelections = [];
      let contractAggregates = [];
      let contractSummaryItems = [];
      let listAggregates = [];
      const contractResponse = target.expectContractResponse !== false && /^\/(?:a|r|f)\//.test(target.path)
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
      await page.locator('[data-product-page-mode], main').filter({ visible: true }).first().waitFor({ timeout: 45000 });
      await waitForStableProductSurface(page);
      if (bootSummaryFixtureTarget === target) {
        while (bootSummaryRoutesInFlight > 0) await new Promise((resolve) => setTimeout(resolve, 10));
        await page.unroute(bootContractRoutePattern, bootContractRouteHandler);
      }
      const result = await page.evaluate(() => {
        const root = document.documentElement;
        const style = getComputedStyle(root);
        const primitiveDrivers = [
          ['ScButton', '.t-button'],
          ['ScInput', '.t-input'],
          ['ScTextarea', '.t-textarea'],
          ['ScSelect', '.t-select'],
          ['ScCheckbox', '.t-checkbox'],
        ].map(([component, driverSelector]) => {
          const nodes = [...document.querySelectorAll(`[data-semantic-component="${component}"][data-primitive-driver="tdesign"], [data-semantic-component="${component}"]:not([data-primitive-driver])`)];
          return {
            component,
            count: nodes.length,
            missingDriverCount: nodes.filter((node) => !node.matches(driverSelector) && !node.querySelector(driverSelector)).length,
          };
        });
        const overlayResidues = [...document.querySelectorAll('.t-drawer, .t-drawer__mask, .t-dialog, .t-dialog__mask, [data-overlay-kind]')]
          .filter((node) => {
            const nodeStyle = getComputedStyle(node);
            const rect = node.getBoundingClientRect();
            return nodeStyle.display !== 'none' && nodeStyle.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
          })
          .map((node) => {
            const rect = node.getBoundingClientRect();
            return {
              tag: node.tagName,
              className: typeof node.className === 'string' ? node.className : '',
              overlayKind: node.getAttribute('data-overlay-kind') || '',
              state: node.getAttribute('data-state') || '',
              ariaHidden: node.getAttribute('aria-hidden'),
              rect: [Math.round(rect.left), Math.round(rect.top), Math.round(rect.right), Math.round(rect.bottom)],
            };
          });
        const publishedApps = [...document.querySelectorAll('.published-apps__list .published-app')]
          .filter((node) => node instanceof HTMLElement && node.offsetParent !== null)
          .map((node) => {
            const content = node.querySelector('.sc-btn__content');
            const mark = node.querySelector('.published-app__mark');
            const label = node.querySelector('.published-app__label');
            const contentStyle = content ? getComputedStyle(content) : null;
            const markRect = mark?.getBoundingClientRect();
            const labelRect = label?.getBoundingClientRect();
            return {
              label: label?.textContent?.trim() || '',
              contentDisplay: contentStyle?.display || '',
              contentColumns: contentStyle?.gridTemplateColumns || '',
              labelWidth: Math.round(labelRect?.width || 0),
              ordered: Boolean(markRect && labelRect && labelRect.left >= markRect.right),
            };
          });
        const navigationSearch = document.querySelector('.product-side-navigation__search [data-semantic-component="ScInput"]');
        const navigationSearchPrefix = navigationSearch?.querySelector('.t-input__prefix-icon');
        const navigationSearchInput = navigationSearch?.querySelector('input');
        return {
          h1: document.querySelectorAll('h1').length,
          pageHeaders: document.querySelectorAll('.template-page-header, [data-product-page-header]').length,
          primaryActions: [...document.querySelectorAll('[data-product-primary-action]')]
            .filter((node) => node instanceof HTMLElement && node.offsetParent !== null).length,
          presentationModes: [...new Set([...document.querySelectorAll('[data-product-page-pattern][data-presentation-mode]')].map((node) => node.getAttribute('data-presentation-mode')).filter(Boolean))],
          nativeStructureCount: document.querySelectorAll('[data-native-contract-structure]').length,
          nativeNotebookPageCount: document.querySelectorAll('[data-native-contract-structure] .t-tabs__nav-item').length,
          overflow: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - window.innerWidth,
          tokenLoaded: Boolean(style.getPropertyValue('--sc-semantic-surface-interactive').trim()),
          nativeTitle: document.querySelector('.native-title-text')?.textContent?.trim() || '',
          primitiveDriverEvidence: {
            drivers: primitiveDrivers,
            specializedInputCount: document.querySelectorAll('[data-semantic-component="ScInput"][data-primitive-driver="browser-specialized"]').length,
            pass: primitiveDrivers.every((entry) => entry.missingDriverCount === 0),
          },
          overlayResidueEvidence: {
            residues: overlayResidues,
            activeElement: document.activeElement instanceof HTMLElement ? {
              tag: document.activeElement.tagName,
              className: document.activeElement.className,
              semantic: document.activeElement.getAttribute('data-semantic-component') || '',
            } : null,
            pass: overlayResidues.length === 0,
          },
          shellAdapterEvidence: {
            publishedApps,
            navigationSearchCount: navigationSearch ? 1 : 0,
            navigationSearchPrefixCount: navigationSearchPrefix ? 1 : 0,
            navigationSearchInputCount: navigationSearchInput ? 1 : 0,
            pass: publishedApps.length > 0
              && publishedApps.every((entry) => entry.label && entry.contentDisplay === 'grid' && entry.contentColumns !== 'none' && entry.labelWidth >= 32 && entry.ordered)
              && Boolean(navigationSearch && navigationSearchPrefix && navigationSearchInput),
          },
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
      let sidebarScrollEvidence = null;
      if (target.exerciseSidebarScroll === true && viewport.name === 'desktop') {
        const originalViewport = page.viewportSize();
        await page.setViewportSize({ width: originalViewport?.width || 1440, height: Math.min(originalViewport?.height || 960, 600) });
        await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
        sidebarScrollEvidence = await page.evaluate(() => {
          const sidebar = document.querySelector('#primary-sidebar');
          const owner = document.querySelector('#primary-sidebar .product-side-navigation__tree');
          if (!(sidebar instanceof HTMLElement) || !(owner instanceof HTMLElement)) return { pass: false, reason: 'scroll_owner_missing' };
          const sidebarStyle = getComputedStyle(sidebar);
          const ownerStyle = getComputedStyle(owner);
          const menuOwner = owner.querySelector('.t-menu--scroll');
          const scrollOwner = menuOwner instanceof HTMLElement ? menuOwner : owner;
          const scrollOwnerStyle = getComputedStyle(scrollOwner);
          scrollOwner.scrollTop = scrollOwner.scrollHeight;
          const observedScrollTop = scrollOwner.scrollTop;
          scrollOwner.scrollTop = 0;
          return {
            viewportHeight: window.innerHeight,
            sidebarHeight: sidebar.clientHeight,
            sidebarDisplay: sidebarStyle.display,
            ownerClientHeight: owner.clientHeight,
            ownerScrollHeight: owner.scrollHeight,
            ownerScrollTop: owner.scrollTop,
            ownerOverflowY: ownerStyle.overflowY,
            scrollOwnerClass: scrollOwner.className,
            scrollOwnerClientHeight: scrollOwner.clientHeight,
            scrollOwnerScrollHeight: scrollOwner.scrollHeight,
            scrollOwnerScrollTop: observedScrollTop,
            scrollOwnerOverflowY: scrollOwnerStyle.overflowY,
            pass: sidebar.clientHeight <= window.innerHeight
              && sidebarStyle.display === 'grid'
              && ownerStyle.overflowY === 'auto'
              && ['auto', 'scroll'].includes(scrollOwnerStyle.overflowY)
              && scrollOwner.scrollHeight > scrollOwner.clientHeight
              && observedScrollTop > 0,
          };
        });
      }
      let nativeActionPresentationEvidence = null;
      if (target.exerciseNativeActionOverflow === true) {
        const smartActions = page.locator('[data-semantic-component="NativeSmartAction"]:visible');
        const overflow = page.locator('[data-semantic-component="NativeActionOverflowMenu"]:visible').first();
        const trigger = overflow.locator('[aria-haspopup="menu"]');
        const smartActionCount = await smartActions.count();
        const overflowCount = await page.locator('[data-semantic-component="NativeActionOverflowMenu"]:visible').count();
        if (smartActionCount < 1 || overflowCount < 1 || await trigger.count() !== 1) {
          throw new Error(`${target.name}: governed native smart action overflow is missing`);
        }
        const initialExpanded = await trigger.getAttribute('aria-expanded');
        await trigger.click();
        const menu = overflow.locator('[role="menu"]');
        await menu.waitFor({ state: 'visible', timeout: 15000 });
        const menuId = await menu.getAttribute('id');
        const controls = await trigger.getAttribute('aria-controls');
        const menuItemCount = await menu.locator('[role="menuitem"]').count();
        await trigger.press('Escape');
        await menu.waitFor({ state: 'hidden', timeout: 15000 });
        const restoredExpanded = await trigger.getAttribute('aria-expanded');
        const focusRestored = await trigger.evaluate((node) => node === document.activeElement);
        nativeActionPresentationEvidence = {
          smartActionCount, overflowCount, initialExpanded, menuId, controls, menuItemCount,
          restoredExpanded, focusRestored,
          pass: initialExpanded === 'false'
            && Boolean(menuId)
            && controls === menuId
            && menuItemCount > 0
            && restoredExpanded === 'false'
            && focusRestored,
        };
        if (!nativeActionPresentationEvidence.pass) throw new Error(`${target.name}: native action disclosure semantics failed`);
      }
      await page.screenshot({ path: path.join(outputDir, `${viewport.name}-${target.name.replace(/[^a-zA-Z0-9_-]/g, '_')}.png`), fullPage: false });
      let relationSearchDialogEvidence = null;
      if (target.captureRelationSearchDialog === true) {
        const relations = page.locator('.many2one-combobox:visible');
        const relationCount = await relations.count();
        let searchMore = null;
        for (let index = 0; index < relationCount; index += 1) {
          const relation = relations.nth(index);
          await relation.locator('input').focus();
          const candidate = relation.locator('.many2one-action:visible').filter({ hasText: /搜索更多/ }).first();
          if (await candidate.count() === 1) {
            searchMore = candidate;
            break;
          }
        }
        if (!searchMore) throw new Error(`${target.name}: no visible relation field declares search-more capability`);
        await searchMore.click();
        const dialog = page.locator('[data-professional-relation-lifecycle="search"]:visible');
        await dialog.waitFor({ state: 'visible', timeout: 15000 });
        const panel = page.locator('.relation-dialog:visible');
        await panel.waitFor({ state: 'visible', timeout: 15000 });
        await dialog.locator('[data-semantic-component="ScInput"] input[type="search"]').waitFor({ state: 'visible', timeout: 15000 });
        await dialog.locator('[data-semantic-component="RelationSearchResult"]:visible, [data-semantic-component="ScEmptyState"]:visible').first().waitFor({ state: 'visible', timeout: 15000 });
        const visibleResults = dialog.locator('[data-semantic-component="RelationSearchResult"]:visible');
        const resultCount = await visibleResults.count();
        const resultLayouts = await visibleResults.evaluateAll((nodes) => nodes.map((node) => ({
          layout: node.getAttribute('data-semantic-layout') || '',
          recordId: node.getAttribute('data-record-id') || '',
          role: node.getAttribute('role') || '',
          tabIndex: node.getAttribute('tabindex') || '',
          selected: node.getAttribute('aria-selected') || '',
        })));
        let keyboardSelected = null;
        if (resultCount > 0) {
          const firstResult = visibleResults.first();
          await firstResult.focus();
          await firstResult.press('Space');
          keyboardSelected = await firstResult.getAttribute('aria-selected');
        }
        const dialogBox = await panel.boundingBox();
        const listboxCount = await dialog.locator('[role="listbox"]:visible').count();
        const searchInputCount = await dialog.locator('[data-semantic-component="ScInput"] input[type="search"]:visible').count();
        const primaryCount = await dialog.locator('.relation-dialog-footer .sc-btn-primary:visible:not(:disabled)').count();
        const footerActionLabels = await dialog.locator('.relation-dialog-footer-actions button:visible').allTextContents();
        relationSearchDialogEvidence = {
          resultCount, resultLayouts, keyboardSelected, listboxCount, searchInputCount, primaryCount,
          footerActionLabels: footerActionLabels.map((label) => label.replace(/\s+/g, ' ').trim()),
          width: Math.round(dialogBox?.width || 0),
          pass: resultCount > 0
            && resultLayouts.every((item) => item.recordId && item.role === 'option' && item.tabIndex === '0')
            && keyboardSelected === 'true'
            && listboxCount === 1
            && searchInputCount === 1
            && primaryCount === 1
            && (viewport.name !== 'desktop' || Number(dialogBox?.width || 0) >= 800)
            && Number(dialogBox?.width || 0) <= viewport.width,
        };
        await page.screenshot({ path: path.join(outputDir, `${viewport.name}-${target.name.replace(/[^a-zA-Z0-9_-]/g, '_')}-relation-dialog.png`), fullPage: false });
        await page.keyboard.press('Escape');
        await dialog.waitFor({ state: 'hidden', timeout: 15000 });
      }
      let collectionSelectionEvidence = null;
      let collectionSummaryEvidence = null;
      let collectionMobileRecordEvidence = null;
      let collectionKanbanEvidence = null;
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
          actionIdentityFixtureApplied: summaryFixture ? bootSummaryActionIdentityApplied : null,
          fixtureCarrierPaths: summaryFixture ? [...bootSummaryCarrierPaths] : [],
          pass: JSON.stringify(domItems) === JSON.stringify(expectedItems)
            && (contractSummaryItems.length > 0 ? ownerCount === 1 : ownerCount === 0)
            && (!summaryFixture || (
              bootSummaryFixtureApplied
              && (!target.summaryFixtureActionId || bootSummaryActionIdentityApplied > 0)
            )),
        };
      }
      if (target.captureCollectionMobileRecords === true && viewport.name === 'mobile') {
        const rows = await page.locator('[data-semantic-component="CollectionMobileRecordRow"]:visible').evaluateAll((nodes) => nodes.map((node) => {
          const card = node.querySelector('button.collection-mobile-record-row__card');
          const selection = node.querySelector('[data-semantic-component="CollectionSelectionControl"]');
          const selectionRect = selection?.getBoundingClientRect();
          return {
            recordKey: node.getAttribute('data-record-key') || '',
            selectionState: node.getAttribute('data-selection-state') || '',
            role: node.getAttribute('role') || '',
            ariaSelected: node.getAttribute('aria-selected') || '',
            identity: node.querySelector('.collection-mobile-record-row__identity')?.textContent?.trim() || '',
            status: node.querySelector('.sc-badge')?.textContent?.replace(/^状态：/, '').trim() || '',
            facts: [...node.querySelectorAll('[data-fact-key]')].map((fact) => ({
              key: fact.getAttribute('data-fact-key') || '',
              label: fact.querySelector('small')?.textContent?.trim() || '',
              value: fact.querySelector('b')?.textContent?.trim() || '',
            })),
            openLabel: node.querySelector('.collection-mobile-record-row__open')?.textContent?.replace(/\s+/g, ' ').trim() || '',
            openAriaLabel: card?.getAttribute('aria-label') || '',
            selectionWidth: Math.round(selectionRect?.width || 0),
            selectionHeight: Math.round(selectionRect?.height || 0),
          };
        }));
        collectionMobileRecordEvidence = {
          ownerCount: rows.length,
          rows,
          pass: rows.length > 0 && rows.every((row) => row.recordKey
            && row.identity
            && row.openLabel
            && row.openAriaLabel.includes(row.identity)
            && row.facts.length > 0
            && row.facts.every((fact) => fact.key && fact.label && fact.value)
            && (row.selectionWidth === 0 || (row.selectionWidth >= 44 && row.selectionHeight >= 44))),
        };
      }
      if (target.captureCollectionKanban === true) {
        const lanes = await page.locator('[data-semantic-component="CollectionKanbanLane"]:visible').evaluateAll((nodes) => nodes.map((node) => ({
          key: node.getAttribute('data-lane-key') || '',
          label: node.querySelector('.collection-kanban-lane__header h3')?.textContent?.trim() || '',
          cardCount: node.querySelectorAll('[data-semantic-component="CollectionKanbanRecordCard"]').length,
        })));
        const cards = await page.locator('[data-semantic-component="CollectionKanbanRecordCard"]:visible').evaluateAll((nodes) => nodes.map((node) => ({
          recordKey: node.getAttribute('data-record-key') || '',
          role: node.getAttribute('role') || '',
          tabIndex: node.getAttribute('tabindex') || '',
          title: node.querySelector('.collection-kanban-record-card__title')?.textContent?.trim() || '',
          openAriaLabel: node.getAttribute('aria-label') || '',
          factCount: node.querySelectorAll('[data-fact-key]').length,
        })));
        const paginationOwnerCount = await page.locator('[data-semantic-component="CollectionPaginationFooter"]:visible').count();
        collectionKanbanEvidence = {
          lanes, cards, paginationOwnerCount,
          pass: lanes.length > 0 && cards.length > 0 && paginationOwnerCount === 1
            && lanes.every((lane) => lane.key && lane.cardCount > 0)
            && cards.every((card) => card.recordKey && card.title && card.role === 'button' && card.tabIndex === '0' && card.openAriaLabel.includes(card.title)),
        };
      }
      if (target.exerciseCollectionSelection === true) {
        const mobileDriver = viewport.name === 'mobile';
        const table = page.locator('[data-semantic-component="ScTable"][data-semantic-driver="tdesign-table"]:visible').first();
        const controls = mobileDriver
          ? page.locator('[data-semantic-component="CollectionSelectionControl"]:visible')
          : table.locator('input[type="checkbox"]');
        const controlCount = await controls.count();
        if (controlCount < 1) throw new Error(`${target.name}: collection selection adapter is missing`);
        const rowControl = mobileDriver
          ? page.locator('[data-semantic-component="CollectionSelectionControl"][data-selection-scope="row"]:visible').first()
          : table.locator('tbody .t-checkbox').first();
        if (await rowControl.count() !== 1) throw new Error(`${target.name}: collection row selection adapter is missing`);
        const rowInput = mobileDriver ? rowControl.locator('input[type="checkbox"]') : rowControl;
        const effectiveInput = mobileDriver ? rowInput : rowControl.locator('input[type="checkbox"]');
        const stateOf = async (input) => await input.isChecked() ? 'checked' : 'unchecked';
        const initialRowState = mobileDriver ? await rowControl.getAttribute('data-selection-state') : await stateOf(effectiveInput);
        const ariaLabel = await effectiveInput.getAttribute('aria-label') || await rowControl.getAttribute('aria-label') || await rowControl.getAttribute('title') || '';
        const touchTarget = await rowControl.boundingBox();
        await effectiveInput.focus();
        const focusContained = await rowControl.evaluate((node) => node.contains(document.activeElement));
        await rowControl.click();
        await page.waitForFunction((input) => input instanceof HTMLInputElement && input.checked, await effectiveInput.elementHandle(), { timeout: 15000 });
        const selectedRowState = mobileDriver ? await rowControl.getAttribute('data-selection-state') : await stateOf(effectiveInput);
        let selectedHeaderState = null;
        let headerIndeterminate = null;
        const headerControl = mobileDriver
          ? page.locator('[data-semantic-component="CollectionSelectionControl"]:visible:not([data-selection-scope="row"])').first()
          : table.locator('thead input[type="checkbox"]').first();
        if (viewport.name === 'desktop' && await headerControl.count() === 1) {
          selectedHeaderState = await headerControl.evaluate((input) => input.indeterminate ? 'mixed' : input.checked ? 'checked' : 'unchecked');
          headerIndeterminate = await headerControl.evaluate((input) => input.indeterminate);
        }
        await rowControl.click();
        await page.waitForFunction((input) => input instanceof HTMLInputElement && !input.checked, await effectiveInput.elementHandle(), { timeout: 15000 });
        const restoredRowState = mobileDriver ? await rowControl.getAttribute('data-selection-state') : await stateOf(effectiveInput);
        const restoredHeaderState = viewport.name === 'desktop' && await headerControl.count() === 1
          ? await headerControl.evaluate((input) => input.indeterminate ? 'mixed' : input.checked ? 'checked' : 'unchecked')
          : null;
        collectionSelectionEvidence = {
          driver: mobileDriver ? 'CollectionSelectionControl' : 'tdesign-table',
          controlCount, ariaLabel, touchTarget, focusContained, initialRowState, selectedRowState,
          selectedHeaderState, headerIndeterminate, restoredRowState, restoredHeaderState,
          pass: Boolean(ariaLabel) && focusContained && initialRowState === 'unchecked'
            && selectedRowState === 'checked' && restoredRowState === 'unchecked'
            && (viewport.name !== 'mobile' || (Number(touchTarget?.width || 0) >= 44 && Number(touchTarget?.height || 0) >= 44))
            && (viewport.name !== 'desktop' || (selectedHeaderState === 'mixed' && headerIndeterminate === true && restoredHeaderState === 'unchecked')),
        };
        if (!collectionSelectionEvidence.pass) throw new Error(`${target.name}: collection selection state contract failed ${JSON.stringify(collectionSelectionEvidence)}`);
      }
      let collectionAggregateEvidence = null;
      if (target.exerciseCollectionAggregate === true) {
        const tdesignTables = page.locator('[data-semantic-component="ScTable"][data-semantic-driver="tdesign-table"]:visible');
        const tdesignFooters = tdesignTables.locator('tfoot');
        const summaryFooters = page.locator('[data-semantic-component="CollectionAggregateFooter"]:visible');
        const usesTdesign = viewport.name === 'desktop' && await tdesignFooters.count() > 0;
        const footers = usesTdesign ? tdesignFooters : summaryFooters;
        const footerCount = await footers.count();
        if (footerCount < 1) throw new Error(`${target.name}: collection aggregate adapter is missing`);
        const expectedContext = target.aggregateContext === 'group' ? 'group' : 'flat';
        const contexts = usesTdesign
          ? Array(footerCount).fill(expectedContext)
          : await summaryFooters.evaluateAll((nodes) => nodes.map((node) => node.getAttribute('data-aggregate-context') || ''));
        const rows = usesTdesign ? tdesignFooters.locator('tr') : summaryFooters.locator('[data-aggregate-scope]');
        const rowCount = await rows.count();
        const scopes = usesTdesign
          ? Array(rowCount).fill('page-or-total')
          : await rows.evaluateAll((nodes) => nodes.map((node) => node.getAttribute('data-aggregate-scope') || ''));
        const rowHeaderCount = usesTdesign ? rowCount : await rows.locator('th[scope="row"], [data-aggregate-row-label]').count();
        const numericCells = usesTdesign ? rows.locator('td.column-layout-numeric') : rows.locator('.collection-aggregate-number');
        const numericCellCount = await numericCells.count();
        const misalignedNumericCells = await numericCells.evaluateAll((nodes) => nodes.filter((node) => getComputedStyle(node).textAlign !== 'right').length);
        collectionAggregateEvidence = {
          driver: usesTdesign ? 'tdesign-table-footData' : 'CollectionAggregateFooter',
          footerCount, contexts, rowCount, scopes, rowHeaderCount, numericCellCount, misalignedNumericCells,
          pass: footerCount >= 1
            && contexts.every((context) => context === expectedContext)
            && rowCount >= footerCount
            && scopes.every((scope) => scope === 'page' || scope === 'total' || scope === 'page-or-total')
            && rowHeaderCount === rowCount
            && numericCellCount > 0
            && misalignedNumericCells === 0,
        };
        if (!collectionAggregateEvidence.pass) throw new Error(`${target.name}: collection aggregate presentation contract failed ${JSON.stringify(collectionAggregateEvidence)}`);
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
        const primitiveOwners = {
          buttons: await toolbar.locator('[data-semantic-component="ScButton"]').count(),
          inputs: await toolbar.locator('[data-semantic-component="ScInput"]').count(),
          selects: await toolbar.locator('[data-semantic-component="ScSelect"]').count(),
        };
        let customFilterPrimitiveEvidence = null;
        if (target.exerciseCustomFilterPrimitives === true) {
          const customFilterToggle = searchLayer.getByRole('button', { name: /自定义/ }).first();
          await customFilterToggle.click();
          const customPanel = searchLayer.locator('.custom-search-panel').first();
          await customPanel.waitFor({ state: 'visible', timeout: 15000 });
          const fieldSelect = customPanel.locator('[data-semantic-component="ScSelect"]').first();
          const nonEmptyOptions = await fieldSelect.locator('option').evaluateAll((nodes) => (
            nodes.map((node) => node.value).filter(Boolean)
          ));
          if (!nonEmptyOptions.length) throw new Error('custom filter has no selectable field');
          await fieldSelect.selectOption(nonEmptyOptions[0]);
          const valueInput = customPanel.locator('[data-semantic-component="ScInput"]');
          const valueSelects = customPanel.locator('[data-semantic-component="ScSelect"]');
          let valueSettled = false;
          if (await valueInput.count()) {
            await valueInput.fill('验收');
            valueSettled = await valueInput.inputValue() === '验收';
          } else if (await valueSelects.count() > 2) {
            const valueSelect = valueSelects.nth(2);
            const values = await valueSelect.locator('option').evaluateAll((nodes) => nodes.map((node) => node.value).filter(Boolean));
            if (values.length) {
              await valueSelect.selectOption(values[0]);
              valueSettled = await valueSelect.inputValue() === values[0];
            }
          }
          customFilterPrimitiveEvidence = {
            scButtons: await customPanel.locator('[data-semantic-component="ScButton"]').count(),
            scInputs: await customPanel.locator('[data-semantic-component="ScInput"]').count(),
            scSelects: await customPanel.locator('[data-semantic-component="ScSelect"]').count(),
            selectedField: await fieldSelect.inputValue(),
            valueSettled,
          };
          if (customFilterPrimitiveEvidence.scButtons !== 2
            || customFilterPrimitiveEvidence.scSelects < 2
            || !customFilterPrimitiveEvidence.selectedField
            || !customFilterPrimitiveEvidence.valueSettled) {
            throw new Error(`custom filter primitive settlement failed: ${JSON.stringify(customFilterPrimitiveEvidence)}`);
          }
        }
        await page.keyboard.press('Escape');
        await searchLayer.waitFor({ state: 'hidden', timeout: 15000 });
        const searchFocusRestored = await searchToggle.evaluate((node) => node === document.activeElement);
        const rowSelection = viewport.name === 'mobile'
          ? page.locator('.mobile-record-list [data-semantic-component="CollectionSelectionControl"][data-selection-scope="row"]').first()
          : page.locator('.desktop-record-table tbody [data-semantic-component="CollectionSelectionControl"][data-selection-scope="row"]').first();
        const batchBar = page.locator('[data-semantic-component="CollectionBatchActionBar"]');
        const selectionAvailable = await rowSelection.count() === 1;
        let actionCount = 0;
        let directKeys = [];
        let overflowKeys = [];
        let projectedKeys = [];
        let batchFocusContained = true;
        let batchFocusRestored = true;
        if (selectionAvailable) {
          const rowCheckbox = rowSelection.locator('input[type="checkbox"]');
          await rowSelection.click();
          if (!(await rowCheckbox.isChecked())) throw new Error('collection row selection control did not settle checked');
          await batchBar.waitFor({ state: 'visible', timeout: 15000 });
          actionCount = Number(await batchBar.getAttribute('data-action-count') || 0);
          directKeys = String(await batchBar.getAttribute('data-direct-action-keys') || '').split(',').filter(Boolean);
          overflowKeys = String(await batchBar.getAttribute('data-overflow-action-keys') || '').split(',').filter(Boolean);
          projectedKeys = await batchBar.locator('button[data-action-key]').evaluateAll((nodes) => nodes.map((node) => node.getAttribute('data-action-key') || '').filter(Boolean));
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
        }
        const uniqueKeys = [...new Set([...directKeys, ...overflowKeys])];
        collectionToolbarEvidence = {
          selectionAvailable, actionCount, directKeys, overflowKeys, projectedKeys,
          primitiveOwners, customFilterPrimitiveEvidence,
          searchFocusContained, searchFocusRestored, batchFocusContained, batchFocusRestored,
          pass: searchFocusContained && searchFocusRestored && batchFocusContained && batchFocusRestored
            && primitiveOwners.buttons >= 1 && primitiveOwners.inputs >= 1
            && (target.exerciseCustomFilterPrimitives !== true || customFilterPrimitiveEvidence?.valueSettled === true)
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
        const invalidColumnRoots = await columnHeaders.evaluateAll((nodes) => nodes.filter((node) => node.closest('th') === null).length);
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
      const verticalLineEvidence = target.captureVerticalLineEvidence === true
        ? await page.evaluate(() => {
          const x = Math.round(window.innerWidth * 0.568);
          const points = [10, 100, 300, 700].map((y) => ({
            x, y,
            stack: document.elementsFromPoint(x, y).slice(0, 8).map((node) => {
              const style = getComputedStyle(node);
              const rect = node.getBoundingClientRect();
              return {
                tag: node.tagName,
                id: node.id,
                className: typeof node.className === 'string' ? node.className : '',
                semantic: node.getAttribute('data-semantic-component') || '',
                rect: [Math.round(rect.left), Math.round(rect.top), Math.round(rect.right), Math.round(rect.bottom)],
                borderLeft: style.borderLeft,
                borderRight: style.borderRight,
                outline: style.outline,
                boxShadow: style.boxShadow,
              };
            }),
          }));
          const resizeHandles = [...document.querySelectorAll('.column-resize-handle')].map((node) => {
            const rect = node.getBoundingClientRect();
            const pseudo = getComputedStyle(node, '::after');
            return {
              rect: [Math.round(rect.left), Math.round(rect.top), Math.round(rect.right), Math.round(rect.bottom)],
              hovered: node.matches(':hover'),
              focused: node === document.activeElement,
              afterBackground: pseudo.backgroundColor,
              afterHeight: pseudo.height,
              afterTop: pseudo.top,
            };
          });
          return { points, resizeHandles };
        })
        : null;
      report.routes.push({ name: target.name, path: target.path, viewport: viewport.name, finalUrl: initialFinalUrl, expectedPageHeaders: target.expectedPageHeaders ?? null, expectedPrimaryActions: target.expectedPrimaryActions ?? null, expectedPresentationMode: target.expectedPresentationMode ?? null, expectedNativeStructureCount: target.expectedNativeStructureCount ?? null, expectedNativeNotebookPageCount: target.expectedNativeNotebookPageCount ?? null, contractH1Nodes, contractSelections, contractAggregates, contractSummaryItems, listAggregates, nativeActionPresentationEvidence, relationSearchDialogEvidence, collectionSummaryEvidence, collectionMobileRecordEvidence, collectionKanbanEvidence, collectionSelectionEvidence, collectionAggregateEvidence, collectionGroupHeaderEvidence, mobileOverflowEvidence, dialogLifecycleEvidence, collectionToolbarEvidence, collectionNavigationEvidence, sidebarScrollEvidence, verticalLineEvidence, ...result });
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
  if (item.path && item.primitiveDriverEvidence && !item.primitiveDriverEvidence.pass) {
    failures.push({ name: item.name, primitiveDriverEvidence: item.primitiveDriverEvidence });
  }
  if (item.path && item.overlayResidueEvidence && !item.overlayResidueEvidence.pass) {
    failures.push({ name: item.name, overlayResidueEvidence: item.overlayResidueEvidence });
  }
  if (item.path && item.shellAdapterEvidence && routes.find((target) => target.name === item.name)?.exerciseShellAdapterProjection === true && !item.shellAdapterEvidence.pass) {
    failures.push({ name: item.name, shellAdapterEvidence: item.shellAdapterEvidence });
  }
  if (item.path && item.expectedPageHeaders !== null && item.pageHeaders !== item.expectedPageHeaders) {
    failures.push({ name: item.name, expectedPageHeaders: item.expectedPageHeaders, actualPageHeaders: item.pageHeaders });
  }
  if (item.path && item.expectedPrimaryActions !== null && item.primaryActions !== item.expectedPrimaryActions) {
    failures.push({ name: item.name, expectedPrimaryActions: item.expectedPrimaryActions, actualPrimaryActions: item.primaryActions });
  }
  if (item.path && item.expectedPresentationMode !== null && !item.presentationModes.includes(item.expectedPresentationMode)) {
    failures.push({ name: item.name, expectedPresentationMode: item.expectedPresentationMode, actualPresentationModes: item.presentationModes });
  }
  if (item.path && item.expectedNativeStructureCount !== null && item.nativeStructureCount !== item.expectedNativeStructureCount) {
    failures.push({ name: item.name, expectedNativeStructureCount: item.expectedNativeStructureCount, actualNativeStructureCount: item.nativeStructureCount });
  }
  if (item.path && item.expectedNativeNotebookPageCount !== null && item.nativeNotebookPageCount !== item.expectedNativeNotebookPageCount) {
    failures.push({ name: item.name, expectedNativeNotebookPageCount: item.expectedNativeNotebookPageCount, actualNativeNotebookPageCount: item.nativeNotebookPageCount });
  }
  if (item.sidebarScrollEvidence && !item.sidebarScrollEvidence.pass) failures.push({ name: item.name, sidebarScrollEvidence: item.sidebarScrollEvidence });
}
for (const item of report.routes) {
  if (item.mobileOverflowEvidence && !item.mobileOverflowEvidence.pass) failures.push({ name: item.name, mobileOverflowEvidence: item.mobileOverflowEvidence });
  if (item.collectionSelectionEvidence && !item.collectionSelectionEvidence.pass) failures.push({ name: item.name, collectionSelectionEvidence: item.collectionSelectionEvidence });
  if (item.collectionSummaryEvidence && !item.collectionSummaryEvidence.pass) failures.push({ name: item.name, collectionSummaryEvidence: item.collectionSummaryEvidence });
  if (item.collectionMobileRecordEvidence && !item.collectionMobileRecordEvidence.pass) failures.push({ name: item.name, collectionMobileRecordEvidence: item.collectionMobileRecordEvidence });
  if (item.collectionKanbanEvidence && !item.collectionKanbanEvidence.pass) failures.push({ name: item.name, collectionKanbanEvidence: item.collectionKanbanEvidence });
  if (item.relationSearchDialogEvidence && !item.relationSearchDialogEvidence.pass) failures.push({ name: item.name, relationSearchDialogEvidence: item.relationSearchDialogEvidence });
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
