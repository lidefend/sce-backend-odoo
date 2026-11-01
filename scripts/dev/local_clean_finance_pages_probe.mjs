// P4-04B focused positive-path probe: login fixture_role_finance on the
// local.clean entry, navigate to the three productized finance pages, and bind
// the released navigation, the served ui.contract.v2 envelope and the rendered
// ContractFormPage surface in one browser session. Read-only; no business write.
import fs from 'node:fs';
import { launchChromium } from '../verify/playwright_runtime.mjs';
import { matrixLoginUrl } from '../verify/business_entry_matrix_model.mjs';
import { captureReleasedNavigation } from '../verify/released_navigation_target.mjs';

const BASE = (process.env.SC_ACCEPTANCE_FRONTEND_URL || 'http://127.0.0.1:18083').replace(/\/$/, '');
const LOGIN = process.env.ACCEPTANCE_LOGIN || 'fixture_role_finance';
const PASSWORD = process.env.ACCEPTANCE_PASSWORD;
if (!PASSWORD) throw new Error('ACCEPTANCE_PASSWORD is required');

const ENTRIES = [
  ['smart_construction_core.menu_sc_user_payment_apply', 'payment.request'],
  ['smart_construction_core.menu_sc_payment_execution', 'sc.payment.execution'],
  ['smart_construction_core.menu_sc_receipt_income', 'sc.receipt.income'],
];

const FORM_SURFACE = '[data-semantic-component="ContractFormPage"][data-product-page-mode="form"][data-state]';
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
for (const [menuXmlid, model] of ENTRIES) {
  const target = await navigation.targetByMenuXmlid(menuXmlid, 60000);
  await page.goto(`${BASE}/a/${target.action_id}?menu_id=${target.menu_id}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1200);
  const surface = page.locator(FORM_SURFACE).last();
  let rendered = false;
  let state = '';
  if (await surface.count()) {
    rendered = true;
    state = String((await surface.getAttribute('data-state')) || '');
  }
  const relevant = contracts
    .filter((c) => c.action_id === target.action_id || c.menu_id === target.menu_id)
    .slice(-1)[0] || null;
  const contract = relevant && relevant.data ? relevant.data : null;
  const pageComposition = contract && contract.pageComposition ? contract.pageComposition : null;
  const layout = contract && contract.layoutContract ? contract.layoutContract : null;
  const formStructure = contract && contract.formStructureContract ? contract.formStructureContract : null;
  const identity = formStructure && (formStructure.identity || formStructure.identity_fields) ? (formStructure.identity || formStructure.identity_fields) : null;
  const sections = formStructure && Array.isArray(formStructure.sections) ? formStructure.sections.map((s) => ({ key: s.key, title: s.title, field_count: Array.isArray(s.fields) ? s.fields.length : 0 })) : null;
  const containerTree = layout && Array.isArray(layout.containerTree) ? layout.containerTree : null;
  pages.push({
    menu_xmlid: menuXmlid,
    expected_model: model,
    action_id: target.action_id,
    menu_id: target.menu_id,
    rendered_form_surface: rendered,
    surface_state: state,
    contract_model: relevant ? relevant.model : null,
    contract_view_type: relevant ? relevant.view_type : null,
    page_composition: pageComposition && pageComposition.classification ? pageComposition.classification : (pageComposition || null),
    identity,
    sections,
    container_tree_top: containerTree ? containerTree.slice(0, 24) : null,
  });
  await page.screenshot({ path: `/tmp/p4-04b-${model.replace(/\./g, '-')}.png`, fullPage: false });
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
fs.writeFileSync(`${out}/finance-pages-probe.json`, JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
await browser.close();
