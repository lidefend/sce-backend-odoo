import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { launchChromium } from './playwright_runtime.mjs';

const target = JSON.parse(process.env.FRONTEND_BASE_CONFIGURATION_DOMAIN_TARGET || '{}');
const base = process.env.FRONTEND_URL;
assert.equal(target.database, 'sc_dev_demo');
assert.equal(new URL(base).origin, 'http://127.0.0.1:18081');
assert.equal(target.security_user.parameter_admin, false, 'denial principal must lack parameter-admin groups');
const output = path.resolve('.runtime/agent-runs/PRODUCT-ITERATION-V2-20261020/parameter-denial');
fs.mkdirSync(output, { recursive: true });
const report = { status: 'failed', head: process.env.CANDIDATE_HEAD, database: target.database,
  principal: target.security_user.xmlid, cases: [], errors: [] };
const browser = await launchChromium();
const context = await browser.newContext();
const page = await context.newPage();
function params(request) { try { return request.postDataJSON() || {}; } catch { return {}; } }
function find(value, key) {
  if (!value || typeof value !== 'object') return undefined;
  if (Object.hasOwn(value, key)) return value[key];
  for (const child of Object.values(value)) { const hit = find(child, key); if (hit !== undefined) return hit; }
}
function assertDenied(body) {
  assert.equal(find(body, 'parameters'), undefined, 'denied response must not disclose catalog');
  assert.ok(JSON.stringify(body).includes('PERMISSION_DENIED'), 'explicit permission denial required');
}
page.on('pageerror', error => report.errors.push(error.message));
try {
  await page.goto(`${base}/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.locator('#login-username').fill(target.security_user.login);
  await page.locator('#login-password').fill(process.env.E2E_PASSWORD);
  const db = page.getByLabel(/数据库/);
  if (await db.count() === 1 && await db.isVisible() && await db.isEnabled()) await db.fill(target.database);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 45000 });
  const response = page.waitForResponse(res => params(res.request()).intent === 'sc.product.system_parameter.catalog', { timeout: 30000 });
  await page.goto(`${base}/admin/system-parameters`, { waitUntil: 'domcontentloaded' });
  const received = await response;
  assertDenied(await received.json());
  await page.getByText('系统参数目录暂时无法加载，请稍后重试。', { exact: true }).waitFor();
  assert.equal(await page.locator('[data-parameter-key]').count(), 0);
  assert.equal(await page.getByRole('button', { name: /^(发布|预览影响|回滚)$/ }).count(), 0);
  report.cases.push({ case: 'catalog_and_page_denied', status: 'passed' });
  const request = received.request();
  const headers = await request.allHeaders();
  delete headers['content-length'];
  for (const intent of ['preview', 'publish', 'rollback']) {
    // Invalid values and absent change ID keep the probe non-mutating even if authorization regresses.
    const denied = await context.request.post(request.url(), {
      headers,
      data: { ...params(request), intent: `sc.product.system_parameter.${intent}`,
        params: intent === 'rollback' ? { change_id: 0 } : { parameter_key: 'default_payment_terms', proposed_value: '__invalid_denial_probe__' } },
    });
    assertDenied(await denied.json());
    report.cases.push({ case: `${intent}_denied`, status: 'passed' });
  }
  assert.deepEqual(report.errors, []);
  await page.screenshot({ path: path.join(output, 'denied-page.png'), fullPage: true });
  report.status = 'passed';
} catch (error) {
  report.failure = error.message;
  process.exitCode = 1;
  await page.screenshot({ path: path.join(output, 'failure.png'), fullPage: true }).catch(() => {});
} finally {
  fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify(report, null, 2));
  await browser.close();
  console.log(`[system-parameter.denial] ${report.status} cases=${report.cases.length}${report.failure ? ` reason=${report.failure}` : ''}`);
}
