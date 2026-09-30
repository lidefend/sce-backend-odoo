import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { launchChromium } from '../../../../scripts/verify/playwright_runtime.mjs';

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
      ...(process.env.TPL07_SCOPE === 'task-authority' ? { structure: node.formStructureContract, layout: node.layoutContract, actions: node.actionContract } : {}) };
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

async function login(role) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 950 }, locale: 'zh-CN' });
  const page = await ctx.newPage();
  page.on('pageerror', (error) => report.errors.push(error.message));
  await page.route('**/api/v1/intent*', async (route) => {
    const body = route.request().postDataJSON();
    if ((body?.intent === 'api.data' && !['list', 'read'].includes(body.params?.op))
      || ['search.favorite.set', 'api.data.create', 'api.data.write', 'api.data.unlink'].includes(body?.intent)) {
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
        if (body.intent === 'system.init') report.productVersion = result.data?.product_version;
      }
      if (body?.intent === 'api.data' && body.params?.op === 'list') {
        const result = await response.json();
        report.calls.push({ role, model: body.params.model, domain: body.params.domain, order: body.params.order, offset: body.params.offset || 0, limit: body.params.limit, ids: result.data?.records?.map((row) => row.id) || [] });
      }
      if (typeof body?.intent === 'string' && body.intent.startsWith('ui.contract')) {
        const contract = await response.json();
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
  if (process.env.TPL07_SCOPE === 'task-authority') {
    const finance = await login('fixture_role_finance');
    await form(finance.page, '/f/payment.request/1813?menu_id=545&action_id=775', 'task-authority');
    const authority = report.taskAuthorities?.['payment.request'];
    check('task: actual payment authority received', authority?.model === 'payment.request');
    check('task: native tree is sole layout authority', authority.structure?.layoutPolicy === 'container_tree_authority');
    check('task: retired slots remain empty', Array.isArray(authority.structure?.slots) && authority.structure.slots.length === 0);
    check('task: effective native tree is present', Boolean(authority.layout?.containerTree));
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

  if (!['task-authority', 'detail', 'detail-state', 'style', 'navigation', 'favorites', 'favorites-failure', 'favorite-recovery'].includes(process.env.TPL07_SCOPE)) {
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
  check('no business writes attempted', report.forbiddenWrites.length === 0);
  report.status = 'passed';
} catch (error) {
  report.status = 'failed';
  report.error = error.message;
  process.exitCode = 1;
} finally {
  await Promise.allSettled([...pendingProbeAborts].map((abort) => abort()));
  await browser.close();
  await fs.writeFile(path.join(out, 'report.json'), JSON.stringify(report, null, 2));
  console.log(`[standard_page_type_browser] ${report.status} assertions=${report.assertions.length} report=${out}/report.json`);
}
