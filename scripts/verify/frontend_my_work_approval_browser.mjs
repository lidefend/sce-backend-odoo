#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';
import { applyReleasedNavigationTarget, captureReleasedNavigation } from './released_navigation_target.mjs';

const BASE_URL = process.env.FRONTEND_URL || 'http://127.0.0.1:5175';
const DB_NAME = process.env.DB_NAME || 'sc_frontend_acceptance';
const PASSWORD = process.env.SC_ACCEPTANCE_FIXTURE_PASSWORD || '';
const OUTPUT_DIR = process.env.ARTIFACTS_DIR || 'artifacts/frontend-my-work-approval';
const TARGETS = JSON.parse(process.env.FRONTEND_MY_WORK_APPROVAL_TARGETS_JSON || '{}');
const EXPECTED_SHA = String(process.env.SC_ACCEPTANCE_EXPECTED_SHA || '').trim();
const PREVIEW_BASE_SHA = String(process.env.SC_ACCEPTANCE_PREVIEW_BASE_SHA || '').trim();
const PREVIEW_ENTRY = String(process.env.SC_ACCEPTANCE_PREVIEW_ENTRY || '').trim();
const PREVIEW_ENTRY_SHA256 = String(process.env.SC_ACCEPTANCE_PREVIEW_ENTRY_SHA256 || '').trim();
const SCRIPT_SHA = String(process.env.SC_ACCEPTANCE_TEST_SCRIPT_SHA || '').trim();
const APPROVAL_REVIEWER_LOGIN = String(process.env.FRONTEND_APPROVAL_REVIEWER_LOGIN || 'fixture_role_finance_reviewer').trim();
const MY_WORK_MENU_XMLID = 'smart_construction_core.menu_sc_my_work';
fs.mkdirSync(OUTPUT_DIR, { recursive: true });

function check(value, message) { if (!value) throw new Error(message); }
function route(target) { return `/r/${target.model}/${target.record_id}?action_id=${target.action_id}&menu_id=${target.menu_id}`; }
function canonicalForm(page, target, recordId = target.record_id) {
  return page.locator(`[data-product-page-mode="form"][data-state="ok"][data-form-model="${target.model}"][data-form-record="${recordId}"]`);
}

async function waitForCanonicalForm(page, target, recordId = target.record_id) {
  const form = canonicalForm(page, target, recordId);
  await form.waitFor({ timeout: 45000 });
  return form;
}

async function waitForWorkflowState(page, state) {
  const statusbar = page.locator(`[data-professional-workflow-component="statusbar"][data-workflow-current="${state}"]`);
  await statusbar.waitFor({ timeout: 45000 });
  return statusbar;
}

function captureRuntime(page) {
  const state = { consoleErrors: [], pageErrors: [], responses: [] };
  page.on('console', (message) => {
    if (message.type() === 'error' && !/favicon|ResizeObserver/i.test(message.text())) state.consoleErrors.push(message.text());
  });
  page.on('pageerror', (error) => state.pageErrors.push(error.message));
  page.on('response', async (response) => {
    if (!response.url().includes('/api/v1/')) return;
    let intent = ''; let body = ''; let request = {};
    try { request = JSON.parse(response.request().postData() || '{}'); intent = request?.intent || ''; } catch {}
    if (response.status() < 400 && !['execute_button', 'payment.request.submit', 'payment.request.execute', 'payment.request.approve', 'payment.request.reject'].includes(intent)) return;
    try { body = (await response.text()).slice(0, 24000); } catch {}
    state.responses.push({ intent, status: response.status(), url: response.url(), request, body });
  });
  return state;
}

function findNavigationNodeByMenuXmlid(nodes, menuXmlid) {
  const pending = Array.isArray(nodes) ? [...nodes] : [];
  while (pending.length) {
    const node = pending.shift();
    if (!node || typeof node !== 'object') continue;
    const meta = node.meta && typeof node.meta === 'object' ? node.meta : {};
    if (String(node.menu_xmlid || node.xmlid || meta.menu_xmlid || '') === menuXmlid) return node;
    if (Array.isArray(node.children)) pending.push(...node.children);
  }
  return null;
}

