import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { captureReleasedNavigation } from './released_navigation_target.mjs';
import { resolveAcceptanceEnvironment } from './lib/frontend_acceptance_environment.mjs';
import { acquireAcceptanceLease } from './lib/frontend_acceptance_lease.mjs';
import { launchAcceptanceChromium } from './playwright_runtime.mjs';

const acceptance = resolveAcceptanceEnvironment({ tool: 'dynamic-list-optional-columns' });
const baseUrl = acceptance.baseUrl;
const dbName = acceptance.database;
const login = String(process.env.E2E_LOGIN || acceptance.login || acceptance.roleBindings.project_manager || '');
const password = String(process.env.E2E_PASSWORD || acceptance.password || process.env.SC_ACCEPTANCE_FIXTURE_PASSWORD || '');
const artifactsDir = path.resolve(process.env.ARTIFACTS_DIR || acceptance.runArtifactRoot);
const routes = process.env.DYNAMIC_LIST_TARGETS_JSON
  ? JSON.parse(process.env.DYNAMIC_LIST_TARGETS_JSON)
  : [
    {
      name: 'customer',
      actionXmlid: 'smart_construction_core.action_sc_customer_partner',
      requiredHeaders: ['单位名称', '客户类型', '地区', '联系人', '电话', '负责人'],
      hiddenLabels: ['业务角色', '业务事实依据', '来源项目', '来源单据状态', '来源客商编码'],
      hiddenSelectableLabel: '统一社会信用代码',
    },
    {
      name: 'supplier',
      actionXmlid: 'smart_construction_core.action_sc_supplier_partner',
      requiredHeaders: ['单位名称', '供应商类型', '地区', '联系人', '电话', '负责人'],
      hiddenLabels: ['业务角色', '业务事实依据', '来源项目', '来源单据状态', '来源客商编码'],
      hiddenSelectableLabel: '统一社会信用代码',
    },
    {
      name: 'project',
      actionXmlid: 'smart_construction_core.action_sc_project_list',
      requiredHeaders: ['项目名称', '项目编号', '项目状态', '项目负责人'],
      hiddenLabels: ['项目经理'],
      hiddenSelectableLabel: '项目经理',
    },
  ];

assert(password, 'E2E_PASSWORD is required');
assert(Array.isArray(routes) && routes.length, 'DYNAMIC_LIST_TARGETS_JSON must contain at least one target');

const technicalLabel = /^(?:sc_|x_)[a-z0-9_]+$/i;
const hasChinese = /[\u3400-\u9fff]/;
const columnChoiceSelector = '.list-surface-column-choice';

async function authenticate(page) {
  await page.goto(`${baseUrl}/login?db=${encodeURIComponent(dbName)}`, { waitUntil: 'domcontentloaded' });
  await page.locator('input').first().fill(login);
  await page.locator('input[type="password"]').fill(password);
  if (await page.locator('input').count() >= 3) {
    const dbInput = page.locator('input').nth(2);
    if (await dbInput.isEnabled().catch(() => false)) await dbInput.fill(dbName);
  }
  await page.locator('button[type="submit"]').click();
  await page.waitForFunction(() => !location.pathname.includes('/login'));
  await page.locator('input[placeholder*="搜索菜单"]').waitFor({ state: 'visible' });
}

async function visibleHeaderLabels(page) {
  return page.locator('thead th').evaluateAll((nodes) => nodes
    .filter((node) => {
      const rect = node.getBoundingClientRect();
      const style = getComputedStyle(node);
      return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
    })
    .map((node) => String(node.textContent || '').replace(/\s+/g, ' ').trim())
    .filter(Boolean));
}

async function waitForListReady(page) {
  await page.waitForFunction(() => {
    const main = document.querySelector('#main-content');
    const text = String(main?.textContent || '');
    const loading = /加载中|正在载入|正在加载/.test(text);
    const hasTable = Boolean(main?.querySelector('thead th'));
    const hasEmptyState = Boolean(main?.querySelector('.list-empty, .sc-empty, [data-empty-state]'));
    return !loading && (hasTable || hasEmptyState);
  }, null, { timeout: 45_000 });
}

