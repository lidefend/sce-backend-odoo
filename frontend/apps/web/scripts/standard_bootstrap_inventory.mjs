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
const managementOnly = process.env.BOOTSTRAP_MANAGEMENT_ONLY === '1';
const out = path.join(root, 'artifacts/frontend-web-fix-20260928', `bootstrap-inventory-${Date.now()}`);
const build = JSON.parse(await fs.readFile(path.resolve(root, '../sce-offrepo/artifacts/config05-20260929/build-identity.json')));
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
report.managementOnly = managementOnly;
if (managementOnly) assert.ok(candidateStartup && roles.length === 1 && roles[0] === 'fixture_role_config_admin', 'management-only audit requires the registered config-admin candidate journey');
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
        if (intent === 'enterprise.readiness.diagnosis.get' || intent === 'system.init' || intent === 'scenario.activation.catalog.get' || intent.startsWith('ui.contract')) {
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
    if (candidateStartup && role === 'fixture_role_config_admin') {
      const surface = init?.navigation?.scenario_surface?.tree;
      assert.ok(surface?.platform?.length, 'authorized configuration entries survive scenario projection');
      const management = page.locator('[data-management-navigation="true"]');
      await management.waitFor();
      for (const entry of surface.platform) await management.getByRole('button', { name: entry.label, exact: true }).waitFor();
      assert.equal(new URL(observed.landing, base).pathname, '/s/enterprise.setup', 'administrator first hop reaches existing initialization scene');
      const catalogPanel = page.locator('[data-semantic-component="ScenarioActivationPanel"][data-state="ready"]');
      await catalogPanel.waitFor();
      const catalog = observed.contracts.find(row => row.intent === 'scenario.activation.catalog.get')?.payload?.data;
      assert.equal(catalog?.business_scenarios?.length, 17, 'real business catalog delivered');
      assert.equal(await catalogPanel.locator('li').count(), catalog.business_scenarios.length);
      for (const row of catalog.business_scenarios) {
        assert.ok(row.actions.length, 'native-authorized administrator can manage each released scene');
        await catalogPanel.getByText(row.name, { exact: true }).waitFor();
      }
      observed.managementRecovery = { visibleEntries: surface.platform.length,
        scope: 'native_configuration_and_existing_setup_first_hop', initializationEntry: 'enterprise.setup',
        catalogCount: catalog.business_scenarios.length, mutationPerformed: false };
      await page.screenshot({ path: path.join(out, `${role}-configuration-entries.png`) });
      if (process.env.BOOTSTRAP_ENTERPRISE_INITIALIZATION === '1') {
        assert.ok(managementOnly, 'initialization traversal is scoped to the config-admin journey');
        const entries = ['企业信息', '组织架构', '岗位管理', '人员与账号', '业务权限分配'];
        observed.initializationEntries = [];
        for (const label of entries) {
          await page.goto(`${base}/s/enterprise.setup`);
          const button = page.locator('.handling-surface').getByRole('button', { name: label, exact: true });
          await button.waitFor();
          assert.equal(await button.isEnabled(), true, `${label} has native action authority`);
          const offset = observed.contracts.length;
          const diagnosis = page.locator('.enterprise-readiness-panel[data-state="ready"]');
          await diagnosis.waitFor();
          assert.equal(await diagnosis.locator('li').count(), 12, 'twelve actual readiness results');
          const readiness = observed.contracts.filter(row => row.intent === 'enterprise.readiness.diagnosis.get').at(-1)?.payload?.data;
          assert.equal(readiness?.contract_version, 'enterprise_readiness.v2');
          assert.ok(readiness.rules.some(row => row.remediation?.label === label), `${label} has native remediation`);
          if (label === '企业信息') {
            await diagnosis.getByRole('button', { name: '前往场景管理', exact: true }).click();
            await page.locator('#enterprise-scenario-activation[data-state="ready"]').waitFor();
            assert.equal(await page.locator('#enterprise-scenario-activation li').count(), 17);
          }
          await diagnosis.getByRole('button', { name: label, exact: true }).first().click();
          await page.waitForURL(url => /^\/a\/\d+/.test(url.pathname));
          await page.locator('[data-list-composition="official-standard-list"]').waitFor();
          await page.waitForLoadState('networkidle');
          const contracts = observed.contracts.slice(offset).filter(row => row.intent.startsWith('ui.contract'));
          assert.ok(contracts.some(row => row.payload.ok), `${label} consumes an actual successful contract`);
          assert.deepEqual(await page.locator('[role="alert"]').allTextContents(), [], `${label} has no blocking alert`);
          const entryResult = { label, route: page.url().replace(base, ''), contractCount: contracts.length };
          observed.initializationEntries.push(entryResult);
          if (label === '企业信息') {
            const companyRows = page.locator('.desktop-record-table tbody tr .cell-primary-link');
            assert.equal(await companyRows.count(), 1, 'company action returns only the current company');
            const formOffset = observed.contracts.length;
            await companyRows.first().click();
            await page.locator('[data-form-composition]').waitFor();
            await page.waitForLoadState('networkidle');
            const save = page.getByRole('button', { name: '保存草稿', exact: true });
            await save.waitFor();
            assert.equal(await save.isEnabled(), true, 'configuration administrator can edit the company profile');
            assert.ok(observed.contracts.slice(formOffset).some(row => row.intent === 'ui.contract.v2' && row.params.view_type === 'form' && row.payload.ok), 'native company form contract consumed');
            const formContract = observed.contracts.slice(formOffset).find(row => row.intent === 'ui.contract.v2' && row.params.view_type === 'form' && row.payload.ok)?.payload.data;
            const currencyFields = [];
            const collectCurrency = value => {
              if (!value || typeof value !== 'object') return;
              if (value.fieldInfo?.name === 'currency_id') currencyFields.push(value.fieldInfo);
              for (const child of Object.values(value)) collectCurrency(child);
            };
            collectCurrency(formContract.layoutContract.containerTree);
            assert.ok(currencyFields.length && currencyFields.every(field => field.modifiers?.readonly === true), 'native currency readonly modifier survives company delegation');
            const currencyStatus = formContract.statusContract.widgetStatus.filter(row => row.widgetId.startsWith('field.currency_id.'));
            assert.ok(currencyStatus.length && currencyStatus.every(row => row.readonly === true && row.auth === 'read'), 'effective currency contract is readonly');
            const currencyControl = page.locator('[data-field-name="currency_id"]');
            await currencyControl.waitFor();
            assert.equal(await currencyControl.locator('input:not([readonly]):not([disabled]), select:not([disabled])').count(), 0, 'currency has no editable input');
            entryResult.formRoute = page.url().replace(base, '');
            await page.screenshot({ path: path.join(out, `${role}-enterprise-company-form.png`) });
          }
        }
      }
      if (managementOnly) {
        await page.unrouteAll({ behavior: 'wait' });
        assert.deepEqual(observed.blockedWrites, [], 'no unregistered request in management recovery');
        assert.deepEqual(observed.errors, [], 'no uncaught management recovery error');
        await ctx.close();
        continue;
      }
    }
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
