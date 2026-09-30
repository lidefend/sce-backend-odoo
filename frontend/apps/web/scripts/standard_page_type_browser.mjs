import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { eventProbeWriteKind, diaryProbeWriteKind, expenseProbeWriteKind, permitsExpensePolicyWrite } from './standard_expense_success_scope.mjs';
import { launchChromium } from '../../../../scripts/verify/playwright_runtime.mjs';
import { permitsProjectNameWrite } from './standard_project_save_scope.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../..');
const base = 'http://127.0.0.1:5180';
const out = path.join(root, 'artifacts/frontend-web-fix-20260928', `tpl07-${Date.now()}`);
const report = { startup: [], status: 'not_run', assertions: [], calls: [], errors: [], forbiddenWrites: [], introduceContract: null };
// The introduce entry and dialog are contract driven: the probe reads the
// declared vocabulary from the effective contract response, so it can assert
// that the page renders the declared terms instead of a local rebuild.
function findIntroduceConfig(node, depth = 0) {
  if (!node || typeof node !== 'object' || depth > 14) return null;
  if (Array.isArray(node)) {
    for (const item of node) {
      const hit = findIntroduceConfig(item, depth + 1);
      if (hit) return hit;
    }
    return null;
  }
  if (node.componentKey === 'sc.payment.settlement_detail_collection' && node.componentConfig?.introduceDialog) {
    return { introduceLabel: node.componentConfig.introduceLabel, dialog: node.componentConfig.introduceDialog };
  }
  for (const value of Object.values(node)) {
    const hit = findIntroduceConfig(value, depth + 1);
    if (hit) return hit;
  }
  return null;
}
function findSavedSearchAuthority(node, depth = 0) {
  if (!node || typeof node !== 'object' || depth > 14) return null;
  if (node.custom?.favorites && typeof node.custom.favorites.save_enabled === 'boolean') return node.custom.favorites;
  for (const value of Object.values(node)) {
    const found = findSavedSearchAuthority(value, depth + 1);
    if (found) return found;
  }
  return null;
}
function findRecordAuthority(node, depth = 0) {
  if (!node || typeof node !== 'object' || depth > 14) return null;
  if (node.statusContract?.globalStatus?.effectiveRecordCapabilities && node.pageInfo?.model) {
    return { model: node.pageInfo.model, status: node.statusContract.globalStatus,
      deletePolicy: node.actionContract?.deletePolicy, mainData: node.dataContract?.mainData,
      ...(['task-authority', 'approval-actions', 'expense-policy'].includes(process.env.TPL07_SCOPE) ? { structure: node.formStructureContract, layout: node.layoutContract, actions: node.actionContract } : {}) };
  }
  for (const value of Object.values(node)) {
    const found = findRecordAuthority(value, depth + 1);
    if (found) return found;
  }
  return null;
}
const check = (name, passed, detail = {}) => { report.assertions.push({ name, passed, ...detail }); assert.ok(passed, name); };
await fs.mkdir(out, { recursive: true });
const build = JSON.parse(await fs.readFile(path.resolve(root, '../sce-offrepo/artifacts/config05-20260929/build-identity.json')));
const entry = Buffer.from(await fetch(`${base}${build.entry}`).then((res) => res.arrayBuffer()));
assert.equal(createHash('sha256').update(entry).digest('hex'), build.entry_sha256);
report.build = build;
const browser = await launchChromium({ headless: true });
const pendingProbeAborts = new Set();
let favoriteWritePermit = null;
let projectWritePermit = null;
let expenseCreateCapture = false;
const diarySaveProbe = process.env.TPL07_DIARY_SAVE_PROBE === '1';
assert.ok(!diarySaveProbe || (process.env.TPL07_SCOPE === 'approval-actions' && process.env.TPL07_APPROVAL_MODEL === 'sc.construction.diary' && process.env.TPL07_APPROVAL_VIEW === 'create'));
const eventSaveProbe = process.env.TPL07_EVENT_SAVE_PROBE === '1';
assert.ok(!eventSaveProbe || (process.env.TPL07_SCOPE === 'approval-actions' && process.env.TPL07_APPROVAL_MODEL === 'sc.contract.event' && process.env.TPL07_APPROVAL_VIEW === 'create'));
const eventSaveSuccess = process.env.TPL07_EVENT_SAVE_SUCCESS === '1';
assert.ok(!eventSaveSuccess || (eventSaveProbe && process.env.TPL07_EXPENSE_SAVE_SUCCESS !== '1' && process.env.TPL07_DIARY_SAVE_SUCCESS !== '1'));
let eventSuccess = null;
let eventCreateCapture = false;
let diaryCreateCapture = false;
const diarySaveSuccess = process.env.TPL07_DIARY_SAVE_SUCCESS === '1';
assert.ok(!diarySaveSuccess || (diarySaveProbe && process.env.TPL07_EXPENSE_SAVE_SUCCESS !== '1'));
let diarySuccess = null;
const expenseSaveProbe = process.env.TPL07_EXPENSE_SAVE_PROBE === '1';
const expenseSaveSuccess = process.env.TPL07_EXPENSE_SAVE_SUCCESS === '1';
const expenseFailureStage = process.env.TPL07_EXPENSE_FAILURE_STAGE || '';
assert.ok(['', 'upload', 'submit'].includes(expenseFailureStage));
const expensePartialUpload = process.env.TPL07_EXPENSE_PARTIAL_UPLOAD === '1';
assert.ok(!expensePartialUpload || (expenseSaveSuccess && expenseSaveProbe && expenseFailureStage === 'upload'));
let expenseSuccess = null;
let expensePolicyPermit = null;
const expenseRecoveryPath = path.join(out, 'expense-success-recovery.json');
async function expenseCleanup(stage) {
  const output = execFileSync('make', ['verify.business_config.approval_runtime', 'SC_ACCEPTANCE_RUNTIME_PROFILE=local'], {
    cwd: root, encoding: 'utf8', timeout: 60000,
    env: { ...process.env, SC_APPROVAL_RUNTIME_SCOPE: 'expense-browser-cleanup', SC_EXPENSE_CREATE_REPORT: expenseRecoveryPath },
  });
  await fs.writeFile(path.join(out, `expense-cleanup-${stage}.log`), output);
  check(`expense cleanup: ${stage} authoritative restoration`, output.includes('EXPENSE_BROWSER_CLEANUP=') && output.includes('"status": "restored"'));
}
const lifecycleName = 'FE-TPL53-私有收藏闭环';

async function login(role) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 950 }, locale: 'zh-CN' });
  const page = await ctx.newPage();
  page.on('pageerror', (error) => report.errors.push(error.message));
  await page.route('**/api/v1/intent*', async (route) => {
    const body = route.request().postDataJSON();
    if (permitsExpensePolicyWrite(role, body, expensePolicyPermit)) {
      report.expensePolicyWrites ??= [];
      report.expensePolicyWrites.push({ ...expensePolicyPermit });
      expensePolicyPermit = null;
      return route.continue();
    }
    const eventKind = eventProbeWriteKind(role, body, eventSuccess);
    if (eventKind) {
      eventSuccess.phase = `${eventKind}_in_flight`;
      await fs.writeFile(expenseRecoveryPath, JSON.stringify(eventSuccess, null, 2));
      const response = await route.fetch();
      const result = await response.json();
      report.eventSuccessWrites ??= [];
      report.eventSuccessWrites.push({ kind: eventKind, result });
      if (result.ok === true) {
        if (eventKind === 'create') eventSuccess.id = result.data?.id;
        eventSuccess.phase = eventKind === 'create' ? 'submit' : 'done';
      }
      await fs.writeFile(expenseRecoveryPath, JSON.stringify(eventSuccess, null, 2));
      return route.fulfill({ response });
    }
    if (eventSaveProbe && eventCreateCapture && role === 'fixture_role_contract_operator' && body?.intent === 'api.data'
      && body.params?.op === 'create' && body.params.model === 'sc.contract.event') {
      report.eventSaveAttempts ??= [];
      report.eventSaveAttempts.push(body.params);
      return route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({
        ok: false, error: { code: 'TPL53_EVENT_SAVE_UNAVAILABLE', message: '验收注入：事件保存暂不可用，请重试' },
      }) });
    }
    if (eventSaveProbe && ['contract.action', 'execute_button', 'file.upload'].includes(body?.intent)) {
      report.forbiddenWrites.push({ intent: body.intent, reason: 'event save failure probe cannot execute business actions' });
      return route.abort();
    }
    const diaryKind = diaryProbeWriteKind(role, body, diarySuccess);
    if (diaryKind) {
      diarySuccess.phase = `${diaryKind}_in_flight`;
      await fs.writeFile(expenseRecoveryPath, JSON.stringify(diarySuccess, null, 2));
      const response = await route.fetch();
      const result = await response.json();
      report.diarySuccessWrites ??= [];
      report.diarySuccessWrites.push({ kind: diaryKind, result });
      if (result.ok === true) {
        if (diaryKind === 'create') diarySuccess.id = result.data?.id;
        diarySuccess.phase = diaryKind === 'create' ? 'submit' : 'done';
      }
      await fs.writeFile(expenseRecoveryPath, JSON.stringify(diarySuccess, null, 2));
      return route.fulfill({ response });
    }
    if (diarySaveProbe && diaryCreateCapture && role === 'fixture_role_pm' && body?.intent === 'api.data'
      && body.params?.op === 'create' && body.params.model === 'sc.construction.diary') {
      report.diarySaveAttempts ??= [];
      report.diarySaveAttempts.push(body.params);
      return route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({
        ok: false, error: { code: 'TPL53_DIARY_SAVE_UNAVAILABLE', message: '验收注入：日志保存暂不可用，请重试' },
      }) });
    }
    if (diarySaveProbe && ['contract.action', 'execute_button', 'file.upload'].includes(body?.intent)) {
      report.forbiddenWrites.push({ intent: body.intent, reason: 'diary save failure probe cannot execute business actions' });
      return route.abort();
    }
    const expenseWriteKind = expenseProbeWriteKind(role, body, expenseSuccess);
    if (expenseWriteKind) {
      if (expenseFailureStage === expenseWriteKind && !expenseSuccess.failureInjected
        && (!expensePartialUpload || expenseSuccess.uploadIndex === 1)) {
        expenseSuccess.failureInjected = true;
        report.expenseInjectedFailure = { kind: expenseWriteKind, id: expenseSuccess.id };
        await fs.writeFile(expenseRecoveryPath, JSON.stringify(expenseSuccess, null, 2));
        return route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({
          ok: false, error: { code: 'TPL53_LATER_STAGE_UNAVAILABLE', message: '验收注入：后续操作暂不可用，请重试' },
        }) });
      }
      expenseSuccess.phase = `${expenseWriteKind}_in_flight`;
      await fs.writeFile(expenseRecoveryPath, JSON.stringify(expenseSuccess, null, 2));
      const response = await route.fetch();
      const result = await response.json();
      report.expenseSuccessWrites ??= [];
      report.expenseSuccessWrites.push({ kind: expenseWriteKind, intent: body.intent, filename: body.params?.name, result });
      if (result.ok === true) {
        if (expenseWriteKind === 'create') expenseSuccess.id = result.data?.id;
        expenseSuccess.phase = ({ create: 'upload', upload: 'submit', submit: 'done' })[expenseWriteKind];
        if (expenseWriteKind === 'upload' && expenseSuccess.files) {
          expenseSuccess.uploadIndex += 1;
          if (expenseSuccess.uploadIndex < expenseSuccess.files.length) expenseSuccess.phase = 'upload';
        }
      }
      await fs.writeFile(expenseRecoveryPath, JSON.stringify(expenseSuccess, null, 2));
      return route.fulfill({ response });
    }
    if ((expenseSaveProbe || process.env.TPL07_SCOPE === 'expense-policy') && ['contract.action', 'execute_button', 'file.upload'].includes(body?.intent)) {
      report.forbiddenWrites.push({ intent: body.intent, reason: 'save-failure probe cannot execute business actions' });
      return route.abort();
    }
    if (expenseCreateCapture && role === 'fixture_role_finance' && body?.intent === 'api.data'
      && body.params?.op === 'create' && body.params.model === 'sc.expense.claim') {
      report.expenseSaveAttempts ??= [];
      report.expenseSaveAttempts.push(body.params);
      return route.fulfill({ status: 503, contentType: 'application/json',
        body: JSON.stringify({ ok: false, error: { code: 'TPL53_SAVE_UNAVAILABLE', message: '验收注入：保存暂不可用，请重试' } }) });
    }
    if (permitsProjectNameWrite(role, body, projectWritePermit)) {
        report.projectWriteAttempts ??= [];
        report.projectWriteAttempts.push({ id: 10, name: projectWritePermit.name });
        projectWritePermit = null;
        return route.continue();
    }
    if (favoriteWritePermit && body?.intent === favoriteWritePermit.intent) {
      const permit = favoriteWritePermit;
      const params = body.params || {};
      const exact = params.model === 'payment.request' && Number(params.action_id) === 775
        && (body.intent === 'search.favorite.set'
          ? params.name === lifecycleName && params.is_default === false && params.is_shared === false
          : params.filter_id === permit.id);
      if (exact) {
        favoriteWritePermit = null;
        report.configurationAttempts ??= [];
        report.configurationAttempts.push({ intent: body.intent, id: params.filter_id, injectedFailure: permit.abort === true });
        return permit.abort ? route.abort('failed') : route.continue();
      }
    }
    if ((body?.intent === 'api.data' && !['list', 'read', 'default_get'].includes(body.params?.op))
      || ['search.favorite.set', 'search.favorite.delete', 'api.data.create', 'api.data.write', 'api.data.unlink'].includes(body?.intent)) {
      report.forbiddenWrites.push({ intent: body.intent, op: body.params?.op });
      return route.abort();
    }
    return route.continue();
  });
  page.on('response', async (response) => {
    try {
      if (new URL(response.url()).pathname === '/api/v1/auth/page-contracts') report.publicAuthContract = await response.json();
      const body = response.request().postDataJSON();
      if (['system.init', 'ui.contract', 'ui.contract.get'].includes(body?.intent)) {
        const result = await response.json();
        report.startup.push({ role, intent: body.intent, success: result.ok !== false && Boolean(result.data) });
        if (body.intent === 'system.init') {
          report.productVersion = result.data?.product_version;
          if (['approval-actions', 'expense-policy'].includes(process.env.TPL07_SCOPE)) report.routeAuthority = result.data?.navigation?.route_authority;
        }
      }
      if (body?.intent === 'api.data' && body.params?.op === 'list') {
        const result = await response.json();
        report.calls.push({ role, model: body.params.model, domain: body.params.domain, domainRaw: body.params.domain_raw, order: body.params.order, offset: body.params.offset || 0, limit: body.params.limit, ids: result.data?.records?.map((row) => row.id) || [] });
      }
      if (typeof body?.intent === 'string' && body.intent.startsWith('ui.contract')) {
        const contract = await response.json();
        if (['approval-actions', 'expense-policy'].includes(process.env.TPL07_SCOPE)) {
          report.contractResponses ??= [];
          report.contractResponses.push({ intent: body.intent, model: body.params?.model, contract });
        }
        if (contract.meta?.projection_cache) {
          report.projectionCaches ??= [];
          report.projectionCaches.push(contract.meta.projection_cache);
        }
        const recordAuthority = findRecordAuthority(contract);
        if (recordAuthority) {
          report.recordAuthority = recordAuthority;
          if (process.env.TPL07_SCOPE === 'task-authority') {
            report.taskAuthorities ??= {};
            report.taskAuthorities[recordAuthority.model] = recordAuthority;
          }
        }
        const savedSearch = findSavedSearchAuthority(contract);
        if (savedSearch) report.savedSearchAuthority = savedSearch;
        const found = findIntroduceConfig(contract);
        if (found) report.introduceContract = found;
      }
    } catch { /* only JSON list responses are observations */ }
  });
  await page.goto(`${base}/login`);
  const inputs = page.locator('input');
  if (process.env.TPL07_SCOPE === 'navigation') {
    await page.getByRole('button', { name: '激活账号', exact: true }).waitFor();
    const actions = report.publicAuthContract?.data?.pages?.login?.page_orchestration?.action_schema?.actions;
    check('login: activation has public execution target', actions?.open_account_activation?.target?.path === '/activate-account');
    check('login: declared recovery entry is present', await page.getByRole('button', { name: '忘记密码', exact: true }).count() === 1);
    check('login: heading consumes public brand identity', (await page.getByRole('heading', { level: 1 }).innerText()).includes(report.publicAuthContract.data.pages.login.texts.brand_name));
    await page.screenshot({ animations: 'disabled', path: path.join(out, 'login-public-authority.png') });
  }
  await inputs.nth(0).fill(role);
  await inputs.nth(1).fill(process.env.SC_ACCEPTANCE_FIXTURE_PASSWORD);
  if (await inputs.count() > 2 && await inputs.nth(2).isEnabled()) await inputs.nth(2).fill('sc_frontend_acceptance');
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 60000 });
  await page.locator('.layout-shell').waitFor();
  return { page, ctx };
}

async function list(page, menu, name) {
  await page.goto(`${base}/m/${menu}`);
  await page.locator('[data-list-card-container="official"]').waitFor();
  check(`${name}: standard type`, await page.locator('[data-list-composition-reason="contract-collection-view"]').count() === 1);
  check(`${name}: one container`, await page.locator('[data-list-card-container="official"]').count() === 1);
  await page.screenshot({ animations: 'disabled', path: path.join(out, `${name}.png`) });
}

