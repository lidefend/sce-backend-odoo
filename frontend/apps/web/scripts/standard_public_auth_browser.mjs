/** Real anonymous page contracts; activation writes remain intercepted UI simulation. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { launchChromium } from '../../../../scripts/verify/playwright_runtime.mjs';
const root = process.cwd();
const build = JSON.parse(await fs.readFile(path.resolve(root, '../sce-offrepo/artifacts/auth03-20260929/build-identity.json')));
const base = 'http://127.0.0.1:5180';
assert.equal(createHash('sha256').update(Buffer.from(await fetch(`${base}${build.entry}`).then(r => r.arrayBuffer()))).digest('hex'), build.entry_sha256);
assert.equal(process.env.DB_NAME, 'sc_frontend_acceptance');
const out = path.join(root, 'artifacts/frontend-web-fix-20260928', `public-auth-${Date.now()}`);
await fs.mkdir(out, { recursive: true });
const report = { kind: 'real-public-contract-and-simulated-activation-no-account-write', build, status: 'running', checks: 0, errors: [], unexpected: [] };
const browser = await launchChromium({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 950 } });
  page.setDefaultTimeout(10000);
  page.on('pageerror', error => report.errors.push(error.message));
  let starts = 0, finishes = 0, publicReads = 0;
  await page.route('**/api/**', async route => {
    try {
    const request = route.request();
    const url = new URL(request.url());
    let body;
    if (url.pathname === '/api/v1/auth/page-contracts' && request.method() === 'GET') {
      publicReads++;
      if (publicReads === 1) return route.fulfill({ status: 503, contentType: 'application/json', body: '{"ok":false}' });
      const response = await route.fetch({ timeout: 15000 });
      const payload = await response.json();
      assert.equal(response.status(), 200);
      assert.deepEqual(Object.keys(payload.data.pages).sort(), ['account_activation','login','password_recovery']);
      assert.equal(payload.data.pages.password_recovery.page_orchestration.action_schema.actions.open_login.target.path, '/login');
      report.publicContract = payload;
      return route.fulfill({ response });
    }
    if (url.pathname === '/api/v1/auth/activation/start' && request.method() === 'POST') {
      starts++;
      body = { ok: true, activation_context: 'ui-simulation-context' };
    } else if (url.pathname === '/api/v1/auth/activation/complete' && request.method() === 'POST') {
      finishes++;
      body = finishes === 1 ? { ok: false, message: '模拟服务拒绝，请重新输入' } : { ok: true };
    } else if (url.pathname === '/api/v1/auth/password-recovery/status' && request.method() === 'GET') {
      const response = await route.fetch({ timeout: 15000 });
      assert.equal(response.status(), 200);
      return route.fulfill({ response });
    } else {
      report.unexpected.push(url.pathname);
      return route.abort();
    }
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify(body) });
    } catch (error) {
      report.errors.push(String(error.message).split('\n')[0]);
      await route.abort().catch(() => {});
    }
  });
  const check = (actual, expected) => { assert.equal(actual, expected); report.checks++; };
  await page.goto(`${base}/activate-account`);
  await page.getByRole('alert').filter({ hasText: '账号入口配置加载失败' }).waitFor();
  await page.getByRole('button', { name: '重试加载' }).click();
  await page.getByRole('alert').filter({ hasText: '账号入口配置加载失败' }).waitFor({ state: 'hidden' });
  check(publicReads, 2);
  check(await page.locator('[data-auth-composition="official-credential-form"]').count(), 1);
  await page.getByRole('textbox', { name: '激活码', exact: true }).fill('synthetic-ui-code');
  await page.getByRole('button', { name: '继续', exact: true }).click();
  await page.locator('#activation-password').waitFor();
  check(starts, 1);
  check(await page.locator('#activation-code').count(), 0);
  check(await page.locator('[data-auth-composition="official-credential-form"]').count(), 1);
  for (const id of ['#activation-password', '#activation-password-confirm']) await page.locator(id).fill('short');
  await page.getByRole('button', { name: '设置正式密码', exact: true }).click();
  await page.locator('[data-semantic-component="ScFormItem"]').filter({ has: page.locator('#activation-password') }).getByText('密码至少12位，并同时包含字母和数字。', { exact: true }).waitFor();
  check(finishes, 0);
  for (const id of ['#activation-password', '#activation-password-confirm']) await page.locator(id).fill('synthetic-only-1234');
  await page.getByRole('button', { name: '设置正式密码', exact: true }).click();
  await page.getByRole('alert').filter({ hasText: '模拟服务拒绝' }).waitFor();
  check(finishes, 1);
  for (const id of ['#activation-password', '#activation-password-confirm']) check(await page.locator(id).inputValue(), '');
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 950 });
    check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), true);
    // Only empty secret inputs are captured.
    await page.screenshot({ path: path.join(out, `activation-empty-after-failure-${width}.png`) });
  }
  for (const id of ['#activation-password', '#activation-password-confirm']) await page.locator(id).fill('synthetic-only-1234');
  await page.getByRole('button', { name: '设置正式密码', exact: true }).click();
  await page.getByRole('status').waitFor();
  check(finishes, 2);
  check(await page.locator('input[type="password"]').count(), 0);
  await page.getByRole('button', { name: '返回登录', exact: true }).click();
  await page.waitForURL('**/login');
  check(await page.locator('[data-auth-composition="official-credential-form"]').count(), 1);
  await page.goto(`${base}/password-recovery`);
  await page.getByText('当前请通过已批准的组织身份核验流程申请密码恢复', { exact: true }).waitFor();
  check(await page.locator('form').count(), 0);
  await page.waitForLoadState('networkidle');
  await page.getByRole('button', { name: '返回登录', exact: true }).click();
  await page.waitForURL('**/login');
  check(await page.locator('[data-auth-composition="official-credential-form"]').count(), 1);
  await page.unrouteAll({ behavior: 'wait' });
  assert.deepEqual(report.errors, []);
  assert.deepEqual(report.unexpected, []);
  report.status = 'passed';
} catch (error) { report.status = 'failed'; report.error = String(error.message).split('\n')[0]; process.exitCode = 1; }
finally {
  await browser.close();
  await fs.writeFile(path.join(out, 'report.json'), JSON.stringify(report, null, 2));
  console.log(`[public-auth] ${report.status} checks=${report.checks} report=${out}/report.json`);
}
