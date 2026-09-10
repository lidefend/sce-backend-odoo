import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';

const baseUrl = String(process.env.FRONTEND_URL || '').replace(/\/$/, '');
const database = String(process.env.DB_NAME || '');
const login = String(process.env.E2E_LOGIN || '');
const password = String(process.env.E2E_PASSWORD || '');
const head = String(process.env.CANDIDATE_GIT_HEAD || '');
const routes = JSON.parse(process.env.CANDIDATE_VISUAL_ROUTES_JSON || '[]');
const desktopWidth = Math.max(960, Math.min(1920, Math.trunc(Number(process.env.CANDIDATE_VISUAL_DESKTOP_WIDTH || 1440)) || 1440));
const desktopHeight = Math.max(720, Math.trunc(Number(process.env.CANDIDATE_VISUAL_DESKTOP_HEIGHT || 960)) || 960);
const mobileWidth = Math.max(320, Math.min(560, Math.trunc(Number(process.env.CANDIDATE_VISUAL_MOBILE_WIDTH || 390)) || 390));
const theme = String(process.env.CANDIDATE_VISUAL_THEME || 'light') === 'dark' ? 'dark' : 'light';
const outputDir = path.resolve(process.env.CANDIDATE_VISUAL_OUTPUT_DIR || 'artifacts/playwright/local-dev-candidate-visual-smoke');

if (!baseUrl || !database || !login || !password || !/^[0-9a-f]{40}$/.test(head)) throw new Error('candidate visual identity is incomplete');
if (!Array.isArray(routes) || routes.length === 0 || routes.some((item) => !item || typeof item.name !== 'string' || !String(item.path || '').startsWith('/'))) {
  throw new Error('candidate visual routes must be a non-empty name/path array');
}

fs.mkdirSync(outputDir, { recursive: true });
const report = {
  head,
  baseUrl,
  database,
  login,
  mutationCount: 0,
  inputs: {
    desktop: { width: desktopWidth, height: desktopHeight },
    mobile: { width: mobileWidth, height: 844 },
    theme,
    routes,
  },
  startup: {},
  routes: [],
};
const browser = await launchChromium({ headless: true });