async function form(page, url, name, profile = 'form') {
  await page.goto(`${base}${url}`);
  // Readiness follows the mode the contract declared for this page, never one
  // assumed composition. An editable record waits for the adopted form engine;
  // a readonly record waits for the page to publish the readonly detail
  // composition the contract declared. Demanding the editable engine on a
  // readonly record would require a mode the same contract cannot declare at
  // the same time, so the probe would hang on a page that is behaving correctly.
  await page.locator(profile === 'readonly'
    ? '[data-product-page-mode="form"][data-state="ok"][data-detail-composition="official-standard-detail"][data-detail-composition-reason="contract-readonly-record-view"]'
    : '[data-form-composition="official-standard-form"][data-state="ok"]').waitFor();
  check(`${name}: no unknown renderer`, await page.locator('[data-field-fail-closed]').count() === 0);
  if (profile === 'readonly') {
    check(`${name}: readonly mode published`, await page.locator('[data-semantic-component="ContractFormProductHeader"][data-state="readonly"]').count() === 1);
    check(`${name}: no editable form composition`, await page.locator('[data-form-composition="official-standard-form"]').count() === 0);
    // "The form engine is not mounted" is not the same claim as "no part of the
    // record is presented as editable": a readonly record could still be framed
    // by an editable section without ever mounting the engine. Assert the
    // sections themselves, so the readonly profile cannot hide an edit surface
    // behind the facts layout.
    check(`${name}: no editable record section`, await page.locator('[data-detail-section-reason][data-state="editable"]').count() === 0);
    check(`${name}: nonzero official facts`, await page.locator('[data-detail-facts="official-standard-detail"]').count() > 0);
    check(`${name}: readonly detail adopted`, await page.locator('[data-detail-composition="official-standard-detail"]').count() === 1);
    const collections = page.locator('[data-field-type="one2many"], [data-field-type="many2many"], [data-field-type="binary"]');
    const count = await collections.count();
    if (name === 'payment-readonly') check('payment readonly: nonzero detail collection', await page.locator('[data-field-type="one2many"]').count() > 0);
    for (let index = 0; index < count; index += 1) {
      check(`${name}: collection remains outside descriptions`, await collections.nth(index).locator('xpath=ancestor::*[@data-detail-facts="official-standard-detail"]').count() === 0);
    }
    report.detailSections ??= {};
    report.detailSections[name] = await page.locator('[data-detail-section-reason]').evaluateAll((nodes) => nodes.map((node) => node.getAttribute('data-detail-section-reason')));
  } else {
    check(`${name}: official form engine mounted`, await page.locator('[data-semantic-component="ScForm"]').count() > 0);
  }
  await page.screenshot({ animations: 'disabled', path: path.join(out, `${name}.png`) });
}

async function favoritesScope() {
  const finance = await login('fixture_role_finance');
  const page = finance.page;
  const failureProbe = process.env.TPL07_SCOPE === 'favorites-failure';
  let signalRequest;
  let releaseRequest;
  let requestStarted;
  if (failureProbe) {
    report.injectedFavoriteFailures = [];
    await page.route('**/api/v1/intent*', async (route) => {
      const body = route.request().postDataJSON();
      if (body?.intent !== 'search.favorite.set') return route.fallback();
      report.injectedFavoriteFailures.push({ model: body.params.model, shared: body.params.is_shared });
      let settled = false;
      let resume;
      const abort = async () => {
        if (settled) return;
        settled = true;
        try { await route.abort('failed'); }
        finally { resume?.(); pendingProbeAborts.delete(abort); }
      };
      pendingProbeAborts.add(abort);
      const waiting = new Promise((resolve) => { resume = resolve; releaseRequest = resolve; });
      signalRequest();
      await waiting;
      return abort();
    });
  }
  await list(page, 545, 'favorites-list');
  const authority = report.savedSearchAuthority;
  check('favorites: effective contract declares capability', typeof authority?.save_enabled === 'boolean');
  check('favorites: authorized fixture can exercise save form', authority.save_enabled === true && authority.intent === 'search.favorite.set');
  const menu = page.getByRole('button', { name: '展开搜索菜单', exact: true });
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: width === 1440 ? 900 : 844 });
    await menu.click();
    const entry = page.getByRole('button', { name: authority.label, exact: true });
    check(`favorites-${width}: declared save entry is available`, await entry.isEnabled());
    await entry.click();
    const name = page.getByPlaceholder('收藏名称', { exact: true });
    await name.waitFor();
    check(`favorites-${width}: sharing follows declared capability`, await page.getByRole('checkbox', { name: '共享给所有用户', exact: true }).count() === (authority.shared_enabled === true ? 1 : 0));
    await name.fill('仅检查表单，不保存');
    const save = page.getByRole('button', { name: /^保存/ });
    await save.scrollIntoViewIfNeeded();
    check(`favorites-${width}: named save form is usable`, await save.isEnabled());
    check(`favorites-${width}: save action can enter viewport`, await save.evaluate((el) => { const box = el.getBoundingClientRect(); return box.top >= 0 && box.bottom <= innerHeight; }));
    if (failureProbe) {
      requestStarted = new Promise((resolve) => { signalRequest = resolve; });
      await save.click();
      let requestDeadline;
      try {
        await Promise.race([requestStarted, new Promise((_, reject) => { requestDeadline = setTimeout(() => reject(new Error('favorite request did not start')), 15000); })]);
      } finally { clearTimeout(requestDeadline); }
      check(`favorites-${width}: saving prevents duplicate submission`, await save.isDisabled());
      check(`favorites-${width}: pending input is stable`, await name.isDisabled());
      releaseRequest();
      await page.getByRole('alert').filter({ hasText: '收藏保存未完成' }).waitFor();
      check(`favorites-${width}: failure retains input`, await name.inputValue() === '仅检查表单，不保存');
      check(`favorites-${width}: failure permits retry`, await save.isEnabled());
      check(`favorites-${width}: no sharing escalation`, report.injectedFavoriteFailures.at(-1).shared === false);
    }
    await page.screenshot({ animations: 'disabled', path: path.join(out, `favorites-${width}.png`) });
    await page.getByRole('button', { name: '取消', exact: true }).click();
    await name.waitFor({ state: 'detached' });
    await page.keyboard.press('Escape');
    check(`favorites-${width}: escape restores search control`, await menu.evaluate((el) => el === document.activeElement));
    check(`favorites-${width}: no page overflow`, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
  }
  check('favorites: real startup authority present', report.startup.some((r) => r.intent === 'system.init' && r.success));
  await finance.ctx.close();
}

async function navigationScope() {
  const finance = await login('fixture_role_finance');
  const page = finance.page;
  await list(page, 545, 'navigation-desktop');
  check('navigation: desktop keeps one official aside', await page.locator('[data-navigation-driver="official-aside"]').count() === 1);
  check('navigation: runtime product version is declared', typeof report.productVersion === 'string' && report.productVersion.length > 0);
  check('navigation: expanded footer consumes runtime version', (await page.locator('[data-product-version]').innerText()).trim() === `版本 ${report.productVersion}`);
  const before = new URL(page.url()).pathname;
  await page.setViewportSize({ width: 390, height: 844 });
  const toggle = page.getByRole('button', { name: '菜单', exact: true });
  await toggle.click();
  const dialog = page.getByRole('dialog', { name: '主导航', exact: true });
  await dialog.waitFor();
  check('navigation: mobile footer preserves runtime version', (await dialog.locator('[data-product-version]').innerText()).trim() === `版本 ${report.productVersion}`);
  check('navigation: mobile version fits drawer', await dialog.locator('[data-product-version]').evaluate((el) => { const box = el.getBoundingClientRect(); return box.right <= innerWidth && box.bottom <= innerHeight; }));
  check('navigation: exactly one dialog', await page.getByRole('dialog').count() === 1);
  check('navigation: official drawer owns the navigation', await dialog.locator('[data-navigation-driver="official-drawer"]').count() === 1);
  check('navigation: private mask exited', await page.locator('.mobile-sidebar-backdrop').count() === 0);
  check('navigation: authorized current menu retained', await dialog.getByText('付款申请', { exact: true }).count() > 0);
  await page.keyboard.press('Tab');
  check('navigation: focus remains in drawer', await dialog.evaluate((el) => el.contains(document.activeElement)));
  await page.screenshot({ animations: 'disabled', path: path.join(out, 'navigation-mobile-open.png') });
  await page.keyboard.press('Escape');
  await dialog.waitFor({ state: 'detached' });
  check('navigation: escape restores opener', await toggle.evaluate((el) => el === document.activeElement));
  check('navigation: closing preserves route', new URL(page.url()).pathname === before);
  check('navigation: scroll lock released', await page.evaluate(() => document.body.style.overflow !== 'hidden'));
  await toggle.click();
  await dialog.waitFor();
  await page.mouse.click(385, 420);
  await dialog.waitFor({ state: 'detached' });
  check('navigation: official backdrop dismisses', await page.getByRole('dialog').count() === 0);
  await page.setViewportSize({ width: 1440, height: 900 });
  check('navigation: desktop restored without duplicate navigation', await page.locator('[data-navigation-driver="official-aside"]').count() === 1 && await page.locator('#primary-sidebar').count() === 1);
  check('navigation: real startup authority present', report.startup.some((r) => r.intent === 'system.init' && r.success));
  await finance.ctx.close();
}

async function styleScope() {
  const family = process.env.TPL52_FAMILY || 'all';
  assert.ok(['all', 'shell', 'collection', 'detail', 'form', 'overlay'].includes(family), 'known style family');
  report.styleFamily = family;
  const finance = await login('fixture_role_finance');
  const page = finance.page;
  const tokenSources = await Promise.all([
    'frontend/apps/web/src/styles/tokens/semantic.css',
    'frontend/apps/web/src/styles/tokens/component.css',
    'frontend/apps/web/src/styles/tokens/pattern.css',
  ].map((file) => fs.readFile(path.join(root, file), 'utf8')));
  const tokenNames = [...new Set(tokenSources.flatMap((text) => [...text.matchAll(/(--sc-[\w-]+)\s*:/g)].map((m) => m[1])))];
  tokenNames.push('--sc-semantic-text-disabled', '--sc-font-title-large', '--sc-font-title-medium');
  report.styles = [];
  const titleRole = await page.evaluate(() => {
    const probe = document.createElement('span');
    probe.style.font = 'var(--sc-font-title-large)';
    document.body.append(probe);
    const style = getComputedStyle(probe);
    const result = [style.fontSize, style.fontWeight, style.lineHeight];
    probe.remove();
    return result;
  });
  check('shell: official title-large role resolves', JSON.stringify(titleRole) === JSON.stringify(['18px', '600', '26px']), { titleRole });
  async function inspect(name, headingSelector, expected) {
    const result = await page.evaluate(({ tokenNames, headingSelector }) => {
      const rootStyle = getComputedStyle(document.documentElement);
      const missing = tokenNames.filter((name) => !rootStyle.getPropertyValue(name).trim());
      const headings = [...document.querySelectorAll(headingSelector)].filter((el) => el.getClientRects().length).map((el) => {
        const s = getComputedStyle(el);
        return { text: el.textContent.trim(), size: s.fontSize, weight: s.fontWeight, line: s.lineHeight };
      });
      return { missing, headings, placeholder: rootStyle.getPropertyValue('--td-text-color-placeholder').trim(),
        muted: rootStyle.getPropertyValue('--sc-semantic-text-muted').trim(),
        contained: document.documentElement.scrollWidth <= innerWidth + 1 };
    }, { tokenNames, headingSelector });
    report.styles.push({ name, ...result });
    check(`${name}: shared token chains resolve`, result.missing.length === 0, { missing: result.missing });
    check(`${name}: placeholder uses muted role`, result.placeholder === result.muted && Boolean(result.muted));
    check(`${name}: heading rendered`, result.headings.length > 0);
    if (expected) check(`${name}: official typography`, result.headings.every((h) => h.size === expected[0] && h.weight === expected[1] && h.line === expected[2]), { headings: result.headings });
    check(`${name}: page contained`, result.contained);
    await page.screenshot({ animations: 'disabled', path: path.join(out, `${name}.png`), fullPage: true });
  }
  for (const viewport of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
    await page.setViewportSize(viewport);
    if (family !== 'overlay') {
    await list(page, 545, `style-list-${viewport.width}`);
    // This standard list intentionally suppresses the outer headline; its record
    // header keeps the pinned official headline-small ladder.
    await inspect(`shell-${viewport.width}`, '.product-page-header h1', ['24px', '600', '32px']);
    }
    if (['all', 'collection'].includes(family)) {
      const selector = viewport.width > 600 ? '.flat-table .column-sort-btn' : '.collection-mobile-record-row__identity';
      await page.locator(selector).first().waitFor();
      await inspect(`collection-cells-${viewport.width}`, selector, viewport.width > 600 ? ['14px', '600', '22px'] : ['16px', '600', '24px']);
    }
    if (['shell', 'collection'].includes(family)) continue;
    if (family === 'detail') {
      await form(page, '/r/payment.request/1813?menu_id=545&action_id=775', `style-detail-${viewport.width}`, 'readonly');
      await inspect(`detail-${viewport.width}`, '.product-page-header h1', ['24px', '600', '32px']);
      continue;
    }
    await form(page, '/f/payment.request/1813?menu_id=545&action_id=775', `style-form-${viewport.width}`);
    if (family === 'form') {
      await inspect(`form-${viewport.width}`, '.product-page-header h1', ['24px', '600', '32px']);
      continue;
    }
    await inspect(`form-text-${viewport.width}`, '.template-form-section .readonly-value:not(.readonly-value--action)', ['14px', '400', '22px']);
    const introduce = page.locator('[data-contract-entry-label]');
    check(`form-${viewport.width}: contract supplies introduce label`, Boolean(report.introduceContract?.introduceLabel));
    await introduce.click();
    await page.locator('[data-dialog-purpose="payment-settlement-introduce"]').waitFor();
    await page.getByText('正在搜索结算单', { exact: false }).waitFor({ state: 'hidden' });
    await inspect(`dialog-${viewport.width}`, '.sc-design-dialog__heading h2', ['16px', '600', '24px']);
    await page.keyboard.press('Escape');
    await page.locator('[data-dialog-purpose="payment-settlement-introduce"]').waitFor({ state: 'detached' });
    if (family === 'overlay') continue;
    await form(page, '/r/payment.request/1813?menu_id=545&action_id=775', `style-detail-${viewport.width}`, 'readonly');
    await inspect(`detail-${viewport.width}`, '.product-page-header h1', ['24px', '600', '32px']);
    await inspect(`detail-text-${viewport.width}`, '.template-form-section-descriptions .readonly-value:not(.readonly-value--action)', ['14px', '400', '22px']);
  }
  if (family === 'all') {
    const variants = await page.evaluate((names) => {
      const el = document.documentElement;
      const original = el.getAttribute('data-sc-theme');
      try {
        return ['light', 'dark'].map((theme) => {
          el.setAttribute('data-sc-theme', theme);
          const s = getComputedStyle(el);
          return { theme, missing: names.filter((name) => !s.getPropertyValue(name).trim()), disabled: s.getPropertyValue('--td-text-color-disabled').trim() };
        });
      } finally {
        if (original === null) el.removeAttribute('data-sc-theme'); else el.setAttribute('data-sc-theme', original);
      }
    }, tokenNames);
    check('style: both token variants resolve including disabled text', variants.every((v) => !v.missing.length && v.disabled), { variants });
  }
  check('style: real startup contract loaded', report.startup.some((r) => r.intent === 'system.init' && r.success));
  await finance.ctx.close();
}

