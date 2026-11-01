// BNVA-04-06D-02 focused positive-path probe: login fixture_role_finance on the
// local.clean entry, navigate to the two productized professional pages
// (sc.quality.issue, sc.tax.certificate.registration), and bind the served
// ui.contract.v2 envelope plus the rendered Vue surface in one browser session.
// Read-only: no business write, no save, no create.
import fs from 'node:fs';
import { launchChromium } from '../verify/playwright_runtime.mjs';
import { matrixLoginUrl } from '../verify/business_entry_matrix_model.mjs';
import { captureReleasedNavigation } from '../verify/released_navigation_target.mjs';

const BASE = (process.env.SC_ACCEPTANCE_FRONTEND_URL || 'http://127.0.0.1:18083').replace(/\/$/, '');
const LOGIN = process.env.ACCEPTANCE_LOGIN || 'fixture_role_finance';
const PASSWORD = process.env.ACCEPTANCE_PASSWORD;
if (!PASSWORD) throw new Error('ACCEPTANCE_PASSWORD is required');

// Action + menu database IDs resolved in sc_clean for the two formal entries:
//   action_sc_quality_issue -> action 744 / menu 523 (sc.quality.issue)
//   action_sc_tax_certificate_registration_user -> action 711 / menu 539 (sc.tax.certificate.registration)
const ENTRIES = [
  [744, 523, 'sc.quality.issue'],
  [711, 539, 'sc.tax.certificate.registration'],
];

const LIST_SURFACE = '[data-semantic-component="ActionView"][data-product-page-mode="list"]';
const FORM_SURFACE = '[data-semantic-component="ContractFormPage"][data-product-page-mode="form"]';
const consoleErrors = [];
const contracts = [];

const browser = await launchChromium({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, locale: 'zh-CN' });
page.setDefaultTimeout(30000);
page.on('pageerror', (error) => consoleErrors.push(`pageerror: ${error.message}`));
page.on('console', (message) => {
  if (message.type() === 'error') consoleErrors.push(`console.error: ${message.text()}`.slice(0, 300));
});
page.on('response', async (response) => {
  let payload = {};
  try { payload = JSON.parse(response.request().postData() || '{}'); } catch { return; }
  if (String(payload.intent || '') !== 'ui.contract.v2' || response.status() >= 400) return;
  try {
    const body = await response.json();
    const data = (body && (body.data || (body.result && (body.result.data || body.result)))) || {};
    const params = payload.params || {};
    contracts.push({
      action_id: Number(params.action_id || 0),
      menu_id: Number(params.menu_id || 0),
      model: String(params.model || ''),
      view_type: String(params.view_type || ''),
      data: data,
    });
  } catch {}
});

const navigation = captureReleasedNavigation(page);

await page.goto(matrixLoginUrl(BASE), { waitUntil: 'networkidle' });
const inputs = page.locator('input');
await inputs.nth(0).fill(LOGIN);
await inputs.nth(1).fill(PASSWORD);
await page.getByRole('button', { name: /^登录$/ }).click();
await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45000 });
await page.waitForTimeout(2500);

const pages = [];
for (const [actionId, menuId, model] of ENTRIES) {
  await page.goto(`${BASE}/a/${actionId}?menu_id=${menuId}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1600);

  const listSurface = page.locator(LIST_SURFACE).last();
  const formSurface = page.locator(FORM_SURFACE).last();
  const listCount = await listSurface.count();
  const formCount = await formSurface.count();
  const rendered_surface = formCount ? 'form' : (listCount ? 'list' : 'none');

  const relevant = contracts
    .filter((c) => c.action_id === actionId)
    .slice(-1)[0] || null;
  const contract = relevant && relevant.data ? relevant.data : null;
  const formStructure = contract && contract.formStructureContract ? contract.formStructureContract : null;
  const compositionMode = formStructure && formStructure.composition_mode ? formStructure.composition_mode
    : (contract && contract.view_orchestration ? ((contract.view_orchestration.views || {}).form || {}).composition_mode : null);
  const treeFields = (contract && contract.tree && Array.isArray(contract.tree.fields)) ? contract.tree.fields.map((f) => f.name || f.field) : null;
  const formFieldNames = formStructure && Array.isArray(formStructure.fields) ? formStructure.fields.map((f) => f.name || f.field) : null;

  pages.push({
    action_id: actionId,
    expected_model: model,
    rendered_surface,
    list_rendered: listCount > 0,
    form_rendered: formCount > 0,
    contract_model: relevant ? relevant.model : null,
    contract_view_type: relevant ? relevant.view_type : null,
    composition_mode: compositionMode || null,
    tree_field_names: treeFields,
    form_field_names: formFieldNames,
    has_source_created_by: (treeFields || []).includes('source_created_by') || (formFieldNames || []).includes('source_created_by'),
    has_source_created_at: (treeFields || []).includes('source_created_at') || (formFieldNames || []).includes('source_created_at'),
  });
  await page.screenshot({ path: `/tmp/bnva-${model.replace(/\./g, '-')}.png`, fullPage: false });
}

const report = {
  base: BASE,
  login: LOGIN,
  url_after_login: page.url(),
  pages,
  console_errors: consoleErrors.slice(0, 10),
  contract_count: contracts.length,
};
fs.mkdirSync(process.env.SC_ACCEPTANCE_OUTPUT_DIR || '/tmp', { recursive: true });
const out = process.env.SC_ACCEPTANCE_OUTPUT_DIR || '/tmp';
fs.writeFileSync(`${out}/quality-tax-pages-probe.json`, JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
await browser.close();
