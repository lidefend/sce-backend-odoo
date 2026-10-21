import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { launchChromium } from './playwright_runtime.mjs';

const target = JSON.parse(process.env.FRONTEND_BASE_CONFIGURATION_DOMAIN_TARGET || '{}');
const base = process.env.FRONTEND_URL;
const output = path.resolve('.runtime/agent-runs/PRODUCT-ITERATION-V2-20261020/parameter-browser');
assert.equal(target.database, 'sc_dev_demo');
assert.ok(target.user?.login && base && process.env.E2E_PASSWORD);
fs.mkdirSync(output, { recursive: true });
const report = { status: 'failed', head: process.env.CANDIDATE_HEAD, stage: 'head_plus_dirty_scope', database: target.database, principal: target.user.xmlid, cases: [], errors: [], mutationAttempts: [] };
const browser = await launchChromium();
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
const page = await context.newPage();
function params(request) {
  try { return request.postDataJSON() || {}; } catch { return {}; }
}
function find(value, key) {
  if (!value || typeof value !== 'object') return undefined;
  if (Object.hasOwn(value, key)) return value[key];
  for (const child of Object.values(value)) { const hit = find(child, key); if (hit !== undefined) return hit; }
}
// No parameter writes are permitted in this exact read-only surface check.
await page.route('**/*', async route => {
  const intent = params(route.request()).intent || '';
  if (['sc.product.system_parameter.publish', 'sc.product.system_parameter.rollback'].includes(intent)) {
    report.mutationAttempts.push(intent);
    return route.abort();
  }
  return route.continue();
});
page.on('pageerror', error => report.errors.push(error.message));
try {
  await page.goto(`${base}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.locator('#login-username').fill(target.user.login);
  await page.locator('#login-password').fill(process.env.E2E_PASSWORD);
  const db = page.getByLabel(/数据库/);
  if (await db.count() === 1 && await db.isVisible() && await db.isEnabled()) await db.fill(target.database);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 45000 });
  const catalogResponse = page.waitForResponse(response => params(response.request()).intent === 'sc.product.system_parameter.catalog', { timeout: 30000 });
  await page.goto(`${base}/admin/system-parameters`, { waitUntil: 'domcontentloaded' });
  const catalog = find(await (await catalogResponse).json(), 'parameters');
  assert.ok(Array.isArray(catalog) && catalog.length > 0, 'non-empty runtime catalog');
  await page.locator('[data-semantic-component="SystemParameterCatalogView"]').waitFor();
  for (const key of ['approval_mode', 'default_payment_terms']) {
    const declaration = catalog.find(row => row.key === key);
    assert.equal(declaration?.available, true, `${key} backed availability`);
    const card = page.locator(`[data-parameter-key="${key}"]`);
    await card.waitFor();
    assert.ok((await card.innerText()).includes(declaration.label));
    assert.equal(await card.getByRole('button', { name: /^发布$/ }).isDisabled(), true);
    const response = page.waitForResponse(res => params(res.request()).intent === 'sc.product.system_parameter.preview', { timeout: 30000 });
    await card.getByRole('button', { name: '预览影响', exact: true }).click();
    const received = await response;
    const request = params(received.request());
    assert.equal(request.params.parameter_key, key);
    assert.equal(request.params.proposed_value, declaration.current_value ?? declaration.default);
    const preview = find(await received.json(), 'impact');
    assert.ok(preview?.summary && preview?.surfaces?.length, 'runtime impact facts');
    const panel = page.locator('[data-semantic-component="SystemParameterImpactPreview"]');
    await panel.waitFor();
    assert.ok((await panel.innerText()).includes(preview.summary));
    assert.equal(await card.getByRole('button', { name: /^发布$/ }).isEnabled(), true);
    report.cases.push({ key, preview: 'passed', value: request.params.proposed_value });
  }
  for (const row of catalog.filter(row => !row.available)) {
    assert.equal(await page.locator(`[data-parameter-key="${row.key}"]`).getByRole('button', { name: /^发布$/ }).count(), 0);
  }
  assert.deepEqual(report.errors, []);
  assert.deepEqual(report.mutationAttempts, []);
  await page.screenshot({ path: path.join(output, 'catalog-preview.png'), fullPage: true });
  report.status = 'passed';
} catch (error) {
  report.failure = error.message;
  await page.screenshot({ path: path.join(output, 'failure.png'), fullPage: true }).catch(() => {});
  process.exitCode = 1;
} finally {
  fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify(report, null, 2));
  await browser.close();
  console.log(`[system-parameter.browser] ${report.status} cases=${report.cases.length}${report.failure ? ` reason=${report.failure}` : ''}`);
}