try {
  if (process.env.TPL07_SCOPE === 'expense-policy') {
    const admin = await login('fixture_role_config_admin');
    const resolveEntry = (xmlid) => {
      const entries = ['primary_actions', 'role_home_actions', 'contextual_actions', 'admin_actions']
        .flatMap((key) => report.routeAuthority?.[key] || []).filter((row) => row.menu_xmlid === xmlid);
      assert.equal(entries.length, 1, `one authorized entry: ${xmlid}`);
      assert.ok(Number(entries[0].menu_id) > 0 && Number(entries[0].action_id) > 0);
      return entries[0];
    };
    const categoryEntry = resolveEntry('smart_construction_core.menu_sc_business_category');
    const request = (params) => admin.page.evaluate(async (params) => {
      const token = Object.entries(sessionStorage).find(([key]) => key.startsWith('sc_auth_token:'))?.[1];
      const response = await fetch('/api/v1/intent?db=sc_frontend_acceptance', {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}`, 'X-Odoo-DB': 'sc_frontend_acceptance' },
        body: JSON.stringify({ intent: 'api.data', params }),
      });
      return response.json();
    }, params);
    const found = await request({ op: 'list', model: 'sc.business.category',
      domain: [['code', '=', 'finance.expense.reimbursement'], ['active', '=', true]],
      fields: ['id', 'code', 'attachment_policy'], limit: 2 });
    assert.equal(found.ok, true);
    assert.equal(found.data?.records?.length, 1);
    const baseline = found.data.records[0];
    assert.equal(baseline.attachment_policy, 'required');
    const read = async () => {
      const result = await request({ op: 'read', model: 'sc.business.category', ids: [baseline.id], fields: ['id', 'code', 'attachment_policy'] });
      assert.equal(result.ok, true);
      assert.equal(result.data?.records?.length, 1);
      return result.data.records[0];
    };
    const recovery = { database: 'sc_frontend_acceptance', role: 'fixture_role_config_admin', baseline, restored: false };
    const recoveryPath = path.join(out, 'expense-policy-recovery.json');
    await fs.writeFile(recoveryPath, JSON.stringify(recovery, null, 2));
    report.expensePolicy = recovery;
    const finance = await login('fixture_role_finance');
    const expenseEntry = resolveEntry('smart_construction_core.menu_sc_reimbursement_request');
    const observe = async (value, stage) => {
      const start = report.contractResponses?.length || 0;
      await form(finance.page, `/f/sc.expense.claim/new?menu_id=${expenseEntry.menu_id}&action_id=${expenseEntry.action_id}`, `expense-policy-${stage}`);
      const authority = (report.contractResponses || []).slice(start).map((row) => findRecordAuthority(row.contract))
        .findLast((row) => row?.model === 'sc.expense.claim' && !Number(row.mainData?.id));
      check(`policy ${stage}: effective contract value`, authority?.mainData?.submission_attachment_policy === value);
      await finance.page.getByRole('button', { name: '提交审批', exact: true }).click();
      const message = value === 'required' ? '当前业务分类要求上传附件后才能提交、批准或完成。' : '请先补充必填信息，再保存草稿或提交。';
      await finance.page.getByText(message, { exact: true }).first().waitFor();
      check(`policy ${stage}: submission feedback`, true);
      await finance.page.screenshot({ path: path.join(out, `expense-policy-${stage}-feedback.png`) });
    };
    const change = async (value, label) => {
      const start = report.contractResponses?.length || 0;
      await form(admin.page, `/f/sc.business.category/${baseline.id}?menu_id=${categoryEntry.menu_id}&action_id=${categoryEntry.action_id}`, `expense-policy-admin-${value}`);
      const authority = (report.contractResponses || []).slice(start).map((row) => findRecordAuthority(row.contract))
        .findLast((row) => row?.model === 'sc.business.category' && Number(row.mainData?.id) === baseline.id);
      const save = authority?.actions?.actionRuleList?.find((row) => row.actionSemantics?.purpose === 'save_draft');
      check('policy: authorized save action', save?.enabled === true && save.target?.operation === 'write');
      await admin.page.locator('[data-field-name="attachment_policy"] input').click();
      await admin.page.locator('li.t-select-option:visible').filter({ hasText: label }).click();
      expensePolicyPermit = { id: baseline.id, value };
      const response = admin.page.waitForResponse((res) => {
        try { const body = res.request().postDataJSON(); return body?.intent === 'api.data' && body.params?.op === 'write'; } catch { return false; }
      });
      const [saved] = await Promise.all([response, admin.page.getByRole('button', { name: save.label, exact: true }).click()]);
      assert.equal((await saved.json()).ok, true);
      check(`policy ${value}: authoritative readback`, (await read()).attachment_policy === value);
    };
    try {
      await observe('required', 'before');
      await change('recommended', '建议上传');
      await observe('recommended', 'changed');
      await change('required', '必须上传');
      await observe('required', 'restored');
    } finally {
      expensePolicyPermit = null;
      const current = await read();
      assert.equal(current.code, baseline.code);
      assert.ok(['required', 'recommended'].includes(current.attachment_policy), 'external configuration change; refuse overwrite');
      if (current.attachment_policy !== baseline.attachment_policy) {
        expensePolicyPermit = { id: baseline.id, value: baseline.attachment_policy };
        const restored = await request({ op: 'write', model: 'sc.business.category', ids: [baseline.id], vals: { attachment_policy: baseline.attachment_policy } });
        assert.equal(restored.ok, true);
      }
      expensePolicyPermit = null;
      assert.deepEqual(await read(), baseline);
      recovery.restored = true;
      await fs.writeFile(recoveryPath, JSON.stringify(recovery, null, 2));
      check('policy: baseline restored', true);
    }
    await finance.ctx.close();
    await admin.ctx.close();
  } else if (['favorite-lifecycle', 'favorite-lifecycle-resume', 'favorite-active-delete', 'favorite-active-delete-resume'].includes(process.env.TPL07_SCOPE)) {
    const finance = await login('fixture_role_finance');
    const page = finance.page;
    await list(page, 545, 'favorite-lifecycle-list');
    async function readFavorite() {
      const response = await page.evaluate(async (name) => {
        const token = Object.entries(sessionStorage).find(([key]) => key.startsWith('sc_auth_token:'))?.[1];
        return (await fetch('/api/v1/intent?db=sc_frontend_acceptance', {
          method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}`, 'X-Odoo-DB': 'sc_frontend_acceptance' },
          body: JSON.stringify({ intent: 'api.data', params: { op: 'list', model: 'ir.filters', fields: ['id', 'name', 'user_id', 'model_id', 'action_id', 'is_default'], domain: [['name','=',name],['user_id','=',30],['model_id','=','payment.request'],['action_id','=',775]], limit: 2 } }),
        })).json();
      }, lifecycleName);
      check('favorite lifecycle: authoritative query succeeds', response.ok === true && Array.isArray(response.data?.records));
      return response.data.records;
    }
    const baseline = await readFavorite();
    const resuming = ['favorite-lifecycle-resume', 'favorite-active-delete-resume'].includes(process.env.TPL07_SCOPE);
    if (resuming) {
      const originalPath = process.env.TPL07_SCOPE === 'favorite-active-delete-resume'
        ? 'artifacts/frontend-web-fix-20260928/tpl07-1790769721849/report.json'
        : 'artifacts/frontend-web-fix-20260928/tpl07-1790769469765/report.json';
      const original = JSON.parse(await fs.readFile(path.join(root, originalPath)));
      const created = original.favoriteCreated?.[0];
      check('favorite lifecycle: resume exact previously observed private record', original.favoriteSaved?.ok === true
        && created?.id === original.favoriteSaved?.data?.id && baseline.length === 1 && JSON.stringify(baseline[0]) === JSON.stringify(created));
      report.carriedForwardSave = originalPath;
    } else check('favorite lifecycle: named private configuration initially absent', baseline.length === 0);
    check('favorite lifecycle: explicit save authority', report.savedSearchAuthority?.save_enabled === true);
    const menu = page.getByRole('button', { name: '展开搜索菜单', exact: true });
    let id = baseline[0]?.id;
    await menu.click();
    if (!resuming) {
    await page.getByRole('button', { name: report.savedSearchAuthority.label, exact: true }).click();
    const name = page.getByPlaceholder('收藏名称', { exact: true });
    await name.fill(lifecycleName);
    favoriteWritePermit = { intent: 'search.favorite.set' };
    const saveResponse = page.waitForResponse((response) => response.request().postData()?.includes('search.favorite.set'), { timeout: 15000 });
    await page.getByRole('button', { name: /^保存/ }).click();
    const saved = await (await saveResponse).json();
    report.favoriteSaved = saved;
    check('favorite lifecycle: server accepted save', saved.ok === true && Number(saved.data?.id) > 0);
    const rows = await readFavorite();
    report.favoriteCreated = rows;
    check('favorite lifecycle: exact private nondefault record read back', rows.length === 1 && rows[0].id === saved.data.id && rows[0].is_default === false);
    id = rows[0].id;
    await name.waitFor({ state: 'detached' });
    }
    // The menu stays open after saving; the refreshed contract supplies deletion.
    const deleteButton = page.getByRole('button', { name: `删除收藏：${lifecycleName}`, exact: true });
    await deleteButton.waitFor();
    check('favorite lifecycle: refreshed menu supplies product delete action', await deleteButton.isEnabled());
    await page.reload();
    await page.locator('[data-list-card-container="official"]').waitFor();
    await menu.click();
    await deleteButton.waitFor();
    check('favorite lifecycle: reload retains saved item and deletion grant', await deleteButton.isEnabled());
    const activeDeletion = process.env.TPL07_SCOPE.startsWith('favorite-active-delete');
    if (activeDeletion) {
      await page.getByRole('button', { name: lifecycleName, exact: true }).click();
      await page.waitForURL((url) => url.searchParams.get('saved_filter') === lifecycleName);
      await menu.click();
      check('favorite lifecycle: saved filter can be applied', await page.locator('[aria-pressed]').filter({ hasText: lifecycleName }).evaluateAll((nodes) => nodes.length > 0 && nodes.every((node) => node.getAttribute('aria-pressed') === 'true')));
    }
    for (const width of activeDeletion ? [390] : [1440, 390]) {
      await page.setViewportSize({ width, height: width === 1440 ? 900 : 844 });
      if (!(await deleteButton.isVisible())) await menu.click();
      await deleteButton.click();
      const dialog = page.getByRole('dialog', { name: '删除收藏', exact: true });
      await dialog.waitFor();
      check(`favorite-${width}: official confirmation`, await dialog.getAttribute('data-semantic-driver') === 'tdesign-dialog');
      check(`favorite-${width}: deletion scope explained`, (await dialog.innerText()).includes('不删除业务记录'));
      check(`favorite-${width}: confirmation fits viewport`, await dialog.evaluate((el) => { const r = el.getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth; }));
      await page.screenshot({ animations: 'disabled', path: path.join(out, `favorite-delete-${width}.png`) });
      await dialog.getByRole('button', { name: '取消', exact: true }).click();
      await dialog.waitFor({ state: 'detached' });
    }
    check('favorite lifecycle: cancel preserved exact record', (await readFavorite())[0]?.id === id);
    await menu.click();
    await deleteButton.click();
    const dialog = page.getByRole('dialog', { name: '删除收藏', exact: true });
    favoriteWritePermit = { intent: 'search.favorite.delete', id, abort: true };
    await dialog.getByRole('button', { name: '确认删除', exact: true }).click();
    await dialog.getByRole('alert').waitFor();
    check('favorite lifecycle: failed deletion retains confirmation', await dialog.isVisible());
    check('favorite lifecycle: failed deletion preserved record', (await readFavorite())[0]?.id === id);
    favoriteWritePermit = { intent: 'search.favorite.delete', id };
    const deleteResponse = page.waitForResponse((response) => response.request().postData()?.includes('search.favorite.delete'), { timeout: 15000 });
    await dialog.getByRole('button', { name: '确认删除', exact: true }).click();
    const deleted = await (await deleteResponse).json();
    report.favoriteDeleted = deleted;
    check('favorite lifecycle: server confirms exact deletion', deleted.ok === true && deleted.data?.deleted === true && deleted.data?.id === id);
    await dialog.waitFor({ state: 'detached' });
    check('favorite lifecycle: authoritative state restored', (await readFavorite()).length === 0);
    if (activeDeletion) {
      await page.waitForURL((url) => !url.searchParams.get('saved_filter'));
      check('favorite lifecycle: deleting selected filter clears route state', !new URL(page.url()).searchParams.get('saved_filter'));
    }
    check('favorite lifecycle: refreshed menu removed deleted entry', await deleteButton.count() === 0);
    await page.reload();
    await page.locator('[data-list-card-container="official"]').waitFor();
    await menu.click();
    check('favorite lifecycle: reload retains restoration', await page.getByText(lifecycleName, { exact: true }).count() === 0);
    await finance.ctx.close();
  } else if (process.env.TPL07_SCOPE === 'task-authority') {
    const finance = await login('fixture_role_finance');
    await form(finance.page, '/f/payment.request/1813?menu_id=545&action_id=775', 'task-authority');
    const authority = report.taskAuthorities?.['payment.request'];
    check('task: actual payment authority received', authority?.model === 'payment.request');
    check('task: native tree is sole layout authority', authority.structure?.layoutPolicy === 'container_tree_authority');
    check('task: retired slots remain empty', Array.isArray(authority.structure?.slots) && authority.structure.slots.length === 0);
    check('task: effective native tree is present', Boolean(authority.layout?.containerTree));
    const matrix = JSON.parse(await fs.readFile(path.join(root, 'config/p1_payment_request_field_completeness_v1.json')));
    const rules = matrix.field_rules.filter((row) => row.model === 'payment.request' && row.surfaces.some((surface) => ['edit', 'create_edit'].includes(surface)));
    check('task: existing P1 field responsibilities are nonempty', rules.length > 0);
    const fieldReferences = new Set(Object.keys(authority.mainData || {}));
    function collectFieldReferences(node) {
      if (!node || typeof node !== 'object') return;
      if (node.fieldCode) fieldReferences.add(node.fieldCode);
      if (node.type === 'field' && node.name) fieldReferences.add(node.name);
      for (const child of Object.values(node)) collectFieldReferences(child);
    }
    collectFieldReferences(authority.layout.containerTree);
    for (const field of Object.keys(authority.structure.sourceAuthority?.governance_source?.fieldSemanticRoles || {})) fieldReferences.add(field);
    // The P1 native payment view explicitly removes this duplicate heading
    // field; business_category_id remains the authoritative handling input.
    const retiredDuplicateFields = ['payment_flow_label'];
    const missingDeclarations = rules.filter((row) => !fieldReferences.has(row.field) && !retiredDuplicateFields.includes(row.field)).map((row) => row.field);
    report.taskFieldCoverage = { ruleCount: rules.length, missingDeclarations, retiredDuplicateFields };
    check('task: P1 handling fields declared by contract', missingDeclarations.length === 0, { missingDeclarations });
    // Only unconditional required user inputs are asserted unconditionally.
    // Conditional facts keep their backend modifiers; no inferred applicability.
    for (const row of rules.filter((row) => row.classification === 'required' && row.applicability === 'always')) {
      check(`task: required ${row.field} visible`, await finance.page.locator(`[data-field-name="${row.field}"]`).first().isVisible());
    }
    check('task: attachment input retained', await finance.page.locator('[data-field-name="attachment_ids"]').first().isVisible());
    const trace = finance.page.locator('[data-group-title="履约与追溯"]').first();
    await trace.getByRole('button', { name: '履约与追溯', exact: true }).click();
    check('task: declared trace section can expand', await trace.getAttribute('data-collapsed') === 'false');
    check('task: existing record supplies conditional contract and settlement', Boolean(authority.mainData.contract_id && authority.mainData.settlement_id));
    const applicableFacts = rules.filter((row) => ['contract_selected', 'settlement_selected'].includes(row.applicability));
    check('task: conditional fact scope is nonempty', applicableFacts.length > 0);
    for (const row of applicableFacts) {
      check(`task: applicable ${row.field} visible`, await finance.page.locator(`[data-field-name="${row.field}"]`).first().isVisible());
    }
    check('task: pay record does not expose receipt-only notebook', await trace.getByText('收款发票明细', { exact: true }).count() === 0);
    report.traceControls = await trace.evaluate((el) => ({ text: el.innerText, controls: [...el.querySelectorAll('[role],button')].map((node) => ({ tag: node.tagName, role: node.getAttribute('role'), text: node.textContent?.trim() })) }));
    await finance.page.screenshot({ animations: 'disabled', path: path.join(out, 'trace-before-tabs.png') });
    await trace.getByText('付款记录', { exact: true }).click();
    check('task: declared payment relation is reachable', await trace.locator('[data-field-name="ledger_line_ids"]').isVisible());
    await trace.getByText('历史金额确认', { exact: true }).click();
    const historical = trace.locator('[data-field-name="accepted_amount_uppercase"]');
    check('task: historical fact is reachable', await historical.isVisible());
    check('task: historical fact remains readonly', await historical.locator('input, textarea').count() === 0);
    check('task: historical empty text follows declared semantics', (await historical.innerText()).includes('无历史确认记录'));
    await trace.getByText('结算与来源匹配', { exact: true }).click();
    check('task: trace return restores settlement facts', await trace.locator('[data-field-name="paid_amount_total"]').isVisible());
    report.taskPresentation = [];
    for (const width of [1440, 390]) {
      await finance.page.setViewportSize({ width, height: width === 1440 ? 900 : 844 });
      report.taskPresentation.push(await finance.page.evaluate(() => ({
        width: innerWidth,
        fields: [...document.querySelectorAll('[data-field-name]')].map((el) => ({
          name: el.getAttribute('data-field-name'), visible: Boolean(el.getClientRects().length),
        })),
        groups: [...document.querySelectorAll('[data-group-title]')].map((el) => ({
          title: el.getAttribute('data-group-title'), columns: getComputedStyle(el).gridTemplateColumns,
          width: el.getBoundingClientRect().width,
        })),
      })));
      const geometry = await finance.page.evaluate(() => {
        const first = document.querySelector('[data-field-name="project_id"]')?.getBoundingClientRect();
        const second = document.querySelector('[data-field-name="partner_id"]')?.getBoundingClientRect();
        return first && second ? { first: { x: first.x, y: first.y }, second: { x: second.x, y: second.y } } : null;
      });
      check(`task-${width}: responsive field geometry`, Boolean(geometry) && (width > 600
        ? Math.abs(geometry.first.y - geometry.second.y) < 2 && geometry.second.x > geometry.first.x
        : Math.abs(geometry.first.x - geometry.second.x) < 2 && geometry.second.y > geometry.first.y), { geometry });
      check(`task-${width}: one official form composition`, await finance.page.locator('[data-form-composition="official-standard-form"]').count() === 1);
      check(`task-${width}: no page overflow`, await finance.page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
      await finance.page.screenshot({ animations: 'disabled', path: path.join(out, `task-authority-${width}.png`), fullPage: true });
    }
    check('task: startup authority loaded', report.startup.some((row) => row.intent === 'system.init' && row.success));
    await finance.ctx.close();
  } else if (process.env.TPL07_SCOPE === 'approval-actions') {
    report.approvalPages = [];
    check('approval scope: supported model selection', !process.env.TPL07_APPROVAL_MODEL || ['sc.expense.claim', 'sc.settlement.adjustment', 'sc.receipt.income', 'sc.financing.loan', 'sc.self.funding.registration', 'sc.treasury.reconciliation', 'sc.output.invoice.adjustment', 'tender.guarantee', 'sc.project.document', 'tender.doc.purchase', 'payment.request', 'sc.contract.event', 'sc.payment.execution', 'sc.plan', 'sc.plan.report', 'sc.construction.diary', 'project.task', 'project.project', 'sc.material.inbound', 'sc.material.acceptance', 'sc.material.purchase.request', 'sc.material.rfq', 'sc.material.settlement', 'sc.equipment.plan', 'sc.equipment.request', 'sc.equipment.usage', 'sc.equipment.settlement', 'sc.labor.plan', 'sc.labor.request', 'sc.material.rental.plan', 'sc.material.rental.order', 'sc.material.rental.settlement', 'sc.safety.plan', 'sc.safety.disclosure', 'sc.subcontract.plan', 'sc.subcontract.request', 'sc.subcontract.settlement', 'sc.attendance.checkin', 'sc.labor.usage', 'sc.labor.settlement'].includes(process.env.TPL07_APPROVAL_MODEL));
    for (const spec of [
      { role: 'fixture_role_pm', model: 'sc.material.inbound', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.material.acceptance', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.material.purchase.request', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.material.rfq', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.project.document', domain: [] },
      { role: 'fixture_role_pm', model: 'tender.doc.purchase', domain: [] },
      { role: 'fixture_role_pm', model: 'tender.guarantee', domain: [] },
      { role: 'fixture_role_project_a_member', model: 'sc.settlement.adjustment', domain: [] },
      { role: 'fixture_role_finance', model: 'sc.expense.claim', domain: [['source_origin', '!=', 'legacy']] },
      { role: 'fixture_role_finance', model: 'sc.receipt.income', domain: [] },
      { role: 'fixture_role_finance', model: 'sc.financing.loan', domain: [] },
      { role: 'fixture_role_finance', model: 'sc.self.funding.registration', domain: [] },
      { role: 'fixture_role_finance', model: 'sc.treasury.reconciliation', domain: [] },
      { role: 'fixture_role_finance', model: 'sc.output.invoice.adjustment', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.material.settlement', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.equipment.plan', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.equipment.request', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.equipment.usage', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.equipment.settlement', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.labor.plan', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.labor.request', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.material.rental.plan', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.material.rental.order', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.material.rental.settlement', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.safety.plan', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.safety.disclosure', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.subcontract.plan', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.subcontract.request', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.subcontract.settlement', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.attendance.checkin', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.labor.usage', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.labor.settlement', domain: [] },
      { role: 'fixture_role_pm', model: 'project.project', stateField: 'lifecycle_state', fields: ['sc_approval_state'], domain: [] },
      { role: 'fixture_role_pm', model: 'project.task', stateField: 'sc_state', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.plan', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.plan.report', domain: [] },
      { role: 'fixture_role_pm', model: 'sc.construction.diary', domain: [] },
      { role: 'fixture_role_contract_operator', model: 'sc.contract.event', domain: [] },
      { role: 'fixture_role_finance', model: 'payment.request', domain: [] },
      { role: 'fixture_role_finance', model: 'sc.payment.execution', domain: [['state', '=', 'paid']] },
    ].filter((spec) => !process.env.TPL07_APPROVAL_MODEL || spec.model === process.env.TPL07_APPROVAL_MODEL)) {
      const executionLabels = {
        'sc.equipment.usage': ['登记单号', '确认台班'],
        'sc.equipment.settlement': ['结算单号', '确认结算'],
        'sc.attendance.checkin': ['考勤单号', '确认考勤'],
        'sc.labor.usage': ['用工单号', '确认用工'],
        'sc.labor.settlement': ['结算单号', '确认结算'],
      }[spec.model];
      const session = await login(spec.role);
      if (process.env.TPL07_APPROVAL_VIEW === 'create') {
        check('approval create scope: explicit supported form', ['sc.contract.event', 'sc.expense.claim', 'sc.settlement.adjustment', 'sc.receipt.income', 'sc.financing.loan', 'sc.self.funding.registration', 'sc.treasury.reconciliation', 'sc.output.invoice.adjustment', 'tender.guarantee', 'sc.project.document', 'tender.doc.purchase', 'payment.request', 'sc.plan', 'sc.plan.report', 'sc.construction.diary', 'project.task', 'project.project', 'sc.material.inbound', 'sc.material.acceptance', 'sc.material.purchase.request', 'sc.material.rfq', 'sc.material.settlement', 'sc.equipment.plan', 'sc.equipment.request', 'sc.equipment.usage', 'sc.equipment.settlement', 'sc.labor.plan', 'sc.labor.request', 'sc.material.rental.plan', 'sc.material.rental.order', 'sc.material.rental.settlement', 'sc.safety.plan', 'sc.safety.disclosure', 'sc.subcontract.plan', 'sc.subcontract.request', 'sc.subcontract.settlement', 'sc.attendance.checkin', 'sc.labor.usage', 'sc.labor.settlement'].includes(spec.model));
        report.recordAuthority = null;
        const createResponseStart = report.contractResponses?.length || 0;
        let createContext = '';
        if (spec.model === 'project.project') {
          const entries = ['primary_actions', 'role_home_actions', 'contextual_actions', 'admin_actions']
            .flatMap((key) => report.routeAuthority?.[key] || []);
          const matches = entries.filter((row) => row.menu_xmlid === 'smart_construction_core.menu_sc_project_initiation');
          report.projectCreateEntryResolution = { role: spec.role, requestedMenuXmlid: 'smart_construction_core.menu_sc_project_initiation', matches, availableProjectEntries: entries.filter((row) => row.model === 'project.project') };

          check('project create: one authorized initiation entry', matches.length === 1 && Number(matches[0].menu_id) > 0 && Number(matches[0].action_id) > 0);
          report.approvalCreateEntry = matches[0];
          createContext = `?menu_id=${Number(matches[0].menu_id)}&action_id=${Number(matches[0].action_id)}`;
        }
        if (spec.model === 'sc.expense.claim') {
          const entries = ['primary_actions', 'role_home_actions', 'contextual_actions', 'admin_actions']
            .flatMap((key) => report.routeAuthority?.[key] || []);
          const matches = entries.filter((row) => row.menu_xmlid === 'smart_construction_core.menu_sc_reimbursement_request');
          check('expense create: one authorized reimbursement entry', matches.length === 1 && Number(matches[0].menu_id) > 0 && Number(matches[0].action_id) > 0);
          report.approvalCreateEntry = matches[0];
          createContext = `?menu_id=${Number(matches[0].menu_id)}&action_id=${Number(matches[0].action_id)}`;
        }
        if (diarySaveProbe || eventSaveProbe || ['sc.plan', 'sc.plan.report'].includes(spec.model)) {
          const entries = ['primary_actions', 'role_home_actions', 'contextual_actions', 'admin_actions']
            .flatMap(key => report.routeAuthority?.[key] || []);
          const entryXmlid = spec.model === 'sc.plan.report' ? 'smart_construction_core.menu_sc_plan_report'
            : spec.model === 'sc.plan' ? 'smart_construction_core.menu_sc_plan'
            : eventSaveProbe ? 'smart_construction_core.menu_sc_contract_event' : 'smart_construction_core.menu_sc_construction_diary';
          const matches = entries.filter(row => row.menu_xmlid === entryXmlid);
          check(`${spec.model}: one authorized native entry`, matches.length === 1 && Number(matches[0].menu_id) > 0 && Number(matches[0].action_id) > 0);
          report.approvalCreateEntry = matches[0];
          createContext = `?menu_id=${Number(matches[0].menu_id)}&action_id=${Number(matches[0].action_id)}`;
        }
        await form(session.page, `/f/${spec.model}/new${createContext}`, `${spec.model}-create`);
        // Child relation contracts may arrive last; bind the create observation
        // to the requested parent model within this navigation's responses.
        const authority = (report.contractResponses || []).slice(createResponseStart)
          .map((row) => findRecordAuthority(row.contract))
          .findLast((row) => row?.model === spec.model && !(Number(row.mainData?.id) > 0));
        check(`${spec.model}: new form effective contract`, authority?.model === spec.model);
        report.approvalPages.push({ ...spec, view: 'create', authority });
        if (spec.model === 'sc.plan') {
          for (const field of ['company_id', 'owner_id']) {
            const value = authority.mainData?.[field];
            check(`plan create: ${field} default relation label retained`, Array.isArray(value)
              && typeof value[1] === 'string' && value[1].length > 0
              && await session.page.locator(`[data-field-name="${field}"] input`).first().inputValue() === value[1]);
          }
        }
        if (eventSaveProbe) {
          report.eventCreateAuthority = authority;
          for (const field of ['name', 'project_id', 'event_type', 'description']) {
            check(`event create: ${field} has an editable native input`,
              await session.page.locator(`[data-field-name="${field}"]`).locator('input, textarea, [contenteditable="true"]').count() > 0);
          }
          const name = `TPL53-EVENT-SAVE-${Date.now()}`;
          const content = '临时验收合同履约事件：核对官方表单保存与提交恢复。';
          const projectInput = session.page.locator('[data-field-name="project_id"] input').first();
          const projectResponse = session.page.waitForResponse(response => {
            try { const body = response.request().postDataJSON(); return body?.intent === 'api.data' && body.params?.op === 'list'
              && body.params.model === 'project.project' && JSON.stringify(body.params).includes('FE Project A'); } catch { return false; }
          });
          await projectInput.fill('FE Project A');
          const projectResult = await projectResponse;
          let candidates = await projectResult.json();
          report.eventProjectQuery = { request: projectResult.request().postDataJSON(), result: candidates };
          if (candidates.ok === true && !candidates.data?.records?.length) {
            const availableResponse = session.page.waitForResponse(response => {
              try { const body = response.request().postDataJSON(); return body?.intent === 'api.data' && body.params?.op === 'list'
                && body.params.model === 'project.project' && !body.params.search_term; } catch { return false; }
            });
            await projectInput.fill('');
            const available = await availableResponse;
            candidates = await available.json();
            report.eventAvailableProjects = { request: available.request().postDataJSON(), result: candidates };
          }
          const project = candidates.data?.records?.find(row => Number(row.id) > 0);
          report.eventSelectedProject = project || null;
          check('event create: project returned in operator authorized query', candidates.ok === true && Boolean(project));
          await session.page.getByRole('option', { name: String(project.display_name || project.name), exact: true }).click();
          const nameInput = session.page.locator('[data-field-name="name"]').locator('input, textarea').first();
          const contentInput = session.page.locator('[data-field-name="description"]').locator('textarea, input').first();
          await nameInput.fill(name);
          await session.page.locator('[data-field-name="event_type"] input').first().click();
          await session.page.getByText('设计变更', { exact: true }).click();
          await contentInput.fill(content);
          eventCreateCapture = true;
          for (const label of ['保存草稿', '提交']) {
            const response = session.page.waitForResponse(response => {
              try { const body = response.request().postDataJSON(); return body?.intent === 'api.data' && body.params?.op === 'create'
                && body.params.model === 'sc.contract.event'; } catch { return false; }
            });
            await session.page.getByRole('button', { name: label, exact: true }).click();
            await response;
            await session.page.getByText('验收注入：事件保存暂不可用，请重试', { exact: true }).first().waitFor();
            const payload = report.eventSaveAttempts.at(-1);
            check(`event ${label}: actual fields and relation identity preserved`, payload.vals.project_id === project.id
              && payload.vals.name === name && payload.vals.description === content && payload.vals.event_type === 'design_change');
            check(`event ${label}: authorized context preserved`, String(payload.context?.menu_id) === String(report.approvalCreateEntry.menu_id)
              && String(payload.context?.action_id) === String(report.approvalCreateEntry.action_id) && payload.context.company_id === 8);
            check(`event ${label}: failed create retains draft`, new URL(session.page.url()).pathname === '/f/sc.contract.event/new'
              && await nameInput.inputValue() === name && await contentInput.inputValue() === content);
          }
          eventCreateCapture = false;
          check('event save: two attempts and no follow-up action', report.eventSaveAttempts.length === 2 && report.forbiddenWrites.length === 0);
          await session.page.screenshot({ path: path.join(out, 'event-filled-save-failure.png') });
          if (eventSaveSuccess) {
            eventSuccess = { model: spec.model, request: structuredClone(report.eventSaveAttempts.at(-1)), phase: 'prepare', id: null, projectId: project.id };
            await fs.writeFile(expenseRecoveryPath, JSON.stringify(eventSuccess, null, 2));
            await expenseCleanup('preflight');
            eventSuccess.phase = 'create';
            await session.page.getByRole('button', { name: '提交', exact: true }).click();
            await session.page.waitForFunction(() => !window.location.pathname.endsWith('/new'));
            check('event success: create and confirm each execute once', eventSuccess.phase === 'done'
              && JSON.stringify(report.eventSuccessWrites?.map(row => row.kind)) === JSON.stringify(['create', 'submit']));
            const saved = await session.page.evaluate(async id => {
              const token = Object.entries(sessionStorage).find(([key]) => key.startsWith('sc_auth_token:'))?.[1];
              return (await fetch('/api/v1/intent?db=sc_frontend_acceptance', {
                method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}`, 'X-Odoo-DB': 'sc_frontend_acceptance' },
                body: JSON.stringify({ intent: 'api.data', params: { op: 'read', model: 'sc.contract.event', ids: [id],
                  fields: ['id', 'state', 'project_id', 'company_id', 'name', 'description', 'event_type'], context: { company_id: 8 } } }),
              })).json();
            }, eventSuccess.id);
            report.eventSavedRecord = saved;
            const row = saved.data?.records?.[0];
            check('event success: operator authoritative record readback', saved.ok === true && row?.id === eventSuccess.id
              && row.state === 'approved' && row.project_id[0] === project.id && row.company_id[0] === 8
              && row.name === name && row.description === content && row.event_type === 'design_change');
            await form(session.page, `/f/sc.contract.event/${eventSuccess.id}${createContext}`, 'event-success-saved', 'readonly');
            for (const width of [1440, 390]) {
              await session.page.setViewportSize({ width, height: 950 });
              check(`event saved ${width}: no page overflow`, await session.page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2));
              await session.page.screenshot({ path: path.join(out, `event-success-${width}.png`) });
            }
            continue;
          }
        }

        if (diarySaveProbe) {
          const title = `TPL53-DIARY-SAVE-${Date.now()}`;
          const content = '临时验收施工日志：核对官方表单保存与提交失败恢复。';
          report.diaryCreateAuthority = authority;
          for (const field of ['project_id', 'title', 'description']) {
            check(`diary create: ${field} has an editable native input`,
              await session.page.locator(`[data-field-name="${field}"]`).locator('input, textarea, [contenteditable="true"]').count() > 0);
          }
          const projectInput = session.page.locator('[data-field-name="project_id"] input').first();
          const projectResponse = session.page.waitForResponse(response => {
            try { const body = response.request().postDataJSON(); return body?.intent === 'api.data' && body.params?.op === 'list'
              && body.params.model === 'project.project' && JSON.stringify(body.params).includes('FE Project A'); } catch { return false; }
          });
          await projectInput.fill('FE Project A');
          const candidates = await (await projectResponse).json();
          const project = candidates.data?.records?.find(row => Number(row.id) === 10);
          check('diary create: project returned in PM authorized query', candidates.ok === true && Boolean(project));
          const label = String(project.display_name || project.name);
          await session.page.getByRole('option', { name: label, exact: true }).click();
          const titleInput = session.page.locator('[data-field-name="title"]').locator('input, textarea').first();
          const contentInput = session.page.locator('[data-field-name="description"]').locator('textarea, input').first();
          await titleInput.fill(title);
          await contentInput.fill(content);
          diaryCreateCapture = true;
          for (const label of ['保存草稿', '提交审批']) {
            const response = session.page.waitForResponse(response => {
              try { const body = response.request().postDataJSON(); return body?.intent === 'api.data' && body.params?.op === 'create'
                && body.params.model === 'sc.construction.diary'; } catch { return false; }
            });
            await session.page.getByRole('button', { name: label, exact: true }).click();
            await response;
            await session.page.getByText('验收注入：日志保存暂不可用，请重试', { exact: true }).first().waitFor();
            const payload = report.diarySaveAttempts.at(-1);
            check(`diary ${label}: actual values and numeric project preserved`, payload.vals.project_id === project.id
              && payload.vals.title === title && payload.vals.description === content);
            check(`diary ${label}: unchanged date remains an effective backend default`, Boolean(authority.mainData?.date_diary)
              && (!Object.hasOwn(payload.vals, 'date_diary') || payload.vals.date_diary === authority.mainData.date_diary));
            check(`diary ${label}: native entry context preserved`, String(payload.context?.menu_id) === String(report.approvalCreateEntry.menu_id)
              && String(payload.context?.action_id) === String(report.approvalCreateEntry.action_id));
            check(`diary ${label}: failed create preserves editable draft`, new URL(session.page.url()).pathname === '/f/sc.construction.diary/new'
              && await titleInput.inputValue() === title && await contentInput.inputValue() === content);
          }
          diaryCreateCapture = false;
          check('diary save: two explicit attempts and no follow-up business mutation', report.diarySaveAttempts.length === 2 && report.forbiddenWrites.length === 0);
          await session.page.screenshot({ path: path.join(out, 'diary-filled-save-failure.png'), fullPage: true });
          if (diarySaveSuccess) {
            diarySuccess = { model: spec.model, request: structuredClone(report.diarySaveAttempts.at(-1)), phase: 'prepare', id: null };
            await fs.writeFile(expenseRecoveryPath, JSON.stringify(diarySuccess, null, 2));
            await expenseCleanup('preflight');
            diarySuccess.phase = 'create';
            await session.page.getByRole('button', { name: '提交审批', exact: true }).click();
            await session.page.waitForFunction(() => !window.location.pathname.endsWith('/new'));
            check('diary success: create and confirm each execute once', diarySuccess.phase === 'done'
              && JSON.stringify(report.diarySuccessWrites?.map(row => row.kind)) === JSON.stringify(['create', 'submit']));
            const saved = await session.page.evaluate(async id => {
              const token = Object.entries(sessionStorage).find(([key]) => key.startsWith('sc_auth_token:'))?.[1];
              return (await fetch('/api/v1/intent?db=sc_frontend_acceptance', {
                method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}`, 'X-Odoo-DB': 'sc_frontend_acceptance' },
                body: JSON.stringify({ intent: 'api.data', params: { op: 'read', model: 'sc.construction.diary', ids: [id],
                  fields: ['id', 'state', 'project_id', 'company_id', 'title', 'description', 'date_diary', 'diary_type', 'source_origin'], context: { company_id: 8 } } }),
              })).json();
            }, diarySuccess.id);
            report.diarySavedRecord = saved;
            const row = saved.data?.records?.[0];
            check('diary success: PM authoritative record readback', saved.ok === true && row?.id === diarySuccess.id
              && row.state === 'confirmed' && row.project_id[0] === 10 && row.company_id[0] === 8
              && row.title === title && row.description === content && Boolean(row.date_diary)
              && row.diary_type === '施工日志' && row.source_origin === 'manual');
            await form(session.page, `/f/sc.construction.diary/${diarySuccess.id}${createContext}`, 'diary-success-saved', 'readonly');
            for (const width of [1440, 390]) {
              await session.page.setViewportSize({ width, height: 950 });
              check(`diary saved ${width}: no page overflow`, await session.page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2));
              await session.page.screenshot({ path: path.join(out, `diary-success-${width}.png`) });
            }
            continue;
          }

        }

        if (spec.model === 'sc.expense.claim') {
          const fields = [];
          const visit = (nodes) => { for (const node of nodes || []) { if (node.type === 'field') fields.push(node); visit(node.children); } };
          visit(authority.layout?.containerTree);
          for (const name of ['project_id', 'partner_id', 'payment_request_id', 'amount', 'payee_account', 'payer_account']) {
            check(`expense create: ${name} retained in effective contract`, fields.some((field) => field.name === name));
          }
          for (const name of ['payment_request_id', 'amount', 'payee_account', 'payer_account']) {
            check(`expense create: ${name} has rendered input`, await session.page.locator(`[data-field-name="${name}"] input`).count() > 0);
          }
          await session.page.getByRole('button', { name: '提交审批', exact: true }).click();
          await session.page.getByText('当前业务分类要求上传附件后才能提交、批准或完成。', { exact: true }).first().waitFor({ state: 'visible' });
          check('expense create: incomplete submission stays on unsaved form', new URL(session.page.url()).pathname === '/f/sc.expense.claim/new');
          check('expense create: required validation sends no business write', report.forbiddenWrites.length === 0);
          const projectInput = session.page.locator('[data-field-name="project_id"] input').first();
          const projectResponse = session.page.waitForResponse((response) => {
            try { const body = response.request().postDataJSON(); return body?.intent === 'api.data' && body.params?.op === 'list'
              && body.params.model === 'project.project' && JSON.stringify(body.params).includes('FE Project A'); } catch { return false; }
          });
          await projectInput.fill('FE Project A');
          const projectResult = await (await projectResponse).json();
          const project = projectResult.data?.records?.find((row) => row.name === 'FE Project A' || row.display_name === 'FE Project A');
          check('expense relation: existing authorized project returned', projectResult.ok === true && Number(project?.id) > 0);
          await session.page.getByRole('option', { name: String(project.display_name || project.name), exact: true }).click();
          const paymentInput = session.page.locator('[data-field-name="payment_request_id"] input').first();
          const paymentResponse = session.page.waitForResponse((response) => {
            try { const body = response.request().postDataJSON(); return body?.intent === 'api.data' && body.params?.op === 'list' && body.params.model === 'payment.request'; } catch { return false; }
          });
          await paymentInput.click();
          const response = await paymentResponse;
          const query = response.request().postDataJSON().params;
          const result = await response.json();
          report.expenseRelation = { projectId: project.id, query, result };
          const hasProject = (value) => Array.isArray(value) && ((value[0] === 'project_id' && value[1] === '=' && Number(value[2]) === Number(project.id)) || value.some(hasProject));
          check('expense relation: actual request query includes selected project', hasProject(query.domain));
          const hasPayDirection = (value) => Array.isArray(value) && ((value[0] === 'type' && value[1] === 'in'
            && Array.isArray(value[2]) && value[2].length === 1 && value[2][0] === 'pay') || value.some(hasPayDirection));
          check('expense relation: cash-out query restricts request direction', hasPayDirection(query.domain));
          check('expense relation: authorized request candidates returned', result.ok === true && result.data?.records?.length > 0);
          const selected = result.data.records[0];
          const selectedLabel = String(selected.display_name || selected.name);
          await session.page.getByRole('option', { name: selectedLabel, exact: true }).click();
          check('expense relation: selected candidate label retained', await paymentInput.inputValue() === selectedLabel);
          report.expenseRelation.selected = { id: selected.id, label: selectedLabel };
          const otherProjectResponse = session.page.waitForResponse((response) => {
            try { const body = response.request().postDataJSON(); return body?.intent === 'api.data' && body.params?.op === 'list'
              && body.params.model === 'project.project' && JSON.stringify(body.params).includes('FE Project B'); } catch { return false; }
          });
          await projectInput.fill('FE Project B');
          const otherResult = await (await otherProjectResponse).json();
          const otherProject = otherResult.data?.records?.find((row) => row.name === 'FE Project B' || row.display_name === 'FE Project B');
          check('expense relation: second authorized project returned', otherResult.ok === true && Number(otherProject?.id) > 0 && otherProject.id !== project.id);
          await session.page.getByRole('option', { name: String(otherProject.display_name || otherProject.name), exact: true }).click();
          check('expense relation: changing project clears stale request', await paymentInput.inputValue() === '');
          const otherPaymentResponse = session.page.waitForResponse((response) => {
            try { const body = response.request().postDataJSON(); return body?.intent === 'api.data' && body.params?.op === 'list' && body.params.model === 'payment.request'
              && JSON.stringify(body.params.domain).includes(JSON.stringify(['project_id', '=', otherProject.id])); } catch { return false; }
          });
          await paymentInput.click();
          const otherResponse = await otherPaymentResponse;
          report.expenseRelation.changedProject = { id: otherProject.id, query: otherResponse.request().postDataJSON().params, result: await otherResponse.json() };
          check('expense relation: next query uses changed project', report.expenseRelation.changedProject.result.ok === true);
          check('expense relation: changed project preserves cash-out direction', hasPayDirection(report.expenseRelation.changedProject.query.domain));
          check('expense relation: draft interactions send no business write', report.forbiddenWrites.length === 0);

          if (expenseSaveProbe) {
            const sourceResult = await session.page.evaluate(async ({ id, context }) => {
              const token = Object.entries(sessionStorage).find(([key]) => key.startsWith('sc_auth_token:'))?.[1];
              return (await fetch('/api/v1/intent?db=sc_frontend_acceptance', {
                method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}`, 'X-Odoo-DB': 'sc_frontend_acceptance' },
                body: JSON.stringify({ intent: 'api.data', params: { op: 'read', model: 'payment.request', ids: [id],
                  fields: ['id', 'project_id', 'partner_id', 'company_id', 'currency_id', 'amount', 'type', 'state'], context } }),
              })).json();
            }, { id: selected.id, context: query.context });
            const source = sourceResult.data?.records?.[0];
            check('expense save: selected source authoritatively read', sourceResult.ok === true && source?.id === selected.id && source.type === 'pay');
            report.expenseSaveSource = source;
            await projectInput.fill('FE Project A');
            await session.page.getByRole('option', { name: String(project.display_name || project.name), exact: true }).click();
            const partnerInput = session.page.locator('[data-field-name="partner_id"] input').first();
            await partnerInput.fill(source.partner_id[1]);
            await session.page.getByRole('option', { name: source.partner_id[1], exact: true }).click();
            await paymentInput.click();
            await session.page.getByRole('option', { name: selectedLabel, exact: true }).click();
            const amountInput = session.page.locator('[data-field-name="amount"] input').first();
            await amountInput.fill(String(source.amount));
            for (const [name, value] of [['payee_account', 'EXPENSE-SAVE-PAYEE'], ['payer_account', 'EXPENSE-SAVE-PAYER']]) {
              await session.page.locator(`[data-field-name="${name}"] input`).first().fill(value);
            }
            expenseCreateCapture = true;
            await session.page.getByRole('button', { name: '提交审批', exact: true }).click();
            await session.page.getByText('当前业务分类要求上传附件后才能提交、批准或完成。', { exact: true }).first().waitFor();
            check('expense submit: missing attachment blocks before create', !report.expenseSaveAttempts?.length);
            const draftResponse = session.page.waitForResponse((response) => {
              try { const body = response.request().postDataJSON(); return body?.intent === 'api.data'
                && body.params?.op === 'create' && body.params.model === 'sc.expense.claim'; } catch { return false; }
            });
            await session.page.getByRole('button', { name: '保存草稿', exact: true }).click();
            await draftResponse;
            await session.page.getByText('验收注入：保存暂不可用，请重试', { exact: true }).first().waitFor();
            check('expense draft: missing attachment does not prevent save', report.expenseSaveAttempts?.length === 1);
            report.expenseDraftSaveAttempt = report.expenseSaveAttempts[0];
            report.expenseSaveAttempts = [];
            const pendingName = 'tpl53-submission-requirement.txt';
            await session.page.locator('[data-professional-collaboration-component="attachments"] input[type="file"]').setInputFiles({
              name: pendingName, mimeType: 'text/plain', buffer: Buffer.from('Rollback-only submission prerequisite verification'),
            });
            await session.page.getByText(pendingName, { exact: true }).first().waitFor();
            check('expense submit: attachment stays pending before record creation', report.forbiddenWrites.length === 0);
            for (let attempt = 1; attempt <= 2; attempt += 1) {
              const saveResponse = session.page.waitForResponse((response) => {
                try { const body = response.request().postDataJSON(); return body?.intent === 'api.data'
                  && body.params?.op === 'create' && body.params.model === 'sc.expense.claim'; } catch { return false; }
              });
              await session.page.getByRole('button', { name: '提交审批', exact: true }).click();
              await saveResponse;
              await session.page.getByText('验收注入：保存暂不可用，请重试', { exact: true }).first().waitFor();
              check(`expense save: attempt ${attempt} sends exactly one create`, report.expenseSaveAttempts.length === attempt);
              const payload = report.expenseSaveAttempts[attempt - 1];
              check(`expense save: attempt ${attempt} preserves numeric relationship identity`,
                payload.vals.project_id === project.id && payload.vals.partner_id === source.partner_id[0]
                && payload.vals.payment_request_id === selected.id);
              check(`expense save: attempt ${attempt} preserves amount and entry context`,
                Number(payload.vals.amount) === Number(source.amount)
                && String(payload.context?.menu_id) === String(report.approvalCreateEntry.menu_id)
                && String(payload.context?.action_id) === String(report.approvalCreateEntry.action_id));
              check(`expense save: attempt ${attempt} preserves editable draft`, new URL(session.page.url()).pathname === '/f/sc.expense.claim/new'
                && Number(await amountInput.inputValue()) === Number(source.amount) && await paymentInput.inputValue() === selectedLabel);
            }
            expenseCreateCapture = false;
            check('expense save: failed saves do not execute business actions', report.forbiddenWrites.length === 0);
            if (expenseSaveSuccess) {
              const request = structuredClone(report.expenseSaveAttempts[1]);
              request.vals.summary = `TPL53-EXPENSE-SUCCESS-${Date.now()}`;
              expenseSuccess = { request, source, filename: pendingName,
                data: Buffer.from('Rollback-only submission prerequisite verification').toString('base64'), phase: 'prepare', id: null };
              if (expensePartialUpload) {
                expenseSuccess.files = [
                  { name: pendingName, data: expenseSuccess.data },
                  { name: 'tpl53-partial-second.txt', data: Buffer.from('Rollback-only second attachment').toString('base64') },
                ];
                expenseSuccess.uploadIndex = 0;
                const second = expenseSuccess.files[1];
                await session.page.locator('[data-professional-collaboration-component="attachments"] input[type="file"]').setInputFiles({
                  name: second.name, mimeType: 'text/plain', buffer: Buffer.from(second.data, 'base64'),
                });
                await session.page.getByText(second.name, { exact: true }).first().waitFor();
              }
              await fs.writeFile(expenseRecoveryPath, JSON.stringify(expenseSuccess, null, 2));
              await expenseCleanup('preflight');
              await session.page.locator('[data-field-name="summary"]').locator('input, textarea').first().fill(request.vals.summary);
              expenseSuccess.phase = 'create';
              await session.page.getByRole('button', { name: '提交审批', exact: true }).click();
              await session.page.waitForFunction(() => !window.location.pathname.endsWith('/new'));
              if (expenseFailureStage) {
                await session.page.locator('[data-form-composition="official-standard-form"][data-state="ok"]').waitFor();
                const recoveryUrl = new URL(session.page.url());
                check('expense recovery: generated record remains the current identity', recoveryUrl.pathname === `/f/sc.expense.claim/${expenseSuccess.id}`
                  && recoveryUrl.searchParams.get('create_recovery') === expenseFailureStage && report.expenseInjectedFailure?.id === expenseSuccess.id);
                const message = expenseFailureStage === 'upload'
                  ? '单据已保存，附件上传未完成。请在当前单据重新选择附件后提交。'
                  : '单据已保存，提交未完成。请在当前单据核对后重试。';
                await session.page.getByText(message, { exact: true }).waitFor();
                if (expenseFailureStage === 'upload') {
                  if (expensePartialUpload) {
                    check('expense partial: first file confirmed before second failed', expenseSuccess.uploadIndex === 1
                      && report.expenseSuccessWrites.filter(row => row.kind === 'upload').length === 1);
                    await session.page.getByText(pendingName, { exact: true }).first().waitFor();
                  }
                  const retryFile = expenseSuccess.files?.[expenseSuccess.uploadIndex]
                    || { name: pendingName, data: expenseSuccess.data };
                  const uploadResponse = session.page.waitForResponse((response) => {
                    try { return response.request().postDataJSON()?.intent === 'file.upload'; } catch { return false; }
                  });
                  await session.page.locator('[data-professional-collaboration-component="attachments"] input[type="file"]').setInputFiles({
                    name: retryFile.name, mimeType: 'text/plain', buffer: Buffer.from(retryFile.data, 'base64'),
                  });
                  await uploadResponse;
                }
                await session.page.getByRole('button', { name: '提交审批', exact: true }).click();
              }
              const completed = () => report.expenseSuccessWrites?.some((row) => row.kind === 'submit' && row.result.ok === true);
              for (let wait = 0; wait < 100 && !completed(); wait += 1) await session.page.waitForTimeout(100);
              check('expense success: create upload submit occur exactly once',
                JSON.stringify(report.expenseSuccessWrites?.map((row) => row.kind)) === JSON.stringify(expensePartialUpload ? ['create', 'upload', 'upload', 'submit'] : ['create', 'upload', 'submit']) && completed());
              const saved = await session.page.evaluate(async (id) => {
                const token = Object.entries(sessionStorage).find(([key]) => key.startsWith('sc_auth_token:'))?.[1];
                return (await fetch('/api/v1/intent?db=sc_frontend_acceptance', {
                  method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}`, 'X-Odoo-DB': 'sc_frontend_acceptance' },
                  body: JSON.stringify({ intent: 'api.data', params: { op: 'read', model: 'sc.expense.claim', ids: [id],
                    fields: ['id', 'state', 'project_id', 'partner_id', 'payment_request_id', 'amount', 'attachment_ids', 'summary'], context: { company_id: 8 } } }),
                })).json();
              }, expenseSuccess.id);
              report.expenseSuccessRecord = saved;
              const savedRow = saved.data?.records?.[0];
              check('expense success: submitted record and attachment authoritative readback', saved.ok === true && savedRow?.state === 'approved'
                && savedRow.attachment_ids.length === (expensePartialUpload ? 2 : 1) && savedRow.payment_request_id[0] === source.id && savedRow.summary === request.vals.summary);
              await form(session.page, `/f/sc.expense.claim/${expenseSuccess.id}${createContext}`, 'expense-success-saved', 'readonly');
              const savedAuthority = (report.contractResponses || []).map((row) => findRecordAuthority(row.contract))
                .findLast((row) => row?.model === 'sc.expense.claim' && Number(row.mainData?.id) === expenseSuccess.id);
              check('expense success: saved contract is readonly', savedAuthority?.status.effectiveRenderProfile === 'readonly');
              for (const width of [1440, 390]) {
                await session.page.setViewportSize({ width, height: 950 });
                check(`expense success ${width}: no page overflow`, await session.page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
                await session.page.screenshot({ path: path.join(out, `expense-success-${width}.png`) });
              }
              await session.ctx.close();
              continue;
            }
          }

          await session.page.getByRole('heading', { name: '新建报销申请', exact: true }).click();

        }

        if (['sc.settlement.adjustment', 'sc.receipt.income', 'sc.financing.loan', 'sc.self.funding.registration', 'sc.treasury.reconciliation'].includes(spec.model)) {
          const fields = [];
          const walk = (nodes, pages = []) => { for (const node of nodes || []) { const path = node.type === 'page' ? [...pages, node.label || node.title] : pages; if (node.type === 'field') fields.push({ ...node, probePages: path }); walk(node.children, path); } };
          walk(authority.layout?.containerTree);
          const required = spec.model === 'sc.treasury.reconciliation'
            ? ['project_id', 'treasury_ledger_id', 'system_difference'] : spec.model === 'sc.settlement.adjustment'
              ? ['project_id', 'contract_id', 'item_name', 'amount'] : spec.model === 'sc.receipt.income'
              ? ['project_id', 'payment_request_id', 'partner_id', 'amount'] : ['project_id', 'partner_id', 'amount'];
          for (const name of required) {
            const field = fields.find((node) => node.name === name);
            check(`${spec.model}: ${name} editable contract`, Boolean(field) && field.readonly !== true && field.fieldInfo?.readonly !== true);
            const input = session.page.locator(`[data-field-name="${name}"] input`).first();
            // Task forms may project native notebook fields into semantic regions.
            // Prefer the actual input; native pages are navigation only when needed.
            if (!(await input.isVisible())) {
              for (const title of field.probePages) {
                const pageLink = session.page.getByText(title, { exact: true });
                if (await pageLink.count() === 1) await pageLink.click();
              }
            }
            await input.waitFor({ state: 'visible' });
            await input.scrollIntoViewIfNeeded();
            check(`${spec.model}: ${name} actual input`, await session.page.locator(`[data-field-name="${name}"] input`).count() > 0);
          }
          for (const label of ['审批通过', spec.model === 'sc.treasury.reconciliation' ? '对账完成' : spec.model === 'sc.receipt.income' ? '已收款' : '完成']) {
            check(`${spec.model}: no ${label} on unsaved document`, await session.page.getByRole('button', { name: label, exact: true }).count() === 0);
          }
        }
        if (spec.model === 'sc.project.document') {
          const fields = [];
          const walk = (nodes) => { for (const node of nodes || []) { if (node.type === 'field') fields.push(node); walk(node.children); } };
          walk(authority.layout?.containerTree);
          for (const name of ['name', 'project_id', 'doc_type_id']) {
            const field = fields.find((node) => node.name === name);
            check(`project document: ${name} editable contract`, Boolean(field) && field.readonly !== true && field.fieldInfo?.readonly !== true);
            check(`project document: ${name} actual input`, await session.page.locator(`[data-field-name="${name}"] input`).count() > 0);
          }
          check('project document: no archival before saved approval', await session.page.getByRole('button', { name: '归档', exact: true }).count() === 0);
          check('project document: no approval of unsaved document', await session.page.getByRole('button', { name: '审批通过', exact: true }).count() === 0);
        }
        if (spec.model === 'tender.doc.purchase') {
          const fields = [];
          const walk = (nodes) => { for (const node of nodes || []) { if (node.type === 'field') fields.push(node); walk(node.children); } };
          walk(authority.layout?.containerTree);
          for (const name of ['bid_id', 'apply_date', 'amount']) {
            const field = fields.find((node) => node.name === name);
            check(`tender purchase: ${name} editable contract`, Boolean(field) && field.readonly !== true && field.fieldInfo?.readonly !== true);
            check(`tender purchase: ${name} actual input`, await session.page.locator(`[data-field-name="${name}"] input`).count() > 0);
          }
          check('tender purchase: no direct approval on unsaved document', await session.page.getByRole('button', { name: '通过', exact: true }).count() === 0);
        }
        if (spec.model === 'tender.guarantee') {
          const fields = [];
          const walk = (nodes) => { for (const node of nodes || []) { if (node.type === 'field') fields.push(node); walk(node.children); } };
          walk(authority.layout?.containerTree);
          for (const name of ['bid_id', 'date', 'amount']) {
            const field = fields.find((node) => node.name === name);
            check(`tender guarantee: ${name} editable contract`, Boolean(field) && field.readonly !== true && field.fieldInfo?.readonly !== true);
            check(`tender guarantee: ${name} actual input`, await session.page.locator(`[data-field-name="${name}"] input`).count() > 0);
          }
          check('tender guarantee: no cash posting before approval', await session.page.getByRole('button', { name: '确认入账', exact: true }).count() === 0);
          check('tender guarantee: no direct approval on unsaved document', await session.page.getByRole('button', { name: '通过', exact: true }).count() === 0);
        }
        if (spec.model === 'sc.output.invoice.adjustment') {
          const fields = [];
          const walk = (nodes) => { for (const node of nodes || []) { if (node.type === 'field') fields.push(node); walk(node.children); } };
          walk(authority.layout?.containerTree);
          for (const name of ['original_ledger_id', 'adjustment_date', 'red_flush_invoice_no']) {
            const field = fields.find((node) => node.name === name);
            check(`red flush: ${name} editable contract`, Boolean(field) && field.readonly !== true && field.fieldInfo?.readonly !== true);
            check(`red flush: ${name} actual input`, await session.page.locator(`[data-field-name="${name}"] input`).count() > 0);
          }
          const originalControl = session.page.locator('[data-field-name="original_ledger_id"] input').first();
          const originalResponse = session.page.waitForResponse((response) => {
            try {
              const body = response.request().postDataJSON();
              return body?.intent === 'api.data' && body.params?.op === 'list' && body.params.model === 'sc.output.invoice.ledger';
            } catch { return false; }
          });
          await originalControl.click();
          const originalQuery = (await originalResponse).request().postDataJSON().params;
          const eligibleDomain = [['active', '=', true], ['adjustment_kind', '=', 'normal'], '|', ['source_model', '!=', 'sc.invoice.registration'], ['invoice_document_state', 'in', ['registered', 'legacy_confirmed']]];
          check('red flush: actual original query preserves eligibility domain', JSON.stringify(originalQuery.domain) === JSON.stringify(eligibleDomain));
          await session.page.getByRole('heading', { name: '新建记录', exact: true }).click();
          check('red flush: no red invoice before approval', await session.page.getByRole('button', { name: '确认红冲', exact: true }).count() === 0);
          check('red flush: no direct approval on unsaved document', await session.page.getByRole('button', { name: '通过', exact: true }).count() === 0);
        }
        if (spec.model === 'payment.request') {
          const nodes = [];
          const visit = (items) => {
            for (const node of items || []) {
              if (node.type === 'field') nodes.push(node);
              visit(node.children);
            }
          };
          visit(authority.layout?.containerTree);
          const basis = nodes.find((node) => node.name === 'subcontract_settlement_id');
          check('payment create: explicit subcontract basis in effective contract', Boolean(basis));
          check('payment create: subcontract basis is editable', basis.readonly !== true && basis.fieldInfo?.readonly !== true && basis.componentConfig?.readonly !== true);
          const control = session.page.getByPlaceholder('请选择分包结算单', { exact: true });
          check('payment create: actual subcontract relation control', await control.count() === 1);
          await control.scrollIntoViewIfNeeded();
          const sourceResponse = session.page.waitForResponse((response) => {
            try {
              const body = response.request().postDataJSON();
              return body?.intent === 'api.data' && body.params?.op === 'list'
                && body.params.model === 'sc.subcontract.settlement';
            } catch { return false; }
          });
          await control.click();
          const sourceQuery = (await sourceResponse).request().postDataJSON().params;
          check('payment create: unresolved project blocks source query',
            JSON.stringify(sourceQuery.domain) === JSON.stringify([['id', '=', -1]]));
          await session.page.screenshot({ animations: 'disabled', path: path.join(out, 'payment-subcontract-basis-open.png') });
          await session.page.getByRole('heading', { name: '新建记录', exact: true }).click();
          const projectControl = session.page.locator('[data-field-name="project_id"]').locator('input').first();
          const projectResponse = session.page.waitForResponse((response) => {
            try {
              const body = response.request().postDataJSON();
              return body?.intent === 'api.data' && body.params?.op === 'list'
                && body.params.model === 'project.project';
            } catch { return false; }
          });
          await projectControl.click();
          const projects = (await (await projectResponse).json()).data?.records || [];
          check('payment source: existing authorized project available', projects.length > 0);
          let project = projects[0];
          const projectLabel = String(project.display_name || project.name);
          const matchesScope = (domain) => Array.isArray(domain)
            && domain.some((term) => JSON.stringify(term) === JSON.stringify(['project_id', '=', project.id]))
            && domain.some((term) => JSON.stringify(term) === JSON.stringify(['state', '=', 'confirmed']));
          const scopedResponse = session.page.waitForResponse((response) => {
            try {
              const body = response.request().postDataJSON();
              return body?.intent === 'api.data' && body.params?.op === 'list'
                && body.params.model === 'sc.subcontract.settlement'
                && matchesScope(body.params.domain);
            } catch { return false; }
          });
          await session.page.getByRole('option', { name: projectLabel, exact: true }).click();
          const scopedQuery = (await scopedResponse).request().postDataJSON().params;
          check('payment source: selected project and confirmed state preserved', matchesScope(scopedQuery.domain));
          report.paymentSourceScope = { projectId: project.id, domain: scopedQuery.domain };
          await control.click();
          const moreResponse = session.page.waitForResponse((response) => {
            try {
              const body = response.request().postDataJSON();
              return body?.intent === 'api.data' && body.params?.op === 'list'
                && body.params.model === 'sc.subcontract.settlement' && body.params.limit === 120;
            } catch { return false; }
          });
          const [moreResult] = await Promise.all([
            moreResponse,
            session.page.getByRole('button', { name: '搜索更多...', exact: true }).click(),
          ]);
          const moreQuery = moreResult.request().postDataJSON().params;
          check('payment source: search dialog preserves same scope', matchesScope(moreQuery.domain));
          const sourceDialog = session.page.getByRole('dialog');
          await sourceDialog.getByRole('button', { name: '取消', exact: true }).click();
          check('payment source: second existing project available', projects.length > 1);
          project = projects[1];
          await projectControl.click();
          const changedSourceResponse = session.page.waitForResponse((response) => {
            try {
              const body = response.request().postDataJSON();
              return body?.intent === 'api.data' && body.params?.op === 'list'
                && body.params.model === 'sc.subcontract.settlement' && matchesScope(body.params.domain);
            } catch { return false; }
          });
          const [changedSource] = await Promise.all([
            changedSourceResponse,
            session.page.getByRole('option', { name: String(project.display_name || project.name), exact: true }).click(),
          ]);
          check('payment source: project change replaces query scope', matchesScope(changedSource.request().postDataJSON().params.domain));
          report.paymentSourceScope.changedProjectId = project.id;
          await session.page.getByRole('heading', { name: '新建记录', exact: true }).click();
        }
        if (['sc.material.rental.order', 'sc.material.rental.settlement'].includes(spec.model)) {
          const settlement = spec.model === 'sc.material.rental.settlement';
          const dateField = settlement ? 'settlement_date' : 'rental_date';
          const fields = [];
          const visit = (nodes) => {
            for (const node of nodes || []) {
              if (node.type === 'field') fields.push(node);
              visit(node.children);
            }
          };
          visit(authority.layout?.containerTree);
          for (const name of ['project_id', 'supplier_id', dateField, 'note']) {
            const field = fields.find((node) => node.name === name);
            check(`${spec.model}: ${name} editable contract`, Boolean(field) && field.readonly !== true && field.fieldInfo?.readonly !== true);
          }
          for (const label of ['项目', '供应商']) {
            check(`${spec.model}: ${label} input visible`, await session.page.getByPlaceholder(`请选择${label}`, { exact: true }).isVisible());
          }
          check(`${spec.model}: date input visible`, await session.page.locator(`input[value="${authority.mainData[dateField]}"]`).isVisible());
          check(`${spec.model}: note input visible`, await session.page.locator('textarea').first().isVisible());

          check(`${spec.model}: generated number absent on create`, await session.page.getByText(settlement ? '结算单号' : '租赁单号', { exact: true }).count() === 0);
          for (const name of (settlement ? ['确认结算', '确认支付'] : ['确认租赁', '确认退还', '完成结算'])) {
            check(`${spec.model}: unsaved cannot ${name}`, await session.page.getByRole('button', { name, exact: true }).count() === 0);
          }
        }
        if (executionLabels) {
          check(`${spec.model}: generated number absent on create`, await session.page.getByText(executionLabels[0], { exact: true }).count() === 0);
          check(`${spec.model}: unsaved cannot confirm`, await session.page.getByRole('button', { name: executionLabels[1], exact: true }).count() === 0);
        }
        if (['sc.safety.plan', 'sc.safety.disclosure', 'sc.subcontract.plan', 'sc.subcontract.request', 'sc.subcontract.settlement'].includes(spec.model)) {
          const fields = [];
          const visit = (nodes) => {
            for (const node of nodes || []) {
              if (node.type === 'field') fields.push(node);
              visit(node.children);
            }
          };
          visit(authority.layout?.containerTree);
          if (spec.model.startsWith('sc.subcontract.')) {
            const number = fields.find((node) => node.name === 'name');
            const invisible = number?.modifiers?.invisible;
            const hiddenForNewIdentity = invisible?.kind === 'not'
              && invisible.expr?.kind === 'field_truthy' && invisible.expr?.field === 'id'
              && !(Number(authority.mainData?.id) > 0);
            check(`${spec.model}: generated number hidden by effective contract`, !number || number.invisible === true || number.fieldInfo?.invisible === true || number.componentConfig?.invisible === true || hiddenForNewIdentity);
          }
          const inputs = spec.model === 'sc.subcontract.settlement'
            ? ['project_id', 'subcontractor_id', 'settlement_date']
            : spec.model.startsWith('sc.subcontract.')
            ? ['project_id', 'subcontract_scope', spec.model.endsWith('plan') ? 'plan_date' : 'request_date']
            : spec.model === 'sc.safety.plan'
            ? ['name', 'project_id', 'description']
            : ['name', 'project_id', 'participant_note', 'content'];
          for (const name of inputs) {
            const field = fields.find((node) => node.name === name);
            check(`${spec.model}: ${name} editable input contract`, Boolean(field) && field.readonly !== true && field.fieldInfo?.readonly !== true && field.componentConfig?.readonly !== true);
          }
        }
        if (['sc.equipment.plan', 'sc.equipment.request', 'sc.labor.plan', 'sc.labor.request', 'sc.material.rental.plan', 'sc.subcontract.plan', 'sc.subcontract.request'].includes(spec.model)) {
          const numberLabel = spec.model.endsWith('plan') ? '计划单号' : '申请单号';
          check(`${spec.model}: generated number absent on create`, await session.page.getByText(new RegExp(numberLabel)).count() === 0);
          check(`${spec.model}: old direct approval absent`, await session.page.getByRole('button', { name: spec.model === 'sc.material.rental.plan' ? '确认' : spec.model.endsWith('plan') ? '确认计划' : '确认申请', exact: true }).count() === 0);
        }
        if (spec.model === 'sc.labor.settlement') {
          const nodes = [];
          const visit = (items) => {
            for (const node of items || []) {
              if (node.type === 'field') nodes.push(node);
              visit(node.children);
            }
          };
          visit(authority.layout?.containerTree);
          for (const [name, label] of [['project_id', '项目'], ['contractor_id', '劳务单位'], ['settlement_date', '结算日期'], ['note', '结算说明']]) {
            const field = nodes.find((node) => node.name === name);
            check(`labor settlement: ${name} input contract`, Boolean(field) && field.readonly !== true && field.fieldInfo?.readonly !== true && field.componentConfig?.readonly !== true);
            const input = name === 'project_id' || name === 'contractor_id'
              ? session.page.getByPlaceholder(`请选择${label}`, { exact: true })
              : name === 'settlement_date'
                ? session.page.locator(`input[value="${authority.mainData.settlement_date}"]`)
                : session.page.locator('textarea');
            check(`labor settlement: ${name} input visible`, await input.count() > 0);
          }
        }
        if (spec.model === 'sc.subcontract.settlement') {
          check('subcontract settlement: generated number absent on create', await session.page.getByText(/结算单号/).count() === 0);
          check('subcontract settlement: unsaved has no confirmation', await session.page.getByRole('button', { name: '确认结算', exact: true }).count() === 0);
          for (const name of ['project_id', 'subcontractor_id', 'settlement_date']) {
            const field = session.page.locator(`[data-field-name="${name}"]`);
            check(`subcontract settlement: ${name} has actual input`, await field.locator('input').count() > 0);
          }
        }
        if (spec.model === 'sc.material.settlement') check('material settlement: generated number absent on create', await session.page.getByText('结算单号', { exact: true }).count() === 0);
        if (spec.model === 'sc.material.rfq') check('RFQ: generated number absent on create', await session.page.getByText('询价单号', { exact: true }).count() === 0);
        if (spec.model === 'sc.material.purchase.request') {
          check('purchase request: generated number not exposed for create input', await session.page.getByText('申请单号', { exact: true }).count() === 0);
        }

        for (const name of ['审批通过', '审批驳回', '完成', ...(spec.model === 'sc.material.inbound' ? ['确认入库'] : spec.model === 'sc.material.acceptance' ? ['验收通过', '验收不通过'] : spec.model === 'sc.material.purchase.request' ? ['生成询价单', '生成采购订单'] : spec.model === 'sc.material.rfq' ? ['确定报价', '生成采购订单'] : spec.model === 'sc.material.settlement' ? ['确认结算', '生成剩余付款申请'] : [])]) {
          check(`${spec.model}: unsaved form has no ${name} action`, await session.page.getByRole('button', { name, exact: true }).count() === 0);
        }
        for (const width of [1440, 390]) {
          await session.page.setViewportSize({ width, height: 900 });
          await session.page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
          check(`${spec.model}-create-${width}: no page overflow`, await session.page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
          if (['sc.subcontract.plan', 'sc.subcontract.request'].includes(spec.model)) {
            const names = spec.model.endsWith('plan')
              ? ['project_id', 'subcontract_scope', 'plan_date', 'start_date', 'end_date']
              : ['project_id', 'subcontract_scope', 'request_date'];
            const observation = await session.page.evaluate((fieldNames) => {
              const box = (el) => {
                if (!el) return null;
                const r = el.getBoundingClientRect();
                return { x: r.x, y: r.y, width: r.width, height: r.height };
              };
              return fieldNames.map((name) => ({
                name,
                occurrences: [...document.querySelectorAll('[data-field-name]')]
                  .filter((el) => el.getAttribute('data-field-name') === name)
                  .map((el) => ({
                    box: box(el),
                    label: box(el.querySelector('label')),
                    controls: [...el.querySelectorAll('input, textarea')].map((input) => ({
                      box: box(input), id: input.id, placeholder: input.getAttribute('placeholder'),
                      disabled: input.disabled, readonly: input.readOnly,
                    })),
                  })),
              }));
            }, names);
            (report.createInputGeometry ||= []).push({ model: spec.model, width, fields: observation });
            for (const field of observation) {
              const rendered = field.occurrences.filter((row) => row.box?.width > 0 && row.box?.height > 0);
              check(`${spec.model}-${width}: ${field.name} rendered usable input`, rendered.length > 0 && rendered.every((row) =>
                row.controls.some((control) => !control.disabled && control.box?.width > 0 && control.box?.height > 0)));
              check(`${spec.model}-${width}: ${field.name} label separated from input`, rendered.every((row) =>
                row.label && row.controls.every((control) => control.box.y >= row.label.y + row.label.height)));
            }
            const scopeField = observation.find((field) => field.name === 'subcontract_scope');
            const scopeInput = session.page.locator(`[id="${scopeField.occurrences[0].controls[0].id}"]`);
            await scopeInput.fill('本地验收未保存分包范围');
            check(`${spec.model}-${width}: scope accepts draft input`, await scopeInput.inputValue() === '本地验收未保存分包范围');
            await scopeInput.fill('');
            const dateField = observation.find((field) => field.name === (spec.model.endsWith('plan') ? 'start_date' : 'request_date'));
            const dateInput = session.page.locator(`[id="${dateField.occurrences[0].controls[0].id}"]`);
            await dateInput.click();
            await session.page.getByText('一', { exact: true }).waitFor({ state: 'visible' });
            await session.page.getByText('六', { exact: true }).waitFor({ state: 'visible' });
            check(`${spec.model}-${width}: date opens official calendar`, await session.page.getByText('一', { exact: true }).isVisible() && await session.page.getByText('六', { exact: true }).isVisible());
            await session.page.getByRole('heading', { name: '新建记录', exact: true }).click();
            await session.page.getByText('一', { exact: true }).waitFor({ state: 'hidden' });
            check(`${spec.model}-${width}: calendar closes on outside click`, !await session.page.getByText('一', { exact: true }).isVisible());
            await session.page.evaluate(() => window.scrollTo(0, 0));

          }
          await session.page.screenshot({ animations: 'disabled', path: path.join(out, `${spec.model}-create-${width}.png`) });
        }
        await session.ctx.close();
        continue;
      }
      const projectSave = process.env.TPL07_PROJECT_SAVE === '1';
      if (projectSave) {
        check('project save: exact governed scope', spec.model === 'project.project' && spec.role === 'fixture_role_pm'
          && process.env.TPL07_APPROVAL_VIEW === 'information-edit');
        spec.domain = [['id', '=', 10]];
      }
      const candidate = await session.page.evaluate(async ({ model, domain, stateField, fields }) => {
        const token = Object.entries(sessionStorage).find(([key]) => key.startsWith('sc_auth_token:'))?.[1];
        const response = await fetch('/api/v1/intent?db=sc_frontend_acceptance', {
          method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}`, 'X-Odoo-DB': 'sc_frontend_acceptance' },
          body: JSON.stringify({ intent: 'api.data', params: { op: 'list', model, fields: ['id', stateField || 'state', ...(fields || [])], domain, limit: 1 } }),
        });
        return response.json();
      }, spec);
      report.approvalPages.push({ ...spec, candidate });
      check(`${spec.model}: existing authorized record available`, candidate.ok === true && candidate.data?.records?.length === 1);
      const record = candidate.data.records[0];
      report.recordAuthority = null;
      const informationEdit = process.env.TPL07_APPROVAL_VIEW === 'information-edit';
      const editing = process.env.TPL07_APPROVAL_VIEW === 'edit' || informationEdit;
      let entryContext = '';
      if (informationEdit) {
        check('information edit: project-only responsibility', spec.model === 'project.project');
        const entries = ['primary_actions', 'role_home_actions', 'contextual_actions', 'admin_actions']
          .flatMap((key) => report.routeAuthority?.[key] || []);
        const matches = entries.filter((row) => row.menu_xmlid === 'smart_construction_core.menu_sc_product_project_edit_v1');
        check('information edit: current principal has one authorized entry', matches.length === 1 && Number(matches[0].menu_id) > 0 && Number(matches[0].action_id) > 0);
        report.approvalPages.at(-1).entry = matches[0];
        entryContext = `?menu_id=${Number(matches[0].menu_id)}&action_id=${Number(matches[0].action_id)}`;
      }
      const responseStart = report.contractResponses?.length || 0;
      await form(session.page, `/${editing ? 'f' : 'r'}/${spec.model}/${record.id}${entryContext}`, spec.model, editing ? 'form' : 'readonly');
      // Embedded relation contracts can finish after the main record. Select
      // this navigation's exact record, never the last unrelated response.
      const authority = (report.contractResponses || []).slice(responseStart)
        .map((row) => findRecordAuthority(row.contract))
        .findLast((row) => row?.model === spec.model && Number(row.mainData?.id) === Number(record.id));
      check(`${spec.model}: matching effective contract`, authority?.model === spec.model && authority.mainData?.[spec.stateField || 'state'] === record[spec.stateField || 'state']);
      report.approvalPages.at(-1).authority = authority;
      if (spec.model === 'sc.expense.claim') {
        const rules = authority.actions?.actionRuleList || [];
        for (const [method, purpose] of [['action_submit', 'submit'], ['validate_tier', 'approve'], ['reject_tier', 'reject'], ['action_done', 'complete']]) {
          check(`expense: ${method} declares its responsibility`, rules.some((rule) => rule.button?.name === method && rule.actionSemantics?.purpose === purpose));
        }
        if (record.state !== 'approved') check('expense: completion absent before approval or after execution', await session.page.getByRole('button', { name: '完成', exact: true }).count() === 0);
      }
      if (['sc.plan', 'sc.construction.diary'].includes(spec.model)) {
        const rules = authority.actions?.actionRuleList || [];
        check(`${spec.model}: native approval methods declared`, ['validate_tier', 'reject_tier'].every((method) => rules.some((rule) => rule.button?.name === method)));
        const completeState = spec.model === 'sc.plan' ? 'in_progress' : 'confirmed';
        if (record.state !== completeState) {
          check(`${spec.model}: premature completion absent`, await session.page.getByRole('button', { name: '完成', exact: true }).count() === 0);
        }
        if (spec.model === 'sc.plan' && record.state !== 'cancel') {
          check('plan: reset absent outside cancelled state', await session.page.getByRole('button', { name: '重置草稿', exact: true }).count() === 0);
        }
      }
      if (['sc.equipment.plan', 'sc.equipment.request', 'sc.labor.plan', 'sc.labor.request', 'sc.material.rental.plan', 'sc.subcontract.plan', 'sc.subcontract.request'].includes(spec.model)) {
        const rules = authority.actions?.actionRuleList || [];
        for (const [method, purpose] of [['action_submit', 'submit'], ['validate_tier', 'approve'], ['reject_tier', 'reject']]) {
          check(`${spec.model}: ${method} declares its responsibility`, rules.some((rule) => rule.button?.name === method && rule.actionSemantics?.purpose === purpose));
        }
        check(`${spec.model}: legacy direct approval retired`, !rules.some((rule) => rule.button?.name === 'action_approve'));
      }
      if (spec.model === 'sc.material.rental.order') {
        const rules = authority.actions?.actionRuleList || [];
        for (const [method, purpose] of [['action_submit', 'submit'], ['validate_tier', 'approve'], ['reject_tier', 'reject'], ['action_activate', 'start_execution'], ['action_return', 'complete'], ['action_settle', 'complete']]) {
          check(`rental order: ${method} responsibility`, rules.some((rule) => rule.button?.name === method && rule.actionSemantics?.purpose === purpose));
        }
        for (const [state, name] of [['approved', '确认租赁'], ['active', '确认退还'], ['returned', '完成结算']]) {
          if (record.state !== state) check(`rental order: ${name} respects state`, await session.page.getByRole('button', { name, exact: true }).count() === 0);
        }
      }
      if (executionLabels) {
        const rules = authority.actions?.actionRuleList || [];
        for (const [method, purpose] of [['action_submit', 'submit'], ['validate_tier', 'approve'], ['reject_tier', 'reject'], ['action_confirm', 'complete']]) {
          check(`${spec.model}: ${method} declares its responsibility`, rules.some((rule) => rule.button?.name === method && rule.actionSemantics?.purpose === purpose));
        }
        if (record.state !== 'approved') check(`${spec.model}: confirmation absent outside approved`, await session.page.getByRole('button', { name: executionLabels[1], exact: true }).count() === 0);
      }
      if (spec.model === 'sc.material.settlement') {
        const rules = authority.actions?.actionRuleList || [];
        for (const [method, purpose] of [['action_submit', 'submit'], ['validate_tier', 'approve'], ['reject_tier', 'reject'], ['action_confirm', 'complete']]) {
          check(`material settlement: ${method} declares its responsibility`, rules.some((rule) => rule.button?.name === method && rule.actionSemantics?.purpose === purpose));
        }
        if (record.state !== 'approved') check('material settlement: confirmation absent outside approved', await session.page.getByRole('button', { name: '确认结算', exact: true }).count() === 0);
        if (record.state !== 'confirmed') check('material settlement: remaining payment absent before confirmation', await session.page.getByRole('button', { name: '生成剩余付款申请', exact: true }).count() === 0);
      }
      if (spec.model === 'sc.material.rfq') {
        const rules = authority.actions?.actionRuleList || [];
        for (const [method, purpose] of [['action_submit', 'submit'], ['validate_tier', 'approve'], ['reject_tier', 'reject'], ['action_select', 'complete']]) {
          check(`RFQ: ${method} declares its responsibility`, rules.some((rule) => rule.button?.name === method && rule.actionSemantics?.purpose === purpose));
        }
        if (record.state !== 'approved') check('RFQ: quote selection absent before approval or after selection', await session.page.getByRole('button', { name: '确定报价', exact: true }).count() === 0);
        if (record.state !== 'selected') check('RFQ: order generation absent before selection', await session.page.getByRole('button', { name: '生成采购订单', exact: true }).count() === 0);
      }
      if (spec.model === 'sc.material.purchase.request') {
        const rules = authority.actions?.actionRuleList || [];
        for (const [method, purpose] of [['action_submit', 'submit'], ['validate_tier', 'approve'], ['reject_tier', 'reject']]) {
          check(`purchase request: ${method} declares its business meaning`, rules.some((rule) => rule.button?.name === method && rule.actionSemantics?.purpose === purpose));
        }
        check('purchase request: old direct approval entry retired', !rules.some((rule) => rule.button?.name === 'action_approve'));
        if (record.state !== 'approved') {
          for (const name of ['生成询价单', '生成采购订单']) check(`purchase request: ${name} absent outside approved`, await session.page.getByRole('button', { name, exact: true }).count() === 0);
        }
      }
      if (spec.model === 'sc.material.acceptance') {
        const rules = authority.actions?.actionRuleList || [];
        for (const [method, purpose] of [['action_submit', 'submit'], ['validate_tier', 'approve'], ['reject_tier', 'reject'], ['action_accept', 'complete'], ['action_reject', 'complete']]) {
          check(`acceptance: ${method} has distinct declared responsibility`, rules.some((rule) => rule.button?.name === method && rule.actionSemantics?.purpose === purpose));
        }
        if (record.state !== 'approved') {
          for (const name of ['验收通过', '验收不通过']) check(`acceptance: ${name} absent outside approved`, await session.page.getByRole('button', { name, exact: true }).count() === 0);
        }
      }
      if (spec.model === 'sc.material.inbound') {
        const rules = authority.actions?.actionRuleList || [];
        for (const [method, purpose] of [['action_submit', 'submit'], ['validate_tier', 'approve'], ['reject_tier', 'reject'], ['action_receive', 'complete']]) {
          check(`inbound: ${method} declares its business meaning`, rules.some((rule) => rule.button?.name === method && rule.actionSemantics?.purpose === purpose));
        }
        if (record.state !== 'approved') check('inbound: no receiving before approval or after receipt', await session.page.getByRole('button', { name: '确认入库', exact: true }).count() === 0);
      }
      if (spec.model === 'project.project') {
        const rules = authority.actions?.actionRuleList || [];
        if (informationEdit) {
          check('information edit: submission is the only native workflow action', rules.filter((rule) => rule.button?.type === 'object').every((rule) => rule.button.name === 'action_sc_submit') && rules.some((rule) => rule.button?.name === 'action_sc_submit' && rule.actionSemantics?.purpose === 'submit'));
          check('information edit: effective entry remains editable', authority.status?.effectiveRenderProfile === 'edit' || authority.status?.effectiveRenderProfile === 'editable');
        } else {
          check('project: submit and start are distinct native methods', ['action_sc_submit', 'action_sc_start'].every((method) => rules.some((rule) => rule.button?.name === method)));
          for (const [method, purpose] of [['action_sc_submit', 'submit'], ['action_sc_start', 'start_execution'], ['validate_tier', 'approve'], ['reject_tier', 'reject']]) {
            check(`project: ${method} has declared business meaning`, rules.some((rule) => rule.button?.name === method && rule.actionSemantics?.purpose === purpose));
          }
        }
        if (editing && record.lifecycle_state === 'draft' && record.sc_approval_state === 'draft') {
          check('project: editable draft exposes submission', await session.page.getByRole('button', { name: '提交立项', exact: true }).first().isVisible());
        }
        if (record.lifecycle_state !== 'draft' || record.sc_approval_state !== 'approved') {
          check('project: start absent before approval or after startup', await session.page.getByRole('button', { name: '启动项目', exact: true }).count() === 0);
        }
        check('project: approval state remains a separate fact', authority.mainData?.sc_approval_state === record.sc_approval_state);
        if (projectSave) {
          const request = (params) => session.page.evaluate(async (params) => {
            const token = Object.entries(sessionStorage).find(([key]) => key.startsWith('sc_auth_token:'))?.[1];
            const response = await fetch('/api/v1/intent?db=sc_frontend_acceptance', {
              method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}`, 'X-Odoo-DB': 'sc_frontend_acceptance' },
              body: JSON.stringify({ intent: 'api.data', params }),
            });
            return response.json();
          }, params);
          const read = async () => {
            const result = await request({ op: 'read', model: 'project.project', ids: [10], fields: ['id', 'name', 'company_id', 'lifecycle_state', 'sc_approval_state'] });
            assert.equal(result.ok, true);
            assert.equal(result.data?.records?.length, 1);
            return result.data.records[0];
          };
          const baseline = await read();
          check('project save: exact draft object authority', baseline.id === 10 && baseline.lifecycle_state === 'draft'
            && baseline.sc_approval_state === 'draft' && baseline.name === authority.mainData.name);
          const temporaryName = `${baseline.name} [TPL53保存验证]`;
          report.projectSave = { baseline, temporaryName, restored: false };
          await fs.writeFile(path.join(out, 'project-save-recovery.json'), JSON.stringify(report.projectSave, null, 2));
          try {
            const saveAction = authority.actions.actionRuleList.find((rule) => rule.actionSemantics?.purpose === 'save_draft');
            check('project save: explicit enabled write action', saveAction?.enabled === true && saveAction.target?.operation === 'write');
            await session.page.locator('[data-field-name="name"] input').fill(temporaryName);
            projectWritePermit = { name: temporaryName };
            const response = session.page.waitForResponse((res) => {
              try { const body = res.request().postDataJSON(); return body?.intent === 'api.data' && body.params?.op === 'write'; } catch { return false; }
            });
            const [saved] = await Promise.all([response, session.page.getByRole('button', { name: saveAction.label, exact: true }).click()]);
            const result = await saved.json();
            check('project save: write accepted', result.ok === true);
            const observed = await read();
            check('project save: authoritative readback preserves lifecycle', observed.name === temporaryName
              && observed.lifecycle_state === baseline.lifecycle_state && observed.sc_approval_state === baseline.sc_approval_state);
            report.projectSave.saved = observed;
          } finally {
            projectWritePermit = null;
            const current = await read();
            assert.ok(current.name === baseline.name || current.name === temporaryName, 'project changed outside this probe; refuse restoration overwrite');
            if (current.name === temporaryName) {
              projectWritePermit = { name: baseline.name };
              const restored = await request({ op: 'write', model: 'project.project', ids: [10], vals: { name: baseline.name } });
              assert.equal(restored.ok, true, 'project restoration rejected');
            }
            projectWritePermit = null;
            assert.deepEqual(await read(), baseline, 'project baseline not restored');
            report.projectSave.restored = true;
            await fs.writeFile(path.join(out, 'project-save-recovery.json'), JSON.stringify(report.projectSave, null, 2));
            check('project save: original business values restored', true);
          }
          await session.page.reload();
          await session.page.locator('[data-field-name="name"] input').waitFor();
          check('project save: reloaded official form shows restored name', await session.page.locator('[data-field-name="name"] input').inputValue() === baseline.name);
        }
      }
      if (spec.model === 'sc.payment.execution') {
        check('paid execution: unrelated payment prerequisite absent', await session.page.getByText('新系统付款执行必须填写付款账户信息。', { exact: true }).count() === 0);
        check('paid execution: reversal entry is visible', await session.page.getByRole('button', { name: '撤销付款', exact: true }).count() === 1);
        check('paid execution: pre-payment cancellation is absent', await session.page.getByRole('button', { name: '取消', exact: true }).count() === 0);
        check('paid execution: duplicate payment is absent', await session.page.getByRole('button', { name: '已付款', exact: true }).count() === 0);
        const reversal = authority.actions?.actionRuleList?.find((action) => action.button?.name === 'action_reverse_payment');
        check('paid execution: native reversal declares confirmation', reversal?.actionSafety?.requires_confirm === true && reversal.actionSafety.classification === 'danger');
        await session.page.getByRole('button', { name: '撤销付款', exact: true }).click();
        const dialog = session.page.getByRole('dialog');
        await dialog.waitFor();
        check('paid execution: confirmation consumes declared consequence', (await dialog.innerText()).includes(reversal.actionSafety.confirm_message));
        await dialog.getByRole('button', { name: '取消', exact: true }).click();
        await dialog.waitFor({ state: 'hidden' });
        check('paid execution: cancelled confirmation dispatched no write', report.forbiddenWrites.length === 0);

      }
      for (const width of [1440, 390]) {
        await session.page.setViewportSize({ width, height: 900 });
        if (spec.model === 'sc.payment.execution') {
          const relationValue = authority.mainData.payment_request_id;
          check(`paid execution-${width}: declared relation label available`, Array.isArray(relationValue) && Boolean(relationValue[1]));
          const relation = session.page.getByRole('button').filter({ hasText: String(relationValue[1]) });
          check(`paid execution-${width}: one relation action`, await relation.count() === 1);
          const geometry = await relation.evaluate((button) => {
            const bounds = button.getBoundingClientRect();
            const walker = document.createTreeWalker(button, NodeFilter.SHOW_TEXT);
            const lines = [];
            for (let node = walker.nextNode(); node; node = walker.nextNode()) {
              if (!node.textContent?.trim()) continue;
              const range = document.createRange();
              range.selectNodeContents(node);
              for (const rect of range.getClientRects()) lines.push({ left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom });
            }
            return { bounds: { left: bounds.left, right: bounds.right, top: bounds.top, bottom: bounds.bottom }, lines };
          });
          (report.readonlyRelationGeometry ||= []).push({ model: spec.model, width, ...geometry });
          check(`paid execution-${width}: relation text fits its action`, geometry.lines.length > 0 && geometry.lines.every((line) =>
            line.left >= geometry.bounds.left - 1 && line.right <= geometry.bounds.right + 1
            && line.top >= geometry.bounds.top - 1 && line.bottom <= geometry.bounds.bottom + 1));
        }
        check(`${spec.model}-${width}: no page overflow`, await session.page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
        await session.page.screenshot({ animations: 'disabled', path: path.join(out, `${spec.model}-${width}.png`) });
      }
      if (spec.model === 'sc.payment.execution') {
        const originUrl = session.page.url();
        const relationValue = authority.mainData.payment_request_id;
        const targetId = Number(relationValue[0]);
        const fields = [];
        const walk = (nodes) => { for (const node of nodes || []) { if (node.type === 'field') fields.push(node); walk(node.children); } };
        walk(authority.layout?.containerTree);
        const entry = fields.find((field) => field.name === 'payment_request_id')?.fieldInfo?.relation_entry;
        check('paid relation: explicit authorized entry', entry?.can_read === true && entry.can_open === true && entry.model === 'payment.request');
        const waitRecordContract = (model, id) => session.page.waitForResponse(async (response) => {
          try {
            const body = response.request().postDataJSON();
            if (!String(body?.intent || '').startsWith('ui.contract')) return false;
            const current = findRecordAuthority(await response.json());
            return current?.model === model && Number(current.mainData?.id) === id;
          } catch { return false; }
        });
        const targetResponse = waitRecordContract(entry.model, targetId);
        await session.page.getByRole('button').filter({ hasText: String(relationValue[1]) }).click();
        const targetAuthority = findRecordAuthority(await (await targetResponse).json());
        await session.page.waitForURL((url) => url.pathname.endsWith(`/payment.request/${targetId}`));
        const targetUrl = new URL(session.page.url());
        check('paid relation: target uses declared menu and action', Number(targetUrl.searchParams.get('menu_id')) === Number(entry.menu_id)
          && Number(targetUrl.searchParams.get('action_id')) === Number(entry.action_id));
        const sourceUrl = new URL(originUrl);
        check('paid relation: return context preserves source', decodeURIComponent(targetUrl.searchParams.get('return_url') || '') === `${sourceUrl.pathname}${sourceUrl.search}`
          && targetUrl.searchParams.get('return_model') === spec.model && targetUrl.searchParams.get('return_field') === 'payment_request_id');
        const targetProfile = targetAuthority.status.effectiveRenderProfile;
        await session.page.locator(targetProfile === 'readonly'
          ? '[data-detail-composition="official-standard-detail"][data-state="ok"]'
          : '[data-form-composition="official-standard-form"][data-state="ok"]').waitFor();
        check('paid relation: target identity and declared renderer', Number(targetAuthority.mainData.id) === targetId
          && await session.page.locator('[data-field-fail-closed]').count() === 0);
        report.paidRelationNavigation = { source: { model: spec.model, id: record.id, url: originUrl }, target: { model: entry.model, id: targetId, url: targetUrl.href, profile: targetProfile } };
        await session.page.goBack();
        await session.page.waitForURL(originUrl);
        const restoredPage = session.page.locator(`[data-form-model="${spec.model}"][data-form-record="${record.id}"][data-detail-composition="official-standard-detail"][data-state="ok"]`);
        await restoredPage.waitFor();
        check('paid relation: browser back restores exact source', session.page.url() === originUrl && await restoredPage.count() === 1);
        await restoredPage.getByRole('button', { name: '撤销付款', exact: true }).waitFor({ state: 'visible' });
        // The status badge includes the accessibility prefix “状态：”; its
        // declared title identifies the label without assuming a bare text node.
        await restoredPage.getByLabel('业务状态', { exact: true }).getByTitle('已付款', { exact: true }).waitFor({ state: 'visible' });
        const terminalActions = {
          reversal: await restoredPage.getByRole('button', { name: '撤销付款', exact: true }).count(),
          duplicatePayment: await restoredPage.getByRole('button', { name: '已付款', exact: true }).count(),
        };
        check('paid relation: cached source keeps terminal actions', terminalActions.reversal === 1 && terminalActions.duplicatePayment === 0, terminalActions);
        await session.page.screenshot({ animations: 'disabled', path: path.join(out, 'paid-relation-return.png') });
        check('paid relation: navigation dispatched no business write', report.forbiddenWrites.length === 0);
      }
      await session.ctx.close();
    }
  } else if (process.env.TPL07_SCOPE === 'detail-state') {
    const finance = await login('fixture_role_finance');
    await form(finance.page, '/r/payment.request/1813?menu_id=545&action_id=775', 'detail-state', 'readonly');
    let authority = report.recordAuthority;
    check('detail state: effective record authority received', authority?.model === 'payment.request');
    check('detail state: allowed draft has no invented denial', await finance.page.locator('[data-record-action-denials]').count() === 0);
    const statePolicy = authority.deletePolicy;
    const candidate = await finance.page.evaluate(async ({ field, allowed, project, company }) => {
      const token = Object.entries(sessionStorage).find(([key]) => key.startsWith('sc_auth_token:'))?.[1];
      const domain = [[field, 'not in', allowed]];
      if (project) domain.push(['project_id', '=', project]);
      if (company) domain.push(['company_id', '=', company]);
      const response = await fetch('/api/v1/intent?db=sc_frontend_acceptance', {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}`, 'X-Odoo-DB': 'sc_frontend_acceptance' },
        body: JSON.stringify({ intent: 'api.data', params: { op: 'list', model: 'payment.request', fields: ['id', field], domain, limit: 1 } }),
      });
      return response.json();
    }, { field: statePolicy.state_field, allowed: statePolicy.allowed_states,
      project: Array.isArray(authority.mainData.project_id) ? authority.mainData.project_id[0] : authority.mainData.project_id,
      company: Array.isArray(authority.mainData.company_id) ? authority.mainData.company_id[0] : authority.mainData.company_id });
    check('detail state: existing restricted record available in same scope', candidate.ok === true && candidate.data?.records?.length === 1);
    report.restrictedRecord = candidate.data.records[0];
    await form(finance.page, `/r/payment.request/${report.restrictedRecord.id}?menu_id=545&action_id=775`, 'detail-state-restricted', 'readonly');
    authority = report.recordAuthority;
    const caps = authority.status.effectiveRecordCapabilities;
    const reasons = authority.status.recordDeniedReasons || {};
    const policy = authority.deletePolicy || {};
    const stateBlocked = policy.policy_kind === 'state_limited_business_document'
      && policy.allowed_states?.length && authority.mainData?.[policy.state_field]
      && !policy.allowed_states.includes(authority.mainData[policy.state_field]);
    const declaredDenial = ['write', 'unlink'].some((op) => caps[op] !== true && reasons[op])
      || (policy.allowed === false && policy.reason_code) || (stateBlocked && policy.denied_reason_code);
    check('detail state: restriction explicitly declared', Boolean(declaredDenial));
    for (const width of [1440, 390]) {
      await finance.page.setViewportSize({ width, height: width === 1440 ? 900 : 844 });
      const notice = finance.page.locator('[data-record-action-denials]');
      check(`detail-state-${width}: explicit denials drive feedback`, await notice.count() === (declaredDenial ? 1 : 0));
      if (declaredDenial) {
        check(`detail-state-${width}: official alert owns feedback`, await notice.getAttribute('data-semantic-driver') === 'tdesign-alert');
        check(`detail-state-${width}: feedback explains restriction`, /不可编辑|不可删除/.test(await notice.innerText()));
      }
      check(`detail-state-${width}: no page overflow`, await finance.page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
      await finance.page.screenshot({ animations: 'disabled', path: path.join(out, `detail-state-${width}.png`) });
    }
    await finance.ctx.close();
  } else if (process.env.TPL07_SCOPE === 'favorite-recovery') {
    const finance = await login('fixture_role_finance');
    await list(finance.page, 545, 'recovery-list');
    report.recovery = await finance.page.evaluate(async () => {
      const token = Object.entries(sessionStorage).find(([key]) => key.startsWith('sc_auth_token:'))?.[1];
      const response = await fetch('/api/v1/intent?db=sc_frontend_acceptance', {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}`, 'X-Odoo-DB': 'sc_frontend_acceptance' },
        body: JSON.stringify({ intent: 'api.data', params: { op: 'list', model: 'ir.filters', fields: ['id', 'name', 'user_id', 'model_id', 'action_id', 'create_date', 'is_default'], domain: [['name', '=', '仅检查表单，不保存'], ['user_id', '=', 30], ['model_id', '=', 'payment.request'], ['action_id', '=', 775]], limit: 2 } }),
      });
      return { status: response.status, body: await response.json() };
    });
    check('recovery: authoritative read succeeded', report.recovery.body.ok === true);
    check('recovery: probe records are absent', report.recovery.body.data.records.length === 0);
    await finance.page.getByRole('button', { name: '展开搜索菜单', exact: true }).click();
    check('recovery: menu reflects removal', await finance.page.getByText('仅检查表单，不保存', { exact: true }).count() === 0);
    await finance.page.reload();
    await finance.page.locator('[data-list-card-container="official"]').waitFor();
    await finance.page.getByRole('button', { name: '展开搜索菜单', exact: true }).click();
    check('recovery: warm contract menu remains restored', await finance.page.getByText('仅检查表单，不保存', { exact: true }).count() === 0);
    check('recovery: cache-hit delivery exercised', report.projectionCaches?.some((entry) => ['hot', 'persisted'].includes(entry.status)));
    await finance.ctx.close();
  } else if (['favorites', 'favorites-failure', 'favorite-recovery'].includes(process.env.TPL07_SCOPE)) {
    await favoritesScope();
  } else if (process.env.TPL07_SCOPE === 'navigation') {
    await navigationScope();
  } else if (process.env.TPL07_SCOPE === 'style') {
    await styleScope();
  } else if (process.env.TPL07_SCOPE === 'detail') {
    const finance = await login('fixture_role_finance');
    await form(finance.page, '/r/payment.request/1813?menu_id=545&action_id=775', 'payment-readonly', 'readonly');
    check('payment: existing company fact preserved', await finance.page.getByText('FE Company A', { exact: true }).count() > 0);
    report.paymentFactText = await finance.page.locator('[data-detail-facts]').allTextContents();
    await finance.page.setViewportSize({ width: 390, height: 844 });
    check('payment detail: narrow page contained', await finance.page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1));
    await finance.page.screenshot({ path: path.join(out, 'payment-readonly-narrow.png') });
    await finance.ctx.close();
    const contract = await login('fixture_role_contract_operator');
    await form(contract.page, '/r/sc.general.contract/11?menu_id=662', 'contract-readonly', 'readonly');
    await contract.ctx.close();
  } else if (process.env.TPL07_SCOPE !== 'additional') {
  const finance = await login('fixture_role_finance');
  const p = finance.page;
  await list(p, 545, 'payment-list');
  const pager = p.locator('[data-semantic-component="ScPagination"]');
  await pager.locator('.t-pagination__select input').click();
  await p.locator('li.t-select-option:visible').filter({ hasText: /^10 条\/页$/ }).click();
  await p.waitForTimeout(1500);
  const before = report.calls.filter((call) => call.model === 'payment.request').at(-1);
  await pager.locator('.t-pagination__btn-next').click();
  await p.waitForTimeout(1800);
  const next = report.calls.filter((call) => call.model === 'payment.request').at(-1);
  check('payment: server next page', next.offset === 10 && next.ids.length > 0 && JSON.stringify(next.ids) !== JSON.stringify(before.ids), { ids: next.ids });
  // The record a list opens declares its own mode: a closed row is a readonly
  // detail, so the probe binds the opened page to the identity of the row it
  // clicked and to the composition the contract declared for it, instead of
  // assuming an editable draft sits first on the page. What must hold either
  // way is that the page is classified by the contract (never an unclassified
  // fallback) and keeps the list context it was opened from.
  const openedRow = p.locator('.flat-table tbody tr[data-record-key]').filter({ has: p.locator('td') }).first();
  const openedRecordKey = await openedRow.getAttribute('data-record-key');
  await openedRow.click();
  await p.locator(`[data-form-record="${openedRecordKey}"][data-state="ok"]`).waitFor();
  check('payment: opened record identity matches the clicked row', await p.locator(`[data-form-record="${openedRecordKey}"]`).count() === 1, { openedRecordKey });
  check(
    'payment: opened record composition follows the contract declaration',
    await p.locator('[data-form-composition-reason="contract-record-view"], [data-detail-composition-reason="contract-readonly-record-view"]').count() === 1,
  );
  check(
    'payment: opened record is not an unclassified fallback',
    await p.locator('[data-form-composition-reason="contract-view-not-classified"], [data-detail-composition-reason="contract-view-not-classified"]').count() === 0,
  );
  check('payment: return context carried', new URL(p.url()).searchParams.get('list_offset') === '10');
  await p.goBack();
  await p.locator('[data-list-card-container="official"]').waitFor();
  await p.waitForTimeout(1500);
  check('payment: return keeps page and set', JSON.stringify(report.calls.filter((call) => call.model === 'payment.request').at(-1).ids) === JSON.stringify(next.ids));
  await form(p, '/f/payment.request/1813?menu_id=545&action_id=775', 'payment-master-detail');
  check('payment: master detail extension preserved', await p.locator('[data-field-type="one2many"]').count() > 0);
  // The introduce action and its dialog must render the terms the effective
  // contract declares, and a contract gap must surface instead of being
  // rebuilt locally from production copy.
  const declaredIntroduce = report.introduceContract;
  check('payment: introduce contract published to the page', Boolean(declaredIntroduce?.dialog?.title && declaredIntroduce?.introduceLabel));
  const introduceEntry = p.locator('[data-contract-entry-label]');
  check('payment: introduce entry carries the declared label', await introduceEntry.count() === 1);
  check(
    'payment: introduce entry text is the declared label',
    (await introduceEntry.innerText()).trim() === String(declaredIntroduce.introduceLabel).trim(),
  );
  check('payment: no introduce contract gap rendered', await p.locator('[data-contract-semantic-gap]').count() === 0);
  await introduceEntry.click();
  const introduceDialog = p.locator('[data-dialog-purpose="payment-settlement-introduce"]');
  await introduceDialog.waitFor();
  check(
    'payment: introduce dialog uses the declared title',
    await introduceDialog.getByText(String(declaredIntroduce.dialog.title), { exact: false }).count() > 0,
  );
  check(
    'payment: introduce dialog uses the declared confirm label',
    await p.getByRole('button', { name: String(declaredIntroduce.dialog.confirmLabel), exact: true }).count() > 0,
  );
  await p.screenshot({ path: path.join(out, 'payment-introduce-dialog.png') });
  await p.keyboard.press('Escape');
  await p.locator('[data-dialog-purpose="payment-settlement-introduce"]').waitFor({ state: 'detached' });
  await form(p, '/r/payment.request/1813?menu_id=545&action_id=775', 'payment-readonly', 'readonly');
  await p.setViewportSize({ width: 390, height: 844 });
  check('payment detail: narrow page contained', await p.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1));
  await p.screenshot({ path: path.join(out, 'payment-readonly-narrow.png') });
  await finance.ctx.close();

  const contract = await login('fixture_role_contract_operator');
  await list(contract.page, 662, 'contract-list');
  await form(contract.page, '/r/sc.general.contract/11?menu_id=662', 'contract-readonly', 'readonly');
  await contract.ctx.close();
  }

  if (!['expense-policy', 'favorite-lifecycle', 'favorite-lifecycle-resume', 'favorite-active-delete', 'favorite-active-delete-resume', 'task-authority', 'approval-actions', 'detail', 'detail-state', 'style', 'navigation', 'favorites', 'favorites-failure', 'favorite-recovery'].includes(process.env.TPL07_SCOPE)) {
  const admin = await login('fixture_role_config_admin');
  // Resolve a non-pilot entry from authorized navigation instead of model IDs.
  await admin.page.getByPlaceholder('搜索菜单...').fill('客户档案');
  await admin.page.getByText('客户档案', { exact: true }).first().click();
  await admin.page.locator('[data-list-card-container="official"]').waitFor();
  check('non-pilot standard list: official default', await admin.page.locator('[data-list-composition-reason="contract-collection-view"]').count() === 1);
  await admin.page.screenshot({ path: path.join(out, 'customer-list.png') });
  await admin.ctx.close();
  }
  check('no page exceptions', report.errors.length === 0);
  check('no undeclared business writes attempted', report.forbiddenWrites.length === 0);
  report.status = 'passed';
} catch (error) {
  report.status = 'failed';
  report.error = error.message;
  if (['approval-actions', 'expense-policy'].includes(process.env.TPL07_SCOPE)) {
    report.failurePages = [];
    for (const ctx of browser.contexts()) for (const page of ctx.pages()) {
      report.failurePages.push({ url: page.url(), text: (await page.locator('body').innerText()).slice(0, 8000),
        surfaces: await page.locator('[data-product-page-mode], [data-form-composition], [data-detail-composition], [data-semantic-component="ScForm"]').evaluateAll((nodes) => nodes.map((node) => ({ tag: node.tagName, attributes: Object.fromEntries([...node.attributes].filter((attr) => attr.name.startsWith('data-')).map((attr) => [attr.name, attr.value])) }))) });
      await page.screenshot({ path: path.join(out, `failure-${report.failurePages.length}.png`) });
    }
  }
  process.exitCode = 1;
} finally {
  await Promise.allSettled([...pendingProbeAborts].map((abort) => abort()));
  await browser.close();
  if (expenseSuccess || diarySuccess || eventSuccess) {
    try { await expenseCleanup('final'); }
    catch (error) { report.status = 'failed'; report.cleanupError = error.message; process.exitCode = 1; }
  }
  await fs.writeFile(path.join(out, 'report.json'), JSON.stringify(report, null, 2));
  console.log(`[standard_page_type_browser] ${report.status} assertions=${report.assertions.length} report=${out}/report.json`);
}
