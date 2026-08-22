import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';

const target = JSON.parse(process.env.LOCAL_DEV_PAYMENT_FLOORPLAN_JSON || '{}');
const frontendUrl = process.env.FRONTEND_URL || '';
const database = process.env.DB_NAME || '';
const password = process.env.E2E_PASSWORD || '';
const login = String(target?.user?.login || '');
const actionId = Number(target?.action?.id || 0);
const menuId = Number(target?.menu?.id || 0);
const record = target?.actionable_record || {};
const candidateInventory = Array.isArray(target?.candidate_inventory) ? target.candidate_inventory : [];
const recordId = Number(record.id || 0);
const outputDir = path.resolve('artifacts/playwright/local-dev-payment-request-floorplan-submit');

function check(value, message, details = undefined) {
  if (value) return;
  throw new Error(`${message}${details === undefined ? '' : ` ${JSON.stringify(details)}`}`);
}

function intentOf(response) {
  if (!response.url().includes('/api/v1/intent')) return '';
  try { return String(JSON.parse(response.request().postData() || '{}').intent || ''); } catch { return ''; }
}

function isListDataResponse(response) {
  if (intentOf(response) !== 'api.data') return false;
  try {
    const body = JSON.parse(response.request().postData() || '{}');
    return String(body?.params?.op || body?.op || '') === 'list';
  } catch {
    return false;
  }
}

check(frontendUrl && database && password && login, 'local.dev submit identity is incomplete');
check(actionId > 0 && menuId > 0 && recordId > 0 && record.state === 'draft', 'submit-ready target is invalid', record);
fs.mkdirSync(outputDir, { recursive: true });

