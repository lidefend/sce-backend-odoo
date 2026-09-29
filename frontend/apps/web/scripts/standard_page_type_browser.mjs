import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { launchChromium } from '../../../../scripts/verify/playwright_runtime.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../..');
const base = 'http://127.0.0.1:5180';
const out = path.join(root, 'artifacts/frontend-web-fix-20260928', `tpl07-${Date.now()}`);
const report = { status: 'not_run', assertions: [], calls: [], errors: [], forbiddenWrites: [] };
const check = (name, passed, detail = {}) => { report.assertions.push({ name, passed, ...detail }); assert.ok(passed, name); };
await fs.mkdir(out, { recursive: true });
const build = JSON.parse(await fs.readFile(path.resolve(root, '../sce-offrepo/artifacts/config05-20260929/build-identity.json')));
const entry = Buffer.from(await fetch(`${base}${build.entry}`).then((res) => res.arrayBuffer()));
assert.equal(createHash('sha256').update(entry).digest('hex'), build.entry_sha256);
report.build = build;
const browser = await launchChromium({ headless: true });

async function login(role) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 950 }, locale: 'zh-CN' });
  const page = await ctx.newPage();
  page.on('pageerror', (error) => report.errors.push(error.message));
  await page.route('**/api/v1/intent', async (route) => {
    const body = route.request().postDataJSON();
    if (body?.intent === 'api.data' && !['list', 'read'].includes(body.params?.op)) {
      report.forbiddenWrites.push(body.params?.op);
      return route.abort();
    }
    return route.continue();
  });
  page.on('response', async (response) => {
    try {
      const body = response.request().postDataJSON();
      if (body?.intent === 'api.data' && body.params?.op === 'list') {
        const result = await response.json();
        report.calls.push({ role, model: body.params.model, domain: body.params.domain, order: body.params.order, offset: body.params.offset || 0, limit: body.params.limit, ids: result.data?.records?.map((row) => row.id) || [] });
      }
    } catch { /* only JSON list responses are observations */ }
  });
  await page.goto(`${base}/login`);
  const inputs = page.locator('input');
  await inputs.nth(0).fill(role);
  await inputs.nth(1).fill(process.env.SC_ACCEPTANCE_FIXTURE_PASSWORD);
  if (await inputs.count() > 2 && await inputs.nth(2).isEnabled()) await inputs.nth(2).fill('sc_frontend_acceptance');
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 60000 });
  await page.locator('.layout-shell').waitFor();
  return { page, ctx };
}

async function list(page, menu, name) {
  await page.goto(`${base}/m/${menu}`);
  await page.locator('[data-list-card-container="official"]').waitFor();
  check(`${name}: standard type`, await page.locator('[data-list-composition-reason="contract-collection-view"]').count() === 1);
  check(`${name}: one container`, await page.locator('[data-list-card-container="official"]').count() === 1);
  await page.screenshot({ path: path.join(out, `${name}.png`) });
}

async function form(page, url, name, profile = 'form') {
  await page.goto(`${base}${url}`);
  // Readiness follows the mode the contract declared for this page, never one
  // assumed composition. An editable record waits for the adopted form engine;
  // a readonly record waits for the page to publish the readonly detail
  // composition the contract declared. Demanding the editable engine on a
  // readonly record would require a mode the same contract cannot declare at
  // the same time, so the probe would hang on a page that is behaving correctly.
  await page.locator(profile === 'readonly'
    ? '[data-product-page-mode="form"][data-state="ok"][data-detail-composition="official-standard-detail"][data-detail-composition-reason="contract-readonly-record-view"]'
    : '[data-form-composition="official-standard-form"][data-state="ok"]').waitFor();
  check(`${name}: no unknown renderer`, await page.locator('[data-field-fail-closed]').count() === 0);
  if (profile === 'readonly') {
    check(`${name}: readonly mode published`, await page.locator('[data-semantic-component="ContractFormProductHeader"][data-state="readonly"]').count() === 1);
    check(`${name}: no editable form composition`, await page.locator('[data-form-composition="official-standard-form"]').count() === 0);
    check(`${name}: nonzero official facts`, await page.locator('[data-detail-facts="official-standard-detail"]').count() > 0);
    check(`${name}: readonly detail adopted`, await page.locator('[data-detail-composition="official-standard-detail"]').count() === 1);
    const collections = page.locator('[data-field-type="one2many"], [data-field-type="many2many"], [data-field-type="binary"]');
    const count = await collections.count();
    if (name === 'payment-readonly') check('payment readonly: nonzero detail collection', await page.locator('[data-field-type="one2many"]').count() > 0);
    for (let index = 0; index < count; index += 1) {
      check(`${name}: collection remains outside descriptions`, await collections.nth(index).locator('xpath=ancestor::*[@data-detail-facts="official-standard-detail"]').count() === 0);
    }
    report.detailSections ??= {};
    report.detailSections[name] = await page.locator('[data-detail-section-reason]').evaluateAll((nodes) => nodes.map((node) => node.getAttribute('data-detail-section-reason')));
  } else {
    check(`${name}: official form engine mounted`, await page.locator('[data-semantic-component="ScForm"]').count() > 0);
  }
  await page.screenshot({ path: path.join(out, `${name}.png`) });
}