async function resolveDesignedMyWorkScene(page, releasedNavigation) {
  const started = Date.now();
  while (Date.now() - started < 45_000) {
    const node = findNavigationNodeByMenuXmlid(releasedNavigation.nav(), MY_WORK_MENU_XMLID);
    if (node) {
      const meta = node.meta && typeof node.meta === 'object' ? node.meta : {};
      const route = String(node.route || meta.route || '').trim();
      const sceneKey = String(node.scene_key || node.sceneKey || meta.scene_key || '').trim();
      const contentKind = String(node.content_kind || meta.content_kind || '').trim();
      check(sceneKey === 'my_work.workspace', `My Work scene key invalid: ${sceneKey || 'missing'}`);
      check(contentKind === 'designed_scene', `My Work content kind invalid: ${contentKind || 'missing'}`);
      check(new URL(route, BASE_URL).pathname === '/s/my_work.workspace', `My Work route is not scenarioized: ${route || 'missing'}`);
      return { route, scene_key: sceneKey, content_kind: contentKind };
    }
    await page.waitForTimeout(50);
  }
  throw new Error(`released navigation designed scene target missing: ${MY_WORK_MENU_XMLID}`);
}

function resetRuntime(state) { state.consoleErrors.length = 0; state.pageErrors.length = 0; state.responses.length = 0; }
function assertClean(state, step, allowed = []) {
  const unexpected = state.responses.filter((row) => row.status >= 400 && !allowed.includes(row.status));
  check(!state.consoleErrors.length, `${step}: console errors ${state.consoleErrors.join(' | ')}`);
  check(!state.pageErrors.length, `${step}: page errors ${state.pageErrors.join(' | ')}`);
  check(!unexpected.length, `${step}: unexpected HTTP ${JSON.stringify(unexpected.map(({ intent, status }) => ({ intent, status })))}`);
}

async function login(page, user) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const username = page.locator('#login-username, input[autocomplete="username"]').first();
  const password = page.locator('#login-password, input[autocomplete="current-password"]').first();
  await username.fill(user);
  await password.fill(PASSWORD);
  const database = page.locator('#login-db, input[name="db"], input[autocomplete="organization"]').first();
  if (await database.count() && await database.isEnabled().catch(() => false)) await database.fill(DB_NAME);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45000 });
  await page.locator('.layout-shell').waitFor({ timeout: 45000 });
}

async function logout(page) {
  const logoutButton = page.getByRole('button', { name: '退出登录' });
  if (!(await logoutButton.isVisible().catch(() => false))) {
    const menuButton = page.getByRole('button', { name: '菜单', exact: true });
    if (await menuButton.isVisible().catch(() => false)) await menuButton.click();
  }
  await logoutButton.click();
  await page.waitForURL((url) => url.pathname.includes('/login'), { timeout: 30000 });
}