async function loginPage(page) {
  await page.goto(`${baseUrl}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const inputs = page.locator('input');
  await inputs.nth(0).fill(login);
  await inputs.nth(1).fill(password);
  if (await inputs.nth(2).count() && !(await inputs.nth(2).isDisabled())) await inputs.nth(2).fill(database);
  const systemInitResponse = page.waitForResponse(isSystemInitResponse, { timeout: 45000 });
  await page.getByRole('button', { name: /^登录$/ }).click();
  const response = await systemInitResponse;
  if (!response.ok()) throw new Error(`system.init request failed: ${response.status()}`);
  const payload = await response.json();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45000 });
  await page.locator('.layout-shell').waitFor({ timeout: 45000 });
  return summarizeSystemInit(payload);
}

async function waitForStableProductSurface(page) {
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  await page.waitForFunction(() => {
    const pendingForm = document.querySelector('[data-workspace-primary-content][aria-busy="true"]');
    const pendingCollection = document.querySelector('.product-loading-shell[aria-busy="true"]');
    const formPage = document.querySelector('[data-semantic-component="ContractFormPage"]');
    const formSettled = !(formPage instanceof HTMLElement) || formPage.dataset.state !== 'loading';
    const actionPage = document.querySelector('[data-semantic-component="ActionView"]');
    const actionSettled = !(actionPage instanceof HTMLElement) || actionPage.dataset.collectionState !== 'loading';
    const homePage = document.querySelector('[data-semantic-component="WorkspaceHome"]');
    const homeSettled = !(homePage instanceof HTMLElement) || homePage.dataset.state !== 'loading';
    const myWorkPage = document.querySelector('[data-semantic-component="MyWorkView"]');
    const myWorkSettled = !(myWorkPage instanceof HTMLElement) || myWorkPage.dataset.state !== 'loading';
    const configPage = document.querySelector('[data-product-page-mode="admin"]');
    const configSettled = !(configPage instanceof HTMLElement)
      || Boolean(configPage.querySelector('[data-business-config-surface-error="true"]'))
      || Boolean(configPage.querySelector('[data-business-config-change-set="v1"]') && configPage.querySelector('.page-picker-panel'));
    return !pendingForm && !pendingCollection && formSettled && actionSettled && homeSettled && myWorkSettled && configSettled;
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

function isSystemInitResponse(response) {
  if (!response.url().includes('/api/v1/intent') || response.request().method() !== 'POST') return false;
  try {
    return JSON.parse(response.request().postData() || '{}').intent === 'system.init';
  } catch {
    return false;
  }
}

function summarizeSystemInit(payload) {
  const data = payload?.data && typeof payload.data === 'object' ? payload.data : payload;
  const navigation = data?.navigation && typeof data.navigation === 'object' ? data.navigation : {};
  const authority = navigation?.route_authority && typeof navigation.route_authority === 'object'
    ? navigation.route_authority
    : {};
  const routeEntries = ['primary_actions', 'role_home_actions', 'contextual_actions', 'admin_actions']
    .flatMap((bucket) => Array.isArray(authority[bucket]) ? authority[bucket].map((entry) => ({
      bucket,
      menuId: Number(entry?.menu_id || 0),
      actionId: Number(entry?.action_id || 0),
      menuXmlid: String(entry?.menu_xmlid || ''),
      actionXmlid: String(entry?.action_xmlid || ''),
    })) : []);
  return {
    roleCode: String(data?.role_surface?.role_code || ''),
    userId: Number(authority?.principal_scope?.user_id || 0),
    companyId: Number(authority?.principal_scope?.company_id || 0),
    routeEntries,
  };
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
  for (const viewport of [{ name: 'desktop', width: desktopWidth, height: desktopHeight }, { name: 'mobile', width: mobileWidth, height: 844 }]) {
    const context = await browser.newContext({
      viewport: { width: viewport.width, height: viewport.height },
      locale: 'zh-CN',
      hasTouch: viewport.name === 'mobile',
    });
    await context.addInitScript((requestedTheme) => localStorage.setItem('sc_theme', requestedTheme), theme);
    const page = await context.newPage();
    const errors = [];
    let expectedReadFailureResponses = 0;
    let expectedReadFailureConsoleErrors = 0;
    page.on('console', (message) => {
      if (message.type() !== 'error' || message.text().includes('favicon')) return;
      if (expectedReadFailureConsoleErrors > 0 && message.text().includes('503 (Service Unavailable)')) {
        expectedReadFailureConsoleErrors -= 1;
        return;
      }
      errors.push(`console:${message.text()}`);
    });
    page.on('pageerror', (error) => errors.push(`page:${error.message}`));
    page.on('response', (response) => {
      if (response.status() < 400 || !response.url().includes('/api/')) return;
      if (expectedReadFailureResponses > 0) {
        expectedReadFailureResponses -= 1;
        return;
      }
      errors.push(`http:${response.status()}:${response.url()}`);
    });
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
    report.startup[viewport.name] = await loginPage(page);
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
      let readFailureEvidence = null;
      let businessConfigExperienceEvidence = null;
      let businessConfigReadFailureEvidence = null;
      let safeReturnEvidence = null;
      let formStructureEvidence = null;
      let fieldAlignmentEvidence = null;
      let officialComponentBehaviorEvidence = null;
      let officialAlertOperationEvidence = null;
      let expectedLoadedSelectorEvidence = null;
      const exerciseReadFailure = target.exerciseReadFailureRecovery === true
        && (target.readFailureDesktopOnly !== true || viewport.name === 'desktop');
      let readFailureInjected = false;
      let readFailureOperation = '';
      const readFailurePattern = '**/api/v1/**';
      const readFailureHandler = async (route) => {
        const request = route.request();
        let body = {};
        try { body = JSON.parse(request.postData() || '{}'); } catch {}
        const operation = body.intent === 'ui.contract.v2' ? 'ui.contract.v2' : body?.params?.op;
        const expectedRecordId = Number(target.recordId || 0);
        const requestRecordIds = body.intent === 'ui.contract.v2'
          ? [Number(body?.params?.record_id || 0)]
          : (Array.isArray(body?.params?.ids) ? body.params.ids.map(Number) : []);
        const matchesRecord = expectedRecordId <= 0 || requestRecordIds.includes(expectedRecordId);
        if (request.method() === 'POST' && matchesRecord
          && (operation === 'ui.contract.v2' || (body.intent === 'api.data' && operation === 'read'))) {
          readFailureInjected = true;
          readFailureOperation = operation;
          expectedReadFailureResponses += 1;
          expectedReadFailureConsoleErrors += 1;
          await route.fulfill({
            status: 503,
            contentType: 'application/json',
            body: JSON.stringify({ error: { message: '受控读取失败，请重试。', reason_code: 'CONTROLLED_READ_FAILURE', retryable: true } }),
          });
          return;
        }
        await route.continue();
      };
      if (exerciseReadFailure) await page.route(readFailurePattern, readFailureHandler);
      const exerciseBusinessConfigReadFailure = target.exerciseBusinessConfigReadFailure === true
        && (target.businessConfigReadFailureDesktopOnly !== true || viewport.name === 'desktop');
      let businessConfigReadFailureInjected = false;
      const businessConfigReadFailureHandler = async (route) => {
        const request = route.request();
        let body = {};
        try { body = JSON.parse(request.postData() || '{}'); } catch {}
        if (request.method() === 'POST' && body.intent === 'ui.business_config.surface.get' && !businessConfigReadFailureInjected) {
          businessConfigReadFailureInjected = true;
          expectedReadFailureResponses += 1;
          expectedReadFailureConsoleErrors += 1;
          await route.fulfill({
            status: 503,
            contentType: 'application/json',
            body: JSON.stringify({ error: { message: '受控配置读取失败，请重试。', reason_code: 'CONTROLLED_CONFIG_READ_FAILURE', retryable: true } }),
          });
          return;
        }
        await route.continue();
      };
      if (exerciseBusinessConfigReadFailure) await page.route(readFailurePattern, businessConfigReadFailureHandler);
      const exerciseOfficialAlertOperation = target.exerciseOfficialAlertOperation === true;
      let officialAlertFailureInjected = false;
      const officialAlertFailureHandler = async (route) => {
        const request = route.request();
        let body = {};
        try { body = JSON.parse(request.postData() || '{}'); } catch {}
        if (!officialAlertFailureInjected && request.method() === 'POST' && body.intent === 'my.work.summary') {
          officialAlertFailureInjected = true;
          expectedReadFailureResponses += 1;
          expectedReadFailureConsoleErrors += 1;
          await route.fulfill({
            status: 503,
            contentType: 'application/json',
            body: JSON.stringify({ error: { message: '受控组件读取失败，请重试。', reason_code: 'CONTROLLED_COMPONENT_FAILURE', retryable: true } }),
          });
          return;
        }
        await route.continue();
      };
      if (exerciseOfficialAlertOperation) await page.route(readFailurePattern, officialAlertFailureHandler);
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
      if (exerciseOfficialAlertOperation) {
        const alert = page.locator('[data-semantic-component="ScInlineState"][data-semantic-driver="tdesign-alert"][data-state="error"]:visible');
        await alert.waitFor({ state: 'visible', timeout: 15000 });
        const retry = alert.getByRole('button', { name: '重试', exact: true });
        const operation = alert.locator('.t-alert__operation');
        const description = alert.locator('.sc-inline-state__description');
        const retryCount = await retry.count();
        const operationCount = await operation.count();
        const descriptionText = String(await description.textContent() || '').replace(/\s+/g, ' ').trim();
        const driverClassPresent = await alert.evaluate((node) => node.classList.contains('t-alert'));
        await retry.focus();
        const focusedBeforeActivation = await retry.evaluate((node) => node === document.activeElement);
        await page.unroute(readFailurePattern, officialAlertFailureHandler);
        let retryRequestCount = 0;
        const countRetryRequest = (request) => {
          if (!request.url().includes('/api/v1/intent') || request.method() !== 'POST') return;
          try {
            if (JSON.parse(request.postData() || '{}').intent === 'my.work.summary') retryRequestCount += 1;
          } catch {}
        };
        page.on('request', countRetryRequest);
        const recoveryResponse = page.waitForResponse((response) => {
          if (!response.url().includes('/api/v1/intent') || response.request().method() !== 'POST') return false;
          try { return JSON.parse(response.request().postData() || '{}').intent === 'my.work.summary'; } catch { return false; }
        }, { timeout: 45000 });
        await retry.press('Enter');
        const recovered = await recoveryResponse;
        if (!recovered.ok()) throw new Error(`${target.name}: alert operation recovery failed with ${recovered.status()}`);
        await page.locator('[data-semantic-component="WorkspaceHome"][data-state="ready"]:visible').waitFor({ state: 'visible', timeout: 45000 });
        await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
        page.off('request', countRetryRequest);
        officialAlertOperationEvidence = {
          failureInjected: officialAlertFailureInjected,
          driverClassPresent,
          operationCount,
          retryCount,
          descriptionText,
          focusedBeforeActivation,
          retryRequestCount,
          recovered: await page.locator('[data-semantic-component="WorkspaceHome"][data-state="ready"]:visible').count() === 1,
        };
        officialAlertOperationEvidence.pass = officialAlertOperationEvidence.failureInjected
          && officialAlertOperationEvidence.operationCount === 1
          && officialAlertOperationEvidence.retryCount === 1
          && officialAlertOperationEvidence.driverClassPresent
          && officialAlertOperationEvidence.descriptionText.length > 0
          && officialAlertOperationEvidence.focusedBeforeActivation
          && officialAlertOperationEvidence.retryRequestCount === 1
          && officialAlertOperationEvidence.recovered;
      }
      if (exerciseBusinessConfigReadFailure) {
        const errorSurface = page.locator('[data-business-config-surface-error="true"]:visible');
        await errorSurface.waitFor({ state: 'visible', timeout: 15000 });
        const errorText = String(await errorSurface.textContent() || '').replace(/\s+/g, ' ').trim();
        const retry = errorSurface.getByRole('button', { name: '重试读取' });
        const retryCount = await retry.count();
        await page.unroute(readFailurePattern, businessConfigReadFailureHandler);
        await retry.click();
        await page.locator('[data-business-config-change-set="v1"]:visible').waitFor({ state: 'visible', timeout: 45000 });
        await page.locator('.page-picker-panel:visible').waitFor({ state: 'visible', timeout: 45000 });
        businessConfigReadFailureEvidence = {
          injected: businessConfigReadFailureInjected,
          errorText,
          retryCount,
          recovered: await page.locator('[data-business-config-surface-error="true"]:visible').count() === 0,
        };
        businessConfigReadFailureEvidence.pass = businessConfigReadFailureEvidence.injected
          && businessConfigReadFailureEvidence.errorText.includes('受控配置读取失败')
          && businessConfigReadFailureEvidence.retryCount === 1
          && businessConfigReadFailureEvidence.recovered;
      }
      if (exerciseReadFailure) {
        const errorSurface = page.locator('[data-semantic-state-surface="page"][data-state="error"]:visible').first();
        await errorSurface.waitFor({ state: 'visible', timeout: 15000 });
        const errorText = String(await errorSurface.textContent() || '').replace(/\s+/g, ' ').trim();
        const retry = errorSurface.getByRole('button').filter({ hasText: /重试|重新加载/ }).first();
        const retryCount = await retry.count();
        await page.unroute(readFailurePattern, readFailureHandler);
        if (retryCount !== 1) throw new Error(`${target.name}: read failure did not expose one retry action`);
        const retryContractResponse = page.waitForResponse(isContractV2Response, { timeout: 45000 });
        await retry.click();
        const recoveredResponse = await retryContractResponse;
        if (!recoveredResponse.ok()) {
          throw new Error(`${target.name}: retry contract request failed with ${recoveredResponse.status()}`);
        }
        try {
          await page.locator('[data-semantic-component="ContractFormPage"][data-state="ok"]').waitFor({ state: 'visible', timeout: 45000 });
        } catch (error) {
          const retryState = await page.locator('[data-semantic-component="ContractFormPage"]').getAttribute('data-state');
          const retrySurfaceText = String(await page.locator('[data-semantic-state-surface="page"]:visible').first().textContent().catch(() => '') || '').replace(/\s+/g, ' ').trim();
          throw new Error(`${target.name}: retry did not restore ready state (state=${retryState || '-'}, surface=${retrySurfaceText || '-'})`, { cause: error });
        }
        await waitForStableProductSurface(page);
        const restoredState = await page.locator('[data-semantic-component="ContractFormPage"]').getAttribute('data-state');
        readFailureEvidence = {
          injected: readFailureInjected,
          operation: readFailureOperation,
          errorText,
          retryCount,
          restoredState,
          pass: readFailureInjected && errorText.length > 0 && restoredState === 'ok',
        };
      }
      if (target.expectedLoadedSelector) {
        const expectedLoadedSelector = String(target.expectedLoadedSelector);
        const loadedSurface = page.locator(expectedLoadedSelector).filter({ visible: true });
        await loadedSurface.first().waitFor({ state: 'visible', timeout: 45000 });
        expectedLoadedSelectorEvidence = {
          selector: expectedLoadedSelector,
          visibleCount: await loadedSurface.count(),
          pass: await loadedSurface.count() > 0,
        };
      }
      if (target.exerciseOfficialComponentBehavior === true) {
        const workspace = page.locator('[data-semantic-component="MyWorkApprovalWorkspace"][data-state="ready"]:visible');
        await workspace.waitFor({ state: 'visible', timeout: 45000 });
        const searchRoot = workspace.locator('.product-work__filters [data-semantic-component="ScInput"]').first();
        const searchInput = searchRoot.locator('input[type="search"]');
        const initialCardCount = await workspace.locator('.work-card:visible').count();
        await searchInput.focus();
        const inputFocused = await searchInput.evaluate((node) => node === document.activeElement);
        await searchInput.fill('__official_component_no_match__');
        await workspace.getByRole('button', { name: '清除查找', exact: true }).waitFor({ state: 'visible', timeout: 15000 });
        const filteredEmptyCount = await workspace.locator('[data-semantic-component="ScEmptyState"]:visible').count();
        await workspace.getByRole('button', { name: '清除查找', exact: true }).click();
        await page.waitForFunction(
          () => document.querySelector('.product-work__filters input[type="search"]')?.value === ''
            && document.querySelectorAll('.work-card').length > 0,
          undefined,
          { timeout: 15000 },
        );
        const restoredCardCount = await workspace.locator('.work-card:visible').count();

        const selectRoot = workspace.locator('.product-work__filters [data-semantic-component="ScSelect"]').first();
        const selectInput = selectRoot.locator('input').first();
        const initialSelectValue = await selectInput.inputValue();
        await selectRoot.click();
        const mouseOptions = page.locator('.t-select-option:visible:not(.t-is-disabled)');
        await mouseOptions.first().waitFor({ state: 'visible', timeout: 15000 });
        const mouseOptionCount = await mouseOptions.count();
        const mouseOption = mouseOptions.last();
        const mouseOptionText = String(await mouseOption.textContent() || '').replace(/\s+/g, ' ').trim();
        await mouseOption.click();
        await page.waitForFunction(
          (before) => document.querySelector('.product-work__filters [data-semantic-component="ScSelect"] input')?.value !== before,
          initialSelectValue,
          { timeout: 15000 },
        );
        const mouseSelectValue = await selectInput.inputValue();
        await selectInput.focus();
        await selectInput.press('ArrowDown');
        await selectInput.press('ArrowUp');
        await selectInput.press('Enter');
        await page.waitForFunction(
          (before) => document.querySelector('.product-work__filters [data-semantic-component="ScSelect"] input')?.value !== before,
          mouseSelectValue,
          { timeout: 15000 },
        );
        const keyboardSelectValue = await selectInput.inputValue();
        const selectFocused = await selectInput.evaluate((node) => node === document.activeElement);

        const metricButtons = workspace.locator('.count-card[data-primitive-driver="browser-structured"]');
        const metricCount = await metricButtons.count();
        const mouseMetric = metricButtons.nth(Math.min(1, Math.max(0, metricCount - 1)));
        const mouseMetricKey = String(await mouseMetric.getAttribute('data-section-key') || '');
        const mouseActivationCount = await mouseMetric.evaluate((node) => {
          node.dataset.browserActivationCount = '0';
          node.addEventListener('click', () => {
            node.dataset.browserActivationCount = String(Number(node.dataset.browserActivationCount || '0') + 1);
          });
          return Number(node.dataset.browserActivationCount || '0');
        });
        await mouseMetric.click();
        const mouseActivationAfter = Number(await mouseMetric.getAttribute('data-browser-activation-count') || 0);
        const mousePressed = await mouseMetric.getAttribute('aria-pressed');
        const keyboardMetric = metricButtons.first();
        await keyboardMetric.evaluate((node) => {
          node.dataset.browserActivationCount = '0';
          node.addEventListener('click', () => {
            node.dataset.browserActivationCount = String(Number(node.dataset.browserActivationCount || '0') + 1);
          });
        });
        await keyboardMetric.focus();
        await keyboardMetric.press('Enter');
        const keyboardActivationAfter = Number(await keyboardMetric.getAttribute('data-browser-activation-count') || 0);
        const keyboardPressed = await keyboardMetric.getAttribute('aria-pressed');
        const metricFocused = await keyboardMetric.evaluate((node) => node === document.activeElement);
        const publicBodyCards = workspace.locator('.work-card .t-card__body.work-card__body');
        officialComponentBehaviorEvidence = {
          inputSearchClear: {
            driver: await searchRoot.getAttribute('data-primitive-driver'),
            inputFocused,
            filteredEmptyCount,
            initialCardCount,
            restoredCardCount,
            valueAfterClear: await searchInput.inputValue(),
          },
          selectMouse: { initialSelectValue, mouseOptionCount, mouseOptionText, value: mouseSelectValue },
          selectKeyboard: { before: mouseSelectValue, value: keyboardSelectValue, focused: selectFocused },
          structuredButtonActivation: {
            metricCount,
            mouseMetricKey,
            mouseActivationCount,
            mouseActivationAfter,
            mousePressed,
            keyboardActivationAfter,
            keyboardPressed,
            focused: metricFocused,
          },
          cardPublicBodyClass: { count: await publicBodyCards.count() },
        };
        officialComponentBehaviorEvidence.pass = officialComponentBehaviorEvidence.inputSearchClear.driver === 'tdesign'
          && officialComponentBehaviorEvidence.inputSearchClear.inputFocused
          && officialComponentBehaviorEvidence.inputSearchClear.filteredEmptyCount === 1
          && officialComponentBehaviorEvidence.inputSearchClear.initialCardCount > 0
          && officialComponentBehaviorEvidence.inputSearchClear.restoredCardCount === officialComponentBehaviorEvidence.inputSearchClear.initialCardCount
          && officialComponentBehaviorEvidence.inputSearchClear.valueAfterClear === ''
          && officialComponentBehaviorEvidence.selectMouse.mouseOptionCount > 1
          && officialComponentBehaviorEvidence.selectMouse.mouseOptionText.length > 0
          && officialComponentBehaviorEvidence.selectMouse.value !== officialComponentBehaviorEvidence.selectMouse.initialSelectValue
          && officialComponentBehaviorEvidence.selectKeyboard.value !== officialComponentBehaviorEvidence.selectKeyboard.before
          && officialComponentBehaviorEvidence.selectKeyboard.focused
          && officialComponentBehaviorEvidence.structuredButtonActivation.metricCount > 1
          && officialComponentBehaviorEvidence.structuredButtonActivation.mouseActivationAfter === 1
          && officialComponentBehaviorEvidence.structuredButtonActivation.mousePressed === 'true'
          && officialComponentBehaviorEvidence.structuredButtonActivation.keyboardActivationAfter === 1
          && officialComponentBehaviorEvidence.structuredButtonActivation.keyboardPressed === 'true'
          && officialComponentBehaviorEvidence.structuredButtonActivation.focused
          && officialComponentBehaviorEvidence.cardPublicBodyClass.count > 0;
        if (!officialComponentBehaviorEvidence.pass) {
          throw new Error(`${target.name}: official component behavior failed ${JSON.stringify(officialComponentBehaviorEvidence)}`);
        }
      }
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
            const content = node.querySelector('.published-app__content');
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
        const analysisRoot = document.querySelector('[data-analysis-view]');
        const analysisView = analysisRoot?.getAttribute('data-analysis-view') || '';
        const analysisState = analysisRoot?.getAttribute('data-analysis-state') || '';
        const analysisReason = analysisRoot?.getAttribute('data-analysis-reason') || '';
        const analysisPivotRows = analysisRoot?.querySelectorAll('.t-table__body tr, tbody tr').length || 0;
        const analysisGraphRows = analysisRoot?.querySelectorAll('.analysis-bar-row').length || 0;
        const activityRoot = document.querySelector('[data-activity-surface="native-readonly"]');
        const activityCards = activityRoot ? [...activityRoot.querySelectorAll('[data-activity-card="record"]')] : [];
        const activityCardEvidence = activityCards.map((node) => {
          const rect = node.getBoundingClientRect();
          const descendants = [...node.querySelectorAll('*')].map((child) => {
            const childRect = child.getBoundingClientRect();
            return {
              tag: child.tagName,
              className: typeof child.className === 'string' ? child.className : '',
              rect: [Math.round(childRect.left), Math.round(childRect.top), Math.round(childRect.right), Math.round(childRect.bottom)],
              overflowRight: Math.round(Math.max(0, childRect.right - rect.right)),
            };
          });
          const widestDescendant = descendants.sort((left, right) => right.overflowRight - left.overflowRight)[0] || null;
          const computed = getComputedStyle(node);
          return {
            ordinal: node.getAttribute('data-record-ordinal') || '',
            rect: [Math.round(rect.left), Math.round(rect.top), Math.round(rect.right), Math.round(rect.bottom)],
            clientSize: [node.clientWidth, node.clientHeight],
            scrollSize: [node.scrollWidth, node.scrollHeight],
            horizontalClipped: node.scrollWidth > node.clientWidth + 1,
            verticalClipped: node.scrollHeight > node.clientHeight + 1,
            computed: { padding: computed.padding, boxSizing: computed.boxSizing, overflowX: computed.overflowX },
            widestDescendant,
            visibleText: String(node.textContent || '').replace(/\s+/g, ' ').trim(),
          };
        });
        const relationTagCells = [...document.querySelectorAll('[data-semantic-cell-kind="relation-tags"]')]
          .filter((node) => node instanceof HTMLElement && node.offsetParent !== null);
        const relationTagLabels = relationTagCells.flatMap((node) =>
          [...node.querySelectorAll('.relation-tag, .collection-mobile-record-row__relation-tag')]
            .map((label) => String(label.textContent || '').trim())
            .filter(Boolean),
        );
        const homeRoot = document.querySelector('[data-role-home]');
        const homeQuickEntries = homeRoot
          ? [...homeRoot.querySelectorAll('[data-appearance="dashboard-quick-link"]')]
            .filter((node) => node instanceof HTMLElement && node.offsetParent !== null)
            .map((node) => {
              const content = node.querySelector('.sc-btn__content');
              const icon = node.querySelector('.role-home-surface__entry-icon');
              const copy = node.querySelector('.role-home-surface__entry-copy');
              const label = copy?.querySelector('strong');
              const detail = copy?.querySelector('small');
              const arrow = node.querySelector('.role-home-surface__entry-arrow');
              const contentStyle = content instanceof HTMLElement ? getComputedStyle(content) : null;
              const copyStyle = copy instanceof HTMLElement ? getComputedStyle(copy) : null;
              const nodeRect = node.getBoundingClientRect();
              const contentRect = content?.getBoundingClientRect();
              const iconRect = icon?.getBoundingClientRect();
              const copyRect = copy?.getBoundingClientRect();
              const labelRect = label?.getBoundingClientRect();
              const detailRect = detail?.getBoundingClientRect();
              const arrowRect = arrow?.getBoundingClientRect();
              return {
                label: String(label?.textContent || '').trim(),
                detail: String(detail?.textContent || '').trim(),
                contentDisplay: contentStyle?.display || '',
                contentColumns: contentStyle?.gridTemplateColumns || '',
                copyDisplay: copyStyle?.display || '',
                buttonWidth: Math.round(nodeRect.width),
                contentWidth: Math.round(contentRect?.width || 0),
                copyWidth: Math.round(copyRect?.width || 0),
                arrowRightGap: Math.round(nodeRect.right - (arrowRect?.right || nodeRect.right)),
                arrowVisible: Boolean(
                  arrowRect && arrowRect.width > 0 && arrowRect.height > 0
                  && arrow instanceof Element && getComputedStyle(arrow).visibility !== 'hidden'
                ),
                ordered: Boolean(
                  iconRect && copyRect && arrowRect
                  && iconRect.right <= copyRect.left
                  && copyRect.right <= arrowRect.left
                  && copyRect.width > 0
                  && (!detailRect || !labelRect || labelRect.bottom <= detailRect.top)
                ),
                horizontalClipped: node.scrollWidth > node.clientWidth + 1,
              };
            })
          : [];
        const navigationTree = document.querySelector('#primary-sidebar .product-side-navigation__tree');
        const navigationMenu = navigationTree?.querySelector('.sc-navigation-menu');
        const topbar = document.querySelector('.topbar');
        const topbarActions = topbar?.querySelector('.topbar-actions');
        const pageFrame = document.querySelector('.router-host > [data-product-page-mode]');
        const topbarRect = topbar?.getBoundingClientRect();
        const topbarActionsRect = topbarActions?.getBoundingClientRect();
        const pageFrameRect = pageFrame?.getBoundingClientRect();
        const topbarActionItems = topbarActions instanceof HTMLElement
          ? [...topbarActions.children]
            .filter((node) => {
              if (!(node instanceof HTMLElement)) return false;
              const rect = node.getBoundingClientRect();
              const nodeStyle = getComputedStyle(node);
              return nodeStyle.display !== 'none' && nodeStyle.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
            })
            .map((node) => {
              const rect = node.getBoundingClientRect();
              const action = node.matches('button') ? node : node.querySelector('button');
              return {
                label: String(action?.getAttribute('aria-label') || action?.getAttribute('title') || action?.textContent || '').replace(/\s+/g, ' ').trim(),
                rect: [Math.round(rect.left), Math.round(rect.top), Math.round(rect.right), Math.round(rect.bottom)],
                withinViewport: rect.left >= -1 && rect.right <= window.innerWidth + 1,
                withinActions: Boolean(topbarActionsRect) && rect.left >= topbarActionsRect.left - 1 && rect.right <= topbarActionsRect.right + 1,
              };
            })
          : [];
        const workItemCards = [...document.querySelectorAll('[data-work-item-key]')]
          .filter((node) => node instanceof HTMLElement && node.offsetParent !== null)
          .map((node) => {
            const rect = node.getBoundingClientRect();
            return {
              recordId: node.getAttribute('data-record-id') || '',
              state: node.getAttribute('data-work-item-state') || '',
              rect: [Math.round(rect.left), Math.round(rect.top), Math.round(rect.right), Math.round(rect.bottom)],
              fullyVisible: rect.top >= 0 && rect.bottom <= window.innerHeight,
              primaryFactCount: node.querySelectorAll('[data-primary-fact-key]').length,
              supplementaryFactCount: node.querySelectorAll('[data-supplementary-fact-key]').length,
              disclosureCount: node.querySelectorAll('[data-disclosure-trigger]').length,
              actionLabels: [...node.querySelectorAll('button')]
                .filter((button) => button instanceof HTMLElement && button.offsetParent !== null)
                .map((button) => String(button.textContent || '').replace(/\s+/g, ' ').trim())
                .filter(Boolean),
            };
          });
        const homeWorkItems = [...document.querySelectorAll('[data-role-home] [data-record-id]')]
          .filter((node) => node instanceof HTMLElement && node.offsetParent !== null)
          .map((node) => ({
            recordId: node.getAttribute('data-record-id') || '',
            state: node.getAttribute('data-work-item-state') || '',
            text: String(node.textContent || '').replace(/\s+/g, ' ').trim(),
          }));
        const detailRecordId = document.querySelector('[data-semantic-component="ContractFormPage"]')?.getAttribute('data-form-record') || '';
        return {
          h1: document.querySelectorAll('h1').length,
          pageHeaders: document.querySelectorAll('.template-page-header, [data-product-page-header]').length,
          primaryActions: [...document.querySelectorAll('[data-product-primary-action]')]
            .filter((node) => node instanceof HTMLElement && node.offsetParent !== null).length,
          presentationModes: [...new Set([...document.querySelectorAll('[data-product-page-pattern][data-presentation-mode]')].map((node) => node.getAttribute('data-presentation-mode')).filter(Boolean))],
          nativeStructureCount: document.querySelectorAll('[data-native-contract-structure]').length,
          nativeNotebookPageCount: document.querySelectorAll('[data-native-contract-structure] .t-tabs__nav-item').length,
          loadedSurfaceEvidence: {
            homeState: homeRoot?.getAttribute('data-state') || '',
            myWorkState: document.querySelector('[data-semantic-component="MyWorkView"]')?.getAttribute('data-state') || '',
            collectionState: document.querySelector('[data-semantic-component="ActionView"]')?.getAttribute('data-collection-state') || '',
            formState: document.querySelector('[data-semantic-component="ContractFormPage"]')?.getAttribute('data-state') || '',
          },
          workItemEvidence: {
            cards: workItemCards,
            homeItems: homeWorkItems,
            detailRecordId,
            fullyVisibleCardCount: workItemCards.filter((item) => item.fullyVisible).length,
          },
          overflow: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - window.innerWidth,
          shellGeometry: {
            topbarHeight: Math.round(topbarRect?.height || 0),
            contentStart: Math.round(pageFrameRect?.top || 0),
            minimal: Boolean(topbar?.classList.contains('topbar--minimal')),
          },
          topbarActionEvidence: topbar instanceof HTMLElement && topbarActions instanceof HTMLElement && topbarRect && topbarActionsRect ? {
            topbarRect: [Math.round(topbarRect.left), Math.round(topbarRect.top), Math.round(topbarRect.right), Math.round(topbarRect.bottom)],
            actionsRect: [Math.round(topbarActionsRect.left), Math.round(topbarActionsRect.top), Math.round(topbarActionsRect.right), Math.round(topbarActionsRect.bottom)],
            actionItems: topbarActionItems,
            horizontalClipped: topbarActions.scrollWidth > topbarActions.clientWidth + 1,
            pass: topbarActionsRect.left >= topbarRect.left - 1
              && topbarActionsRect.right <= topbarRect.right + 1
              && topbarActionsRect.left >= -1
              && topbarActionsRect.right <= window.innerWidth + 1
              && topbarActions.scrollWidth <= topbarActions.clientWidth + 1
              && topbarActionItems.length > 0
              && topbarActionItems.every((item) => item.label && item.withinViewport && item.withinActions),
          } : null,
          homePresentationEvidence: homeRoot ? {
            quickEntryCount: homeQuickEntries.length,
            quickEntries: homeQuickEntries,
            pass: homeQuickEntries.length > 0
              && homeQuickEntries.every((entry) => entry.label
                && entry.contentDisplay === 'grid'
                && entry.contentColumns !== 'none'
                && entry.copyDisplay === 'grid'
                && entry.contentWidth >= entry.buttonWidth - 24
                && entry.arrowVisible
                && entry.arrowRightGap >= 8
                && entry.arrowRightGap <= 16
                && entry.ordered
                && !entry.horizontalClipped),
          } : null,
          navigationHorizontalEvidence: navigationTree instanceof HTMLElement && navigationMenu instanceof HTMLElement ? {
            treeClientWidth: navigationTree.clientWidth,
            treeScrollWidth: navigationTree.scrollWidth,
            menuClientWidth: navigationMenu.clientWidth,
            menuScrollWidth: navigationMenu.scrollWidth,
            pass: navigationTree.scrollWidth <= navigationTree.clientWidth + 1
              && navigationMenu.scrollWidth <= navigationMenu.clientWidth + 1,
          } : null,
          tokenLoaded: Boolean(style.getPropertyValue('--sc-semantic-surface-interactive').trim()),
          themeEvidence: {
            mode: root.getAttribute('data-sc-theme-mode') || '',
            resolved: root.getAttribute('data-sc-theme-resolved') || '',
          },
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
          analysisEvidence: analysisRoot ? {
            view: analysisView,
            state: analysisState,
            reason: analysisReason,
            pivotRowCount: analysisPivotRows,
            graphRowCount: analysisGraphRows,
            pass: analysisState === 'ready'
              && !analysisReason
              && (analysisView === 'pivot' ? analysisPivotRows > 0 : analysisView === 'graph' && analysisGraphRows > 0),
          } : null,
          activityEvidence: activityRoot ? {
            state: activityRoot.getAttribute('data-state') || '',
            cardCount: activityCards.length,
            cards: activityCardEvidence,
            visibleRawIdentityCount: activityCardEvidence.filter((entry) => /记录\s*#\d+/.test(entry.visibleText)).length,
            pass: activityRoot.getAttribute('data-state') === 'ready'
              && activityCards.length > 0
              && activityCardEvidence.every((entry) => entry.ordinal && !entry.horizontalClipped && !entry.verticalClipped)
              && activityCardEvidence.every((entry) => !/记录\s*#\d+/.test(entry.visibleText)),
          } : null,
          relationTagEvidence: {
            cellCount: relationTagCells.length,
            labels: relationTagLabels,
            numericOnlyLabelCount: relationTagLabels.filter((label) => /^\d+$/.test(label)).length,
            pass: relationTagCells.length > 0
              && relationTagLabels.length > 0
              && relationTagLabels.every((label) => !/^\d+$/.test(label)),
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
          const shell = document.querySelector('.layout-shell');
          const shellStyle = shell instanceof HTMLElement ? getComputedStyle(shell) : null;
          scrollOwner.scrollTop = scrollOwner.scrollHeight;
          const observedScrollTop = scrollOwner.scrollTop;
          scrollOwner.scrollTop = 0;
          return {
            viewportHeight: window.innerHeight,
            sidebarHeight: sidebar.clientHeight,
            sidebarComputedHeight: sidebarStyle.height,
            sidebarMinHeight: sidebarStyle.minHeight,
            sidebarMaxHeight: sidebarStyle.maxHeight,
            sidebarBlockSize: sidebarStyle.blockSize,
            sidebarMaxBlockSize: sidebarStyle.maxBlockSize,
            sidebarDisplay: sidebarStyle.display,
            shellClientHeight: shell instanceof HTMLElement ? shell.clientHeight : 0,
            shellComputedHeight: shellStyle?.height || '',
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
      let hierarchicalWorkspaceEvidence = null;
      if (target.exerciseHierarchicalWorkspace === true) {
        const worksheet = page.locator('[data-semantic-component="HierarchicalWorksheet"][data-state="ready"]:visible');
        await worksheet.waitFor({ state: 'visible', timeout: 45000 });
        const search = worksheet.locator('[data-semantic-component="ProductListHeader"] input[type="search"]');
        const scopeTrigger = worksheet.locator('.worksheet-scope-trigger:visible');
        const initialCountText = String(await worksheet.locator('.worksheet-grid-title span').first().textContent() || '').trim();
        let mobileScopeEvidence = null;
        if (viewport.name === 'mobile') {
          const waitForDrawerBoundaryToSettle = async () => {
            await page.waitForFunction(() => {
              const surface = [...document.querySelectorAll('[data-semantic-component="ScDrawer"][data-state="open"]')]
                .find((node) => node instanceof HTMLElement && node.offsetParent !== null);
              if (!(surface instanceof HTMLElement)) return false;
              const box = surface.getBoundingClientRect();
              return box.left >= -1 && box.right <= window.innerWidth + 1;
            }, undefined, { timeout: 2000 });
            await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
          };
          const captureDrawerBoundary = async (drawer) => drawer.evaluate((surface) => {
            const rect = (node) => {
              if (!(node instanceof HTMLElement)) return null;
              const box = node.getBoundingClientRect();
              return {
                left: Math.round(box.left),
                right: Math.round(box.right),
                top: Math.round(box.top),
                bottom: Math.round(box.bottom),
                width: Math.round(box.width),
                height: Math.round(box.height),
              };
            };
            const panel = surface.closest('.sc-design-drawer');
            const title = surface.querySelector('h2');
            const close = surface.querySelector('[aria-label="关闭"]');
            const firstTreeNode = surface.querySelector('.tree-node');
            const fitsViewport = (box) => Boolean(box && box.left >= -1 && box.right <= window.innerWidth + 1 && box.top >= -1 && box.bottom <= window.innerHeight + 1);
            return {
              viewport: { width: window.innerWidth, height: window.innerHeight },
              panel: rect(panel),
              surface: rect(surface),
              title: rect(title),
              titleText: String(title?.textContent || '').trim(),
              titleClipped: title instanceof HTMLElement && (title.scrollWidth > title.clientWidth + 1 || title.scrollHeight > title.clientHeight + 1),
              close: rect(close),
              treeNode: rect(firstTreeNode),
              pass: fitsViewport(rect(panel))
                && fitsViewport(rect(surface))
                && fitsViewport(rect(title))
                && fitsViewport(rect(close))
                && fitsViewport(rect(firstTreeNode))
                && String(title?.textContent || '').trim().length > 0
                && !(title instanceof HTMLElement && (title.scrollWidth > title.clientWidth + 1 || title.scrollHeight > title.clientHeight + 1)),
            };
          });
          const originalViewport = page.viewportSize();
          await scopeTrigger.click();
          const drawer = page.getByRole('dialog', { name: /收入合同履约结构|选择范围/ });
          await drawer.waitFor({ state: 'visible', timeout: 15000 });
          await waitForDrawerBoundaryToSettle();
          const initialDescription = String(await drawer.getAttribute('aria-describedby') || '');
          const initialBoundary = await captureDrawerBoundary(drawer);
          await drawer.press('Escape');
          await drawer.waitFor({ state: 'hidden', timeout: 15000 });
          const escapeFocusRestored = await scopeTrigger.evaluate((node) => node === document.activeElement);
          await scopeTrigger.click();
          await drawer.waitFor({ state: 'visible', timeout: 15000 });
          await waitForDrawerBoundaryToSettle();
          const reopenedBoundary = await captureDrawerBoundary(drawer);
          const alternateWidth = originalViewport?.width === 320 ? 390 : 320;
          await page.setViewportSize({ width: alternateWidth, height: originalViewport?.height || 900 });
          await waitForDrawerBoundaryToSettle();
          const resizedBoundary = await captureDrawerBoundary(drawer);
          await page.setViewportSize({ width: originalViewport?.width || mobileWidth, height: originalViewport?.height || 900 });
          await waitForDrawerBoundaryToSettle();
          const restoredBoundary = await captureDrawerBoundary(drawer);
          await page.screenshot({ path: path.join(outputDir, `mobile-${target.name.replace(/[^a-zA-Z0-9_-]/g, '_')}-scope-drawer-open.png`), fullPage: false });
          const firstScope = drawer.locator('.tree-node').first();
          const chosenScope = String(await firstScope.textContent() || '').replace(/\s+/g, ' ').trim().replace(/^[▾▸]\s*/, '');
          await firstScope.click();
          await drawer.waitFor({ state: 'hidden', timeout: 15000 });
          const selectedScope = String(await scopeTrigger.textContent() || '').replace(/\s+/g, ' ').trim();
          await scopeTrigger.click();
          await drawer.waitFor({ state: 'visible', timeout: 15000 });
          await drawer.locator('.navigation-all').click();
          await drawer.waitFor({ state: 'hidden', timeout: 15000 });
          const clearedScope = String(await scopeTrigger.textContent() || '').replace(/\s+/g, ' ').trim();
          await scopeTrigger.click();
          await drawer.waitFor({ state: 'visible', timeout: 15000 });
          await drawer.locator('.tree-node').first().click();
          await drawer.waitFor({ state: 'hidden', timeout: 15000 });
          mobileScopeEvidence = {
            initialDescription,
            chosenScope,
            selectedScope,
            clearedScope,
            touchHeight: Math.round((await scopeTrigger.boundingBox())?.height || 0),
            initialBoundary,
            reopenedBoundary,
            resizedBoundary,
            restoredBoundary,
            escapeFocusRestored,
          };
        } else {
          await worksheet.locator('.worksheet-navigation .tree-node').first().click();
        }
        await page.waitForFunction(() => document.querySelectorAll('.worksheet-table-scroll tbody tr[data-record-id]').length > 0);
        const scopedTitle = String(await worksheet.locator('.worksheet-grid-title strong').textContent() || '').trim();
        const scopedCountText = String(await worksheet.locator('.worksheet-grid-title span').first().textContent() || '').trim();
        const initialSelectedId = String(await worksheet.locator('tbody tr[aria-selected="true"]').first().getAttribute('data-record-id') || '');
        await search.fill('__c1_no_match__');
        await page.waitForFunction(() => document.querySelectorAll('.worksheet-table-scroll tbody tr[data-record-id]').length === 0
          && !document.querySelector('.worksheet-open-record'));
        const zeroState = {
          countText: String(await worksheet.locator('.worksheet-grid-title span').first().textContent() || '').trim(),
          selectedRows: await worksheet.locator('tbody tr[aria-selected="true"]').count(),
          openActions: await worksheet.locator('.worksheet-open-record').count(),
          emptyStates: await worksheet.locator('[data-semantic-component="ScEmptyState"]:visible').count(),
          detailHint: String(await worksheet.locator('.worksheet-detail-empty').textContent() || '').trim(),
        };
        await worksheet.locator('[data-semantic-component="ProductListHeader"]').getByRole('button', { name: '清除', exact: true }).click();
        await page.waitForFunction(() => document.querySelectorAll('.worksheet-table-scroll tbody tr[data-record-id]').length > 0
          && Boolean(document.querySelector('.worksheet-open-record')));
        const restoredCountText = String(await worksheet.locator('.worksheet-grid-title span').first().textContent() || '').trim();
        const restoredSelectedId = String(await worksheet.locator('tbody tr[aria-selected="true"]').first().getAttribute('data-record-id') || '');
        const selectedRow = worksheet.locator('tbody tr[aria-selected="true"]').first();
        const searchableText = await selectedRow.locator('td').evaluateAll((cells) => cells
          .map((cell) => String(cell.textContent || '').replace(/\s+/g, ' ').trim())
          .find((value) => value.length >= 2) || '');
        if (!searchableText) throw new Error(`${target.name}: selected hierarchical row has no searchable text`);
        await search.fill(searchableText);
        await page.waitForFunction(() => document.querySelectorAll('.worksheet-table-scroll tbody tr[data-record-id]').length > 0);
        const retainedQuery = await search.inputValue();
        const retainedSelectedId = String(await worksheet.locator('tbody tr[aria-selected="true"]').first().getAttribute('data-record-id') || '');
        const monetaryValues = await worksheet.locator('[data-detail-field][data-field-type="monetary"]:visible').allTextContents();
        const tableScroll = worksheet.locator('[data-table-scroll-region="true"]');
        const scrollBefore = await tableScroll.evaluate((node) => {
          node.scrollLeft = Math.min(96, Math.max(0, node.scrollWidth - node.clientWidth));
          return { left: Math.round(node.scrollLeft), max: Math.round(node.scrollWidth - node.clientWidth) };
        });
        let separatorEvidence = null;
        if (viewport.name === 'desktop') {
          const navigationSeparator = worksheet.locator('.worksheet-resizer-navigation');
          const detailSeparator = worksheet.locator('.worksheet-resizer-detail');
          const navigationBefore = Number(await navigationSeparator.getAttribute('aria-valuenow'));
          await navigationSeparator.focus();
          await navigationSeparator.press('ArrowRight');
          const navigationAfter = Number(await navigationSeparator.getAttribute('aria-valuenow'));
          await navigationSeparator.press('Home');
          const navigationMinimum = Number(await navigationSeparator.getAttribute('aria-valuenow'));
          const detailBefore = Number(await detailSeparator.getAttribute('aria-valuenow'));
          await detailSeparator.focus();
          await detailSeparator.press('ArrowUp');
          const detailAfter = Number(await detailSeparator.getAttribute('aria-valuenow'));
          await detailSeparator.press('End');
          const detailMaximum = Number(await detailSeparator.getAttribute('aria-valuenow'));
          separatorEvidence = {
            navigationBefore, navigationAfter, navigationMinimum,
            detailBefore, detailAfter, detailMaximum,
            navigationFocused: await navigationSeparator.evaluate((node) => node === document.activeElement),
            detailFocused: await detailSeparator.evaluate((node) => node === document.activeElement),
          };
        }
        const beforeOpenUrl = page.url();
        const detailResponse = page.waitForResponse(isContractV2Response, { timeout: 45000 });
        await worksheet.locator('.worksheet-open-record').click();
        await page.waitForURL((url) => url.href !== beforeOpenUrl, { timeout: 15000 });
        await detailResponse;
        await waitForStableProductSurface(page);
        const detailRecordId = String(await page.locator('[data-semantic-component="ContractFormPage"]').getAttribute('data-form-record') || '');
        const returnAction = page.locator('[data-form-secondary-action="return-list"]:visible');
        if (await returnAction.count() === 1) {
          await returnAction.click();
        } else {
          const mobileActionTrigger = page.locator('[data-semantic-component="ScButton"][aria-label="打开更多页面操作"]:visible');
          await mobileActionTrigger.click();
          const mobileReturn = page.locator('.t-dropdown__item:visible').filter({ hasText: '返回' });
          await mobileReturn.click();
        }
        await page.waitForURL((url) => url.pathname === new URL(beforeOpenUrl).pathname, { timeout: 15000 });
        await waitForStableProductSurface(page);
        const restoredWorksheet = page.locator('[data-semantic-component="HierarchicalWorksheet"][data-state="ready"]:visible');
        const returnState = {
          query: await restoredWorksheet.locator('[data-semantic-component="ProductListHeader"] input[type="search"]').inputValue(),
          scope: String(await restoredWorksheet.locator('.worksheet-grid-title strong').textContent() || '').trim(),
          selectedId: String(await restoredWorksheet.locator('tbody tr[aria-selected="true"]').first().getAttribute('data-record-id') || ''),
          scrollLeft: Math.round(await restoredWorksheet.locator('[data-table-scroll-region="true"]').evaluate((node) => node.scrollLeft)),
        };
        hierarchicalWorkspaceEvidence = {
          initialCountText, scopedCountText, scopedTitle, initialSelectedId, zeroState, restoredCountText, restoredSelectedId,
          retainedQuery, retainedSelectedId, monetaryValues, scrollBefore, separatorEvidence, mobileScopeEvidence,
          detailRecordId, returnState,
          pass: /46/.test(initialCountText)
            && initialSelectedId.length > 0
            && /0/.test(zeroState.countText)
            && zeroState.selectedRows === 0
            && zeroState.openActions === 0
            && zeroState.emptyStates === 1
            && zeroState.detailHint.length > 0
            && restoredSelectedId.length > 0
            && monetaryValues.length > 0
            && monetaryValues.every((value) => /¥|CNY/.test(value) && /\.\d{2}/.test(value))
            && detailRecordId === retainedSelectedId
            && returnState.query === retainedQuery
            && returnState.scope === scopedTitle
            && returnState.selectedId === retainedSelectedId
            && returnState.scrollLeft === scrollBefore.left
            && (viewport.name !== 'desktop' || (
              separatorEvidence.navigationAfter > separatorEvidence.navigationBefore
              && separatorEvidence.navigationMinimum === 200
              && separatorEvidence.detailAfter > separatorEvidence.detailBefore
              && separatorEvidence.detailMaximum === 420
              && separatorEvidence.detailFocused
            ))
            && (viewport.name !== 'mobile' || (
              mobileScopeEvidence.chosenScope.length > 0
              && mobileScopeEvidence.selectedScope.includes(mobileScopeEvidence.chosenScope)
              && mobileScopeEvidence.clearedScope.includes('全部收入合同')
              && mobileScopeEvidence.touchHeight >= 44
              && mobileScopeEvidence.initialBoundary.pass
              && mobileScopeEvidence.reopenedBoundary.pass
              && mobileScopeEvidence.resizedBoundary.pass
              && mobileScopeEvidence.restoredBoundary.pass
              && mobileScopeEvidence.escapeFocusRestored
            )),
        };
        if (!hierarchicalWorkspaceEvidence.pass) throw new Error(`${target.name}: hierarchical workspace journey failed ${JSON.stringify(hierarchicalWorkspaceEvidence)}`);
      }
      if (target.captureFormStructure === true && target.expectReadonlyDetailComparison === true) {
        const expectedDetail = viewport.name === 'desktop' ? '.o2m-readonly-table:visible' : '.o2m-readonly-list:visible';
        await page.locator(expectedDetail).first().waitFor({ state: 'visible', timeout: 15000 });
      }
      if (target.captureFieldAlignment === true && target.expandFormDisclosures === true) {
        const collapsedDisclosures = page.locator('[data-semantic-component="ScDisclosure"] [data-disclosure-trigger][data-state="collapsed"]:visible');
        for (let index = await collapsedDisclosures.count() - 1; index >= 0; index -= 1) {
          await collapsedDisclosures.nth(index).click();
        }
        await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      }
      await page.screenshot({ path: path.join(outputDir, `${viewport.name}-${target.name.replace(/[^a-zA-Z0-9_-]/g, '_')}.png`), fullPage: false });
      if (target.captureFormStructure === true) {
        const screenshotStem = `${viewport.name}-${target.name.replace(/[^a-zA-Z0-9_-]/g, '_')}`;
        let popupBoundaryEvidence = { checked: false, reason: 'no enabled visible select', pass: true };
        const formSelects = page.locator('.field [data-semantic-component="ScSelect"]:visible, .field [role="combobox"]:visible');
        for (let index = 0; index < await formSelects.count(); index += 1) {
          const select = formSelects.nth(index);
          const enabled = await select.evaluate((node) => {
            const input = node.querySelector('input');
            return node.getAttribute('aria-disabled') !== 'true' && !(input instanceof HTMLInputElement && input.disabled);
          });
          if (!enabled) continue;
          await select.click();
          await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
          popupBoundaryEvidence = await page.evaluate(() => {
            const visible = (node) => node instanceof HTMLElement && node.offsetParent !== null;
            const select = [...document.querySelectorAll('.field [data-semantic-component="ScSelect"], .field [role="combobox"]')]
              .find((node) => visible(node) && (node === document.activeElement || node.contains(document.activeElement)))
              || null;
            const popup = [...document.querySelectorAll('[role="listbox"]')]
              .find((node) => visible(node) && node.getBoundingClientRect().width > 0);
            const pack = (node) => {
              if (!(node instanceof HTMLElement)) return null;
              const rect = node.getBoundingClientRect();
              return [Math.round(rect.left), Math.round(rect.top), Math.round(rect.right), Math.round(rect.bottom)];
            };
            const popupRect = popup instanceof HTMLElement ? popup.getBoundingClientRect() : null;
            return {
              checked: true,
              selectRect: pack(select),
              popupFound: popup instanceof HTMLElement,
              popupRect: pack(popup),
              viewport: [window.innerWidth, window.innerHeight],
              pass: popupRect instanceof DOMRect
                && popupRect.left >= -1
                && popupRect.right <= window.innerWidth + 1
                && popupRect.top >= -1
                && popupRect.bottom <= window.innerHeight + 1,
            };
          });
          await page.keyboard.press('Escape');
          break;
        }
        const top = await page.evaluate(() => {
          const visible = (node) => node instanceof HTMLElement && node.offsetParent !== null;
          const box = (node) => {
            if (!(node instanceof HTMLElement)) return null;
            const rect = node.getBoundingClientRect();
            const style = getComputedStyle(node);
            return {
              selector: node.getAttribute('data-semantic-component') || node.className || node.tagName,
              rect: [Math.round(rect.left), Math.round(rect.top), Math.round(rect.right), Math.round(rect.bottom)],
              size: [Math.round(rect.width), Math.round(rect.height)],
              clientWidth: node.clientWidth,
              scrollWidth: node.scrollWidth,
              minWidth: style.minWidth,
              width: style.width,
              maxWidth: style.maxWidth,
              paddingInline: [style.paddingLeft, style.paddingRight],
              boxSizing: style.boxSizing,
              overflowX: style.overflowX,
            };
          };
          const boundary = (node, owner) => {
            if (!(node instanceof HTMLElement) || !(owner instanceof HTMLElement)) return null;
            const rect = node.getBoundingClientRect();
            const ownerRect = owner.getBoundingClientRect();
            const ownerStyle = getComputedStyle(owner);
            const ownerLeft = ownerRect.left + parseFloat(ownerStyle.borderLeftWidth || '0') + parseFloat(ownerStyle.paddingLeft || '0');
            const ownerRight = ownerRect.right - parseFloat(ownerStyle.borderRightWidth || '0') - parseFloat(ownerStyle.paddingRight || '0');
            return {
              node: box(node),
              owner: box(owner),
              overflowLeft: Math.max(0, Math.round(ownerLeft - rect.left)),
              overflowRight: Math.max(0, Math.round(rect.right - ownerRight)),
              pass: rect.left >= ownerLeft - 1 && rect.right <= ownerRight + 1,
            };
          };
          const boundarySet = (selector, ownerSelector) => [...document.querySelectorAll(selector)]
            .filter(visible)
            .map((node) => boundary(node, node.parentElement?.closest(ownerSelector)))
            .filter(Boolean);
          const firstVisible = (selector) => [...document.querySelectorAll(selector)].find(visible) || null;
          const header = [...document.querySelectorAll('.template-page-header')].find(visible);
          const relation = [...document.querySelectorAll('[data-floorplan-region="relation"]')].find(visible);
          const addAction = [...document.querySelectorAll('button')].find((node) => visible(node) && /添加.*明细/.test(String(node.textContent || '')));
          const sectionNavigation = [...document.querySelectorAll('[data-form-section-navigation]')].find(visible);
          const summaryFields = [...document.querySelectorAll('[data-floorplan-region="summary"] .canonical-form-node')].filter(visible);
          const monetarySummary = summaryFields.find((node) => node instanceof HTMLElement && node.dataset.valueEmphasis === 'monetary');
          const visualSummaryFields = [...summaryFields].sort((left, right) => {
            const leftRect = left.getBoundingClientRect();
            const rightRect = right.getBoundingClientRect();
            return Math.abs(leftRect.top - rightRect.top) > 2 ? leftRect.top - rightRect.top : leftRect.left - rightRect.left;
          });
          const relationFrameDepth = relation instanceof HTMLElement
            ? [...relation.querySelectorAll('*')].filter((node) => {
                if (!(node instanceof HTMLElement) || !visible(node)) return false;
                const style = getComputedStyle(node);
                return parseFloat(style.borderLeftWidth) > 0 && parseFloat(style.borderRightWidth) > 0
                  && parseFloat(style.borderTopWidth) > 0 && parseFloat(style.borderBottomWidth) > 0;
              }).length
            : 0;
          const pattern = firstVisible('[data-product-page-pattern]');
          const driver = firstVisible('.sc-form-driver-host');
          const nativePage = firstVisible('[data-native-contract-structure]');
          const navigation = firstVisible('[data-form-section-navigation]');
          const navigationTrack = firstVisible('.form-section-navigation__track');
          const tree = firstVisible('.sc-native-contract-tree');
          const authorizedScrollers = [...document.querySelectorAll('.form-section-navigation__track, .o2m-table-scroll, [data-table-scroll-region="true"]')]
            .filter(visible)
            .map((node) => {
              const style = getComputedStyle(node);
              const rect = node.getBoundingClientRect();
              return {
                node: box(node),
                scrollable: node.scrollWidth > node.clientWidth,
                overflowPermitted: ['auto', 'scroll'].includes(style.overflowX),
                withinViewport: rect.left >= -1 && rect.right <= window.innerWidth + 1,
                pass: ['auto', 'scroll'].includes(style.overflowX) && rect.left >= -1 && rect.right <= window.innerWidth + 1,
              };
            });
          const nestedBoundaries = [
            ...boundarySet('.native-form-tree', '.sc-native-contract-tree, [data-native-contract-structure]'),
            ...boundarySet('.native-container--group', '.native-container--group, .native-form-tree, .sc-native-contract-tree'),
            ...boundarySet('.template-form-section', '.native-container--group, .native-form-tree, .sc-native-contract-tree, [data-native-contract-structure]'),
            ...boundarySet('.template-form-section-grid', '.template-form-section'),
            ...boundarySet('.template-form-section-grid > .field', '.template-form-section-grid'),
            ...boundarySet('.template-form-section-grid > .field input, .template-form-section-grid > .field textarea, .template-form-section-grid > .field select, .template-form-section-grid > .field [role="combobox"]', '.field'),
          ];
          const responsiveBoundaryEvidence = {
            patternInDriver: boundary(pattern, driver),
            nativePageInPattern: boundary(nativePage, pattern),
            navigationInNativePage: boundary(navigation, nativePage),
            navigationTrackInNavigation: boundary(navigationTrack, navigation),
            treeInNativePage: boundary(tree, nativePage),
            nestedBoundaries,
            checkedNestedBoundaryCount: nestedBoundaries.length,
            authorizedScrollers,
          };
          responsiveBoundaryEvidence.pass = [
            responsiveBoundaryEvidence.patternInDriver,
            responsiveBoundaryEvidence.nativePageInPattern,
            responsiveBoundaryEvidence.navigationInNativePage,
            responsiveBoundaryEvidence.navigationTrackInNavigation,
            responsiveBoundaryEvidence.treeInNativePage,
            ...responsiveBoundaryEvidence.nestedBoundaries,
          ].filter(Boolean).every((item) => item.pass)
            && responsiveBoundaryEvidence.checkedNestedBoundaryCount > 0
            && responsiveBoundaryEvidence.authorizedScrollers.every((item) => item.pass);
          const background = header instanceof HTMLElement ? getComputedStyle(header).backgroundColor : '';
          const alpha = background.match(/rgba?\([^)]*(?:,|\/)\s*([\d.]+)\s*\)$/)?.[1];
          return {
            sectionLinks: [...document.querySelectorAll('[data-form-section-navigation] [data-section-link]')]
              .filter(visible).map((node) => String(node.textContent || '').replace(/\s+/g, ' ').trim()),
            currentSectionCount: [...document.querySelectorAll('[data-form-section-navigation] [aria-current="location"]')].filter(visible).length,
            navigationOverflowDiscoverable: sectionNavigation instanceof HTMLElement
              && (sectionNavigation.dataset.overflowAfter !== 'true'
                || [...sectionNavigation.querySelectorAll('.form-section-navigation__cue--after')].some(visible)),
            sectionTitles: [...document.querySelectorAll('[data-section-title], [data-form-semantic-role] .native-container-head h3')]
              .filter(visible).map((node) => String(node instanceof HTMLElement ? node.dataset.sectionTitle || node.textContent || '' : '').replace(/\s+/g, ' ').trim()).filter(Boolean),
            relationInFirstViewport: relation instanceof HTMLElement && relation.getBoundingClientRect().top < window.innerHeight,
            addActionInFirstViewport: addAction instanceof HTMLElement && addAction.getBoundingClientRect().bottom <= window.innerHeight,
            relationFrameDepth,
            mobileMonetarySummaryFirst: !monetarySummary || visualSummaryFields[0] === monetarySummary,
            stickyHeaderBackground: background,
            stickyHeaderOpaque: Boolean(background) && background !== 'transparent' && background !== 'rgba(0, 0, 0, 0)' && alpha !== '0',
            readonlyTableVisible: [...document.querySelectorAll('.o2m-readonly-table')].some(visible),
            readonlyCardsVisible: [...document.querySelectorAll('.o2m-readonly-list')].some(visible),
            attachmentHeadings: [...document.querySelectorAll('.relation-attachment-heading, .professional-attachment-heading')]
              .filter(visible).map((node) => String(node.textContent || '').replace(/\s+/g, ' ').trim()),
            responsiveBoundaryEvidence,
          };
        });
        const navigationJourney = [];
        const sectionLinkCount = await page.locator('[data-form-section-navigation] [data-section-link]').count();
        for (let index = 0; index < sectionLinkCount; index += 1) {
          const link = page.locator('[data-form-section-navigation] [data-section-link]').nth(index);
          await link.evaluate((node) => {
            const track = node.parentElement;
            if (!(node instanceof HTMLElement) || !(track instanceof HTMLElement)) return;
            track.scrollTo({ left: Math.max(0, node.offsetLeft - (track.clientWidth - node.offsetWidth) / 2), behavior: 'auto' });
          });
          await link.click();
          await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
          navigationJourney.push(await link.evaluate((node) => {
            const selector = node instanceof HTMLElement ? String(node.dataset.sectionTarget || '') : '';
            const expectedLabel = String(node.textContent || '').replace(/\s+/g, ' ').trim();
            const expectedContentKind = node instanceof HTMLElement ? String(node.dataset.sectionContentKind || '') : '';
            const expectedSourceIdentity = node instanceof HTMLElement ? String(node.dataset.sectionSourceIdentity || '') : '';
            const nav = node.closest('[data-form-section-navigation]');
            const root = nav?.closest('[data-native-contract-structure], .object-task-page');
            const matches = selector && root ? [...root.querySelectorAll(selector)] : [];
            const target = matches.length === 1 ? matches[0] : null;
            const header = [...document.querySelectorAll('.template-page-header')]
              .find((candidate) => candidate instanceof HTMLElement && candidate.offsetParent !== null);
            const targetRect = target instanceof HTMLElement ? target.getBoundingClientRect() : null;
            const navRect = nav instanceof HTMLElement ? nav.getBoundingClientRect() : null;
            const track = node.parentElement;
            const trackRect = track instanceof HTMLElement ? track.getBoundingClientRect() : null;
            const linkRect = node instanceof HTMLElement ? node.getBoundingClientRect() : null;
            const headerRect = header instanceof HTMLElement ? header.getBoundingClientRect() : null;
            const obstructionBottom = Math.max(navRect?.bottom || 0, headerRect?.bottom || 0);
            const targetText = String(target?.textContent || '').replace(/\s+/g, ' ').trim();
            const targetLabels = target instanceof HTMLElement
              ? [targetText, target.getAttribute('aria-label'), target.dataset.sectionTitle]
                .map((value) => String(value || '').replace(/\s+/g, ' ').trim())
                .filter(Boolean)
              : [];
            return {
              key: node instanceof HTMLElement ? String(node.dataset.sectionLink || '') : '',
              current: node.getAttribute('aria-current') === 'location',
              targetMatchCount: matches.length,
              targetFound: target instanceof HTMLElement,
              expectedLabel,
              expectedContentKind,
              targetContentKind: target instanceof HTMLElement ? String(target.dataset.sectionContentKind || '') : '',
              expectedSourceIdentity,
              targetSourceIdentity: target instanceof HTMLElement ? String(target.dataset.sectionSourceIdentity || '') : '',
              targetIdentityMatches: target instanceof HTMLElement
                && Boolean(expectedSourceIdentity)
                && target.dataset.sectionSourceIdentity === expectedSourceIdentity,
              targetContentMatches: target instanceof HTMLElement
                && Boolean(expectedContentKind)
                && target.dataset.sectionContentKind === expectedContentKind
                && Boolean(expectedLabel)
                && targetLabels.some((label) => label.includes(expectedLabel)),
              targetTop: targetRect ? Math.round(targetRect.top) : null,
              obstructionBottom: Math.round(obstructionBottom),
              targetVisibleBelowSticky: Boolean(targetRect && targetRect.bottom > obstructionBottom && targetRect.top >= obstructionBottom - 2),
              linkFullyVisibleInTrack: Boolean(linkRect && trackRect && linkRect.left >= trackRect.left - 1 && linkRect.right <= trackRect.right + 1),
            };
          }));
        }
        const scrollMetrics = await page.evaluate(() => {
          const owner = document.querySelector('.router-host');
          if (owner instanceof HTMLElement) return { scrollHeight: owner.scrollHeight, viewportHeight: owner.clientHeight };
          const fallback = document.scrollingElement || document.documentElement;
          return { scrollHeight: fallback.scrollHeight, viewportHeight: fallback.clientHeight };
        });
        const captures = [];
        for (const [position, topOffset] of [['middle', Math.max(0, Math.floor((scrollMetrics.scrollHeight - scrollMetrics.viewportHeight) / 2))], ['bottom', Math.max(0, scrollMetrics.scrollHeight - scrollMetrics.viewportHeight)]]) {
          await page.evaluate((top) => {
            const owner = document.querySelector('.router-host');
            if (owner instanceof HTMLElement) owner.scrollTo({ top, behavior: 'auto' });
            else window.scrollTo({ top, behavior: 'auto' });
          }, topOffset);
          await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
          const sticky = await page.evaluate(() => {
            const header = [...document.querySelectorAll('.template-page-header')]
              .find((node) => node instanceof HTMLElement && node.offsetParent !== null);
            const rect = header instanceof HTMLElement ? header.getBoundingClientRect() : null;
            const background = header instanceof HTMLElement ? getComputedStyle(header).backgroundColor : '';
            const owner = document.querySelector('.router-host');
            const scrollTop = owner instanceof HTMLElement ? owner.scrollTop : window.scrollY;
            return { scrollY: Math.round(scrollTop), headerRect: rect ? [Math.round(rect.top), Math.round(rect.bottom)] : null, background };
          });
          await page.screenshot({ path: path.join(outputDir, `${screenshotStem}-${position}.png`), fullPage: false });
          captures.push({ position, ...sticky });
        }
        await page.evaluate(() => {
          const owner = document.querySelector('.router-host');
          if (owner instanceof HTMLElement) owner.scrollTo({ top: 0, behavior: 'auto' });
          else window.scrollTo({ top: 0, behavior: 'auto' });
        });
        formStructureEvidence = {
          ...top,
          popupBoundaryEvidence,
          navigationJourney,
          captures,
          pass: target.expectFormStructure !== true || (
            top.sectionLinks.length > 1
            && top.currentSectionCount === 1
            && top.navigationOverflowDiscoverable
            && top.stickyHeaderOpaque
            && top.responsiveBoundaryEvidence.pass
            && popupBoundaryEvidence.pass
            && navigationJourney.length === top.sectionLinks.length
            && navigationJourney.every((item) => item.current
              && item.targetMatchCount === 1
              && item.targetFound
              && item.targetIdentityMatches
              && item.targetContentMatches
              && item.targetVisibleBelowSticky
              && item.linkFullyVisibleInTrack)
            && (viewport.name !== 'mobile' || top.mobileMonetarySummaryFirst)
            && (target.expectRelationFirstViewport !== true || viewport.name !== 'desktop' || (top.relationInFirstViewport && top.addActionInFirstViewport))
            && (target.expectReadonlyDetailComparison !== true || (viewport.name === 'desktop' ? top.readonlyTableVisible : top.readonlyCardsVisible))
          ),
        };
      }
      if (target.captureFieldAlignment === true) {
        fieldAlignmentEvidence = await page.evaluate(() => {
          const visible = (node) => node instanceof HTMLElement
            && node.offsetParent !== null
            && node.getBoundingClientRect().width > 0
            && node.getBoundingClientRect().height > 0;
          const roundedRect = (node) => {
            if (!(node instanceof HTMLElement)) return null;
            const rect = node.getBoundingClientRect();
            return {
              left: Number(rect.left.toFixed(2)),
              top: Number(rect.top.toFixed(2)),
              right: Number(rect.right.toFixed(2)),
              bottom: Number(rect.bottom.toFixed(2)),
              width: Number(rect.width.toFixed(2)),
              height: Number(rect.height.toFixed(2)),
            };
          };
          const borderWidth = (node) => {
            if (!(node instanceof HTMLElement)) return 0;
            const style = getComputedStyle(node);
            return ['borderLeftWidth', 'borderRightWidth', 'borderTopWidth', 'borderBottomWidth']
              .map((key) => Number.parseFloat(style[key] || '0'))
              .reduce((sum, value) => sum + (Number.isFinite(value) ? value : 0), 0);
          };
          const visualFrame = (semanticRoot) => {
            if (!(semanticRoot instanceof HTMLElement)) return null;
            const candidates = [semanticRoot, ...semanticRoot.querySelectorAll('.t-input, .t-input-number, .t-textarea, input, textarea, select')]
              .filter(visible);
            return candidates.find((node) => borderWidth(node) > 0) || candidates[0] || semanticRoot;
          };
          const controlSelector = [
            '[data-semantic-component="ScInput"]',
            '[data-semantic-component="ScRelationField"]',
            '[data-semantic-component="ScSelect"]',
            '[data-semantic-component="ScDateField"]',
            '[data-semantic-component="ScNumberInput"]',
            '[data-semantic-component="ScTextarea"]',
          ].join(',');
          const excludedTypes = new Set(['boolean', 'binary', 'one2many', 'many2many']);
          const fields = [...document.querySelectorAll('[data-product-page-mode="form"] .template-form-section-grid > .field[data-field-name]')]
            .filter(visible)
            .map((field) => {
              const slot = field.querySelector(':scope > .field-control-row .field-control-main');
              const semanticRoot = slot instanceof HTMLElement
                ? [...slot.querySelectorAll(controlSelector)].find(visible) || null
                : null;
              const frame = visualFrame(semanticRoot);
              const label = field.querySelector(':scope > .field-label-row .label');
              const slotRect = roundedRect(slot);
              const frameRect = roundedRect(frame);
              const labelRect = roundedRect(label);
              const type = String(field.getAttribute('data-field-type') || '');
              const eligible = !excludedTypes.has(type) && slotRect !== null && frameRect !== null;
              return {
                name: String(field.getAttribute('data-field-name') || ''),
                type,
                state: String(field.getAttribute('data-field-state') || ''),
                semanticComponent: semanticRoot instanceof HTMLElement ? String(semanticRoot.dataset.semanticComponent || '') : '',
                groupDepth: field.closest('.native-form-tree')
                  ? [...field.closest('.native-form-tree').querySelectorAll('.native-container--group')]
                    .filter((group) => group.contains(field) && group !== field).length
                  : 0,
                fieldRect: roundedRect(field),
                slotRect,
                frameRect,
                labelRect,
                eligible,
                insetLeft: eligible ? Number((frameRect.left - slotRect.left).toFixed(2)) : null,
                insetRight: eligible ? Number((slotRect.right - frameRect.right).toFixed(2)) : null,
              };
            });
          const grids = [...document.querySelectorAll('[data-product-page-mode="form"] .template-form-section-grid')]
            .filter(visible)
            .map((grid, index) => ({
              index,
              rect: roundedRect(grid),
              fieldCount: [...grid.children].filter((child) => child instanceof HTMLElement && child.matches('.field') && visible(child)).length,
              ordinaryFieldCount: [...grid.children].filter((child) => child instanceof HTMLElement
                && child.matches('.field[data-field-type]')
                && visible(child)
                && !excludedTypes.has(String(child.getAttribute('data-field-type') || ''))).length,
              groupDepth: grid.closest('.native-form-tree')
                ? [...grid.closest('.native-form-tree').querySelectorAll('.native-container--group')]
                  .filter((group) => group.contains(grid)).length
                : 0,
            }))
            .filter((grid) => grid.ordinaryFieldCount > 0 && grid.rect);
          const eligible = fields.filter((field) => field.eligible);
          const ordinarySlots = fields.filter((field) => !excludedTypes.has(field.type) && field.slotRect);
          const frameFailures = eligible.filter((field) => Math.abs(field.insetLeft) > 1 || Math.abs(field.insetRight) > 1);
          const rowGroups = [];
          for (const field of ordinarySlots) {
            const controlRect = field.frameRect || field.slotRect;
            if (!field.fieldRect || !controlRect || !field.labelRect) continue;
            const row = rowGroups.find((candidate) => Math.abs(candidate.fieldTop - field.fieldRect.top) <= 1
              && Math.abs(candidate.labelHeight - field.labelRect.height) <= 1);
            const measuredField = { ...field, measuredControlTop: controlRect.top };
            if (row) row.fields.push(measuredField);
            else rowGroups.push({ fieldTop: field.fieldRect.top, labelHeight: field.labelRect.height, fields: [measuredField] });
          }
          const rowBaselineFailures = rowGroups
            .filter((row) => row.fields.length > 1)
            .map((row) => ({
              names: row.fields.map((field) => field.name),
              controlTops: row.fields.map((field) => field.measuredControlTop),
              delta: Number((Math.max(...row.fields.map((field) => field.measuredControlTop)) - Math.min(...row.fields.map((field) => field.measuredControlTop))).toFixed(2)),
            }))
            .filter((row) => row.delta > 1);
          const gridEdges = grids.map((grid) => ({ left: grid.rect.left, right: grid.rect.right, depth: grid.groupDepth }));
          const gridEdgeSpread = gridEdges.length > 1 ? {
            left: Number((Math.max(...gridEdges.map((edge) => edge.left)) - Math.min(...gridEdges.map((edge) => edge.left))).toFixed(2)),
            right: Number((Math.max(...gridEdges.map((edge) => edge.right)) - Math.min(...gridEdges.map((edge) => edge.right))).toFixed(2)),
          } : { left: 0, right: 0 };
          return {
            tolerance: 1,
            fields,
            grids,
            eligibleControlCount: eligible.length,
            ordinarySlotCount: ordinarySlots.length,
            frameFailures,
            rowBaselineFailures,
            gridEdgeSpread,
            meetsControlFrameTolerance: ordinarySlots.length > 0 && frameFailures.length === 0,
            meetsRowBaselineTolerance: rowBaselineFailures.length === 0,
            meetsGridEdgeTolerance: gridEdges.length > 0 && gridEdgeSpread.left <= 1 && gridEdgeSpread.right <= 1,
          };
        });
        const guideLines = await page.evaluate((evidence) => {
          document.querySelector('[data-field-alignment-guide-overlay]')?.remove();
          const overlay = document.createElement('div');
          overlay.dataset.fieldAlignmentGuideOverlay = 'true';
          overlay.setAttribute('aria-hidden', 'true');
          overlay.style.cssText = 'position:fixed;inset:0;z-index:2147483647;pointer-events:none;overflow:hidden';
          const lines = [];
          const addLine = (x, color, label) => {
            if (!Number.isFinite(x) || x < 0 || x > window.innerWidth) return;
            const line = document.createElement('i');
            line.style.cssText = `position:absolute;left:${x}px;top:0;bottom:0;width:1px;background:${color};opacity:.88`;
            line.title = label;
            overlay.appendChild(line);
            lines.push({ x, color, label });
          };
          const distinct = (values) => [...new Set(values.map((value) => Number(value.toFixed(1))))];
          distinct(evidence.fields.filter((field) => field.eligible && field.slotRect).flatMap((field) => [field.slotRect.left, field.slotRect.right]))
            .forEach((x) => addLine(x, '#1677ff', 'field-slot'));
          distinct(evidence.fields.filter((field) => field.eligible && field.frameRect).flatMap((field) => [field.frameRect.left, field.frameRect.right]))
            .forEach((x) => addLine(x, '#ef4444', 'visible-control-frame'));
          document.body.appendChild(overlay);
          return lines;
        }, fieldAlignmentEvidence);
        await page.screenshot({ path: path.join(outputDir, `${viewport.name}-${target.name.replace(/[^a-zA-Z0-9_-]/g, '_')}-alignment-guides.png`), fullPage: false });
        await page.evaluate(() => document.querySelector('[data-field-alignment-guide-overlay]')?.remove());
        fieldAlignmentEvidence.guideLines = guideLines;
        fieldAlignmentEvidence.pass = target.expectFieldAlignment !== true || (
          fieldAlignmentEvidence.meetsControlFrameTolerance
          && fieldAlignmentEvidence.meetsRowBaselineTolerance
          && fieldAlignmentEvidence.meetsGridEdgeTolerance
        );
      }
      if (target.exerciseBusinessConfigExperience === true) {
        const changeSetPanel = page.locator('[data-business-config-change-set="v1"]:visible');
        const initialChangeSetState = String(await changeSetPanel.getAttribute('data-change-set-state') || '');
        const initialChangeSetText = String(await changeSetPanel.textContent() || '').replace(/\s+/g, ' ').trim();
        const selectionPrompt = page.getByRole('heading', { name: '选择一个业务页面', exact: true });
        const selectionPromptVisible = await selectionPrompt.isVisible();
        const falseCurrentPageCount = await page.getByText('正在配置 当前页面', { exact: true }).count();
        const pageSearch = page.locator('.page-search input').first();
        const initialRowCount = await page.locator('.page-picker-panel .scan-row').count();
        await pageSearch.fill('__no_matching_business_page__');
        const emptyState = page.getByRole('heading', { name: '当前没有匹配的业务页面' });
        await emptyState.waitFor({ state: 'visible', timeout: 15000 });
        await page.getByRole('button', { name: '清除筛选' }).click();
        await page.waitForFunction(() => document.querySelectorAll('.page-picker-panel .scan-row').length > 0, undefined, { timeout: 15000 });
        const restoredRowCount = await page.locator('.page-picker-panel .scan-row').count();
        const emptyRecoveryVisible = await emptyState.count() === 0;
        const firstRow = page.locator('.page-picker-panel .scan-row').first();
        const selectedLabel = String(await firstRow.getAttribute('aria-label') || '');
        await firstRow.click();
        const selectedPanel = page.locator('[aria-label="已选页面配置"]:visible');
        await selectedPanel.waitFor({ state: 'visible', timeout: 45000 });
        const selectedText = String(await selectedPanel.textContent() || '').replace(/\s+/g, ' ').trim();
        const responsiveEvidence = await page.evaluate(() => {
          const selectors = ['.selected-page-overview', '.selected-page-overview-meta span', '.config-type-tabs .sc-btn', '[aria-label="已选页面配置"]'];
          const entries = selectors.flatMap((selector) => [...document.querySelectorAll(selector)]
            .filter((node) => node instanceof HTMLElement && node.offsetParent !== null)
            .map((node) => {
              const rect = node.getBoundingClientRect();
              return {
                selector,
                rect: [Math.round(rect.left), Math.round(rect.top), Math.round(rect.right), Math.round(rect.bottom)],
                withinViewport: rect.left >= -1 && rect.right <= window.innerWidth + 1,
                horizontallyClipped: node.scrollWidth > node.clientWidth + 1,
                height: Math.round(rect.height),
              };
            }));
          return {
            entries,
            pass: entries.length > 0
              && entries.every((entry) => entry.withinViewport && !entry.horizontallyClipped)
              && (window.innerWidth > 480
                || entries.filter((entry) => entry.selector === '.config-type-tabs .sc-btn').every((entry) => entry.height >= 44)),
          };
        });
        await page.screenshot({ path: path.join(outputDir, `${viewport.name}-${target.name.replace(/[^a-zA-Z0-9_-]/g, '_')}-selected.png`), fullPage: false });
        businessConfigExperienceEvidence = {
          initialChangeSetState,
          initialChangeSetText,
          selectionPromptVisible,
          falseCurrentPageCount,
          initialRowCount,
          emptyRecoveryVisible,
          restoredRowCount,
          selectedLabel,
          selectedText,
          responsiveEvidence,
          pass: initialChangeSetState === String(target.expectedChangeSetState || initialChangeSetState)
            && !(initialChangeSetState === 'empty' && initialChangeSetText.includes('状态：有未发布修改'))
            && selectionPromptVisible
            && falseCurrentPageCount === 0
            && initialRowCount > 0
            && restoredRowCount === initialRowCount
            && emptyRecoveryVisible
            && selectedLabel.length > 0
            && selectedText.includes('正在配置')
            && responsiveEvidence.pass,
        };
      }
      if (target.exerciseSafeReturn === true) {
        const errorState = page.locator('[data-semantic-component="ScErrorState"]:visible');
        const deniedUrl = new URL(page.url());
        const beforePath = deniedUrl.pathname;
        const authorityDeniedEvidence = target.expectAuthorityDenied === true ? {
          from: deniedUrl.searchParams.get('from') || '',
          reason: deniedUrl.searchParams.get('reason') || '',
        } : null;
        if (authorityDeniedEvidence) {
          authorityDeniedEvidence.pass = beforePath === '/access-denied'
            && authorityDeniedEvidence.from === target.path
            && authorityDeniedEvidence.reason === 'NAVIGATION_AUTHORITY_DENIED';
        }
        const errorText = String(await errorState.textContent() || '').replace(/\s+/g, ' ').trim();
        const returnAction = errorState.getByRole('button', { name: '返回安全页面' });
        const actionCount = await returnAction.count();
        const responsiveEvidence = await errorState.evaluate((root) => {
          const description = root.querySelector('p');
          const action = root.querySelector('button');
          const rootRect = root.getBoundingClientRect();
          const descriptionRect = description?.getBoundingClientRect();
          const actionRect = action?.getBoundingClientRect();
          return {
            rootRect: [Math.round(rootRect.left), Math.round(rootRect.top), Math.round(rootRect.right), Math.round(rootRect.bottom)],
            descriptionRect: descriptionRect ? [Math.round(descriptionRect.left), Math.round(descriptionRect.top), Math.round(descriptionRect.right), Math.round(descriptionRect.bottom)] : null,
            actionRect: actionRect ? [Math.round(actionRect.left), Math.round(actionRect.top), Math.round(actionRect.right), Math.round(actionRect.bottom)] : null,
            pass: Boolean(descriptionRect && actionRect)
              && rootRect.left >= -1 && rootRect.right <= window.innerWidth + 1
              && descriptionRect.left >= rootRect.left && descriptionRect.right <= rootRect.right + 1
              && actionRect.left >= rootRect.left && actionRect.right <= rootRect.right + 1
              && (window.innerWidth > 480 || (actionRect.top >= descriptionRect.bottom && actionRect.height >= 44)),
          };
        });
        await returnAction.click();
        await page.waitForURL((url) => url.pathname === '/', { timeout: 15000 });
        safeReturnEvidence = { beforePath, authorityDeniedEvidence, errorText, actionCount, responsiveEvidence, afterPath: new URL(page.url()).pathname };
        safeReturnEvidence.pass = errorText.length > 0
          && actionCount === 1
          && responsiveEvidence.pass
          && (authorityDeniedEvidence?.pass ?? true)
          && safeReturnEvidence.afterPath === '/';
      }
      let formValidationEvidence = null;
      if (target.exerciseFormValidation === true) {
        const form = page.locator('[data-product-page-mode="form"]:visible');
        const saveAction = page.locator('button[data-action-ref="form.save"]:visible').first();
        if (await form.count() !== 1 || await saveAction.count() !== 1) {
          throw new Error(`${target.name}: editable form validation entry is missing`);
        }
        const mutationCountBefore = report.mutationCount;
        await saveAction.click();
        const validationAlert = form.locator('[role="alert"]:visible').first();
        await validationAlert.waitFor({ state: 'visible', timeout: 15000 });
        const invalidControl = form.locator('[aria-invalid="true"]:visible').first();
        const invalidControlCount = await invalidControl.count();
        const invalidField = invalidControlCount === 1
          ? invalidControl.locator('xpath=ancestor::*[@data-field-name][1]')
          : null;
        const activeFieldName = await page.evaluate(() => document.activeElement?.closest('[data-field-name]')?.getAttribute('data-field-name') || '');
        const invalidFieldName = String(await invalidField?.getAttribute('data-field-name') || '');
        const alertText = String(await validationAlert.textContent() || '').replace(/\s+/g, ' ').trim();
        const fieldGeometry = await form.locator('[data-field-name]:visible').evaluateAll((nodes) => nodes
          .filter((node) => node.querySelector('input:not([disabled]), textarea:not([disabled]), button:not([disabled])'))
          .slice(0, 12)
          .map((node) => {
            const rect = node.getBoundingClientRect();
            const gridRect = node.closest('.template-form-section-grid')?.getBoundingClientRect();
            return {
              name: node.getAttribute('data-field-name') || '',
              left: Math.round(rect.left),
              right: Math.round(rect.right),
              width: Math.round(rect.width),
              gridWidth: Math.round(gridRect?.width || 0),
              gridWidthRatio: gridRect?.width ? Number((rect.width / gridRect.width).toFixed(3)) : 0,
            };
          }));
        const minimumPhoneFieldWidth = viewport.name === 'mobile'
          ? Math.max(180, viewport.width - 140)
          : 0;
        formValidationEvidence = {
          invalidFieldName,
          invalidControlCount,
          activeFieldName,
          alertText,
          mutationCountBefore,
          mutationCountAfter: report.mutationCount,
          fieldGeometry,
          minimumPhoneFieldWidth,
          pass: Boolean(invalidFieldName)
            && activeFieldName === invalidFieldName
            && alertText.length > 0
            && mutationCountBefore === report.mutationCount
            && (viewport.name !== 'mobile' || fieldGeometry.every((item) => (
              item.width >= minimumPhoneFieldWidth && item.gridWidthRatio >= 0.9
            ))),
        };
      }
      let detailCollectionEvidence = null;
      if (target.exerciseDetailCollection === true) {
        if (formValidationEvidence) {
          await page.goto(`${baseUrl}${target.path}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
          await page.locator('[data-semantic-component="ContractFormPage"][data-state="ok"]:visible').waitFor({ state: 'visible', timeout: 45000 });
          await waitForStableProductSurface(page);
        }
        const form = page.locator('[data-product-page-mode="form"]:visible');
        const addRow = form.locator('.o2m-create:visible').first();
        const saveAction = page.locator('button[data-action-ref="form.save"]:visible').first();
        if (await form.count() !== 1 || await addRow.count() !== 1 || await saveAction.count() !== 1) {
          throw new Error(`${target.name}: editable detail collection entry is missing ${JSON.stringify({
            url: page.url(),
            forms: await form.count(),
            addActions: await addRow.count(),
            saveActions: await saveAction.count(),
          })}`);
        }
        const mutationCountBefore = report.mutationCount;
        await addRow.click();
        const cellEditor = form.locator('[data-semantic-component="One2ManyCellEditor"]:visible').first();
        try {
          await cellEditor.waitFor({ state: 'visible', timeout: 15000 });
        } catch (error) {
          const detailState = await form.locator('.o2m-card:visible').evaluateAll((cards) => cards.map((card) => ({
            title: card.querySelector('.o2m-title')?.textContent?.trim() || '',
            count: card.querySelector('.o2m-count')?.textContent?.trim() || '',
            empty: card.querySelector('.o2m-empty')?.textContent?.replace(/\s+/g, ' ').trim() || '',
            desktopRows: card.querySelectorAll('.o2m-table-scroll tbody tr').length,
            mobileRows: card.querySelectorAll('[data-o2m-row]').length,
            editors: card.querySelectorAll('[data-semantic-component="One2ManyCellEditor"]').length,
            text: card.textContent?.replace(/\s+/g, ' ').trim().slice(0, 500) || '',
          })));
          throw new Error(`${target.name}: detail row did not expose shared cell editors ${JSON.stringify({ detailState, browserErrors: errors, mutationCount: report.mutationCount })}`, { cause: error });
        }
        const row = viewport.name === 'mobile'
          ? cellEditor.locator('xpath=ancestor::*[contains(concat(" ", normalize-space(@class), " "), " o2m-mobile-row ")][1]')
          : cellEditor.locator('xpath=ancestor::tr[1]');
        await row.waitFor({ state: 'visible', timeout: 15000 });
        const labels = viewport.name === 'mobile'
          ? await row.locator('.o2m-mobile-label:visible').allTextContents()
          : await form.locator('.o2m-table-scroll:visible thead th:visible').allTextContents();
        const readableLabels = labels.map((label) => label.replace(/\s+/g, ' ').replace(/\*$/, '').trim()).filter(Boolean);
        const disabledReasons = (await row.locator('.o2m-disabled-reason:visible').allTextContents())
          .map((label) => label.replace(/\s+/g, ' ').trim()).filter(Boolean);
        let detailRelationSearchEvidence = null;
        await saveAction.click();
        const cellError = row.locator('.o2m-cell-error[role="alert"]:visible').first();
        await cellError.waitFor({ state: 'visible', timeout: 15000 });
        const errorCell = cellError.locator('xpath=ancestor::*[@data-validation-target][1]');
        const errorTarget = String(await errorCell.getAttribute('data-validation-target') || '');
        const activeTarget = await page.evaluate(() => document.activeElement?.closest('[data-validation-target]')?.getAttribute('data-validation-target') || '');
        const invalidControlCount = await errorCell.locator('[aria-invalid="true"]:visible').count();
        const boundaryOwner = viewport.name === 'mobile' ? row : form.locator('.o2m-table-scroll:visible').first();
        const rowBoundary = await boundaryOwner.evaluate((node) => {
          const rect = node.getBoundingClientRect();
          const documentRoot = document.documentElement;
          return {
            left: Math.round(rect.left),
            right: Math.round(rect.right),
            viewportWidth: window.innerWidth,
            documentClientWidth: documentRoot.clientWidth,
            documentScrollWidth: documentRoot.scrollWidth,
            pass: rect.left >= -1
              && rect.right <= window.innerWidth + 1
              && documentRoot.scrollWidth <= documentRoot.clientWidth + 1,
          };
        });
        detailCollectionEvidence = {
          layout: viewport.name === 'mobile' ? 'mobile-card' : 'desktop-table',
          readableLabels,
          disabledReasons,
          errorTarget,
          activeTarget,
          validationFocusRequired: target.exerciseDetailRelationSearchRecovery !== true,
          invalidControlCount,
          detailRelationSearchEvidence,
          rowBoundary,
          mutationCountBefore,
          mutationCountAfter: report.mutationCount,
          pass: readableLabels.length > 2
            && disabledReasons.every((label) => !label.includes('契约'))
            && Boolean(errorTarget)
            && (target.exerciseDetailRelationSearchRecovery === true || activeTarget === errorTarget)
            && invalidControlCount > 0
            && (detailRelationSearchEvidence?.pass ?? true)
            && rowBoundary.pass
            && mutationCountBefore === report.mutationCount,
        };
        await page.screenshot({
          path: path.join(outputDir, `${viewport.name}-${target.name.replace(/[^a-zA-Z0-9_-]/g, '_')}-detail-validation.png`),
          fullPage: false,
        });
        if (target.exerciseDetailRelationSearchRecovery === true) {
          const relationEditors = form.locator('[data-semantic-component="One2ManyCellEditor"][data-validation-target$=":material_catalog_id"]:visible');
          let relationEditor = relationEditors.first();
          for (let index = 0; index < await relationEditors.count(); index += 1) {
            const candidate = relationEditors.nth(index);
            const candidateInput = candidate.locator('input:visible').first();
            const hitTarget = await candidateInput.evaluate((input) => {
              const rect = input.getBoundingClientRect();
              const hit = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
              return Boolean(hit && (hit === input || input.contains(hit) || hit.contains(input)));
            }).catch(() => false);
            if (hitTarget) {
              relationEditor = candidate;
              break;
            }
          }
          const relationSelect = relationEditor.locator('[data-semantic-component="ScSelect"]:visible').first();
          const relationInput = relationSelect.locator('input').first();
          const relationRow = viewport.name === 'mobile'
            ? relationEditor.locator('xpath=ancestor::*[contains(concat(" ", normalize-space(@class), " "), " o2m-mobile-row ")][1]')
            : relationEditor.locator('xpath=ancestor::tr[1]');
          if (await relationSelect.count() !== 1 || await relationInput.count() !== 1) {
            throw new Error(`${target.name}: editable detail relation selector is missing`);
          }
          const relationEditorInstances = {
            mounted: await form.locator('[data-semantic-component="One2ManyCellEditor"][data-validation-target$=":material_catalog_id"]').count(),
            visible: await relationEditors.count(),
          };
          let relationQueryCount = 0;
          const relationQueryEvents = [];
          const countRelationQuery = (request) => {
            if (request.method() !== 'POST') return;
            let body = {};
            try { body = JSON.parse(request.postData() || '{}'); } catch {}
            if (body.intent === 'api.data' && body?.params?.op === 'list' && body?.params?.model === 'sc.material.catalog') {
              relationQueryCount += 1;
              relationQueryEvents.push({
                kind: 'request',
                searchTerm: String(body?.params?.search_term || ''),
              });
            }
          };
          const countRelationResponse = async (response) => {
            const request = response.request();
            if (request.method() !== 'POST') return;
            let body = {};
            try { body = JSON.parse(request.postData() || '{}'); } catch {}
            if (body.intent === 'api.data' && body?.params?.op === 'list' && body?.params?.model === 'sc.material.catalog') {
              const payload = await response.json().catch(() => null);
              relationQueryEvents.push({
                kind: 'response',
                searchTerm: String(body?.params?.search_term || ''),
                status: response.status(),
                recordCount: Array.isArray(payload?.data?.records) ? payload.data.records.length : null,
                ok: payload?.ok ?? null,
              });
            }
          };
          page.on('request', countRelationQuery);
          page.on('response', countRelationResponse);
          const visibleDropdown = page.locator('.t-select__dropdown:visible').last();
          const visibleOptions = visibleDropdown.locator('[role="option"]:visible, .t-select-option:visible');
          const waitForMaterialCatalogQuery = (searchTerm) => page.waitForResponse((response) => {
            if (response.request().method() !== 'POST') return false;
            let body = {};
            try { body = JSON.parse(response.request().postData() || '{}'); } catch {}
            return body.intent === 'api.data'
              && body?.params?.op === 'list'
              && body?.params?.model === 'sc.material.catalog'
              && String(body?.params?.search_term || '') === searchTerm;
          }, { timeout: 15000 });
          const waitForVisibleRelationOptionCount = async (maximum) => {
            const selectHandle = await relationSelect.elementHandle();
            try {
              await page.waitForFunction(
                ({ select, limit }) => {
                  const count = Number(select?.getAttribute('data-option-count') ?? -1);
                  return count >= 0 && count <= limit;
                },
                { select: selectHandle, limit: maximum },
                { timeout: 15000 },
              );
            } catch (error) {
              const diagnostics = await form.locator('[data-semantic-component="One2ManyCellEditor"][data-validation-target$=":material_catalog_id"]')
                .evaluateAll((editors) => editors.map((editor) => ({
                  target: editor.getAttribute('data-validation-target'),
                  visible: editor instanceof HTMLElement && editor.offsetParent !== null,
                  diagnostic: editor.getAttribute('data-relation-query-diagnostic'),
                  optionCount: editor.querySelector('[data-semantic-component="ScSelect"]')?.getAttribute('data-option-count'),
                })));
              throw new Error(`${target.name}: active relation selector did not project at most ${maximum} options diagnostics=${JSON.stringify(diagnostics)}`, { cause: error });
            } finally {
              await selectHandle?.dispose();
            }
          };
          await relationInput.click();
          await visibleDropdown.waitFor({ state: 'visible', timeout: 15000 });
          const requireActiveRelationInput = async (phase) => {
            const ownsFocus = await relationInput.evaluate((input) => document.activeElement === input);
            if (!ownsFocus) {
              throw new Error(`${target.name}: visible relation selector did not retain its official search input during ${phase}`);
            }
            return relationInput;
          };
          let relationSearchInput = await requireActiveRelationInput('initial-open');
          await visibleOptions.first().waitFor({ state: 'visible', timeout: 15000 });
          const initialCount = await visibleOptions.count();
          const noMatchKeyword = '__shared_relation_no_match__';
          const noMatchResponse = waitForMaterialCatalogQuery(noMatchKeyword);
          await relationSearchInput.fill('S');
          await relationSearchInput.fill(noMatchKeyword);
          await noMatchResponse;
          await waitForVisibleRelationOptionCount(0);
          const noResultCount = await visibleOptions.count();
          const noResultControlOptionCount = Number(await relationSelect.getAttribute('data-option-count') || -1);
          const noResultText = String(await visibleDropdown.textContent().catch(() => '') || '').replace(/\s+/g, ' ').trim();
          const clearResponse = waitForMaterialCatalogQuery('');
          await relationSearchInput.fill('');
          await clearResponse;
          try {
            await visibleOptions.first().waitFor({ state: 'visible', timeout: 15000 });
          } catch (error) {
            const recoveryDiagnostic = {
              inputValue: await relationInput.inputValue(),
              relationQueryCount,
              relationQueryEvents,
              visibleDropdownCount: await page.locator('.t-select__dropdown:visible').count(),
              visibleOptionCount: await visibleOptions.count(),
              dropdownText: String(await visibleDropdown.textContent().catch(() => '') || '').replace(/\s+/g, ' ').trim(),
              loading: await relationSelect.locator('.t-loading:visible, [aria-busy="true"]:visible').count(),
              failureText: String(await relationSelect.locator('[data-relation-query-state="error"]:visible').textContent().catch(() => '') || '').replace(/\s+/g, ' ').trim(),
            };
            await page.screenshot({
              path: path.join(outputDir, `${viewport.name}-${target.name.replace(/[^a-zA-Z0-9_-]/g, '_')}-relation-recovery-failure.png`),
              fullPage: false,
            });
            fs.writeFileSync(
              path.join(outputDir, `${viewport.name}-${target.name.replace(/[^a-zA-Z0-9_-]/g, '_')}-relation-recovery-failure.json`),
              `${JSON.stringify(recoveryDiagnostic, null, 2)}\n`,
              'utf8',
            );
            throw new Error(`${target.name}: relation clear recovery failed: ${JSON.stringify(recoveryDiagnostic)}`, { cause: error });
          }
          const restoredCount = await visibleOptions.count();
          const selectedLabel = String(await visibleOptions.first().textContent() || '').replace(/\s+/g, ' ').trim();
          await visibleOptions.first().click();
          await visibleDropdown.waitFor({ state: 'hidden', timeout: 15000 });
          const selectedDisplay = await relationInput.inputValue();
          const selectedDisplays = await relationRow.locator('[data-validation-target$=":material_catalog_id"] input:visible')
            .evaluateAll((inputs) => inputs.map((input) => input.value));
          await relationInput.click();
          await visibleDropdown.waitFor({ state: 'visible', timeout: 15000 });
          relationSearchInput = await requireActiveRelationInput('selected-reopen');
          const selectedOptionBeforeSearch = String(await visibleDropdown.locator('[aria-selected="true"]:visible').first().textContent().catch(() => '') || '').replace(/\s+/g, ' ').trim();
          const selectedNoMatchResponse = waitForMaterialCatalogQuery(noMatchKeyword);
          await relationSearchInput.fill(noMatchKeyword);
          await selectedNoMatchResponse;
          await waitForVisibleRelationOptionCount(1);
          const selectedNoResultCount = await visibleOptions.count();
          const selectedNoResultLabels = (await visibleOptions.allTextContents()).map((value) => value.replace(/\s+/g, ' ').trim());
          await page.keyboard.press('Escape');
          await visibleDropdown.waitFor({ state: 'hidden', timeout: 15000 });
          const selectedDisplayAfterSearch = await relationInput.inputValue();
          const selectedDisplaysAfterSearch = await relationRow.locator('[data-validation-target$=":material_catalog_id"] input:visible')
            .evaluateAll((inputs) => inputs.map((input) => input.value));
          await relationInput.click();
          await visibleDropdown.waitFor({ state: 'visible', timeout: 15000 });
          await visibleOptions.first().waitFor({ state: 'visible', timeout: 15000 });
          const reopenedCount = await visibleOptions.count();
          const selectedOptionAfterReopen = String(await visibleDropdown.locator('[aria-selected="true"]:visible').first().textContent().catch(() => '') || '').replace(/\s+/g, ' ').trim();
          await page.keyboard.press('Escape');
          await visibleDropdown.waitFor({ state: 'hidden', timeout: 15000 });
          const noteInput = relationRow.locator('[data-validation-target$=":note"] input:visible').first();
          const relationQueriesBeforeNote = relationQueryCount;
          const unrelatedRelationRequest = page.waitForRequest((request) => {
            if (request.method() !== 'POST') return false;
            let body = {};
            try { body = JSON.parse(request.postData() || '{}'); } catch {}
            return body.intent === 'api.data'
              && body?.params?.op === 'list'
              && body?.params?.model === 'sc.material.catalog';
          }, { timeout: 750 }).then(() => true).catch(() => false);
          if (await noteInput.count() === 1) await noteInput.fill('未提交的关系查询验证');
          const noteTriggeredRelationQuery = await unrelatedRelationRequest;
          const relationQueriesAfterNote = relationQueryCount;

          let failureInjected = false;
          const failureRoutePattern = '**/api/v1/**';
          const failureRouteHandler = async (route) => {
            const request = route.request();
            let body = {};
            try { body = JSON.parse(request.postData() || '{}'); } catch {}
            if (!failureInjected
              && body.intent === 'api.data'
              && body?.params?.op === 'list'
              && body?.params?.model === 'sc.material.catalog') {
              failureInjected = true;
              expectedReadFailureResponses += 1;
              expectedReadFailureConsoleErrors += 1;
              await route.fulfill({
                status: 503,
                contentType: 'application/json',
                body: JSON.stringify({ ok: false, error: { code: 'TEMPORARY_UNAVAILABLE', message: 'injected relation read failure' } }),
              });
              return;
            }
            await route.continue();
          };
          await page.route(failureRoutePattern, failureRouteHandler);
          await relationInput.click();
          await visibleDropdown.waitFor({ state: 'visible', timeout: 15000 });
          const failureSearchInput = await requireActiveRelationInput('failure-injection-open');
          await failureSearchInput.fill('__shared_relation_failure__');
          const failureState = page.locator('[data-relation-query-state="error"]:visible').filter({ hasText: '可选内容加载失败' }).first();
          try {
            await failureState.waitFor({ state: 'visible', timeout: 15000 });
          } catch (error) {
            const failureDiagnostic = {
              inputValue: await relationInput.inputValue(),
              failureInjected,
              relationQueryCount,
              relationQueryEvents,
              loading: await relationSelect.locator('.t-loading:visible, [aria-busy="true"]:visible').count(),
              visibleOptionCount: await visibleOptions.count(),
            };
            await page.screenshot({
              path: path.join(outputDir, `${viewport.name}-${target.name.replace(/[^a-zA-Z0-9_-]/g, '_')}-relation-failure-missing.png`),
              fullPage: false,
            });
            fs.writeFileSync(
              path.join(outputDir, `${viewport.name}-${target.name.replace(/[^a-zA-Z0-9_-]/g, '_')}-relation-failure-missing.json`),
              `${JSON.stringify(failureDiagnostic, null, 2)}\n`,
              'utf8',
            );
            throw new Error(`${target.name}: relation failure state missing: ${JSON.stringify(failureDiagnostic)}`, { cause: error });
          }
          const failureText = String(await failureState.textContent() || '').replace(/\s+/g, ' ').trim();
          const failureOwnerTarget = await failureState.evaluate((node) => (
            node.closest('[data-semantic-component="One2ManyCellEditor"]')?.getAttribute('data-validation-target') || ''
          ));
          await page.screenshot({
            path: path.join(outputDir, `${viewport.name}-${target.name.replace(/[^a-zA-Z0-9_-]/g, '_')}-relation-failure.png`),
            fullPage: false,
          });
          const failureRecoveryResponse = waitForMaterialCatalogQuery('__shared_relation_failure__');
          await failureState.getByRole('button', { name: '重试', exact: true }).click();
          await failureRecoveryResponse;
          await failureState.waitFor({ state: 'hidden', timeout: 15000 });
          const failureRecovered = failureInjected && await failureState.count() === 0;
          await page.unroute(failureRoutePattern, failureRouteHandler);
          await page.keyboard.press('Escape');
          page.off('request', countRelationQuery);
          page.off('response', countRelationResponse);
          detailRelationSearchEvidence = {
            initialCount,
            noResultCount,
            noResultControlOptionCount,
            noResultText,
            restoredCount,
            selectedLabel,
            selectedDisplay,
            selectedDisplays,
            selectedOptionBeforeSearch,
            selectedNoResultCount,
            selectedNoResultLabels,
            selectedDisplayAfterSearch,
            selectedDisplaysAfterSearch,
            reopenedCount,
            selectedOptionAfterReopen,
              relationQueriesBeforeNote,
              relationQueriesAfterNote,
              noteTriggeredRelationQuery,
            failureInjected,
            failureText,
            failureOwnerTarget,
            failureRecovered,
            relationEditorInstances,
            relationQueryEvents,
            pass: initialCount > 0
              && (noResultCount === 0 || noResultText.includes('未找到匹配'))
              && restoredCount > 0
              && Boolean(selectedLabel)
              && (selectedDisplay === selectedLabel || selectedDisplays.includes(selectedLabel) || selectedOptionBeforeSearch === selectedLabel)
              && selectedNoResultCount <= 1
              && (selectedNoResultCount === 0 || selectedNoResultLabels.includes(selectedLabel))
              && (selectedDisplayAfterSearch === selectedLabel || selectedDisplaysAfterSearch.includes(selectedLabel) || selectedOptionAfterReopen === selectedLabel)
              && reopenedCount > 0
              && relationQueryEvents.filter((event) => event.kind === 'request' && event.searchTerm === noMatchKeyword).length === 2
              && !noteTriggeredRelationQuery
              && relationQueriesAfterNote === relationQueriesBeforeNote
              && failureText.includes('加载失败')
              && failureOwnerTarget.endsWith(':material_catalog_id')
              && failureRecovered,
          };
          detailCollectionEvidence.detailRelationSearchEvidence = detailRelationSearchEvidence;
          detailCollectionEvidence.pass = detailCollectionEvidence.pass && detailRelationSearchEvidence.pass;
        }
        const removeRow = row.locator('.o2m-row-remove:visible, button[aria-label^="移除"]:visible').first();
        if (await removeRow.count() !== 1) throw new Error(`${target.name}: temporary detail row cannot be removed`);
        await removeRow.click();
      }
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
          const card = node.querySelector('.collection-mobile-record-row__open')?.closest('button');
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
              role: fact.getAttribute('data-fact-role') || '',
              visibility: fact.getAttribute('data-fact-visibility') || '',
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
            && (!row.facts.some((fact) => fact.role === 'money')
              || row.facts.some((fact) => fact.role === 'money' && fact.visibility === 'primary'))
            && (row.selectionWidth === 0 || (row.selectionWidth >= 44 && row.selectionHeight >= 44))),
        };
      }
      let factDisclosureEvidence = null;
      if (target.exerciseFactDisclosure === true && (target.factDisclosureMobileOnly !== true || viewport.name === 'mobile')) {
        const recordId = String(target.recordId || '').trim();
        const ownerSelector = recordId ? `[data-work-item-key][data-record-id="${recordId}"]` : '[data-work-item-key]';
        const owner = page.locator(`${ownerSelector}:visible, [data-semantic-component="CollectionMobileRecordRow"]:visible`).first();
        const disclosure = owner.locator('[data-disclosure-trigger]').filter({ visible: true }).first();
        if (await disclosure.count() !== 1) throw new Error(`${target.name}: progressive fact disclosure is missing`);
        const rawIdentity = String(await owner.locator('h3').first().textContent() || '').replace(/\s+/g, ' ').trim();
        const before = await disclosure.getAttribute('aria-expanded');
        if (viewport.name === 'mobile') await disclosure.tap();
        else {
          await disclosure.focus();
          await disclosure.press('Enter');
        }
        await page.waitForFunction((node) => node?.getAttribute('aria-expanded') === 'true', await disclosure.elementHandle(), { timeout: 5000 });
        const expanded = await disclosure.getAttribute('aria-expanded');
        const fullIdentity = String(await owner.locator('[data-work-item-full-identity]').textContent() || '').replace(/\s+/g, ' ').trim();
        if (viewport.name === 'mobile') await disclosure.tap();
        else {
          await disclosure.focus();
          await disclosure.press('Space');
        }
        await page.waitForFunction((node) => node?.getAttribute('aria-expanded') === 'false', await disclosure.elementHandle(), { timeout: 5000 });
        const after = await disclosure.getAttribute('aria-expanded');
        const expectedIdentityText = String(target.expectedIdentityText || '').trim();
        factDisclosureEvidence = {
          method: viewport.name === 'mobile' ? 'touch' : 'keyboard',
          rawIdentity,
          fullIdentity,
          before,
          expanded,
          after,
          pass: Boolean(rawIdentity)
            && fullIdentity === rawIdentity
            && (!expectedIdentityText || fullIdentity.includes(expectedIdentityText))
            && before === 'false'
            && expanded === 'true'
            && after === 'false',
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
        const collectionState = String(await page.locator('[data-semantic-component="ActionView"]').getAttribute('data-collection-state') || '');
        collectionNavigationEvidence = {
          footerCount,
          paginationMode,
          collectionState,
          columnHeaderCount,
          invalidColumnRoots,
          missingDragLabels,
          missingResizeLabels,
          groupingToolbarCount,
          groupPageControlsCount,
          pass: footerCount === 1
            && ['count', 'grouped', 'paged'].includes(paginationMode)
            && (collectionState === 'empty' || columnHeaderCount > 0)
            && invalidColumnRoots === 0
            && missingDragLabels === 0
            && missingResizeLabels === 0,
        };
      }
      let recordEntryEvidence = null;
      if (target.exerciseRecordEntry === true) {
        const recordId = String(target.recordId || '').trim();
        if (!recordId) throw new Error(`${target.name}: record entry requires recordId`);
        const recordOwner = page.locator(`[data-record-key="${recordId}"]:visible`);
        if (await recordOwner.count() !== 1) throw new Error(`${target.name}: expected exactly one visible record ${recordId}`);
        const opener = recordOwner.locator('.cell-primary-link, .collection-mobile-record-row__open-action, [data-semantic-action="open-record"]');
        if (await opener.count() !== 1) throw new Error(`${target.name}: expected exactly one record opener for ${recordId}`);
        const beforeUrl = page.url();
        const captureReturnScroll = target.captureReturnScroll === true
          && (target.returnScrollMobileOnly !== true || viewport.name === 'mobile');
        const scrollBefore = captureReturnScroll
          ? await recordOwner.evaluate((node) => {
            node.scrollIntoView({ block: 'center', inline: 'nearest' });
            const candidates = [];
            let current = node.parentElement;
            while (current) {
              if (current.scrollHeight > current.clientHeight + 1) candidates.push(current);
              current = current.parentElement;
            }
            const scrolling = document.scrollingElement;
            if (scrolling && scrolling.scrollHeight > scrolling.clientHeight + 1) candidates.push(scrolling);
            const owner = candidates[0];
            if (!(owner instanceof HTMLElement)) return { available: false, scrollTop: 0, maxScrollTop: 0 };
            const maxScrollTop = Math.max(0, owner.scrollHeight - owner.clientHeight);
            return { available: true, scrollTop: Math.round(owner.scrollTop), maxScrollTop: Math.round(maxScrollTop) };
          })
          : null;
        const detailContractResponse = page.waitForResponse(isContractV2Response, { timeout: 45000 });
        await opener.click(captureReturnScroll ? { force: true } : undefined);
        await page.waitForURL((url) => url.href !== beforeUrl, { timeout: 15000 });
        const response = await detailContractResponse;
        const payload = await response.json();
        const widgetTypes = [];
        const visit = (value) => {
          if (Array.isArray(value)) return value.forEach(visit);
          if (!value || typeof value !== 'object') return;
          if (typeof value.widgetType === 'string') widgetTypes.push(value.widgetType);
          Object.values(value).forEach(visit);
        };
        visit(payload.layoutContract?.containerTree || []);
        await waitForStableProductSurface(page);
        await page.locator('[data-semantic-component="ContractFormPage"][data-state="ok"]').waitFor({ state: 'visible', timeout: 45000 });
        recordEntryEvidence = {
          recordId,
          beforeUrl,
          firstUrl: page.url(),
          responseStatus: response.status(),
          pageInfo: payload.pageInfo || null,
          widgetTypes: [...new Set(widgetTypes)].sort(),
          visibleError: await page.locator('[role="alert"]:visible, .error-state:visible, .form-error:visible').allTextContents(),
        };
        if (target.exerciseRecordReturn === true && (target.recordReturnDesktopOnly !== true || viewport.name === 'desktop')) {
          const preservedKeys = Array.isArray(target.preservedQueryKeys) ? target.preservedQueryKeys.map(String) : ['search', 'order', 'list_offset'];
          const before = new URL(beforeUrl);
          const detailRecordId = String(await page.locator('[data-semantic-component="ContractFormPage"]').getAttribute('data-form-record') || '');
          const returnAction = page.locator('[data-form-secondary-action="return-list"]:visible');
          if (await returnAction.count() === 1) {
            await returnAction.click();
          } else if (viewport.name === 'mobile') {
            const mobileActions = page.locator('.form-header-mobile-actions:visible');
            if (await mobileActions.count() !== 1) throw new Error(`${target.name}: mobile return action owner is missing`);
            const mobileActionTrigger = page.locator('[data-semantic-component="ScButton"][aria-label="打开更多页面操作"]:visible');
            if (await mobileActionTrigger.count() !== 1) throw new Error(`${target.name}: mobile return action trigger is missing`);
            await mobileActionTrigger.click();
            const mobileItems = page.locator('.t-dropdown__item:visible');
            await mobileItems.first().waitFor({ state: 'visible', timeout: 15000 });
            const mobileReturn = mobileItems.filter({ hasText: '返回' });
            if (await mobileReturn.count() !== 1) throw new Error(`${target.name}: expected exactly one mobile return-to-list action`);
            await mobileReturn.click();
          } else {
            throw new Error(`${target.name}: expected exactly one return-to-list action`);
          }
          await page.waitForURL((url) => url.pathname === before.pathname, { timeout: 15000 });
          await waitForStableProductSurface(page);
          const afterUrl = page.url();
          const after = new URL(afterUrl);
          const scrollAfter = captureReturnScroll
            ? await page.locator(`[data-record-key="${recordId}"]:visible`).evaluate((node) => {
              const candidates = [];
              let current = node.parentElement;
              while (current) {
                if (current.scrollHeight > current.clientHeight + 1) candidates.push(current);
                current = current.parentElement;
              }
              const scrolling = document.scrollingElement;
              if (scrolling && scrolling.scrollHeight > scrolling.clientHeight + 1) candidates.push(scrolling);
              const owner = candidates[0];
              return owner instanceof HTMLElement
                ? { available: true, scrollTop: Math.round(owner.scrollTop), maxScrollTop: Math.round(owner.scrollHeight - owner.clientHeight) }
                : { available: false, scrollTop: 0, maxScrollTop: 0 };
            })
            : null;
          const preservedQuery = Object.fromEntries(preservedKeys.map((key) => [key, {
            before: before.searchParams.get(key) || '',
            after: after.searchParams.get(key) || '',
          }]));
          recordEntryEvidence.returnEvidence = {
            detailRecordId,
            afterUrl,
            preservedQuery,
            scrollBefore,
            scrollAfter,
            pass: detailRecordId === recordId
              && preservedKeys.every((key) => (before.searchParams.get(key) || '') === (after.searchParams.get(key) || ''))
              && (!captureReturnScroll || (
                scrollBefore?.available === true
                && scrollAfter?.available === true
                && scrollBefore.scrollTop > 0
                && Math.abs(scrollAfter.scrollTop - scrollBefore.scrollTop) <= 2
              )),
          };
        }
      }
      let collectionSearchEvidence = null;
      if (target.exerciseCollectionSearchCycle === true && (target.collectionSearchDesktopOnly !== true || viewport.name === 'desktop')) {
        const queryBar = page.locator('[data-semantic-component="ProductListHeader"]:visible, [data-semantic-component="CollectionActionToolbar"]:visible').first();
        const searchForm = queryBar.locator('form[role="search"]');
        const searchOwner = await searchForm.count() === 1 ? searchForm : queryBar;
        const searchInput = searchOwner.locator('input[type="search"]');
        if (await queryBar.count() !== 1 || await searchInput.count() !== 1) throw new Error(`${target.name}: collection search control is missing`);
        const footer = page.locator('[data-semantic-component="CollectionPaginationFooter"]:visible').last();
        const totalBefore = String(await footer.textContent() || '').replace(/\s+/g, ' ').trim();
        const noMatchQuery = String(target.noMatchQuery || '__codex_no_matching_record__');
        await searchInput.fill(noMatchQuery);
        await searchOwner.getByRole('button', { name: /^搜索$/ }).click();
        await waitForStableProductSurface(page);
        const emptySurface = page.locator('.list-empty-surface:visible');
        await emptySurface.waitFor({ state: 'visible', timeout: 15000 });
        const noResultUrl = page.url();
        const noResultText = String(await emptySurface.textContent() || '').replace(/\s+/g, ' ').trim();
        const emptyClearAction = emptySurface.getByRole('button', { name: /^清除查询条件$/ });
        const toolbarClearAction = searchOwner.getByRole('button', { name: /^清除$/ });
        const clearAction = await emptyClearAction.count() === 1 ? emptyClearAction : toolbarClearAction;
        if (await clearAction.count() !== 1) throw new Error(`${target.name}: collection clear-search action is missing`);
        const clearActionLabel = String(await clearAction.textContent() || '').replace(/\s+/g, ' ').trim();
        await clearAction.click();
        await waitForStableProductSurface(page);
        await page.locator('[data-record-key]:visible').first().waitFor({ state: 'visible', timeout: 15000 });
        const restoredFooter = page.locator('[data-semantic-component="CollectionPaginationFooter"]:visible').last();
        const totalAfter = String(await restoredFooter.textContent() || '').replace(/\s+/g, ' ').trim();
        const recordTotal = (text) => Number(text.match(/共\s*(\d+)\s*条/)?.[1] || 0);
        collectionSearchEvidence = {
          totalBefore,
          recordTotalBefore: recordTotal(totalBefore),
          noMatchQuery,
          noResultUrl,
          noResultText,
          clearActionLabel,
          totalAfter,
          recordTotalAfter: recordTotal(totalAfter),
          finalUrl: page.url(),
          finalSearchValue: await searchInput.inputValue(),
          pass: Boolean(totalBefore)
            && noResultText.length > 0
            && ['清除查询条件', '清除'].includes(clearActionLabel)
            && recordTotal(totalBefore) > 0
            && recordTotal(totalAfter) === recordTotal(totalBefore)
            && await searchInput.inputValue() === '',
        };
      }
      const taskDensityEvidence = target.captureTaskDensity === true
        ? await page.evaluate((viewportName) => {
          const selector = '[data-product-page-pattern="task-form"]';
          const root = document.querySelector(selector);
          if (!(root instanceof HTMLElement)) return { present: false, regions: [], nodes: [] };
          const describe = (node) => {
            const rect = node.getBoundingClientRect();
            const style = getComputedStyle(node);
            return {
              tag: node.tagName,
              className: typeof node.className === 'string' ? node.className : '',
              region: node.getAttribute('data-floorplan-region') || '',
              text: node.textContent?.replace(/\s+/g, ' ').trim().slice(0, 120) || '',
              rect: [Math.round(rect.left), Math.round(rect.top), Math.round(rect.width), Math.round(rect.height)],
              display: style.display,
              gridTemplateColumns: style.gridTemplateColumns,
              gridAutoRows: style.gridAutoRows,
              alignContent: style.alignContent,
              rowGap: style.rowGap,
            };
          };
          const summary = root.querySelector('.object-task-page__summary-grid');
          const summaryNodes = summary instanceof HTMLElement
            ? [...summary.children].filter((node) => node instanceof HTMLElement).map(describe)
            : [];
          const summaryRows = [...new Set(summaryNodes.map((node) => node.rect[1]))];
          const summaryColumns = summary instanceof HTMLElement
            ? getComputedStyle(summary).gridTemplateColumns.split(' ').filter(Boolean).length
            : 0;
          const expectedColumns = viewportName === 'mobile' ? 2 : 4;
          const maxSummaryItemHeight = viewportName === 'mobile' ? 150 : 120;
          return {
            present: true,
            root: describe(root),
            summary: {
              columns: summaryColumns,
              itemCount: summaryNodes.length,
              rowCount: summaryRows.length,
              height: summary instanceof HTMLElement ? Math.round(summary.getBoundingClientRect().height) : 0,
              maxItemHeight: Math.max(0, ...summaryNodes.map((node) => node.rect[3])),
              pass: summaryNodes.length === 0 || (
                summaryColumns === expectedColumns
                && summaryRows.length === Math.ceil(summaryNodes.length / expectedColumns)
                && Math.max(0, ...summaryNodes.map((node) => node.rect[3])) <= maxSummaryItemHeight
              ),
            },
            decisionInput: (() => {
              const region = root.querySelector('[data-floorplan-region="decision-input"]');
              const money = region?.querySelector('[data-field-type="monetary"]');
              return {
                present: region instanceof HTMLElement,
                monetaryFieldPresent: money instanceof HTMLElement,
                rect: region instanceof HTMLElement ? describe(region).rect : [],
              };
            })(),
            regions: [...root.querySelectorAll('[data-floorplan-region]')].map(describe),
            nodes: [...root.querySelectorAll('.canonical-form-node')].map(describe),
          };
        }, viewport.name)
        : null;
      const monetaryExpressionEvidence = target.captureMonetaryExpression === true
        ? await page.evaluate((configuration) => {
          const recordId = String(configuration.recordId || '').trim();
          const fieldName = String(configuration.monetaryFieldName || '').trim();
          const selectors = [
            recordId ? `[data-work-item-key][data-record-id="${recordId}"]` : '',
            recordId ? `[data-role-home] [data-record-id="${recordId}"]` : '',
            recordId ? `[data-record-key="${recordId}"]` : '',
            recordId ? `[data-semantic-component="ContractFormPage"][data-form-record="${recordId}"]` : '',
          ].filter(Boolean);
          const roots = selectors.flatMap((selector) => [...document.querySelectorAll(selector)])
            .filter((node) => node instanceof HTMLElement && node.offsetParent !== null);
          const root = roots[0];
          if (!(root instanceof HTMLElement)) return { present: false, roots: 0, displayValues: [], fieldCount: 0, input: null, pass: false };
          const fieldSelector = fieldName ? `[data-field-name="${fieldName}"]` : '[data-field-type="monetary"]';
          const fields = [...root.querySelectorAll(fieldSelector)].filter((node) => node instanceof HTMLElement && node.offsetParent !== null);
          const displayValues = [...root.querySelectorAll('[data-money-display], [data-fact-role="money"] b')]
            .filter((node) => node instanceof HTMLElement && node.offsetParent !== null)
            .map((node) => node.getAttribute('data-money-display') || node.textContent?.replace(/\s+/g, ' ').trim() || '')
            .filter(Boolean);
          const input = fields[0]?.querySelector('input[type="number"]');
          const expectedDisplay = String(configuration.expectedMoneyDisplay || '').trim();
          const expectedInput = String(configuration.expectedMoneyInput || '').trim();
          return {
            present: true,
            roots: roots.length,
            text: root.textContent?.replace(/\s+/g, ' ').trim() || '',
            displayValues,
            fieldCount: fields.length,
            input: input instanceof HTMLInputElement ? { value: input.value, step: input.step } : null,
            pass: (!expectedDisplay || displayValues.includes(expectedDisplay) || (root.textContent || '').includes(expectedDisplay))
              && (!fieldName || fields.length === 1)
              && (!expectedInput || (input instanceof HTMLInputElement && input.value === expectedInput && input.step === '0.01')),
          };
        }, {
          recordId: target.recordId,
          monetaryFieldName: target.monetaryFieldName,
          expectedMoneyDisplay: target.expectedMoneyDisplay,
          expectedMoneyInput: target.expectedMoneyInput,
        })
        : null;
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
      const notebookTabEvidence = await page.locator('[data-semantic-component="ScTabs"]').evaluateAll((nodes) => nodes.map((node) => {
        const rect = node.getBoundingClientRect();
        return {
          rect: [Math.round(rect.left), Math.round(rect.top), Math.round(rect.right), Math.round(rect.bottom)],
          text: String(node.textContent || '').replace(/\s+/g, ' ').trim(),
          declaredLabels: [...node.querySelectorAll('[data-section-tab]')].map((item) => ({
            label: item.getAttribute('data-section-tab') || '',
            rect: (() => { const itemRect = item.getBoundingClientRect(); return [Math.round(itemRect.left), Math.round(itemRect.top), Math.round(itemRect.right), Math.round(itemRect.bottom)]; })(),
            color: getComputedStyle(item).color,
            display: getComputedStyle(item).display,
            font: getComputedStyle(item).font,
            fontSize: getComputedStyle(item).fontSize,
            visibility: getComputedStyle(item).visibility,
            parentClass: item.parentElement?.className || '',
            parentRect: (() => { const parentRect = item.parentElement?.getBoundingClientRect(); return parentRect ? [Math.round(parentRect.left), Math.round(parentRect.top), Math.round(parentRect.right), Math.round(parentRect.bottom)] : null; })(),
          })),
        };
      }));
      report.routes.push({ name: target.name, path: target.path, viewport: viewport.name, finalUrl: initialFinalUrl, expectedPageHeaders: target.expectedPageHeaders ?? null, expectedPrimaryActions: target.expectedPrimaryActions ?? null, expectedPresentationMode: target.expectedPresentationMode ?? null, expectedNativeStructureCount: target.expectedNativeStructureCount ?? null, expectedNativeNotebookPageCount: target.expectedNativeNotebookPageCount ?? null, expectedLoadedSelectorEvidence, contractH1Nodes, contractSelections, contractAggregates, contractSummaryItems, listAggregates, nativeActionPresentationEvidence, hierarchicalWorkspaceEvidence, formValidationEvidence, detailCollectionEvidence, relationSearchDialogEvidence, collectionSummaryEvidence, collectionMobileRecordEvidence, collectionKanbanEvidence, collectionSelectionEvidence, collectionAggregateEvidence, collectionGroupHeaderEvidence, mobileOverflowEvidence, dialogLifecycleEvidence, collectionToolbarEvidence, collectionNavigationEvidence, recordEntryEvidence, collectionSearchEvidence, readFailureEvidence, businessConfigExperienceEvidence, businessConfigReadFailureEvidence, officialComponentBehaviorEvidence, officialAlertOperationEvidence, safeReturnEvidence, formStructureEvidence, fieldAlignmentEvidence, factDisclosureEvidence, taskDensityEvidence, monetaryExpressionEvidence, sidebarScrollEvidence, verticalLineEvidence, notebookTabEvidence, ...result });
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
  const configuredTarget = routes.find((target) => target.name === item.name);
  const finalPath = item.finalUrl ? new URL(item.finalUrl).pathname : '';
  if (item.path && finalPath === '/access-denied' && configuredTarget?.allowAccessDenied !== true) {
    failures.push({ name: item.name, expectedAuthorizedRoute: item.path, finalUrl: item.finalUrl });
  }
  if (item.path && item.primitiveDriverEvidence && !item.primitiveDriverEvidence.pass) {
    failures.push({ name: item.name, primitiveDriverEvidence: item.primitiveDriverEvidence });
  }
  if (item.path && item.overlayResidueEvidence && !item.overlayResidueEvidence.pass) {
    failures.push({ name: item.name, overlayResidueEvidence: item.overlayResidueEvidence });
  }
  if (item.path && configuredTarget?.captureFormStructure === true && !item.formStructureEvidence?.pass) {
    failures.push({ name: item.name, formStructureEvidence: item.formStructureEvidence || null });
  }
  if (item.path && configuredTarget?.captureFieldAlignment === true && !item.fieldAlignmentEvidence?.pass) {
    failures.push({ name: item.name, fieldAlignmentEvidence: item.fieldAlignmentEvidence || null });
  }
  if (item.path && item.homePresentationEvidence && !item.homePresentationEvidence.pass) {
    failures.push({ name: item.name, homePresentationEvidence: item.homePresentationEvidence });
  }
  if (item.path && item.navigationHorizontalEvidence && !item.navigationHorizontalEvidence.pass) {
    failures.push({ name: item.name, navigationHorizontalEvidence: item.navigationHorizontalEvidence });
  }
  if (item.path && item.viewport === 'desktop' && item.shellAdapterEvidence && routes.find((target) => target.name === item.name)?.exerciseShellAdapterProjection === true && !item.shellAdapterEvidence.pass) {
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
  const expectedAnalysisView = routes.find((target) => target.name === item.name)?.expectedAnalysisView;
  if (item.path && expectedAnalysisView && (!item.analysisEvidence?.pass || item.analysisEvidence.view !== expectedAnalysisView)) {
    failures.push({ name: item.name, expectedAnalysisView, analysisEvidence: item.analysisEvidence || null });
  }
  if (item.path && routes.find((target) => target.name === item.name)?.expectedActivityReady === true && !item.activityEvidence?.pass) {
    failures.push({ name: item.name, expectedActivityReady: true, activityEvidence: item.activityEvidence || null });
  }
  if (item.path && routes.find((target) => target.name === item.name)?.expectedRelationTagsReady === true && !item.relationTagEvidence?.pass) {
    failures.push({ name: item.name, expectedRelationTagsReady: true, relationTagEvidence: item.relationTagEvidence || null });
  }
  if (item.path && configuredTarget?.expectedLoadedSelector) {
    if (!item.expectedLoadedSelectorEvidence?.pass) {
      failures.push({ name: item.name, expectedLoadedSelector: configuredTarget.expectedLoadedSelector, expectedLoadedSelectorEvidence: item.expectedLoadedSelectorEvidence || null });
    }
  }
  if (item.path && configuredTarget?.expectedWorkRecordId) {
    const expectedRecordId = String(configuredTarget.expectedWorkRecordId);
    const evidence = item.workItemEvidence || {};
    const observedRecordIds = [
      ...(evidence.cards || []).map((entry) => entry.recordId),
      ...(evidence.homeItems || []).map((entry) => entry.recordId),
      evidence.detailRecordId,
    ].filter(Boolean);
    if (!observedRecordIds.includes(expectedRecordId)) {
      failures.push({ name: item.name, expectedWorkRecordId: expectedRecordId, observedRecordIds });
    }
  }
  if (item.path && configuredTarget?.captureWorkItemDensity === true && item.viewport === 'desktop') {
    const evidence = item.workItemEvidence || {};
    const cards = evidence.cards || [];
    const compactAndComplete = Number(evidence.fullyVisibleCardCount || 0) >= 3
      && cards.slice(0, 3).every((entry) => entry.recordId && entry.state && entry.primaryFactCount > 0
        && entry.actionLabels.includes('打开详情')
        && (entry.supplementaryFactCount === 0 || entry.disclosureCount > 0));
    if (!compactAndComplete) failures.push({ name: item.name, workItemDensityEvidence: evidence });
  }
  if (item.sidebarScrollEvidence && !item.sidebarScrollEvidence.pass) failures.push({ name: item.name, sidebarScrollEvidence: item.sidebarScrollEvidence });
  if (item.taskDensityEvidence && (!item.taskDensityEvidence.present || !item.taskDensityEvidence.summary?.pass)) failures.push({ name: item.name, taskDensityEvidence: item.taskDensityEvidence });
}
for (const item of report.routes) {
  if (item.mobileOverflowEvidence && !item.mobileOverflowEvidence.pass) failures.push({ name: item.name, mobileOverflowEvidence: item.mobileOverflowEvidence });
  if (item.collectionSelectionEvidence && !item.collectionSelectionEvidence.pass) failures.push({ name: item.name, collectionSelectionEvidence: item.collectionSelectionEvidence });
  if (item.collectionSummaryEvidence && !item.collectionSummaryEvidence.pass) failures.push({ name: item.name, collectionSummaryEvidence: item.collectionSummaryEvidence });
  if (item.collectionMobileRecordEvidence && !item.collectionMobileRecordEvidence.pass) failures.push({ name: item.name, collectionMobileRecordEvidence: item.collectionMobileRecordEvidence });
  if (item.collectionKanbanEvidence && !item.collectionKanbanEvidence.pass) failures.push({ name: item.name, collectionKanbanEvidence: item.collectionKanbanEvidence });
  if (item.relationSearchDialogEvidence && !item.relationSearchDialogEvidence.pass) failures.push({ name: item.name, relationSearchDialogEvidence: item.relationSearchDialogEvidence });
  if (item.formValidationEvidence && !item.formValidationEvidence.pass) failures.push({ name: item.name, formValidationEvidence: item.formValidationEvidence });
  if (item.detailCollectionEvidence && !item.detailCollectionEvidence.pass) failures.push({ name: item.name, detailCollectionEvidence: item.detailCollectionEvidence });
  if (item.collectionAggregateEvidence && !item.collectionAggregateEvidence.pass) failures.push({ name: item.name, collectionAggregateEvidence: item.collectionAggregateEvidence });
  if (item.collectionGroupHeaderEvidence && !item.collectionGroupHeaderEvidence.pass) failures.push({ name: item.name, collectionGroupHeaderEvidence: item.collectionGroupHeaderEvidence });
  if (item.dialogLifecycleEvidence && !item.dialogLifecycleEvidence.pass) failures.push({ name: item.name, dialogLifecycleEvidence: item.dialogLifecycleEvidence });
  if (item.collectionToolbarEvidence && !item.collectionToolbarEvidence.pass) failures.push({ name: item.name, collectionToolbarEvidence: item.collectionToolbarEvidence });
  if (item.collectionNavigationEvidence && !item.collectionNavigationEvidence.pass) failures.push({ name: item.name, collectionNavigationEvidence: item.collectionNavigationEvidence });
  if (item.recordEntryEvidence?.returnEvidence && !item.recordEntryEvidence.returnEvidence.pass) failures.push({ name: item.name, recordReturnEvidence: item.recordEntryEvidence.returnEvidence });
  if (item.collectionSearchEvidence && !item.collectionSearchEvidence.pass) failures.push({ name: item.name, collectionSearchEvidence: item.collectionSearchEvidence });
  if (item.readFailureEvidence && !item.readFailureEvidence.pass) failures.push({ name: item.name, readFailureEvidence: item.readFailureEvidence });
  if (item.businessConfigExperienceEvidence && !item.businessConfigExperienceEvidence.pass) failures.push({ name: item.name, businessConfigExperienceEvidence: item.businessConfigExperienceEvidence });
  if (item.businessConfigReadFailureEvidence && !item.businessConfigReadFailureEvidence.pass) failures.push({ name: item.name, businessConfigReadFailureEvidence: item.businessConfigReadFailureEvidence });
  if (item.officialComponentBehaviorEvidence && !item.officialComponentBehaviorEvidence.pass) failures.push({ name: item.name, officialComponentBehaviorEvidence: item.officialComponentBehaviorEvidence });
  if (item.officialAlertOperationEvidence && !item.officialAlertOperationEvidence.pass) failures.push({ name: item.name, officialAlertOperationEvidence: item.officialAlertOperationEvidence });
  if (item.safeReturnEvidence && !item.safeReturnEvidence.pass) failures.push({ name: item.name, safeReturnEvidence: item.safeReturnEvidence });
  if (item.topbarActionEvidence && !item.topbarActionEvidence.pass) failures.push({ name: item.name, topbarActionEvidence: item.topbarActionEvidence });
  if (item.factDisclosureEvidence && !item.factDisclosureEvidence.pass) failures.push({ name: item.name, factDisclosureEvidence: item.factDisclosureEvidence });
  if (item.monetaryExpressionEvidence && !item.monetaryExpressionEvidence.pass) failures.push({ name: item.name, monetaryExpressionEvidence: item.monetaryExpressionEvidence });
  if (item.hierarchicalWorkspaceEvidence && !item.hierarchicalWorkspaceEvidence.pass) failures.push({ name: item.name, hierarchicalWorkspaceEvidence: item.hierarchicalWorkspaceEvidence });
}
for (const viewport of ['desktop', 'mobile']) {
  const groups = [...new Set(routes.map((target) => String(target.equivalentGroup || '')).filter(Boolean))];
  for (const group of groups) {
    const names = routes.filter((target) => target.equivalentGroup === group).map((target) => target.name);
    const rows = report.routes.filter((item) => item.viewport === viewport && names.includes(item.name));
    const geometry = rows.map((item) => item.shellGeometry);
    const equivalent = rows.length === names.length
      && geometry.every((item) => item?.minimal === true)
      && new Set(geometry.map((item) => item?.topbarHeight)).size === 1
      && new Set(geometry.map((item) => item?.contentStart)).size === 1;
    if (!equivalent) failures.push({ equivalentGroup: group, viewport, names, geometry });
  }
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