try {
  if (process.env.TPL07_SCOPE === 'detail') {
    const finance = await login('fixture_role_finance');
    await form(finance.page, '/r/payment.request/1813?menu_id=545&action_id=775', 'payment-readonly', 'readonly');
    check('payment: existing company fact preserved', await finance.page.getByText('FE Company A', { exact: true }).count() > 0);
    report.paymentFactText = await finance.page.locator('[data-detail-facts]').allTextContents();
    await finance.page.setViewportSize({ width: 390, height: 844 });
    check('payment detail: narrow page contained', await finance.page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1));
    await finance.page.screenshot({ path: path.join(out, 'payment-readonly-narrow.png') });
    await finance.ctx.close();
    const contract = await login('fixture_role_contract_operator');
    await form(contract.page, '/r/sc.general.contract/11?menu_id=662', 'contract-readonly', 'readonly');
    await contract.ctx.close();
  } else if (process.env.TPL07_SCOPE !== 'additional') {
  const finance = await login('fixture_role_finance');
  const p = finance.page;
  await list(p, 545, 'payment-list');
  const pager = p.locator('[data-semantic-component="ScPagination"]');
  await pager.locator('.t-pagination__select input').click();
  await p.locator('li.t-select-option:visible').filter({ hasText: /^10 条\/页$/ }).click();
  await p.waitForTimeout(1500);
  const before = report.calls.filter((call) => call.model === 'payment.request').at(-1);
  await pager.locator('.t-pagination__btn-next').click();
  await p.waitForTimeout(1800);
  const next = report.calls.filter((call) => call.model === 'payment.request').at(-1);
  check('payment: server next page', next.offset === 10 && next.ids.length > 0 && JSON.stringify(next.ids) !== JSON.stringify(before.ids), { ids: next.ids });
  // The record a list opens declares its own mode: a closed row is a readonly
  // detail, so the probe binds the opened page to the identity of the row it
  // clicked and to the composition the contract declared for it, instead of
  // assuming an editable draft sits first on the page. What must hold either
  // way is that the page is classified by the contract (never an unclassified
  // fallback) and keeps the list context it was opened from.
  const openedRow = p.locator('.flat-table tbody tr[data-record-key]').filter({ has: p.locator('td') }).first();
  const openedRecordKey = await openedRow.getAttribute('data-record-key');
  await openedRow.click();
  await p.locator(`[data-form-record="${openedRecordKey}"][data-state="ok"]`).waitFor();
  check('payment: opened record identity matches the clicked row', await p.locator(`[data-form-record="${openedRecordKey}"]`).count() === 1, { openedRecordKey });
  check(
    'payment: opened record composition follows the contract declaration',
    await p.locator('[data-form-composition-reason="contract-record-view"], [data-detail-composition-reason="contract-readonly-record-view"]').count() === 1,
  );
  check(
    'payment: opened record is not an unclassified fallback',
    await p.locator('[data-form-composition-reason="contract-view-not-classified"], [data-detail-composition-reason="contract-view-not-classified"]').count() === 0,
  );
  check('payment: return context carried', new URL(p.url()).searchParams.get('list_offset') === '10');
  await p.goBack();
  await p.locator('[data-list-card-container="official"]').waitFor();
  await p.waitForTimeout(1500);
  check('payment: return keeps page and set', JSON.stringify(report.calls.filter((call) => call.model === 'payment.request').at(-1).ids) === JSON.stringify(next.ids));
  await form(p, '/f/payment.request/1813?menu_id=545&action_id=775', 'payment-master-detail');
  check('payment: master detail extension preserved', await p.locator('[data-field-type="one2many"]').count() > 0);
  await form(p, '/r/payment.request/1813?menu_id=545&action_id=775', 'payment-readonly', 'readonly');
  await p.setViewportSize({ width: 390, height: 844 });
  check('payment detail: narrow page contained', await p.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1));
  await p.screenshot({ path: path.join(out, 'payment-readonly-narrow.png') });
  await finance.ctx.close();

  const contract = await login('fixture_role_contract_operator');
  await list(contract.page, 662, 'contract-list');
  await form(contract.page, '/r/sc.general.contract/11?menu_id=662', 'contract-readonly', 'readonly');
  await contract.ctx.close();
  }

  if (process.env.TPL07_SCOPE !== 'detail') {
  const admin = await login('fixture_role_config_admin');
  // Resolve a non-pilot entry from authorized navigation instead of model IDs.
  await admin.page.getByPlaceholder('搜索菜单...').fill('客户档案');
  await admin.page.getByText('客户档案', { exact: true }).first().click();
  await admin.page.locator('[data-list-card-container="official"]').waitFor();
  check('non-pilot standard list: official default', await admin.page.locator('[data-list-composition-reason="contract-collection-view"]').count() === 1);
  await admin.page.screenshot({ path: path.join(out, 'customer-list.png') });
  await admin.ctx.close();
  }
  check('no page exceptions', report.errors.length === 0);
  check('no business writes attempted', report.forbiddenWrites.length === 0);
  report.status = 'passed';
} catch (error) {
  report.status = 'failed';
  report.error = error.message;
  process.exitCode = 1;
} finally {
  await browser.close();
  await fs.writeFile(path.join(out, 'report.json'), JSON.stringify(report, null, 2));
  console.log(`[standard_page_type_browser] ${report.status} assertions=${report.assertions.length} report=${out}/report.json`);
}