async function openMyWork(page, sceneTarget) {
  check(sceneTarget?.content_kind === 'designed_scene', 'My Work must be delivered as a designed scene');
  await page.goto(`${BASE_URL}${sceneTarget.route}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  check(new URL(page.url()).pathname === '/s/my_work.workspace', `My Work left its scene route: ${page.url()}`);
  await page.locator('[data-semantic-component="MyWorkView"][data-my-work-renderer="product-workspace"]').waitFor({ timeout: 45000 });
  check(await page.locator('[data-semantic-component="ActionView"]').count() === 0, 'designed My Work scene rendered through ActionView');
  await page.locator('.product-work').waitFor({ timeout: 45000 });
  check((await page.title()).startsWith('我的工作 - '), `My Work document title invalid: ${await page.title()}`);
}

async function selectCompany(page, companyName) {
  const expectedCompanyId = Number(companyName === 'FE Company A' ? TARGETS.companies?.a : companyName === 'FE Company B' ? TARGETS.companies?.b : 0);
  check(expectedCompanyId > 0, `missing governed company identity for ${companyName}`);
  const contextIndicator = page.locator('[data-semantic-component="WorkspaceContextIndicator"]:visible');
  await contextIndicator.waitFor({ timeout: 30000 });
  check(await contextIndicator.count() === 1, 'workspace context indicator identity is not unique');
  const trigger = contextIndicator.getByRole('button', { name: /^切换公司：/ });
  await trigger.waitFor({ timeout: 30000 });
  check(await trigger.count() === 1, 'company switch trigger identity is not unique');
  await trigger.click();
  const panel = page.locator('.workspace-scope-panel').filter({
    has: page.getByRole('heading', { name: '公司空间', exact: true }),
  });
  await panel.waitFor({ timeout: 30000 });
  const option = panel.locator('.workspace-scope-options > button').filter({ hasText: companyName }).first();
  await option.waitFor({ timeout: 30000 });
  if (await option.getAttribute('aria-current') === 'true') {
    await option.click();
    return;
  }
  const init = page.waitForResponse((response) => {
    if (!response.url().includes('/api/v1/intent')) return false;
    try {
      const payload = JSON.parse(response.request().postData() || '{}');
      const requestCompanyId = Number(payload?.context?.company_id || payload?.params?.context?.company_id || payload?.params?.company_id || 0);
      return payload?.intent === 'system.init' && requestCompanyId === expectedCompanyId;
    } catch {
      return false;
    }
  }, { timeout: 45000 });
  await option.click();
  const response = await init;
  check(response.ok(), `company switch system.init failed: ${response.status()}`);
  await panel.waitFor({ state: 'hidden', timeout: 45000 });
  await contextIndicator.getByRole('button', { name: `切换公司：${companyName}`, exact: true }).waitFor({ timeout: 45000 });
}

async function selectProjectContext(page, target) {
  check(target.project_id > 0, 'project context target id is required');
  check(Boolean(target.project_label), 'project context target label is required');
  const trigger = page.getByRole('button', { name: /项目空间：切换项目|切换项目/ }).first();
  await trigger.click();
  const panel = page.locator('section[aria-labelledby="record-context-space-title"]');
  await panel.waitFor({ timeout: 30000 });
  const option = panel.getByRole('button').filter({ hasText: target.project_label }).first();
  await option.waitFor({ timeout: 30000 });
  const initResponse = page.waitForResponse((response) => {
    if (!response.url().includes('/api/v1/intent')) return false;
    try {
      const payload = JSON.parse(response.request().postData() || '{}');
      return payload?.intent === 'system.init'
        && Number(payload?.params?.current_project_id || 0) === Number(target.project_id);
    } catch {
      return false;
    }
  }, { timeout: 45000 });
  await option.click();
  const response = await initResponse;
  check(response.ok(), `project context system.init failed: ${response.status()}`);
  const request = JSON.parse(response.request().postData() || '{}');
  check(Number(request?.params?.current_project_id || 0) === Number(target.project_id), 'project context was not carried by system.init');
  return {
    project_id: Number(target.project_id),
    project_label: target.project_label,
    system_init_project_id: Number(request.params.current_project_id),
  };
}

async function sectionCount(page, key) {
  return Number((await page.locator(`.count-card[data-section-key="${key}"] strong`).innerText()).trim());
}

async function assertCountMatches(page, key) {
  await page.locator(`.count-card[data-section-key="${key}"]`).click();
  const count = await sectionCount(page, key);
  const rows = await page.locator(`.work-section[data-section-key="${key}"] .work-card`).count();
  check(count === rows, `${key} count/list mismatch ${count}/${rows}`);
  return count;
}

async function noOverflow(page, label) {
  const size = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }));
  check(size.scroll <= size.client + 1, `${label}: horizontal overflow ${size.scroll}/${size.client}`);
}

async function main() {
  for (const key of ['draft', 'approval', 'reject', 'completed']) check(TARGETS[key]?.record_id > 0, `missing target ${key}`);
  check(TARGETS.draft.project_id > 0 && TARGETS.draft.project_label, 'missing project context target');
  check(/^[0-9a-f]{40}$/.test(EXPECTED_SHA), 'exact expected candidate SHA is required');
  check(/^[0-9a-f]{40}$/.test(PREVIEW_BASE_SHA), 'exact preview base SHA is required');
  check(Boolean(PREVIEW_ENTRY && /^[0-9a-f]{64}$/.test(PREVIEW_ENTRY_SHA256)), 'preview bundle identity is required');
  const browser = await launchChromium({ headless: true });
  const report = {
    pass: false,
    provenance: {
      base_url: BASE_URL,
      database: DB_NAME,
      expected_sha: EXPECTED_SHA,
      preview_base_sha: PREVIEW_BASE_SHA,
      preview_entry: PREVIEW_ENTRY,
      preview_entry_sha256: PREVIEW_ENTRY_SHA256,
      test_script_sha: SCRIPT_SHA,
      approval_reviewer_login: APPROVAL_REVIEWER_LOGIN,
    },
    j07: {}, j08: {}, responsive: [], failure_paths: {}, isolation: {},
  };
  let page;
  let runtime;
  try {
    page = await browser.newPage({ viewport: { width: 1440, height: 900 }, locale: 'zh-CN' });
    async function capture(stage) {
      const screenshot = path.join(OUTPUT_DIR, `approval-page-${stage}.png`);
      await page.screenshot({ path: screenshot, fullPage: true });
      report.approval_page_captures = [...(report.approval_page_captures || []), {
        stage,
        url: page.url(),
        screenshot,
      }];
    }
    runtime = captureRuntime(page);
    const releasedNavigation = captureReleasedNavigation(page);
    const runtimeVersionResponse = await page.request.get(`${BASE_URL}/api/runtime-version`);
    check(runtimeVersionResponse.ok(), `runtime identity request failed: ${runtimeVersionResponse.status()}`);
    const runtimeVersion = await runtimeVersionResponse.json();
    report.provenance.runtime_version = runtimeVersion;
    check(runtimeVersion.source_revision === EXPECTED_SHA, `served revision ${runtimeVersion.source_revision || 'unknown'} != expected ${EXPECTED_SHA}`);
    check(runtimeVersion.database === DB_NAME, `served database ${runtimeVersion.database || 'unknown'} != ${DB_NAME}`);
    await login(page, 'fixture_role_finance');
    report.provenance.project_context = await selectProjectContext(page, TARGETS.draft);
    applyReleasedNavigationTarget(
      TARGETS,
      ['draft', 'approval', 'reject', 'completed'],
      await releasedNavigation.targetByMenuXmlid(TARGETS.draft.menu_xmlid),
    );
    const myWorkScene = await resolveDesignedMyWorkScene(page, releasedNavigation);
    report.provenance.my_work_scene = myWorkScene;
    resetRuntime(runtime);

    // J07: authoritative counts, detail round-trip, submit and company A/B/A invalidation.
    await openMyWork(page, myWorkScene);
    const todoBefore = await assertCountMatches(page, 'todo');
    const initiatedBefore = await assertCountMatches(page, 'initiated');
    check(todoBefore > 0 && initiatedBefore > 0, 'J07 finance work sections are empty');
    await page.locator('.work-card').filter({ hasText: 'FE-JOURNEY-PAYMENT-001' }).getByRole('button', { name: '打开详情' }).click();
    await waitForCanonicalForm(page, TARGETS.draft);
    check((await page.locator('body').innerText()).includes('FE-JOURNEY-PAYMENT-001'), 'J07 detail identity missing');
    await page.goBack();
    await page.locator('.product-work').waitFor({ timeout: 45000 });
    await page.locator('.count-card[data-section-key="todo"]').click();
    const journeyCard = page.locator('.work-card').filter({ hasText: 'FE-JOURNEY-PAYMENT-001' });
    await journeyCard.getByRole('button', { name: '提交' }).click();
    const dialog = page.getByRole('dialog');
    await dialog.waitFor({ timeout: 15000 });
    const confirm = dialog.getByRole('button', { name: '确认提交' });
    await page.waitForFunction(() => {
      const primary = document.querySelector('.intent-dialog .dialog-actions button:last-child');
      return primary !== null && primary === document.activeElement;
    }, null, { timeout: 5000 }).catch(() => {
      throw new Error('J07 confirmation focus did not enter');
    });
    await confirm.press('Enter');
    await dialog.waitFor({ state: 'hidden', timeout: 45000 });
    await page.locator('.work-section[data-section-key="todo"] .work-card').filter({ hasText: 'FE-JOURNEY-PAYMENT-001' }).waitFor({ state: 'detached', timeout: 45000 });
    await assertCountMatches(page, 'todo');
    await page.locator('.count-card[data-section-key="initiated"]').click();
    check(await page.locator('.work-card').filter({ hasText: 'FE-JOURNEY-PAYMENT-001' }).count() === 1, 'J07 submitted item left initiated section');
    await selectCompany(page, 'FE Company B');
    await openMyWork(page, myWorkScene);
    check(!(await page.locator('body').innerText()).includes('FE-JOURNEY-PAYMENT-001'), 'J07 company B retained company A item');
    await page.locator('.count-card[data-section-key="initiated"]').click();
    await page.locator('.work-section[data-section-key="initiated"]').waitFor({ timeout: 15000 });
    check((await page.locator('body').innerText()).includes('FE-C-PR-001'), 'J07 company B work item missing');
    await selectCompany(page, 'FE Company A');
    report.provenance.project_context = await selectProjectContext(page, TARGETS.draft);
    await openMyWork(page, myWorkScene);
    check(!(await page.locator('body').innerText()).includes('FE-C-PR-001'), 'J07 company A retained company B item');
    assertClean(runtime, 'J07');
    report.j07 = { status: 'PASS', todo_before: todoBefore, initiated_before: initiatedBefore, company_a_b_a: 'PASS' };

    // J08 approval fixture: load the authoritative summary, prove the assigned
    // reviewer can act, execute the real approval and verify the result feedback.
    resetRuntime(runtime);
    await logout(page);
    await login(page, APPROVAL_REVIEWER_LOGIN);
    report.provenance.project_context = await selectProjectContext(page, TARGETS.approval);
    await openMyWork(page, myWorkScene);
    await page.locator('.count-card[data-section-key="todo"]').click();
    const reviewerTodoBefore = await sectionCount(page, 'todo');
    const approvalCard = page.locator('.work-card').filter({ hasText: 'FE-JOURNEY-APPROVAL-001' }).first();
    await approvalCard.waitFor({ timeout: 45000 });
    check(Boolean(TARGETS.approval.amount_display), 'approval target money display is required');
    check((await approvalCard.innerText()).includes(TARGETS.approval.amount_display), 'approval work item lost the authoritative money value');
    await approvalCard.getByRole('button', { name: '打开详情' }).click();
    await waitForCanonicalForm(page, TARGETS.approval);
    const approvalForm = canonicalForm(page, TARGETS.approval);
    const approvalPageSummary = await approvalForm.innerText();
    check(approvalPageSummary.includes('FE-JOURNEY-APPROVAL-001'), 'approval page lost the work item identity');
    check(approvalPageSummary.includes(TARGETS.approval.amount_display), 'approval page lost the authoritative money value');
    const approvalButtons = page.getByRole('button', { name: /^(审批|审批通过)$/, exact: true });
    check(await approvalButtons.count() === 1, 'approval page must expose exactly one current approve action');
    const approvalExecuted = page.waitForResponse((response) => {
      if (!response.url().includes('/api/v1/intent')) return false;
      try {
        const payload = JSON.parse(response.request().postData() || '{}');
        return ['payment.request.execute', 'execute_button'].includes(payload?.intent)
          && Number(payload?.params?.id || payload?.params?.res_id || 0) === Number(TARGETS.approval.record_id);
      } catch {
        return false;
      }
    }, { timeout: 45000 });
    await approvalButtons.click();
    const approvalDialog = page.getByRole('dialog');
    if (await approvalDialog.count()) {
      await approvalDialog.getByRole('button', { name: /^(确认审批|确认审批通过|确认)$/ }).click();
    }
    const approvalResponse = await approvalExecuted;
    const approvalPayload = await approvalResponse.json();
    check(approvalResponse.ok() && approvalPayload?.ok, 'approval page action was rejected');
    await waitForWorkflowState(page, 'approved');
    await capture('approval-result');
    await openMyWork(page, myWorkScene);
    const approvedTodo = page.locator('.work-section[data-section-key="todo"] .work-card').filter({ hasText: 'FE-JOURNEY-APPROVAL-001' });
    await approvedTodo.waitFor({ state: 'detached', timeout: 45000 });
    check(await approvedTodo.count() === 0, 'J08 approved item remained in todo');
    await page.waitForFunction((expected) => Number(document.querySelector('.count-card[data-section-key="todo"] strong')?.textContent || -1) === expected, reviewerTodoBefore - 1, { timeout: 15000 });
    const reviewerTodoAfter = await sectionCount(page, 'todo');
    check(reviewerTodoAfter === reviewerTodoBefore - 1, 'J08 approval did not update the visible worklist count');
    await logout(page);

    await login(page, 'fixture_role_finance');
    report.provenance.project_context = await selectProjectContext(page, TARGETS.approval);
    await page.goto(`${BASE_URL}${route(TARGETS.approval)}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
    const approvedForm = await waitForCanonicalForm(page, TARGETS.approval);
    await waitForWorkflowState(page, 'approved');
    check((await page.locator('body').innerText()).includes('FE-JOURNEY-APPROVAL-001'), 'J08 finance cannot see approved result');
    const approvedAmountField = approvedForm.locator('[data-field-name="amount"]:visible');
    check(await approvedAmountField.count() === 1, 'J08 detail amount field identity is not unique');
    check(
      (await approvedAmountField.innerText()).includes(TARGETS.approval.amount_display),
      'J08 canonical amount field lost the My Work amount',
    );
    const approvedWorkflowBars = page.locator('[data-professional-workflow-component="action-bar"]:visible');
    await approvedWorkflowBars.first().waitFor({ timeout: 15000 });
    const approvedWorkflow = await approvedWorkflowBars.evaluateAll((nodes) => nodes.map((node) => ({
      actionCount: node.getAttribute('data-workflow-action-count'),
      disabledCount: node.getAttribute('data-workflow-disabled-count'),
      text: node.textContent,
      buttons: [...node.querySelectorAll('button')].map((button) => ({
        text: button.textContent,
        disabled: button.disabled,
        actionEnabled: button.getAttribute('data-action-enabled'),
      })),
    })));
    const approvedDenialTriggers = await page.locator(
      '.form-action-denial-trigger:visible, [data-workflow-reason-trigger]:visible',
    ).evaluateAll((nodes) => nodes.map((node) => ({
      text: node.textContent,
      label: node.getAttribute('aria-label'),
      role: node.getAttribute('role'),
      tabindex: node.getAttribute('tabindex'),
    })));
    assertClean(runtime, 'J08');
    report.j08 = {
      status: 'PASS',
      fixture: 'FE-JOURNEY-APPROVAL-001',
      reviewer_login: APPROVAL_REVIEWER_LOGIN,
      reviewer_availability: 'PASS',
      reviewer_approval: 'PASS_FROM_APPROVAL_PAGE',
      approval_page_summary: 'PASS',
      approval_result_readback: 'PASS_APPROVED',
      approval_feedback: 'PASS_RETURNED_TO_UPDATED_WORKLIST',
      pending_inline_feedback: 'NOT_OBSERVED',
      cross_page_readout: {
        status: 'PASS',
        identity: 'FE-JOURNEY-APPROVAL-001',
        amount: TARGETS.approval.amount_display,
        work_card: 'PASS',
        approval_summary: 'PASS',
        approved_detail_field: 'PASS: [data-field-name="amount"]',
        workflow_current: 'approved',
      },
      todo_before: reviewerTodoBefore,
      todo_after: reviewerTodoAfter,
      approved_workflow: approvedWorkflow,
      approved_denial_triggers: approvedDenialTriggers,
    };

    // Explicit reject validation and unauthorized isolation.
    await logout(page);
    await login(page, APPROVAL_REVIEWER_LOGIN);
    report.provenance.project_context = await selectProjectContext(page, TARGETS.reject);
    await openMyWork(page, myWorkScene);
    await page.locator('.count-card[data-section-key="todo"]').click();
    const rejectCard = page.locator('.work-card').filter({ hasText: 'FE-JOURNEY-REJECT-001' });
    await rejectCard.getByRole('button', { name: '打开详情' }).click();
    await waitForCanonicalForm(page, TARGETS.reject);
    let rejectButton = page.getByRole('button', { name: /^(审批驳回|驳回)$/, exact: true });
    if (!await rejectButton.count()) {
      await page.getByRole('button', { name: '更多操作', exact: true }).click();
      rejectButton = page.getByText('审批驳回', { exact: true }).filter({ visible: true });
      await rejectButton.waitFor({ state: 'visible', timeout: 5000 });
    }
    check(await rejectButton.count() === 1, 'approval page must expose exactly one current reject action');
    let rejectRequestCount = 0;
    const observeRejectRequest = (request) => {
      if (!request.url().includes('/api/v1/intent')) return;
      try {
        const payload = JSON.parse(request.postData() || '{}');
        if (['payment.request.execute', 'execute_button'].includes(payload?.intent)
          && Number(payload?.params?.id || payload?.params?.res_id || 0) === Number(TARGETS.reject.record_id)) {
          rejectRequestCount += 1;
        }
      } catch {}
    };
    page.on('request', observeRejectRequest);
    await rejectButton.click();
    const rejectSafetyDialog = page.locator('[data-dialog-purpose="intent-confirmation"][data-state="open"]');
    await rejectSafetyDialog.waitFor({ state: 'visible', timeout: 10000 });
    await rejectSafetyDialog.getByRole('button', { name: /^确认(?:审批)?驳回$/ }).click();
    await rejectSafetyDialog.waitFor({ state: 'hidden', timeout: 10000 });
    const rejectDialog = page.locator('.contract-reason-dialog');
    await rejectDialog.waitFor({ state: 'visible', timeout: 10000 });
    const rejectReason = rejectDialog.getByLabel('拒绝原因');
    const rejectSubmit = rejectDialog.getByRole('button', { name: '确认驳回' });
    await rejectReason.waitFor({ state: 'visible', timeout: 10000 });
    check(await rejectSubmit.isDisabled(), 'empty decision reason must leave submit disabled');
    check(await canonicalForm(page, TARGETS.reject).isVisible(), 'reject without reason left the approval page');
    await page.waitForTimeout(300);
    check(rejectRequestCount === 0, 'reject must not issue execute_button before a valid reason');
    await rejectReason.fill('验收拒绝原因');
    check(await rejectSubmit.isEnabled(), 'a valid decision reason must enable submit');
    const rejectExecuted = page.waitForResponse((response) => {
      if (!response.url().includes('/api/v1/intent')) return false;
      try {
        const payload = JSON.parse(response.request().postData() || '{}');
        return ['payment.request.execute', 'execute_button'].includes(payload?.intent)
          && Number(payload?.params?.id || payload?.params?.res_id || 0) === Number(TARGETS.reject.record_id);
      } catch {
        return false;
      }
    }, { timeout: 45000 });
    await rejectSubmit.click();
    const rejectResponse = await rejectExecuted;
    const rejectPayload = await rejectResponse.json();
    const rejectRequestPayload = JSON.parse(rejectResponse.request().postData() || '{}');
    check(rejectResponse.ok() && rejectPayload?.ok, 'reject page action was rejected after a valid reason');
    check(rejectRequestPayload?.params?.button?.name === 'action_approval_reject', 'reject used a different action identity');
    check(rejectRequestPayload?.params?.action_params?.reason === '验收拒绝原因', 'reject reason was not carried by the execute_button contract request');
    await rejectDialog.waitFor({ state: 'hidden', timeout: 45000 });
    await waitForWorkflowState(page, 'rejected');
    await capture('reject-result');
    await openMyWork(page, myWorkScene);
    const rejectedTodo = page.locator('.work-section[data-section-key="todo"] .work-card[data-record-id="' + Number(TARGETS.reject.record_id) + '"]').filter({ hasText: 'FE-JOURNEY-REJECT-001' });
    await rejectedTodo.waitFor({ timeout: 45000 });
    check(await rejectedTodo.getAttribute('data-work-item-state') === 'rejected', 'rejected payment work item did not expose the authoritative rejected state');
    check(await page.locator('.work-section[data-section-key="todo"] .work-card[data-record-id="' + Number(TARGETS.reject.record_id) + '"][data-work-item-state="pending"]').count() === 0, 'completed approval task remained pending');
    page.off('request', observeRejectRequest);
    report.failure_paths.reject_reason = 'PASS_PAGE_DATA_UNCHANGED_BEFORE_VALID_REASON_AND_CARRIED_TO_EXECUTION';
    await logout(page);

    await login(page, 'fixture_role_project_a_member');
    report.provenance.project_context = await selectProjectContext(page, TARGETS.approval);
    await openMyWork(page, myWorkScene);
    const memberText = await page.locator('body').innerText();
    check(!/FE-JOURNEY-(?:PAYMENT|APPROVAL|REJECT)|¥|￥/.test(memberText), 'project member My Work leaked payment facts');
    await page.goto(`${BASE_URL}${route(TARGETS.approval)}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.getByText('当前账号无权访问此内容，请返回已授权的工作区。', { exact: true }).waitFor({ timeout: 45000 });
    const denied = await page.locator('body').innerText();
    check(!denied.includes('FE-JOURNEY-APPROVAL-001') && !denied.includes('80.00'), 'denial leaked approval facts');
    report.isolation.project_member = 'PASS';

    for (const viewport of [{ width: 1440, height: 900 }, { width: 1280, height: 800 }, { width: 390, height: 844 }]) {
      await page.setViewportSize(viewport);
      await openMyWork(page, myWorkScene);
      await noOverflow(page, `${viewport.width}x${viewport.height}`);
      const screenshot = path.join(OUTPUT_DIR, `my-work-${viewport.width}x${viewport.height}.png`);
      await page.screenshot({ path: screenshot, fullPage: true });
      report.responsive.push({ viewport, status: 'PASS', screenshot });
    }
    await logout(page);
    report.pass = true;
    fs.writeFileSync(path.join(OUTPUT_DIR, 'report.json'), `${JSON.stringify(report, null, 2)}\n`);
    console.log('[verify.frontend.my_work_approval.browser] PASS');
  } catch (error) {
    if (page) await page.screenshot({ path: path.join(OUTPUT_DIR, 'failure.png'), fullPage: true }).catch(() => {});
    const pageState = page ? { url: page.url(), text: (await page.locator('body').innerText().catch(() => '')).slice(0, 12000) } : {};
    fs.writeFileSync(path.join(OUTPUT_DIR, 'failure.json'), `${JSON.stringify({ report, runtime, page: pageState, error: error.stack || error.message }, null, 2)}\n`);
    throw error;
  } finally {
    await browser.close();
  }
}

main().catch((error) => { console.error(`[verify.frontend.my_work_approval.browser] FAIL ${error.stack || error.message}`); process.exitCode = 1; });
