import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { createRequire } from 'node:module';
import path from 'node:path';

const require = createRequire(new URL('../../frontend/apps/web/package.json', import.meta.url));
const { chromium } = require('playwright');

const baseUrl = String(process.env.BASE_URL || 'http://127.0.0.1:5175').replace(/\/$/, '');
const dbName = String(process.env.DB_NAME || 'sc_demo');
const login = String(process.env.E2E_LOGIN || 'wutao');
const password = String(process.env.E2E_PASSWORD || '');
const artifactsDir = path.resolve(process.env.ARTIFACTS_DIR || 'artifacts/frontend-dynamic-list-optional-columns');
const routes = process.env.DYNAMIC_LIST_TARGETS_JSON
  ? JSON.parse(process.env.DYNAMIC_LIST_TARGETS_JSON)
  : [{ name: 'customer', route: `/a/786?db=${encodeURIComponent(dbName)}&menu_id=598`, hiddenLabel: '来源项目' }];

assert(password, 'E2E_PASSWORD is required');
assert(Array.isArray(routes) && routes.length, 'DYNAMIC_LIST_TARGETS_JSON must contain at least one target');

const technicalLabel = /^(?:sc_|x_)[a-z0-9_]+$/i;
const hasChinese = /[\u3400-\u9fff]/;

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

async function inspectTarget(browser, target) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, locale: 'zh-CN' });
  const consoleErrors = [];
  const pageErrors = [];
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  page.on('pageerror', (error) => pageErrors.push(error.message));
  await authenticate(page);
  await page.goto(`${baseUrl}${target.route}`, { waitUntil: 'domcontentloaded' });
  await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => {});
  await page.getByRole('button', { name: /列设置/ }).waitFor({ state: 'visible' });

  const defaultHeaders = await visibleHeaderLabels(page);
  const businessHeaders = defaultHeaders.filter((label) => label !== '序号');
  assert.equal(defaultHeaders.filter((label) => technicalLabel.test(label)).length, 0, `${target.name}: default technical field headers leaked`);
  assert.equal(businessHeaders.filter((label) => !hasChinese.test(label)).length, 0, `${target.name}: visible labels are not fully Chinese`);
  await page.screenshot({ path: path.join(artifactsDir, `${target.name}-desktop-default.png`), fullPage: true });

  await page.getByRole('button', { name: /列设置/ }).click();
  const choices = page.locator('.column-choice');
  const choiceLabels = await choices.locator('span').allTextContents();
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
  const hiddenChoice = choices.filter({ hasText: target.hiddenLabel }).first();
  await hiddenChoice.waitFor({ state: 'visible' });
  const checkbox = hiddenChoice.locator('input[type="checkbox"]');
  assert.equal(await checkbox.isChecked(), false, `${target.name}: optional=hide field is enabled by default`);
  await checkbox.check();
  await page.waitForTimeout(500);
  assert((await visibleHeaderLabels(page)).includes(target.hiddenLabel), `${target.name}: hidden field cannot be enabled through column settings`);
  await page.screenshot({ path: path.join(artifactsDir, `${target.name}-desktop-hidden-enabled.png`), fullPage: true });
  await page.getByRole('button', { name: '恢复默认' }).click();
  await page.waitForTimeout(500);
  assert(!(await visibleHeaderLabels(page)).includes(target.hiddenLabel), `${target.name}: reset did not restore optional=hide default`);

  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => {});
  const mobileText = await page.locator('.mobile-record-card, .record-card, [class*=mobile][class*=card]').allTextContents();
  assert.equal(mobileText.some((text) => /\bsc_(?:source|business)_[a-z0-9_]+\b/i.test(text)), false, `${target.name}: mobile cards leak technical fields`);
  assert.equal(mobileText.some((text) => uncheckedLabels.some((label) => text.includes(label))), false, `${target.name}: optional=hide field leaked into mobile cards`);
  await page.screenshot({ path: path.join(artifactsDir, `${target.name}-mobile-default.png`), fullPage: true });

  const result = { name: target.name, route: target.route, defaultHeaders, choiceLabels, consoleErrors, pageErrors };
  assert.deepEqual(consoleErrors, [], `${target.name}: console errors`);
  assert.deepEqual(pageErrors, [], `${target.name}: page errors`);
  await page.close();
  return result;
}

await fs.mkdir(artifactsDir, { recursive: true });
const browser = await chromium.launch({ headless: true });
try {
  const results = [];
  for (const target of routes) results.push(await inspectTarget(browser, target));
  await fs.writeFile(path.join(artifactsDir, 'report.json'), `${JSON.stringify({ baseUrl, dbName, results }, null, 2)}\n`, 'utf8');
  console.log(`[frontend_dynamic_list_optional_columns_browser] PASS ${results.length}/${routes.length}`);
} finally {
  await browser.close();
}
