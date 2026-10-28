#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';
import { resolveAcceptanceEnvironment } from './lib/frontend_acceptance_environment.mjs';

const acceptance = resolveAcceptanceEnvironment({ tool: 'geometry-scroll-audit', operation: 'readonly' });
const targets = JSON.parse(process.env.PRODUCT_PAGE_HEADER_TARGETS_JSON || '[]');
const output = path.resolve(process.env.PRODUCT_PAGE_HEADER_OUTPUT || 'artifacts/frontend-product-page-header/summary.json');

function check(value, message) { if (!value) throw new Error(message); }
function requestBody(request) { try { return request.postDataJSON() || {}; } catch { return {}; } }
function isMutation(request) {
  if (request.method() !== 'POST') return false;
  const body = requestBody(request);
  const intent = String(body.intent || body.params?.intent || '');
  if (['execute_button', 'api.data.create', 'api.data.write', 'api.data.unlink'].includes(intent)) return true;
  return intent === 'api.data' && ['create', 'write', 'unlink'].includes(String(body.params?.op || body.params?.payload?.op || ''));
}

check(Array.isArray(targets) && targets.length > 0 && targets.length <= 3, 'one to three governed targets are required');
check(acceptance.login && acceptance.password, 'governed acceptance credentials are required');
fs.mkdirSync(path.dirname(output), { recursive: true });