async function resetColumnPreferences(page) {
  const picker = page.getByRole('button', { name: /列设置/ });
  if ((await picker.getAttribute('aria-expanded')) !== 'true') await picker.click();
  await page.getByRole('button', { name: '恢复默认' }).click();
  // A no-op reset is allowed to remain idle; the reload and projection assertions below
  // are the authoritative proof that persisted preferences returned to defaults.
  await page.getByText('已保存', { exact: true }).first().waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {});
  await page.waitForTimeout(500);
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => {});
  await waitForListReady(page);
  await picker.waitFor({ state: 'visible' });
}

async function inspectTarget(browser, target) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, locale: 'zh-CN' });
  const navigation = captureReleasedNavigation(page);
  const consoleErrors = [];
  const pageErrors = [];
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  page.on('pageerror', (error) => pageErrors.push(error.message));
  await authenticate(page);
  const released = target.actionXmlid ? await navigation.target(target.actionXmlid) : null;
  const route = String(target.route || (released ? `/a/${released.action_id}?menu_id=${released.menu_id}` : '')).trim();
  assert(route, `${target.name}: governed navigation route is required`);
  await page.goto(`${baseUrl}${route}`, { waitUntil: 'domcontentloaded' });
  await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => {});
  await waitForListReady(page);
  await page.getByRole('button', { name: /列设置/ }).waitFor({ state: 'visible' });
  await resetColumnPreferences(page);

  const defaultHeaders = await visibleHeaderLabels(page);
  const requiredHeaders = Array.isArray(target.requiredHeaders) ? target.requiredHeaders : [];
  const hiddenLabels = Array.isArray(target.hiddenLabels)
    ? target.hiddenLabels
    : [target.hiddenLabel].filter(Boolean);
  const hiddenSelectableLabel = String(target.hiddenSelectableLabel || hiddenLabels[0] || '');
  await page.screenshot({ path: path.join(artifactsDir, `${target.name}-desktop-default.png`), fullPage: true });

  await page.getByRole('button', { name: /列设置/ }).click();
  const choices = page.locator(columnChoiceSelector);
  const choiceLabels = await choices.locator('span').allTextContents();
  const checkedLabels = await choices.evaluateAll((nodes) => nodes
    .filter((node) => node.querySelector('input[type="checkbox"]')?.checked)
    .map((node) => String(node.textContent || '').replace(/\s+/g, ' ').trim())
    .filter(Boolean));
  const renderedBusinessHeaders = defaultHeaders.filter((label) => label !== '序号');
  const effectiveVisibleLabels = renderedBusinessHeaders.length ? renderedBusinessHeaders : checkedLabels;
  assert.equal(defaultHeaders.filter((label) => technicalLabel.test(label)).length, 0, `${target.name}: default technical field headers leaked`);
  assert.equal(effectiveVisibleLabels.filter((label) => !hasChinese.test(label)).length, 0, `${target.name}: visible labels are not fully Chinese`);
  assert.deepEqual(requiredHeaders.filter((label) => !effectiveVisibleLabels.includes(label)), [], `${target.name}: required business headers are missing`);
  assert.deepEqual(hiddenLabels.filter((label) => effectiveVisibleLabels.includes(label)), [], `${target.name}: default-hidden business trace headers leaked`);
  assert.equal(choiceLabels.filter((label) => technicalLabel.test(label.trim())).length, 0, `${target.name}: column settings expose technical labels`);
  assert.equal(choiceLabels.filter((label) => !hasChinese.test(label)).length, 0, `${target.name}: column settings labels are not fully Chinese`);
  const uncheckedLabels = await choices.evaluateAll((nodes) => nodes
    .filter((node) => !node.querySelector('input[type="checkbox"]')?.checked)
    .map((node) => String(node.textContent || '').replace(/\s+/g, ' ').trim())
    .filter(Boolean));
  assert.equal(
    uncheckedLabels.filter((label) => defaultHeaders.includes(label)).length,
    0,
    `${target.name}: default-hidden fields leaked into visible headers`,
  );
  assert(hiddenSelectableLabel, `${target.name}: a selectable optional=hide field is required`);
  const hiddenChoice = choices.filter({ hasText: hiddenSelectableLabel }).first();
  await hiddenChoice.waitFor({ state: 'visible' });
  const checkbox = hiddenChoice.locator('input[type="checkbox"]');
  assert.equal(await checkbox.isChecked(), false, `${target.name}: optional=hide field is enabled by default`);
  await checkbox.check();
  await page.getByText('已保存', { exact: true }).first().waitFor({ state: 'visible', timeout: 10_000 });
  try {
    if (defaultHeaders.length) {
      assert((await visibleHeaderLabels(page)).includes(hiddenSelectableLabel), `${target.name}: hidden field cannot be enabled through column settings`);
    } else {
      await page.waitForFunction((label) => Array.from(document.querySelectorAll('.list-surface-column-choice'))
        .some((node) => String(node.textContent || '').replace(/\s+/g, ' ').trim().includes(label)
          && node.querySelector('input[type="checkbox"]')?.checked), hiddenSelectableLabel, { timeout: 10_000 });
    }
    await page.screenshot({ path: path.join(artifactsDir, `${target.name}-desktop-hidden-enabled.png`), fullPage: true });
  } finally {
    await resetColumnPreferences(page);
  }
  if (defaultHeaders.length) {
    assert(!(await visibleHeaderLabels(page)).includes(hiddenSelectableLabel), `${target.name}: reset did not restore optional=hide default`);
  } else {
    await page.getByRole('button', { name: /列设置/ }).click();
    const restoredChoice = page.locator(columnChoiceSelector).filter({ hasText: hiddenSelectableLabel }).first().locator('input[type="checkbox"]');
    assert.equal(await restoredChoice.isChecked(), false, `${target.name}: reset did not restore optional=hide default on an empty list`);
    await page.getByRole('button', { name: /列设置/ }).click();
  }

  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => {});
  const mobileText = await page.locator('.mobile-record-card, .record-card, [class*=mobile][class*=card]').allTextContents();
  assert.equal(mobileText.some((text) => /\bsc_(?:source|business)_[a-z0-9_]+\b/i.test(text)), false, `${target.name}: mobile cards leak technical fields`);
  assert.equal(mobileText.some((text) => uncheckedLabels.some((label) => text.includes(label))), false, `${target.name}: optional=hide field leaked into mobile cards`);
  assert.deepEqual(hiddenLabels.filter((label) => mobileText.some((text) => text.includes(label))), [], `${target.name}: mobile cards leak business trace fields`);
  await page.screenshot({ path: path.join(artifactsDir, `${target.name}-mobile-default.png`), fullPage: true });

  const result = { name: target.name, actionXmlid: target.actionXmlid || '', route, defaultHeaders, checkedLabels, choiceLabels, consoleErrors, pageErrors };
  assert.deepEqual(consoleErrors, [], `${target.name}: console errors`);
  assert.deepEqual(pageErrors, [], `${target.name}: page errors`);
  await page.close();
  return result;
}

await fs.mkdir(artifactsDir, { recursive: true });
const lease = await acquireAcceptanceLease({ environment: acceptance, mode: 'shared-read', owner: { tool: 'dynamic-list-optional-columns' } });
let browser;
try {
  browser = await launchAcceptanceChromium(acceptance, { headless: true });
  const results = [];
  for (const target of routes) results.push(await inspectTarget(browser, target));
  await fs.writeFile(path.join(artifactsDir, 'report.json'), `${JSON.stringify({ baseUrl, dbName, results }, null, 2)}\n`, 'utf8');
  console.log(`[frontend_dynamic_list_optional_columns_browser] PASS ${results.length}/${routes.length}`);
} finally {
  await browser?.close();
  await lease.release();
}
