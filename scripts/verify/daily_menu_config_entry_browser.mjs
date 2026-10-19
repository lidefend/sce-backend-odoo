import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';
import { resolveAcceptanceEnvironment, verifyServedIdentity, redactedEnvironmentEvidence } from './lib/frontend_acceptance_environment.mjs';
import { permitsInventoryRequest } from '../../frontend/apps/web/scripts/bootstrap_inventory_policy.mjs';

const env = resolveAcceptanceEnvironment({ tool: 'menu-config-entry-audit' });
const identity = await verifyServedIdentity(env);
const output = env.runArtifactRoot;
await fs.mkdir(output, { recursive: true });
const report = { status: 'running', environment: redactedEnvironmentEvidence(env), identity, checks: [], errors: [], blocked: [], calls: [] };
const browser = await launchChromium({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 950 } });
page.setDefaultTimeout(30000);
const prefix = new URL(env.baseUrl).pathname.replace(/\/$/, '');
const relative = pathname => prefix && pathname.startsWith(`${prefix}/`) ? pathname.slice(prefix.length) : pathname;
page.on('pageerror', error => report.errors.push(error.message));
page.on('response', response => { if (response.status() >= 500) report.errors.push(`HTTP ${response.status()} ${new URL(response.url()).pathname}`); });
await page.route('**/api/**', async route => {
  const req = route.request();
  let body;
  try { body = req.postDataJSON(); } catch { body = null; }
  const pathname = relative(new URL(req.url()).pathname);
  const intent = (body?.params?.intent ? body.params : body)?.intent;
  if (!permitsInventoryRequest(req.method(), pathname, body, true)) {
    report.blocked.push(intent || pathname);
    await route.abort();
    return;
  }
  report.calls.push(intent || pathname);
  await route.continue();
});
try {
  await page.goto(`${env.baseUrl}/login`);
  await page.locator('input').nth(0).fill(env.login);
  await page.locator('input').nth(1).fill(env.password);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL(url => !url.pathname.endsWith('/login'));
  const nav = page.getByRole('complementary', { name: '主导航' });
  await nav.waitFor();
  await nav.getByText('产品配置', { exact: true }).click();
  const entry = nav.getByText('菜单配置', { exact: true });
  await entry.waitFor();
  report.checks.push('published_sidebar_entry_visible');
  const panelResponse = () => page.waitForResponse(response => {
    try {
      const raw = response.request().postDataJSON();
      return (raw?.params?.intent ? raw.params : raw)?.intent === 'ui.menu_config.panel.get';
    } catch { return false; }
  });
  const assertPanel = async response => {
    assert.equal(response.status(), 200, 'menu panel HTTP status');
    const payload = await response.json();
    assert.equal(payload.ok, true, 'menu panel business result');
    assert.ok(Array.isArray(payload.data?.menus) && payload.data.menus.length > 0, 'menu panel contains readable menus');
    report.checks.push('panel_response_success_with_nonempty_menus');
  };
  const opened = panelResponse();
  await entry.click();
  await assertPanel(await opened);
  await page.waitForURL(url => relative(url.pathname) === '/admin/menu-config');
  await page.getByRole('heading', { name: '菜单配置', exact: true, level: 1 }).waitFor();
  await page.getByRole('region', { name: '当前菜单配置' }).waitFor();
  assert.ok(report.calls.includes('ui.menu_config.panel.get'));
  report.checks.push('sidebar_click_opens_menu_configuration');
  const refreshed = panelResponse();
  await page.reload();
  await assertPanel(await refreshed);
  await page.getByRole('region', { name: '当前菜单配置' }).waitFor();
  report.checks.push('refresh_retains_configuration_panel');
  assert.equal(await page.getByText(/CONTRACT_GAP/).count(), 0);
  assert.deepEqual(report.blocked, []);
  assert.deepEqual(report.errors, []);
  await page.screenshot({ path: path.join(output, 'menu-configuration.png') });
  report.status = 'passed';
} catch (error) {
  report.status = 'failed';
  report.error = String(error.message);
  await page.screenshot({ path: path.join(output, 'failure.png') }).catch(() => {});
  process.exitCode = 1;
} finally {
  await browser.close();
  await fs.writeFile(path.join(output, 'report.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ status: report.status, checks: report.checks, report: path.join(output, 'report.json'), error: report.error }));
}