const browser = await launchChromium({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();
page.setDefaultTimeout(30_000);
const evidence = {
  schema: 'frontend_product_page_header_browser.v1',
  passed: false,
  provenance: {
    profile: acceptance.profile,
    base_url: acceptance.baseUrl,
    database: acceptance.database,
    login: acceptance.login,
    expected_sha: acceptance.provenance.expectedSha,
  },
  console: [],
  pageerror: [],
  http: [],
  mutations: [],
  targets: [],
};
page.on('console', (message) => { if (message.type() === 'error' && !/favicon|ResizeObserver/i.test(message.text())) evidence.console.push(message.text().replace(/token=[^\s'"]+/g, 'token=[redacted]')); });
page.on('pageerror', (error) => evidence.pageerror.push(error.message));
page.on('response', async (response) => {
  if (requestBody(response.request()).intent === 'ui.contract.v2' && targets.some(t => t.stageRequirements)) {
    const body = await response.json().catch(() => ({}));
    const data = body.data || {};
    console.log('[presentation] stage contract ' + JSON.stringify({keys:Object.keys(data),stage:data.dataContract?.mainData?.lifecycle_state,rules:(data.actionContract?.actionRuleList || []).filter(r => r.actionKey === 'action_view_stage_requirements' || r.button?.name === 'action_view_stage_requirements')}));
  }
});
page.on('response', (response) => { if (response.status() >= 500) evidence.http.push({ status: response.status(), url: response.url() }); });
await page.route('**/*', async (route) => {
  if (isMutation(route.request())) {
    evidence.mutations.push({ url: route.request().url(), body: requestBody(route.request()) });
    await route.abort('blockedbyclient');
    return;
  }
  await route.continue();
});

console.log('[presentation] login');
await page.goto(`${acceptance.baseUrl}/login`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
await page.locator('#login-username, input[autocomplete="username"]').first().fill(acceptance.login);
await page.locator('#login-password, input[autocomplete="current-password"]').first().fill(acceptance.password);
const database = page.locator('input').nth(2);
if (await database.isEnabled().catch(() => false)) await database.fill(acceptance.database);
await page.getByRole('button', { name: /^登录$/ }).click();
await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45_000 });

console.log("[presentation] login completed");
for (const target of targets) {
  console.log(`[presentation] target=${target.key}`);
  if (target.entryObjectModel) {
    check(
      typeof target.entryObjectModel === 'string'
        && /^[a-z][a-z0-9_.]+$/.test(target.entryObjectModel),
      'entry object model is invalid',
    );
    await page.goto(`${acceptance.baseUrl}/`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
    const objectEntry = page.locator(
      `[data-login-home-block="my_objects"] article[data-object-model="${target.entryObjectModel}"]`,
    ).first();
    await objectEntry.waitFor({ state: 'visible', timeout: 45_000 });
    await objectEntry.getByRole('button', { name: '打开', exact: true }).click();
    const recordRoute = new RegExp(
      `/r/${target.entryObjectModel.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}/\\d+`,
    );
    await page.waitForURL(
      (url) => recordRoute.test(url.pathname),
      { timeout: 45_000 },
    );
  } else {
    check(typeof target.route === 'string' && target.route.startsWith('/'), 'target route is invalid');
    await page.goto(`${acceptance.baseUrl}${target.route}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  }
  const header = page.locator('[data-product-page-header]');
  await header.waitFor({ state: 'visible', timeout: 45_000 });
  await page.waitForFunction(() => !/正在载入|正在加载|正在初始化/.test(document.body.innerText || ''), null, { timeout: 45_000 });
  if (target.stageRequirements) {
    console.log("[presentation] stage button check");
    const before = page.url();
    const buttons = await page.getByRole('button', { name: '查看阶段要求', exact: true }).count();
    console.log(`[presentation] stage visible buttons=${buttons}`);
    await page.screenshot({ path: path.join(path.dirname(output), 'before-stage.png'), fullPage: false });
    if (!buttons) {
      const source = await page.locator('[data-semantic-component]').count();
      console.log(`[presentation] no visible entry; direct read observation only; nodes=${source}`);
    }
    check(buttons <= 1, 'stage navigation is ambiguous');
    const [response] = await Promise.all([
      page.waitForResponse(r => requestBody(r.request()).intent === 'project.stage.requirements.read'),
      buttons ? page.getByRole('button', { name: '查看阶段要求', exact: true }).click() : page.goto(`${acceptance.baseUrl}/project-stage-requirements/${target.recordId}`),
    ]);
    const body = await response.json();
    check(response.status() === 200 && body.ok !== false, `stage read failed HTTP ${response.status()}`);
    const data = body.data;
    check(data?.project?.id === target.recordId, 'wrong project in stage response');
    const surface = page.locator('[data-semantic-component="ProjectStageRequirementsView"]');
    await surface.getByRole('heading', { name: data.title, exact: true }).waitFor();
    check((await surface.innerText()).includes(data.project.name), 'project identity missing');
    check((await surface.innerText()).includes(data.stage.label), 'stage identity missing');
    check(await surface.locator('li').count() === data.items.length, 'not all requirements rendered');
    for (const item of data.items) check((await surface.innerText()).includes(item.title), 'requirement missing');
    if (!data.items.length) check((await surface.innerText()).includes(data.labels.empty), 'empty state missing');
    await page.screenshot({ path: path.join(path.dirname(output), 'stage-requirements.png'), fullPage: false });
    await surface.getByRole('button', { name: data.labels.back, exact: true }).click();
    await page.waitForURL(buttons ? before : `${acceptance.baseUrl}${data.return_path}`);
    await header.waitFor({ state: 'visible' });
    evidence.targets.push({ key: target.key, source: 'real_isolated_runtime', buttonClicked: buttons === 1, project: data.project,
      stage: data.stage, itemCount: data.items.length, httpStatus: response.status(), returned: true });
    // Existing fixture C belongs to a different company. This is a real server
    // denial; negative transport cases below are explicitly simulated, not data.
    const deniedResponse = page.waitForResponse(r => requestBody(r.request()).intent === 'project.stage.requirements.read');
    await page.goto(`${acceptance.baseUrl}/project-stage-requirements/${target.deniedProjectId}`);
    check((await deniedResponse).status() === 403, 'cross-company read must remain denied');
    await page.getByRole('heading', { name: '无权访问', exact: true }).waitFor();
    evidence.targets.push({ key: 'denied', source: 'real_isolated_runtime', httpStatus: 403 });
    for (const message of evidence.console.splice(0)) check(/403.*Forbidden|Failed to load resource.*403/.test(message), `unexpected console error: ${message}`);
    for (const fault of ['empty', 'network', 'server']) {
      const intercept = async route => {
        if (requestBody(route.request()).intent !== 'project.stage.requirements.read') return route.fallback();
        if (fault === 'network') return route.abort('failed');
        return route.fulfill({ status: fault === 'server' ? 500 : 200, contentType: 'application/json',
          body: JSON.stringify(fault === 'server' ? {ok:false,error:{code:'INTERNAL_ERROR',message:'internal diagnostic sentinel'}}
            : {...body,data:{...data,items:[]}}) });
      };
      await page.route('**/api/v1/intent', intercept);
      await page.goto(`${acceptance.baseUrl}/project-stage-requirements/${target.recordId}`);
      if (fault === 'empty') await page.getByText(data.labels.empty, {exact:true}).waitFor();
      else await page.getByRole('heading', {name:fault === 'network' ? '网络连接异常' : '服务暂时不可用',exact:true}).waitFor();
      check(!(await page.locator('body').innerText()).includes('internal diagnostic sentinel'), 'internal diagnostics leaked');
      evidence.targets.push({key:fault,source:'simulated_transport_only',databaseWrites:false});
      for (const message of evidence.console.splice(0)) check(/Failed to load resource|net::ERR_FAILED/.test(message), `unexpected console error: ${message}`);
      for (const failed of evidence.http.splice(0)) check(fault === 'server' && failed.status === 500 && failed.url.endsWith('/api/v1/intent'), 'unexpected server failure');
      await page.unroute('**/api/v1/intent', intercept);
    }
    continue;
  }
  if (target.activateTab) {
    const tab = page.locator('.native-tab').filter({ hasText: String(target.activateTab) });
    check(await tab.count() === 1, `${target.key}: native tab ${target.activateTab} is not unique`);
    await tab.click();
  }
  if (target.openAuditTimeline) {
    const auditTimeline = page.locator('[data-professional-audit-timeline]');
    check(await auditTimeline.count() === 1, `${target.key}: professional audit timeline is not unique`);
    if (!await auditTimeline.evaluate((node) => node.hasAttribute('open'))) await auditTimeline.locator('summary').click();
  }
  const snapshot = await page.evaluate(() => {
    const visible = (node) => node instanceof HTMLElement && node.getClientRects().length > 0 && getComputedStyle(node).visibility !== 'hidden';
    const headerNode = document.querySelector('[data-product-page-header]');
    const patternNode = document.querySelector('[data-product-page-pattern]');
    const primary = [...document.querySelectorAll('[data-product-primary-action]')].filter(visible);
    const enabledPrimary = primary.filter((node) => !(node instanceof HTMLButtonElement) || !node.disabled);
    const save = [...document.querySelectorAll('[data-action-ref="form.save"], [data-action-method="save"], [data-action-method="write"]')].filter(visible);
    const componentNodes = [...document.querySelectorAll('[data-component-key]')].filter(visible);
    const unresolvedComponents = componentNodes.filter((node) => {
      const readiness = node.getAttribute('data-component-readiness');
      return !node.getAttribute('data-component-key') || !['ready', 'readable_fallback'].includes(readiness || '');
    });
    const professionalBaseFields = [...document.querySelectorAll('[data-professional-field-family="base"]')];
    const visibleProfessionalBaseFields = professionalBaseFields.filter(visible);
    const professionalBusinessValues = [...document.querySelectorAll('[data-professional-field-family="business-value"]')];
    const visibleProfessionalBusinessValues = professionalBusinessValues.filter(visible);
    const professionalRelations = [...document.querySelectorAll('[data-professional-field-family="relation"]')];
    const visibleProfessionalRelations = professionalRelations.filter(visible);
    const professionalDetailCollections = [...document.querySelectorAll('[data-professional-field-family="detail-collection"]')];
    const visibleProfessionalDetailCollections = professionalDetailCollections.filter(visible);
    const workflowStatusbars = [...document.querySelectorAll('[data-professional-workflow-component="statusbar"]')].filter(visible);
    const workflowActionBars = [...document.querySelectorAll('[data-professional-workflow-component="action-bar"]')].filter(visible);
    const professionalAuditTimelines = [...document.querySelectorAll('[data-professional-audit-timeline]')].filter(visible);
    const professionalAuditEvents = [...document.querySelectorAll('[data-professional-audit-event]')].filter(visible);
    const professionalBaseContextMismatches = professionalBaseFields.filter((node) => (
      node.getAttribute('data-presentation-mode') !== headerNode?.getAttribute('data-presentation-mode')
      || node.getAttribute('data-render-profile') !== headerNode?.getAttribute('data-render-profile')
    ));
    return {
      url: location.href,
      headerCount: document.querySelectorAll('[data-product-page-header]').length,
      patternCount: document.querySelectorAll('[data-product-page-pattern]').length,
      pagePattern: patternNode?.getAttribute('data-product-page-pattern') || '',
      h1Count: document.querySelectorAll('h1').length,
      presentationMode: headerNode?.getAttribute('data-presentation-mode') || '',
      renderProfile: headerNode?.getAttribute('data-render-profile') || '',
      dirtyState: headerNode?.getAttribute('data-dirty-state') || '',
      primaryCount: primary.length,
      enabledPrimaryCount: enabledPrimary.length,
      saveCount: save.length,
      editTransitionCount: [...document.querySelectorAll('[data-form-mode-action="edit"]')].filter(visible).length,
      bodyActionBarCount: [...document.querySelectorAll('.sc-form-driver-host [data-canonical-action-bar]')].filter(visible).length,
      componentCount: componentNodes.length,
      unresolvedComponentCount: unresolvedComponents.length,
      professionalBaseFieldCount: professionalBaseFields.length,
      visibleProfessionalBaseFieldCount: visibleProfessionalBaseFields.length,
      professionalBusinessValueCount: professionalBusinessValues.length,
      visibleProfessionalBusinessValueCount: visibleProfessionalBusinessValues.length,
      professionalBusinessValueKinds: [...new Set(visibleProfessionalBusinessValues.map((node) => node.getAttribute('data-business-value-kind') || ''))].filter(Boolean),
      professionalRelationCount: professionalRelations.length,
      visibleProfessionalRelationCount: visibleProfessionalRelations.length,
      professionalRelationKinds: [...new Set(visibleProfessionalRelations.map((node) => node.getAttribute('data-relation-kind') || ''))].filter(Boolean),
      professionalRelationCreateModes: [...new Set(visibleProfessionalRelations.map((node) => node.getAttribute('data-relation-create-mode') || ''))].filter(Boolean),
      professionalDetailCollectionCount: professionalDetailCollections.length,
      visibleProfessionalDetailCollectionCount: visibleProfessionalDetailCollections.length,
      professionalDetailCollectionRows: visibleProfessionalDetailCollections.map((node) => Number(node.getAttribute('data-row-count') || 0)),
      professionalDetailCollectionColumns: visibleProfessionalDetailCollections.map((node) => Number(node.getAttribute('data-column-count') || 0)),
      workflowStatusbarCount: workflowStatusbars.length,
      workflowActionBarCount: workflowActionBars.length,
      workflowActionCount: workflowActionBars.map((node) => Number(node.getAttribute('data-workflow-action-count') || 0)),
      workflowDisabledCount: workflowActionBars.map((node) => Number(node.getAttribute('data-workflow-disabled-count') || 0)),
      professionalAuditTimelineCount: professionalAuditTimelines.length,
      professionalAuditEventCount: professionalAuditEvents.length,
      professionalBaseContextMismatchCount: professionalBaseContextMismatches.length,
      overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    };
  });
  check(snapshot.headerCount === 1, `${target.key}: page header count ${snapshot.headerCount}`);
  check(snapshot.patternCount === 1, `${target.key}: page pattern count ${snapshot.patternCount}`);
  check(snapshot.pagePattern === target.pagePattern, `${target.key}: page pattern ${snapshot.pagePattern}`);
  check(snapshot.h1Count === 1, `${target.key}: h1 count ${snapshot.h1Count}`);
  check(snapshot.presentationMode === target.presentationMode, `${target.key}: presentation mode ${snapshot.presentationMode}`);
  check(snapshot.renderProfile === target.renderProfile, `${target.key}: render profile ${snapshot.renderProfile}`);
  check(snapshot.primaryCount <= 1, `${target.key}: multiple primary actions`);
  check(snapshot.bodyActionBarCount === 0, `${target.key}: parallel body action bar remains`);
  check(snapshot.componentCount > 0, `${target.key}: no registered component evidence`);
  check(snapshot.unresolvedComponentCount === 0, `${target.key}: unresolved component evidence remains`);
  if (target.requireProfessionalBaseField !== false) {
    check(snapshot.professionalBaseFieldCount > 0, `${target.key}: professional base field family is absent`);
    check(snapshot.visibleProfessionalBaseFieldCount > 0, `${target.key}: professional base field family is not visible`);
  }
  if (target.requireBusinessValue) {
    check(snapshot.visibleProfessionalBusinessValueCount > 0, `${target.key}: professional business-value family is not visible`);
  }
  if (target.requireRelation) {
    check(snapshot.visibleProfessionalRelationCount > 0, `${target.key}: professional relation family is not visible`);
  }
  if (target.requireDetailCollection) {
    check(snapshot.visibleProfessionalDetailCollectionCount > 0, `${target.key}: professional detail collection family is not visible`);
  }
  if (target.requireWorkflowStatusbar) {
    check(snapshot.workflowStatusbarCount === 1, `${target.key}: workflow statusbar count ${snapshot.workflowStatusbarCount}`);
  }
  if (target.requireWorkflowActionBar) {
    check(snapshot.workflowActionBarCount === 1, `${target.key}: workflow action bar count ${snapshot.workflowActionBarCount}`);
  }
  if (target.requireAuditTimeline) {
    check(snapshot.professionalAuditTimelineCount === 1, `${target.key}: professional audit timeline count ${snapshot.professionalAuditTimelineCount}`);
  }
  if (target.requireAuditEvent) {
    check(snapshot.professionalAuditEventCount > 0, `${target.key}: professional audit event is absent`);
  }
  check(snapshot.professionalBaseContextMismatchCount === 0, `${target.key}: professional base field context mismatch`);
  if (target.renderProfile === 'edit') {
    check(snapshot.saveCount === 1 && snapshot.primaryCount === 1 && snapshot.enabledPrimaryCount === 1, `${target.key}: edit save action is not uniquely available`);
    check(snapshot.editTransitionCount === 0, `${target.key}: edit transition button remains`);
  }
  if (target.renderProfile === 'readonly') check(snapshot.saveCount === 0, `${target.key}: readonly exposes save`);
  await page.setViewportSize({ width: 390, height: 844 });
  const mobileOverflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  check(!mobileOverflow, `${target.key}: 390px overflow`);
  await page.setViewportSize({ width: 1440, height: 900 });
  evidence.targets.push({ key: target.key, ...snapshot, mobileOverflow });
}

check(evidence.console.length === 0, `console errors: ${JSON.stringify(evidence.console)}`);
check(evidence.pageerror.length === 0, `page errors: ${JSON.stringify(evidence.pageerror)}`);
check(evidence.http.length === 0, `http 5xx: ${JSON.stringify(evidence.http)}`);
check(evidence.mutations.length === 0, `business mutations: ${JSON.stringify(evidence.mutations)}`);
evidence.passed = true;
fs.writeFileSync(output, `${JSON.stringify({ ...evidence, mutationCount: 0 }, null, 2)}\n`);
await browser.close();
console.log(`[frontend_product_page_header_browser] PASS targets=${evidence.targets.length} mutations=0 errors=0`);