const browser = await launchChromium({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' });
const page = await context.newPage();
const errors = [];
const mutations = [];
const observedIntents = [];
page.on('console', (message) => {
  if (message.type() === 'error' && !message.text().includes('favicon')) errors.push(message.text());
});
page.on('pageerror', (error) => errors.push(error.message));
page.on('request', (request) => {
  if (request.method() !== 'POST') return;
  let body = {};
  try { body = JSON.parse(request.postData() || '{}'); } catch {}
  const intent = String(body?.intent || '');
  if (intent) observedIntents.push(intent);
  if (intent === 'execute_button') mutations.push({ intent, params: body.params });
});

const report = { schemaVersion: 'payment_request_floorplan_submit.v1', target: record, pass: false };
try {
  await page.goto(`${frontendUrl}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const inputs = page.locator('input');
  await inputs.nth(0).fill(login);
  await inputs.nth(1).fill(password);
  if (await inputs.nth(2).count() && !(await inputs.nth(2).isDisabled())) await inputs.nth(2).fill(database);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 30000 });

  await page.goto(`${frontendUrl}/`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const homeSurface = page.locator('[data-role-home]').first();
  await homeSurface.waitFor({ timeout: 45000 });
  await homeSurface.locator('.role-home-surface__tasks .role-home-surface__state, .role-home-surface__task-list').waitFor({ timeout: 45000 });
  const homeBefore = {
    tasks: await homeSurface.locator('.role-home-surface__task-list article').allTextContents(),
    summaries: await homeSurface.locator('.role-home-surface__summary-list article').allTextContents(),
  };

  const listUrl = `${frontendUrl}/a/${actionId}?menu_id=${menuId}`;
  await page.goto(listUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const listSurface = page.locator('[data-product-page-mode="list"]').first();
  await listSurface.waitFor({ timeout: 45000 });
  const actionableRow = listSurface.locator('tbody tr').filter({ hasText: record.name }).first();
  await actionableRow.waitFor({ timeout: 45000 });
  const listRowBefore = (await actionableRow.innerText()).replace(/\s+/g, ' ').trim();
  await listSurface.getByRole('button', { name: /^新建$/ }).click();
  const createSurface = page.locator('[data-product-page-mode="form"]').first();
  await createSurface.waitFor({ timeout: 45000 });
  await createSurface.locator('[data-contract-form-driver]').waitFor({ timeout: 45000 });
  const createEditableFieldLocator = createSurface.locator(
    'input:not([type="hidden"]):not(:disabled), textarea:not(:disabled), select:not(:disabled)',
  );
  await createEditableFieldLocator.first().waitFor({ timeout: 15000 });
  const createEditableFields = await createEditableFieldLocator.count();
  check(createEditableFields > 0, 'payment create entry did not open an editable form', createEditableFields);
  await page.goto(listUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.locator('[data-product-page-mode="list"]').first().waitFor({ timeout: 45000 });

  const blocked = candidateInventory.find((item) => item.state === 'draft' && item.submit_enabled === false);
  const terminal = candidateInventory.find((item) => ['done', 'paid'].includes(item.state)
    || /已足额付款|已完成/.test(String(item.legal_next_action || '')));
  check(blocked?.id && terminal?.id, 'payment state variant fixtures are incomplete', candidateInventory);
  const stateVariants = {};
  for (const [kind, item] of [['blocked', blocked], ['terminal', terminal]]) {
    await page.goto(`${frontendUrl}/r/payment.request/${item.id}?menu_id=${menuId}&action_id=${actionId}`, {
      waitUntil: 'domcontentloaded', timeout: 45000,
    });
    await page.locator('[data-object-task-page]').waitFor({ timeout: 45000 });
    const enabledPrimaryCount = await page.locator(
      '[data-object-task-page] [data-action-tier="primary"][data-action-enabled="true"]',
    ).count();
    const taskText = (await page.locator('[data-floorplan-region="current-task"]').innerText()).replace(/\s+/g, ' ').trim();
    stateVariants[kind] = { id: item.id, name: item.name, enabledPrimaryCount, taskText };
    check(enabledPrimaryCount === 0, `${kind} payment record exposed a misleading primary action`, stateVariants[kind]);
    if (kind === 'blocked') {
      check(/缺少|请补充|请维护/.test(taskText), 'blocked payment has no repair path', stateVariants[kind]);
      const editAction = page.locator('[data-form-mode-action="edit"]:visible');
      check(await editAction.count() === 1, 'blocked payment must expose one remediation edit path');
      await editAction.click();
      const editableFields = page.locator(
        '[data-product-page-mode="form"] input:not([type="hidden"]):not(:disabled), '
        + '[data-product-page-mode="form"] textarea:not(:disabled), [data-product-page-mode="form"] select:not(:disabled)',
      );
      await editableFields.first().waitFor({ timeout: 15000 });
      stateVariants[kind].editableFields = await editableFields.count();
      check(stateVariants[kind].editableFields > 0, 'blocked remediation path did not enter edit mode');
    }
  }

  await page.goto(listUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.locator('[data-product-page-mode="list"]').first().waitFor({ timeout: 45000 });
  const journeyRow = page.locator('[data-product-page-mode="list"] tbody tr').filter({ hasText: record.name }).first();
  await journeyRow.waitFor({ timeout: 45000 });
  await journeyRow.click();
  await page.waitForURL((url) => url.pathname === `/r/payment.request/${recordId}`, { timeout: 45000 });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(300);
  await page.locator('[data-object-task-page]').waitFor({ timeout: 45000 });

  check(page.url().includes(`/r/payment.request/${recordId}`), 'list row did not open the actionable payment detail', page.url());
  const surface = page.locator('[data-mobile-action-surface]').first();
  const primary = surface.locator('[data-action-tier="primary"][data-action-enabled="true"]');
  check(await primary.count() === 1, 'submit-ready fixture must expose one enabled primary action');
  check((await primary.innerText()).trim() === '提交审批', 'unexpected primary action label', await primary.innerText());
  const metrics = await surface.evaluate((node) => {
    const rect = node.getBoundingClientRect();
    const style = getComputedStyle(node);
    return {
      position: style.position,
      bottom: rect.bottom,
      viewportHeight: innerHeight,
      overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    };
  });
  check(metrics.position === 'fixed' && Math.abs(metrics.bottom - metrics.viewportHeight) <= 1 && metrics.overflow <= 0,
    'mobile primary action surface is not fixed and contained', metrics);
  const beforeTaskText = (await page.locator('[data-floorplan-region="current-task"]').innerText()).replace(/\s+/g, ' ').trim();
  await page.screenshot({ path: path.join(outputDir, 'before-submit-390.png') });

  await primary.click();
  const dialog = page.locator('dialog.intent-confirmation[open]');
  await dialog.waitFor({ state: 'visible', timeout: 5000 });
  const confirmationText = (await dialog.innerText()).replace(/\s+/g, ' ').trim();
  check(confirmationText.includes('确认提交审批'), 'business confirmation title is missing', confirmationText);
  check(confirmationText.includes('系统将重新读取付款申请及上下游金额状态'), 'authoritative confirmation message is missing', confirmationText);
  await page.screenshot({ path: path.join(outputDir, 'confirmation-390.png') });

  const executePromise = page.waitForResponse((response) => intentOf(response) === 'execute_button', { timeout: 30000 });
  await dialog.getByRole('button', { name: /^确认提交审批$/ }).click();
  const executeResponse = await executePromise;
  const executeBody = await executeResponse.json();
  report.execute = { status: executeResponse.status(), body: executeBody };
  check(executeResponse.status() === 200 && executeBody?.ok === true, 'submit execution failed', executeBody);
  const statusSummary = page.locator('.native-statusbar-summary--readonly').first();
  const currentStateLocator = statusSummary.locator('strong').first();
  await currentStateLocator.waitFor({ state: 'visible', timeout: 45000 });
  await page.locator('[data-object-task-page]').waitFor({ state: 'visible', timeout: 45000 });
  const currentState = (await currentStateLocator.innerText()).trim();
  const statusSummaryText = (await statusSummary.innerText()).replace(/\s+/g, ' ').trim();
  const currentTaskText = (await page.locator('[data-floorplan-region="current-task"]').innerText()).replace(/\s+/g, ' ').trim();
  const currentPageText = (await page.locator('body').innerText()).replace(/\s+/g, ' ').trim();
  check(!currentPageText.includes('无权访问'), 'successful submit navigated to an access-denied product surface', {
    executeBody, observedIntents, url: page.url(), currentPageText,
  });
  check(currentState === '提交', 'page did not refresh to the submitted business state', {
    currentState, observedIntents, url: page.url(), currentPageText,
  });
  check(currentTaskText.includes('下一步办理') && currentTaskText.includes('审批处理'),
    'post-submit next step was not refreshed from authoritative facts', currentTaskText);
  check(currentTaskText !== beforeTaskText, 'post-submit task and blocker projection did not refresh', {
    beforeTaskText, currentTaskText,
  });
  const executeIntentIndex = observedIntents.lastIndexOf('execute_button');
  const refreshIntents = executeIntentIndex >= 0 ? observedIntents.slice(executeIntentIndex + 1) : [];
  check(refreshIntents.includes('ui.contract.v2') && refreshIntents.includes('api.data'),
    'post-submit contract and record were not refreshed', refreshIntents);

  const regions = await page.locator('[data-object-task-page] [data-floorplan-region]').evaluateAll((nodes) => (
    [...new Set(nodes.map((node) => node.getAttribute('data-floorplan-region')).filter(Boolean))]
  ));
  for (const region of ['summary', 'current-task', 'relation', 'activity', 'audit']) {
    check(regions.includes(region), `post-submit Floorplan region missing: ${region}`, regions);
  }
  const auditRegion = page.locator('[data-floorplan-region="audit"]').first();
  await auditRegion.locator('summary').click();
  await auditRegion.locator('[data-audit-event]').first().waitFor({ timeout: 15000 });
  const auditEvents = await auditRegion.locator('[data-audit-event]').evaluateAll((nodes) => nodes.map((node) => ({
    actor: String(node.querySelector('[data-audit-actor]')?.textContent || '').replace(/\s+/g, ' ').trim(),
    time: String(node.querySelector('[data-audit-time]')?.textContent || '').replace(/\s+/g, ' ').trim(),
    event: String(node.querySelector('[data-audit-event-name]')?.textContent || '').replace(/\s+/g, ' ').trim(),
    result: String(node.querySelector('[data-audit-result]')?.textContent || '').replace(/\s+/g, ' ').trim(),
  })));
  check(auditEvents.length >= 1 && auditEvents.every((event) => event.actor && event.time && event.event && event.result),
    'post-submit audit region has no trustworthy event', auditEvents);
  check(mutations.length === 1 && mutations[0].params?.button?.name === 'action_submit', 'journey emitted unexpected mutations', mutations);
  check(errors.length === 0, 'browser errors detected', errors);
  await page.screenshot({ path: path.join(outputDir, 'after-submit-390-full.png'), fullPage: true });
  await page.setViewportSize({ width: 1440, height: 960 });
  const listRefreshResponse = page.waitForResponse(isListDataResponse, { timeout: 45000 });
  await page.getByRole('button', { name: /返回列表/ }).first().click();
  await page.locator('[data-product-page-mode="list"]').first().waitFor({ timeout: 45000 });
  await listRefreshResponse;
  await page.waitForFunction(
    ({ name, before }) => {
      const row = [...document.querySelectorAll('[data-product-page-mode="list"] tbody tr')]
        .find((node) => String(node.textContent || '').includes(name));
      return row && String(row.textContent || '').replace(/\s+/g, ' ').trim() !== before;
    },
    { name: record.name, before: listRowBefore },
    { timeout: 45000 },
  );
  const refreshedRow = page.locator('[data-product-page-mode="list"] tbody tr').filter({ hasText: record.name }).first();
  await refreshedRow.waitFor({ timeout: 45000 });
  const listRowAfter = (await refreshedRow.innerText()).replace(/\s+/g, ' ').trim();
  check(/提交|待审批/.test(listRowAfter) && listRowAfter !== listRowBefore,
    'payment list retained the pre-submit state', { listRowBefore, listRowAfter });
  await page.screenshot({ path: path.join(outputDir, 'after-submit-list-desktop.png'), fullPage: true });

  await page.goto(`${frontendUrl}/`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  const refreshedHome = page.locator('[data-role-home]').first();
  await refreshedHome.waitFor({ timeout: 45000 });
  await refreshedHome.locator('.role-home-surface__tasks .role-home-surface__state, .role-home-surface__task-list').waitFor({ timeout: 45000 });
  const homeAfter = {
    tasks: await refreshedHome.locator('.role-home-surface__task-list article').allTextContents(),
    summaries: await refreshedHome.locator('.role-home-surface__summary-list article').allTextContents(),
  };
  const staleHomeTask = homeAfter.tasks.find((text) => text.includes(record.name) && /草稿/.test(text));
  check(!staleHomeTask, 'home todo retained the pre-submit payment state', { homeBefore, homeAfter });
  const executeIntentIndexForHome = observedIntents.lastIndexOf('execute_button');
  check(observedIntents.slice(executeIntentIndexForHome + 1).includes('my.work.summary'),
    'home todo was not reloaded after the payment transition', observedIntents);
  await page.screenshot({ path: path.join(outputDir, 'after-submit-home-desktop.png'), fullPage: true });
  report.regions = regions;
  report.statusSummary = statusSummaryText;
  report.currentTask = currentTaskText;
  report.auditEvents = auditEvents;
  report.mutations = mutations;
  report.errors = errors;
  report.observedIntents = observedIntents;
  report.stateVariants = stateVariants;
  report.list = { before: listRowBefore, after: listRowAfter };
  report.create = { editableFields: createEditableFields };
  report.home = { before: homeBefore, after: homeAfter };
  report.pass = true;
  fs.writeFileSync(path.join(outputDir, 'summary.json'), `${JSON.stringify(report, null, 2)}\n`);
  console.log(`[local.dev.payment.floorplan.submit] PASS record=${recordId} transition=draft->submit mutations=${mutations.length}`);
} catch (error) {
  report.failure = error instanceof Error ? error.message : String(error);
  report.mutations = mutations;
  report.errors = errors;
  report.observedIntents = observedIntents;
  fs.writeFileSync(path.join(outputDir, 'summary.json'), `${JSON.stringify(report, null, 2)}\n`);
  await page.screenshot({ path: path.join(outputDir, 'failure.png'), fullPage: true }).catch(() => {});
  throw error;
} finally {
  await context.close();
  await browser.close();
}
