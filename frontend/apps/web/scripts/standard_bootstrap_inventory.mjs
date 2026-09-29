/** Registered build inventory and scoped current-candidate bootstrap acceptance. */
import { permitsInventoryRequest } from './bootstrap_inventory_policy.mjs';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { launchChromium } from '../../../../scripts/verify/playwright_runtime.mjs';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../..');
const base = 'http://127.0.0.1:5180';
const candidateStartup = process.env.BOOTSTRAP_SCOPE === 'candidate-startup';
const out = path.join(root, 'artifacts/frontend-web-fix-20260928', `bootstrap-inventory-${Date.now()}`);
const build = JSON.parse(await fs.readFile(path.resolve(root, '../sce-offrepo/artifacts/boot01-20260929-r3/build-identity.json')));
const bytes = Buffer.from(await fetch(`${base}${build.entry}`).then(r => r.arrayBuffer()));
assert.equal(createHash('sha256').update(bytes).digest('hex'), build.entry_sha256);
assert.equal(process.env.DB_NAME, 'sc_frontend_acceptance');
const report = { kind: candidateStartup ? 'candidate-startup-acceptance' : 'observed-build-inventory-not-candidate-acceptance', build, status: 'running', roles: [] };
await fs.mkdir(out, { recursive: true });
const browser = await launchChromium({ headless: true });
const redact = (value) => {
  if (Array.isArray(value)) return value.map(redact);
  if (!value || typeof value !== 'object') return value;
  return Object.fromEntries(Object.entries(value).filter(([key]) => !/password|secret|token|session_id|cookie/i.test(key)).map(([key, item]) => [key, redact(item)]));
};
const registeredRoles = ['fixture_role_finance', 'fixture_role_contract_operator', 'fixture_role_config_admin'];
const roles = process.env.BOOTSTRAP_ROLES?.split(',') || registeredRoles;
assert.ok(roles.length && roles.every(role => registeredRoles.includes(role)), 'registered fixture role scope only');
report.roleScope = roles;
try {
  for (const role of roles) {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 950 }, locale: 'zh-CN' });
    const page = await ctx.newPage();
    page.setDefaultTimeout(15000);
    page.setDefaultNavigationTimeout(30000);
    const observed = { role, calls: [], contracts: [], errors: [], blockedWrites: [] };
    report.roles.push(observed);
    page.on('pageerror', error => observed.errors.push(error.message));
    await page.route('**/api/**', async route => {
      try {
      const rawBody = route.request().postDataJSON();
      const body = rawBody?.params?.intent ? rawBody.params : rawBody;
      observed.requests ??= [];
      observed.requests.push({ path: new URL(route.request().url()).pathname, keys: Object.keys(rawBody || {}) });
      if (!permitsInventoryRequest(route.request().method(), new URL(route.request().url()).pathname, rawBody, candidateStartup)) {
        observed.blockedWrites.push(body?.intent || new URL(route.request().url()).pathname);
        return route.abort();
      }
      const response = await route.fetch({ timeout: 15000 });
      const intent = body?.intent;
      if (intent) {
        observed.calls.push({ intent, httpStatus: response.status() });
        if (intent === 'system.init' || intent.startsWith('ui.contract')) {
          const result = await response.json();
          observed.contracts.push({ intent, params: redact(body.params || {}), payload: redact(result) });
        }
      }
      await route.fulfill({ response });
      } catch (error) {
        // Request errors can contain credential-bearing headers; retain only the reason.
        if (!page.isClosed()) observed.errors.push(String(error.message).split('\n')[0]);
        await route.abort().catch(() => {});
      }
    });
    await page.goto(`${base}/login`);
    observed.login = await page.locator('main').evaluate(node => ({ forms: node.querySelectorAll('form').length, officialForms: node.querySelectorAll('[data-semantic-component="ScForm"]').length }));
    if (candidateStartup) {
      assert.equal(observed.login.officialForms, 1, 'one official login form');
      const requiredMessage = await page.locator('input').nth(0).getAttribute('placeholder');
      await page.getByRole('button', { name: /^登录$/ }).click();
      try { await page.getByText(requiredMessage, { exact: true }).waitFor({ timeout: 5000 }); }
      catch (error) {
        observed.loginFailure = await page.locator('form').evaluate(form => ({ noValidate: form.noValidate, attributes: [...form.attributes].map(a => [a.name,a.value]), text: form.innerText, controls: [...form.querySelectorAll('input,button')].map(n => ({ tag:n.tagName,type:n.type,required:n.required,disabled:n.disabled,valid:n.validity?.valid })) }));
        throw error;
      }
      assert.equal(await page.locator('input').nth(0).getAttribute('required'), '', 'native required semantics preserved');
      assert.equal(observed.calls.filter(call => call.intent === 'login').length, 0, 'empty credentials stopped by official engine');
      assert.equal(await page.getByRole('textbox', { name: '账号', exact: true }).count(), 1);
    }
    await page.locator('input').nth(0).fill(role);
    await page.locator('input').nth(1).fill(process.env.SC_ACCEPTANCE_FIXTURE_PASSWORD);
    const db = page.getByPlaceholder(/请输入数据库名/);
    if (await db.count() && await db.isEnabled()) await db.fill('sc_frontend_acceptance');
    await page.getByRole('button', { name: /^登录$/ }).click();
    await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 60000 });
    await page.locator('.layout-shell').waitFor();
    await page.waitForLoadState('networkidle');
    observed.landing = page.url().replace(base, '');
    observed.surfaces = await page.locator('[data-shell-composition], [data-product-page-pattern], [data-semantic-component]').evaluateAll(nodes => [...new Set(nodes.map(node => [node.getAttribute('data-shell-composition'), node.getAttribute('data-product-page-pattern'), node.getAttribute('data-semantic-component')].filter(Boolean).join(':')))]);
    assert.ok(observed.contracts.some(row => row.intent === 'system.init'), 'real initialization response required');
    await page.screenshot({ path: path.join(out, `${role}-landing.png`) });
    const init = observed.contracts.find(row => row.intent === 'system.init')?.payload?.data;
    const leaves = [];
    const walk = (nodes) => { for (const node of nodes || []) {
      if (node.children?.length) walk(node.children);
      else leaves.push(node);
    } };
    walk(init?.navigation?.nav);
    observed.navigation = leaves.map(node => ({ menuId: node.menu_id, label: node.label, route: node.meta?.route, model: node.meta?.model, viewModes: node.meta?.view_modes }));
    observed.pages = [];
    for (const entry of candidateStartup ? observed.navigation.filter(entry => [335,698,699,374,696,454,663,702,703,417].includes(entry.menuId)) : observed.navigation) {
      if (typeof entry.route !== 'string' || !entry.route.startsWith('/') || entry.route.startsWith('//')) continue;
      const item = { ...entry };
      observed.pages.push(item);
      try {
        await page.goto(`${base}${entry.route}`);
        await page.waitForLoadState('networkidle', { timeout: 4000 }).catch(() => { item.networkSettled = false; });
        item.actualRoute = page.url().replace(base, '');
        item.markers = await page.locator('[data-list-composition], [data-form-composition], [data-detail-composition], [data-product-page-pattern], [data-active-renderer], [data-requested-renderer], [data-surface-semantic], [data-renderer-status], [data-my-work-renderer], [data-semantic-component="BusinessConfigSurfaceView"]').evaluateAll(nodes => nodes.map(node => Object.fromEntries([...node.attributes].filter(attr => attr.name.startsWith('data-')).map(attr => [attr.name, attr.value]))));
        item.alerts = await page.locator('[role="alert"]').allTextContents();
      } catch (error) { item.error = error.message; }
      await fs.writeFile(path.join(out, 'report.json'), JSON.stringify(report, null, 2));
      console.log(`[bootstrap-inventory] ${role} menu=${entry.menuId} observed=${observed.pages.length}/${observed.navigation.length}`);
    }
    if (candidateStartup) {
      const expectedLanding = init?.role_surface?.landing_path || init?.default_route?.route;
      assert.equal(new URL(observed.landing, base).pathname, new URL(expectedLanding, base).pathname, 'landing follows authoritative role/default route');
      assert.equal(init.role_surface.role_code.length > 0, true, 'effective role is supplied');
      const entry = observed.navigation.find(node => node.route?.startsWith('/') && node.viewModes?.includes('tree'));
      assert.ok(entry, 'authorized collection entry from initialization');
      const contractOffset = observed.contracts.length;
      console.log(`[bootstrap-inventory] ${role} standard-list menu=${entry.menuId}`);
      await page.goto(`${base}${entry.route}`);
      await page.locator('[data-list-composition="official-standard-list"]').waitFor();
      await page.waitForLoadState('networkidle');
      assert.ok(observed.contracts.slice(contractOffset).some(row => row.intent === 'ui.contract.v2' && row.payload.ok && Number(row.params.menu_id) === entry.menuId), 'current navigation page contract consumed');
      for (const target of ['/s/workspace.home', '/my-work']) {
        console.log(`[bootstrap-inventory] ${role} workspace=${target}`);
        await page.goto(`${base}${target}`);
        await page.locator('[data-workspace-composition="official-dashboard-workspace"]').waitFor();
        for (const width of [1440, 390]) {
          await page.setViewportSize({ width, height: 950 });
          assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), `workspace overflow at ${width}`);
          await page.screenshot({ path: path.join(out, `${role}-${target.includes('my-work') ? 'work' : 'home'}-${width}.png`) });
        }
      }

    }
    await page.unrouteAll({ behavior: 'wait' });
    if (candidateStartup) {
      assert.deepEqual(observed.blockedWrites, [], 'no unregistered request in candidate startup');
      assert.deepEqual(observed.errors, [], 'no uncaught page or request error');
    }
    await ctx.close();
  }
  report.status = candidateStartup ? 'passed' : 'observed';
} catch (error) { report.status = 'failed'; report.error = error.message; process.exitCode = 1; }
finally {
  await fs.writeFile(path.join(out, 'report.json'), JSON.stringify(report, null, 2));
  // Settle interception callbacks before disposing their API request contexts.
  for (const context of browser.contexts()) {
    for (const page of context.pages()) await page.unrouteAll({ behavior: 'wait' });
  }
  await browser.close();
  await fs.writeFile(path.join(out, 'report.json'), JSON.stringify(report, null, 2));
  console.log(`[bootstrap-inventory] ${report.status} roles=${report.roles.length} report=${out}/report.json`);
}
